# ZONATA Agent Factory — Enterprise Operations Runbook

**Document Version:** 1.0.0  
**Target Environment:** Linux ARM64 (Android / Termux, Sovereign T0 Mode)  
**Primary Engine:** ZONATA Sovereign Core & Agent Factory Engine  
**Authoritative Ledger:** EvidenceLedger (HMAC-SHA256 Merkle chain)

---

## 1. System Overview & Host Architecture

The ZONATA Agent Factory automates the specification, compilation, sandboxing, testing, certification, release, and lifecycle monitoring of sovereign enterprise agents and hierarchical teams.

### Operational Modes
* **Host Mode:** Operates strictly in **T0 Mode** on Linux ARM64 (Termux). All builds execute through pure-Python AST parsing, declarative compilation, and in-process governed execution.
* **Storage Engines:** SQLite 3 (`storage/roboassistant.db`) and PostgreSQL 16+ via declarative idempotent migrations (`0013_agent_factory_core.sql`).
* **Audit Trail:** Every state change, compile event, gate evaluation, and approval decision is cryptographically logged before state mutation via `agent_factory.domain.transition.transition()`.

---

## 2. Standard Operating Procedures (SOP)

### 2.1 Starting and Managing the Worker Daemon
The Factory Worker daemon polls `DbQueueOrchestrator` for queued builds, renews lease heartbeats, and reaps lost builds:

```bash
# Start daemon in background with logging
python -m agent_factory.worker >> storage/logs/factory_worker.log 2>&1 &
WORKER_PID=$!
echo "Factory worker started with PID $WORKER_PID"
```

To stop gracefully:
```bash
kill -SIGTERM $WORKER_PID
```
The daemon will complete any active heartbeat, finish current compilation stage, and exit cleanly without leaving orphaned builds.

### 2.2 Template Catalog Updates
When introducing or updating agent templates:
1. Place template manifest in `agent_factory/templates/starter/<template_name>.yaml`.
2. Ensure `apiVersion: zonata.template/v1` and `kind: AgentTemplate`.
3. Verify parameter schema constraints:
   ```bash
   PYTHONPATH=. pytest tests/agent_factory/test_template_loader.py tests/agent_factory/test_at02_template_instantiation.py
   ```
4. Changes take effect immediately via in-memory caching and filesystem reload.

### 2.3 Running QA Gate Certification
Before any agent version can be published, it must pass deterministic Gate G00–G13 evaluation:
```bash
# Evaluate gates and seal signed certification bundle
curl -X POST "http://localhost:8000/api/v8/agent-factory/agent-versions/{version_id}/certify" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {evaluator_principal_id}" \
  -H "X-Company-ID: {company_id}" \
  -H "Content-Type: application/json"
```

---

## 3. Emergency Incident Response & Runbooks

### 3.1 Emergency Kill Switch (Global or Scoped)
If an agent or team exhibits unexpected behavior or security violations:

```bash
# Scoped agent termination
curl -X POST "http://localhost:8000/api/v8/agent-factory/kill" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {admin_id}" \
  -H "X-Company-ID: {company_id}" \
  -H "Content-Type: application/json" \
  -d '{"scope": "AGENT", "target_id": "agt_xyz", "reason": "Security incident containment"}'

# Global system halt
curl -X POST "http://localhost:8000/api/v8/agent-factory/kill" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {admin_id}" \
  -H "X-Company-ID: {company_id}" \
  -H "Content-Type: application/json" \
  -d '{"scope": "GLOBAL", "target_id": "SYSTEM", "reason": "Critical infrastructure incident"}'
```

### 3.2 Immediate Agent Suspension ($\le 5$s Halt, AT-18)
To immediately revoke credentials and halt execution of an active agent without deleting its record:

```bash
curl -X POST "http://localhost:8000/api/v8/agent-factory/agents/{agent_id}/suspend" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {admin_id}" \
  -H "X-Company-ID: {company_id}" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Performance anomaly under investigation"}'
```

**Effects:**
1. Invalidates session tokens via `AuthorityPort.revoke_principal_tokens()`.
2. Halts runtime instances via `RuntimePort.suspend_instance()`.
3. Switches lifecycle status to `SUSPENDED` and monitoring status to `INCIDENT`.
4. Executes within $\le 5.0$ seconds.

To resume once verified:
```bash
curl -X POST "http://localhost:8000/api/v8/agent-factory/agents/{agent_id}/resume" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {admin_id}" \
  -H "X-Company-ID: {company_id}"
```

### 3.3 Atomic Version Rollback (AT-17)
To roll back a faulty active version to a previously certified version:

```bash
curl -X POST "http://localhost:8000/api/v8/agent-factory/agents/{agent_id}/rollback" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {admin_id}" \
  -H "X-Company-ID: {company_id}" \
  -H "Content-Type: application/json" \
  -d '{"to_version": "agv_stable_v1_0_0", "reason": "Incident in v2.0.0"}'
```

**Guardrails:**
* Target version must have status `CERTIFIED`, `PUBLISHED`, or `SUPERSEDED`.
* Uncertified, draft, or failed versions are rejected with HTTP 400 `AF-ROLLBACK-ERROR`.
* Atomically switches `af_agent.active_version_id`.

### 3.4 Worker Crash Recovery (AT-19)
If a worker crashes mid-build:
1. The heartbeat expires after 60 seconds.
2. The orchestrator's `reap_lost_builds(timeout_seconds=60.0)` automatically marks stale jobs as `LOST`.
3. An active worker claims the next queued attempt.
4. Stage checkpoints ensure recovery from the last durable compilation checkpoint without double-minting agent identities.

---

## 4. Database Maintenance & Backup

### 4.1 SQLite Snapshot Backup
```bash
sqlite3 storage/roboassistant.db ".backup storage/backups/roboassistant_$(date +%Y%m%d_%H%M%S).db"
```

### 4.2 Verifying Audit Ledger Integrity (AT-14)
```bash
python -c "
from core.evidence_ledger import EvidenceLedger
ledger = EvidenceLedger()
res = ledger.verify_chain()
print('Audit Ledger Integrity:', res)
assert res.get('valid') is True
"
```

### 4.3 Quota Monitoring
Query monthly tenant usage against limits:
```bash
curl -X GET "http://localhost:8000/api/v8/agent-factory/quotas" \
  -H "X-Tenant-ID: {tenant_id}" \
  -H "X-User-ID: {admin_id}" \
  -H "X-Company-ID: {company_id}"
```
Metric caps enforced: `builds`, `agents_published`, `tokens`, `cost_usd`, `sandbox_seconds`, `concurrent_builds`.
