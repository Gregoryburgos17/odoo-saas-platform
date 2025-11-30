#!/usr/bin/env python3
"""
Customer Portal Web UI
Serves the customer portal frontend interface
"""

from flask import Blueprint, render_template, redirect, url_for, jsonify

# Create blueprint
web_bp = Blueprint('web', __name__, template_folder='../templates', static_folder='../static')

@web_bp.route('/')
def index():
    """Customer portal home page"""
    # For now, return a simple JSON response
    # TODO: Implement proper React/Vue frontend
    return jsonify({
        'message': 'Customer Portal',
        'description': 'Web UI will be implemented here',
        'api_endpoints': {
            'auth': '/api/auth',
            'tenants': '/api/tenants',
            'billing': '/api/billing',
            'support': '/api/support',
            'webhooks': '/webhooks',
            'health': '/health'
        }
    })

@web_bp.route('/login')
def login_page():
    """Login page"""
    return jsonify({
        'message': 'Login Page',
        'description': 'Use POST /api/auth/login to authenticate'
    })

@web_bp.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    return jsonify({
        'message': 'Dashboard Page',
        'description': 'Customer portal dashboard interface'
    })

@web_bp.route('/tenants')
def tenants():
    """Tenant instances page"""
    return jsonify({
        'message': 'My Tenants',
        'description': 'View and manage your tenant instances'
    })

@web_bp.route('/billing')
def billing():
    """Billing page"""
    return jsonify({
        'message': 'Billing & Subscriptions',
        'description': 'Manage billing and subscriptions'
    })

@web_bp.route('/support')
def support():
    """Support page"""
    return jsonify({
        'message': 'Support',
        'description': 'Submit and view support tickets'
    })
