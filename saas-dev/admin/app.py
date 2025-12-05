"""
===========================================
Admin Dashboard - Flask Application
Odoo SaaS Platform Management
===========================================
"""

import os
import re
import json
import logging
import xmlrpc.client
from datetime import datetime
from functools import wraps

import psycopg2
import redis
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# ===========================================
# Configuration
# ===========================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_me')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
class Config:
    # PostgreSQL
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'db')
    POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'odoo')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'odoo_secret_2024')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'postgres')

    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

    # Odoo
    ODOO_HOST = os.environ.get('ODOO_HOST', 'odoo')
    ODOO_PORT = int(os.environ.get('ODOO_PORT', 8069))
    ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'admin_master_2024')

    # Default Tenant Settings
    DEFAULT_ADMIN_LOGIN = os.environ.get('DEFAULT_ODOO_ADMIN_LOGIN', 'admin')
    DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ODOO_ADMIN_PASSWORD', 'admin')
    DEFAULT_COUNTRY = os.environ.get('DEFAULT_COUNTRY_CODE', 'US')
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'en_US')

config = Config()

# ===========================================
# Database Helper Functions
# ===========================================

def get_postgres_connection(database='saas_metadata'):
    """Create a connection to PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            database=database
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"PostgreSQL connection error: {e}")
        return None

def get_redis_client():
    """Create a Redis client connection."""
    try:
        client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            decode_responses=True
        )
        client.ping()
        return client
    except redis.RedisError as e:
        logger.error(f"Redis connection error: {e}")
        return None

# ===========================================
# Odoo API Helper Functions
# ===========================================

def get_odoo_url():
    """Get the Odoo base URL."""
    return f"http://{config.ODOO_HOST}:{config.ODOO_PORT}"

def check_odoo_health():
    """Check if Odoo is responding."""
    try:
        response = requests.get(
            f"{get_odoo_url()}/web/health",
            timeout=10
        )
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Odoo health check failed: {e}")
        return False

def list_odoo_databases():
    """List all databases in Odoo using XML-RPC."""
    try:
        url = f"{get_odoo_url()}/xmlrpc/2/db"
        db_proxy = xmlrpc.client.ServerProxy(url)
        databases = db_proxy.list()
        return databases
    except Exception as e:
        logger.error(f"Failed to list Odoo databases: {e}")
        return []

def create_odoo_database(db_name, admin_password='admin', demo_data=False, language='en_US', country_code='US'):
    """
    Create a new Odoo database using XML-RPC.

    Args:
        db_name: Name of the database to create
        admin_password: Password for the admin user
        demo_data: Whether to load demo data
        language: Language code (e.g., 'en_US')
        country_code: Country code (e.g., 'US')

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        url = f"{get_odoo_url()}/xmlrpc/2/db"
        db_proxy = xmlrpc.client.ServerProxy(url)

        # Check if database already exists
        existing_dbs = db_proxy.list()
        if db_name in existing_dbs:
            return False, f"Database '{db_name}' already exists"

        logger.info(f"Creating Odoo database: {db_name}")

        # Create the database
        # Parameters: master_password, db_name, demo, lang, admin_password, admin_login, country_code
        result = db_proxy.create_database(
            config.ODOO_MASTER_PASSWORD,  # Master password
            db_name,                       # Database name
            demo_data,                     # Demo data
            language,                      # Language
            admin_password,                # Admin password
            'admin',                       # Admin login
            country_code                   # Country code
        )

        if result:
            logger.info(f"Successfully created database: {db_name}")
            return True, f"Database '{db_name}' created successfully"
        else:
            return False, "Database creation returned False"

    except xmlrpc.client.Fault as e:
        logger.error(f"XML-RPC Fault creating database: {e}")
        return False, f"XML-RPC error: {e.faultString}"
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False, f"Error: {str(e)}"

