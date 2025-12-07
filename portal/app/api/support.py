"""
Support Tickets API for Customer Portal
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from shared.database import session_scope, get_session
from shared.models import SupportTicket, Customer, TicketStatus, TicketPriority

logger = logging.getLogger(__name__)

support_bp = Blueprint('support', __name__)


@support_bp.route('/tickets', methods=['GET'])
@jwt_required()
def list_tickets():
    """List customer's support tickets"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        # Query parameters
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        query = session.query(SupportTicket).filter(
            SupportTicket.customer_id == identity
        )

        if status:
            query = query.filter(SupportTicket.status == status)

        total = query.count()
        tickets = query.order_by(SupportTicket.created_at.desc()) \
            .offset((page - 1) * per_page) \
            .limit(per_page) \
            .all()

        result = {
            'status': 'success',
            'data': {
                'tickets': [t.to_dict() for t in tickets],
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
        logger.error(f"List tickets error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to list tickets'}), 500


@support_bp.route('/tickets/<ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    """Get ticket details"""
    try:
        identity = get_jwt_identity()
        session = get_session()

        ticket = session.query(SupportTicket).filter(
            SupportTicket.id == ticket_id,
            SupportTicket.customer_id == identity
        ).first()

        if not ticket:
            session.close()
            return jsonify({'status': 'error', 'message': 'Ticket not found'}), 404

        result = {
            'status': 'success',
            'data': ticket.to_dict()
        }

        session.close()
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Get ticket error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get ticket'}), 500


@support_bp.route('/tickets', methods=['POST'])
@jwt_required()
def create_ticket():
    """Create a support ticket"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    subject = data.get('subject', '').strip()
    description = data.get('description', '').strip()
    category = data.get('category', 'general')
    priority = data.get('priority', TicketPriority.NORMAL.value)

    # Validation
    if not subject:
        return jsonify({'status': 'error', 'message': 'Subject is required'}), 400

    if not description:
        return jsonify({'status': 'error', 'message': 'Description is required'}), 400

    if len(subject) > 200:
        return jsonify({'status': 'error', 'message': 'Subject too long (max 200 chars)'}), 400

    valid_categories = ['billing', 'technical', 'general']
    if category not in valid_categories:
        category = 'general'

    valid_priorities = [p.value for p in TicketPriority]
    if priority not in valid_priorities:
        priority = TicketPriority.NORMAL.value

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            ticket = SupportTicket(
                customer_id=identity,
                subject=subject,
                description=description,
                category=category,
                priority=priority,
                status=TicketStatus.OPEN.value,
            )
            session.add(ticket)
            session.flush()

            return jsonify({
                'status': 'success',
                'message': 'Ticket created successfully',
                'data': ticket.to_dict()
            }), 201

    except Exception as e:
        logger.error(f"Create ticket error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create ticket'}), 500


@support_bp.route('/tickets/<ticket_id>', methods=['PUT'])
@jwt_required()
def update_ticket(ticket_id):
    """Update ticket (add info)"""
    data = request.get_json()

    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            ticket = session.query(SupportTicket).filter(
                SupportTicket.id == ticket_id,
                SupportTicket.customer_id == identity
            ).first()

            if not ticket:
                return jsonify({'status': 'error', 'message': 'Ticket not found'}), 404

            if ticket.status == TicketStatus.CLOSED.value:
                return jsonify({'status': 'error', 'message': 'Cannot update closed ticket'}), 400

            # Update allowed fields
            if 'description' in data:
                # Append to description
                new_info = data['description'].strip()
                if new_info:
                    ticket.description += f"\n\n--- Update ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')}) ---\n{new_info}"

            if 'priority' in data and data['priority'] in [p.value for p in TicketPriority]:
                ticket.priority = data['priority']

            return jsonify({
                'status': 'success',
                'message': 'Ticket updated',
                'data': ticket.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Update ticket error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update ticket'}), 500


@support_bp.route('/tickets/<ticket_id>/close', methods=['POST'])
@jwt_required()
def close_ticket(ticket_id):
    """Close a ticket"""
    try:
        identity = get_jwt_identity()

        with session_scope() as session:
            ticket = session.query(SupportTicket).filter(
                SupportTicket.id == ticket_id,
                SupportTicket.customer_id == identity
            ).first()

            if not ticket:
                return jsonify({'status': 'error', 'message': 'Ticket not found'}), 404

            if ticket.status == TicketStatus.CLOSED.value:
                return jsonify({'status': 'error', 'message': 'Ticket already closed'}), 400

            ticket.status = TicketStatus.CLOSED.value
            ticket.resolved_at = datetime.utcnow()

            return jsonify({
                'status': 'success',
                'message': 'Ticket closed',
                'data': ticket.to_dict()
            }), 200

    except Exception as e:
        logger.error(f"Close ticket error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to close ticket'}), 500


@support_bp.route('/faq', methods=['GET'])
def get_faq():
    """Get FAQ articles (public endpoint)"""
    faq_items = [
        {
            'id': 1,
            'category': 'general',
            'question': 'How do I create a new tenant?',
            'answer': 'Go to your dashboard, click "Create Tenant", enter a unique slug and name, then click Create. Your tenant will be provisioned automatically.'
        },
        {
            'id': 2,
            'category': 'billing',
            'question': 'How does the free trial work?',
            'answer': 'All plans include a 14-day free trial. You can use all features during the trial period. No credit card required to start.'
        },
        {
            'id': 3,
            'category': 'technical',
            'question': 'How do I access my Odoo instance?',
            'answer': 'After your tenant is created, you can access it at your-slug.yourdomain.com. Use the credentials sent to your email.'
        },
        {
            'id': 4,
            'category': 'billing',
            'question': 'Can I upgrade or downgrade my plan?',
            'answer': 'Yes, you can change your plan at any time from the Billing section. Changes take effect immediately.'
        },
        {
            'id': 5,
            'category': 'technical',
            'question': 'How do backups work?',
            'answer': 'Automatic backups run daily. You can also create manual backups from your tenant dashboard. Backups are retained for 30 days.'
        },
        {
            'id': 6,
            'category': 'general',
            'question': 'How do I contact support?',
            'answer': 'Create a support ticket from your dashboard, or email support@example.com. Response times vary by plan.'
        },
    ]

    category = request.args.get('category')
    if category:
        faq_items = [f for f in faq_items if f['category'] == category]

    return jsonify({
        'status': 'success',
        'data': {
            'items': faq_items
        }
    }), 200
