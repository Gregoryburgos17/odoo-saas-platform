"""
Billing API for Customer Portal
"""
import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from shared.database import session_scope, get_session
from shared.models import Plan, Subscription, Customer, AuditLog, AuditAction, SubscriptionStatus

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/plans', methods=['GET'])
def list_plans():
    """List available plans (public endpoint)"""
    try:
        session = get_session()

        plans = session.query(Plan).filter(
            Plan.is_active == True
        ).order_by(Plan.sort_order, Plan.price_monthly).all()

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


@billing_bp.route('/plans/<plan_id>', methods=['GET'])
def get_plan(plan_id):
    """Get plan details (public endpoint)"""
    try:
        session = get_session()

        plan = session.query(Plan).filter(
            Plan.id == plan_id,
            Plan.is_active == True
        ).first()

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


@billing_bp.route('/subscription', methods=['GET'])
@jwt_required()
def get_subscription():
    """Get current subscription"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        subscription = session.query(Subscription).filter(
            Subscription.customer_id == identity,
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE.value,
                SubscriptionStatus.TRIALING.value,
                SubscriptionStatus.PAST_DUE.value
            ])
        ).first()

        if not subscription:
            session.close()
            return jsonify({
                'status': 'success',
                'data': None,
                'message': 'No active subscription'
            }), 200

        result = subscription.to_dict()

        # Add plan details
        if subscription.plan:
            result['plan'] = subscription.plan.to_dict()

        session.close()
        return jsonify({'status': 'success', 'data': result}), 200

    except Exception as e:
        logger.error(f"Get subscription error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get subscription'}), 500


@billing_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    """Subscribe to a plan"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    plan_id = data.get('plan_id')
    interval = data.get('interval', 'month')  # month or year

    if not plan_id:
        return jsonify({'status': 'error', 'message': 'Plan ID is required'}), 400

    if interval not in ['month', 'year']:
        return jsonify({'status': 'error', 'message': 'Invalid interval'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            # Check for existing active subscription
            existing = session.query(Subscription).filter(
                Subscription.customer_id == identity,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.TRIALING.value
                ])
            ).first()

            if existing:
                return jsonify({
                    'status': 'error',
                    'message': 'You already have an active subscription. Use upgrade instead.'
                }), 400

            # Get plan
            plan = session.query(Plan).filter(
                Plan.id == plan_id,
                Plan.is_active == True
            ).first()

            if not plan:
                return jsonify({'status': 'error', 'message': 'Plan not found'}), 404

            # Calculate pricing
            amount = plan.price_monthly if interval == 'month' else (plan.price_yearly or plan.price_monthly * 12)

            # Create subscription with trial
            now = datetime.utcnow()
            trial_end = now + timedelta(days=plan.trial_days) if plan.trial_days > 0 else None

            subscription = Subscription(
                customer_id=identity,
                plan_id=plan_id,
                status=SubscriptionStatus.TRIALING.value if trial_end else SubscriptionStatus.ACTIVE.value,
                current_period_start=now,
                current_period_end=now + timedelta(days=30 if interval == 'month' else 365),
                trial_end=trial_end,
                amount=amount,
                currency=plan.currency,
                interval=interval,
            )
            session.add(subscription)
            session.flush()

            # Update customer limits based on plan
            customer = session.query(Customer).filter(Customer.id == identity).first()
            if customer:
                customer.max_tenants = plan.max_tenants

            # Audit log
            audit_log = AuditLog(
                actor_id=identity,
                actor_email=customer.email if customer else 'unknown',
                action=AuditAction.CREATE.value,
                resource_type='subscription',
                resource_id=str(subscription.id),
                ip_address=request.remote_addr,
                new_values={
                    'plan_id': str(plan_id),
                    'interval': interval,
                    'amount': float(amount),
                    'status': subscription.status
                }
            )
            session.add(audit_log)

            result = subscription.to_dict()
            result['plan'] = plan.to_dict()

            return jsonify({
                'status': 'success',
                'message': 'Subscription created successfully',
                'data': result
            }), 201

    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create subscription'}), 500


