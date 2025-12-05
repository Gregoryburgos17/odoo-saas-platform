"""
Background Jobs Module
Contains all job definitions for async task processing
"""

# Import available jobs
try:
    from workers.jobs.tenant_jobs import (
        provision_tenant_job,
        delete_tenant_job,
        install_module_job,
        uninstall_module_job,
        backup_tenant_job,
        restore_tenant_job
    )
    TENANT_JOBS_AVAILABLE = True
except ImportError:
    TENANT_JOBS_AVAILABLE = False

__all__ = []

if TENANT_JOBS_AVAILABLE:
    __all__.extend([
        'provision_tenant_job',
        'delete_tenant_job',
        'install_module_job',
        'uninstall_module_job',
        'backup_tenant_job',
        'restore_tenant_job'
    ])
