# Odoo SaaS Platform - Deployment Context & Issues

## 🎯 PROJECT OVERVIEW
Multi-tenant Odoo SaaS platform using Podman on Windows with the following architecture:
- **Admin Dashboard** (Flask, port 5000) - Tenant management interface
- **Customer Portal** (Flask, port 5001) - Customer self-service portal
- **Background Workers** (RQ workers) - Async job processing
- **PostgreSQL** (port 5432) - Main database
- **Redis** (port 6379) - Cache and job queue
- **Nginx** (port 8081) - Reverse proxy
- **Grafana** (port 3000) - Monitoring dashboards
- **Prometheus** (port 9090) - Metrics collection
- **RQ Dashboard** (port 9181) - Job queue monitoring
- **Adminer** (port 8085) - Database management UI

## 🔧 ENVIRONMENT DETAILS
- **OS**: Windows with Podman (rootless containers)
- **Container Runtime**: Podman (NOT Docker)
- **Orchestration**: podman-compose
- **Branch**: `claude/fix-alertmanager-config-path-01HPBNpWdMALpiwFbM3TZKrQ`
- **Python Version**: 3.11
- **Podman Quirk**: Requires "Containerfile" instead of "Dockerfile" on Windows

## 🐛 ISSUES IDENTIFIED & FIXES APPLIED

### 1. ✅ Alertmanager Configuration Error
**Error**: `err="read /etc/alertmanager/config.yml: is a directory"`
**Fix**: Created `monitoring/alertmanager/config.yml` with proper YAML configuration
**File**: `monitoring/alertmanager/config.yml`

### 2. ✅ Prometheus Port Conflict
**Error**: `listen tcp 127.0.0.1:9090: bind: address already in use`
**Fix**: Changed port mapping to `9092:9090` in docker-compose.complete.yml
**File**: `docker-compose.complete.yml:143`

### 3. ✅ Missing Python Modules - marshmallow
**Error**: `ModuleNotFoundError: No module named 'marshmallow'`
**Fix**: Added `marshmallow==3.20.1` to requirements.txt
**Files**:
- `admin/requirements.txt` (line 20)
- `portal/requirements.txt` (line 16)

### 4. ✅ Missing Python Modules - werkzeug (workers)
**Error**: `ModuleNotFoundError: No module named 'werkzeug'`
**Fix**: Added `werkzeug==3.0.1` to workers requirements
**File**: `workers/requirements.txt` (line 22)

### 5. ✅ Portal Web Module Missing
**Error**: `ModuleNotFoundError: No module named 'portal.app.web'`
**Fix**: Created `portal/app/web/__init__.py` with web blueprint
**File**: `portal/app/web/__init__.py` (68 lines)

### 6. ✅ Portal Network Binding Issue
**Error**: Portal not accessible from nginx (ERR_EMPTY_RESPONSE)
**Root Cause**: Listening on 127.0.0.1 instead of 0.0.0.0
**Fix**: Changed default host to `0.0.0.0` in portal/run.py
**File**: `portal/run.py:124`

### 7. ✅ RQ Dashboard Redis Connection Error
**Error**: `Error -2 connecting to }redis:6379. Name or service not known`
**Root Cause**: Complex shell substitution in REDIS_URL variable
**Fix**: Simplified to `redis://redis:6379/0`
**File**: `docker-compose.yml:177`

### 8. ✅ Worker request_stop() Signature Error
**Error**: `TypeError: Worker.request_stop() missing 2 required positional arguments`
**Fix**: Pass signal arguments: `self.worker.request_stop(sig.SIGTERM, None)`
**File**: `workers/app/worker.py:174`

### 9. ✅ SQLAlchemy Type Errors
**Error**: `ImportError: cannot import name 'Decimal' from 'sqlalchemy'`
**Fix**: Changed to import from `decimal` module and use `Numeric` column type
**File**: `shared/models.py`

### 10. ✅ Reserved Column Name
**Error**: `Attribute name 'metadata' is reserved`
**Fix**: Renamed to `extra_metadata` in AuditLog model
**File**: `shared/models.py`

### 11. ✅ Port Conflicts - Adminer
**Error**: Port 8080 occupied by another application
**Fix**: Changed Adminer port from 8080 to 8085
**File**: `docker-compose.yml:255`

