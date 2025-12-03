@echo off
REM ============================================================================
REM Odoo SaaS Platform - Script de Desarrollo con Podman para Windows
REM ============================================================================
REM Script helper para facilitar el desarrollo con Podman en Windows

setlocal enabledelayedexpansion

REM Colores (si tu terminal los soporta)
set "GREEN=[32m"
set "YELLOW=[33m"
set "RED=[31m"
set "BLUE=[34m"
set "NC=[0m"

REM Variables - IMPORTANTE: Usa el archivo docker-compose.podman.yml
set "PODMAN_COMPOSE=podman-compose -f docker-compose.podman.yml"

REM Verificar si podman-compose está instalado
where podman-compose >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%Error: podman-compose no está instalado%NC%
    echo Por favor instala podman-compose con: pip install podman-compose
    exit /b 1
)

REM Procesar comando
if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="init" goto :init
if "%1"=="build" goto :build
if "%1"=="up" goto :up
if "%1"=="up-no-build" goto :up_no_build
if "%1"=="down" goto :down
if "%1"=="restart" goto :restart
if "%1"=="logs" goto :logs
if "%1"=="status" goto :status
if "%1"=="db-init" goto :db_init
if "%1"=="db-reset" goto :db_reset
if "%1"=="clean" goto :clean
if "%1"=="shell" goto :shell
goto :unknown

:help
echo.
echo %BLUE%Odoo SaaS Platform - Comandos Disponibles%NC%
echo %YELLOW%=============================================%NC%
echo.
echo   %GREEN%init%NC%         - Inicializar entorno (crear .env)
echo   %GREEN%build%NC%        - Construir imagenes manualmente
echo   %GREEN%up%NC%           - Construir + Iniciar servicios
echo   %GREEN%up-no-build%NC%  - Iniciar sin construir
echo   %GREEN%down%NC%         - Detener servicios
echo   %GREEN%restart%NC%      - Reiniciar servicios
echo   %GREEN%logs%NC%         - Ver logs (opcional: admin, portal, worker)
echo   %GREEN%status%NC%       - Ver estado de servicios
echo   %GREEN%db-init%NC%      - Inicializar base de datos
echo   %GREEN%db-reset%NC%     - Resetear base de datos (PELIGRO)
echo   %GREEN%clean%NC%        - Limpiar recursos
echo   %GREEN%shell%NC%        - Abrir shell (admin, portal, postgres, redis)
echo.
echo %YELLOW%Ejemplos de uso:%NC%
echo   podman-dev.cmd init
echo   podman-dev.cmd up
echo   podman-dev.cmd logs admin
echo   podman-dev.cmd shell postgres
echo.
goto :eof

:init
echo.
echo %YELLOW%Inicializando entorno de desarrollo...%NC%
if exist .env (
    echo %RED%Advertencia: .env ya existe. Renombrando a .env.backup%NC%
    move /y .env .env.backup
)
copy .env.example .env
echo.
echo %GREEN%Archivo .env creado!%NC%
echo %BLUE%Por favor edita .env con tus configuraciones antes de ejecutar 'up'%NC%
echo.
goto :eof

:build
echo.
echo %YELLOW%Construyendo imagenes...%NC%
call build-images.cmd
if %errorlevel% equ 0 (
    echo %GREEN%Imagenes construidas correctamente!%NC%
) else (
    echo %RED%Error al construir imagenes%NC%
    exit /b 1
)
goto :eof

:up
echo.
echo %YELLOW%Paso 1: Construyendo imagenes...%NC%
call build-images.cmd
if %errorlevel% neq 0 (
    echo %RED%Error al construir imagenes%NC%
    exit /b 1
)
echo.
echo %YELLOW%Paso 2: Iniciando servicios con Podman...%NC%
%PODMAN_COMPOSE% up -d
if %errorlevel% equ 0 (
    echo.
    echo %GREEN%Servicios iniciados correctamente!%NC%
    echo.
    echo %BLUE%Accede a los servicios en:%NC%
    echo   Admin Dashboard: http://localhost:5000
    echo   Customer Portal: http://localhost:5001
    echo   Grafana:         http://localhost:3100
    echo   Prometheus:      http://localhost:9091
    echo   RQ Dashboard:    http://localhost:9182
    echo   Nginx:           http://localhost:8082
    echo   Adminer:         http://localhost:8085
    echo.
    echo %YELLOW%No olvides inicializar la base de datos:%NC%
    echo   podman-dev.cmd db-init
    echo.
) else (
    echo %RED%Error al iniciar servicios%NC%
)
goto :eof

