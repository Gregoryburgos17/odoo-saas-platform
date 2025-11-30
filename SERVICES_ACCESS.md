# Odoo SaaS Platform - Services Access Guide

## 🔐 Default Credentials & Service URLs

### Admin Dashboard
- **URL**: http://localhost:5000
- **Credentials**: Create using CLI command below

### Customer Portal
- **URL**: http://localhost:5001
- **Credentials**: Register new user or use admin credentials

### Grafana (Monitoring)
- **URL**: http://localhost:3000
- **Default Username**: `admin`
- **Default Password**: `admin123`
- **Note**: Change password after first login in production

### RQ Dashboard (Job Queue Monitoring)
- **URL**: http://localhost:9181
- **Authentication**: None (development)

### Prometheus (Metrics)
- **URL**: http://localhost:9090
- **Authentication**: None

### Adminer (Database Management)
- **URL**: http://localhost:8085
- **Server**: `postgres`
- **Username**: `odoo`
- **Password**: `password`
- **Database**: `odoo_saas_platform`

### PostgreSQL Database
- **Host**: localhost
- **Port**: 5432
- **Username**: `odoo`
- **Password**: `password`
- **Database**: `odoo_saas_platform`

### Redis
- **Host**: localhost
- **Port**: 6379
- **Password**: None (empty) in development
- **Database**: 0

---

## 🚀 Quick Start Commands

### Create Admin User
```bash
# Enter the admin container
docker exec -it odoo-saas-admin bash

# Create admin user interactively
flask create-admin

# Or using Python
python -c "
from admin.app import create_app, db
from shared.models import Customer, CustomerRole

app = create_app()
with app.app_context():
    admin = Customer(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        role=CustomerRole.ADMIN.value,
        is_active=True,
        is_verified=True,
        max_tenants=999,
        max_quota_gb=999
    )
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    print('✅ Admin user created: admin@example.com / admin123')
"
```

### Initialize Database
```bash
# Enter the admin container
docker exec -it odoo-saas-admin bash

# Initialize database
flask init-db

# With demo data
flask init-db --seed-demo
```

### Check Service Health
```bash
# Admin Dashboard
curl http://localhost:5000/health

# Customer Portal
curl http://localhost:5001/health
```

---

## 🔧 Troubleshooting

### Grafana Login Issues
- **Problem**: "Invalid username or password"
- **Solution**: Use username `admin` (not email) with password `admin123`
- **Reset Password**:
  ```bash
  docker exec -it odoo-saas-grafana grafana-cli admin reset-admin-password admin123
  ```

### RQ Dashboard Redis Authentication Error
- **Problem**: "Authentication required"
- **Solution**: Already fixed in docker-compose.yml. Restart services:
  ```bash
  docker-compose down
  docker-compose up -d rq-dashboard
  ```

### Admin App Flask-Limiter Error
- **Problem**: "TypeError: Limiter.__init__() got an unexpected keyword argument"
- **Solution**: Already fixed in admin/app/__init__.py. Rebuild container:
  ```bash
  docker-compose build admin
  docker-compose up -d admin
  ```

### Port Conflicts
If any ports are already in use, you can modify them in `docker-compose.yml`:
- Admin Dashboard: Change `5000:5000` to `5050:5000`
- Portal: Change `5001:5000` to `5051:5000`
- Grafana: Change `3000:3000` to `3030:3000`

---

## 📊 Service Status

Check all services are running:
```bash
docker-compose ps
```

View service logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f admin
docker-compose logs -f portal
docker-compose logs -f grafana
```

---

## ⚠️ Security Notes

**FOR DEVELOPMENT ONLY**

These default credentials are for development purposes only.

**Before deploying to production:**
1. Change all default passwords in `.env`
2. Set strong random passwords using: `openssl rand -hex 32`
3. Enable Redis authentication with a strong password
4. Configure proper TLS/SSL certificates
5. Set `DEBUG=false` and `FLASK_DEBUG=false`
6. Review and update CORS_ALLOWED_ORIGINS
7. Configure proper SMTP settings
8. Enable 2FA if needed

---

## 🆘 Getting Help

- Check logs: `docker-compose logs [service-name]`
- Restart services: `docker-compose restart [service-name]`
- Rebuild containers: `docker-compose build [service-name]`
- Reset everything: `docker-compose down -v && docker-compose up -d`
