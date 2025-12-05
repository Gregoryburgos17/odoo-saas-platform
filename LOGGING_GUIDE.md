# Odoo SaaS Platform - Logging Guide

## Overview

This guide explains how to retrieve logs from your Odoo SaaS Platform containers running on Podman, especially when working with remote Podman connections.

## The Problem with Remote Podman Logs

When running Podman remotely (e.g., connecting to a Podman machine from Windows), the standard `podman logs <container-name>` command may fail with:

```
Error: logs does not support multiple containers when run remotely
```

This happens when:
- Multiple containers match the service name (running + stopped containers)
- Podman is running in remote mode
- The container name pattern matches multiple results

## Solution: Use the Log Retrieval Scripts

We've created two scripts that handle this issue properly:

### Windows (PowerShell): `get_logs.ps1`
### Linux/Mac (Bash): `get_logs.sh`

Both scripts:
1. ✅ Query running containers specifically using `podman ps`
2. ✅ Extract exact container IDs
3. ✅ Retrieve logs using the specific container ID
4. ✅ Handle multiple matches gracefully
5. ✅ Provide clear error messages and status indicators

## Usage

### Windows (PowerShell)

```powershell
# Get last 50 lines from all services
.\get_logs.ps1

# Get last 100 lines from all services
.\get_logs.ps1 -TailLines 100

# Get logs for a specific service
.\get_logs.ps1 -Service odoo-saas-admin

# Follow logs in real-time (continuous output)
.\get_logs.ps1 -Follow

# Combine options
.\get_logs.ps1 -Service odoo-saas-portal -TailLines 200
```

### Linux/Mac (Bash)

```bash
# Make script executable (first time only)
chmod +x ./get_logs.sh

# Get last 50 lines from all services
./get_logs.sh

# Get last 100 lines from all services
./get_logs.sh -n 100

# Get logs for a specific service
./get_logs.sh -s odoo-saas-admin

# Follow logs in real-time (continuous output)
./get_logs.sh -f

# Combine options
./get_logs.sh -s odoo-saas-portal -n 200

# Show help
./get_logs.sh -h
```

## Available Services

The scripts retrieve logs from these services:

| Service Name | Description |
|-------------|-------------|
| `odoo-saas-admin` | Admin Dashboard Service |
| `odoo-saas-portal` | Customer Portal Service |
| `odoo-saas-worker` | RQ Worker for background jobs |
| `odoo-saas-nginx` | Nginx reverse proxy |
| `odoo-saas-postgres` | PostgreSQL Database |
| `odoo-saas-redis` | Redis cache and job queue |

## Output Example

```
╔════════════════════════════════════════════════════════════════╗
║     ODOO SAAS PLATFORM - LOG RETRIEVAL                        ║
╚════════════════════════════════════════════════════════════════╝
--- LOGS GENERATED AT 12/05/2025 14:30:15 ---

================================================================
 SERVICE: odoo-saas-admin
================================================================
📦 Container ID: a1b2c3d4e5f6
 * Serving Flask app 'admin.app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
...

================================================================
 SERVICE: odoo-saas-portal
================================================================
📦 Container ID: f6e5d4c3b2a1
 * Serving Flask app 'portal.run:app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
...
```

## Troubleshooting

### "Container not running or not found"

This means the container is not currently running. Check container status:

```bash
podman ps -a | grep odoo-saas
```

Start the services:

```bash
podman-compose -f docker-compose.podman.yml up -d
```

### "Multiple containers found"

The script will automatically use the first running container but will show you all matches. To clean up old containers:

```bash
# Remove stopped containers
podman container prune

# Or remove specific stopped containers
podman rm <container-id>
```

### Permission Issues (Linux/Mac)

If you get a permission error, make sure the script is executable:

```bash
chmod +x ./get_logs.sh
```

## Direct Podman Commands (Advanced)

If you need to use Podman commands directly:

```bash
# List all running containers with IDs
podman ps

# Get logs using exact container ID
podman logs --tail 50 <container-id>

# Follow logs for a specific container
podman logs -f <container-id>

# Get logs with timestamps
podman logs --timestamps <container-id>

# Get logs since a specific time
podman logs --since 10m <container-id>
```

## Integration with Development Workflow

### Debugging Issues

1. **Check service health**:
   ```bash
   podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   ```

2. **Get recent logs**:
   ```bash
   ./get_logs.sh -s odoo-saas-admin -n 100
   ```

3. **Monitor in real-time**:
   ```bash
   ./get_logs.sh -s odoo-saas-admin -f
   ```

### Save Logs to File

**PowerShell:**
```powershell
.\get_logs.ps1 | Out-File -FilePath "logs_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
```

**Bash:**
```bash
./get_logs.sh > logs_$(date +%Y%m%d_%H%M%S).txt
```

### Filter Logs

**PowerShell:**
```powershell
.\get_logs.ps1 -Service odoo-saas-admin | Select-String "ERROR"
```

**Bash:**
```bash
./get_logs.sh -s odoo-saas-admin | grep "ERROR"
```

## Automated Log Collection

You can schedule regular log collection:

### Windows Task Scheduler

Create a scheduled task to run:
```powershell
.\get_logs.ps1 | Out-File -Append -FilePath "C:\logs\odoo-saas-$(Get-Date -Format 'yyyyMMdd').log"
```

### Linux Cron

Add to crontab:
```bash
*/30 * * * * cd /path/to/odoo-saas-platform && ./get_logs.sh >> /var/log/odoo-saas-$(date +\%Y\%m\%d).log 2>&1
```

## Related Documentation

- [Podman Compose Guide](./PODMAN_GUIDE.md)
- [Service Restart Scripts](./SERVICE_RESTART_GUIDE.md)
- [Development Setup](./README.md)

## Support

If you continue to experience issues:

1. Check that Podman is running: `podman version`
2. Verify containers are running: `podman ps`
3. Check Podman machine status (Windows): `podman machine list`
4. Review compose file: `docker-compose.podman.yml`

---

**Note**: These scripts are designed specifically to work with remote Podman connections and handle edge cases that the standard `podman logs` command cannot handle in remote mode.
