# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Production Deployment Guide (V2 Distributed Architecture)

---

### 1. Mandatory Environment Configuration
At cluster startup, ZONATA verifies all mandatory configuration variables:

```bash
# Authoritative Relational Database (PostgreSQL)
export DATABASE_URL="postgresql://zonata_app:SECURE_PASSWORD@pg-cluster.prod.internal:5432/zonata_production?sslmode=require"

# Distributed Coordination & Caching (Redis)
export REDIS_URL="redis://:REDIS_AUTH_TOKEN@redis-cluster.prod.internal:6379/0"

# Authoritative Durable Execution (Temporal Cluster)
export TEMPORAL_HOST="temporal-frontend.prod.internal:7233"
export TEMPORAL_NAMESPACE="zonata-prod"

# Object Storage (S3 / MinIO Compliant)
export OBJECT_STORAGE_ENDPOINT="https://s3.us-east-1.amazonaws.com"
export OBJECT_STORAGE_BUCKET="zonata-enterprise-artifacts"

# Cryptographic Authentication Secrets
export ZONATA_AUTH_SECRET="ENTERPRISE_HMAC_SHA256_SECRET_KEY_MIN_64_CHARS"

# Environment Identifier
export ZONATA_ENVIRONMENT="production"
```

---

### 2. Multi-Node Deployment Topology

```
                  KUBERNETES / CLOUD CLUSTER
                               |
       +-----------------------+-----------------------+
       |                                               |
[API REPLICAS (x3+)]                           [WORKER POOLS (x5+)]
- Uvicorn/ASGI Stateless Pods                  - Agent Workforce Workers
- Horizontal Pod Autoscaler (HPA)              - Temporal Activity Workers
- Ingress Rate Limiting                        - Integration Gateways
       |                                               |
       +-----------------------+-----------------------+
                               |
                    [HA SUPERVISOR PODS (x2)]
                    - Active-Passive Leader Election
                    - 15s Heartbeat Lease Renewal
                    - Orphan Job Recovery
```

---

### 3. Startup & Health Verification Commands
```bash
# 1. Execute database migrations
python3 -c "from migrations.migration_manager import MigrationManager; MigrationManager().apply_pending_migrations()"

# 2. Check cluster readiness probe
curl -f http://localhost:8080/readyz

# 3. Check overall health
curl -f http://localhost:8080/health
```
