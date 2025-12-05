"""
MI-SAAS-EXPRESS - Odoo Database Creator
=======================================
Script para crear bases de datos Odoo usando la API XML-RPC.

Este es el corazón del sistema de provisioning. Usa la API nativa
de Odoo para crear nuevas bases de datos de forma programática.
"""

import xmlrpc.client
import socket
from typing import Optional


class OdooCreator:
    """
    Clase para interactuar con Odoo vía XML-RPC.

    Odoo expone varios endpoints XML-RPC:
    - /xmlrpc/2/db      -> Operaciones de base de datos (crear, duplicar, eliminar)
    - /xmlrpc/2/common  -> Autenticación y versión
    - /xmlrpc/2/object  -> Operaciones CRUD en modelos
    """

    def __init__(self, odoo_url: str, master_password: str):
        """
        Inicializa el creador.

        Args:
            odoo_url: URL base de Odoo (ej: http://odoo:8069)
            master_password: Contraseña maestra de Odoo (admin_passwd en config)
        """
        self.odoo_url = odoo_url.rstrip('/')
        self.master_password = master_password

        # Crear proxy XML-RPC para operaciones de DB
        self.db_proxy = xmlrpc.client.ServerProxy(
            f'{self.odoo_url}/xmlrpc/2/db',
            allow_none=True
        )

        # Proxy para operaciones comunes (auth, versión)
        self.common_proxy = xmlrpc.client.ServerProxy(
            f'{self.odoo_url}/xmlrpc/2/common',
            allow_none=True
        )

    def check_connection(self) -> dict:
        """
        Verifica la conexión con Odoo.

        Returns:
            dict con success y version/error
        """
        try:
            version = self.common_proxy.version()
            return {
                'success': True,
                'version': version
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_databases(self) -> list:
        """
        Lista todas las bases de datos disponibles.

        Returns:
            Lista de nombres de bases de datos
        """
        try:
            # Intentar listar (puede estar deshabilitado por seguridad)
            databases = self.db_proxy.list()
            return databases if databases else []
        except xmlrpc.client.Fault as e:
            # Si el listado está deshabilitado, retornar lista vacía
            if 'AccessDenied' in str(e):
                return []
            raise
        except Exception:
            return []

    def database_exists(self, db_name: str) -> bool:
        """
        Verifica si una base de datos ya existe.

        Args:
            db_name: Nombre de la base de datos

        Returns:
            True si existe, False si no
        """
        try:
            return self.db_proxy.db_exist(db_name)
        except Exception:
            # Si falla, intentar con la lista
            databases = self.list_databases()
            return db_name in databases

    def create_database(
        self,
        db_name: str,
        admin_password: str = 'admin',
        admin_email: str = 'admin@example.com',
        lang: str = 'es_ES',
        country_code: str = 'ES',
        demo: bool = False
    ) -> dict:
        """
        Crea una nueva base de datos Odoo.

        Este método usa la API XML-RPC de Odoo para:
        1. Verificar que la DB no existe
        2. Crear la DB con los parámetros especificados
        3. El usuario admin se crea automáticamente

        Args:
            db_name: Nombre de la base de datos (será el nombre del tenant)
            admin_password: Contraseña para el usuario admin
            admin_email: Email del usuario admin (también usado como login)
            lang: Código de idioma (ej: es_ES, en_US)
            country_code: Código de país ISO (ej: ES, US, MX)
            demo: Si True, carga datos de demostración

        Returns:
            dict con success y message/error
        """
        try:
            # 1. Verificar si la base de datos ya existe
            if self.database_exists(db_name):
                return {
                    'success': False,
                    'error': f'La base de datos "{db_name}" ya existe'
                }

            # 2. Crear la base de datos
            # La API create_database de Odoo:
            # create_database(master_password, db_name, demo, lang, admin_password, login, country_code)
            #
            # IMPORTANTE: El parámetro 'login' es el email que se usará
            # como nombre de usuario para el admin

            print(f"[OdooCreator] Creando base de datos: {db_name}")
            print(f"[OdooCreator] Admin email: {admin_email}")
            print(f"[OdooCreator] Idioma: {lang}, País: {country_code}")

            # Llamar a la API de creación
            # Nota: Este método puede tardar 30-60 segundos
            result = self.db_proxy.create_database(
                self.master_password,  # Master password
                db_name,               # Database name
                demo,                  # Load demo data
                lang,                  # Language
                admin_password,        # Admin password
                admin_email,           # Admin login (email)
                country_code           # Country code
            )

            print(f"[OdooCreator] Base de datos creada exitosamente: {result}")

            return {
                'success': True,
                'message': f'Base de datos "{db_name}" creada exitosamente',
                'db_name': db_name,
                'admin_login': admin_email
            }

        except xmlrpc.client.Fault as e:
            error_msg = str(e.faultString)
            print(f"[OdooCreator] Error XML-RPC: {error_msg}")

            # Traducir errores comunes
            if 'database' in error_msg.lower() and 'exists' in error_msg.lower():
                return {
                    'success': False,
                    'error': f'La base de datos "{db_name}" ya existe'
                }
            elif 'access denied' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Contraseña maestra incorrecta'
                }
            else:
                return {
                    'success': False,
                    'error': error_msg
                }

        except socket.timeout:
            return {
                'success': False,
                'error': 'Timeout: La creación está tardando demasiado. Intenta de nuevo.'
            }

        except ConnectionRefusedError:
            return {
                'success': False,
                'error': 'No se puede conectar con Odoo. ¿Está el servicio corriendo?'
            }

        except Exception as e:
            print(f"[OdooCreator] Error inesperado: {type(e).__name__}: {e}")
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }

    def drop_database(self, db_name: str) -> dict:
        """
        Elimina una base de datos.

        ⚠️ CUIDADO: Esta operación es irreversible.

        Args:
            db_name: Nombre de la base de datos a eliminar

        Returns:
            dict con success y message/error
        """
        try:
            if not self.database_exists(db_name):
                return {
                    'success': False,
                    'error': f'La base de datos "{db_name}" no existe'
                }

            result = self.db_proxy.drop(self.master_password, db_name)

            return {
                'success': True,
                'message': f'Base de datos "{db_name}" eliminada'
            }

        except xmlrpc.client.Fault as e:
            return {
                'success': False,
                'error': str(e.faultString)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Para pruebas locales
if __name__ == '__main__':
    import os

    # Configuración de prueba
    odoo_url = os.environ.get('ODOO_URL', 'http://localhost:8069')
    master_pass = os.environ.get('ODOO_MASTER_PASSWORD', 'admin123')

    creator = OdooCreator(odoo_url, master_pass)

    # Verificar conexión
    print("Verificando conexión...")
    conn = creator.check_connection()
    print(f"Conexión: {conn}")

    # Listar DBs
    print("\nBases de datos existentes:")
    dbs = creator.list_databases()
    for db in dbs:
        print(f"  - {db}")

    # Crear DB de prueba
    print("\nCreando base de datos de prueba...")
    result = creator.create_database(
        db_name='test-empresa',
        admin_password='admin',
        admin_email='admin@test.local'
    )
    print(f"Resultado: {result}")
