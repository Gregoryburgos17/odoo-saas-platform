# Odoo SaaS Platform - Quick Start Script for Windows PowerShell
# Run this script to set up and start the platform
#
# Usage: .\start.ps1 [command]
#   Commands:
#     up       - Start all services (default)
#     down     - Stop all services
#     restart  - Restart all services
#     logs     - View logs
#     seed     - Seed demo data
#     clean    - Remove all containers and volumes
#     status   - Show service status

param(
    [Parameter(Position=0)]
    [string]$Command = "up"
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warn { Write-Host $args -ForegroundColor Yellow }
function Write-Err { Write-Host $args -ForegroundColor Red }

# Banner
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║       ODOO SAAS PLATFORM                  ║" -ForegroundColor Cyan
    Write-Host "  ║       Podman Edition for Windows          ║" -ForegroundColor Cyan
    Write-Host "  ╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check Podman
    if (-not (Get-Command "podman" -ErrorAction SilentlyContinue)) {
        Write-Err "ERROR: Podman is not installed or not in PATH"
        Write-Warn "Please install Podman Desktop from: https://podman-desktop.io/"
        exit 1
    }

    # Check podman-compose
    if (-not (Get-Command "podman-compose" -ErrorAction SilentlyContinue)) {
        Write-Warn "podman-compose not found. Installing..."
        pip install podman-compose
    }

    # Check if Podman machine is running
    $machineStatus = podman machine list --format "{{.Running}}" 2>$null
    if ($machineStatus -ne "true" -and $machineStatus -notcontains "true") {
        Write-Warn "Podman machine is not running. Starting..."
        podman machine start
        Start-Sleep -Seconds 5
    }

    Write-Success "Prerequisites OK"
}

# Create .env if not exists
function Initialize-Environment {
    if (-not (Test-Path ".env")) {
        Write-Info "Creating .env file from template..."
        Copy-Item ".env.example" ".env"
        Write-Success ".env file created"
    }
}

# Start services
function Start-Services {
    Write-Info "Starting Odoo SaaS Platform..."
    podman-compose up -d

    Write-Host ""
    Write-Success "Services started successfully!"
    Write-Host ""
    Write-Info "Access URLs:"
    Write-Host "  Admin Dashboard:  " -NoNewline; Write-Host "http://localhost:5000" -ForegroundColor Yellow
    Write-Host "  Customer Portal:  " -NoNewline; Write-Host "http://localhost:5001" -ForegroundColor Yellow
    Write-Host "  RQ Dashboard:     " -NoNewline; Write-Host "http://localhost:9181" -ForegroundColor Yellow
    Write-Host ""
    Write-Info "Default credentials (after seeding):"
    Write-Host "  Admin: admin@example.com / admin123"
    Write-Host "  Demo:  demo@example.com / demo123"
    Write-Host ""
    Write-Warn "Run '.\start.ps1 seed' to create demo data"
}

# Stop services
function Stop-Services {
    Write-Info "Stopping services..."
    podman-compose down
    Write-Success "Services stopped"
}

# Restart services
function Restart-Services {
    Write-Info "Restarting services..."
    podman-compose restart
    Write-Success "Services restarted"
}

# View logs
function Show-Logs {
    Write-Info "Showing logs (Ctrl+C to exit)..."
    podman-compose logs -f
}

# Seed demo data
function Initialize-DemoData {
    Write-Info "Waiting for services to be ready..."
    Start-Sleep -Seconds 10

    Write-Info "Seeding demo data..."
    podman-compose exec admin python /app/scripts/seed_data.py

    Write-Success "Demo data seeded!"
    Write-Host ""
    Write-Info "You can now login with:"
    Write-Host "  Admin: admin@example.com / admin123"
    Write-Host "  Demo:  demo@example.com / demo123"
}

# Clean everything
function Remove-Everything {
    Write-Warn "This will remove all containers, volumes, and data!"
    $confirm = Read-Host "Are you sure? (yes/no)"

    if ($confirm -eq "yes") {
        Write-Info "Stopping and removing everything..."
        podman-compose down -v --remove-orphans
        Write-Success "Cleanup completed"
    } else {
        Write-Info "Cancelled"
    }
}

# Show status
function Show-Status {
    Write-Info "Service Status:"
    podman-compose ps
}

# Build images
function Build-Images {
    Write-Info "Building container images..."
    podman-compose build
    Write-Success "Build completed"
}

# Main
Show-Banner
Test-Prerequisites
Initialize-Environment

switch ($Command.ToLower()) {
    "up" { Start-Services }
    "start" { Start-Services }
    "down" { Stop-Services }
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "logs" { Show-Logs }
    "seed" { Initialize-DemoData }
    "clean" { Remove-Everything }
    "status" { Show-Status }
    "ps" { Show-Status }
    "build" { Build-Images }
    default {
        Write-Err "Unknown command: $Command"
        Write-Host ""
        Write-Info "Available commands:"
        Write-Host "  up, start   - Start all services"
        Write-Host "  down, stop  - Stop all services"
        Write-Host "  restart     - Restart all services"
        Write-Host "  logs        - View logs"
        Write-Host "  seed        - Seed demo data"
        Write-Host "  status, ps  - Show service status"
        Write-Host "  build       - Build container images"
        Write-Host "  clean       - Remove all containers and data"
    }
}
