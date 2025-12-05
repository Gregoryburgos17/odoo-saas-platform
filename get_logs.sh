#!/bin/bash
# =============================================================================
# Odoo SaaS Platform - Log Retrieval Script (Remote Podman Compatible)
# =============================================================================
# This script retrieves logs from all services with proper error handling
# for remote Podman connections
# =============================================================================

set +e  # Don't exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Default values
TAIL_LINES=50
FOLLOW=false
SERVICE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--lines)
            TAIL_LINES="$2"
            shift 2
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -n, --lines N      Show last N lines (default: 50)"
            echo "  -f, --follow       Follow log output"
            echo "  -s, --service NAME Get logs for specific service"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                              # Get last 50 lines from all services"
            echo "  $0 -n 100                       # Get last 100 lines from all services"
            echo "  $0 -s odoo-saas-admin           # Get logs for specific service"
            echo "  $0 -f                           # Follow logs in real-time"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Service container names
SERVICES=(
    "odoo-saas-admin"
    "odoo-saas-portal"
    "odoo-saas-worker"
    "odoo-saas-nginx"
    "odoo-saas-postgres"
    "odoo-saas-redis"
)

# Function to get logs for a specific container
get_container_logs() {
    local service_name=$1
    local lines=$2
    local follow_logs=$3

    echo -e "${CYAN}================================================================${NC}"
    echo -e "${YELLOW} SERVICE: $service_name${NC}"
    echo -e "${CYAN}================================================================${NC}"

    # First, get the exact container ID for running containers only
    local container_info
    container_info=$(podman ps --filter "name=$service_name" --format "{{.ID}} {{.Names}} {{.Status}}" 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}❌ Error checking container status${NC}"
        echo -e "${RED}$container_info${NC}"
        echo ""
        return
    fi

    if [ -z "$container_info" ] || [ -z "${container_info// }" ]; then
        echo -e "${YELLOW}⚠️  Container not running or not found${NC}"
        echo ""
        return
    fi

    # Count number of containers found
    local container_count=$(echo "$container_info" | wc -l)

    if [ $container_count -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No running containers found${NC}"
        echo ""
        return
    fi

    if [ $container_count -gt 1 ]; then
        echo -e "${YELLOW}⚠️  Multiple containers found:${NC}"
        echo "$container_info" | while read line; do
            echo -e "   ${GRAY}$line${NC}"
        done
        # Use the first one
        local container_id=$(echo "$container_info" | head -n1 | awk '{print $1}')
        echo -e "   ${YELLOW}Using first container: $container_id${NC}"
    else
        local container_id=$(echo "$container_info" | awk '{print $1}')
    fi

    echo -e "${GREEN}📦 Container ID: $container_id${NC}"
    echo ""

    # Get logs using the specific container ID
    if [ "$follow_logs" = true ]; then
        podman logs -f "$container_id" 2>&1
    else
        local logs
        logs=$(podman logs --tail "$lines" "$container_id" 2>&1)
        exit_code=$?

        if [ $exit_code -eq 0 ]; then
            if [ -z "$logs" ] || [ -z "${logs// }" ]; then
                echo -e "   ${GRAY}(No logs available)${NC}"
            else
                echo "$logs"
            fi
        else
            echo -e "${RED}❌ Error retrieving logs:${NC}"
            echo -e "${RED}$logs${NC}"
        fi
    fi

    echo ""
}

# Header
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     ODOO SAAS PLATFORM - LOG RETRIEVAL                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${GRAY}--- LOGS GENERATED AT $(date '+%m/%d/%Y %H:%M:%S') ---${NC}"
echo ""

# Check if specific service requested
if [ -n "$SERVICE" ]; then
    # Check if service is in the list
    if [[ " ${SERVICES[@]} " =~ " ${SERVICE} " ]]; then
        get_container_logs "$SERVICE" "$TAIL_LINES" "$FOLLOW"
    else
        echo -e "${RED}❌ Unknown service: $SERVICE${NC}"
        echo -e "${YELLOW}Available services:${NC}"
        for svc in "${SERVICES[@]}"; do
            echo -e "  ${GRAY}- $svc${NC}"
        done
    fi
else
    # Get logs for all services
    for service in "${SERVICES[@]}"; do
        get_container_logs "$service" "$TAIL_LINES" "$FOLLOW"
    done
fi

echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}✅ Log retrieval complete${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""
echo -e "${YELLOW}Usage examples:${NC}"
echo -e "${GRAY}  ./get_logs.sh                          # Get last 50 lines from all services${NC}"
echo -e "${GRAY}  ./get_logs.sh -n 100                   # Get last 100 lines from all services${NC}"
echo -e "${GRAY}  ./get_logs.sh -s odoo-saas-admin       # Get logs for specific service${NC}"
echo -e "${GRAY}  ./get_logs.sh -f                       # Follow logs in real-time${NC}"
echo ""