def delete_odoo_database(db_name):
    """
    Delete an Odoo database using XML-RPC.

    Args:
        db_name: Name of the database to delete

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        url = f"{get_odoo_url()}/xmlrpc/2/db"
        db_proxy = xmlrpc.client.ServerProxy(url)

        # Check if database exists
        existing_dbs = db_proxy.list()
        if db_name not in existing_dbs:
            return False, f"Database '{db_name}' does not exist"

        logger.info(f"Deleting Odoo database: {db_name}")

        # Drop the database
        result = db_proxy.drop(config.ODOO_MASTER_PASSWORD, db_name)

        if result:
            logger.info(f"Successfully deleted database: {db_name}")
            return True, f"Database '{db_name}' deleted successfully"
        else:
            return False, "Database deletion returned False"

    except xmlrpc.client.Fault as e:
        logger.error(f"XML-RPC Fault deleting database: {e}")
        return False, f"XML-RPC error: {e.faultString}"
    except Exception as e:
        logger.error(f"Error deleting database: {e}")
        return False, f"Error: {str(e)}"

def duplicate_odoo_database(source_db, new_db_name):
    """
    Duplicate an existing Odoo database.

    Args:
        source_db: Name of the source database
        new_db_name: Name for the new database

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        url = f"{get_odoo_url()}/xmlrpc/2/db"
        db_proxy = xmlrpc.client.ServerProxy(url)

        existing_dbs = db_proxy.list()
        if source_db not in existing_dbs:
            return False, f"Source database '{source_db}' does not exist"
        if new_db_name in existing_dbs:
            return False, f"Database '{new_db_name}' already exists"

        logger.info(f"Duplicating database {source_db} to {new_db_name}")

        result = db_proxy.duplicate_database(
            config.ODOO_MASTER_PASSWORD,
            source_db,
            new_db_name
        )

        if result:
            return True, f"Database '{source_db}' duplicated to '{new_db_name}'"
        else:
            return False, "Database duplication returned False"

    except Exception as e:
        logger.error(f"Error duplicating database: {e}")
        return False, f"Error: {str(e)}"

# ===========================================
# Tenant Management Functions
# ===========================================

