"""
Dashboard Statistics API (Admin)
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from shared.database import get_session
from shared.models import Customer, Tenant, Plan, Subscription, TenantState, SubscriptionStatus

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get overview statistics for admin dashboard"""
    try:
        session = get_session()

        # Time ranges
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)

        # Customer stats
        total_customers = session.query(func.count(Customer.id)).scalar()
        active_customers = session.query(func.count(Customer.id)).filter(
            Customer.is_active == True
        ).scalar()
        new_customers_24h = session.query(func.count(Customer.id)).filter(
            Customer.created_at >= last_24h
        ).scalar()
        new_customers_7d = session.query(func.count(Customer.id)).filter(
            Customer.created_at >= last_7d
        ).scalar()

        # Tenant stats
        total_tenants = session.query(func.count(Tenant.id)).scalar()
        active_tenants = session.query(func.count(Tenant.id)).filter(
            Tenant.state == TenantState.ACTIVE.value
        ).scalar()
        suspended_tenants = session.query(func.count(Tenant.id)).filter(
            Tenant.state == TenantState.SUSPENDED.value
        ).scalar()
        new_tenants_7d = session.query(func.count(Tenant.id)).filter(
            Tenant.created_at >= last_7d
        ).scalar()

        # Tenant by state
        tenants_by_state = {}
        for state in TenantState:
            count = session.query(func.count(Tenant.id)).filter(
                Tenant.state == state.value
            ).scalar()
            tenants_by_state[state.value] = count

        # Plan stats
        total_plans = session.query(func.count(Plan.id)).scalar()
        active_plans = session.query(func.count(Plan.id)).filter(
            Plan.is_active == True
        ).scalar()

        # Subscription stats
        total_subscriptions = session.query(func.count(Subscription.id)).scalar()
        active_subscriptions = session.query(func.count(Subscription.id)).filter(
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).scalar()
        trialing_subscriptions = session.query(func.count(Subscription.id)).filter(
            Subscription.status == SubscriptionStatus.TRIALING.value
        ).scalar()

        # Revenue estimate (MRR)
        mrr = session.query(func.sum(Subscription.amount)).filter(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.interval == 'month'
        ).scalar() or 0

        arr_monthly_portion = session.query(func.sum(Subscription.amount)).filter(
            Subscription.status == SubscriptionStatus.ACTIVE.value,
            Subscription.interval == 'year'
        ).scalar() or 0
        mrr += float(arr_monthly_portion) / 12

        # Storage stats
        total_db_size = session.query(func.sum(Tenant.db_size_bytes)).scalar() or 0
        total_filestore_size = session.query(func.sum(Tenant.filestore_size_bytes)).scalar() or 0
        total_storage_gb = (total_db_size + total_filestore_size) / (1024 ** 3)

        # Total users across tenants
        total_users = session.query(func.sum(Tenant.current_users)).scalar() or 0

        session.close()

        return jsonify({
            'status': 'success',
            'data': {
                'customers': {
                    'total': total_customers,
                    'active': active_customers,
                    'new_24h': new_customers_24h,
                    'new_7d': new_customers_7d,
                },
                'tenants': {
                    'total': total_tenants,
                    'active': active_tenants,
                    'suspended': suspended_tenants,
                    'new_7d': new_tenants_7d,
                    'by_state': tenants_by_state,
                },
                'plans': {
                    'total': total_plans,
                    'active': active_plans,
                },
                'subscriptions': {
                    'total': total_subscriptions,
                    'active': active_subscriptions,
                    'trialing': trialing_subscriptions,
                },
                'revenue': {
                    'mrr': round(float(mrr), 2),
                    'arr': round(float(mrr) * 12, 2),
                },
                'resources': {
                    'total_storage_gb': round(total_storage_gb, 2),
                    'total_users': total_users,
                },
                'generated_at': now.isoformat(),
            }
        }), 200

    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get stats'}), 500


@dashboard_bp.route('/recent-activity', methods=['GET'])
@jwt_required()
def get_recent_activity():
    """Get recent activity from audit logs"""
    try:
        from shared.models import AuditLog

        session = get_session()

        limit = min(request.args.get('limit', 20, type=int), 100)

        activities = session.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()

        result = {
            'status': 'success',
            'data': {
                'activities': [a.to_dict() for a in activities]
            }
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Recent activity error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get activity'}), 500


@dashboard_bp.route('/tenant-growth', methods=['GET'])
@jwt_required()
def get_tenant_growth():
    """Get tenant growth over time"""
    try:
        session = get_session()

        days = min(request.args.get('days', 30, type=int), 365)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get tenant counts by day
        results = session.query(
            func.date(Tenant.created_at).label('date'),
            func.count(Tenant.id).label('count')
        ).filter(
            Tenant.created_at >= start_date
        ).group_by(
            func.date(Tenant.created_at)
        ).order_by(
            func.date(Tenant.created_at)
        ).all()

        growth_data = [
            {'date': str(r.date), 'count': r.count}
            for r in results
        ]

        session.close()

        return jsonify({
            'status': 'success',
            'data': {
                'growth': growth_data,
                'period_days': days,
            }
        }), 200

    except Exception as e:
        logger.error(f"Tenant growth error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get growth data'}), 500
