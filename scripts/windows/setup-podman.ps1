# =============================================================================
# Odoo SaaS Platform - Script de Configuracion de Podman para Windows
# =============================================================================
# Este script configura Podman Desktop en Windows para ejecutar la plataforma
#
# Uso:
#   .\setup-podman.ps1
#
# Requisitos:
#   - Windows 10/11 con WSL2
#   - PowerShell 5.1 o superior
# =============================================================================

param(
    [switch]$SkipPodmanInstall,
    [switch]$SkipWSLCheck,
    [switch]$Help
)

# Colores para output
$Host.UI.RawUI.WindowTitle = "Odoo SaaS Platform - Setup"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Header {
    Write-Host ""
    Write-Host "=============================================================================" -ForegroundColor Cyan
    Write-Host "  Odoo SaaS Platform - Configuracion de Podman para Windows" -ForegroundColor Cyan
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

function Write-Warning($message) {
    Write-Host "[AVISO] " -ForegroundColor Yellow -NoNewline
    Write-Host $message -ForegroundColor White
}

function Write-Info($message) {
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $message -ForegroundColor White
}

# Mostrar ayuda
if ($Help) {
    Write-Header
    Write-Host "Uso: .\setup-podman.ps1 [opciones]"
    Write-Host ""
    Write-Host "Opciones:"
    Write-Host "  -SkipPodmanInstall   No instalar Podman (ya instalado)"
    Write-Host "  -SkipWSLCheck        No verificar WSL2"
    Write-Host "  -Help                Mostrar esta ayuda"
    Write-Host ""
    exit 0
}

Write-Header

# -----------------------------------------------------------------------------
# PASO 1: Verificar privilegios de administrador
# -----------------------------------------------------------------------------
Write-Step "1/7" "Verificando privilegios de administrador..."

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Warning "Este script requiere privilegios de administrador para algunas operaciones."
    Write-Warning "Algunas funciones pueden no estar disponibles."
}
else {
    Write-Success "Ejecutando con privilegios de administrador"
}

# -----------------------------------------------------------------------------
# PASO 2: Verificar WSL2
# -----------------------------------------------------------------------------
Write-Step "2/7" "Verificando WSL2..."

if (-not $SkipWSLCheck) {
    try {
        $wslStatus = wsl --status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "WSL2 esta instalado y funcionando"
        }
        else {
            Write-Error "WSL2 no esta instalado o configurado correctamente"
            Write-Host ""
            Write-Host "Para instalar WSL2, ejecute como Administrador:" -ForegroundColor Yellow
            Write-Host "  wsl --install" -ForegroundColor White
            Write-Host ""
            Write-Host "Luego reinicie su computadora y ejecute este script nuevamente."
            exit 1
        }
    }
    catch {
        Write-Error "No se pudo verificar WSL. Asegurese de tener WSL2 instalado."
        Write-Host "Para instalar: wsl --install" -ForegroundColor Yellow
        exit 1
    }
}
else {
    Write-Info "Verificacion de WSL omitida"
}

# -----------------------------------------------------------------------------
# PASO 3: Verificar/Instalar Podman
# -----------------------------------------------------------------------------
Write-Step "3/7" "Verificando Podman..."

$podmanInstalled = $false
try {
    $podmanVersion = podman --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $podmanInstalled = $true
        Write-Success "Podman encontrado: $podmanVersion"
    }
}
catch {
    $podmanInstalled = $false
}

if (-not $podmanInstalled -and -not $SkipPodmanInstall) {
    Write-Warning "Podman no esta instalado"
    Write-Host ""
    Write-Host "Opciones de instalacion:" -ForegroundColor Cyan
    Write-Host "1. Descargar Podman Desktop desde: https://podman-desktop.io/downloads" -ForegroundColor White
    Write-Host "2. Usar winget (si esta disponible):" -ForegroundColor White
    Write-Host "   winget install -e --id RedHat.Podman-Desktop" -ForegroundColor Gray
    Write-Host ""

    $response = Read-Host "Desea intentar instalar con winget? (S/N)"
    if ($response -eq "S" -or $response -eq "s") {
        try {
            Write-Info "Instalando Podman Desktop con winget..."
            winget install -e --id RedHat.Podman-Desktop
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Podman Desktop instalado correctamente"
                Write-Warning "Por favor, reinicie PowerShell y ejecute este script nuevamente"
                exit 0
            }
        }
        catch {
            Write-Error "No se pudo instalar con winget. Por favor, instale manualmente."
            exit 1
        }
    }
    else {
        Write-Info "Instalacion omitida. Por favor, instale Podman Desktop manualmente."
        exit 1
    }
}
elseif ($SkipPodmanInstall) {
    Write-Info "Verificacion de instalacion de Podman omitida"
}

# -----------------------------------------------------------------------------
# PASO 4: Verificar podman-compose
# -----------------------------------------------------------------------------
Write-Step "4/7" "Verificando podman-compose..."

$composeInstalled = $false
try {
    $composeVersion = podman-compose --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $composeInstalled = $true
        Write-Success "podman-compose encontrado: $composeVersion"
    }
}
catch {
    $composeInstalled = $false
}

