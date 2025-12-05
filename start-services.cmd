@echo off
echo ========================================
echo   RECONSTRUIR Y LEVANTAR SERVICIOS
echo ========================================
echo.

cd /d D:\odoo-saas-platform

echo [Paso 1/4] Deteniendo servicios actuales...
podman-compose -f docker-compose.podman.yml down

echo.
echo [Paso 2/4] Construyendo Admin (2-3 min)...
podman build -t localhost/odoo-saas-admin:latest -f admin/Dockerfile .

echo.
echo [Paso 3/4] Construyendo Portal (2-3 min)...
podman build -t localhost/odoo-saas-portal:latest -f portal/Dockerfile .

echo.
echo [Paso 4/4] Iniciando todos los servicios...
podman-compose -f docker-compose.podman.yml up -d

echo.
echo ========================================
echo   SERVICIOS INICIADOS
echo ========================================
echo.
echo Ver logs de admin:   podman logs odoo-saas-admin --tail 20
echo Ver logs de portal:  podman logs odoo-saas-portal --tail 20
echo.
echo Acceder a:
echo   - Admin:  http://localhost:5000
echo   - Portal: http://localhost:5001
echo   - Grafana: http://localhost:3100
echo.
pause
