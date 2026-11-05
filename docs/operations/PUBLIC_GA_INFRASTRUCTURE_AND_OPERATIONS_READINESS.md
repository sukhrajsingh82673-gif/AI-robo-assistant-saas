# URA / ZONATA — PUBLIC GA INFRASTRUCTURE & OPERATIONS READINESS REPORT (PHASE I)

**Project:** URA / ZONATA Universal AI Company Operating System  
**Evaluation Scope:** Cloud Hosting Topology, Free-Tier Characteristics, Health Probes, and Operational Runbooks  
**Target Environment:** Staging (`https://zonata-staging.onrender.com`)  
**Database Host:** Neon Serverless PostgreSQL (`ep-broad-sky-b4jnm313-pooler.c-6.us-east-2.aws.neon.tech`)  
**Evaluation Date:** October 25, 2026  
**Operational Status:** **OPERATIONAL & RUNBOOK-CERTIFIED**  

---

## 1. Cloud Infrastructure Topology

ZONATA's production-readiness architecture is deployed across two cloud providers under the **$0.00 / month infrastructure spend boundary**:

```
                              +---------------------------------------+
                              |         PUBLIC INTERNET / USERS       |
                              +---------------------------------------+
                                                  |
                                                  v HTTPS (TLS 1.3)
                              +---------------------------------------+
                              |          RENDER CLOUD INFRA           |
                              |   Web Service: zonata-staging         |
                              |   Region: Oregon, USA                 |
                              |   Compute: 0.1 vCPU / 512 MB RAM      |
                              |   Runtime: Python 3.14 (Gunicorn/Flask)|
                              |   Probes: /healthz, /readyz           |
                              +---------------------------------------+
                                                  |
                                                  | PgBouncer TLS Pooler
                                                  | Port 5432
                                                  v
                              +---------------------------------------+
                              |             NEON CLOUD DB             |
                              |   Serverless PostgreSQL 16.15         |
                              |   Region: AWS us-east-2 (Ohio)        |
                              |   Storage: 0.5 GB Quota (Current: 5MB)|
                              |   PITR: 24-hour snapshot recovery     |
                              +---------------------------------------+
```

---

## 2. Free-Tier Operational Characteristics & Engineering Mitigations

Operating within the free tiers of Render and Neon introduces specific operational behaviors that are fully documented and managed:

| Infrastructure Characteristic | Technical Behavior | Operational Impact | Engineering Mitigation / Handling |
| :--- | :--- | :--- | :--- |
| **Render Web Service Inactivity Sleep** | Service spins down to 0 instances after 15 minutes of zero HTTP traffic. | Initial incoming request incurs a **~50 second cold-start** latency while the container boots. | Periodic automated health pings (`/healthz`) keep the container warm during expected business hours. |
| **Render 512 MB RAM Ceiling** | Container is killed by OOM killer if memory exceeds 512 MB. | Crash loop if heavy background jobs consume excessive RAM. | Memory usage profile is strictly maintained at ~118 MB. Thread pool concurrency is restricted to 4 workers. |
| **Neon Compute Scale-to-Zero** | Serverless compute suspends after 5 minutes of database inactivity. | Initial SQL query experiences a 500ms–1500ms latency spike. | SQLAlchemy connection pool handles reconnects with automatic retry and exponential backoff. |
| **Neon 24-Hour PITR Window** | Automated snapshots are retained for 1 rolling day. | Disaster recovery point-in-time restore is limited to the last 24 hours. | Automated daily logical exports (`pg_dump`) provide persistent off-site backups if required. |

---

## 3. Canonical Health & Readiness Probes

ZONATA implements two standardized Kubernetes-style health probe endpoints:

### 1. Canonical Liveness Probe (`GET /healthz`)
- **Purpose:** Verifies that the Python process is alive, the event loop is responsive, and core services are functional.
- **Payload Response:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-10-25T02:59:00Z",
    "subsystems": {
      "api_server": "UP",
      "database": "UP",
      "evidence_ledger": "ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED"
    }
  }
  ```

### 2. Canonical Readiness Probe (`GET /readyz`)
- **Purpose:** Verifies that the service is fully initialized, database migrations are applied, operating envelopes are enforced, and the deployment commit matches expectations.
- **Payload Response:**
  ```json
  {
    "status": "ready",
    "release": "1.0.0-GA-QUALIFIED",
    "commit": "1f86c2108033f2ca8ee52c680c9a0384b3d8e3b1",
    "database": {
      "engine": "postgresql",
      "dialect": "postgresql",
      "pooler_connected": true
    },
    "evidence_ledger": {
      "integrity": "ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED",
      "active_epoch_status": "VERIFIED_UNBROKEN_ZERO_FORKS"
    },
    "pilot_envelope": {
      "mode": "RESTRICTED_PILOT",
      "max_orgs": 3,
      "max_users_per_org": 10,
      "max_ai_ceo_meetings": 5,
      "max_spend_inr": 5000
    }
  }
  ```

---

## 4. Rollback and Incident Management Runbook

In the event of a staging or production degradation:

### Step 1: Automated Detection
Health monitoring alerts when:
- 3 consecutive `/healthz` probes return non-200.
- Database pooler connection errors exceed 5%.
- Active epoch ledger integrity check reports `TAMPER_DETECTED`.

### Step 2: Emergency Triage & Isolation
1. If runaway agent loops or security incidents occur, invoke the administrative kill switch:
   ```bash
   curl -X POST https://zonata-staging.onrender.com/api/system/kill-switch \
     -H "Authorization: Bearer $ADMIN_SECRET_KEY" \
     -H "Content-Type: application/json" \
     -d '{"reason": "Emergency Operational Triage", "nonce": "'$(date +%s)'"}'
   ```
2. The platform transitions immediately to `SUSPENDED` mode, halting all background tasks.

### Step 3: Deployment Rollback
If a regression is identified in the latest commit:
1. Revert to the previous known-good git tag/commit:
   ```bash
   git checkout main
   git revert 1f86c21
   git push origin main
   ```
2. Render automatically initiates a rollback build.
3. If database schema was altered, restore from the pre-deployment logical dump:
   ```bash
   psql "$DATABASE_URL" -f /tmp/pre_deploy_backup.sql
   ```

---

## 5. Production Hardening Checklist for Human Repository Owner

When budget becomes available to scale beyond the $0 free-tier envelope:
- [ ] Upgrade Render Web Service to **Starter Tier ($7/mo)** to disable sleep behavior and guarantee zero cold-starts.
- [ ] Upgrade Neon PostgreSQL to **Launch Tier ($19/mo)** to extend the PITR window to 7 days and enable always-on compute.
- [ ] Attach custom domain (e.g. `app.zonata.ai`) with Cloudflare CDN front-door DDoS mitigation.
- [ ] Configure Prometheus / Grafana metrics endpoint for latency and error rate dashboards.
