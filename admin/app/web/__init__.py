"""
Admin Web Routes - Serves HTML Templates
"""
from flask import Blueprint, render_template

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """Dashboard page"""
    return render_template('dashboard.html')


@web_bp.route('/login')
def login():
    """Login page"""
    return render_template('login.html')


@web_bp.route('/tenants')
def tenants():
    """Tenants list page"""
    return render_template('tenants.html')


@web_bp.route('/customers')
def customers():
    """Customers list page"""
    return render_template('customers.html')


@web_bp.route('/plans')
def plans():
    """Plans list page"""
    return render_template('plans.html')


@web_bp.route('/audit')
def audit():
    """Audit logs page"""
    return render_template('audit.html')


@web_bp.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')
