# Odoo SaaS Platform - Makefile
# Development commands for Podman on Windows
#
# Usage: make <target>

.PHONY: help up down restart logs build clean seed shell-admin shell-portal shell-db shell-redis test

# Default target
help:
	@echo "Odoo SaaS Platform - Development Commands"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  up          Start all services"
	@echo "  down        Stop all services"
	@echo "  restart     Restart all services"
	@echo "  logs        View logs (all services)"
	@echo "  build       Build container images"
	@echo "  clean       Stop and remove containers, volumes"
	@echo "  seed        Seed database with demo data"
	@echo "  shell-admin Enter admin container shell"
	@echo "  shell-portal Enter portal container shell"
	@echo "  shell-db    PostgreSQL interactive shell"
	@echo "  shell-redis Redis CLI"
	@echo "  dev-tools   Start with Adminer (database UI)"
	@echo "  test        Run tests"

# Start all services
up:
	podman-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "  Admin:      http://localhost:5000"
	@echo "  Portal:     http://localhost:5001"
	@echo "  RQ Dashboard: http://localhost:9181"

# Stop all services
down:
	podman-compose down

# Restart services
restart:
	podman-compose restart

# View logs
logs:
	podman-compose logs -f

# Build images
build:
	podman-compose build

# Clean everything
clean:
	podman-compose down -v --remove-orphans
	podman system prune -f

# Seed database
seed:
	podman-compose exec admin python /app/scripts/seed_data.py

# Initialize database
init-db:
	podman-compose exec admin python -c "from shared.database import init_db; init_db()"

# Shell access
shell-admin:
	podman-compose exec admin /bin/sh

shell-portal:
	podman-compose exec portal /bin/sh

shell-db:
	podman-compose exec postgres psql -U odoo -d odoo_saas

shell-redis:
	podman-compose exec redis redis-cli

# Start with dev tools
dev-tools:
	podman-compose --profile dev-tools up -d
	@echo ""
	@echo "Dev tools started!"
	@echo "  Adminer: http://localhost:8085"

# Run tests
test:
	podman-compose exec admin python -m pytest -v
	podman-compose exec portal python -m pytest -v

# View service status
ps:
	podman-compose ps

# Admin logs only
logs-admin:
	podman-compose logs -f admin

# Portal logs only
logs-portal:
	podman-compose logs -f portal

# Worker logs only
logs-worker:
	podman-compose logs -f worker
