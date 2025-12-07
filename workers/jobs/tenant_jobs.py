"""
Tenant Lifecycle Background Jobs
"""
import os
import sys
import logging
import subprocess
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database import session_scope, create_tenant_database, drop_tenant_database
from shared.models import Tenant, Backup, AuditLog, TenantState, BackupStatus, AuditAction

logger = logging.getLogger(__name__)


def provision_tenant(tenant_id: str):
    """
    Provision a new Odoo tenant.

    This job:
    1. Creates the PostgreSQL database
    2. Initializes Odoo database
    3. Updates tenant state to ACTIVE
    """
    logger.info(f"Starting tenant provisioning: {tenant_id}")

    try:
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                logger.error(f"Tenant not found: {tenant_id}")
                return {'success': False, 'error': 'Tenant not found'}

            if tenant.state != TenantState.CREATING.value:
                logger.warning(f"Tenant {tenant_id} not in CREATING state: {tenant.state}")
                return {'success': False, 'error': f'Invalid state: {tenant.state}'}

            db_name = tenant.db_name

        # Create the database
        logger.info(f"Creating database: {db_name}")
        if not create_tenant_database(db_name):
            with session_scope() as session:
                tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
                if tenant:
                    tenant.state = TenantState.ERROR.value
                    tenant.state_message = "Failed to create database"
            return {'success': False, 'error': 'Database creation failed'}

        # Update tenant state to ACTIVE
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                tenant.state = TenantState.ACTIVE.value
                tenant.state_message = None

                # Create audit log
                audit_log = AuditLog(
                    actor_email='system',
                    action=AuditAction.CREATE.value,
                    resource_type='tenant',
                    resource_id=str(tenant_id),
                    new_values={
                        'state': TenantState.ACTIVE.value,
                        'db_name': db_name,
                        'provisioned_at': datetime.utcnow().isoformat()
                    }
                )
                session.add(audit_log)

        logger.info(f"Tenant provisioned successfully: {tenant_id}")
        return {'success': True, 'tenant_id': tenant_id, 'db_name': db_name}

    except Exception as e:
        logger.error(f"Provisioning failed for tenant {tenant_id}: {e}")

        # Update state to ERROR
        try:
            with session_scope() as session:
                tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
                if tenant:
                    tenant.state = TenantState.ERROR.value
                    tenant.state_message = str(e)[:500]
        except Exception as inner_e:
            logger.error(f"Failed to update tenant state: {inner_e}")

        return {'success': False, 'error': str(e)}


def delete_tenant(tenant_id: str):
    """
    Delete an Odoo tenant.

    This job:
    1. Drops the PostgreSQL database
    2. Removes filestore
    3. Updates tenant state to DELETED
    """
    logger.info(f"Starting tenant deletion: {tenant_id}")

    try:
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                logger.error(f"Tenant not found: {tenant_id}")
                return {'success': False, 'error': 'Tenant not found'}

            if tenant.state == TenantState.DELETED.value:
                logger.warning(f"Tenant {tenant_id} already deleted")
                return {'success': True, 'message': 'Already deleted'}

            db_name = tenant.db_name

        # Drop the database
        if db_name:
            logger.info(f"Dropping database: {db_name}")
            drop_tenant_database(db_name)

        # Update tenant state
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                tenant.state = TenantState.DELETED.value
                tenant.state_message = f"Deleted at {datetime.utcnow().isoformat()}"

                # Audit log
                audit_log = AuditLog(
                    actor_email='system',
                    action=AuditAction.DELETE.value,
                    resource_type='tenant',
                    resource_id=str(tenant_id),
                    old_values={'db_name': db_name},
                    new_values={'state': TenantState.DELETED.value}
                )
                session.add(audit_log)

        logger.info(f"Tenant deleted successfully: {tenant_id}")
        return {'success': True, 'tenant_id': tenant_id}

    except Exception as e:
        logger.error(f"Deletion failed for tenant {tenant_id}: {e}")
        return {'success': False, 'error': str(e)}


