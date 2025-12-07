"""
Authentication Utilities
"""
import functools
import logging
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, current_user

from shared.models import CustomerRole

logger = logging.getLogger(__name__)


def get_current_user_id():
    """Get current user ID from JWT"""
    try:
        verify_jwt_in_request()
        return get_jwt_identity()
    except Exception:
        return None


def require_role(*roles):
    """
    Decorator to require specific roles for an endpoint.

    Usage:
        @require_role(CustomerRole.OWNER, CustomerRole.ADMIN)
        def admin_only_endpoint():
            pass
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            if current_user is None:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found'
                }), 401

            # Convert roles to values if they are enum members
            allowed_roles = [r.value if hasattr(r, 'value') else r for r in roles]

            if current_user.role not in allowed_roles:
                logger.warning(
                    f"Access denied for user {current_user.email} "
                    f"(role: {current_user.role}) to endpoint requiring {allowed_roles}"
                )
                return jsonify({
                    'status': 'error',
                    'message': 'Insufficient permissions'
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_owner(fn):
    """Decorator to require owner role"""
    return require_role(CustomerRole.OWNER)(fn)


def require_admin(fn):
    """Decorator to require admin or owner role"""
    return require_role(CustomerRole.OWNER, CustomerRole.ADMIN)(fn)