### 12. ✅ Port Conflicts - Nginx
**Error**: Rootless podman cannot expose privileged port 80
**Fix**: Changed nginx ports from 80/443 to 8081/8443
**File**: `docker-compose.yml:195`

### 13. ✅ Database Credentials Mismatch
**Error**: `password authentication failed for user "odoo"`
**Fix**: Created `.env` file with consistent credentials
**File**: `.env` (not committed to git)

### 14. ⚠️ Worker Registration Conflict
**Error**: `There exists an active worker named 'worker-1' already`
**Root Cause**: Old worker registrations in Redis
**Solution**: Flush Redis or remove specific worker keys

## 📁 KEY FILES MODIFIED

### Configuration Files
- `docker-compose.yml` - Main orchestration (ports, Redis URL)
- `docker-compose.complete.yml` - Production config (Prometheus port)
- `.env` - Environment variables (local only, not in git)

### Python Requirements
- `admin/requirements.txt` - Added marshmallow, werkzeug
- `portal/requirements.txt` - Added marshmallow
- `workers/requirements.txt` - Added werkzeug

### Application Code
- `portal/run.py` - Changed host binding to 0.0.0.0
- `portal/app/web/__init__.py` - Created web blueprint module
- `workers/app/worker.py` - Fixed request_stop() signature
- `shared/models.py` - Fixed Decimal imports and reserved names
- `shared/database.py` - Created database session manager

### Monitoring
- `monitoring/alertmanager/config.yml` - Created alertmanager config

### Containerfiles (Podman specific)
All services have both Dockerfile and Containerfile:
- `admin/Containerfile`
- `portal/Containerfile`
- `workers/Containerfile`
- `backup-service/Containerfile`
- `odoo-service/Containerfile`

## 🔑 CREDENTIALS & ENDPOINTS

### Database
- Host: postgres (internal) / localhost:5432 (external)
- User: odoo
- Password: password
- Database: odoo_saas_platform

### Redis
- Host: redis (internal) / localhost:6379 (external)
- Password: (empty)

### Service Endpoints
- Admin Dashboard: http://localhost:5000
- Customer Portal: http://localhost:5001
- Nginx Proxy: http://localhost:8081
- RQ Dashboard: http://localhost:9181
- Grafana: http://localhost:3000 (admin/admin123)
- Prometheus: http://localhost:9090
- Adminer: http://localhost:8085

### Grafana
- Username: admin
- Password: admin123

## 🚨 CRITICAL DEPLOYMENT STEPS

### Step 1: Ensure Latest Code
```powershell
git pull origin claude/fix-alertmanager-config-path-01HPBNpWdMALpiwFbM3TZKrQ
```

### Step 2: Stop All Containers
```powershell
podman-compose -f docker-compose.yml down
```

### Step 3: Clean Redis Worker Registry
```powershell
# Start only Redis
podman start odoo-saas-redis

# Clear worker registrations
podman exec odoo-saas-redis redis-cli FLUSHALL

# Or more selectively:
podman exec odoo-saas-redis redis-cli DEL rq:workers
podman exec odoo-saas-redis redis-cli KEYS "rq:worker:*" | xargs -I {} podman exec odoo-saas-redis redis-cli DEL {}

# Stop Redis
podman stop odoo-saas-redis
```

### Step 4: Rebuild ALL Images with --no-cache
```powershell
# Admin
podman build --no-cache -t localhost/odoo-saas-admin:latest -f admin/Containerfile .

# Portal
podman build --no-cache -t localhost/odoo-saas-portal:latest -f portal/Containerfile .

# Workers
podman build --no-cache -t localhost/odoo-saas-worker:latest -f workers/Containerfile .

# Backup Service (if needed)
podman build --no-cache -t localhost/odoo-saas-backup:latest -f backup-service/Containerfile .
```

### Step 5: Recreate Database Container (if needed)
```powershell
# Only if database credentials were wrong
podman rm -f odoo-saas-postgres
podman volume rm odoo-saas-platform_postgres_data
```

### Step 6: Start All Services
```powershell
podman-compose -f docker-compose.yml up -d
```

### Step 7: Wait for Initialization
```powershell
# Wait 30 seconds
Start-Sleep -Seconds 30
```

