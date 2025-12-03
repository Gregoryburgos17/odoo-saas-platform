#!/bin/bash
# =============================================================================
# Script simple para probar Flask-Limiter con curl
# =============================================================================

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
PORTAL_URL="${PORTAL_URL:-http://localhost:5001}"
ADMIN_URL="${ADMIN_URL:-http://localhost:5000}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                      ║${NC}"
echo -e "${BLUE}║     PRUEBA RÁPIDA DE FLASK-LIMITER CON CURL                          ║${NC}"
echo -e "${BLUE}║                                                                      ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"

# Función para probar Redis
test_redis() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}PRUEBA 1: Verificar conexión a Redis${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"

    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &> /dev/null; then
            echo -e "${GREEN}✅ Redis está funcionando correctamente${NC}"
            echo -e "   Host: ${REDIS_HOST}:${REDIS_PORT}"

            # Contar claves de rate limiting
            key_count=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --scan --pattern "LIMITER/*" 2>/dev/null | wc -l)
            echo -e "   Claves de rate limiting: ${key_count}"

            if [ "$key_count" -gt 0 ]; then
                echo -e "\n   ${YELLOW}Claves encontradas:${NC}"
                redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --scan --pattern "LIMITER/*" | head -5 | while read key; do
                    ttl=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" TTL "$key")
                    echo -e "   - $key (expira en ${ttl}s)"
                done
            fi
            return 0
        else
            echo -e "${RED}❌ No se puede conectar a Redis${NC}"
            echo -e "   Asegúrate de que Redis esté corriendo:"
            echo -e "   ${YELLOW}docker-compose up -d redis${NC}"
            echo -e "   ${YELLOW}podman-compose up -d redis${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  redis-cli no está instalado, saltando prueba de Redis${NC}"
        return 1
    fi
}

# Función para probar rate limiting
test_rate_limiting() {
    local service_name=$1
    local url=$2
    local endpoint=$3
    local expected_limit=$4

    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}PRUEBA 2: Rate Limiting - ${service_name}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "URL: ${url}${endpoint}"
    echo -e "Límite esperado: ${expected_limit} requests/minuto"

    # Verificar que el servicio esté disponible
    if ! curl -s -f "${url}/health" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Servicio ${service_name} no disponible en ${url}${NC}"
        echo -e "   Inicia el servicio primero"
        return 1
    fi

    echo -e "${GREEN}✅ Servicio ${service_name} disponible${NC}"
    echo -e "\n${YELLOW}Enviando 10 requests para probar el límite...${NC}\n"

    local success_count=0
    local rate_limited_count=0
    local total_requests=10

    # Enviar requests
    for i in $(seq 1 $total_requests); do
        # Hacer request y capturar código de estado
        response=$(curl -s -w "\n%{http_code}" -X POST "${url}${endpoint}" \
            -H "Content-Type: application/json" \
            -d '{"email":"test@example.com","password":"wrongpassword"}')

        # Extraer código de estado (última línea)
        status_code=$(echo "$response" | tail -n1)

        # Mostrar resultado
        if [ "$status_code" -eq 429 ]; then
            echo -e "${RED}🚫 Request #${i}: 429 RATE LIMITED${NC}"
            rate_limited_count=$((rate_limited_count + 1))
        elif [ "$status_code" -eq 200 ] || [ "$status_code" -eq 400 ] || [ "$status_code" -eq 401 ]; then
            echo -e "${GREEN}✅ Request #${i}: ${status_code} OK${NC}"
            success_count=$((success_count + 1))
        else
            echo -e "${YELLOW}⚠️  Request #${i}: ${status_code}${NC}"
        fi

        # Pequeña pausa entre requests
        sleep 0.1
    done

    # Resumen
    echo -e "\n${CYAN}────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}RESUMEN:${NC}"
    echo -e "  Total de requests: ${total_requests}"
    echo -e "  Requests exitosos: ${success_count}"
    echo -e "  Requests bloqueados (429): ${rate_limited_count}"

    if [ "$rate_limited_count" -gt 0 ]; then
        echo -e "\n${GREEN}✅ RATE LIMITING ESTÁ FUNCIONANDO CORRECTAMENTE${NC}"
        echo -e "   Se bloquearon ${rate_limited_count} requests después de ${success_count} exitosos"
        return 0
    else
        echo -e "\n${YELLOW}⚠️  ADVERTENCIA: No se detectó rate limiting${NC}"
        echo -e "   Posibles causas:"
        echo -e "   - Redis no está configurado correctamente"
        echo -e "   - El endpoint no tiene rate limiting aplicado"
        return 1
    fi
}

