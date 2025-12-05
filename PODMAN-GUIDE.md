# 🚀 Guía Rápida de Podman para Odoo SaaS Platform

Esta guía te ayudará a levantar y gestionar los servicios de Odoo SaaS Platform usando Podman.

## 📋 Requisitos Previos

1. **Podman** instalado
2. **podman-compose** instalado
   ```bash
   pip install podman-compose
   ```
3. **curl** para validaciones de salud

## 🎯 Scripts Disponibles

### 1. `./restart-podman.sh` - Reinicio Completo (Interactivo)

**Cuándo usar:** Primera vez o cuando necesites un control completo del proceso.

**Características:**
- ✅ Detiene todos los contenedores
- ✅ Elimina contenedores existentes
- ✅ Opción para limpiar imágenes antiguas
- ✅ Reconstruye todas las imágenes desde cero
- ✅ Levanta todos los servicios
- ✅ Valida que todo esté funcionando
- ✅ Muestra logs si hay problemas
- ✅ Confirmaciones interactivas

**Uso:**
```bash
./restart-podman.sh
```

### 2. `./restart-podman-fast.sh` - Reinicio Rápido (Automático)

**Cuándo usar:** Para desarrollo diario cuando ya conoces el proceso.

**Características:**
- ⚡ Sin confirmaciones
- ⚡ Proceso automático completo
- ⚡ Validación rápida de servicios
- ⚡ Ideal para reiniciar durante desarrollo

**Uso:**
```bash
./restart-podman-fast.sh
```

## 🔧 Comandos Manuales Útiles

### Ver estado de servicios
```bash
podman-compose -f docker-compose.podman.yml ps
```

### Ver logs de un servicio específico
```bash
# Admin
podman logs -f odoo-saas-admin

# Portal
podman logs -f odoo-saas-portal

# PostgreSQL
podman logs -f odoo-saas-postgres

# Redis
podman logs -f odoo-saas-redis
```

### Reiniciar un servicio específico
```bash
podman-compose -f docker-compose.podman.yml restart admin
```

### Detener todos los servicios
```bash
podman-compose -f docker-compose.podman.yml down
```

### Levantar servicios sin reconstruir
```bash
podman-compose -f docker-compose.podman.yml up -d
```

### Reconstruir un solo servicio
```bash
podman-compose -f docker-compose.podman.yml build --no-cache admin
podman-compose -f docker-compose.podman.yml up -d admin
```

### Ver logs en tiempo real de todos los servicios
```bash
podman-compose -f docker-compose.podman.yml logs -f
```

## 🌐 Servicios Disponibles

| Servicio | Puerto | URL | Descripción |
|----------|--------|-----|-------------|
| **Admin Dashboard** | 5000 | http://localhost:5000 | Panel de administración |
| **Portal Customer** | 5001 | http://localhost:5001 | Portal de clientes |
| **Nginx** | 8082 | http://localhost:8082 | Proxy reverso |
| **RQ Dashboard** | 9182 | http://localhost:9182 | Monitor de trabajos |
| **Grafana** | 3100 | http://localhost:3100 | Visualización (admin/admin123) |
| **Prometheus** | 9091 | http://localhost:9091 | Métricas |
| **Adminer** | 8085 | http://localhost:8085 | Gestión de BD |
| **PostgreSQL** | 55432 | localhost:55432 | Base de datos |
| **Redis** | 6379 | localhost:6379 | Caché y colas |

## 🔍 Verificación de Salud

### Verificar PostgreSQL
```bash
podman exec odoo-saas-postgres pg_isready -U odoo
```

### Verificar Redis
```bash
podman exec odoo-saas-redis redis-cli ping
```

### Verificar Admin Service
```bash
curl http://localhost:5000/health
```

### Verificar Portal Service
```bash
curl http://localhost:5001/health
```

## 🐛 Solución de Problemas

### Problema: Los servicios no levantan

