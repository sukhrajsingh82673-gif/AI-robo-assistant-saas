# URA / ZONATA SaaS — Production Deployment Runbook

**Document Version**: 1.0.0-GA  
**Target Environment**: Production Cloud Infrastructure (Docker Swarm / Kubernetes / Docker Compose)  
**Security Classification**: Confidential Enterprise Operations  
**Date**: 13 October 2026  
**Audited Branch**: `engineering/production-readiness-gap-closure`

---

## 1. System Overview & Architecture

URA / ZONATA is an enterprise AI Company Operating System providing autonomous agents, statutory financial controls, document management, and robotic execution. In production, it operates in a multi-tenant dual-engine architecture:
- **API Server & App Shell**: Python 3.12+ multi-threaded server serving authenticated REST APIs and static SPA assets.
- **Database**: Dedicated PostgreSQL 16+ instance with connection pooling.
- **Message Broker & Event Bus**: NATS JetStream 2.10+.
- **Durable Workflows**: Temporal Server 1.24+.
- **Object Storage**: S3-compatible object store (AWS S3, Cloudflare R2, or MinIO).
- **Reverse Proxy**: NGINX / Caddy with TLS 1.3 termination and HTTP/2.

---

## 2. Infrastructure Prerequisites

| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Compute (Host)** | 4 vCPU, 16 GB RAM | 8 vCPU, 32 GB RAM (Dedicated Host) |
| **Storage (Disk)** | 100 GB NVMe SSD | 500 GB NVMe SSD with automated daily snapshots |
| **Operating System** | Ubuntu 22.04 LTS / Debian 12 | Ubuntu 24.04 LTS / RHEL 9 |
| **Container Engine** | Docker Engine 25.0+ & Compose v2 | Docker Engine 26.0+ with containerd runtime |
| **Network & Ingress** | Public IPv4, Ports 80 & 443 | Load balancer with DDoS mitigation & WAF |
| **TLS Certificate** | Let's Encrypt automated TLS | Cloudflare SSL / Digicert wildcard certificate |

---

## 3. Environment Configuration (`.env.production`)

Copy `.env.production.example` to `.env.production` and populate all mandatory production secrets:

```bash
cp .env.production.example .env.production
chmod 600 .env.production
```

### Critical Environment Variables Checklist

```ini
# Production Core Flags
APP_ENV=production
ZONATA_ENV=production
PORT=8080
ZONATA_STRICT_AUTH=1
ZONATA_DISABLE_DEMO_SEED=1
ZONATA_CLEAN_STARTUP=1
ZONATA_REQUIRE_EXPLICIT_SECRET=1

# Sovereign Cryptographic Secret (MUST BE 64 HEX CHARACTERS OR >= 32 BYTES)
# Generate via: openssl rand -hex 32
ZONATA_AUTH_SECRET=9f8c2e71b4a035d8e1694f27ca3b51908271e6205738ab4c19ef01678234abcd
ZONATA_BOOTSTRAP_SECRET=admin_bootstrap_key_prod_2026_x89f

# PostgreSQL Production Connection String
DATABASE_URL=postgresql://zonata_admin:YourStrongSecretPassword123!@postgres:5432/zonata_production
DB_POOL_MIN=5
DB_POOL_MAX=25
DB_POOL_TIMEOUT=30

# File Storage
ZONATA_STORAGE_DIR=/app/storage
ZONATA_EVIDENCE_DIR=/app/storage/evidence

# Third-Party Production Integration Keys (Leave blank if unconfigured; never use fake keys)
STRIPE_SECRET_KEY=
QUICKBOOKS_CLIENT_ID=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

---

## 4. Step-by-Step Deployment Instructions

### Step 4.1: Clone and Checkout Validated Baseline Release
```bash
git clone https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git /opt/zonata
cd /opt/zonata
git checkout engineering/production-readiness-gap-closure
```

### Step 4.2: Verify Cryptographic Invariant Baseline Hashes
Before launching, confirm that baseline database and ledger assets match their certified digests:
```bash
sha256sum storage/roboassistant.db storage/evidence/audit_ledger.jsonl
# Expected output:
# ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4  storage/roboassistant.db
# ca8181ec9314f281acad3512a34d32323fc195e6eed9f6412d7262e1e6dd0996  storage/evidence/audit_ledger.jsonl

