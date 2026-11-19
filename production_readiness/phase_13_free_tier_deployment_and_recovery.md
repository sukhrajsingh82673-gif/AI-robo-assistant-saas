# Phase 13 Free-Tier Deployment & Disaster Recovery Runbook

**Evaluation Date:** October 19, 2026  
**Target Environment:** Free-Tier Cloud Staging (Render Web Service + Neon Serverless PostgreSQL 16)  
**Public Staging URL:** `https://zonata-staging.onrender.com`  
**Database Cluster:** Neon Serverless PostgreSQL 16 (`ep-broad-sky-b4jnm313-pooler`)  
**Cost Invariant:** **$0.00 / month (Zero Paid Cloud Infrastructure Required)**  

---

## 1. Free-Tier Cloud Architecture & Cost Protection Invariants

In strict compliance with executive directives, the system is architected to operate fully within free-tier quotas during development, testing, and simulated enterprise operations:

| Component | Free-Tier Provider | Configuration / Limit | Cost Protection Invariant |
|:---|:---|:---|:---|
| **Application Web Service** | **Render.com** (Free Web Service) | 0.1 vCPU, 512 MB RAM, spin-down after 15 min inactivity | Zero credit card spend; autoscaling disabled; single instance |
| **Relational Database** | **Neon PostgreSQL 16** (Serverless Free) | 0.5 CU max, scale-to-zero after 5 min idle, 3 GB storage | Connection pooling enabled via `-pooler` endpoint; max pool size clamped to 5 |
| **Object Storage** | **Neon / Local SQLite Baseline** | Zero external S3 buckets; local simulation disk storage | Zero cloud egress transfer fees |
| **Key Management** | **Sovereign HMAC / File Keychain** | Zero AWS KMS / GCP KMS / HashiCorp Vault | Local cryptographic key derivation via `secrets_manager` |
| **Payment Gateways** | **Stripe & Razorpay (Sandbox / Mock)** | Cryptographic HMAC-SHA256 signature verification | No live cards charged; zero merchant fees |
| **AI LLM Routing** | **Mock / Local Gemma 4 Engine** | Local provider adapters with fallback | Zero API usage charges from frontier model providers |

---

## 2. Deployment Runbook (Push-to-Deploy Cycle)

Whenever updates are pushed to the deployment branch, the following automated sequence executes:

```
[ Antigravity Commit ] ──> [ git push origin engineering/production-readiness-gap-closure ]
                                    │
                                    ▼
                         [ Render Auto-Deploy ]
                                    │
                         ├── Build: pip install -r requirements.txt
                         ├── Start: python3 -m gunicorn ... or uvicorn
                         └── Healthcheck: GET /readyz (PostgreSQL check)
                                    │
                                    ▼
                         [ Staging Verified ]
```

### Step-by-Step Procedure:
1. **Commit and Push**:
   ```bash
   git add core/db.py core/economic_governance.py core/overview_service.py core/simulation_fixtures.py tests/
   git commit -m "fix(overview): resolve homepage 502 via PostgresCursorWrapper parameter translation and qualify 9-department simulation"
   git push origin engineering/production-readiness-gap-closure
   ```
2. **Monitor Render Staging Build**:
   - Access `https://dashboard.render.com` or probe `https://zonata-staging.onrender.com/readyz`.
   - Allow cold start (30-60s) if the service was spun down.
3. **Verify Health Endpoints**:
   ```bash
   curl -s -i https://zonata-staging.onrender.com/readyz
   # Expected: HTTP 200 OK {"status": "READY", "database": "CONNECTED", "dialect": "postgresql"}
   ```
4. **Verify Homepage Overview Snapshot**:
   ```bash
   # Register/login to obtain bearer token
   TOKEN=$(curl -s -X POST https://zonata-staging.onrender.com/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"qa_test@novadynamics.sim","password":"SecurePassword123!","name":"QA Tester"}' \
     | jq -r .token)

   # Fetch overview snapshot
   curl -s -i https://zonata-staging.onrender.com/api/overview/snapshot \
     -H "Authorization: Bearer $TOKEN"
   # Expected: HTTP 200 OK with full JSON payload containing "company", "financial", "sales", etc.
   ```

---

## 3. Cold Start & Fault Recovery Architecture

Because free-tier instances spin down during periods of inactivity, the application is hardened to handle cold starts and brief database reconnect latencies:

1. **Neon PostgreSQL Scale-to-Zero Wakeup**:
   - When the Neon compute endpoint is suspended, the first connection request takes 1.5 - 3.0 seconds to resume compute.
   - `PostgresConnectionPool` (`core/db.py`) uses a retry loop with exponential backoff (up to 10s timeout) to absorb cold start latency without throwing 500 errors to users.
2. **Deferred Connection Proxy**:
   - If module imports execute before database sockets establish, `DeferredConnectionProxy` captures and defers DDL/queries without throwing unhandled exceptions.
3. **Render Spin-Down Resilience**:
   - The frontend workspace shows clean loading state indicators while awaiting cold start HTTP responses, preventing UI crashes.
4. **Disaster Recovery / Branch Restoration**:
   - If data corruption occurs on the staging database, a fresh branch can be created in Neon within 2 seconds using Neon's copy-on-write branching technology, with zero downtime.

---

## 4. Operational Maintenance & Budget Verification

To ensure free-tier cost invariants are never violated:
- **Egress Transfer Audit**: Zero external file uploads or large downloads are enabled.
- **Connection Accounting**: Connection pool max size is hard-capped at 10 (well within Neon's 100-connection free limit).
- **Idle Eviction**: Connections are automatically recycled after 120 seconds of idleness.