:up_no_build
echo.
echo %YELLOW%Iniciando servicios (sin build)...%NC%
%PODMAN_COMPOSE% up -d
if %errorlevel% equ 0 (
    echo %GREEN%Servicios iniciados!%NC%
) else (
    echo %RED%Error al iniciar servicios%NC%
)
goto :eof

:down
echo.
echo %YELLOW%Deteniendo servicios...%NC%
%PODMAN_COMPOSE% down
echo %GREEN%Servicios detenidos%NC%
echo.
goto :eof

:restart
echo.
echo %YELLOW%Reiniciando servicios...%NC%
if not "%2"=="" (
    %PODMAN_COMPOSE% restart %2
    echo %GREEN%Servicio %2 reiniciado%NC%
) else (
    %PODMAN_COMPOSE% restart
    echo %GREEN%Todos los servicios reiniciados%NC%
)
echo.
goto :eof

:logs
echo.
if not "%2"=="" (
    echo %YELLOW%Ver logs de %2...%NC%
    %PODMAN_COMPOSE% logs -f %2
) else (
    echo %YELLOW%Ver logs de todos los servicios...%NC%
    %PODMAN_COMPOSE% logs -f
)
goto :eof

:status
echo.
echo %YELLOW%Estado de los servicios:%NC%
%PODMAN_COMPOSE% ps
echo.
goto :eof

:db_init
echo.
echo %YELLOW%Inicializando base de datos...%NC%
echo Ejecutando migraciones...
%PODMAN_COMPOSE% exec admin alembic upgrade head
if %errorlevel% equ 0 (
    echo %GREEN%Migraciones completadas%NC%
    echo.
    echo %YELLOW%Poblando datos de demostración...%NC%
    %PODMAN_COMPOSE% exec admin python admin/app.py seed-db
    %PODMAN_COMPOSE% exec portal python portal/run.py seed-db
    echo.
    echo %GREEN%Base de datos inicializada correctamente!%NC%
    echo.
    echo %BLUE%Credenciales de acceso:%NC%
    echo   Admin: admin@example.com / admin123
    echo   Demo:  demo@example.com / demo123
    echo.
) else (
    echo %RED%Error al ejecutar migraciones%NC%
)
goto :eof

:db_reset
echo.
echo %RED%ADVERTENCIA: Esto eliminará TODOS los datos de la base de datos!%NC%
set /p confirm="¿Estás seguro? (S/N): "
if /i "%confirm%"=="S" (
    echo %YELLOW%Reseteando base de datos...%NC%
    %PODMAN_COMPOSE% exec postgres psql -U odoo -c "DROP DATABASE IF EXISTS odoo_saas_platform;"
    %PODMAN_COMPOSE% exec postgres psql -U odoo -c "CREATE DATABASE odoo_saas_platform;"
    call :db_init
    echo %GREEN%Base de datos reseteada!%NC%
) else (
    echo %YELLOW%Operación cancelada%NC%
)
echo.
goto :eof

:clean
echo.
echo %YELLOW%Limpiando recursos de Podman...%NC%
%PODMAN_COMPOSE% down -v
podman system prune -f
podman volume prune -f
echo %GREEN%Limpieza completada%NC%
echo.
goto :eof

:shell
if "%2"=="" (
    echo %RED%Error: Especifica el servicio (admin, portal, postgres, redis)%NC%
    echo Ejemplo: podman-dev.cmd shell admin
    goto :eof
)
echo.
echo %YELLOW%Abriendo shell en %2...%NC%

if "%2"=="postgres" (
    %PODMAN_COMPOSE% exec postgres psql -U odoo -d odoo_saas_platform
) else if "%2"=="redis" (
    %PODMAN_COMPOSE% exec redis redis-cli -a redis123
) else (
    %PODMAN_COMPOSE% exec %2 bash
)
goto :eof

:unknown
echo.
echo %RED%Comando desconocido: %1%NC%
echo Usa 'podman-dev.cmd help' para ver comandos disponibles
echo.
goto :eof

:eof
endlocal
