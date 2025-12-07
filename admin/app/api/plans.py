"""
Plans Management API (Admin)
"""
import logging
import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user

from shared.database import session_scope, get_session
from shared.models import Plan, AuditLog, AuditAction

logger = logging.getLogger(__name__)

plans_bp = Blueprint('plans', __name__)


def slugify(text: str) -> str:
    """Create URL-safe slug from text"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


@plans_bp.route('', methods=['GET'])
@plans_bp.route('/', methods=['GET'])
@jwt_required()
def list_plans():
    """List all plans"""
    try:
        session = get_session()

        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

        query = session.query(Plan)
        if not include_inactive:
            query = query.filter(Plan.is_active == True)

        plans = query.order_by(Plan.sort_order, Plan.price_monthly).all()

        result = {
            'status': 'success',
            'data': {
                'plans': [p.to_dict() for p in plans]
            }
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"List plans error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list plans'}), 500


@plans_bp.route('/<plan_id>', methods=['GET'])
@jwt_required()
def get_plan(plan_id):
    """Get plan details"""
    try:
        session = get_session()
        plan = session.query(Plan).filter(Plan.id == plan_id).first()

        if not plan:
            session.close()
            return jsonify({'status': 'error', 'message': 'Plan not found'}), 404

        result = {
            'status': 'success',
            'data': plan.to_dict()
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Get plan error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get plan'}), 500


@plans_bp.route('', methods=['POST'])
@plans_bp.route('/', methods=['POST'])
@jwt_required()
def create_plan():
    """Create a new plan"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    name = data.get('name', '').strip()
    slug = data.get('slug', '').strip() or slugify(name)
    description = data.get('description', '')
    price_monthly = data.get('price_monthly', 0)
    price_yearly = data.get('price_yearly')
    currency = data.get('currency', 'USD')

    # Limits
    max_tenants = data.get('max_tenants', 1)
    max_users_per_tenant = data.get('max_users_per_tenant', 5)
    max_db_size_gb = data.get('max_db_size_gb', 1)
    max_filestore_gb = data.get('max_filestore_gb', 1)

    # Features
    features = data.get('features', {})
    allowed_modules = data.get('allowed_modules', [])
    trial_days = data.get('trial_days', 14)

    # Validation
    if not name:
        return jsonify({'status': 'error', 'message': 'Plan name is required'}), 400

    try:
        with session_scope() as session:
            # Check slug uniqueness
            existing = session.query(Plan).filter(
                (Plan.slug == slug) | (Plan.name == name)
            ).first()
            if existing:
                return jsonify({'status': 'error', 'message': 'Plan name or slug already exists'}), 409

            # Create plan
            plan = Plan(
                name=name,
                slug=slug,
                description=description,
                price_monthly=price_monthly,
                price_yearly=price_yearly,
                currency=currency,
                max_tenants=max_tenants,
                max_users_per_tenant=max_users_per_tenant,
                max_db_size_gb=max_db_size_gb,
                max_filestore_gb=max_filestore_gb,
                features=features,
                allowed_modules=allowed_modules,
                trial_days=trial_days,
                is_active=True,
            )
            session.add(plan)
            session.flush()

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.CREATE.value,
                resource_type='plan',
                resource_id=str(plan.id),
                ip_address=request.remote_addr,
                new_values={'name': name, 'slug': slug, 'price_monthly': float(price_monthly)}
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Plan created',
                'data': plan.to_dict()
            }), 201

    except Exception as e:
        logger.error(f"Create plan error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create plan'}), 500


@plans_bp.route('/<plan_id>', methods=['PUT'])
@jwt_required()
def update_plan(plan_id):
    """Update plan details"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    try:
        with session_scope() as session:
            plan = session.query(Plan).filter(Plan.id == plan_id).first()

            if not plan:
                return jsonify({'status': 'error', 'message': 'Plan not found'}), 404

            old_values = plan.to_dict()

            # Update fields
            if 'name' in data:
                plan.name = data['name'].strip()
            if 'description' in data:
                plan.description = data['description']
            if 'price_monthly' in data:
                plan.price_monthly = data['price_monthly']
            if 'price_yearly' in data:
                plan.price_yearly = data['price_yearly']
            if 'currency' in data:
                plan.currency = data['currency']
            if 'max_tenants' in data:
                plan.max_tenants = data['max_tenants']
            if 'max_users_per_tenant' in data:
                plan.max_users_per_tenant = data['max_users_per_tenant']
            if 'max_db_size_gb' in data:
                plan.max_db_size_gb = data['max_db_size_gb']
            if 'max_filestore_gb' in data:
                plan.max_filestore_gb = data['max_filestore_gb']
            if 'features' in data:
                plan.features = data['features']
            if 'allowed_modules' in data:
                plan.allowed_modules = data['allowed_modules']
            if 'trial_days' in data:
                plan.trial_days = data['trial_days']
            if 'is_active' in data:
                plan.is_active = data['is_active']
            if 'sort_order' in data:
                plan.sort_order = data['sort_order']

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.UPDATE.value,
                resource_type='plan',
                resource_id=str(plan.id),
                ip_address=request.remote_addr,
                old_values=old_values,
                new_values=plan.to_dict()
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Plan updated',
                'data': plan.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Update plan error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update plan'}), 500


@plans_bp.route('/<plan_id>', methods=['DELETE'])
@jwt_required()
def delete_plan(plan_id):
    """Deactivate a plan (soft delete)"""
    try:
        with session_scope() as session:
            plan = session.query(Plan).filter(Plan.id == plan_id).first()

            if not plan:
                return jsonify({'status': 'error', 'message': 'Plan not found'}), 404

            # Check for active tenants
            from shared.models import Tenant, TenantState
            active_tenants = session.query(Tenant).filter(
                Tenant.plan_id == plan_id,
                Tenant.state.notin_([TenantState.DELETED.value])
            ).count()

            if active_tenants > 0:
                return jsonify({
                    'status': 'error',
                    'message': f'Cannot delete plan with {active_tenants} active tenant(s). Deactivate instead.'
                }), 400

            plan.is_active = False

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.DELETE.value,
                resource_type='plan',
                resource_id=str(plan.id),
                ip_address=request.remote_addr,
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Plan deactivated'
            }), 200

    except Exception as e:
        logger.error(f"Delete plan error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete plan'}), 500
