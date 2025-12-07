"""
Admin API Blueprints
"""
from .auth import auth_bp
from .health import health_bp
from .tenants import tenants_bp
from .customers import customers_bp
from .plans import plans_bp
from .dashboard import dashboard_bp

__all__ = [
    'auth_bp',
    'health_bp',
    'tenants_bp',
    'customers_bp',
    'plans_bp',
    'dashboard_bp',
]
