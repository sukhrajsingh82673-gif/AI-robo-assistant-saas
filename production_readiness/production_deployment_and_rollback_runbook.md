# Production Deployment & Rollback Runbook

**Document Owner:** DevOps & Platform Engineering  
**Target Platform:** Render Cloud + Neon Serverless PostgreSQL 16  
**Applicable Versions:** 1.0.0-GA (Phase 11 & Phase 12)  
**Last Updated:** October 19, 2026  

---

## 1. Pre-Deployment Prerequisites & Checklist

Before initiating production promotion, the release coordinator must verify:
- [ ] Working tree clean on release commit.
- [ ] All 141 automated qualification tests passing (`PYTHONPATH=. pytest ...`).
- [ ] Constitutional asset hashes verified against canonical digests:
  * `storage/roboassistant.db`: `ba738b6bd96fde655c6c8a1398a4373f45dddb97b62fd72053f2d8a82f53d2d4`
  * `storage/evidence/audit_ledger.jsonl`: `ca8181ec9314f281acad3512a34d32323fc195e6eed9f6412d7262e1e6dd0996`
  * `web/workflow_workspace.js`: Git blob `198d57ec6bda875cd2a6825fe2ef8929b7ba30bd`
- [ ] Target Neon PostgreSQL database accessible and healthy (`/readyz` probe).
- [ ] Production environment variables configured in Render dashboard:
  * `DATABASE_URL`: Production pooled connection string.
  * `ZONATA_AUTH_SECRET`: Minimum 64-char high-entropy secret.
  * `STRIPE_API_KEY` & `STRIPE_WEBHOOK_SECRET`: Live production gateway credentials.
  * `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`: Live credentials.

---

## 2. Production Deployment Execution Steps

### Step 1: Database Schema Migration
Apply schema migrations in strict chronological order:
```bash
# 1. Base schema (172 tables)
psql "$DATABASE_URL" -f migrations/pg/0001_postgresql_full_schema.sql

# 2. Phase 11 Governance schema (budgets, reservations, approval nonces)
psql "$DATABASE_URL" -f migrations/pg/0002_phase_11_governance_schema.sql

# 3. Phase 12 Commercial SaaS schema (subscriptions, webhooks, invoices)
psql "$DATABASE_URL" -f migrations/pg/0003_phase_12_billing_schema.sql
```
*Note: All migrations are idempotent (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`).*

### Step 2: Render Service Deployment
1. Push release commit to deployment branch `main` or trigger manual deploy in Render Dashboard.
2. Monitor Render build and startup logs:
   ```
   ==> Running build command 'pip install -r requirements.txt'...
   ==> Deploying...
   ==> Server listening on 0.0.0.0:10000...
   ```

### Step 3: Post-Deployment Smoke Probing
Execute smoke probes against public HTTPS URL:
```bash
# 1. Liveness & Database Readiness
curl -f -s https://zonata.onrender.com/readyz | grep '"status": "HEALTHY"'

# 2. Basic Health
curl -f -s https://zonata.onrender.com/healthz | grep '"status": "HEALTHY"'

# 3. Anti-CSRF Endpoint
curl -f -s https://zonata.onrender.com/api/auth/csrf | grep 'csrf_token'

# 4. Billing Entitlements Endpoint
curl -f -s -H "Authorization: Bearer $TEST_TOKEN" https://zonata.onrender.com/api/v1/billing/entitlements
```

If all 4 probes return HTTP 200 with valid payloads, declare deployment **SUCCESSFUL**.

---

## 3. Rollback Runbook (Emergency Procedure)

If `/readyz` fails to return HTTP 200 within 3 minutes of deployment, or if error rates exceed 0.5%:

### Rollback Step 1: Immediate Container Rollback
1. In Render Dashboard, click **Deployments** -> locate previous stable release commit -> click **Rollback to this deploy**.
2. Render initiates instant rollback to the previous container image without rebuilding (~45 seconds).

### Rollback Step 2: Database Schema Safety
- Migrations `0002` and `0003` are strictly additive (new tables and nullable columns with defaults).
- Previous application versions do not reference the new tables or columns and will continue operating normally against the migrated schema.
- **Do NOT execute `DROP TABLE` or `DROP COLUMN`** unless instructed by the lead database architect.

### Rollback Step 3: Neon Point-in-Time Restore (Catastrophic Scenario Only)
If catastrophic data corruption occurred during deployment:
1. Open Neon Console -> Project -> Branches.
2. Create recovery branch from snapshot at timestamp immediately preceding deployment:
   ```bash
   neon branch create --name recovery-pre-deploy --parent main --timestamp 2026-10-19T02:00:00Z
   ```
3. Update `DATABASE_URL` in Render to point to the recovery branch and redeploy.

### Rollback Step 4: Incident Notification & Audit
1. Notify stakeholders in `#engineering-incidents`.
2. Inspect Render application logs and Neon query logs.
3. Record rollback event in `storage/evidence/audit_ledger.jsonl`.
