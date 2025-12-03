#!/usr/bin/env python3
"""
Script de prueba para verificar que Flask-Limiter funciona correctamente
Prueba el rate limiting en los endpoints de autenticación
"""

import os
import sys
import time
import requests
import redis
from dotenv import load_dotenv
from termcolor import colored

# Cargar variables de entorno
load_dotenv()

def test_redis_connection():
    """Verifica la conexión a Redis"""
    print("\n" + "="*70)
    print(colored("PRUEBA 1: Verificar conexión a Redis", "cyan", attrs=["bold"]))
    print("="*70)

    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_password = os.getenv('REDIS_PASSWORD', '')
    redis_db = int(os.getenv('REDIS_DB', '0'))

    try:
        if redis_password:
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True
            )
        else:
            r = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True
            )

        # Hacer ping a Redis
        r.ping()
        print(colored("✅ Redis está funcionando correctamente", "green"))
        print(f"   Host: {redis_host}:{redis_port}")
        print(f"   DB: {redis_db}")

        # Verificar si hay claves de rate limiting
        keys = r.keys("LIMITER/*")
        if keys:
            print(f"\n   Claves de rate limiting encontradas: {len(keys)}")
            for key in keys[:5]:  # Mostrar solo las primeras 5
                ttl = r.ttl(key)
                print(f"   - {key} (expira en {ttl}s)")
        else:
            print(f"\n   No hay claves de rate limiting actualmente")

        return True
    except redis.ConnectionError as e:
        print(colored("❌ Error al conectar con Redis", "red"))
        print(f"   Error: {str(e)}")
        return False
    except Exception as e:
        print(colored(f"❌ Error inesperado: {str(e)}", "red"))
        return False

def test_rate_limiting(base_url, endpoint="/api/auth/login", limit=5, window="minute"):
    """
    Prueba el rate limiting enviando múltiples requests

    Args:
        base_url: URL base del servicio (ej: http://localhost:5001)
        endpoint: Endpoint a probar
        limit: Número de requests permitidos
        window: Ventana de tiempo (minute, hour)
    """
    print("\n" + "="*70)
    print(colored(f"PRUEBA 2: Verificar Rate Limiting - {endpoint}", "cyan", attrs=["bold"]))
    print("="*70)
    print(f"Límite configurado: {limit} requests por {window}")
    print(f"URL a probar: {base_url}{endpoint}")

    # Datos de prueba inválidos (para evitar crear usuarios reales)
    test_data = {
        "email": "test@example.com",
        "password": "wrongpassword"
    }

    success_count = 0
    rate_limited_count = 0
    responses = []

    # Enviar requests (intentar el doble del límite)
    total_requests = limit * 2
    print(f"\nEnviando {total_requests} requests...")

    for i in range(total_requests):
        try:
            response = requests.post(
                f"{base_url}{endpoint}",
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )

            responses.append({
                'number': i + 1,
                'status': response.status_code,
                'headers': dict(response.headers)
            })

            # Símbolos para mostrar el resultado
            if response.status_code == 429:
                rate_limited_count += 1
                symbol = colored("🚫", "red")
                status = colored("429 RATE LIMITED", "red", attrs=["bold"])
            elif response.status_code in [200, 400, 401]:
                success_count += 1
                symbol = colored("✅", "green")
                status = colored(f"{response.status_code} OK", "green")
            else:
                symbol = colored("⚠️", "yellow")
                status = colored(f"{response.status_code}", "yellow")

            # Obtener headers de rate limiting si existen
            retry_after = response.headers.get('Retry-After', 'N/A')
            limit_header = response.headers.get('X-RateLimit-Limit', 'N/A')
            remaining = response.headers.get('X-RateLimit-Remaining', 'N/A')
            reset = response.headers.get('X-RateLimit-Reset', 'N/A')

            print(f"{symbol} Request #{i+1}: {status}")
            if response.status_code == 429:
                print(f"   └─ Retry-After: {retry_after}s")
                if limit_header != 'N/A':
                    print(f"   └─ Limit: {limit_header}, Remaining: {remaining}, Reset: {reset}")

            # Pequeña pausa entre requests
            time.sleep(0.1)

        except requests.exceptions.RequestException as e:
            print(colored(f"❌ Request #{i+1} falló: {str(e)}", "red"))

    # Resumen
    print("\n" + "-"*70)
    print(colored("RESUMEN DE LA PRUEBA:", "cyan", attrs=["bold"]))
    print(f"  Total de requests enviados: {total_requests}")
    print(f"  Requests exitosos (200/400/401): {success_count}")
    print(f"  Requests bloqueados (429): {rate_limited_count}")

    # Verificación
    if rate_limited_count > 0:
        print("\n" + colored("✅ RATE LIMITING ESTÁ FUNCIONANDO CORRECTAMENTE", "green", attrs=["bold"]))
        print(f"   Se bloquearon {rate_limited_count} requests después de {success_count} exitosos")
        return True
    else:
        print("\n" + colored("⚠️  ADVERTENCIA: No se detectó rate limiting", "yellow", attrs=["bold"]))
        print("   Posibles causas:")
        print("   - Redis no está configurado correctamente")
        print("   - El endpoint no tiene rate limiting aplicado")
        print("   - El límite es mayor al número de requests enviados")
        return False

