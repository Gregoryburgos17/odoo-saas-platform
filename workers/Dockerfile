# Workers Dockerfile
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
    && mkdir -p /app /tmp/backups \
    && chown -R appuser:appgroup /app /tmp/backups

WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY --chown=appuser:appgroup ../shared /app/shared/

# Copy application code
COPY --chown=appuser:appgroup . /app/workers/

# Set working directory to workers
WORKDIR /app/workers

# Switch to non-root user
USER appuser

# Run the worker
CMD ["python", "run.py"]