def save_tenant_to_metadata(name, database_name, subdomain, admin_email=''):
    """Save tenant information to the metadata database."""
    conn = get_postgres_connection('saas_metadata')
    if not conn:
        return False, "Could not connect to metadata database"

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tenants (name, database_name, subdomain, admin_email, status)
            VALUES (%s, %s, %s, %s, 'active')
            ON CONFLICT (database_name) DO UPDATE SET
                name = EXCLUDED.name,
                subdomain = EXCLUDED.subdomain,
                admin_email = EXCLUDED.admin_email,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (name, database_name, subdomain, admin_email))

        tenant_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return True, tenant_id
    except psycopg2.Error as e:
        logger.error(f"Error saving tenant to metadata: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False, str(e)

def get_all_tenants():
    """Get all tenants from the metadata database."""
    conn = get_postgres_connection('saas_metadata')
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, database_name, subdomain, admin_email, status, created_at
            FROM tenants
            ORDER BY created_at DESC
        """)

        tenants = []
        for row in cursor.fetchall():
            tenants.append({
                'id': row[0],
                'name': row[1],
                'database_name': row[2],
                'subdomain': row[3],
                'admin_email': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None
            })

        cursor.close()
        conn.close()
        return tenants
    except psycopg2.Error as e:
        logger.error(f"Error fetching tenants: {e}")
        return []

def delete_tenant_from_metadata(database_name):
    """Delete a tenant from the metadata database."""
    conn = get_postgres_connection('saas_metadata')
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tenants WHERE database_name = %s", (database_name,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        logger.error(f"Error deleting tenant from metadata: {e}")
        return False

def validate_database_name(name):
    """Validate database name format."""
    # Only allow lowercase letters, numbers, and underscores
    pattern = r'^[a-z][a-z0-9_]{2,62}$'
    if not re.match(pattern, name):
        return False, "Database name must start with a letter, contain only lowercase letters, numbers, and underscores, and be 3-63 characters long"

    # Reserved names
    reserved = ['postgres', 'template0', 'template1', 'saas_metadata', 'odoo', 'admin']
    if name in reserved:
        return False, f"'{name}' is a reserved database name"

    return True, "Valid"

# ===========================================
# Flask Routes
# ===========================================

@app.route('/')
def index():
    """Main dashboard page."""
    # Get statistics
    odoo_healthy = check_odoo_health()
    odoo_databases = list_odoo_databases() if odoo_healthy else []
    tenants = get_all_tenants()

    # Redis status
    redis_client = get_redis_client()
    redis_healthy = redis_client is not None

    return render_template('index.html',
        odoo_healthy=odoo_healthy,
        redis_healthy=redis_healthy,
        odoo_databases=odoo_databases,
        tenants=tenants,
        odoo_url=f"http://localhost:{config.ODOO_PORT}",
        config=config
    )

@app.route('/health')
def health():
    """Health check endpoint."""
    checks = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }

    # Check PostgreSQL
    try:
        conn = get_postgres_connection()
        if conn:
            checks['services']['postgres'] = 'healthy'
            conn.close()
        else:
            checks['services']['postgres'] = 'unhealthy'
            checks['status'] = 'degraded'
    except Exception as e:
        checks['services']['postgres'] = f'error: {str(e)}'
        checks['status'] = 'degraded'

    # Check Redis
    try:
        redis_client = get_redis_client()
        if redis_client:
            checks['services']['redis'] = 'healthy'
        else:
            checks['services']['redis'] = 'unhealthy'
            checks['status'] = 'degraded'
    except Exception as e:
        checks['services']['redis'] = f'error: {str(e)}'
        checks['status'] = 'degraded'

    # Check Odoo
    if check_odoo_health():
        checks['services']['odoo'] = 'healthy'
    else:
        checks['services']['odoo'] = 'unhealthy'
        checks['status'] = 'degraded'

    status_code = 200 if checks['status'] == 'healthy' else 503
    return jsonify(checks), status_code

@app.route('/api/databases')
def api_list_databases():
    """API endpoint to list all Odoo databases."""
    databases = list_odoo_databases()
    return jsonify({
        'success': True,
        'databases': databases,
        'count': len(databases)
    })

@app.route('/api/tenants')
def api_list_tenants():
    """API endpoint to list all tenants."""
    tenants = get_all_tenants()
    return jsonify({
        'success': True,
        'tenants': tenants,
        'count': len(tenants)
    })

@app.route('/create-tenant', methods=['GET', 'POST'])
def create_tenant():
    """Create a new tenant/database."""
    if request.method == 'GET':
        return render_template('create_tenant.html', config=config)

    # POST request - create the tenant
    try:
        # Get form data
        tenant_name = request.form.get('tenant_name', '').strip()
        database_name = request.form.get('database_name', '').strip().lower()
        admin_email = request.form.get('admin_email', '').strip()
        admin_password = request.form.get('admin_password', 'admin').strip()
        demo_data = request.form.get('demo_data') == 'on'
        language = request.form.get('language', 'en_US')
        country_code = request.form.get('country_code', 'US')

        # Validation
        if not tenant_name:
            flash('Tenant name is required', 'error')
            return redirect(url_for('create_tenant'))

        if not database_name:
            # Generate database name from tenant name
            database_name = re.sub(r'[^a-z0-9_]', '_', tenant_name.lower())
            database_name = re.sub(r'_+', '_', database_name).strip('_')

        # Validate database name
        is_valid, validation_msg = validate_database_name(database_name)
        if not is_valid:
            flash(validation_msg, 'error')
            return redirect(url_for('create_tenant'))

        # Create the Odoo database
        success, message = create_odoo_database(
            db_name=database_name,
            admin_password=admin_password,
            demo_data=demo_data,
            language=language,
            country_code=country_code
        )

        if not success:
            flash(f'Failed to create database: {message}', 'error')
            return redirect(url_for('create_tenant'))

        # Save to metadata database
        subdomain = database_name.replace('_', '-')
        save_success, save_result = save_tenant_to_metadata(
            name=tenant_name,
            database_name=database_name,
            subdomain=subdomain,
            admin_email=admin_email
        )

        if not save_success:
            logger.warning(f"Could not save tenant to metadata: {save_result}")

        # Cache the new tenant in Redis
        redis_client = get_redis_client()
        if redis_client:
            redis_client.hset(f"tenant:{database_name}", mapping={
                'name': tenant_name,
                'subdomain': subdomain,
                'admin_email': admin_email,
                'created_at': datetime.utcnow().isoformat()
            })

        flash(f'Tenant "{tenant_name}" created successfully! Database: {database_name}', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        flash(f'Error creating tenant: {str(e)}', 'error')
        return redirect(url_for('create_tenant'))

@app.route('/delete-tenant/<database_name>', methods=['POST'])
def delete_tenant(database_name):
    """Delete a tenant/database."""
    try:
        # Delete from Odoo
        success, message = delete_odoo_database(database_name)

        if success:
            # Delete from metadata database
            delete_tenant_from_metadata(database_name)

            # Delete from Redis cache
            redis_client = get_redis_client()
            if redis_client:
                redis_client.delete(f"tenant:{database_name}")

            flash(f'Tenant "{database_name}" deleted successfully', 'success')
        else:
            flash(f'Failed to delete tenant: {message}', 'error')

    except Exception as e:
        logger.error(f"Error deleting tenant: {e}")
        flash(f'Error deleting tenant: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/duplicate-tenant/<database_name>', methods=['POST'])
def duplicate_tenant(database_name):
    """Duplicate an existing tenant/database."""
    try:
        new_name = request.form.get('new_name', '').strip()
        if not new_name:
            new_name = f"{database_name}_copy"

        new_name = re.sub(r'[^a-z0-9_]', '_', new_name.lower())

        is_valid, validation_msg = validate_database_name(new_name)
        if not is_valid:
            flash(validation_msg, 'error')
            return redirect(url_for('index'))

        success, message = duplicate_odoo_database(database_name, new_name)

        if success:
            # Save to metadata
            save_tenant_to_metadata(
                name=new_name.replace('_', ' ').title(),
                database_name=new_name,
                subdomain=new_name.replace('_', '-'),
                admin_email=''
            )
            flash(f'Database duplicated successfully: {new_name}', 'success')
        else:
            flash(f'Failed to duplicate: {message}', 'error')

    except Exception as e:
        logger.error(f"Error duplicating tenant: {e}")
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/api/create-tenant', methods=['POST'])
def api_create_tenant():
    """API endpoint to create a tenant (JSON)."""
    try:
        data = request.get_json()

        tenant_name = data.get('tenant_name', '')
        database_name = data.get('database_name', '').lower()
        admin_email = data.get('admin_email', '')
        admin_password = data.get('admin_password', 'admin')
        demo_data = data.get('demo_data', False)
        language = data.get('language', 'en_US')
        country_code = data.get('country_code', 'US')

        if not tenant_name:
            return jsonify({'success': False, 'error': 'tenant_name is required'}), 400

        if not database_name:
            database_name = re.sub(r'[^a-z0-9_]', '_', tenant_name.lower())

        is_valid, validation_msg = validate_database_name(database_name)
        if not is_valid:
            return jsonify({'success': False, 'error': validation_msg}), 400

        success, message = create_odoo_database(
            db_name=database_name,
            admin_password=admin_password,
            demo_data=demo_data,
            language=language,
            country_code=country_code
        )

        if not success:
            return jsonify({'success': False, 'error': message}), 500

        subdomain = database_name.replace('_', '-')
        save_tenant_to_metadata(tenant_name, database_name, subdomain, admin_email)

        return jsonify({
            'success': True,
            'message': f'Tenant {tenant_name} created successfully',
            'data': {
                'database_name': database_name,
                'subdomain': subdomain,
                'odoo_url': f"{get_odoo_url()}/web?db={database_name}"
            }
        })

    except Exception as e:
        logger.error(f"API error creating tenant: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/delete-tenant/<database_name>', methods=['DELETE'])
def api_delete_tenant(database_name):
    """API endpoint to delete a tenant."""
    try:
        success, message = delete_odoo_database(database_name)

        if success:
            delete_tenant_from_metadata(database_name)
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===========================================
# Error Handlers
# ===========================================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Page not found', code=404), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('error.html', error='Internal server error', code=500), 500

# ===========================================
# Main Entry Point
# ===========================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    logger.info(f"Starting Admin Dashboard on port {port}")
    logger.info(f"Odoo URL: {get_odoo_url()}")

    app.run(host='0.0.0.0', port=port, debug=debug)
