# Script de Corrección para Odoo SaaS Platform
# Corrige la configuración de Rate Limiting en el archivo .env

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Corrección de Rate Limiting" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si existe .env
if (!(Test-Path ".env")) {
    Write-Host "❌ ERROR: El archivo .env no existe" -ForegroundColor Red
    Write-Host "Por favor copia .env.example a .env primero" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Archivo .env encontrado" -ForegroundColor Green

# Leer contenido actual
$envContent = Get-Content ".env" -Raw

# Verificar si tiene el problema
if ($envContent -match 'RATE_LIMIT_PER_MINUTE\s*=\s*60\s*$' -or $envContent -match 'RATE_LIMIT_PER_MINUTE\s*=\s*60\r') {
    Write-Host "⚠️  Detectado problema: RATE_LIMIT_PER_MINUTE=60" -ForegroundColor Yellow
    
    # Hacer backup
    $backupFile = ".env.backup." + (Get-Date -Format "yyyyMMdd_HHmmss")
    Copy-Item ".env" $backupFile
    Write-Host "✅ Backup creado: $backupFile" -ForegroundColor Green
    
    # Aplicar corrección
    $envContent = $envContent -replace 'RATE_LIMIT_PER_MINUTE\s*=\s*60\s*$', 'RATE_LIMIT_PER_MINUTE=60/minute'
    $envContent = $envContent -replace 'RATE_LIMIT_PER_MINUTE\s*=\s*60\r', "RATE_LIMIT_PER_MINUTE=60/minute`r"
    
    # Guardar archivo corregido
    $envContent | Set-Content ".env" -NoNewline
    
    Write-Host "✅ Corrección aplicada: RATE_LIMIT_PER_MINUTE=60/minute" -ForegroundColor Green
} elseif ($envContent -match 'RATE_LIMIT_PER_MINUTE\s*=\s*60/minute') {
    Write-Host "✅ La configuración ya está correcta" -ForegroundColor Green
} else {
    Write-Host "⚠️  No se encontró RATE_LIMIT_PER_MINUTE, agregando..." -ForegroundColor Yellow
    
    # Agregar la variable
    Add-Content ".env" "`nRATE_LIMIT_PER_MINUTE=60/minute"
    Write-Host "✅ Variable agregada" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Pasos siguientes:" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "1. Reconstruir las imágenes:" -ForegroundColor White
Write-Host "   podman build -t localhost/odoo-saas-admin:latest -f admin/Dockerfile ." -ForegroundColor Gray
Write-Host "   podman build -t localhost/odoo-saas-portal:latest -f portal/Dockerfile ." -ForegroundColor Gray
Write-Host ""
Write-Host "2. Reiniciar los contenedores:" -ForegroundColor White
Write-Host "   podman-compose -f docker-compose.podman.yml down" -ForegroundColor Gray
Write-Host "   podman-compose -f docker-compose.podman.yml up -d" -ForegroundColor Gray
Write-Host ""
