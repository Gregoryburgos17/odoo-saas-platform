#!/usr/bin/env python3
"""
Seed Database with Demo Data
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import session_scope, init_db
from shared.models import Customer, Plan, Tenant, CustomerRole, TenantState


def seed_plans():
    """Create default subscription plans"""
    plans = [
        {
            'name': 'Starter',
            'slug': 'starter',
            'description': 'Perfect for small businesses and startups',
            'price_monthly': 29.00,
            'price_yearly': 290.00,
            'currency': 'USD',
            'max_tenants': 1,
            'max_users_per_tenant': 5,
            'max_db_size_gb': 1,
            'max_filestore_gb': 5,
            'features': {
                'support': 'email',
                'backups': 'daily',
                'ssl': True,
                'api_access': False,
            },
            'allowed_modules': ['sale', 'purchase', 'inventory', 'crm', 'contacts'],
            'trial_days': 14,
            'sort_order': 1,
        },
        {
            'name': 'Professional',
            'slug': 'professional',
            'description': 'For growing businesses that need more power',
            'price_monthly': 79.00,
            'price_yearly': 790.00,
            'currency': 'USD',
            'max_tenants': 3,
            'max_users_per_tenant': 25,
            'max_db_size_gb': 10,
            'max_filestore_gb': 50,
            'features': {
                'support': 'priority',
                'backups': 'hourly',
                'ssl': True,
                'custom_domain': True,
                'api_access': True,
            },
            'allowed_modules': [
                'sale', 'purchase', 'inventory', 'crm', 'contacts',
                'project', 'hr', 'accounting', 'website', 'ecommerce'
            ],
            'trial_days': 14,
            'sort_order': 2,
        },
        {
            'name': 'Enterprise',
            'slug': 'enterprise',
            'description': 'For large organizations with advanced needs',
            'price_monthly': 199.00,
            'price_yearly': 1990.00,
            'currency': 'USD',
            'max_tenants': 10,
            'max_users_per_tenant': 100,
            'max_db_size_gb': 50,
            'max_filestore_gb': 200,
            'features': {
                'support': '24/7',
                'backups': 'continuous',
                'ssl': True,
                'custom_domain': True,
                'api_access': True,
                'sla': '99.9%',
                'dedicated_support': True,
                'custom_development': True,
            },
            'allowed_modules': ['*'],
            'trial_days': 30,
            'sort_order': 3,
        },
    ]

    with session_scope() as session:
        for plan_data in plans:
            existing = session.query(Plan).filter(Plan.slug == plan_data['slug']).first()
            if not existing:
                plan = Plan(**plan_data)
                session.add(plan)
                print(f"Created plan: {plan_data['name']}")
            else:
                print(f"Plan already exists: {plan_data['name']}")


def seed_admin_user():
    """Create default admin user"""
    with session_scope() as session:
        email = 'admin@example.com'
        existing = session.query(Customer).filter(Customer.email == email).first()

        if not existing:
            admin = Customer(
                email=email,
                first_name='Admin',
                last_name='User',
                company='Odoo SaaS Platform',
                role=CustomerRole.OWNER.value,
                is_active=True,
                is_verified=True,
                max_tenants=100,
                max_quota_gb=1000,
            )
            admin.set_password('admin123')
            session.add(admin)
            print(f"Created admin user: {email} (password: admin123)")
        else:
            print(f"Admin user already exists: {email}")


def seed_demo_customer():
    """Create demo customer with tenant"""
    with session_scope() as session:
        email = 'demo@example.com'
        existing = session.query(Customer).filter(Customer.email == email).first()

        if not existing:
            # Create customer
            customer = Customer(
                email=email,
                first_name='Demo',
                last_name='Customer',
                company='Demo Company Inc.',
                role=CustomerRole.OWNER.value,
                is_active=True,
                is_verified=True,
                max_tenants=5,
                max_quota_gb=50,
            )
            customer.set_password('demo123')
            session.add(customer)
            session.flush()

            # Get starter plan
            plan = session.query(Plan).filter(Plan.slug == 'starter').first()

            # Create demo tenant
            tenant = Tenant(
                slug='demo-company',
                name='Demo Company',
                customer_id=customer.id,
                plan_id=plan.id if plan else None,
                state=TenantState.ACTIVE.value,
                db_name='odoo_demo_company',
                current_users=3,
            )
            session.add(tenant)

            print(f"Created demo customer: {email} (password: demo123)")
            print(f"Created demo tenant: demo-company")
        else:
            print(f"Demo customer already exists: {email}")


def seed_all():
    """Seed all demo data"""
    print("=" * 50)
    print("Seeding Database with Demo Data")
    print("=" * 50)

    # Initialize database tables
    print("\nInitializing database tables...")
    init_db()

    # Seed data
    print("\nSeeding plans...")
    seed_plans()

    print("\nSeeding admin user...")
    seed_admin_user()

    print("\nSeeding demo customer...")
    seed_demo_customer()

    print("\n" + "=" * 50)
    print("Database seeding completed!")
    print("=" * 50)
    print("\nDefault credentials:")
    print("  Admin: admin@example.com / admin123")
    print("  Demo:  demo@example.com / demo123")


if __name__ == '__main__':
    seed_all()
