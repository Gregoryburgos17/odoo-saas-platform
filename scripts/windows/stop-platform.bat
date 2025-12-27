@echo off
REM =============================================================================
REM Odoo SaaS Platform - Detener Plataforma
REM =============================================================================

echo.
echo =============================================================================
echo   Odoo SaaS Platform - Deteniendo Servicios
echo =============================================================================
echo.

cd /d "%~dp0..\.."

echo Deteniendo servicios...
podman-compose -f podman-compose.windows.yml down

echo.
echo [OK] Servicios detenidos
echo.
echo Para iniciar nuevamente: scripts\windows\quick-start.bat
echo.

pause
