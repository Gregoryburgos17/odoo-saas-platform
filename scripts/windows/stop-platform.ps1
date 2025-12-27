# =============================================================================
# Odoo SaaS Platform - Script de Parada para Windows
# =============================================================================
# Detiene todos los servicios de la plataforma
#
# Uso:
#   .\stop-platform.ps1           # Detener servicios
#   .\stop-platform.ps1 -Volumes  # Detener y eliminar volumenes
#   .\stop-platform.ps1 -All      # Detener todo y limpiar imagenes
# =============================================================================

param(
    [switch]$Volumes,
    [switch]$All,
    [switch]$StopMachine,
    [switch]$Help
)

$ErrorActionPreference = "Continue"

function Write-Header {
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host "  Odoo SaaS Platform - Deteniendo Servicios" -ForegroundColor Cyan
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

function Write-Info($message) {
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $message -ForegroundColor White
}

function Write-Warning($message) {
    Write-Host "[AVISO] " -ForegroundColor Yellow -NoNewline
    Write-Host $message -ForegroundColor White
}

# Mostrar ayuda
if ($Help) {
    Write-Header
    Write-Host "Uso: .\stop-platform.ps1 [opciones]"
    Write-Host ""
    Write-Host "Opciones:"
    Write-Host "  -Volumes      Eliminar volumenes (BORRA DATOS)"
    Write-Host "  -All          Eliminar todo (contenedores, volumenes, imagenes)"
    Write-Host "  -StopMachine  Detener la maquina Podman al finalizar"
    Write-Host "  -Help         Mostrar esta ayuda"
    Write-Host ""
    Write-Host "ADVERTENCIA: -Volumes y -All eliminaran todos los datos!" -ForegroundColor Red
    Write-Host ""
    exit 0
}

Write-Header

# Obtener directorio del proyecto
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composeFile = Join-Path $projectRoot "podman-compose.windows.yml"

# Verificar que existe el archivo compose
if (-not (Test-Path $composeFile)) {
    Write-Warning "No se encontro podman-compose.windows.yml"
    Write-Info "Intentando detener contenedores directamente..."
}

# Cambiar al directorio del proyecto
Push-Location $projectRoot

try {
    # -------------------------------------------------------------------------
    # Confirmar eliminacion de datos si se solicita
    # -------------------------------------------------------------------------
    if ($Volumes -or $All) {
        Write-Host ""
        Write-Warning "ESTA OPERACION ELIMINARA TODOS LOS DATOS!"
        Write-Host ""
        Write-Host "Datos que se perderan:" -ForegroundColor Red
        Write-Host "  - Base de datos PostgreSQL (usuarios, configuracion, etc.)" -ForegroundColor White
        Write-Host "  - Cache de Redis" -ForegroundColor White
        if ($All) {
            Write-Host "  - Imagenes construidas" -ForegroundColor White
        }
        Write-Host ""

        $response = Read-Host "Esta seguro que desea continuar? (escriba 'SI' para confirmar)"
        if ($response -ne "SI") {
            Write-Info "Operacion cancelada"
            exit 0
        }
        Write-Host ""
    }

    # -------------------------------------------------------------------------
    # PASO 1: Detener servicios
    # -------------------------------------------------------------------------
    $totalSteps = 2
    if ($Volumes -or $All) { $totalSteps++ }
    if ($All) { $totalSteps++ }
    if ($StopMachine) { $totalSteps++ }

    $currentStep = 1

    Write-Step "$currentStep/$totalSteps" "Deteniendo servicios..."
    Write-Host ""

    if (Test-Path $composeFile) {
        $downArgs = @("-f", $composeFile, "down")

        if ($Volumes -or $All) {
            $downArgs += "-v"
        }

        podman-compose @downArgs
    }
    else {
        # Fallback: detener contenedores individualmente
        $containers = @(
            "odoo-saas-admin",
            "odoo-saas-portal",
            "odoo-saas-worker",
            "odoo-saas-rq-dashboard",
            "odoo-saas-adminer",
            "odoo-saas-prometheus",
            "odoo-saas-grafana",
            "odoo-saas-redis",
            "odoo-saas-postgres"
        )

        foreach ($container in $containers) {
            try {
                podman stop $container 2>&1 | Out-Null
                podman rm $container 2>&1 | Out-Null
                Write-Info "Contenedor $container detenido"
            }
            catch {
                # Ignorar si el contenedor no existe
            }
        }
    }

    Write-Host ""
    Write-Success "Servicios detenidos"
    $currentStep++

    # -------------------------------------------------------------------------
    # PASO 2: Eliminar volumenes (si se solicita)
    # -------------------------------------------------------------------------
    if ($Volumes -or $All) {
        Write-Step "$currentStep/$totalSteps" "Eliminando volumenes..."

        $volumes = @(
            "postgres_data",
            "redis_data",
            "prometheus_data",
            "grafana_data"
        )

        foreach ($vol in $volumes) {
            try {
                # Buscar volumenes con diferentes prefijos
                $fullVolNames = podman volume ls --format "{{.Name}}" | Where-Object { $_ -like "*$vol*" }
                foreach ($fullVol in $fullVolNames) {
                    podman volume rm $fullVol 2>&1 | Out-Null
                    Write-Info "Volumen $fullVol eliminado"
                }
            }
            catch {
                # Ignorar si no existe
            }
        }

        Write-Success "Volumenes eliminados"
        $currentStep++
    }

    # -------------------------------------------------------------------------
    # PASO 3: Eliminar imagenes (si -All)
    # -------------------------------------------------------------------------
    if ($All) {
        Write-Step "$currentStep/$totalSteps" "Eliminando imagenes construidas..."

        $images = @(
            "localhost/odoo-saas-admin",
            "localhost/odoo-saas-portal",
            "localhost/odoo-saas-worker"
        )

        foreach ($img in $images) {
            try {
                podman rmi $img 2>&1 | Out-Null
                Write-Info "Imagen $img eliminada"
            }
            catch {
                # Ignorar si no existe
            }
        }

        Write-Success "Imagenes eliminadas"
        $currentStep++
    }

    # -------------------------------------------------------------------------
    # PASO 4: Detener maquina Podman (si se solicita)
    # -------------------------------------------------------------------------
    if ($StopMachine) {
        Write-Step "$currentStep/$totalSteps" "Deteniendo maquina Podman..."

        try {
            podman machine stop 2>&1 | Out-Null
            Write-Success "Maquina Podman detenida"
        }
        catch {
            Write-Warning "No se pudo detener la maquina Podman"
        }
        $currentStep++
    }

    # -------------------------------------------------------------------------
    # Mostrar estado final
    # -------------------------------------------------------------------------
    Write-Step "$currentStep/$totalSteps" "Verificando estado..."
    Write-Host ""

    Write-Host "=============================================================================" -ForegroundColor Green
    Write-Host "  PLATAFORMA DETENIDA" -ForegroundColor Green
    Write-Host "=============================================================================" -ForegroundColor Green
    Write-Host ""

    # Mostrar contenedores restantes (si hay)
    $remainingContainers = podman ps -a --format "{{.Names}}" 2>&1 | Where-Object { $_ -like "odoo-saas-*" }
    if ($remainingContainers) {
        Write-Warning "Contenedores restantes:"
        foreach ($c in $remainingContainers) {
            Write-Host "  - $c" -ForegroundColor Yellow
        }
        Write-Host ""
    }

    Write-Host "Para iniciar nuevamente:" -ForegroundColor Cyan
    Write-Host "  .\scripts\windows\start-platform.ps1" -ForegroundColor Gray
    Write-Host ""

    if ($Volumes -or $All) {
        Write-Host "Nota: Los datos han sido eliminados. La proxima vez que inicie" -ForegroundColor Yellow
        Write-Host "      se creara una nueva base de datos vacia." -ForegroundColor Yellow
        Write-Host ""
    }
}
finally {
    Pop-Location
}
