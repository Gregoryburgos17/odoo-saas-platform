# ===========================================
# Odoo ERP - Dockerfile
# Multi-tenant Configuration
# ===========================================

FROM docker.io/odoo:17.0

# Set environment variables
ENV ODOO_RC=/etc/odoo/odoo.conf

# Switch to root for installations
USER root

# Install additional system packages (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create directories for custom addons
RUN mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons

# Ensure proper permissions for Odoo directories
RUN mkdir -p /var/lib/odoo \
    && chown -R odoo:odoo /var/lib/odoo

# Copy custom configuration
COPY odoo.conf /etc/odoo/odoo.conf
RUN chown odoo:odoo /etc/odoo/odoo.conf

# Switch back to odoo user
USER odoo

# Expose ports
EXPOSE 8069 8072

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8069/web/health || exit 1

# Default command
CMD ["odoo"]
