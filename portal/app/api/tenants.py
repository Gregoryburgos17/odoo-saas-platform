"""
Tenant Management API for Customer Portal
"""
import logging
import re
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, current_user
from redis import Redis
from rq import Queue

from shared.database import session_scope, get_session
from shared.models import Tenant, Plan, AuditLog, AuditAction, TenantState

logger = logging.getLogger(__name__)

tenants_bp = Blueprint('tenants', __name__)


def validate_slug(slug: str) -> bool:
    """Validate tenant slug"""
    pattern = r'^[a-z][a-z0-9-]{2,48}[a-z0-9]$'
    return bool(re.match(pattern, slug))


def get_redis_queue():
    """Get Redis queue connection"""
    try:
        redis_conn = Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', '6379'))
        )
        return Queue('default', connection=redis_conn)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None


@tenants_bp.route('', methods=['GET'])
@tenants_bp.route('/', methods=['GET'])
@jwt_required()
def list_tenants():
    """List customer's tenants"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        # Get customer's tenants only
        tenants = session.query(Tenant).filter(
            Tenant.customer_id == identity,
            Tenant.state != TenantState.DELETED.value
        ).order_by(Tenant.created_at.desc()).all()

        result = {
            'status': 'success',
            'data': {
                'tenants': [t.to_dict() for t in tenants]
            }
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"List tenants error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list tenants'}), 500


@tenants_bp.route('/<tenant_id>', methods=['GET'])
@jwt_required()
def get_tenant(tenant_id):
    """Get tenant details"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        tenant = session.query(Tenant).filter(
            Tenant.id == tenant_id,
            Tenant.customer_id == identity
        ).first()

        if not tenant:
            session.close()
            return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

        # Get plan details
        plan_data = None
        if tenant.plan:
            plan_data = tenant.plan.to_dict()

        result = tenant.to_dict()
        result['plan'] = plan_data

        session.close()
        return jsonify({'status': 'success', 'data': result}), 200

    except Exception as e:
        logger.error(f"Get tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get tenant'}), 500


@tenants_bp.route('', methods=['POST'])
@tenants_bp.route('/', methods=['POST'])
@jwt_required()
def create_tenant():
    """Create a new tenant"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    slug = data.get('slug', '').strip().lower()
    name = data.get('name', '').strip()
    plan_id = data.get('plan_id')

    # Validation
    if not slug or not validate_slug(slug):
        return jsonify({
            'status': 'error',
            'message': 'Invalid slug. Use 4-50 lowercase letters, numbers, and hyphens. Must start with a letter.'
        }), 400

    if not name:
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            # Check tenant limit
            from shared.models import Customer
            customer = session.query(Customer).filter(Customer.id == identity).first()

            if not customer:
                return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

            existing_count = session.query(Tenant).filter(
                Tenant.customer_id == identity,
                Tenant.state != TenantState.DELETED.value
            ).count()

            if existing_count >= customer.max_tenants:
                return jsonify({
                    'status': 'error',
                    'message': f'Tenant limit reached ({customer.max_tenants}). Upgrade your plan for more.'
                }), 403

            # Check slug availability
            existing_slug = session.query(Tenant).filter(Tenant.slug == slug).first()
            if existing_slug:
                return jsonify({'status': 'error', 'message': 'This slug is already taken'}), 409

            # Validate plan if provided
            if plan_id:
                plan = session.query(Plan).filter(Plan.id == plan_id, Plan.is_active == True).first()
                if not plan:
                    return jsonify({'status': 'error', 'message': 'Invalid plan selected'}), 400

            # Create tenant
            tenant = Tenant(
                slug=slug,
                name=name,
                customer_id=identity,
                plan_id=plan_id,
                state=TenantState.CREATING.value,
                db_name=f"odoo_{slug.replace('-', '_')}",
            )
            session.add(tenant)
            session.flush()

            # Audit log
            audit_log = AuditLog(
                actor_id=customer.id,
                actor_email=customer.email,
                actor_role=customer.role,
                action=AuditAction.CREATE.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
                new_values={'slug': slug, 'name': name}
            )
            session.add(audit_log)

            tenant_data = tenant.to_dict()

            # Queue provisioning job
            queue = get_redis_queue()
            if queue:
                try:
                    queue.enqueue(
                        'workers.jobs.tenant_jobs.provision_tenant',
                        str(tenant.id),
                        job_timeout=1800
                    )
                except Exception as e:
                    logger.warning(f"Failed to queue provisioning: {e}")

            return jsonify({
                'status': 'success',
                'message': 'Tenant creation initiated',
                'data': tenant_data
            }), 202

    except Exception as e:
        logger.error(f"Create tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create tenant'}), 500


@tenants_bp.route('/<tenant_id>', methods=['PUT'])
@jwt_required()
def update_tenant(tenant_id):
    """Update tenant details"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            tenant = session.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.customer_id == identity
            ).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            # Update allowed fields
            if 'name' in data:
                tenant.name = data['name'].strip()
            if 'custom_domain' in data:
                tenant.custom_domain = data['custom_domain'].strip() if data['custom_domain'] else None

            return jsonify({
                'status': 'success',
                'message': 'Tenant updated',
                'data': tenant.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Update tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update tenant'}), 500


@tenants_bp.route('/<tenant_id>', methods=['DELETE'])
@jwt_required()
def delete_tenant(tenant_id):
    """Delete a tenant"""
    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            tenant = session.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.customer_id == identity
            ).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            if tenant.state == TenantState.DELETED.value:
                return jsonify({'status': 'error', 'message': 'Tenant already deleted'}), 400

            tenant.state = TenantState.DELETING.value

            # Audit log
            from shared.models import Customer
            customer = session.query(Customer).filter(Customer.id == identity).first()
            audit_log = AuditLog(
                actor_id=customer.id if customer else None,
                actor_email=customer.email if customer else 'unknown',
                action=AuditAction.DELETE.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
            )
            session.add(audit_log)

            # Queue deletion job
            queue = get_redis_queue()
            if queue:
                try:
                    queue.enqueue(
                        'workers.jobs.tenant_jobs.delete_tenant',
                        str(tenant.id),
                        job_timeout=1800
                    )
                except Exception as e:
                    logger.warning(f"Failed to queue deletion: {e}")

            return jsonify({
                'status': 'success',
                'message': 'Tenant deletion initiated'
            }), 202

    except Exception as e:
        logger.error(f"Delete tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete tenant'}), 500


@tenants_bp.route('/<tenant_id>/backup', methods=['POST'])
@jwt_required()
def create_backup(tenant_id):
    """Create a backup for tenant"""
    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            tenant = session.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.customer_id == identity
            ).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            if tenant.state != TenantState.ACTIVE.value:
                return jsonify({'status': 'error', 'message': 'Tenant must be active to backup'}), 400

            # Create backup record
            from shared.models import Backup, BackupStatus
            from datetime import datetime

            backup = Backup(
                tenant_id=tenant.id,
                backup_type='full',
                status=BackupStatus.PENDING.value,
                started_at=datetime.utcnow(),
            )
            session.add(backup)
            session.flush()

            backup_data = backup.to_dict()

            # Queue backup job
            queue = get_redis_queue()
            if queue:
                try:
                    queue.enqueue(
                        'workers.jobs.tenant_jobs.backup_tenant',
                        str(tenant.id),
                        str(backup.id),
                        job_timeout=3600
                    )
                except Exception as e:
                    logger.warning(f"Failed to queue backup: {e}")

            return jsonify({
                'status': 'success',
                'message': 'Backup initiated',
                'data': backup_data
            }), 202

    except Exception as e:
        logger.error(f"Create backup error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create backup'}), 500


@tenants_bp.route('/<tenant_id>/backups', methods=['GET'])
@jwt_required()
def list_backups(tenant_id):
    """List tenant backups"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        tenant = session.query(Tenant).filter(
            Tenant.id == tenant_id,
            Tenant.customer_id == identity
        ).first()

        if not tenant:
            session.close()
            return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

        from shared.models import Backup
        backups = session.query(Backup).filter(
            Backup.tenant_id == tenant_id
        ).order_by(Backup.created_at.desc()).limit(50).all()

        result = {
            'status': 'success',
            'data': {
                'backups': [b.to_dict() for b in backups]
            }
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"List backups error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list backups'}), 500
