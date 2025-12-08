# Workers Dockerfile
# Optimized for Podman on Windows

FROM docker.io/library/python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies including PostgreSQL client for backups
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create backup directory
RUN mkdir -p /tmp/backups

# Copy and install requirements
COPY workers/requirements.txt /app/workers/requirements.txt
RUN pip install --no-cache-dir -r /app/workers/requirements.txt

# Copy shared module first
COPY shared /app/shared/

# Copy workers application
COPY workers /app/workers/

# Create non-root user
RUN useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app /tmp/backups
USER appuser

# Set working directory to workers
WORKDIR /app/workers

# Run the worker
CMD ["python", "run.py"]
