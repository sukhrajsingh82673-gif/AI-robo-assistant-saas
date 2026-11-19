# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Canonical Control Plane & Staging Container
# Multi-stage security-hardened container running unprivileged (non-root UID 10001)

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    ZONATA_ENV=PRODUCTION \
    HOME=/app

WORKDIR /app

# Install security updates and curl for container health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install pinned production dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create unprivileged zonata user and group
RUN groupadd -g 10001 zonata && \
    useradd -u 10001 -g zonata -s /bin/bash -m zonata

# Copy application files
COPY --chown=zonata:zonata . /app

# Create storage and runtime directories with correct permissions
RUN mkdir -p /app/storage/evidence /app/storage/data /app/storage/backups && \
    chown -R zonata:zonata /app/storage

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8080}/readyz || exit 1

ENTRYPOINT ["python3", "api_server.py"]
CMD ["8080"]
