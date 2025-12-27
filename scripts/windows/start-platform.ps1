# =============================================================================
# Odoo SaaS Platform - Script de Inicio para Windows
# =============================================================================
# Inicia todos los servicios de la plataforma usando Podman
#
# Uso:
#   .\start-platform.ps1              # Iniciar servicios basicos
#   .\start-platform.ps1 -Build       # Reconstruir imagenes
#   .\start-platform.ps1 -Monitoring  # Incluir Prometheus/Grafana
#   .\start-platform.ps1 -Logs        # Mostrar logs despues de iniciar
# =============================================================================

param(
    [switch]$Build,
    [switch]$Monitoring,
    [switch]$Logs,
    [switch]$Force,
    [switch]$Help
)

$ErrorActionPreference = "Continue"

function Write-Header {
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host "  Odoo SaaS Platform - Iniciando Servicios" -ForegroundColor Cyan
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($step, $message) {
    Write-Host "[$step] " -ForegroundColor Yellow -NoNewline
    Write-Host $message -ForegroundColor White
}

function Write-Success($message) {
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $message -ForegroundColor White
}

function Write-Error($message) {
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $message -ForegroundColor White
}

function Write-Info($message) {
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $message -ForegroundColor White
}

# Mostrar ayuda
if ($Help) {
    Write-Header
    Write-Host "Uso: .\start-platform.ps1 [opciones]"
    Write-Host ""
    Write-Host "Opciones:"
    Write-Host "  -Build       Reconstruir imagenes antes de iniciar"
    Write-Host "  -Monitoring  Incluir servicios de monitoreo (Prometheus/Grafana)"
    Write-Host "  -Logs        Mostrar logs despues de iniciar"
    Write-Host "  -Force       Forzar recreacion de contenedores"
    Write-Host "  -Help        Mostrar esta ayuda"
    Write-Host ""
    exit 0
}

Write-Header

# Obtener directorio del proyecto
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composeFile = Join-Path $projectRoot "podman-compose.windows.yml"

# Verificar que existe el archivo compose
if (-not (Test-Path $composeFile)) {
    Write-Error "No se encontro podman-compose.windows.yml en $projectRoot"
    exit 1
}

# Cambiar al directorio del proyecto
Push-Location $projectRoot

try {
    # -------------------------------------------------------------------------
    # PASO 1: Verificar maquina Podman
    # -------------------------------------------------------------------------
    Write-Step "1/5" "Verificando maquina Podman..."

    try {
        $machineList = podman machine list --format json 2>&1 | ConvertFrom-Json
        $runningMachine = $machineList | Where-Object { $_.Running -eq $true }

        if (-not $runningMachine) {
            Write-Info "Iniciando maquina Podman..."
            podman machine start 2>&1 | Out-Null
            Start-Sleep -Seconds 5
            Write-Success "Maquina Podman iniciada"
        }
        else {
            Write-Success "Maquina Podman activa: $($runningMachine.Name)"
        }
    }
    catch {
        Write-Error "No se pudo verificar la maquina Podman"
        Write-Host "Ejecute: podman machine start" -ForegroundColor Yellow
        exit 1
    }

    # -------------------------------------------------------------------------
    # PASO 2: Verificar archivo .env
    # -------------------------------------------------------------------------
    Write-Step "2/5" "Verificando configuracion..."

    $envFile = Join-Path $projectRoot ".env"
    if (-not (Test-Path $envFile)) {
        $envWindowsFile = Join-Path $projectRoot ".env.windows"
        if (Test-Path $envWindowsFile) {
            Copy-Item $envWindowsFile $envFile
            Write-Success "Archivo .env creado desde .env.windows"
        }
        else {
            Write-Error "No se encontro archivo .env ni .env.windows"
            exit 1
        }
    }
    else {
        Write-Success "Archivo .env encontrado"
    }

    # -------------------------------------------------------------------------
    # PASO 3: Construir imagenes (si se solicita)
    # -------------------------------------------------------------------------
    if ($Build) {
        Write-Step "3/5" "Construyendo imagenes..."
        Write-Host ""

        podman-compose -f $composeFile build
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Error al construir imagenes"
            exit 1
        }
        Write-Success "Imagenes construidas correctamente"
    }
    else {
        Write-Step "3/5" "Omitiendo construccion de imagenes (use -Build para construir)"
    }

    # -------------------------------------------------------------------------
    # PASO 4: Iniciar servicios
    # -------------------------------------------------------------------------
    Write-Step "4/5" "Iniciando servicios..."
    Write-Host ""

    $upArgs = @("-f", $composeFile, "up", "-d")

    if ($Force) {
        $upArgs += "--force-recreate"
    }

    if ($Monitoring) {
        $upArgs += "--profile"
        $upArgs += "monitoring"
    }

    podman-compose @upArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error al iniciar servicios"
        exit 1
    }

    Write-Host ""
    Write-Success "Servicios iniciados correctamente"

    # -------------------------------------------------------------------------
    # PASO 5: Esperar a que los servicios esten listos
    # -------------------------------------------------------------------------
    Write-Step "5/5" "Esperando a que los servicios esten listos..."

    $maxWait = 60
    $waited = 0
    $services = @(
        @{Name="PostgreSQL"; Url=$null; Container="odoo-saas-postgres"},
        @{Name="Redis"; Url=$null; Container="odoo-saas-redis"},
        @{Name="Admin"; Url="http://localhost:5000/health"; Container="odoo-saas-admin"},
        @{Name="Portal"; Url="http://localhost:5001/health"; Container="odoo-saas-portal"}
    )

    # Esperar un poco para que los contenedores arranquen
    Start-Sleep -Seconds 5

    Write-Host ""

    foreach ($service in $services) {
        Write-Host "  Verificando $($service.Name)... " -NoNewline

        $ready = $false
        $attempts = 0
        $maxAttempts = 12

        while (-not $ready -and $attempts -lt $maxAttempts) {
            try {
                if ($service.Url) {
                    $response = Invoke-WebRequest -Uri $service.Url -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
                    if ($response.StatusCode -eq 200) {
                        $ready = $true
                    }
                }
                else {
                    # Para servicios sin endpoint HTTP, verificar que el contenedor este corriendo
                    $status = podman inspect --format '{{.State.Running}}' $service.Container 2>&1
                    if ($status -eq "true") {
                        $ready = $true
                    }
                }
            }
            catch {
                # Ignorar errores y reintentar
            }

            if (-not $ready) {
                $attempts++
                Start-Sleep -Seconds 5
            }
        }

        if ($ready) {
            Write-Host "[OK]" -ForegroundColor Green
        }
        else {
            Write-Host "[ESPERANDO]" -ForegroundColor Yellow
        }
    }

    # -------------------------------------------------------------------------
    # Mostrar resumen
    # -------------------------------------------------------------------------
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Green
    Write-Host "  PLATAFORMA INICIADA" -ForegroundColor Green
    Write-Host "=============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "URLs de acceso:" -ForegroundColor Cyan
    Write-Host "  - Admin Dashboard:  " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:5000" -ForegroundColor Yellow
    Write-Host "  - Portal Cliente:   " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:5001" -ForegroundColor Yellow
    Write-Host "  - RQ Dashboard:     " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:9181" -ForegroundColor Yellow
    Write-Host "  - Adminer (DB):     " -NoNewline -ForegroundColor White
    Write-Host "http://localhost:8085" -ForegroundColor Yellow

    if ($Monitoring) {
        Write-Host "  - Prometheus:       " -NoNewline -ForegroundColor White
        Write-Host "http://localhost:9090" -ForegroundColor Yellow
        Write-Host "  - Grafana:          " -NoNewline -ForegroundColor White
        Write-Host "http://localhost:3000" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Credenciales de Adminer:" -ForegroundColor Cyan
    Write-Host "  - Sistema:   PostgreSQL" -ForegroundColor White
    Write-Host "  - Servidor:  postgres" -ForegroundColor White
    Write-Host "  - Usuario:   odoo" -ForegroundColor White
    Write-Host "  - Password:  odoo_dev_2024" -ForegroundColor White
    Write-Host "  - Base:      odoo_saas_platform" -ForegroundColor White
    Write-Host ""
    Write-Host "Comandos utiles:" -ForegroundColor Cyan
    Write-Host "  Ver logs:      podman-compose -f podman-compose.windows.yml logs -f" -ForegroundColor Gray
    Write-Host "  Detener:       .\scripts\windows\stop-platform.ps1" -ForegroundColor Gray
    Write-Host "  Estado:        podman-compose -f podman-compose.windows.yml ps" -ForegroundColor Gray
    Write-Host ""

    # Mostrar logs si se solicita
    if ($Logs) {
        Write-Host "Mostrando logs (Ctrl+C para salir)..." -ForegroundColor Cyan
        Write-Host ""
        podman-compose -f $composeFile logs -f
    }
}
finally {
    Pop-Location
}
