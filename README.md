# Odoo SaaS Platform

A complete multi-tenant Odoo SaaS platform built with Flask, optimized for **Podman on Windows**.

## Features

- **Admin Dashboard**: Manage customers, tenants, plans, and view system statistics
- **Customer Portal**: Self-service tenant management, billing, and support
- **Multi-tenant Architecture**: Database-per-tenant isolation
- **Background Workers**: Async job processing with Redis Queue (RQ)
- **API-First Design**: RESTful APIs with JWT authentication
- **Ready for Production**: Nginx reverse proxy, health checks, monitoring

## Quick Start (Windows with Podman)

### Prerequisites

1. Install [Podman Desktop for Windows](https://podman-desktop.io/)
2. Install [podman-compose](https://github.com/containers/podman-compose):
   ```powershell
   pip install podman-compose
   ```

### Start the Platform

```powershell
# Clone and navigate to directory
cd odoo-saas-platform

# Copy environment file
copy .env.example .env

# Start all services
podman-compose up -d

# View logs
podman-compose logs -f

# Seed demo data
podman-compose exec admin python /app/scripts/seed_data.py
```

### Access Services

| Service | URL | Description |
|---------|-----|-------------|
| Admin Dashboard | http://localhost:5000 | Admin management panel |
| Customer Portal | http://localhost:5001 | Customer self-service |
| Nginx (Admin) | http://localhost:80 | Proxied admin access |
| Nginx (Portal) | http://localhost:8080 | Proxied portal access |
| RQ Dashboard | http://localhost:9181 | Job queue monitoring |
| Adminer | http://localhost:8085 | Database management |

### Default Credentials

After seeding:
- **Admin**: `admin@example.com` / `admin123`
- **Demo Customer**: `demo@example.com` / `demo123`

## Project Structure

```
odoo-saas-platform/
├── admin/                  # Admin Dashboard (Flask)
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   └── utils/         # Utilities
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run.py
├── portal/                 # Customer Portal (Flask)
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   └── utils/         # Utilities
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run.py
├── workers/                # Background Workers (RQ)
│   ├── app/
│   ├── jobs/              # Job definitions
│   ├── Dockerfile
│   └── requirements.txt
├── shared/                 # Shared code
│   ├── models.py          # SQLAlchemy models
│   └── database.py        # Database utilities
├── nginx/                  # Nginx configuration
│   └── nginx.conf
├── scripts/                # Utility scripts
│   ├── init-db.sql
│   └── seed_data.py
├── podman-compose.yml      # Container orchestration
├── .env.example            # Environment template
└── README.md
```

## API Documentation

### Admin Dashboard API

#### Authentication
```
POST /api/auth/register    - Register admin user
POST /api/auth/login       - Login
POST /api/auth/refresh     - Refresh token
POST /api/auth/logout      - Logout
GET  /api/auth/me          - Current user profile
POST /api/auth/change-password
```

#### Tenants
```
GET    /api/tenants        - List all tenants
POST   /api/tenants        - Create tenant
GET    /api/tenants/:id    - Get tenant
PUT    /api/tenants/:id    - Update tenant
DELETE /api/tenants/:id    - Delete tenant
POST   /api/tenants/:id/suspend
POST   /api/tenants/:id/resume
```

#### Customers
```
GET    /api/customers      - List customers
POST   /api/customers      - Create customer
GET    /api/customers/:id  - Get customer
PUT    /api/customers/:id  - Update customer
DELETE /api/customers/:id  - Delete customer
```

#### Plans
```
GET    /api/plans          - List plans
POST   /api/plans          - Create plan
GET    /api/plans/:id      - Get plan
PUT    /api/plans/:id      - Update plan
DELETE /api/plans/:id      - Delete plan
```

#### Dashboard
```
GET /api/dashboard/stats   - Overview statistics
GET /api/dashboard/recent-activity
GET /api/dashboard/tenant-growth
```

### Customer Portal API

#### Authentication
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
PUT  /api/auth/me
POST /api/auth/change-password
```

#### Tenants (Customer's own)
```
GET    /api/tenants        - List my tenants
POST   /api/tenants        - Create tenant
GET    /api/tenants/:id    - Get tenant
PUT    /api/tenants/:id    - Update tenant
DELETE /api/tenants/:id    - Delete tenant
POST   /api/tenants/:id/backup
GET    /api/tenants/:id/backups
```

#### Billing
```
GET    /api/billing/plans       - List available plans
GET    /api/billing/subscription - Get subscription
POST   /api/billing/subscribe    - Subscribe to plan
PUT    /api/billing/subscription - Change plan
DELETE /api/billing/subscription - Cancel
GET    /api/billing/usage        - Usage metrics
```

#### Support
```
GET    /api/support/tickets     - List tickets
POST   /api/support/tickets     - Create ticket
GET    /api/support/tickets/:id - Get ticket
PUT    /api/support/tickets/:id - Update ticket
POST   /api/support/tickets/:id/close
GET    /api/support/faq
```

## Development

### Local Development (Without Containers)

```bash
# Install dependencies
pip install -r admin/requirements.txt
pip install -r portal/requirements.txt
pip install -r workers/requirements.txt

# Set environment variables
export PG_HOST=localhost
export REDIS_HOST=localhost

# Run services
python admin/run.py &
python portal/run.py &
python workers/run.py &
```

### Useful Commands

```powershell
# Start services
podman-compose up -d

# Stop services
podman-compose down

# Rebuild after code changes
podman-compose build
podman-compose up -d

# View specific service logs
podman-compose logs -f admin
podman-compose logs -f portal
podman-compose logs -f worker

# Execute commands in container
podman-compose exec admin python -c "from shared.database import init_db; init_db()"

# Database shell
podman-compose exec postgres psql -U odoo -d odoo_saas

# Redis CLI
podman-compose exec redis redis-cli

# Enable dev tools (Adminer)
podman-compose --profile dev-tools up -d
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | development | Environment mode |
| `SECRET_KEY` | - | Flask secret key |
| `JWT_SECRET_KEY` | - | JWT signing key |
| `PG_HOST` | postgres | PostgreSQL host |
| `PG_USER` | odoo | PostgreSQL user |
| `PG_PASSWORD` | - | PostgreSQL password |
| `PG_DATABASE` | odoo_saas | Database name |
| `REDIS_HOST` | redis | Redis host |
| `DEFAULT_TRIAL_DAYS` | 14 | Trial period |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Admin Dashboard │     │ Customer Portal │
│   (Port 5000)   │     │   (Port 5001)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │    Nginx    │
              │ (Port 80/8080)│
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
    │PostgreSQL│ │  Redis  │ │ Workers │
    │ (5432)  │ │ (6379)  │ │  (RQ)   │
    └─────────┘ └─────────┘ └─────────┘
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub Issues page.
