@echo off
REM ================================================================
REM Script para construir imágenes manualmente con Podman
REM ================================================================
REM Este script construye las imágenes una por una para evitar
REM problemas de podman-compose con rutas en Windows

echo.
echo ========================================
echo Construyendo imagenes con Podman
echo ========================================
echo.

REM Cambiar al directorio del script (raíz del proyecto)
cd /d "%~dp0"

echo [1/3] Construyendo imagen Admin...
podman build -t localhost/odoo-saas-admin:latest -f admin/Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Fallo al construir imagen Admin
    exit /b 1
)
echo OK - Admin construido

echo.
echo [2/3] Construyendo imagen Portal...
podman build -t localhost/odoo-saas-portal:latest -f portal/Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Fallo al construir imagen Portal
    exit /b 1
)
echo OK - Portal construido

echo.
echo [3/3] Construyendo imagen Worker...
podman build -t localhost/odoo-saas-worker:latest -f workers/Dockerfile .
if %errorlevel% neq 0 (
    echo ERROR: Fallo al construir imagen Worker
    exit /b 1
)
echo OK - Worker construido

echo.
echo ========================================
echo EXITO: Todas las imagenes construidas!
echo ========================================
echo.
echo Ahora ejecuta: podman-dev.cmd up-no-build
echo.
