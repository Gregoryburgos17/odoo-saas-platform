"""
Database Models for Odoo SaaS Platform
Complete SQLAlchemy models for multi-tenant SaaS management
"""
import uuid
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    Text, Numeric, ForeignKey, Index, CheckConstraint, Enum as SAEnum,
    JSON, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class TenantState(enum.Enum):
    """Tenant lifecycle states"""
    CREATING = "creating"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETING = "deleting"
    DELETED = "deleted"
    ERROR = "error"


class CustomerRole(enum.Enum):
    """Customer permission roles"""
    OWNER = "owner"      # Full access, billing management
    ADMIN = "admin"      # Tenant management
    VIEWER = "viewer"    # Read-only access


class AuditAction(enum.Enum):
    """Audit log action types"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    SUSPEND = "suspend"
    RESUME = "resume"
    BACKUP = "backup"
    RESTORE = "restore"
    MODULE_INSTALL = "module_install"
    MODULE_UNINSTALL = "module_uninstall"
    PASSWORD_CHANGE = "password_change"
    PLAN_CHANGE = "plan_change"


class SubscriptionStatus(enum.Enum):
    """Subscription status"""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class BackupStatus(enum.Enum):
    """Backup status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TicketStatus(enum.Enum):
    """Support ticket status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(enum.Enum):
    """Support ticket priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================================
# MODELS
# ============================================================================

