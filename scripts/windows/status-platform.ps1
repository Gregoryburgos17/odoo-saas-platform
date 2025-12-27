# =============================================================================
# Odoo SaaS Platform - Script de Estado para Windows
# =============================================================================
# Muestra el estado de todos los servicios de la plataforma
#
# Uso:
#   .\status-platform.ps1
# =============================================================================

param(
    [switch]$Detailed,
    [switch]$Help
)

function Write-Header {
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host "  Odoo SaaS Platform - Estado de Servicios" -ForegroundColor Cyan
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Mostrar ayuda
if ($Help) {
    Write-Header
    Write-Host "Uso: .\status-platform.ps1 [opciones]"
    Write-Host ""
    Write-Host "Opciones:"
    Write-Host "  -Detailed    Mostrar informacion detallada de cada servicio"
    Write-Host "  -Help        Mostrar esta ayuda"
    Write-Host ""
    exit 0
}

Write-Header

# Obtener directorio del proyecto
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composeFile = Join-Path $projectRoot "podman-compose.windows.yml"

# Servicios a verificar
$services = @(
    @{Name="PostgreSQL"; Container="odoo-saas-postgres"; Port=5432; HealthUrl=$null},
    @{Name="Redis"; Container="odoo-saas-redis"; Port=6379; HealthUrl=$null},
    @{Name="Admin Dashboard"; Container="odoo-saas-admin"; Port=5000; HealthUrl="http://localhost:5000/health"},
    @{Name="Portal Cliente"; Container="odoo-saas-portal"; Port=5001; HealthUrl="http://localhost:5001/health"},
    @{Name="Worker"; Container="odoo-saas-worker"; Port=$null; HealthUrl=$null},
    @{Name="RQ Dashboard"; Container="odoo-saas-rq-dashboard"; Port=9181; HealthUrl=$null},
    @{Name="Adminer"; Container="odoo-saas-adminer"; Port=8085; HealthUrl=$null},
    @{Name="Prometheus"; Container="odoo-saas-prometheus"; Port=9090; HealthUrl=$null},
    @{Name="Grafana"; Container="odoo-saas-grafana"; Port=3000; HealthUrl=$null}
)

# -------------------------------------------------------------------------
# Verificar maquina Podman
# -------------------------------------------------------------------------
Write-Host "Maquina Podman:" -ForegroundColor Cyan
try {
    $machineList = podman machine list --format json 2>&1 | ConvertFrom-Json
    $runningMachine = $machineList | Where-Object { $_.Running -eq $true }

    if ($runningMachine) {
        Write-Host "  Estado:  " -NoNewline -ForegroundColor White
        Write-Host "EJECUTANDO" -ForegroundColor Green
        Write-Host "  Nombre:  $($runningMachine.Name)" -ForegroundColor White
        Write-Host "  CPUs:    $($runningMachine.CPUs)" -ForegroundColor White
        Write-Host "  Memoria: $($runningMachine.Memory)" -ForegroundColor White
    }
    else {
        Write-Host "  Estado:  " -NoNewline -ForegroundColor White
        Write-Host "DETENIDA" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Ejecute: podman machine start" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Host "  Estado:  " -NoNewline -ForegroundColor White
    Write-Host "ERROR" -ForegroundColor Red
    Write-Host "  No se pudo obtener el estado de la maquina Podman" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# -------------------------------------------------------------------------
# Verificar servicios
# -------------------------------------------------------------------------
Write-Host "Servicios:" -ForegroundColor Cyan
Write-Host ""
Write-Host ("  {0,-20} {1,-12} {2,-8} {3}" -f "SERVICIO", "ESTADO", "PUERTO", "HEALTH") -ForegroundColor Gray
Write-Host ("  " + "-" * 60) -ForegroundColor Gray

$runningCount = 0
$totalCount = $services.Count

foreach ($service in $services) {
    $status = "DETENIDO"
    $statusColor = "Red"
    $health = "-"
    $healthColor = "Gray"

    try {
        $containerStatus = podman inspect --format '{{.State.Status}}' $service.Container 2>&1
        if ($containerStatus -eq "running") {
            $status = "EJECUTANDO"
            $statusColor = "Green"
            $runningCount++

            # Verificar health endpoint si existe
            if ($service.HealthUrl) {
                try {
                    $response = Invoke-WebRequest -Uri $service.HealthUrl -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
                    if ($response.StatusCode -eq 200) {
                        $health = "OK"
                        $healthColor = "Green"
                    }
                    else {
                        $health = "WARN"
                        $healthColor = "Yellow"
                    }
                }
                catch {
                    $health = "FAIL"
                    $healthColor = "Red"
                }
            }
        }
        elseif ($containerStatus -eq "exited") {
            $status = "DETENIDO"
            $statusColor = "Red"
        }
        elseif ($containerStatus -eq "created") {
            $status = "CREADO"
            $statusColor = "Yellow"
        }
    }
    catch {
        $status = "NO EXISTE"
        $statusColor = "Gray"
    }

    $portStr = if ($service.Port) { $service.Port.ToString() } else { "-" }

    Write-Host ("  {0,-20} " -f $service.Name) -NoNewline -ForegroundColor White
    Write-Host ("{0,-12} " -f $status) -NoNewline -ForegroundColor $statusColor
    Write-Host ("{0,-8} " -f $portStr) -NoNewline -ForegroundColor White
    Write-Host $health -ForegroundColor $healthColor
}

Write-Host ""
Write-Host ("  Ejecutando: {0}/{1}" -f $runningCount, $totalCount) -ForegroundColor White
Write-Host ""

# -------------------------------------------------------------------------
# Mostrar detalles si se solicita
# -------------------------------------------------------------------------
if ($Detailed) {
    Write-Host "Detalles de contenedores:" -ForegroundColor Cyan
    Write-Host ""

    foreach ($service in $services) {
        try {
            $info = podman inspect $service.Container 2>&1 | ConvertFrom-Json

            if ($info) {
                Write-Host "  $($service.Name):" -ForegroundColor Yellow
                Write-Host "    ID:      $($info.Id.Substring(0, 12))" -ForegroundColor White
                Write-Host "    Imagen:  $($info.ImageName)" -ForegroundColor White
                Write-Host "    Creado:  $($info.Created)" -ForegroundColor White
                Write-Host "    Estado:  $($info.State.Status)" -ForegroundColor White

                if ($info.State.Health) {
                    Write-Host "    Health:  $($info.State.Health.Status)" -ForegroundColor White
                }

                Write-Host ""
            }
        }
        catch {
            # Ignorar contenedores que no existen
        }
    }
}

# -------------------------------------------------------------------------
# Mostrar volumenes
# -------------------------------------------------------------------------
Write-Host "Volumenes:" -ForegroundColor Cyan
$volumes = podman volume ls --format "{{.Name}}" 2>&1 | Where-Object { $_ -like "*odoo*" -or $_ -like "*postgres*" -or $_ -like "*redis*" -or $_ -like "*grafana*" -or $_ -like "*prometheus*" }

if ($volumes) {
    foreach ($vol in $volumes) {
        Write-Host "  - $vol" -ForegroundColor White
    }
}
else {
    Write-Host "  (ninguno)" -ForegroundColor Gray
}
Write-Host ""

# -------------------------------------------------------------------------
# URLs de acceso
# -------------------------------------------------------------------------
if ($runningCount -gt 0) {
    Write-Host "URLs de acceso:" -ForegroundColor Cyan
    Write-Host "  Admin Dashboard:  http://localhost:5000" -ForegroundColor White
    Write-Host "  Portal Cliente:   http://localhost:5001" -ForegroundColor White
    Write-Host "  RQ Dashboard:     http://localhost:9181" -ForegroundColor White
    Write-Host "  Adminer (DB):     http://localhost:8085" -ForegroundColor White
    Write-Host ""
}

# -------------------------------------------------------------------------
# Comandos utiles
# -------------------------------------------------------------------------
Write-Host "Comandos utiles:" -ForegroundColor Cyan
Write-Host "  Ver logs:    podman-compose -f podman-compose.windows.yml logs -f [servicio]" -ForegroundColor Gray
Write-Host "  Reiniciar:   podman-compose -f podman-compose.windows.yml restart [servicio]" -ForegroundColor Gray
Write-Host "  Shell:       podman exec -it odoo-saas-admin /bin/bash" -ForegroundColor Gray
Write-Host ""