@billing_bp.route('/subscription', methods=['PUT'])
@jwt_required()
def update_subscription():
    """Update subscription (change plan)"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    new_plan_id = data.get('plan_id')

    if not new_plan_id:
        return jsonify({'status': 'error', 'message': 'New plan ID is required'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            subscription = session.query(Subscription).filter(
                Subscription.customer_id == identity,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.TRIALING.value
                ])
            ).first()

            if not subscription:
                return jsonify({'status': 'error', 'message': 'No active subscription'}), 404

            # Get new plan
            new_plan = session.query(Plan).filter(
                Plan.id == new_plan_id,
                Plan.is_active == True
            ).first()

            if not new_plan:
                return jsonify({'status': 'error', 'message': 'Plan not found'}), 404

            old_plan_id = subscription.plan_id

            # Update subscription
            subscription.plan_id = new_plan_id
            subscription.amount = new_plan.price_monthly if subscription.interval == 'month' else (new_plan.price_yearly or new_plan.price_monthly * 12)

            # Update customer limits
            customer = session.query(Customer).filter(Customer.id == identity).first()
            if customer:
                customer.max_tenants = new_plan.max_tenants

            # Audit log
            audit_log = AuditLog(
                actor_id=identity,
                actor_email=customer.email if customer else 'unknown',
                action=AuditAction.PLAN_CHANGE.value,
                resource_type='subscription',
                resource_id=str(subscription.id),
                ip_address=request.remote_addr,
                old_values={'plan_id': str(old_plan_id)},
                new_values={'plan_id': str(new_plan_id)}
            )
            session.add(audit_log)

            result = subscription.to_dict()
            result['plan'] = new_plan.to_dict()

            return jsonify({
                'status': 'success',
                'message': 'Subscription updated',
                'data': result
            }), 200

    except Exception as e:
        logger.error(f"Update subscription error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update subscription'}), 500


@billing_bp.route('/subscription', methods=['DELETE'])
@jwt_required()
def cancel_subscription():
    """Cancel subscription"""
    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            subscription = session.query(Subscription).filter(
                Subscription.customer_id == identity,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.TRIALING.value,
                    SubscriptionStatus.PAST_DUE.value
                ])
            ).first()

            if not subscription:
                return jsonify({'status': 'error', 'message': 'No active subscription'}), 404

            subscription.status = SubscriptionStatus.CANCELED.value
            subscription.canceled_at = datetime.utcnow()

            # Audit log
            customer = session.query(Customer).filter(Customer.id == identity).first()
            audit_log = AuditLog(
                actor_id=identity,
                actor_email=customer.email if customer else 'unknown',
                action=AuditAction.DELETE.value,
                resource_type='subscription',
                resource_id=str(subscription.id),
                ip_address=request.remote_addr,
            )
            session.add(audit_log)

            return jsonify({
                'status': 'success',
                'message': 'Subscription cancelled. Access continues until end of billing period.'
            }), 200

    except Exception as e:
        logger.error(f"Cancel subscription error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to cancel subscription'}), 500


@billing_bp.route('/usage', methods=['GET'])
@jwt_required()
def get_usage():
    """Get current usage metrics"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        from shared.models import Tenant, TenantState
        from sqlalchemy import func

        # Get total usage across all tenants
        tenants = session.query(Tenant).filter(
            Tenant.customer_id == identity,
            Tenant.state != TenantState.DELETED.value
        ).all()

        total_db_size = sum(t.db_size_bytes or 0 for t in tenants)
        total_filestore_size = sum(t.filestore_size_bytes or 0 for t in tenants)
        total_users = sum(t.current_users or 0 for t in tenants)
        tenant_count = len(tenants)

        # Get customer limits
        customer = session.query(Customer).filter(Customer.id == identity).first()

        result = {
            'status': 'success',
            'data': {
                'tenants': {
                    'used': tenant_count,
                    'limit': customer.max_tenants if customer else 0,
                },
                'storage': {
                    'database_bytes': total_db_size,
                    'filestore_bytes': total_filestore_size,
                    'total_bytes': total_db_size + total_filestore_size,
                    'limit_gb': customer.max_quota_gb if customer else 0,
                },
                'users': {
                    'total': total_users,
                },
            }
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Get usage error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get usage'}), 500