class Customer(Base):
    """Customer/User account model"""
    __tablename__ = 'customers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(200))
    phone = Column(String(50))

    role = Column(String(20), default=CustomerRole.OWNER.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Resource limits
    max_tenants = Column(Integer, default=5)
    max_quota_gb = Column(Integer, default=50)

    # External billing IDs
    stripe_customer_id = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)

    # Relationships
    tenants = relationship("Tenant", back_populates="customer", lazy="dynamic")
    audit_logs = relationship("AuditLog", back_populates="actor", lazy="dynamic")
    subscriptions = relationship("Subscription", back_populates="customer", lazy="dynamic")
    support_tickets = relationship("SupportTicket", back_populates="customer", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and set password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password: str) -> bool:
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        """Get full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(p for p in parts if p) or self.email.split('@')[0]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'company': self.company,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'max_tenants': self.max_tenants,
            'max_quota_gb': self.max_quota_gb,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class Plan(Base):
    """Subscription plan model"""
    __tablename__ = 'plans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    # Pricing
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_yearly = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')

    # Limits
    max_tenants = Column(Integer, default=1)
    max_users_per_tenant = Column(Integer, default=5)
    max_db_size_gb = Column(Integer, default=1)
    max_filestore_gb = Column(Integer, default=1)

    # Features
    features = Column(JSONB, default=dict)
    allowed_modules = Column(JSON, default=list)

    # Stripe integration
    stripe_price_id_monthly = Column(String(100))
    stripe_price_id_yearly = Column(String(100))

    # Status
    is_active = Column(Boolean, default=True)
    trial_days = Column(Integer, default=14)
    sort_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    tenants = relationship("Tenant", back_populates="plan", lazy="dynamic")
    subscriptions = relationship("Subscription", back_populates="plan", lazy="dynamic")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'price_monthly': float(self.price_monthly) if self.price_monthly else 0,
            'price_yearly': float(self.price_yearly) if self.price_yearly else None,
            'currency': self.currency,
            'max_tenants': self.max_tenants,
            'max_users_per_tenant': self.max_users_per_tenant,
            'max_db_size_gb': self.max_db_size_gb,
            'max_filestore_gb': self.max_filestore_gb,
            'features': self.features or {},
            'allowed_modules': self.allowed_modules or [],
            'is_active': self.is_active,
            'trial_days': self.trial_days,
        }


class Tenant(Base):
    """Odoo tenant instance model"""
    __tablename__ = 'tenants'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)

    # Ownership
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('plans.id'))

    # State management
    state = Column(String(20), default=TenantState.CREATING.value, nullable=False, index=True)
    state_message = Column(Text)

    # Database configuration
    db_name = Column(String(100), unique=True)
    db_host = Column(String(255), default='postgres')
    db_port = Column(Integer, default=5432)

    # Storage
    filestore_path = Column(String(500))

    # Resource tracking
    current_users = Column(Integer, default=0)
    db_size_bytes = Column(BigInteger, default=0)
    filestore_size_bytes = Column(BigInteger, default=0)

    # Custom domain
    custom_domain = Column(String(255))

    # Odoo configuration
    odoo_version = Column(String(10), default='17.0')
    installed_modules = Column(JSON, default=list)
    odoo_config = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    suspended_at = Column(DateTime)
    last_backup_at = Column(DateTime)

    # Relationships
    customer = relationship("Customer", back_populates="tenants")
    plan = relationship("Plan", back_populates="tenants")
    backups = relationship("Backup", back_populates="tenant", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index('idx_tenant_customer_state', 'customer_id', 'state'),
        CheckConstraint('current_users >= 0', name='check_users_positive'),
        CheckConstraint('db_size_bytes >= 0', name='check_db_size_positive'),
    )

    @property
    def is_active(self) -> bool:
        """Check if tenant is active"""
        return self.state == TenantState.ACTIVE.value

    @property
    def full_domain(self) -> str:
        """Get full domain for tenant"""
        if self.custom_domain:
            return self.custom_domain
        return f"{self.slug}.localhost"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'slug': self.slug,
            'name': self.name,
            'customer_id': str(self.customer_id),
            'plan_id': str(self.plan_id) if self.plan_id else None,
            'state': self.state,
            'state_message': self.state_message,
            'db_name': self.db_name,
            'current_users': self.current_users,
            'db_size_bytes': self.db_size_bytes,
            'filestore_size_bytes': self.filestore_size_bytes,
            'custom_domain': self.custom_domain,
            'full_domain': self.full_domain,
            'odoo_version': self.odoo_version,
            'installed_modules': self.installed_modules or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
        }


class AuditLog(Base):
    """Immutable audit log for tracking all actions"""
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Actor information
    actor_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'))
    actor_email = Column(String(255))  # Denormalized for deleted users
    actor_role = Column(String(20))

    # Action details
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))

    # Request context
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))

    # Change tracking
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    extra_metadata = Column(JSONB)

    # Timestamp (immutable)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    actor = relationship("Customer", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index('idx_audit_actor_action', 'actor_id', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_created_at', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'actor_id': str(self.actor_id) if self.actor_id else None,
            'actor_email': self.actor_email,
            'actor_role': self.actor_role,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Subscription(Base):
    """Customer subscription model"""
    __tablename__ = 'subscriptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('plans.id'), nullable=False)

    # External ID
    stripe_subscription_id = Column(String(100))

    # Status
    status = Column(String(20), default=SubscriptionStatus.TRIALING.value, nullable=False)

    # Period
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    trial_end = Column(DateTime)

    # Billing
    amount = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')
    interval = Column(String(20), default='month')  # month or year

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    canceled_at = Column(DateTime)

    # Relationships
    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")

    # Indexes
    __table_args__ = (
        Index('idx_subscription_customer_status', 'customer_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'customer_id': str(self.customer_id),
            'plan_id': str(self.plan_id),
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'trial_end': self.trial_end.isoformat() if self.trial_end else None,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'interval': self.interval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Backup(Base):
    """Tenant backup model"""
    __tablename__ = 'backups'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)

    # Backup details
    backup_type = Column(String(20), default='full')  # full, incremental
    status = Column(String(20), default=BackupStatus.PENDING.value)

    # Storage
    file_path = Column(String(500))
    file_size_bytes = Column(BigInteger)
    checksum = Column(String(64))  # SHA-256

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="backups")

    # Indexes
    __table_args__ = (
        Index('idx_backup_tenant_status', 'tenant_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'tenant_id': str(self.tenant_id),
            'backup_type': self.backup_type,
            'status': self.status,
            'file_path': self.file_path,
            'file_size_bytes': self.file_size_bytes,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SupportTicket(Base):
    """Customer support ticket model"""
    __tablename__ = 'support_tickets'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey('customers.id'), nullable=False)

    # Ticket details
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), default='general')  # billing, technical, general

    # Priority and status
    priority = Column(String(20), default=TicketPriority.NORMAL.value)
    status = Column(String(20), default=TicketStatus.OPEN.value)

    # Assignment
    assigned_to = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime)

    # Relationships
    customer = relationship("Customer", back_populates="support_tickets")

    # Indexes
    __table_args__ = (
        Index('idx_ticket_customer_status', 'customer_id', 'status'),
        Index('idx_ticket_priority', 'priority', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'customer_id': str(self.customer_id),
            'subject': self.subject,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }
