# Odoo SaaS Platform - Deployment Guide for Windows + Podman

## Complete Guide: From Zero to Running Platform

This guide will walk you through deploying the complete Odoo SaaS Platform on Windows using Podman Desktop.

---

## Prerequisites

### 1. Install Podman Desktop on Windows

1. Download Podman Desktop from: https://podman-desktop.io/
2. Run the installer and follow the prompts
3. During installation, enable WSL2 integration
4. After installation, open Podman Desktop and initialize a Podman machine:
   ```powershell
   podman machine init
   podman machine start
   ```

### 2. Install podman-compose

Open PowerShell as Administrator and run:
```powershell
pip install podman-compose
```

Or with pipx:
```powershell
pipx install podman-compose
```

### 3. Verify Installation

```powershell
podman --version
podman-compose --version
```

---

## Quick Start (5 Minutes to Running)

### Step 1: Clone and Setup

```powershell
# Clone the repository
git clone https://github.com/your-repo/odoo-saas-platform.git
cd odoo-saas-platform

# Copy the development environment file
copy .env.development .env
```

### Step 2: Start All Services

```powershell
# Build and start all services
podman-compose -f docker-compose.podman.yml up -d --build
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Admin Dashboard (port 5000)
- Customer Portal (port 5001)
- Background Worker
- Prometheus (port 9090)
- Grafana (port 3000)
- RQ Dashboard (port 9181)
- Nginx (port 8081)
- AlertManager (port 9093)

### Step 3: Wait for Services to Initialize

```powershell
# Check service status
podman-compose -f docker-compose.podman.yml ps

# Watch logs to see when services are ready
podman-compose -f docker-compose.podman.yml logs -f
```

Wait until you see "Running on http://0.0.0.0:5000" from both admin and portal services.

### Step 4: Initialize the Database

```powershell
# Run database migrations for Admin Dashboard
podman-compose -f docker-compose.podman.yml exec admin python -c "
from admin.app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Admin tables created')
"

# Run database migrations for Portal
podman-compose -f docker-compose.podman.yml exec portal python -c "
from portal.app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Portal tables created')
"
```

### Step 5: Seed Demo Data

```powershell
# Seed the database with demo users and plans
podman-compose -f docker-compose.podman.yml exec admin python -c "
import os
os.environ['SEED_DEMO_DATA'] = 'true'
exec(open('/app/scripts/seed_data.py').read())
"
```

---

## Access the Platform

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Admin Dashboard** | http://localhost:5000 | Platform operator interface |
| **Customer Portal** | http://localhost:5001 | Customer self-service portal |
| **Grafana** | http://localhost:3000 | Monitoring dashboards |
| **Prometheus** | http://localhost:9090 | Metrics and alerting |
| **RQ Dashboard** | http://localhost:9181 | Background job monitoring |
| **Nginx Proxy** | http://localhost:8081 | Reverse proxy (production-like) |
| **AlertManager** | http://localhost:9093 | Alert management |

### Default Credentials

#### Admin Dashboard
- **Email:** admin@example.com
- **Password:** admin123

#### Customer Portal (Demo User)
- **Email:** demo@example.com
- **Password:** demo123

#### Grafana
- **Username:** admin
- **Password:** admin123

---

## Verify Everything is Working

### 1. Test Admin Dashboard

1. Open http://localhost:5000
2. Go to http://localhost:5000/health to verify health check
3. Login with admin credentials

### 2. Test Customer Portal

1. Open http://localhost:5001
2. Go to http://localhost:5001/health to verify health check
3. Login with demo credentials

### 3. Test API Endpoints

```powershell
# Test Admin API health
curl http://localhost:5000/health

# Test Portal API health
curl http://localhost:5001/health

# Login to Admin API (get JWT token)
curl -X POST http://localhost:5000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### 4. Test Monitoring

1. Open Grafana: http://localhost:3000
2. Login with admin/admin123
3. Go to Dashboards > Browse
4. You should see "Odoo SaaS Platform Overview" dashboard

---

## Common Commands

### Service Management

```powershell
# Start all services
podman-compose -f docker-compose.podman.yml up -d

# Stop all services
podman-compose -f docker-compose.podman.yml down

# Restart a specific service
podman-compose -f docker-compose.podman.yml restart admin

# View logs for all services
podman-compose -f docker-compose.podman.yml logs -f

# View logs for a specific service
podman-compose -f docker-compose.podman.yml logs -f admin

# Check service status
podman-compose -f docker-compose.podman.yml ps
```

### Database Operations

