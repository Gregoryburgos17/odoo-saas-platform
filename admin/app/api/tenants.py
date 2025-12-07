"""
Tenants Management API (Admin)
"""
import logging
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user

from shared.database import session_scope, get_session
from shared.models import Tenant, Customer, Plan, AuditLog, AuditAction, TenantState

logger = logging.getLogger(__name__)

tenants_bp = Blueprint('tenants', __name__)


def validate_slug(slug: str) -> bool:
    """Validate tenant slug format"""
    pattern = r'^[a-z][a-z0-9-]{2,48}[a-z0-9]$'
    return bool(re.match(pattern, slug))


@tenants_bp.route('', methods=['GET'])
@tenants_bp.route('/', methods=['GET'])
@jwt_required()
def list_tenants():
    """List all tenants (admin view)"""
    try:
        session = get_session()

        # Query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        state_filter = request.args.get('state')
        customer_id = request.args.get('customer_id')
        search = request.args.get('search', '').strip()

        query = session.query(Tenant)

        # Apply filters
        if state_filter:
            query = query.filter(Tenant.state == state_filter)
        if customer_id:
            query = query.filter(Tenant.customer_id == customer_id)
        if search:
            query = query.filter(
                (Tenant.name.ilike(f'%{search}%')) |
                (Tenant.slug.ilike(f'%{search}%'))
            )

        # Count and paginate
        total = query.count()
        tenants = query.order_by(Tenant.created_at.desc()) \
            .offset((page - 1) * per_page) \
            .limit(per_page) \
            .all()

        result = {
            'status': 'success',
            'data': {
                'tenants': [t.to_dict() for t in tenants],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
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
        session = get_session()
        tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

        if not tenant:
            session.close()
            return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

        result = {
            'status': 'success',
            'data': tenant.to_dict()
        }

        session.close()
        return jsonify(result), 200

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
    customer_id = data.get('customer_id')
    plan_id = data.get('plan_id')

    # Validation
    if not slug or not validate_slug(slug):
        return jsonify({
            'status': 'error',
            'message': 'Invalid slug. Must be 4-50 chars, lowercase alphanumeric and hyphens, start with letter.'
        }), 400

    if not name:
        return jsonify({'status': 'error', 'message': 'Name is required'}), 400

    if not customer_id:
        return jsonify({'status': 'error', 'message': 'Customer ID is required'}), 400

    try:
        with session_scope() as session:
            # Verify customer exists
            customer = session.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

            # Check slug uniqueness
            existing = session.query(Tenant).filter(Tenant.slug == slug).first()
            if existing:
                return jsonify({'status': 'error', 'message': 'Slug already in use'}), 409

            # Check customer tenant limit
            tenant_count = session.query(Tenant).filter(
                Tenant.customer_id == customer_id,
                Tenant.state != TenantState.DELETED.value
            ).count()

            if tenant_count >= customer.max_tenants:
                return jsonify({
                    'status': 'error',
                    'message': f'Tenant limit reached ({customer.max_tenants})'
                }), 403

            # Create tenant
            tenant = Tenant(
                slug=slug,
                name=name,
                customer_id=customer_id,
                plan_id=plan_id,
                state=TenantState.CREATING.value,
                db_name=f"odoo_{slug.replace('-', '_')}",
            )
            session.add(tenant)
            session.flush()

            # Create audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.CREATE.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
                new_values={'slug': slug, 'name': name, 'customer_id': str(customer_id)}
            )
            session.add(audit_log)

            # Queue provisioning job
            try:
                from redis import Redis
                from rq import Queue
                import os

                redis_conn = Redis(
                    host=os.getenv('REDIS_HOST', 'redis'),
                    port=int(os.getenv('REDIS_PORT', '6379'))
                )
                q = Queue('default', connection=redis_conn)
                q.enqueue(
                    'workers.jobs.tenant_jobs.provision_tenant',
                    str(tenant.id),
                    job_timeout=1800
                )
            except Exception as e:
                logger.warning(f"Failed to queue provisioning job: {e}")

            return jsonify({
                'status': 'success',
                'message': 'Tenant creation initiated',
                'data': tenant.to_dict()
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
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            old_values = tenant.to_dict()

            # Update allowed fields
            if 'name' in data:
                tenant.name = data['name'].strip()
            if 'plan_id' in data:
                tenant.plan_id = data['plan_id']
            if 'custom_domain' in data:
                tenant.custom_domain = data['custom_domain']
            if 'odoo_config' in data:
                tenant.odoo_config = data['odoo_config']

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.UPDATE.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
                old_values=old_values,
                new_values=tenant.to_dict()
            )
            session.add(audit_log)

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
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            if tenant.state == TenantState.DELETED.value:
                return jsonify({'status': 'error', 'message': 'Tenant already deleted'}), 400

            old_state = tenant.state
            tenant.state = TenantState.DELETING.value

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.DELETE.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
                old_values={'state': old_state},
                new_values={'state': TenantState.DELETING.value}
            )
            session.add(audit_log)

            # Queue deletion job
            try:
                from redis import Redis
                from rq import Queue
                import os

                redis_conn = Redis(
                    host=os.getenv('REDIS_HOST', 'redis'),
                    port=int(os.getenv('REDIS_PORT', '6379'))
                )
                q = Queue('default', connection=redis_conn)
                q.enqueue(
                    'workers.jobs.tenant_jobs.delete_tenant',
                    str(tenant.id),
                    job_timeout=1800
                )
            except Exception as e:
                logger.warning(f"Failed to queue deletion job: {e}")

            return jsonify({
                'status': 'success',
                'message': 'Tenant deletion initiated'
            }), 202

    except Exception as e:
        logger.error(f"Delete tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete tenant'}), 500


@tenants_bp.route('/<tenant_id>/suspend', methods=['POST'])
@jwt_required()
def suspend_tenant(tenant_id):
    """Suspend a tenant"""
    try:
        from datetime import datetime

        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            if tenant.state != TenantState.ACTIVE.value:
                return jsonify({
                    'status': 'error',
                    'message': f'Cannot suspend tenant in {tenant.state} state'
                }), 400

            old_state = tenant.state
            tenant.state = TenantState.SUSPENDED.value
            tenant.suspended_at = datetime.utcnow()

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.SUSPEND.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
                old_values={'state': old_state},
                new_values={'state': TenantState.SUSPENDED.value}
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Tenant suspended',
                'data': tenant.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Suspend tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to suspend tenant'}), 500


@tenants_bp.route('/<tenant_id>/resume', methods=['POST'])
@jwt_required()
def resume_tenant(tenant_id):
    """Resume a suspended tenant"""
    try:
        with session_scope() as session:
            tenant = session.query(Tenant).filter(Tenant.id == tenant_id).first()

            if not tenant:
                return jsonify({'status': 'error', 'message': 'Tenant not found'}), 404

            if tenant.state != TenantState.SUSPENDED.value:
                return jsonify({
                    'status': 'error',
                    'message': f'Cannot resume tenant in {tenant.state} state'
                }), 400

            old_state = tenant.state
            tenant.state = TenantState.ACTIVE.value
            tenant.suspended_at = None

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.RESUME.value,
                resource_type='tenant',
                resource_id=str(tenant.id),
                ip_address=request.remote_addr,
                old_values={'state': old_state},
                new_values={'state': TenantState.ACTIVE.value}
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Tenant resumed',
                'data': tenant.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Resume tenant error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to resume tenant'}), 500
