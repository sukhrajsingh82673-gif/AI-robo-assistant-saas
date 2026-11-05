# URA / ZONATA — PRODUCTION DEPLOYMENT & ROLLBACK RUNBOOK

**Target System:** URA / ZONATA Universal AI Company Operating System  
**Service Host:** Render Staging / Production Web Service  
**Database:** Neon Serverless PostgreSQL 16 (Connection Pooler)  
**Document Classification:** Confidential / Production Operations Runbook  
**Last Updated:** October 25, 2026  

---

## 1. Architecture & Deployment Prerequisites

### 1.1 Infrastructure Topology
* **Web Compute:** Render Native Python Web Service (Linux container, Python 3.14+).
* **Database:** Neon Serverless PostgreSQL 16 (Pooled endpoint: `ep-broad-sky-b4jnm313-pooler.c-6.us-east-2.aws.neon.tech/Postgres`).
* **Audit Storage:** Local filesystem storage mounted at `/roboassistant/storage/evidence/` backed by transactional PostgreSQL mirror `merkle_evidence_events`.

### 1.2 Mandatory Environment Variables
| Variable | Value (Restricted Pilot) | Value (Public GA Production) | Purpose |
|:---|:---|:---|:---|
| `APP_ENV` | `staging` | `production` | Operational environment mode |
| `APP_RELEASE_VERSION` | `1.0.0-RESTRICTED-PILOT` | `1.0.0-GA` | Release version identifier |
| `ZONATA_RESTRICTED_PILOT_MODE` | `1` | `0` | Controls pilot limit enforcement |
| `ZONATA_PUBLIC_GA_MODE` | `0` | `1` | Enables unrestricted Public GA mode |
| `MAX_DESIGN_PARTNER_ORGS` | `3` | `100` | Maximum tenant registration ceiling |
| `PILOT_MAX_CONCURRENCY` | `4` | `10` | Maximum concurrency leases per tenant |
| `PILOT_MAX_RPM` | `60` | `120` | Requests per minute per tenant rate limit |
| `DATABASE_URL` | Neon PG Pooled URL | Neon PG Pooled URL | Authoritative database connection string |

---

## 2. Pre-Flight Deployment Checklist

Before triggering a production deployment:

1. **Working Tree Cleanliness:**
   ```bash
   cd /root/roboassistant
   git status
   # Must return: nothing to commit, working tree clean
   ```
2. **Branch Synchronization:**
   ```bash
   git checkout engineering/production-readiness-gap-closure
   git pull origin engineering/production-readiness-gap-closure
   git checkout main
   git merge engineering/production-readiness-gap-closure
   ```
3. **Verify Protected Fixture Checksums:**
   ```bash
   sha256sum storage/roboassistant.db storage/evidence/audit_ledger.jsonl web/workflow_workspace.js
   # Expected:
   # ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4  storage/roboassistant.db
   # ca8181ec9314f281acad3512a34d32323fc195e6eed9f6412d7262e1e6dd0996  storage/evidence/audit_ledger.jsonl
   # 88888caf6abc92e7f6f3c2e3559e334b66087b16f29ed58f9b1c0c0449cbbe9b  web/workflow_workspace.js
   ```
4. **Execute Full Test Qualification:**
   ```bash
   python3 -m pytest tests/test_production_infrastructure_qualification.py tests/test_public_ga_integrity_and_finance.py tests/test_restricted_pilot_operating_envelope.py -v
   # All tests must pass with exit code 0
   ```

---

## 3. Standard Deployment Procedure

Render deployments are triggered via Git push to the monitored deployment branch:

1. **Push Changes to GitHub:**
   ```bash
   git push origin main
   git push origin engineering/production-readiness-gap-closure
   ```
2. **Monitor Build Progress on Render:**
   * Watch build logs via Render Dashboard or API.
   * Standard build time: ~45–60 seconds.
3. **Post-Deployment Liveness & Readiness Probe:**
   Execute probe with 60-second timeout to accommodate cold starts:
   ```bash
   curl -s --connect-timeout 30 --max-time 60 https://zonata-staging.onrender.com/readyz | jq .
   ```
   **Acceptance Criteria:**
   * `"status": "HEALTHY"`
   * `"database": "CONNECTED"`
   * `"database_dialect": "postgresql"`
   * `"merkle_ledger": "INTEGRITY_VERIFIED"` or `"ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED"`
   * `"commit"` matches the deployed commit SHA.

---

## 4. Controlled Rollback Procedure

In the event of an unrecoverable runtime regression, memory leak, or broken release gate:

### Step 1: Immediate Traffic Drain / Emergency Freeze
If runaway processes or data corruption is suspected, activate the Emergency Quarantine switch via API or CLI:
```bash
curl -X POST https://zonata-staging.onrender.com/api/settings/effective \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"setting_id": "emergency_quarantine", "value": true}'
```

### Step 2: Identify Stable Rollback Target Commit
Identify the last known good commit (e.g. `ca953b23f665a649e866fa5649bef691000e4d50`):
```bash
git log --oneline -5
ROLLBACK_TARGET="ca953b2"
```

### Step 3: Revert Codebase or Reset Deployment Branch
```bash
# Option A: Fast-forward revert commit (Preserves git history)
git revert HEAD --no-edit
git push origin main
git push origin engineering/production-readiness-gap-closure

# Option B: Emergency hard pointer reset (Authorized only in emergency)
git reset --hard $ROLLBACK_TARGET
git push origin main --force
git push origin engineering/production-readiness-gap-closure --force
```

### Step 4: Verify Database Compatibility
If schema migrations were executed:
```bash
python3 -c "
import sys
sys.path.insert(0, '/root/roboassistant')
from core.db import db
with db.get_connection() as conn:
    print('Checking database tables and schema validity...')
    conn.execute('SELECT COUNT(*) FROM tenants')
    print('Database connection valid and responsive.')
"
```

### Step 5: Post-Rollback Verification Probe
```bash
curl -s --connect-timeout 30 --max-time 60 https://zonata-staging.onrender.com/readyz | jq .
```
Verify that `"commit"` matches `$ROLLBACK_TARGET` and `"status": "HEALTHY"`.
