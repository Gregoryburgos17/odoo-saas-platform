#!/bin/bash
# =============================================================================
# Script de Reinicio RÁPIDO de Servicios Podman (Sin Confirmaciones)
# =============================================================================
# Versión rápida sin confirmaciones - ideal para desarrollo
# =============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ ${1}${NC}"; }
print_success() { echo -e "${GREEN}✓ ${1}${NC}"; }
print_error() { echo -e "${RED}✗ ${1}${NC}"; }

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  REINICIO RÁPIDO - ODOO SaaS Platform${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# 1. Detener y eliminar todo
print_info "Deteniendo y eliminando contenedores..."
podman-compose -f docker-compose.podman.yml down 2>/dev/null || true
podman stop $(podman ps -a --filter "name=odoo-saas" -q) 2>/dev/null || true
podman rm -f $(podman ps -a --filter "name=odoo-saas" -q) 2>/dev/null || true
print_success "Limpieza completada"

# 2. Reconstruir
print_info "Reconstruyendo imágenes..."
podman-compose -f docker-compose.podman.yml build --no-cache

# 3. Levantar
print_info "Levantando servicios..."
podman-compose -f docker-compose.podman.yml up -d

# 4. Esperar y validar
print_info "Esperando a que los servicios estén listos..."
sleep 10

for i in {1..20}; do
    if podman exec odoo-saas-postgres pg_isready -U odoo &> /dev/null; then
        print_success "PostgreSQL listo"
        break
    fi
    sleep 2
done

for i in {1..20}; do
    if podman exec odoo-saas-redis redis-cli ping &> /dev/null; then
        print_success "Redis listo"
        break
    fi
    sleep 2
done

sleep 5

# Verificar servicios
echo ""
print_info "Estado de servicios:"
curl -sf http://localhost:5000/health &> /dev/null && print_success "Admin (5000): OK" || print_error "Admin (5000): FALLO"
curl -sf http://localhost:5001/health &> /dev/null && print_success "Portal (5001): OK" || print_error "Portal (5001): FALLO"
curl -sf http://localhost:8082 &> /dev/null && print_success "Nginx (8082): OK" || print_error "Nginx (8082): FALLO"
curl -sf http://localhost:9182 &> /dev/null && print_success "RQ Dashboard (9182): OK" || print_error "RQ Dashboard (9182): FALLO"

echo ""
print_success "¡Reinicio completado!"
echo ""
echo "Accede a tus servicios:"
echo "  • Admin:     http://localhost:5000"
echo "  • Portal:    http://localhost:5001"
echo "  • Nginx:     http://localhost:8082"
echo "  • RQ Dash:   http://localhost:9182"
echo ""
