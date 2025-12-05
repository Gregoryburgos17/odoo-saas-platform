@echo off
REM ============================================================================
REM Build Script for Odoo SaaS Platform (Podman on Windows)
REM ============================================================================
echo.
echo ====================================
echo Building Odoo SaaS Platform Images
echo ====================================
echo.

REM Change to project directory
cd /d %~dp0

REM Build Admin Dashboard
echo [1/3] Building Admin Dashboard...
podman build -t localhost/odoo-saas-admin:latest -f admin/Dockerfile .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build Admin Dashboard
    pause
    exit /b 1
)
echo Admin Dashboard built successfully!
echo.

REM Build Customer Portal
echo [2/3] Building Customer Portal...
podman build -t localhost/odoo-saas-portal:latest -f portal/Dockerfile .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build Customer Portal
    pause
    exit /b 1
)
echo Customer Portal built successfully!
echo.

REM Build Worker
echo [3/3] Building Worker...
podman build -t localhost/odoo-saas-worker:latest -f workers/Dockerfile .
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to build Worker
    pause
    exit /b 1
)
echo Worker built successfully!
echo.

echo ====================================
echo All images built successfully!
echo ====================================
echo.
echo Now run: podman-compose -f docker-compose.podman.yml up -d
echo.
pause
