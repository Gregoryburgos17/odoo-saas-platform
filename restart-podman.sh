#!/bin/bash
# =============================================================================
# Script de Reinicio Completo de Servicios Podman
# =============================================================================
# Este script detiene todos los contenedores, limpia las imágenes antiguas,
# reconstruye todo y valida que los servicios estén funcionando correctamente
# =============================================================================

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con color
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  ${1}${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Verificar que podman-compose esté instalado
check_dependencies() {
    print_header "Verificando Dependencias"

    if ! command -v podman-compose &> /dev/null; then
        print_error "podman-compose no está instalado"
        print_info "Instálalo con: pip install podman-compose"
        exit 1
    fi

    if ! command -v podman &> /dev/null; then
        print_error "podman no está instalado"
        exit 1
    fi

    print_success "Todas las dependencias están instaladas"
}

# Paso 1: Detener todos los contenedores
stop_containers() {
    print_header "Paso 1: Deteniendo Contenedores"

    print_info "Deteniendo servicios con podman-compose..."
    podman-compose -f docker-compose.podman.yml down || true

    # Verificar si quedan contenedores del proyecto corriendo
    RUNNING=$(podman ps --filter "name=odoo-saas" -q)
    if [ -n "$RUNNING" ]; then
        print_warning "Deteniendo contenedores residuales..."
        podman stop $RUNNING || true
    fi

    print_success "Contenedores detenidos"
}

# Paso 2: Eliminar contenedores existentes
remove_containers() {
    print_header "Paso 2: Eliminando Contenedores"

    CONTAINERS=$(podman ps -a --filter "name=odoo-saas" -q)
    if [ -n "$CONTAINERS" ]; then
        print_info "Eliminando contenedores existentes..."
        podman rm -f $CONTAINERS || true
        print_success "Contenedores eliminados"
    else
        print_info "No hay contenedores para eliminar"
    fi
}

# Paso 3: Eliminar imágenes antiguas (opcional)
remove_images() {
    print_header "Paso 3: Limpiando Imágenes Antiguas"

    print_warning "¿Deseas eliminar las imágenes antiguas? (s/n) [Por defecto: n]"
    read -t 10 -r REMOVE_IMAGES || REMOVE_IMAGES="n"

    if [[ $REMOVE_IMAGES =~ ^[Ss]$ ]]; then
        print_info "Eliminando imágenes del proyecto..."
        podman images --filter "reference=localhost/odoo-saas-*" -q | xargs -r podman rmi -f || true
        print_success "Imágenes eliminadas"
    else
        print_info "Conservando imágenes existentes"
    fi
}

# Paso 4: Reconstruir imágenes
build_images() {
    print_header "Paso 4: Construyendo Imágenes"

    print_info "Construyendo todas las imágenes (esto puede tomar unos minutos)..."
    podman-compose -f docker-compose.podman.yml build --no-cache

    print_success "Imágenes construidas exitosamente"
}

# Paso 5: Levantar servicios
start_services() {
    print_header "Paso 5: Levantando Servicios"

    print_info "Iniciando servicios en segundo plano..."
    podman-compose -f docker-compose.podman.yml up -d

    print_success "Servicios iniciados"
}

# Paso 6: Esperar a que los servicios estén listos
wait_for_services() {
    print_header "Paso 6: Esperando a que los Servicios Estén Listos"

    print_info "Esperando a que PostgreSQL esté listo..."
    for i in {1..30}; do
        if podman exec odoo-saas-postgres pg_isready -U odoo &> /dev/null; then
            print_success "PostgreSQL está listo"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL no respondió a tiempo"
            exit 1
        fi
        echo -n "."
        sleep 2
    done

    print_info "Esperando a que Redis esté listo..."
    for i in {1..30}; do
        if podman exec odoo-saas-redis redis-cli ping &> /dev/null; then
            print_success "Redis está listo"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Redis no respondió a tiempo"
            exit 1
        fi
        echo -n "."
        sleep 2
    done

    print_info "Esperando a que el servicio Admin esté listo (puede tardar un poco)..."
    for i in {1..60}; do
        if curl -f http://localhost:5000/health &> /dev/null; then
            print_success "Servicio Admin está listo"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "Servicio Admin no respondió a tiempo, pero continuaremos..."
            break
        fi
        echo -n "."
        sleep 3
    done

    print_info "Esperando a que el servicio Portal esté listo..."
    for i in {1..60}; do
        if curl -f http://localhost:5001/health &> /dev/null; then
            print_success "Servicio Portal está listo"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "Servicio Portal no respondió a tiempo, pero continuaremos..."
            break
        fi
        echo -n "."
        sleep 3
    done
}

# Paso 7: Validar estado de todos los servicios
validate_services() {
    print_header "Paso 7: Validando Estado de Servicios"

    echo ""
    print_info "Estado de los contenedores:"
    podman-compose -f docker-compose.podman.yml ps

    echo ""
    print_info "Verificando salud de servicios..."

    # Verificar PostgreSQL
    if podman exec odoo-saas-postgres pg_isready -U odoo &> /dev/null; then
        print_success "PostgreSQL: ✓ FUNCIONANDO"
    else
        print_error "PostgreSQL: ✗ NO RESPONDE"
    fi

    # Verificar Redis
    if podman exec odoo-saas-redis redis-cli ping &> /dev/null; then
        print_success "Redis: ✓ FUNCIONANDO"
    else
        print_error "Redis: ✗ NO RESPONDE"
    fi

    # Verificar Admin
    if curl -sf http://localhost:5000/health &> /dev/null; then
        print_success "Admin Service (Puerto 5000): ✓ FUNCIONANDO"
    else
        print_warning "Admin Service (Puerto 5000): ⚠ NO DISPONIBLE"
    fi

    # Verificar Portal
    if curl -sf http://localhost:5001/health &> /dev/null; then
        print_success "Portal Service (Puerto 5001): ✓ FUNCIONANDO"
    else
        print_warning "Portal Service (Puerto 5001): ⚠ NO DISPONIBLE"
    fi

    # Verificar Nginx
    if curl -sf http://localhost:8082 &> /dev/null; then
        print_success "Nginx (Puerto 8082): ✓ FUNCIONANDO"
    else
        print_warning "Nginx (Puerto 8082): ⚠ NO DISPONIBLE"
    fi

    # Verificar RQ Dashboard
    if curl -sf http://localhost:9182 &> /dev/null; then
        print_success "RQ Dashboard (Puerto 9182): ✓ FUNCIONANDO"
    else
        print_warning "RQ Dashboard (Puerto 9182): ⚠ NO DISPONIBLE"
    fi

    # Verificar Grafana
    if curl -sf http://localhost:3100 &> /dev/null; then
        print_success "Grafana (Puerto 3100): ✓ FUNCIONANDO"
    else
        print_warning "Grafana (Puerto 3100): ⚠ NO DISPONIBLE"
    fi

    # Verificar Prometheus
    if curl -sf http://localhost:9091 &> /dev/null; then
        print_success "Prometheus (Puerto 9091): ✓ FUNCIONANDO"
    else
        print_warning "Prometheus (Puerto 9091): ⚠ NO DISPONIBLE"
    fi
}

# Función para mostrar logs si algo falla
show_logs() {
    print_header "Logs de Servicios (últimas 50 líneas)"

    print_info "Logs del Admin Service:"
    podman logs --tail 50 odoo-saas-admin 2>&1 || true

    echo ""
    print_info "Logs del Portal Service:"
    podman logs --tail 50 odoo-saas-portal 2>&1 || true
}

# Resumen final
print_summary() {
    print_header "Resumen de Servicios Disponibles"

    echo ""
    echo -e "${GREEN}Servicios Core:${NC}"
    echo "  • Admin Dashboard:    http://localhost:5000"
    echo "  • Portal Customer:    http://localhost:5001"
    echo "  • Nginx Proxy:        http://localhost:8082"
    echo ""
    echo -e "${GREEN}Monitoreo y Gestión:${NC}"
    echo "  • RQ Dashboard:       http://localhost:9182"
    echo "  • Grafana:            http://localhost:3100 (admin/admin123)"
    echo "  • Prometheus:         http://localhost:9091"
    echo "  • Adminer:            http://localhost:8085"
    echo ""
    echo -e "${GREEN}Base de Datos:${NC}"
    echo "  • PostgreSQL:         localhost:55432"
    echo "  • Redis:              localhost:6379"
    echo ""
    echo -e "${YELLOW}Comandos útiles:${NC}"
    echo "  • Ver logs:           podman-compose -f docker-compose.podman.yml logs -f [servicio]"
    echo "  • Detener todo:       podman-compose -f docker-compose.podman.yml down"
    echo "  • Reiniciar todo:     ./restart-podman.sh"
    echo ""
}

# =============================================================================
# MAIN - Ejecución Principal
# =============================================================================

main() {
    clear
    print_header "ODOO SaaS Platform - Reinicio Completo de Servicios Podman"

    echo "Este script realizará las siguientes acciones:"
    echo "  1. Detener todos los contenedores"
    echo "  2. Eliminar contenedores existentes"
    echo "  3. Limpiar imágenes antiguas (opcional)"
    echo "  4. Reconstruir todas las imágenes"
    echo "  5. Levantar servicios"
    echo "  6. Validar que todo esté funcionando"
    echo ""
    print_warning "¿Deseas continuar? (s/n)"
    read -r CONTINUE

    if [[ ! $CONTINUE =~ ^[Ss]$ ]]; then
        print_info "Operación cancelada"
        exit 0
    fi

    # Ejecutar pasos
    check_dependencies
    stop_containers
    remove_containers
    remove_images
    build_images
    start_services
    wait_for_services
    validate_services

    # Si algún servicio no está disponible, mostrar logs
    if ! curl -sf http://localhost:5000/health &> /dev/null || ! curl -sf http://localhost:5001/health &> /dev/null; then
        print_warning "Algunos servicios no respondieron. Mostrando logs..."
        show_logs
    fi

    print_summary

    print_header "¡Proceso Completado!"
    print_success "Todos los servicios han sido reiniciados"
}

# Ejecutar el script principal
main
