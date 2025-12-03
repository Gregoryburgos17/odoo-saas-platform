# Rebuild Script - Reconstruye solo las imágenes que cambiaron
@echo off
echo.
echo ========================================
echo Reconstruyendo imagenes modificadas
echo ========================================
echo.

cd /d D:\odoo-saas-platform

echo [1/2] Reconstruyendo Admin (codigo modificado)...
podman build -t localhost/odoo-saas-admin:latest -f admin/Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Fallo al construir Admin
    exit /b 1
)
echo OK - Admin

echo.
echo [2/2] Reconstruyendo Portal (codigo modificado)...
podman build -t localhost/odoo-saas-portal:latest -f portal/Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Fallo al construir Portal
    exit /b 1
)
echo OK - Portal

echo.
echo ========================================
echo LISTO! Ahora ejecuta:
echo   podman-dev.cmd down
echo   podman-dev.cmd up-no-build
echo ========================================
echo.
