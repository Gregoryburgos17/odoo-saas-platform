"""
Customer Authentication API
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, current_user
)

from shared.database import session_scope, get_session
from shared.models import Customer, AuditLog, AuditAction, CustomerRole

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new customer"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    company = data.get('company', '').strip()

    # Validation
    if not email or '@' not in email:
        return jsonify({'status': 'error', 'message': 'Valid email is required'}), 400

    if not password or len(password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400

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
                role=CustomerRole.OWNER.value,
                is_active=True,
                is_verified=False,
            )
            customer.set_password(password)
            session.add(customer)
            session.flush()

            # Audit log
            audit_log = AuditLog(
                actor_id=customer.id,
                actor_email=email,
                actor_role=customer.role,
                action=AuditAction.CREATE.value,
                resource_type='customer',
                resource_id=str(customer.id),
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string[:500] if request.user_agent else None,
            )
            session.add(audit_log)

            # Generate tokens
            access_token = create_access_token(identity=customer)
            refresh_token = create_refresh_token(identity=customer)

            return jsonify({
                'status': 'success',
                'message': 'Registration successful',
                'data': {
                    'user': customer.to_dict(),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                }
            }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'status': 'error', 'message': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Customer login"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password required'}), 400

    try:
        session = get_session()
        customer = session.query(Customer).filter(Customer.email == email).first()

        if not customer or not customer.check_password(password):
            session.close()
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

        if not customer.is_active:
            session.close()
            return jsonify({'status': 'error', 'message': 'Account is disabled'}), 403

        # Update last login
        customer.last_login = datetime.utcnow()

        # Audit log
        audit_log = AuditLog(
            actor_id=customer.id,
            actor_email=email,
            actor_role=customer.role,
            action=AuditAction.LOGIN.value,
            resource_type='customer',
            resource_id=str(customer.id),
            ip_address=request.remote_addr,
        )
        session.add(audit_log)
        session.commit()

        # Generate tokens
        access_token = create_access_token(identity=customer)
        refresh_token = create_refresh_token(identity=customer)

        result = {
            'status': 'success',
            'message': 'Login successful',
            'data': {
                'user': customer.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token,
            }
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': 'Login failed'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        identity = get_jwt_identity()
        session = get_session()
        customer = session.query(Customer).filter(Customer.id == identity).first()

        if not customer or not customer.is_active:
            session.close()
            return jsonify({'status': 'error', 'message': 'Invalid user'}), 401

        access_token = create_access_token(identity=customer)
        session.close()

        return jsonify({
            'status': 'success',
            'data': {'access_token': access_token}
        }), 200

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'status': 'error', 'message': 'Token refresh failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout customer"""
    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.id == identity).first()
            if customer:
                audit_log = AuditLog(
                    actor_id=customer.id,
                    actor_email=customer.email,
                    actor_role=customer.role,
                    action=AuditAction.LOGOUT.value,
                    resource_type='customer',
                    resource_id=str(customer.id),
                    ip_address=request.remote_addr,
                )
                session.add(audit_log)

        return jsonify({'status': 'success', 'message': 'Logout successful'}), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'status': 'error', 'message': 'Logout failed'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        if current_user:
            return jsonify({
                'status': 'success',
                'data': current_user.to_dict()
            }), 200
        return jsonify({'status': 'error', 'message': 'User not found'}), 404

    except Exception as e:
        logger.error(f"Get profile error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get profile'}), 500


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.id == identity).first()

            if not customer:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404

            # Update allowed fields
            if 'first_name' in data:
                customer.first_name = data['first_name'].strip()
            if 'last_name' in data:
                customer.last_name = data['last_name'].strip()
            if 'company' in data:
                customer.company = data['company'].strip()
            if 'phone' in data:
                customer.phone = data['phone'].strip()

            return jsonify({
                'status': 'success',
                'message': 'Profile updated',
                'data': customer.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Update profile error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update profile'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change password"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'status': 'error', 'message': 'Both passwords required'}), 400

    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': 'New password must be at least 8 characters'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.id == identity).first()

            if not customer:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404

            if not customer.check_password(current_password):
                return jsonify({'status': 'error', 'message': 'Current password is incorrect'}), 400

            customer.set_password(new_password)

            # Audit log
            audit_log = AuditLog(
                actor_id=customer.id,
                actor_email=customer.email,
                actor_role=customer.role,
                action=AuditAction.PASSWORD_CHANGE.value,
                resource_type='customer',
                resource_id=str(customer.id),
                ip_address=request.remote_addr,
            )
            session.add(audit_log)

        return jsonify({'status': 'success', 'message': 'Password changed successfully'}), 200

    except Exception as e:
        logger.error(f"Change password error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to change password'}), 500
