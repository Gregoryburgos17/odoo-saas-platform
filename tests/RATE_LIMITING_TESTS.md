# Pruebas de Flask-Limiter (Rate Limiting)

Esta guía te ayudará a verificar que Flask-Limiter está funcionando correctamente en la plataforma Odoo SaaS.

## 📋 Tabla de Contenidos

- [Requisitos](#requisitos)
- [Configuración Actual](#configuración-actual)
- [Método 1: Script de Prueba Automatizado (Python)](#método-1-script-de-prueba-automatizado-python)
- [Método 2: Script Bash Simple](#método-2-script-bash-simple)
- [Método 3: Pruebas Manuales con curl](#método-3-pruebas-manuales-con-curl)
- [Verificación de Redis](#verificación-de-redis)
- [Solución de Problemas](#solución-de-problemas)

---

## Requisitos

### Servicios Requeridos

1. **Redis** - Debe estar corriendo para almacenar los límites
2. **PostgreSQL** - Base de datos de la aplicación
3. **Admin Service** (opcional) - Puerto 5000
4. **Portal Service** (opcional) - Puerto 5001

### Dependencias Python (para script automatizado)

```bash
pip install requests redis termcolor python-dotenv
```

---

## Configuración Actual

Flask-Limiter está configurado con los siguientes límites:

### Portal Service (`portal/`)

| Endpoint | Límite | Descripción |
|----------|--------|-------------|
| `POST /api/auth/register` | 5 por minuto | Registro de nuevos usuarios |
| `POST /api/auth/login` | 10 por minuto | Login de usuarios |
| `POST /api/auth/forgot-password` | 3 por minuto | Recuperación de contraseña |
| `POST /api/auth/reset-password` | 3 por minuto | Reseteo de contraseña |
| `POST /api/tenants` | 5 por hora | Crear nuevo tenant |
| `DELETE /api/tenants/:id` | 2 por hora | Eliminar tenant |
| `POST /api/support/tickets` | 30 por minuto | Crear ticket de soporte |
| `POST /api/support/tickets/:id/messages` | 5 por minuto | Enviar mensaje en ticket |

### Admin Service (`admin/`)

| Endpoint | Límite | Descripción |
|----------|--------|-------------|
| `POST /api/auth/register` | 5 por minuto | Registro de administradores |
| `POST /api/auth/login` | 10 por minuto | Login de administradores |
| `POST /api/auth/forgot-password` | 3 por minuto | Recuperación de contraseña |

### Variables de Entorno

El rate limiting se configura en `.env`:

```bash
# Redis (requerido para rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Límite por defecto
RATE_LIMIT_PER_MINUTE=60
```

---

## Método 1: Script de Prueba Automatizado (Python)

### Ejecutar

```bash
cd tests
python test_rate_limiting.py
```

### Qué hace el script

1. ✅ Verifica la conexión a Redis
2. ✅ Muestra las claves de rate limiting existentes
3. ✅ Envía múltiples requests al endpoint de login
4. ✅ Verifica que se reciban errores 429 (Too Many Requests)
5. ✅ Genera un reporte detallado con colores

### Salida Esperada

```
╔══════════════════════════════════════════════════════════════════════╗
║          PRUEBA DE FLASK-LIMITER - ODOO SAAS PLATFORM               ║
╚══════════════════════════════════════════════════════════════════════╝

══════════════════════════════════════════════════════════════════════
PRUEBA 1: Verificar conexión a Redis
══════════════════════════════════════════════════════════════════════
✅ Redis está funcionando correctamente
   Host: localhost:6379
   DB: 0
   Claves de rate limiting encontradas: 5

══════════════════════════════════════════════════════════════════════
PRUEBA 2: Verificar Rate Limiting - /api/auth/login
══════════════════════════════════════════════════════════════════════
✅ Request #1: 401 OK
✅ Request #2: 401 OK
✅ Request #3: 401 OK
✅ Request #4: 401 OK
✅ Request #5: 401 OK
🚫 Request #6: 429 RATE LIMITED
   └─ Retry-After: 60s
🚫 Request #7: 429 RATE LIMITED
🚫 Request #8: 429 RATE LIMITED
...

✅ RATE LIMITING ESTÁ FUNCIONANDO CORRECTAMENTE
   Se bloquearon 5 requests después de 5 exitosos
```

---

## Método 2: Script Bash Simple

### Ejecutar

```bash
cd tests
./test_rate_limiting.sh
```

### Opciones disponibles

```bash
# Todas las pruebas
./test_rate_limiting.sh all

# Solo probar Redis
./test_rate_limiting.sh redis

# Solo probar Portal
./test_rate_limiting.sh portal

# Solo probar Admin
./test_rate_limiting.sh admin

# Limpiar límites de rate
./test_rate_limiting.sh clear

# Ayuda
./test_rate_limiting.sh help
```

### Con variables de entorno personalizadas

```bash
# Probar un servicio remoto
PORTAL_URL=http://192.168.1.100:5001 ./test_rate_limiting.sh portal

# Usar Redis remoto
REDIS_HOST=192.168.1.100 REDIS_PORT=6379 ./test_rate_limiting.sh
```

---

## Método 3: Pruebas Manuales con curl

### 1. Probar endpoint de login (Portal)

```bash
# Enviar 10 requests rápidos
for i in {1..10}; do
    echo "Request #$i"
    curl -X POST http://localhost:5001/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"test123"}' \
        -w "\nStatus: %{http_code}\n" \
        -s | head -5
    echo "---"
    sleep 0.5
done
```

**Resultado esperado:** Los primeros 5 requests devolverán 401 (credenciales inválidas), los siguientes devolverán 429 (rate limited).

### 2. Probar con headers completos

```bash
curl -X POST http://localhost:5001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test123"}' \
    -v 2>&1 | grep -E "(HTTP|X-RateLimit|Retry-After)"
```

**Headers esperados:**
```
HTTP/1.1 401 UNAUTHORIZED
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1733284801
```

Cuando se excede el límite:
```
HTTP/1.1 429 TOO MANY REQUESTS
Retry-After: 60
```

### 3. Probar diferentes endpoints

```bash
# Registro (5 por minuto)
curl -X POST http://localhost:5001/api/auth/register \
    -H "Content-Type: application/json" \
    -d '{
        "email":"test@example.com",
        "password":"Test123!@#",
        "first_name":"Test",
        "last_name":"User"
    }'

# Crear tenant (5 por hora) - requiere autenticación
curl -X POST http://localhost:5001/api/tenants \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_JWT_TOKEN" \
    -d '{
        "name":"test-tenant",
        "plan_id":"plan-uuid"
    }'
```

---

## Verificación de Redis

### Ver claves de rate limiting

```bash
# Listar todas las claves
redis-cli KEYS "LIMITER/*"

# Output esperado:
# LIMITER/ip:127.0.0.1/api/auth/login
# LIMITER/ip:192.168.1.100/api/auth/register
```

### Ver valor de una clave

```bash
# Ver cuántos requests quedan
redis-cli GET "LIMITER/ip:127.0.0.1/api/auth/login"

# Ver tiempo de expiración (TTL)
redis-cli TTL "LIMITER/ip:127.0.0.1/api/auth/login"
```

### Monitorear en tiempo real

```bash
# Ver todos los comandos de Redis en tiempo real
redis-cli MONITOR | grep LIMITER

# Output:
# 1733284801.123456 [0 127.0.0.1:56789] "INCR" "LIMITER/ip:127.0.0.1/api/auth/login"
# 1733284801.234567 [0 127.0.0.1:56789] "EXPIRE" "LIMITER/ip:127.0.0.1/api/auth/login" "60"
```

### Limpiar límites (útil para testing)

```bash
# Eliminar todas las claves de rate limiting
redis-cli --scan --pattern "LIMITER/*" | xargs redis-cli DEL

# O eliminar una clave específica
redis-cli DEL "LIMITER/ip:127.0.0.1/api/auth/login"
```

---

## Solución de Problemas

### ❌ No se detecta rate limiting

**Problema:** Los requests no son bloqueados.

**Soluciones:**

1. **Verificar que Redis esté corriendo:**
   ```bash
   redis-cli ping
   # Debe responder: PONG
   ```

2. **Verificar configuración de REDIS_URL:**
   ```bash
   # En .env
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

3. **Verificar logs de la aplicación:**
   ```bash
   # Buscar errores de conexión a Redis
   cd portal
   FLASK_APP=app flask run --port 5001
   # O
   cd admin
   FLASK_APP=app flask run --port 5000
   ```

4. **Verificar que el endpoint tenga el decorador @limiter.limit:**
   ```bash
   grep -r "@limiter.limit" portal/app/api/
   ```

### ❌ Error: "redis.exceptions.ConnectionError"

**Problema:** No se puede conectar a Redis.

**Soluciones:**

1. **Iniciar Redis:**
   ```bash
   # Con Docker
   docker-compose up -d redis

   # Con Podman
   podman-compose up -d redis

   # Servicio local
   sudo systemctl start redis
   ```

2. **Verificar puerto y host:**
   ```bash
   redis-cli -h localhost -p 6379 ping
   ```

3. **Verificar firewall:**
   ```bash
   sudo ufw allow 6379/tcp
   ```

### ❌ Rate limiting funciona pero los límites no son correctos

**Problema:** Se bloquean más o menos requests de lo esperado.

**Soluciones:**

1. **Limpiar claves antiguas:**
   ```bash
   redis-cli FLUSHDB
   ```

2. **Verificar configuración del endpoint:**
   ```python
   # En portal/app/api/auth.py
   @auth_bp.route('/login', methods=['POST'])
   @limiter.limit("10 per minute", key_func=rate_limit_key)  # ← Verificar este valor
   def login():
       # ...
   ```

3. **Verificar variable de entorno:**
   ```bash
   echo $RATE_LIMIT_PER_MINUTE
   # Debe mostrar: 60
   ```

### ⚠️ Warnings sobre storage_uri deprecation

**Problema:** Mensaje de advertencia en los logs.

```
Flask-Limiter: storage_uri parameter is deprecated, use storage_options instead
```

**Solución:** Esto es solo una advertencia y no afecta la funcionalidad. Se corregirá en futuras versiones actualizando el código a:

```python
limiter.init_app(app, storage_options={'uri': app.config.get('RATELIMIT_STORAGE_URL')})
```

---

## Cómo interpretar los resultados

### ✅ Rate Limiting Funcionando Correctamente

- ✅ Redis responde a PING
- ✅ Se crean claves en Redis con patrón `LIMITER/*`
- ✅ Después de N requests, se recibe HTTP 429
- ✅ Headers `X-RateLimit-*` aparecen en las respuestas
- ✅ Header `Retry-After` indica cuándo se puede intentar de nuevo

### ❌ Rate Limiting NO Funciona

- ❌ Todos los requests retornan 200/401/400 (nunca 429)
- ❌ No aparecen claves `LIMITER/*` en Redis
- ❌ No aparecen headers `X-RateLimit-*`
- ❌ Redis no está conectado o responde con errores

---

## Información Adicional

### Arquitectura

```
┌─────────────┐
│   Cliente   │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────────────┐
│   Flask App         │
│   (Admin/Portal)    │
├─────────────────────┤
│  Flask-Limiter      │◄──────┐
│  Middleware         │       │
└──────┬──────────────┘       │
       │                      │
       │ Check limit          │ Store count
       ▼                      │
┌─────────────────────┐       │
│      Redis          │───────┘
│  (Storage Backend)  │
└─────────────────────┘
```

### Endpoints de Salud

```bash
# Verificar estado de los servicios
curl http://localhost:5001/health  # Portal
curl http://localhost:5000/health  # Admin

# Respuesta esperada:
{
    "status": "healthy",
    "redis": "connected",
    "database": "connected"
}
```

### Documentación Oficial

- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/)
- [Redis Documentation](https://redis.io/docs/)
- [HTTP 429 Status Code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)

---

## Resumen de Comandos Rápidos

```bash
# 1. Iniciar servicios
docker-compose up -d redis postgres

# 2. Ejecutar prueba automatizada
python tests/test_rate_limiting.py

# 3. Ejecutar prueba bash
./tests/test_rate_limiting.sh

# 4. Prueba manual rápida
for i in {1..10}; do curl -X POST http://localhost:5001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}' \
    -w "\n%{http_code}\n" -s | tail -1; done

# 5. Ver claves de Redis
redis-cli KEYS "LIMITER/*"

# 6. Limpiar límites
redis-cli --scan --pattern "LIMITER/*" | xargs redis-cli DEL

# 7. Monitorear Redis
redis-cli MONITOR | grep LIMITER
```

---

**¿Necesitas ayuda?** Revisa la sección de [Solución de Problemas](#solución-de-problemas) o contacta al equipo de desarrollo.