if (-not $composeInstalled) {
    Write-Warning "podman-compose no esta instalado"
    Write-Info "Intentando instalar con pip..."

    try {
        pip install podman-compose
        if ($LASTEXITCODE -eq 0) {
            Write-Success "podman-compose instalado correctamente"
        }
        else {
            Write-Error "No se pudo instalar podman-compose"
            Write-Host "Intente manualmente: pip install podman-compose" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Error "pip no disponible. Instale Python y ejecute: pip install podman-compose"
    }
}

# -----------------------------------------------------------------------------
# PASO 5: Inicializar maquina Podman
# -----------------------------------------------------------------------------
Write-Step "5/7" "Verificando maquina Podman..."

try {
    $machineList = podman machine list --format json 2>&1 | ConvertFrom-Json
    $runningMachine = $machineList | Where-Object { $_.Running -eq $true }

    if ($runningMachine) {
        Write-Success "Maquina Podman activa: $($runningMachine.Name)"
    }
    else {
        Write-Warning "No hay maquina Podman ejecutandose"

        $defaultMachine = $machineList | Where-Object { $_.Name -eq "podman-machine-default" }

        if ($defaultMachine) {
            Write-Info "Iniciando maquina por defecto..."
            podman machine start
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Maquina Podman iniciada"
            }
        }
        else {
            Write-Info "Creando nueva maquina Podman..."
            podman machine init --cpus 4 --memory 4096 --disk-size 50
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Maquina creada"
                podman machine start
                Write-Success "Maquina iniciada"
            }
        }
    }
}
catch {
    Write-Error "Error al verificar maquina Podman: $_"
    Write-Host "Ejecute manualmente:" -ForegroundColor Yellow
    Write-Host "  podman machine init" -ForegroundColor White
    Write-Host "  podman machine start" -ForegroundColor White
}

# -----------------------------------------------------------------------------
# PASO 6: Configurar archivo .env
# -----------------------------------------------------------------------------
Write-Step "6/7" "Configurando archivo de entorno..."

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $projectRoot ".env"
$envWindowsFile = Join-Path $projectRoot ".env.windows"

if (Test-Path $envFile) {
    Write-Info "Archivo .env ya existe"
    $response = Read-Host "Desea sobrescribirlo con .env.windows? (S/N)"
    if ($response -eq "S" -or $response -eq "s") {
        Copy-Item $envWindowsFile $envFile -Force
        Write-Success "Archivo .env actualizado"
    }
}
else {
    if (Test-Path $envWindowsFile) {
        Copy-Item $envWindowsFile $envFile
        Write-Success "Archivo .env creado desde .env.windows"
    }
    else {
        Write-Warning "Archivo .env.windows no encontrado. Cree .env manualmente."
    }
}

# -----------------------------------------------------------------------------
# PASO 7: Verificacion final
# -----------------------------------------------------------------------------
Write-Step "7/7" "Verificacion final..."

Write-Host ""
Write-Host "=============================================================================" -ForegroundColor Green
Write-Host "  CONFIGURACION COMPLETADA" -ForegroundColor Green
Write-Host "=============================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Resumen de configuracion:" -ForegroundColor Cyan
Write-Host ""

# Verificar componentes
$components = @(
    @{Name="WSL2"; Check={wsl --status 2>&1; $LASTEXITCODE -eq 0}},
    @{Name="Podman"; Check={podman --version 2>&1; $LASTEXITCODE -eq 0}},
    @{Name="podman-compose"; Check={podman-compose --version 2>&1; $LASTEXITCODE -eq 0}},
    @{Name="Maquina Podman"; Check={$m = podman machine list --format json | ConvertFrom-Json; ($m | Where-Object {$_.Running}).Count -gt 0}}
)

foreach ($comp in $components) {
    try {
        $result = & $comp.Check
        if ($result -or $LASTEXITCODE -eq 0) {
            Write-Host "  [OK] " -ForegroundColor Green -NoNewline
            Write-Host $comp.Name -ForegroundColor White
        }
        else {
            Write-Host "  [X]  " -ForegroundColor Red -NoNewline
            Write-Host $comp.Name -ForegroundColor White
        }
    }
    catch {
        Write-Host "  [?]  " -ForegroundColor Yellow -NoNewline
        Write-Host $comp.Name -ForegroundColor White
    }
}

Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Navegar al directorio del proyecto:" -ForegroundColor White
Write-Host "     cd $projectRoot" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Construir las imagenes:" -ForegroundColor White
Write-Host "     podman-compose -f podman-compose.windows.yml build" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Iniciar la plataforma:" -ForegroundColor White
Write-Host "     podman-compose -f podman-compose.windows.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "  O usar el script de inicio:" -ForegroundColor White
Write-Host "     .\scripts\windows\start-platform.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "URLs de acceso (despues de iniciar):" -ForegroundColor Cyan
Write-Host "  - Admin Dashboard:  http://localhost:5000" -ForegroundColor White
Write-Host "  - Portal Cliente:   http://localhost:5001" -ForegroundColor White
Write-Host "  - RQ Dashboard:     http://localhost:9181" -ForegroundColor White
Write-Host "  - Adminer (DB):     http://localhost:8085" -ForegroundColor White
Write-Host ""
