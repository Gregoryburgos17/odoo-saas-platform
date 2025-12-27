@echo off
REM =============================================================================
REM Odoo SaaS Platform - Inicio Rapido para Windows
REM =============================================================================
REM Este script inicia la plataforma con un solo click
REM =============================================================================

echo.
echo =============================================================================
echo   Odoo SaaS Platform - Inicio Rapido
echo =============================================================================
echo.

REM Verificar que podman esta disponible
podman --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Podman no esta instalado o no esta en el PATH
    echo.
    echo Por favor, instale Podman Desktop desde:
    echo   https://podman-desktop.io/downloads
    echo.
    pause
    exit /b 1
)

REM Verificar que la maquina esta corriendo
echo [1/4] Verificando maquina Podman...
podman machine list | findstr /C:"Currently running" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Iniciando maquina Podman...
    podman machine start
    timeout /t 10 /nobreak >nul
)
echo       [OK] Maquina Podman activa

REM Navegar al directorio del proyecto
cd /d "%~dp0..\.."

REM Verificar archivo .env
echo [2/4] Verificando configuracion...
if not exist ".env" (
    if exist ".env.windows" (
        copy ".env.windows" ".env" >nul
        echo       [OK] Archivo .env creado
    ) else (
        echo       [AVISO] No se encontro .env.windows
    )
) else (
    echo       [OK] Archivo .env existe
)

REM Construir imagenes si es la primera vez
echo [3/4] Verificando imagenes...
podman images | findstr /C:"odoo-saas-admin" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Construyendo imagenes (primera vez, puede tardar varios minutos)...
    podman-compose -f podman-compose.windows.yml build
    if %errorlevel% neq 0 (
        echo       [ERROR] Error al construir imagenes
        pause
        exit /b 1
    )
)
echo       [OK] Imagenes listas

REM Iniciar servicios
echo [4/4] Iniciando servicios...
podman-compose -f podman-compose.windows.yml up -d
if %errorlevel% neq 0 (
    echo       [ERROR] Error al iniciar servicios
    pause
    exit /b 1
)

echo.
echo =============================================================================
echo   PLATAFORMA INICIADA
echo =============================================================================
echo.
echo URLs de acceso:
echo   - Admin Dashboard:  http://localhost:5000
echo   - Portal Cliente:   http://localhost:5001
echo   - RQ Dashboard:     http://localhost:9181
echo   - Adminer (DB):     http://localhost:8085
echo.
echo Credenciales Adminer:
echo   Sistema:  PostgreSQL
echo   Servidor: postgres
echo   Usuario:  odoo
echo   Password: odoo_dev_2024
echo   Base:     odoo_saas_platform
echo.
echo Para detener: scripts\windows\stop-platform.bat
echo.

REM Abrir navegador
echo Abriendo Admin Dashboard en el navegador...
timeout /t 5 /nobreak >nul
start http://localhost:5000

pause