# Función para limpiar límites de rate (útil para testing)
clear_rate_limits() {
    echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Limpiando límites de rate...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"

    if command -v redis-cli &> /dev/null; then
        local deleted_count=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --scan --pattern "LIMITER/*" | xargs -r redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" DEL 2>/dev/null | wc -l)
        echo -e "${GREEN}✅ Eliminadas ${deleted_count} claves de rate limiting${NC}"
    else
        echo -e "${YELLOW}⚠️  redis-cli no está disponible${NC}"
    fi
}

# Función para mostrar ayuda
show_help() {
    echo -e "\n${CYAN}USO:${NC}"
    echo -e "  $0 [opción]"
    echo -e "\n${CYAN}OPCIONES:${NC}"
    echo -e "  ${GREEN}all${NC}          - Ejecutar todas las pruebas (por defecto)"
    echo -e "  ${GREEN}redis${NC}        - Solo probar conexión a Redis"
    echo -e "  ${GREEN}portal${NC}       - Solo probar rate limiting en Portal"
    echo -e "  ${GREEN}admin${NC}        - Solo probar rate limiting en Admin"
    echo -e "  ${GREEN}clear${NC}        - Limpiar límites de rate en Redis"
    echo -e "  ${GREEN}help${NC}         - Mostrar esta ayuda"
    echo -e "\n${CYAN}VARIABLES DE ENTORNO:${NC}"
    echo -e "  PORTAL_URL   - URL del servicio Portal (default: http://localhost:5001)"
    echo -e "  ADMIN_URL    - URL del servicio Admin (default: http://localhost:5000)"
    echo -e "  REDIS_HOST   - Host de Redis (default: localhost)"
    echo -e "  REDIS_PORT   - Puerto de Redis (default: 6379)"
    echo -e "\n${CYAN}EJEMPLOS:${NC}"
    echo -e "  ${YELLOW}$0${NC}                    # Ejecutar todas las pruebas"
    echo -e "  ${YELLOW}$0 portal${NC}             # Probar solo el Portal"
    echo -e "  ${YELLOW}$0 clear${NC}              # Limpiar límites y volver a probar"
    echo -e "  ${YELLOW}PORTAL_URL=http://192.168.1.100:5001 $0 portal${NC}"
}

# Main
case "${1:-all}" in
    help)
        show_help
        ;;
    redis)
        test_redis
        ;;
    portal)
        test_rate_limiting "Portal" "$PORTAL_URL" "/api/auth/login" 5
        ;;
    admin)
        test_rate_limiting "Admin" "$ADMIN_URL" "/api/auth/login" 5
        ;;
    clear)
        clear_rate_limits
        ;;
    all|*)
        # Ejecutar todas las pruebas
        test_redis
        redis_ok=$?

        if [ $redis_ok -eq 0 ]; then
            test_rate_limiting "Portal" "$PORTAL_URL" "/api/auth/login" 5
            echo ""
            test_rate_limiting "Admin" "$ADMIN_URL" "/api/auth/login" 5

            # Mostrar instrucciones finales
            echo -e "\n${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
            echo -e "${CYAN}COMANDOS ÚTILES:${NC}"
            echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
            echo -e "\n${YELLOW}1. Ver todas las claves de rate limiting:${NC}"
            echo -e "   redis-cli KEYS 'LIMITER/*'"
            echo -e "\n${YELLOW}2. Limpiar todos los límites:${NC}"
            echo -e "   $0 clear"
            echo -e "\n${YELLOW}3. Monitorear Redis en tiempo real:${NC}"
            echo -e "   redis-cli MONITOR | grep LIMITER"
            echo -e ""
        fi
        ;;
esac

echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}PRUEBAS COMPLETADAS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"
