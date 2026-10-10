# ZONATA / URA — Local & Production Installation Guide

## 1. Local Development Installation

### Prerequisites
- Linux OS (POSIX compatible, Termux, Ubuntu 22.04+, Debian 12+)
- Python 3.10+ (Tested through 3.14.0)
- SQLite 3 (WAL mode enabled)
- Git 2.30+

### Setup Steps
```bash
# 1. Clone repository
git clone https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git
cd AI-robo-assistant-saas

# 2. Virtual Environment (Optional)
python3 -m venv .venv
source .venv/bin/activate

# 3. Initialize SQLite Database & Tables
python3 -c "from core.db import db; print('DB Initialized in WAL mode')"

# 4. Start Local Background API Daemon
python3 api_server.py 8080 &

# 5. Verify Health Probe
curl -s http://127.0.0.1:8080/api/automation/fabric/status
```

---

## 2. Docker Compose Production Topology

Production compose orchestration is defined in [`docker-compose.prod.yml`](file:///root/roboassistant/docker-compose.prod.yml):

```bash
# Launch Production Stack
docker compose -f docker-compose.prod.yml up -d
```

### Services Included
1. **`zonata-api`**: Multi-threaded REST and WebSocket server running `api_server.py 8080`.
2. **`zonata-worker`**: Dedicated background task execution worker running `UniversalAutomationFabric.start_background_worker(0.5)`.
3. **`zonata-supervisor`**: Process supervisor ensuring automatic restart, crash-window recovery, and lease reconciliation.
4. **`shared-storage`**: Mounted volume `/app/storage` shared between API and worker processes.

---

## 3. Kubernetes Multi-Node Enterprise Topology

Kubernetes manifests are located in [`k8s/`](file:///root/roboassistant/k8s/):

1. `k8s/01-configmap.yaml`: Environment configuration and strict authentication flags.
2. `k8s/02-secrets.yaml`: Sealed secrets for signing keys and Vault access tokens.
3. `k8s/03-pv-pvc.yaml`: Persistent volume claims for durable SQLite or shared storage.
4. `k8s/04-deployment.yaml`: Replicated API server deployment.
5. `k8s/05-worker-deployment.yaml`: Replicated background worker deployment.
6. `k8s/07-ingress.yaml`: TLS ingress controller with cert-manager annotations.
7. `k8s/10-networkpolicy.yaml`: Zero-trust network segmentation.
8. `k8s/16-edge-waf-gateway.yaml`: Ingress WAF gateway running OWASP CRS rules.

---

## 4. Environment Variables Configuration

Copy `production.env.example` to `.env`:

```ini
# Environment
ENVIRONMENT=production
APP_ENV=production
ZONATA_STRICT_AUTH=1
ZONATA_STRICT_CONFIG=true

# Cryptography & Leases
URA_LEASE_SECRET=generate_strong_64_char_hex_secret_here

# Network & Ports
API_PORT=8080
HOST=0.0.0.0

# Database
DATABASE_URL=sqlite:////app/storage/roboassistant.db
SQLITE_WAL=true
SQLITE_BUSY_TIMEOUT=60000

# Vault / SecretManager
VAULT_ADDR=http://vault.internal:8200
VAULT_TOKEN=s.production_vault_token_here
```
