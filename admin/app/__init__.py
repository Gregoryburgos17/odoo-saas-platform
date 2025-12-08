"""
Admin Dashboard Flask Application Factory
"""
import os
import logging
from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('FLASK_DEBUG', 'false').lower() == 'true' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Extensions
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])


def create_app(config_name: str = None) -> Flask:
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    configure_app(app, config_name)

    # Initialize extensions
    init_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # Register CLI commands
    register_cli_commands(app)

    logger.info(f"Admin Dashboard initialized in {config_name or 'default'} mode")

    return app


def configure_app(app: Flask, config_name: str = None):
    """Configure Flask application"""
    config_name = config_name or os.getenv('FLASK_ENV', 'development')

    # Base configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600'))
    )
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(
        seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '604800'))
    )
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'

    # Database configuration (for reference, actual connection in shared.database)
    app.config['PG_HOST'] = os.getenv('PG_HOST', 'postgres')
    app.config['PG_PORT'] = os.getenv('PG_PORT', '5432')
    app.config['PG_USER'] = os.getenv('PG_USER', 'odoo')
    app.config['PG_PASSWORD'] = os.getenv('PG_PASSWORD', 'odoo_password')
    app.config['PG_DATABASE'] = os.getenv('PG_DATABASE', 'odoo_saas')

    # Redis configuration
    app.config['REDIS_HOST'] = os.getenv('REDIS_HOST', 'redis')
    app.config['REDIS_PORT'] = int(os.getenv('REDIS_PORT', '6379'))
    app.config['REDIS_PASSWORD'] = os.getenv('REDIS_PASSWORD', '')

    # CORS configuration
    app.config['CORS_ORIGINS'] = os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:3000,http://localhost:5000,http://localhost:5001'
    ).split(',')

    # Environment specific
    if config_name == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    elif config_name == 'testing':
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
    else:  # development
        app.config['DEBUG'] = True
        app.config['TESTING'] = False


def init_extensions(app: Flask):
    """Initialize Flask extensions"""
    # CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # JWT
    jwt.init_app(app)

    # Rate limiter
    limiter.init_app(app)

    # JWT callbacks
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return str(user.id) if hasattr(user, 'id') else str(user)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from shared.database import get_session
        from shared.models import Customer

        identity = jwt_data["sub"]
        session = get_session()
        try:
            user = session.query(Customer).filter(Customer.id == identity).first()
            return user
        finally:
            session.close()

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'status': 'error',
            'message': 'Token has expired',
            'error': 'token_expired'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'status': 'error',
            'message': 'Invalid token',
            'error': 'invalid_token'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'status': 'error',
            'message': 'Authorization token required',
            'error': 'authorization_required'
        }), 401


def register_blueprints(app: Flask):
    """Register all blueprints"""
    from .api import auth_bp, health_bp, tenants_bp, customers_bp, plans_bp, dashboard_bp
    from .web import web_bp

    # API blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(tenants_bp, url_prefix='/api/tenants')
    app.register_blueprint(customers_bp, url_prefix='/api/customers')
    app.register_blueprint(plans_bp, url_prefix='/api/plans')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

    # Web UI blueprint
    app.register_blueprint(web_bp)


def register_error_handlers(app: Flask):
    """Register global error handlers"""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 'error',
            'message': 'Bad request',
            'error': str(error)
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized',
            'error': str(error)
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'status': 'error',
            'message': 'Forbidden',
            'error': str(error)
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'message': 'Resource not found',
            'error': str(error)
        }), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'status': 'error',
            'message': 'Rate limit exceeded',
            'error': 'too_many_requests'
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': 'internal_error'
        }), 500


def register_cli_commands(app: Flask):
    """Register CLI commands"""
    import click

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database."""
        from shared.database import init_db
        init_db()
        click.echo('Database initialized.')

    @app.cli.command('create-admin')
    @click.option('--email', prompt=True, help='Admin email address')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option('--first-name', default='Admin')
    @click.option('--last-name', default='User')
    def create_admin_command(email, password, first_name, last_name):
        """Create an admin user."""
        from shared.database import session_scope
        from shared.models import Customer, CustomerRole

        with session_scope() as session:
            existing = session.query(Customer).filter(Customer.email == email).first()
            if existing:
                click.echo(f'User {email} already exists.')
                return

            admin = Customer(
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=CustomerRole.OWNER.value,
                is_active=True,
                is_verified=True,
            )
            admin.set_password(password)
            session.add(admin)

        click.echo(f'Admin user {email} created successfully.')

    @app.cli.command('seed-data')
    def seed_data_command():
        """Seed database with demo data."""
        from scripts.seed_data import seed_all
        seed_all()
        click.echo('Demo data seeded successfully.')