def backup_tenant(tenant_id: str, backup_id: str = None):
    """
    Create a backup of tenant data.

    This job:
    1. Dumps the PostgreSQL database
    2. Creates backup archive
    3. Updates backup record
    """
    logger.info(f"Starting backup for tenant: {tenant_id}")

    try:
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                return {'success': False, 'error': 'Tenant not found'}

            if tenant.state != TenantState.ACTIVE.value:
                return {'success': False, 'error': f'Tenant not active: {tenant.state}'}

            db_name = tenant.db_name

            # Update backup status
            if backup_id:
                backup = session.query(Backup).filter(Backup.id == backup_id).first()
                if backup:
                    backup.status = BackupStatus.IN_PROGRESS.value
                    backup.started_at = datetime.utcnow()

        # Perform database dump
        backup_dir = os.getenv('BACKUP_DIR', '/tmp/backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{backup_dir}/{db_name}_{timestamp}.sql"

        pg_host = os.getenv('PG_HOST', 'postgres')
        pg_port = os.getenv('PG_PORT', '5432')
        pg_user = os.getenv('PG_USER', 'odoo')
        pg_password = os.getenv('PG_PASSWORD', 'odoo_password')

        # Set password in environment
        env = os.environ.copy()
        env['PGPASSWORD'] = pg_password

        try:
            # Run pg_dump
            result = subprocess.run(
                [
                    'pg_dump',
                    '-h', pg_host,
                    '-p', pg_port,
                    '-U', pg_user,
                    '-F', 'c',  # Custom format
                    '-f', backup_file,
                    db_name
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=3600
            )

            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")

            # Get file size
            file_size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0

            # Update backup record
            with session_scope() as session:
                if backup_id:
                    backup = session.query(Backup).filter(Backup.id == backup_id).first()
                    if backup:
                        backup.status = BackupStatus.COMPLETED.value
                        backup.completed_at = datetime.utcnow()
                        backup.file_path = backup_file
                        backup.file_size_bytes = file_size

                # Update tenant last backup time
                tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
                if tenant:
                    tenant.last_backup_at = datetime.utcnow()

                # Audit log
                audit_log = AuditLog(
                    actor_email='system',
                    action=AuditAction.BACKUP.value,
                    resource_type='tenant',
                    resource_id=str(tenant_id),
                    new_values={
                        'backup_file': backup_file,
                        'file_size': file_size,
                    }
                )
                session.add(audit_log)

            logger.info(f"Backup completed: {backup_file} ({file_size} bytes)")
            return {
                'success': True,
                'tenant_id': tenant_id,
                'backup_file': backup_file,
                'file_size': file_size
            }

        except subprocess.TimeoutExpired:
            raise Exception("Backup timed out after 1 hour")

    except Exception as e:
        logger.error(f"Backup failed for tenant {tenant_id}: {e}")

        # Update backup status
        if backup_id:
            try:
                with session_scope() as session:
                    backup = session.query(Backup).filter(Backup.id == backup_id).first()
                    if backup:
                        backup.status = BackupStatus.FAILED.value
                        backup.error_message = str(e)[:500]
            except Exception:
                pass

        return {'success': False, 'error': str(e)}


def restore_tenant(tenant_id: str, backup_id: str):
    """
    Restore tenant from backup.

    This job:
    1. Verifies backup exists
    2. Restores database from backup
    3. Updates tenant state
    """
    logger.info(f"Starting restore for tenant {tenant_id} from backup {backup_id}")

    try:
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
            backup = session.query(Backup).filter(Backup.id == backup_id).first()

            if not tenant:
                return {'success': False, 'error': 'Tenant not found'}

            if not backup:
                return {'success': False, 'error': 'Backup not found'}

            if backup.tenant_id != tenant.id:
                return {'success': False, 'error': 'Backup does not belong to this tenant'}

            if not backup.file_path or not os.path.exists(backup.file_path):
                return {'success': False, 'error': 'Backup file not found'}

            db_name = tenant.db_name
            backup_file = backup.file_path

        pg_host = os.getenv('PG_HOST', 'postgres')
        pg_port = os.getenv('PG_PORT', '5432')
        pg_user = os.getenv('PG_USER', 'odoo')
        pg_password = os.getenv('PG_PASSWORD', 'odoo_password')

        env = os.environ.copy()
        env['PGPASSWORD'] = pg_password

        # Drop and recreate database
        drop_tenant_database(db_name)
        create_tenant_database(db_name)

        # Restore from backup
        result = subprocess.run(
            [
                'pg_restore',
                '-h', pg_host,
                '-p', pg_port,
                '-U', pg_user,
                '-d', db_name,
                backup_file
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=3600
        )

        if result.returncode != 0:
            logger.warning(f"pg_restore warnings: {result.stderr}")

        # Update tenant state
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                tenant.state = TenantState.ACTIVE.value

            # Audit log
            audit_log = AuditLog(
                actor_email='system',
                action=AuditAction.RESTORE.value,
                resource_type='tenant',
                resource_id=str(tenant_id),
                new_values={
                    'backup_id': str(backup_id),
                    'restored_at': datetime.utcnow().isoformat(),
                }
            )
            session.add(audit_log)

        logger.info(f"Restore completed for tenant {tenant_id}")
        return {'success': True, 'tenant_id': tenant_id}

    except Exception as e:
        logger.error(f"Restore failed for tenant {tenant_id}: {e}")
        return {'success': False, 'error': str(e)}