git hash-object web/workflow_workspace.js
# Expected output:
# 198d57ec6bda875cd2a6825fe2ef8929b7ba30bd
```

### Step 4.3: Build Container Images
Build the production multi-stage images for the API server and worker daemon:
```bash
docker compose -f docker-compose.prod.yml build
```

### Step 4.4: Launch Infrastructure Stack
Start PostgreSQL, NATS, Temporal, MinIO, and Monitoring services:
```bash
docker compose -f docker-compose.prod.yml up -d postgres nats temporal minio
```

Wait 15 seconds for PostgreSQL healthy status:
```bash
docker compose -f docker-compose.prod.yml ps postgres
# Status should report: Up (healthy)
```

### Step 4.5: Run Schema Migration & Database Initialization
Execute the schema migration script against PostgreSQL:
```bash
docker compose -f docker-compose.prod.yml run --rm zonata-api python3 -c "
from core.db import db
db.initialize()
print('PostgreSQL production schema initialized successfully.')
"
```

### Step 4.6: Launch Application API & Worker Daemons
Start the complete application stack:
```bash
docker compose -f docker-compose.prod.yml up -d zonata-api zonata-worker otel-collector prometheus grafana
```

---

## 5. Reverse Proxy & TLS Configuration

Deploy NGINX as the TLS termination reverse proxy:

```nginx
# /etc/nginx/sites-available/zonata.conf
server {
    listen 80;
    server_name app.zonata.internal zonata.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.zonata.internal zonata.example.com;

    ssl_certificate /etc/letsencrypt/live/zonata.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/zonata.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for agent telemetry stream
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /metrics {
        # Restrict Prometheus metrics scraping to monitoring CIDR
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8080/metrics;
    }
}
```

---

## 6. Verification & Health Probes

Run verification checks to confirm zero downtime readiness:

### 6.1 Liveness Probe
```bash
curl -s http://localhost:8080/livez | jq .
# Expected: {"status": "HEALTHY", "version": "1.0.0-GA", "database": "CONNECTED", ...}
```

### 6.2 Readiness Probe
```bash
curl -s http://localhost:8080/readyz | jq .
# Expected HTTP 200 with status HEALTHY
```

### 6.3 Authentication Negative Test
Confirm that unauthenticated access is strictly blocked:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/overview
# Expected: 401
```

### 6.4 Tenant Registration Verification
Register the sovereign initial owner account:
```bash
curl -s -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "host@zonata.internal",
    "password": "StrongMasterPassword2026!",
    "name": "Sovereign Host",
    "tenant_name": "Sovereign Enterprise"
  }' | jq .
# Expected: HTTP 201 with Bearer token, tenant_id, and user_id
```

---

## 7. Day-2 Operations Runbook

### 7.1 Database Backup (Automated Daily)
Create a daily automated PostgreSQL backup:
```bash
#!/bin/bash
BACKUP_DIR="/opt/zonata/backups/db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
docker compose -f /opt/zonata/docker-compose.prod.yml exec -T postgres pg_dump -U zonata_admin -d zonata_production -Fc > "$BACKUP_DIR/zonata_backup_$TIMESTAMP.dump"
gzip "$BACKUP_DIR/zonata_backup_$TIMESTAMP.dump"
# Retain last 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete
```

### 7.2 Database Restore Drill
To restore a snapshot into a disposable database for disaster recovery drills:
```bash
docker compose -f docker-compose.prod.yml exec -T postgres createdb -U zonata_admin zonata_restore_test
docker compose -f docker-compose.prod.yml exec -T postgres pg_restore -U zonata_admin -d zonata_restore_test < backup.dump
```

### 7.3 Cryptographic Key Rotation
To rotate `ZONATA_AUTH_SECRET`:
1. Generate new 64-char hex secret: `NEW_SECRET=$(openssl rand -hex 32)`
2. In `.env.production`:
   - Set `ZONATA_PREVIOUS_AUTH_SECRET=$ZONATA_AUTH_SECRET`
   - Set `ZONATA_AUTH_SECRET=$NEW_SECRET`
3. Reload API server gracefully: `docker compose -f docker-compose.prod.yml restart zonata-api`
4. All existing tokens will be accepted during the grace rotation period via `get_verification_keys()`.

### 7.4 Log Rotation
Ensure Docker daemon log rotation is configured in `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
```
