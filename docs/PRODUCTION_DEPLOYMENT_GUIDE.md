# PRODUCTION DEPLOYMENT & OPERATIONS GUIDE
**ZONATA Universal AI Company Operating System**  
*Classification: PRODUCTION OPERATIONS*  
*Timestamp: 2026-10-02T11:15:00Z*

---

## 1. System Architecture & Topology

```
                       [Internet / Clients / Webhooks]
                                      │
                                      ▼
                   [Nginx / Cloudflare Ingress Proxy]
                       - SSL/TLS Termination
                       - Rate Limiting & DDoS Shield
                       - Static Asset Caching (/web/*)
                                      │
                                      ▼
              [ZONATA Multi-Threaded API Server (Port 8080)]
                       - ThreadedHTTPServer / ASGI
                       - JWT/HMAC Bearer Token Auth
                       - Security Headers & Request Correlation
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
    [Autonomous Supervisor]                         [Worker Fleet & Sagas]
   (zonata_daemon.py - 10s tick)                   - Temporal Worker Runtime
   - Company Vitals Surveillance                   - Nango Sync Workers
   - Schedule Milestone Dispatch                   - OpenHands Sandboxes
   - Worker Heartbeat Monitoring                   - Browser Use Instances
               │                                             │
               └──────────────────────┬──────────────────────┘
                                      │
                                      ▼
             [Persistence Layer: WAL-Enabled SQLite / PostgreSQL]
                    - roboassistant.db (WAL Mode)
                    - audit_ledger.jsonl (Flock-Protected)
```

---

## 2. Production Environment Configuration

Create `/etc/zonata/zonata.env` or `.env`:

```bash
# Security & Secret Management
ZONATA_ENV=production
ZONATA_STRICT_AUTH=1
ZONATA_AUTH_SECRET=CHANGE_ME_TO_A_64_CHAR_HEX_SECRET_IN_PRODUCTION

# Tenant & Organization
ZONATA_TENANT_ID=tnt_primary
ZONATA_COMPANY_ID=comp_primary

# Supervisor Daemon
ZONATA_TICK_INTERVAL=10.0

# Storage Quotas
ZONATA_STORAGE_DIR=/var/lib/zonata/storage
ZONATA_MIN_FREE_GB=10.0

# Database Configuration (PostgreSQL when scaled)
# DATABASE_URL=postgresql://zonata_user:password@localhost:5432/zonata_db
```

---

## 3. Systemd Service Manifests

### A. API Server Service (`/etc/systemd/system/zonata-api.service`)
```ini
[Unit]
Description=ZONATA Universal AI Company Operating System API Server
After=network.target

[Service]
Type=simple
User=zonata
WorkingDirectory=/opt/zonata
EnvironmentFile=/etc/zonata/zonata.env
ExecStart=/usr/bin/python3 api_server.py 8080
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### B. Supervisor Daemon Service (`/etc/systemd/system/zonata-daemon.service`)
```ini
[Unit]
Description=ZONATA Autonomous 24x7x365 Company Supervisor Daemon
After=zonata-api.service

[Service]
Type=simple
User=zonata
WorkingDirectory=/opt/zonata
EnvironmentFile=/etc/zonata/zonata.env
ExecStart=/usr/bin/python3 zonata_daemon.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 4. Docker Compose Deployment Option

```yaml
version: '3.8'

services:
  zonata-api:
    image: python:3.14-slim
    container_name: zonata-api
    restart: always
    working_dir: /app
    volumes:
      - .:/app
      - zonata-storage:/app/storage
    ports:
      - "8080:8080"
    environment:
      - ZONATA_ENV=production
      - ZONATA_STRICT_AUTH=1
      - ZONATA_AUTH_SECRET=${ZONATA_AUTH_SECRET}
    command: python3 api_server.py 8080

  zonata-daemon:
    image: python:3.14-slim
    container_name: zonata-daemon
    restart: always
    working_dir: /app
    volumes:
      - .:/app
      - zonata-storage:/app/storage
    environment:
      - ZONATA_ENV=production
      - ZONATA_TICK_INTERVAL=10.0
    command: python3 zonata_daemon.py

volumes:
  zonata-storage:
```