### Step 8: Verify Services
```powershell
# Check container status
podman-compose -f docker-compose.yml ps

# Check logs
podman logs odoo-saas-admin --tail 20
podman logs odoo-saas-portal --tail 20
podman logs odoo-saas-worker --tail 20
podman logs odoo-saas-rq-dashboard --tail 20
```

### Step 9: Create Database (if new)
```powershell
podman exec odoo-saas-postgres psql -U odoo -d postgres -c "CREATE DATABASE odoo_saas_platform;"
```

## 🔍 TROUBLESHOOTING

### Issue: "ModuleNotFoundError" after rebuild
**Cause**: Build cache is using old requirements
**Solution**: Use `--no-cache` flag when building images

### Issue: Portal shows ERR_EMPTY_RESPONSE
**Cause**: Portal listening on 127.0.0.1 instead of 0.0.0.0
**Check**: `podman logs odoo-saas-portal` should show "Starting Customer Portal on 0.0.0.0:5001"
**Solution**: Rebuild portal image

### Issue: Worker "already exists" error
**Cause**: Old worker registration in Redis
**Solution**: Run `podman exec odoo-saas-redis redis-cli FLUSHALL`

### Issue: "password authentication failed"
**Cause**: Database container has different password than .env
**Solution**: Recreate postgres container and volume

### Issue: RQ Dashboard connection error
**Cause**: Redis URL malformed
**Check**: Should be `redis://redis:6379/0` (no braces or substitution)
**Solution**: Recreate rq-dashboard container

### Issue: Nginx 502 Bad Gateway
**Cause**: Backend services (admin/portal) not running or not accessible
**Check**:
- `podman logs odoo-saas-admin`
- `podman logs odoo-saas-portal`
- Ensure both show "Running on 0.0.0.0:500X"

## 📊 EXPECTED LOG OUTPUT

### Admin (Healthy)
```
✅ Database tables created/verified
🚀 Starting Admin Dashboard on http://0.0.0.0:5000
📝 Environment: development
🔧 Debug mode: True
* Running on all addresses (0.0.0.0)
* Running on http://127.0.0.1:5000
```

### Portal (Healthy)
```
Starting Customer Portal on 0.0.0.0:5001
Environment: development
Debug mode: True
* Running on http://0.0.0.0:5001
```

### Worker (Healthy)
```
Connected to Redis at redis:6379
Initialized queue: high
Initialized queue: default
Initialized queue: low
Starting background job worker...
Created worker: worker-1
Starting worker worker-1 for queues: ['high', 'default', 'low']
```

### RQ Dashboard (Healthy)
```
RQ Dashboard version 0.6.0
* Running on 0.0.0.0:9181
```

## 🔄 COMMON MISTAKES

1. **Not rebuilding images** - Just restarting containers won't pick up code changes
2. **Using Docker commands** - Must use `podman` and `podman-compose`
3. **Forgetting --no-cache** - Build cache can cause old dependencies to persist
4. **Not cleaning Redis** - Old worker registrations cause conflicts
5. **Wrong database password** - Container was created with different password than .env

## 📝 NOTES

- All fixes are committed to branch `claude/fix-alertmanager-config-path-01HPBNpWdMALpiwFbM3TZKrQ`
- `.env` file is NOT in git (must be created locally)
- Images MUST be rebuilt after code changes
- Podman on Windows requires Containerfiles, not Dockerfiles
- Rootless Podman cannot use ports < 1024

## 🎯 SUCCESS CRITERIA

✅ All containers show "Up" status in `podman-compose ps`
✅ Admin accessible at http://localhost:5000 (returns JSON)
✅ Portal accessible at http://localhost:5001 (returns JSON)
✅ RQ Dashboard shows no Redis connection errors
✅ Worker logs show "Starting worker" without errors
✅ Nginx returns admin/portal pages (not 502)
✅ Grafana login works with admin/admin123

## 🆘 LAST RESORT

If nothing works after following all steps:

```powershell
# Nuclear option - full cleanup
podman-compose -f docker-compose.yml down -v
podman system prune -a -f
podman volume prune -f

# Rebuild everything
podman build --no-cache -t localhost/odoo-saas-admin:latest -f admin/Containerfile .
podman build --no-cache -t localhost/odoo-saas-portal:latest -f portal/Containerfile .
podman build --no-cache -t localhost/odoo-saas-worker:latest -f workers/Containerfile .

# Start fresh
podman-compose -f docker-compose.yml up -d
```
