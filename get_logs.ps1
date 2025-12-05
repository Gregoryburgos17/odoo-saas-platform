# =============================================================================
# Odoo SaaS Platform - Log Retrieval Script (Remote Podman Compatible)
# =============================================================================
# This script retrieves logs from all services with proper error handling
# for remote Podman connections
# =============================================================================

param(
    [int]$TailLines = 50,
    [switch]$Follow,
    [string]$Service = ""
)

$ErrorActionPreference = "Continue"

# Service container names
$services = @(
    "odoo-saas-admin",
    "odoo-saas-portal",
    "odoo-saas-worker",
    "odoo-saas-nginx",
    "odoo-saas-postgres",
    "odoo-saas-redis"
)

# Function to get logs for a specific container
function Get-ContainerLogs {
    param(
        [string]$ServiceName,
        [int]$Lines,
        [bool]$FollowLogs
    )

    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host " SERVICE: $ServiceName" -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Cyan

    # First, get the exact container ID for running containers only
    $containerInfo = podman ps --filter "name=$ServiceName" --format "{{.ID}} {{.Names}} {{.Status}}" 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error checking container status" -ForegroundColor Red
        Write-Host $containerInfo -ForegroundColor Red
        return
    }

    if ([string]::IsNullOrWhiteSpace($containerInfo)) {
        Write-Host "⚠️  Container not running or not found" -ForegroundColor Yellow
        return
    }

    # Parse the output - might have multiple lines if multiple containers match
    $containerLines = $containerInfo -split "`n" | Where-Object { $_ -match "\S" }

    if ($containerLines.Count -eq 0) {
        Write-Host "⚠️  No running containers found" -ForegroundColor Yellow
        return
    }

    if ($containerLines.Count -gt 1) {
        Write-Host "⚠️  Multiple containers found:" -ForegroundColor Yellow
        foreach ($line in $containerLines) {
            Write-Host "   $line" -ForegroundColor Gray
        }
        # Use the first one
        $containerID = ($containerLines[0] -split "\s+")[0]
        Write-Host "   Using first container: $containerID" -ForegroundColor Yellow
    } else {
        $containerID = ($containerLines[0] -split "\s+")[0]
    }

    Write-Host "📦 Container ID: $containerID" -ForegroundColor Green
    Write-Host ""

    # Get logs using the specific container ID
    try {
        if ($FollowLogs) {
            podman logs -f $containerID 2>&1
        } else {
            $logs = podman logs --tail $Lines $containerID 2>&1
            if ($LASTEXITCODE -eq 0) {
                if ([string]::IsNullOrWhiteSpace($logs)) {
                    Write-Host "   (No logs available)" -ForegroundColor Gray
                } else {
                    Write-Host $logs
                }
            } else {
                Write-Host "❌ Error retrieving logs:" -ForegroundColor Red
                Write-Host $logs -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "❌ Exception occurred: $_" -ForegroundColor Red
    }

    Write-Host ""
}

# Header
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     ODOO SAAS PLATFORM - LOG RETRIEVAL                        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host "--- LOGS GENERATED AT $(Get-Date -Format 'MM/dd/yyyy HH:mm:ss') ---" -ForegroundColor Gray
Write-Host ""

# Check if specific service requested
if ($Service -ne "") {
    if ($services -contains $Service) {
        Get-ContainerLogs -ServiceName $Service -Lines $TailLines -FollowLogs $Follow
    } else {
        Write-Host "❌ Unknown service: $Service" -ForegroundColor Red
        Write-Host "Available services:" -ForegroundColor Yellow
        foreach ($svc in $services) {
            Write-Host "  - $svc" -ForegroundColor Gray
        }
    }
} else {
    # Get logs for all services
    foreach ($service in $services) {
        Get-ContainerLogs -ServiceName $service -Lines $TailLines -FollowLogs $Follow
    }
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "✅ Log retrieval complete" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Usage examples:" -ForegroundColor Yellow
Write-Host "  .\get_logs.ps1                          # Get last 50 lines from all services" -ForegroundColor Gray
Write-Host "  .\get_logs.ps1 -TailLines 100           # Get last 100 lines from all services" -ForegroundColor Gray
Write-Host "  .\get_logs.ps1 -Service odoo-saas-admin # Get logs for specific service" -ForegroundColor Gray
Write-Host "  .\get_logs.ps1 -Follow                  # Follow logs in real-time" -ForegroundColor Gray
Write-Host ""
