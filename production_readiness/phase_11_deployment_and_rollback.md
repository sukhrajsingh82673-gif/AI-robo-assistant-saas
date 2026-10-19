# Phase 11 Deployment & Rollback Runbook: Governance, Economic Command, and Cryptographic Gateways
**URA / ZONATA Production Readiness Program**

**Runbook Date:** 2026-10-19  
**Branch:** `engineering/production-readiness-gap-closure`  
**Target Environments:** Staging (`https://zonata-staging.onrender.com`), Production Cloud  
**Database:** Neon Serverless PostgreSQL 16 (Pooled)  

---

## 1. Deployment Overview & Prerequisites

Phase 11 introduces database schema expansions, two new governance engines (`core/economic_governance.py` and `core/cryptographic_approvals.py`), and corresponding REST API endpoints in `api_server.py`.

### Required Environment Configuration
Ensure the following variables are configured in Render environment settings or the host `.env`:
- `DATABASE_URL`: Active Neon PostgreSQL connection string (pooled endpoint recommended).
- `ZONATA_APPROVAL_SECRET`: 256-bit cryptographic secret for HMAC-SHA256 approval signatures (falls back to `ZONATA_AUTH_SECRET` or `JWT_SECRET` if omitted).
- `APP_ENV`: `staging` or `production`.
- `ZONATA_PROTECT_METRICS`: `1` (edge metrics protection active).

---

## 2. Step-by-Step Deployment Procedure

### Step 1: Pre-Deployment Health & Asset Check
Confirm staging baseline is healthy and invariant hashes match:
```bash
curl -fsS https://zonata-staging.onrender.com/health
curl -fsS https://zonata-staging.onrender.com/readyz
sha256sum storage/roboassistant.db storage/evidence/audit_ledger.jsonl
git hash-object web/workflow_workspace.js
```

### Step 2: Database Migration Execution (Neon PostgreSQL)
Apply the non-destructive Phase 11 migration `migrations/pg/0002_phase_11_governance_schema.sql`:
```bash
python3 -c "
from core.db import db
with open('migrations/pg/0002_phase_11_governance_schema.sql') as f:
    sql = f.read()
with db.get_connection() as conn:
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
print('Phase 11 PostgreSQL schema migration applied successfully.')
"
```
*Note: The migration uses `ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS`, guaranteeing zero downtime and complete forward/backward compatibility.*

### Step 3: Git Push & Render Auto-Deploy
Push the verified commit to the tracking branch:
```bash
git push origin engineering/production-readiness-gap-closure
```
Render triggers an automatic zero-downtime deployment based on `render.yaml`.

### Step 4: Post-Deployment Smoke Verification
Verify Phase 11 endpoints over public HTTPS:
```bash
# 1. Health & Database Readiness
curl -fsS https://zonata-staging.onrender.com/readyz

# 2. Economic Budgets Endpoint
curl -fsS https://zonata-staging.onrender.com/api/v1/economic/budgets

# 3. Nonces Endpoint
curl -fsS https://zonata-staging.onrender.com/api/v1/approvals/cryptographic/nonces
```

---

## 3. Rollback Runbook & Contingency Procedures

In the unlikely event of an operational anomaly, follow these phased rollback procedures:

### Scenario A: Application Rollback (Zero DB Changes Required)
Because all database changes are strictly additive (`ADD COLUMN IF NOT EXISTS`, new standalone tables), the application code can be rolled back to the previous stable commit (`20d6081`) without rolling back database tables.

1. **Revert Application Deployment in Git / Render:**
   ```bash
   git revert HEAD --no-edit
   git push origin engineering/production-readiness-gap-closure
   ```
   Or trigger a manual rollback to commit `20d6081` in the Render dashboard.

2. **Verify Restored Baseline:**
   ```bash
   curl -fsS https://zonata-staging.onrender.com/health
   python3 deploy/free_tier/phase_10_5_live_qualification.py https://zonata-staging.onrender.com
   ```

### Scenario B: Emergency KillSwitch / Financial Stop (Zero Deployment Required)
If an agent swarm exhibits anomalous spending or rapid task loops without needing code rollback:

1. **Trigger Global Financial Halt:**
   ```python
   from core.economic_governance import economic_governor
   economic_governor.freeze_budget(entity_id="tnt_primary", reason="SRE Emergency Stop")
   ```
2. **Activate Global A2A KillSwitch:**
   ```python
   from core.a2a_interoperability_runtime import A2AKillSwitch
   A2AKillSwitch.activate()
   ```
All autonomous agent executions, delegations, and budget reservations halt immediately fail-closed.

### Scenario C: Database Schema Rollback (Disaster Recovery Only)
If explicitly necessary to drop Phase 11 tables:
```sql
DROP TABLE IF EXISTS action_approval_nonces CASCADE;
DROP TABLE IF EXISTS enterprise_budget_reservations CASCADE;
ALTER TABLE enterprise_budgets DROP COLUMN IF EXISTS reserved_usd;
ALTER TABLE enterprise_budgets DROP COLUMN IF EXISTS allocated_tokens;
ALTER TABLE enterprise_budgets DROP COLUMN IF EXISTS spent_tokens;
ALTER TABLE enterprise_budgets DROP COLUMN IF EXISTS reserved_tokens;
```

---

## 4. Telemetry & Monitoring Observability

Phase 11 metrics exposed for Prometheus / Grafana scraping:
- `zonata_budget_reservations_total{tenant_id, status}`
- `zonata_budget_exhaustion_events_total{tenant_id, scope}`
- `zonata_approval_nonces_issued_total{tenant_id, risk_class}`
- `zonata_approval_nonces_consumed_total{tenant_id}`
- `zonata_approval_replay_attacks_blocked_total{tenant_id}`
- `zonata_stateful_memory_conflicts_total{tenant_id, status}`
- `zonata_a2a_tasks_total{tenant_id, state}`
