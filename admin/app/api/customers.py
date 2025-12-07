"""
Customers Management API (Admin)
"""
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user

from shared.database import session_scope, get_session
from shared.models import Customer, AuditLog, AuditAction, CustomerRole

logger = logging.getLogger(__name__)

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('', methods=['GET'])
@customers_bp.route('/', methods=['GET'])
@jwt_required()
def list_customers():
    """List all customers"""
    try:
        session = get_session()

        # Query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        search = request.args.get('search', '').strip()
        is_active = request.args.get('is_active')
        role = request.args.get('role')

        query = session.query(Customer)

        # Apply filters
        if search:
            query = query.filter(
                (Customer.email.ilike(f'%{search}%')) |
                (Customer.first_name.ilike(f'%{search}%')) |
                (Customer.last_name.ilike(f'%{search}%')) |
                (Customer.company.ilike(f'%{search}%'))
            )
        if is_active is not None:
            query = query.filter(Customer.is_active == (is_active.lower() == 'true'))
        if role:
            query = query.filter(Customer.role == role)

        # Count and paginate
        total = query.count()
        customers = query.order_by(Customer.created_at.desc()) \
            .offset((page - 1) * per_page) \
            .limit(per_page) \
            .all()

        result = {
            'status': 'success',
            'data': {
                'customers': [c.to_dict() for c in customers],
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
        logger.error(f"List customers error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list customers'}), 500


@customers_bp.route('/<customer_id>', methods=['GET'])
@jwt_required()
def get_customer(customer_id):
    """Get customer details"""
    try:
        session = get_session()
        customer = session.query(Customer).filter(Customer.id == customer_id).first()

        if not customer:
            session.close()
            return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

        # Get tenant count
        tenant_count = customer.tenants.count()

        result = customer.to_dict()
        result['tenant_count'] = tenant_count

        session.close()
        return jsonify({
            'status': 'success',
            'data': result
        }), 200

    except Exception as e:
        logger.error(f"Get customer error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get customer'}), 500


@customers_bp.route('', methods=['POST'])
@customers_bp.route('/', methods=['POST'])
@jwt_required()
def create_customer():
    """Create a new customer"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    company = data.get('company', '').strip()
    role = data.get('role', CustomerRole.OWNER.value)
    max_tenants = data.get('max_tenants', 5)
    max_quota_gb = data.get('max_quota_gb', 50)

    # Validation
    if not email or '@' not in email:
        return jsonify({'status': 'error', 'message': 'Valid email is required'}), 400

    if not password or len(password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400

    if role not in [r.value for r in CustomerRole]:
        return jsonify({'status': 'error', 'message': 'Invalid role'}), 400

    try:
        with session_scope() as session:
            # Check if email exists
            existing = session.query(Customer).filter(Customer.email == email).first()
            if existing:
                return jsonify({'status': 'error', 'message': 'Email already registered'}), 409

            # Create customer
            customer = Customer(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company=company,
                role=role,
                max_tenants=max_tenants,
                max_quota_gb=max_quota_gb,
                is_active=True,
                is_verified=True,  # Admin-created accounts are pre-verified
            )
            customer.set_password(password)
            session.add(customer)
            session.flush()

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.CREATE.value,
                resource_type='customer',
                resource_id=str(customer.id),
                ip_address=request.remote_addr,
                new_values={'email': email, 'role': role}
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Customer created',
                'data': customer.to_dict()
            }), 201

    except Exception as e:
        logger.error(f"Create customer error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create customer'}), 500


@customers_bp.route('/<customer_id>', methods=['PUT'])
@jwt_required()
def update_customer(customer_id):
    """Update customer details"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    try:
        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.id == customer_id).first()

            if not customer:
                return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

            old_values = customer.to_dict()

            # Update fields
            if 'first_name' in data:
                customer.first_name = data['first_name'].strip()
            if 'last_name' in data:
                customer.last_name = data['last_name'].strip()
            if 'company' in data:
                customer.company = data['company'].strip()
            if 'phone' in data:
                customer.phone = data['phone'].strip()
            if 'role' in data and data['role'] in [r.value for r in CustomerRole]:
                customer.role = data['role']
            if 'is_active' in data:
                customer.is_active = bool(data['is_active'])
            if 'is_verified' in data:
                customer.is_verified = bool(data['is_verified'])
            if 'max_tenants' in data:
                customer.max_tenants = int(data['max_tenants'])
            if 'max_quota_gb' in data:
                customer.max_quota_gb = int(data['max_quota_gb'])

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.UPDATE.value,
                resource_type='customer',
                resource_id=str(customer.id),
                ip_address=request.remote_addr,
                old_values=old_values,
                new_values=customer.to_dict()
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Customer updated',
                'data': customer.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Update customer error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update customer'}), 500


@customers_bp.route('/<customer_id>', methods=['DELETE'])
@jwt_required()
def delete_customer(customer_id):
    """Delete/deactivate a customer"""
    try:
        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.id == customer_id).first()

            if not customer:
                return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

            # Check for active tenants
            from shared.models import Tenant, TenantState
            active_tenants = session.query(Tenant).filter(
                Tenant.customer_id == customer_id,
                Tenant.state.notin_([TenantState.DELETED.value])
            ).count()

            if active_tenants > 0:
                return jsonify({
                    'status': 'error',
                    'message': f'Cannot delete customer with {active_tenants} active tenant(s)'
                }), 400

            # Soft delete - deactivate
            customer.is_active = False

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.DELETE.value,
                resource_type='customer',
                resource_id=str(customer.id),
                ip_address=request.remote_addr,
                old_values={'is_active': True},
                new_values={'is_active': False}
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Customer deactivated'
            }), 200

    except Exception as e:
        logger.error(f"Delete customer error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete customer'}), 500


@customers_bp.route('/<customer_id>/reset-password', methods=['POST'])
@jwt_required()
def reset_customer_password(customer_id):
    """Reset customer password (admin action)"""
    data = request.get_json()

    if not data or 'new_password' not in data:
        return jsonify({'status': 'error', 'message': 'New password required'}), 400

    new_password = data['new_password']
    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400

    try:
        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.id == customer_id).first()

            if not customer:
                return jsonify({'status': 'error', 'message': 'Customer not found'}), 404

            customer.set_password(new_password)

            # Audit log
            audit_log = AuditLog(
                actor_id=current_user.id if current_user else None,
                actor_email=current_user.email if current_user else 'system',
                action=AuditAction.PASSWORD_CHANGE.value,
                resource_type='customer',
                resource_id=str(customer.id),
                ip_address=request.remote_addr,
                extra_metadata={'admin_reset': True}
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Password reset successfully'
            }), 200

    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to reset password'}), 500
