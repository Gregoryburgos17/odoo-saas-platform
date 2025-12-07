# Shared module for Odoo SaaS Platform
from .models import (
    Base,
    Customer,
    Plan,
    Tenant,
    AuditLog,
    Subscription,
    Backup,
    SupportTicket,
    TenantState,
    CustomerRole,
    AuditAction,
)
from .database import (
    get_engine,
    get_session,
    init_db,
    DatabaseManager,
)

__all__ = [
    'Base',
    'Customer',
    'Plan',
    'Tenant',
    'AuditLog',
    'Subscription',
    'Backup',
    'SupportTicket',
    'TenantState',
    'CustomerRole',
    'AuditAction',
    'get_engine',
    'get_session',
    'init_db',
    'DatabaseManager',
]