def print_manual_test_instructions():
    """Imprime instrucciones para probar manualmente con curl"""
    print("\n" + "="*70)
    print(colored("PRUEBAS MANUALES CON CURL", "cyan", attrs=["bold"]))
    print("="*70)

    print("\n1. Probar endpoint de login del Portal (5 requests/minuto):")
    print(colored("""
    for i in {1..10}; do
        echo "Request #$i"
        curl -X POST http://localhost:5001/api/auth/login \\
            -H "Content-Type: application/json" \\
            -d '{"email":"test@example.com","password":"test123"}' \\
            -w "\\nStatus: %{http_code}\\n" \\
            -s
        echo "---"
        sleep 0.5
    done
    """, "yellow"))

    print("\n2. Probar endpoint de registro del Admin (5 requests/minuto):")
    print(colored("""
    for i in {1..10}; do
        echo "Request #$i"
        curl -X POST http://localhost:5000/api/auth/login \\
            -H "Content-Type: application/json" \\
            -d '{"email":"admin@example.com","password":"admin123"}' \\
            -w "\\nStatus: %{http_code}\\n" \\
            -s
        echo "---"
        sleep 0.5
    done
    """, "yellow"))

    print("\n3. Verificar claves de Redis:")
    print(colored("""
    # Conectar a Redis y ver las claves de rate limiting
    redis-cli KEYS "LIMITER/*"

    # Ver el valor de una clave específica
    redis-cli GET "LIMITER/ip:127.0.0.1/api/auth/login"
    """, "yellow"))

    print("\n4. Limpiar límites de rate (para testing):")
    print(colored("""
    # Eliminar todas las claves de rate limiting
    redis-cli --scan --pattern "LIMITER/*" | xargs redis-cli DEL
    """, "yellow"))

def main():
    """Función principal"""
    print(colored("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║          PRUEBA DE FLASK-LIMITER - ODOO SAAS PLATFORM               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """, "blue", attrs=["bold"]))

    # Verificar que los servicios estén corriendo
    portal_url = os.getenv('PORTAL_URL', 'http://localhost:5001')
    admin_url = os.getenv('ADMIN_URL', 'http://localhost:5000')

    # Paso 1: Verificar Redis
    redis_ok = test_redis_connection()

    if not redis_ok:
        print(colored("\n⚠️  Redis no está disponible. No se pueden realizar más pruebas.", "yellow"))
        print("Asegúrate de que Redis esté corriendo:")
        print("  - Con Docker: docker-compose up -d redis")
        print("  - Con Podman: podman-compose up -d redis")
        return

    # Paso 2: Probar rate limiting en Portal
    print("\nVerificando si el servicio Portal está disponible...")
    try:
        response = requests.get(f"{portal_url}/health", timeout=5)
        print(colored("✅ Servicio Portal disponible", "green"))
        test_rate_limiting(portal_url, "/api/auth/login", limit=5)
    except requests.exceptions.RequestException:
        print(colored(f"⚠️  Servicio Portal no disponible en {portal_url}", "yellow"))
        print("   Inicia el servicio con: cd portal && flask run --port 5001")

    # Paso 3: Probar rate limiting en Admin
    print("\nVerificando si el servicio Admin está disponible...")
    try:
        response = requests.get(f"{admin_url}/health", timeout=5)
        print(colored("✅ Servicio Admin disponible", "green"))
        test_rate_limiting(admin_url, "/api/auth/login", limit=5)
    except requests.exceptions.RequestException:
        print(colored(f"⚠️  Servicio Admin no disponible en {admin_url}", "yellow"))
        print("   Inicia el servicio con: cd admin && flask run --port 5000")

    # Paso 4: Mostrar instrucciones para pruebas manuales
    print_manual_test_instructions()

    print("\n" + "="*70)
    print(colored("PRUEBAS COMPLETADAS", "green", attrs=["bold"]))
    print("="*70 + "\n")

if __name__ == "__main__":
    # Verificar dependencias
    try:
        import termcolor
        import redis
        import requests
    except ImportError as e:
        print("Error: Faltan dependencias. Instala con:")
        print("pip install requests redis termcolor python-dotenv")
        sys.exit(1)

    main()
