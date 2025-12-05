# Odoo SaaS Platform - Development Edition

Una plataforma SaaS para Odoo simplificada, diseñada para desarrollo local con **Podman** en Windows.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                     Odoo SaaS Platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │    Admin     │───▶│    Odoo      │───▶│  PostgreSQL  │      │
│  │  Dashboard   │    │   (8069)     │    │   (5432)     │      │
│  │   (5000)     │    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   ▲               │
│         │                   │                   │               │
│         ▼                   ▼                   │               │
│  ┌──────────────────────────────────────────────┘               │
│  │                                                              │
│  │  ┌──────────────┐                                           │
│  │  │    Redis     │  Cache & Sessions                         │
│  │  │   (6379)     │                                           │
│  │  └──────────────┘                                           │
│  │                                                              │
└──┴──────────────────────────────────────────────────────────────┘
```

## Componentes

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Admin Dashboard** | 5000 | Panel Flask para gestionar tenants |
| **Odoo ERP** | 8069 | Servidor Odoo multi-tenant |
| **PostgreSQL** | 5432 | Base de datos para todos los tenants |
| **Redis** | 6379 | Caché y gestión de sesiones |

## Requisitos Previos

- **Windows 10/11** con WSL2
- **Podman Desktop** instalado y configurado
- **podman-compose** instalado:
  ```bash
  pip install podman-compose
  ```

## Instalación y Ejecución

### Paso 1: Clonar o copiar el proyecto

```bash
cd /ruta/a/tu/proyecto/saas-dev
```

### Paso 2: Iniciar los servicios

```bash
# Construir e iniciar todos los servicios
podman-compose up -d --build

# Ver los logs en tiempo real
podman-compose logs -f
```

### Paso 3: Verificar que todos los servicios están corriendo

```bash
# Ver el estado de los contenedores
podman-compose ps

# Esperar a que Odoo esté listo (puede tomar 1-2 minutos)
# Verificar con:
curl http://localhost:8069/web/health
```

### Paso 4: Acceder al Admin Dashboard

Abre tu navegador y ve a:
- **Admin Dashboard**: http://localhost:5000
- **Odoo directo**: http://localhost:8069

## Uso del Admin Dashboard

### Crear un Nuevo Tenant

1. Accede a http://localhost:5000
2. Haz clic en **"Create New Tenant"**
3. Completa el formulario:
   - **Tenant Name**: Nombre de la empresa (ej: "Acme Corporation")
   - **Database Name**: Se genera automáticamente
   - **Admin Email**: Email del administrador (opcional)
   - **Admin Password**: Contraseña para el usuario admin de Odoo
   - **Language/Country**: Configuración regional
   - **Demo Data**: Marcar si quieres datos de ejemplo
4. Haz clic en **"Create Tenant"**

### Acceder al Odoo del Tenant

Una vez creado el tenant:
1. En el Dashboard, verás el tenant en la lista
2. Haz clic en **"Open"** para ir a Odoo
3. Inicia sesión con:
   - **Usuario**: `admin`
   - **Contraseña**: La que configuraste al crear el tenant

## Credenciales por Defecto

| Servicio | Usuario | Contraseña |
|----------|---------|------------|
| PostgreSQL | odoo | odoo_secret_2024 |
| Odoo Master | - | admin_master_2024 |
| Admin Odoo (por tenant) | admin | (configurado al crear) |

## Comandos Útiles

```bash
# Ver logs de un servicio específico
podman-compose logs -f odoo
podman-compose logs -f admin

# Reiniciar un servicio
podman-compose restart odoo

# Detener todos los servicios
podman-compose down

# Detener y eliminar volúmenes (¡BORRA TODOS LOS DATOS!)
podman-compose down -v

# Reconstruir un servicio específico
podman-compose up -d --build admin

# Acceder a la shell de un contenedor
podman exec -it saas_odoo /bin/bash
podman exec -it saas_admin /bin/bash

# Ver uso de recursos
podman stats
```

## API Endpoints

El Admin Dashboard expone una API REST:

### Listar Bases de Datos
```bash
curl http://localhost:5000/api/databases
```

### Listar Tenants
```bash
curl http://localhost:5000/api/tenants
```

### Crear Tenant (API)
```bash
curl -X POST http://localhost:5000/api/create-tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Mi Empresa",
    "database_name": "mi_empresa",
    "admin_password": "admin123",
    "demo_data": false,
    "language": "es_ES",
    "country_code": "ES"
  }'
```

### Eliminar Tenant (API)
```bash
curl -X DELETE http://localhost:5000/api/delete-tenant/mi_empresa
```

### Health Check
```bash
curl http://localhost:5000/health
```

## Estructura del Proyecto

```
saas-dev/
├── podman-compose.yml      # Orquestación de servicios
├── .env                    # Variables de entorno
├── README.md               # Este archivo
│
├── admin/                  # Admin Dashboard (Flask)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   └── templates/
│       ├── index.html
│       ├── create_tenant.html
│       └── error.html
│
├── odoo/                   # Configuración de Odoo
│   ├── Dockerfile
│   └── odoo.conf
│
└── db/                     # PostgreSQL
    └── init.sql            # Script de inicialización
```

## Solución de Problemas

### Odoo tarda mucho en iniciar
Es normal que Odoo tarde 1-2 minutos en estar disponible la primera vez. Verifica con:
```bash
podman-compose logs -f odoo
```

### Error de conexión a la base de datos
Asegúrate de que PostgreSQL está saludable:
```bash
podman exec saas_db pg_isready -U odoo
```

### El Admin Dashboard no puede conectar con Odoo
Verifica que Odoo responde:
```bash
curl http://localhost:8069/web/health
```

### Permisos en Windows/Podman
Si hay problemas de permisos con volúmenes:
```bash
# Ejecutar Podman con rootless
podman machine set --rootful=false
podman machine stop
podman machine start
```

### Limpiar todo y empezar de nuevo
```bash
podman-compose down -v
podman system prune -a --volumes
podman-compose up -d --build
```

## Desarrollo y Personalización

### Agregar addons personalizados a Odoo
1. Crea una carpeta `addons/` en el directorio `saas-dev/`
2. Modifica `podman-compose.yml` para montar el volumen:
   ```yaml
   odoo:
     volumes:
       - ./addons:/mnt/extra-addons:ro
   ```
3. Reinicia Odoo: `podman-compose restart odoo`

### Modificar el Admin Dashboard
1. Edita los archivos en `admin/`
2. El hot-reload está activado en desarrollo
3. Para cambios en dependencias: `podman-compose up -d --build admin`

## Notas Importantes

- Esta es una configuración de **DESARROLLO**, no usar en producción
- Las contraseñas están en texto plano en `.env` - cambiarlas para producción
- No hay SSL/TLS configurado
- Los datos se persisten en volúmenes de Podman

## Licencia

MIT License
