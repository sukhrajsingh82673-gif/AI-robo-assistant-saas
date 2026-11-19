# URA / ZONATA — PRODUCTION OPERATIONS & INCIDENT RESPONSE RUNBOOK

**Target System:** URA / ZONATA Universal AI Company Operating System  
**Audience:** Site Reliability Engineers (SRE), Operations Leads, Platform Administrators  
**Classification:** Confidential / Standard Operating Procedures  
**Last Updated:** October 25, 2026  

---

## 1. System Health & Operational Endpoints

| Endpoint | HTTP Method | Auth Required | Expected Response | Operational Purpose |
|:---|:---:|:---:|:---|:---|
| `/healthz` | GET | No | HTTP 200 `{"status": "HEALTHY"}` | Basic container liveness probe |
| `/readyz` | GET | No | HTTP 200 `{"database": "CONNECTED", ...}` | Full readiness & DB connectivity probe |
| `/api/pilot/envelope` | GET | No | HTTP 200 Operating envelope metadata | Quota and capacity inspection |
| `/api/operating-envelope` | GET | No | HTTP 200 Operating envelope metadata | General GA envelope inspection |
| `/api/evidence` | GET | Bearer Token | HTTP 200 Merkle root & chain status | Epistemic audit ledger verification |
| `/api/finance/summary` | GET | Bearer Token | HTTP 200 MTD financials & pending claims | Financial health & GL balances |
| `/api/finance/expenses/approve` | POST | Bearer Token | HTTP 200 `{"success": true, "status": "APPROVED"}` | Approve expense & post to GL |

---

## 2. Standard Operating Procedures (SOPs)

### SOP-01: Daily Health & Readiness Inspection
Run automated curl check:
```bash
curl -s --connect-timeout 30 --max-time 60 https://zonata-staging.onrender.com/readyz | jq .
```
Verify:
1. `"status": "HEALTHY"`
2. `"database": "CONNECTED"`
3. `"merkle_ledger": "INTEGRITY_VERIFIED"` or `"ACTIVE_EPOCH_VERIFIED_HISTORICAL_FORKS_RECORDED"`
4. `"database_dialect": "postgresql"`

### SOP-02: Tenant Expense Approval & Financial Posting
When an employee or agent submits an operational expense claim:
1. Inspect pending claims via `/api/finance/summary`.
2. Approve claim and post to General Ledger:
   ```bash
   curl -X POST https://zonata-staging.onrender.com/api/finance/expenses/approve \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"expense_id": "exp_...", "approver": "Executive Lead"}'
   ```
3. Verify that `expenses_mtd` increments by the approved amount and `expenses_pending_approval` decrements to 0.

### SOP-03: Tenant Concurrency Lease Reclamation
If a tenant's processes crash unexpectedly without releasing their concurrency lease:
1. Query active leases:
   ```bash
   curl -s -H "Authorization: Bearer $TOKEN" https://zonata-staging.onrender.com/api/concurrency/leases
   ```
2. Trigger stale lease garbage collection:
   ```bash
   curl -X POST -H "Authorization: Bearer $TOKEN" https://zonata-staging.onrender.com/api/concurrency/leases/reclaim
   ```

---

## 3. Incident Response Playbook

### Incident Severity Classification
* **SEV-1 (Critical Outage):** Service returns 5xx on `/readyz`, database unreachable, or Merkle integrity failure reported.
* **SEV-2 (Degraded Operations):** High response latency (> 5s), concurrency lease exhaustion (HTTP 429), or integration timeout.
* **SEV-3 (Minor / Informational):** Single tenant quota exceeded, unapproved expense claim backlog.

### Playbook 1: Database Unavailability (SEV-1)
1. Check Neon PostgreSQL console status.
2. If Neon database is suspended or scaling, send warm-up query.
3. If database credentials rotated, update `DATABASE_URL` in Render environment settings and trigger redeployment.

### Playbook 2: Emergency Freeze / Agent Runaway (SEV-1)
To instantly freeze all autonomous agent execution across the entire platform:
```bash
curl -X POST https://zonata-staging.onrender.com/api/settings/effective \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"setting_id": "emergency_quarantine", "value": true}'
```

### Playbook 3: Cold-Start Latency Mitigation (SEV-2)
On Render free-tier, compute spins down after 15 minutes of zero traffic.
* **Symptom:** First request times out after 15–20 seconds.
* **Resolution:** Ensure external uptime pings hit `/healthz` every 10 minutes to maintain active compute state.
