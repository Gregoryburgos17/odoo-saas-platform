# Odoo SaaS Platform - Guía de Instalación con Podman en Windows

Esta guía te ayudará a ejecutar la plataforma Odoo SaaS localmente en Windows usando Podman Desktop.

## Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Instalación de Podman](#instalación-de-podman)
- [Configuración Rápida](#configuración-rápida)
- [Inicio de la Plataforma](#inicio-de-la-plataforma)
- [Acceso a los Servicios](#acceso-a-los-servicios)
- [Comandos Útiles](#comandos-útiles)
- [Solución de Problemas](#solución-de-problemas)
- [Arquitectura](#arquitectura)

---

## Requisitos Previos

### Sistema Operativo
- **Windows 10** versión 2004 o superior (Build 19041+)
- **Windows 11** (cualquier versión)

### Software Requerido
1. **WSL2** (Windows Subsystem for Linux 2)
2. **Podman Desktop** (alternativa a Docker)
3. **Python 3.8+** (para podman-compose)
4. **Git** (para clonar el repositorio)

### Recursos Mínimos
- **RAM:** 8 GB (recomendado 16 GB)
- **Disco:** 20 GB libres
- **CPU:** 4 cores

---

## Instalación de Podman

### Paso 1: Instalar WSL2

Abre PowerShell como **Administrador** y ejecuta:

```powershell
# Instalar WSL2
wsl --install

# Reiniciar el equipo cuando se solicite
```

Después del reinicio, verifica la instalación:

```powershell
wsl --status
```

### Paso 2: Instalar Podman Desktop

**Opción A: Descargar instalador (Recomendado)**

1. Ve a [https://podman-desktop.io/downloads](https://podman-desktop.io/downloads)
2. Descarga el instalador para Windows
3. Ejecuta el instalador y sigue las instrucciones

**Opción B: Usar winget**

```powershell
winget install -e --id RedHat.Podman-Desktop
```

### Paso 3: Configurar Podman

1. Abre **Podman Desktop**
2. Sigue el asistente de configuración inicial
3. Cuando pregunte, crea una máquina con estos recursos:
   - **CPUs:** 4
   - **Memoria:** 4096 MB
   - **Disco:** 50 GB

O desde PowerShell:

```powershell
# Crear máquina Podman
podman machine init --cpus 4 --memory 4096 --disk-size 50

# Iniciar la máquina
podman machine start
```

### Paso 4: Instalar podman-compose

```powershell
# Instalar con pip
pip install podman-compose

# Verificar instalación
podman-compose --version
```

---

## Configuración Rápida

### Usando el Script de Configuración

El proyecto incluye un script que automatiza toda la configuración:

```powershell
# Navegar al directorio del proyecto
cd ruta\al\odoo-saas-platform

# Ejecutar script de configuración
.\scripts\windows\setup-podman.ps1
```

El script:
1. Verifica WSL2
2. Verifica/instala Podman
3. Verifica/instala podman-compose
4. Configura la máquina Podman
5. Crea el archivo `.env`

### Configuración Manual

Si prefieres configurar manualmente:

```powershell
# 1. Navegar al proyecto
cd ruta\al\odoo-saas-platform

# 2. Copiar archivo de configuración
copy .env.windows .env

# 3. (Opcional) Editar configuración
notepad .env
```

---

## Inicio de la Plataforma

### Primera Vez (Construir Imágenes)

```powershell
# Opción 1: Usar script
.\scripts\windows\start-platform.ps1 -Build

# Opción 2: Comandos directos
podman-compose -f podman-compose.windows.yml build
podman-compose -f podman-compose.windows.yml up -d
```

### Inicios Posteriores

```powershell
# Usando script
.\scripts\windows\start-platform.ps1

# O directamente
podman-compose -f podman-compose.windows.yml up -d
```

### Con Monitoreo (Prometheus/Grafana)

```powershell
.\scripts\windows\start-platform.ps1 -Build -Monitoring
```

### Ver Logs en Tiempo Real

```powershell
.\scripts\windows\start-platform.ps1 -Logs
```

---

## Acceso a los Servicios

Una vez iniciada la plataforma, estos son los servicios disponibles:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Admin Dashboard** | http://localhost:5000 | Panel de administración |
| **Portal Cliente** | http://localhost:5001 | Portal de autoservicio |
| **RQ Dashboard** | http://localhost:9181 | Monitor de trabajos |
| **Adminer** | http://localhost:8085 | Administrador de BD |
| **Prometheus** | http://localhost:9090 | Métricas (con -Monitoring) |
| **Grafana** | http://localhost:3000 | Dashboards (con -Monitoring) |

### Credenciales de Base de Datos (Adminer)

| Campo | Valor |
|-------|-------|
| Sistema | PostgreSQL |
| Servidor | postgres |
| Usuario | odoo |
| Contraseña | odoo_dev_2024 |
| Base de datos | odoo_saas_platform |

### Credenciales de Grafana

| Campo | Valor |
|-------|-------|
| Usuario | admin |
| Contraseña | admin123 |

---

## Comandos Útiles

### Scripts de PowerShell

```powershell
# Iniciar plataforma
.\scripts\windows\start-platform.ps1

# Iniciar con construcción de imágenes
.\scripts\windows\start-platform.ps1 -Build

# Iniciar con monitoreo
.\scripts\windows\start-platform.ps1 -Monitoring

# Ver estado de servicios
.\scripts\windows\status-platform.ps1

# Ver estado detallado
.\scripts\windows\status-platform.ps1 -Detailed

# Detener plataforma
.\scripts\windows\stop-platform.ps1

# Detener y eliminar datos
.\scripts\windows\stop-platform.ps1 -Volumes

# Detener, eliminar datos e imágenes
.\scripts\windows\stop-platform.ps1 -All
```

### Comandos de Podman

```powershell
# Ver contenedores en ejecución
podman ps

# Ver todos los contenedores
podman ps -a

# Ver logs de un servicio
podman logs odoo-saas-admin
podman logs -f odoo-saas-admin  # En tiempo real

# Acceder a shell de un contenedor
podman exec -it odoo-saas-admin /bin/bash

# Reiniciar un servicio
podman restart odoo-saas-admin

# Ver uso de recursos
podman stats
```

### Comandos de podman-compose

```powershell
# Ver estado de servicios
podman-compose -f podman-compose.windows.yml ps

# Ver logs de todos los servicios
podman-compose -f podman-compose.windows.yml logs

# Ver logs de un servicio específico
podman-compose -f podman-compose.windows.yml logs admin

# Reiniciar todos los servicios
podman-compose -f podman-compose.windows.yml restart

# Detener todos los servicios
podman-compose -f podman-compose.windows.yml down

# Detener y eliminar volúmenes
podman-compose -f podman-compose.windows.yml down -v
```

### Gestión de la Máquina Podman

```powershell
# Ver estado de la máquina
podman machine list

# Iniciar máquina
podman machine start

# Detener máquina
podman machine stop

# Reiniciar máquina
podman machine stop && podman machine start

# Eliminar máquina (¡elimina todos los datos!)
podman machine rm podman-machine-default
```

---

## Solución de Problemas

### Error: "Cannot connect to Podman"

```powershell
# Verificar que la máquina está corriendo
podman machine list

# Si no está corriendo, iniciarla
podman machine start

# Si sigue fallando, reiniciar
podman machine stop
podman machine start
```

### Error: "Port already in use"

```powershell
# Ver qué proceso usa el puerto (ejemplo: 5000)
netstat -ano | findstr :5000

# Terminar el proceso (reemplazar PID)
taskkill /PID <PID> /F

# O cambiar el puerto en .env
```

### Error: "Image not found"

```powershell
# Reconstruir imágenes
podman-compose -f podman-compose.windows.yml build --no-cache
```

### Contenedores se reinician constantemente

```powershell
# Ver logs para identificar el error
podman logs odoo-saas-admin

# Errores comunes:
# - Base de datos no lista: esperar más tiempo
# - Dependencias faltantes: reconstruir imagen
# - Configuración incorrecta: revisar .env
```

### Error de memoria o recursos

```powershell
# Aumentar recursos de la máquina
podman machine stop
podman machine rm podman-machine-default

# Crear nueva máquina con más recursos
podman machine init --cpus 4 --memory 8192 --disk-size 100
podman machine start
```

### Limpiar todo y empezar de cero

```powershell
# Detener y eliminar todo
.\scripts\windows\stop-platform.ps1 -All

# O manualmente:
podman-compose -f podman-compose.windows.yml down -v
podman system prune -a -f
podman volume prune -f
```

---

## Arquitectura

### Servicios Incluidos

```
┌─────────────────────────────────────────────────────────────┐
│                     PODMAN EN WINDOWS                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Admin     │  │   Portal    │  │   Worker    │          │
│  │  Dashboard  │  │   Cliente   │  │   (RQ)      │          │
│  │  :5000      │  │   :5001     │  │             │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│              ┌───────────┴───────────┐                       │
│              │                       │                       │
│        ┌─────┴─────┐          ┌──────┴──────┐               │
│        │PostgreSQL │          │    Redis    │               │
│        │  :5432    │          │   :6379     │               │
│        └───────────┘          └─────────────┘               │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │     RQ      │  │   Adminer   │  │  Prometheus │          │
│  │  Dashboard  │  │   (DB UI)   │  │  + Grafana  │          │
│  │   :9181     │  │   :8085     │  │ :9090/:3000 │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

1. **Usuario** accede via navegador a Admin (:5000) o Portal (:5001)
2. **Flask Apps** procesan las solicitudes
3. **PostgreSQL** almacena datos persistentes
4. **Redis** maneja caché y cola de trabajos
5. **Workers** procesan tareas en segundo plano

### Volúmenes Persistentes

| Volumen | Uso |
|---------|-----|
| `postgres_data` | Base de datos PostgreSQL |
| `redis_data` | Datos de Redis |
| `prometheus_data` | Métricas históricas |
| `grafana_data` | Configuración de dashboards |

---

## Desarrollo

### Modificar Código

Los directorios `admin/`, `portal/`, `workers/` y `shared/` están montados como volúmenes de solo lectura. Para desarrollar:

1. Modifica los archivos en tu editor de Windows
2. Los cambios se reflejan automáticamente en el contenedor
3. Para cambios que requieren reinicio:
   ```powershell
   podman restart odoo-saas-admin
   ```

### Agregar Dependencias

1. Edita el archivo `requirements.txt` correspondiente
2. Reconstruye la imagen:
   ```powershell
   podman-compose -f podman-compose.windows.yml build admin
   podman restart odoo-saas-admin
   ```

### Ejecutar Migraciones de Base de Datos

```powershell
podman exec -it odoo-saas-admin alembic upgrade head
```

### Ejecutar Tests

```powershell
podman exec -it odoo-saas-admin pytest
```

---

## Diferencias con Docker

| Característica | Docker | Podman |
|----------------|--------|--------|
| Daemon | Requiere daemon | Sin daemon (daemonless) |
| Root | Requiere root por defecto | Sin root por defecto |
| Compose | docker-compose | podman-compose |
| Imágenes | docker.io/ | docker.io/ (prefijo explícito) |
| Seguridad | Menor aislamiento | Mayor aislamiento |

### Compatibilidad

- Los archivos `Dockerfile` son 100% compatibles
- Los archivos `docker-compose.yml` son mayormente compatibles
- Algunos ajustes pueden ser necesarios para volúmenes y redes

---

## Soporte

Si encuentras problemas:

1. Revisa la sección [Solución de Problemas](#solución-de-problemas)
2. Revisa los logs: `podman logs <contenedor>`
3. Abre un issue en el repositorio

---

## Licencia

Este proyecto está bajo la licencia especificada en el archivo LICENSE del repositorio principal.