1. **Verificar logs:**
   ```bash
   podman logs odoo-saas-admin
   podman logs odoo-saas-portal
   ```

2. **Limpiar todo y empezar de nuevo:**
   ```bash
   ./restart-podman.sh
   # Selecciona 's' cuando pregunte si quieres eliminar imágenes
   ```

### Problema: Puerto ya en uso

1. **Ver qué está usando el puerto:**
   ```bash
   podman ps | grep 5000
   ```

2. **Detener el contenedor específico:**
   ```bash
   podman stop <container-id>
   ```

### Problema: Error de conexión a PostgreSQL

1. **Verificar que PostgreSQL esté corriendo:**
   ```bash
   podman ps | grep postgres
   ```

2. **Reiniciar PostgreSQL:**
   ```bash
   podman restart odoo-saas-postgres
   ```

3. **Verificar variables de entorno:**
   ```bash
   cat .env
   ```

### Problema: Error de conexión a Redis

1. **Verificar que Redis esté corriendo:**
   ```bash
   podman ps | grep redis
   ```

2. **Reiniciar Redis:**
   ```bash
   podman restart odoo-saas-redis
   ```

### Problema: Imágenes corruptas

**Eliminar todas las imágenes y reconstruir:**
```bash
podman images --filter "reference=localhost/odoo-saas-*" -q | xargs -r podman rmi -f
./restart-podman.sh
```

## 📊 Monitoreo Durante Desarrollo

### Ver uso de recursos
```bash
podman stats
```

### Ver solo contenedores de este proyecto
```bash
podman ps --filter "name=odoo-saas"
```

### Ejecutar comando dentro de un contenedor
```bash
# Acceder a PostgreSQL
podman exec -it odoo-saas-postgres psql -U odoo -d odoo_saas_platform

# Acceder a Redis CLI
podman exec -it odoo-saas-redis redis-cli

# Acceder a shell del Admin
podman exec -it odoo-saas-admin /bin/bash
```

## 🔄 Workflow Recomendado para Desarrollo

1. **Primera vez del día:**
   ```bash
   ./restart-podman.sh
   ```

2. **Durante desarrollo (si cambias código):**
   - Los cambios en Python se reflejan automáticamente (volúmenes montados)
   - No necesitas reiniciar a menos que cambies dependencias

3. **Si cambias requirements.txt o Dockerfile:**
   ```bash
   ./restart-podman-fast.sh
   ```

4. **Al final del día (opcional):**
   ```bash
   podman-compose -f docker-compose.podman.yml down
   ```

## ⚡ Tips de Performance

1. **No elimines imágenes si no es necesario** - acelera el reinicio
2. **Usa `restart-podman-fast.sh` para desarrollo diario**
3. **Monta volúmenes para hot-reload** - ya está configurado
4. **Monitorea con `podman stats`** - identifica cuellos de botella

## 🔐 Seguridad

- ⚠️ Estos scripts son para **desarrollo local**
- ⚠️ No usar en producción sin revisar configuración
- ⚠️ Cambiar contraseñas por defecto en `.env`

## 📝 Variables de Entorno

Revisa y ajusta el archivo `.env`:

```bash
# Base de datos
PG_DATABASE=odoo_saas_platform
PG_USER=odoo
PG_PASSWORD=tu_password_seguro

# Redis
REDIS_PASSWORD=tu_redis_password

# Flask
SECRET_KEY=tu_secret_key_super_seguro

# Grafana
GRAFANA_ADMIN_PASSWORD=tu_grafana_password
```

## 🆘 Ayuda Adicional

Si tienes problemas:

1. Revisa los logs: `podman-compose -f docker-compose.podman.yml logs`
2. Verifica el estado: `podman-compose -f docker-compose.podman.yml ps`
3. Consulta la documentación oficial de Podman: https://podman.io/docs

---

**¡Feliz desarrollo! 🎉**
