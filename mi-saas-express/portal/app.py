"""
MI-SAAS-EXPRESS - Portal de Creación de Tenants
===============================================
Un portal Flask minimalista para crear nuevas instancias Odoo.
"""

import os
import sys
from flask import Flask, render_template, request, jsonify

# Agregar el directorio provisioner al path
sys.path.insert(0, '/app/provisioner')
from odoo_creator import OdooCreator

app = Flask(__name__)

# Configuración desde variables de entorno
ODOO_URL = os.environ.get('ODOO_URL', 'http://odoo:8069')
ODOO_MASTER_PASSWORD = os.environ.get('ODOO_MASTER_PASSWORD', 'admin123')
DEFAULT_ADMIN_PASSWORD = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin')
ODOO_EXTERNAL_PORT = os.environ.get('ODOO_EXTERNAL_PORT', '8069')


@app.route('/')
def index():
    """Página principal con el formulario de creación."""
    return render_template('index.html', odoo_port=ODOO_EXTERNAL_PORT)


@app.route('/create', methods=['POST'])
def create_tenant():
    """
    Endpoint para crear un nuevo tenant (base de datos Odoo).

    Espera JSON con:
    - tenant_name: Nombre del tenant (será el nombre de la DB)
    - admin_email: Email del administrador (opcional)
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No se recibieron datos JSON'
            }), 400

        tenant_name = data.get('tenant_name', '').strip().lower()
        admin_email = data.get('admin_email', f'admin@{tenant_name}.local')

        # Validar nombre del tenant
        if not tenant_name:
            return jsonify({
                'success': False,
                'error': 'El nombre del tenant es requerido'
            }), 400

        # Solo permitir caracteres alfanuméricos y guiones
        if not all(c.isalnum() or c == '-' for c in tenant_name):
            return jsonify({
                'success': False,
                'error': 'El nombre solo puede contener letras, números y guiones'
            }), 400

        # Crear el tenant usando el provisioner
        creator = OdooCreator(
            odoo_url=ODOO_URL,
            master_password=ODOO_MASTER_PASSWORD
        )

        result = creator.create_database(
            db_name=tenant_name,
            admin_password=DEFAULT_ADMIN_PASSWORD,
            admin_email=admin_email
        )

        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Tenant "{tenant_name}" creado exitosamente',
                'tenant_name': tenant_name,
                'url': f'http://localhost:{ODOO_EXTERNAL_PORT}/web?db={tenant_name}',
                'credentials': {
                    'email': admin_email,
                    'password': DEFAULT_ADMIN_PASSWORD
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Error desconocido')
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/list', methods=['GET'])
def list_databases():
    """Lista todas las bases de datos disponibles."""
    try:
        creator = OdooCreator(
            odoo_url=ODOO_URL,
            master_password=ODOO_MASTER_PASSWORD
        )

        databases = creator.list_databases()

        return jsonify({
            'success': True,
            'databases': databases,
            'count': len(databases)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health')
def health():
    """Endpoint de salud."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
