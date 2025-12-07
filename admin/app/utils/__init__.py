"""
Admin Utilities
"""
from .auth import require_role, get_current_user_id

__all__ = ['require_role', 'get_current_user_id']