```powershell
# Connect to PostgreSQL
podman-compose -f docker-compose.podman.yml exec postgres psql -U odoo -d odoo_saas_platform

# Backup database
podman-compose -f docker-compose.podman.yml exec postgres pg_dump -U odoo odoo_saas_platform > backup.sql

# Restore database
type backup.sql | podman-compose -f docker-compose.podman.yml exec -T postgres psql -U odoo odoo_saas_platform
```

### Development Tools (Optional)

```powershell
# Start with development tools (Adminer, MailHog)
podman-compose -f docker-compose.podman.yml --profile dev up -d

# Access Adminer (database UI): http://localhost:8085
# Access MailHog (email capture): http://localhost:8025
```

---

## Troubleshooting

### Issue: Services fail to start

```powershell
# Check if ports are in use
netstat -ano | findstr :5000
netstat -ano | findstr :5432

# Kill process using the port (replace PID)
taskkill /PID <PID> /F

# Restart services
podman-compose -f docker-compose.podman.yml down
podman-compose -f docker-compose.podman.yml up -d --build
```

### Issue: Database connection errors

```powershell
# Check if PostgreSQL is healthy
podman-compose -f docker-compose.podman.yml exec postgres pg_isready -U odoo

# Check PostgreSQL logs
podman-compose -f docker-compose.podman.yml logs postgres

# Recreate PostgreSQL container (WARNING: loses data)
podman-compose -f docker-compose.podman.yml down -v
podman-compose -f docker-compose.podman.yml up -d --build
```

### Issue: Redis connection errors

```powershell
# Check if Redis is healthy
podman-compose -f docker-compose.podman.yml exec redis redis-cli ping

# Check Redis logs
podman-compose -f docker-compose.podman.yml logs redis
```

### Issue: Permission errors on Windows

```powershell
# Run PowerShell as Administrator
# Or adjust Podman machine settings
podman machine ssh
sudo chmod -R 777 /path/to/mounted/volumes
```

### Issue: Out of memory

```powershell
# Check Podman machine resources
podman machine inspect

# Increase memory (requires machine restart)
podman machine stop
podman machine set --memory 8192
podman machine start
```

---

## Production Considerations

### Security Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate secure SECRET_KEY: `openssl rand -hex 32`
- [ ] Enable HTTPS with proper SSL certificates
- [ ] Configure firewall rules
- [ ] Set up proper CORS origins
- [ ] Enable rate limiting
- [ ] Review container security settings

### Performance Optimization

1. **PostgreSQL Tuning:**
   - Adjust `shared_buffers` based on available RAM
   - Configure connection pooling
   - Set up regular VACUUM

2. **Redis Configuration:**
   - Set appropriate memory limits
   - Configure persistence strategy
   - Enable password authentication

3. **Application Scaling:**
   - Scale admin/portal replicas
   - Add more worker instances
   - Implement load balancing

### Backup Strategy

1. **Database Backups:**
   - Configure automated PostgreSQL backups
   - Test restore procedures regularly
   - Store backups in S3 or similar

2. **Application Data:**
   - Back up filestore volumes
   - Export Grafana dashboards
   - Document configuration changes

---

## Architecture Overview

```
                                    ┌─────────────────┐
                                    │     Users       │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │   Nginx:8081    │
                                    │ (Reverse Proxy) │
                                    └────────┬────────┘
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                 ┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐
                 │  Admin:5000     │ │  Portal:5001   │ │   Worker       │
                 │  (Flask App)    │ │  (Flask App)   │ │   (RQ Jobs)    │
                 └────────┬────────┘ └───────┬────────┘ └───────┬────────┘
                          │                  │                  │
         ┌────────────────┴──────────────────┴──────────────────┘
         │
         ├──────────────────────────────────────────┐
         │                                          │
┌────────▼────────┐                       ┌────────▼────────┐
│  PostgreSQL     │                       │     Redis       │
│    :5432        │                       │     :6379       │
└─────────────────┘                       └─────────────────┘

                    ┌─────────────────────────────────────────┐
                    │           Monitoring Stack              │
                    │                                         │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
                    │  │Prometheus│  │ Grafana │  │AlertMgr │ │
                    │  │  :9090   │  │  :3000  │  │  :9093  │ │
                    │  └─────────┘  └─────────┘  └─────────┘ │
                    └─────────────────────────────────────────┘
```

---

## Support

If you encounter issues:

1. Check the logs: `podman-compose -f docker-compose.podman.yml logs -f`
2. Verify service health: `podman-compose -f docker-compose.podman.yml ps`
3. Review environment variables in `.env`
4. Check GitHub Issues for known problems

---

**Happy Deploying!**
