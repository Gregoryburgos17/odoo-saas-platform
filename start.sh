#!/bin/bash
# Odoo SaaS Platform - Quick Start Script for Linux/Mac
# Run this script to set up and start the platform
#
# Usage: ./start.sh [command]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
show_banner() {
    echo ""
    echo -e "${CYAN}  ╔═══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}  ║       ODOO SAAS PLATFORM                  ║${NC}"
    echo -e "${CYAN}  ║       Podman Edition                      ║${NC}"
    echo -e "${CYAN}  ╚═══════════════════════════════════════════╝${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    echo -e "${CYAN}Checking prerequisites...${NC}"

    if ! command -v podman &> /dev/null; then
        echo -e "${RED}ERROR: Podman is not installed${NC}"
        exit 1
    fi

    if ! command -v podman-compose &> /dev/null; then
        echo -e "${YELLOW}podman-compose not found. Installing...${NC}"
        pip install podman-compose
    fi

    echo -e "${GREEN}Prerequisites OK${NC}"
}

# Create .env if not exists
init_env() {
    if [ ! -f ".env" ]; then
        echo -e "${CYAN}Creating .env file from template...${NC}"
        cp .env.example .env
        echo -e "${GREEN}.env file created${NC}"
    fi
}

# Start services
start_services() {
    echo -e "${CYAN}Starting Odoo SaaS Platform...${NC}"
    podman-compose up -d

    echo ""
    echo -e "${GREEN}Services started successfully!${NC}"
    echo ""
    echo -e "${CYAN}Access URLs:${NC}"
    echo -e "  Admin Dashboard:  ${YELLOW}http://localhost:5000${NC}"
    echo -e "  Customer Portal:  ${YELLOW}http://localhost:5001${NC}"
    echo -e "  RQ Dashboard:     ${YELLOW}http://localhost:9181${NC}"
    echo ""
    echo -e "${CYAN}Default credentials (after seeding):${NC}"
    echo "  Admin: admin@example.com / admin123"
    echo "  Demo:  demo@example.com / demo123"
    echo ""
    echo -e "${YELLOW}Run './start.sh seed' to create demo data${NC}"
}

# Stop services
stop_services() {
    echo -e "${CYAN}Stopping services...${NC}"
    podman-compose down
    echo -e "${GREEN}Services stopped${NC}"
}

# Seed demo data
seed_data() {
    echo -e "${CYAN}Waiting for services to be ready...${NC}"
    sleep 10

    echo -e "${CYAN}Seeding demo data...${NC}"
    podman-compose exec admin python /app/scripts/seed_data.py

    echo -e "${GREEN}Demo data seeded!${NC}"
}

# Show logs
show_logs() {
    echo -e "${CYAN}Showing logs (Ctrl+C to exit)...${NC}"
    podman-compose logs -f
}

# Clean everything
clean_all() {
    echo -e "${YELLOW}This will remove all containers, volumes, and data!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        podman-compose down -v --remove-orphans
        echo -e "${GREEN}Cleanup completed${NC}"
    else
        echo -e "${CYAN}Cancelled${NC}"
    fi
}

# Show status
show_status() {
    echo -e "${CYAN}Service Status:${NC}"
    podman-compose ps
}

# Main
show_banner
check_prerequisites
init_env

case "${1:-up}" in
    up|start)
        start_services
        ;;
    down|stop)
        stop_services
        ;;
    restart)
        podman-compose restart
        ;;
    logs)
        show_logs
        ;;
    seed)
        seed_data
        ;;
    status|ps)
        show_status
        ;;
    clean)
        clean_all
        ;;
    build)
        podman-compose build
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        echo "Available commands:"
        echo "  up, start   - Start all services"
        echo "  down, stop  - Stop all services"
        echo "  restart     - Restart all services"
        echo "  logs        - View logs"
        echo "  seed        - Seed demo data"
        echo "  status, ps  - Show service status"
        echo "  build       - Build container images"
        echo "  clean       - Remove all containers and data"
        ;;
esac
