# Admin Dashboard Dockerfile
# Optimized for Podman on Windows

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user and directory
RUN groupadd -r appgroup && useradd -r -g appgroup appuser \
    && mkdir -p /app \
    && chown -R appuser:appgroup /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY --chown=appuser:appgroup ../shared /app/shared/

# Copy application code
COPY --chown=appuser:appgroup . /app/admin/

# Set working directory to admin
WORKDIR /app/admin

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "run.py"]
