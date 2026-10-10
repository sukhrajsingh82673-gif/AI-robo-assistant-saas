# ZONATA / URA — Integration Health & Incident Runbook

This runbook outlines operational health monitoring, circuit breaker behavior, KillSwitch engagement, and incident containment procedures for the Universal Automation Fabric.

---

## 1. Health Monitoring & Status Probes

### Primary Fabric Health Endpoint
```bash
curl -s http://127.0.0.1:8080/api/automation/fabric/status
```
**Expected Response:**
```json
{
  "status": "OPERATIONAL",
  "killswitch_active": false,
  "metrics": {
    "tenant_id": "tnt_primary",
    "total_executions": 446,
    "completed": 346,
    "failed": 9,
    "unknown_outcome": 0,
    "pending_approvals": 23,
    "success_rate": 0.7758,
    "killswitch_active": false,
    "connectors_active": 18,
    "templates_available": 19,
    "specialized_agent_roles": 11
  }
}
```

### Connector Catalog Status
```bash
curl -s http://127.0.0.1:8080/api/automation/connectors
```
Verifies all 18 connectors report `health_status: "HEALTHY"`.

---

## 2. Circuit Breaker Operations

Each connector maintains an autonomous [`GovernedCircuitBreaker`](file:///root/roboassistant/core/automation_fabric/connector_registry.py#L39-L70):
- **Threshold:** 3–5 consecutive failures (configurable per connector).
- **Behavior in OPEN state:** Immediately raises `CircuitBreakerTrippedError` without calling downstream systems, preventing cascading saturation.
- **Cooldown:** 30 seconds.
- **Recovery:** Automatically enters `HALF_OPEN` state, allowing a single canary probe. If successful, state resets to `CLOSED`.

---

## 3. KillSwitch Engagement & Process Interruption

### Engaging the Emergency KillSwitch
```bash
# Engaging KillSwitch via REST API
curl -X POST http://127.0.0.1:8080/api/automation/killswitch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <valid_token>" \
  -d '{"active": true, "reason": "Suspected unauthorized external API activity"}'
```

### What Happens Internally
1. **Queued Work:** All pending tasks in `QUEUED` state are immediately blocked from dequeuing.
2. **In-Flight Steps:** Active worker loops evaluate `is_killswitch_active()` every 5ms.
3. **Active Subprocesses:** The process group is terminated using `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)`, halting the parent and all child subprocesses cleanly.
4. **Evidence Sealing:** `PROCESS_ABORTED_BY_KILLSWITCH` is sealed into the evidence ledger.

### Disengaging the KillSwitch
```bash
curl -X POST http://127.0.0.1:8080/api/automation/killswitch \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <valid_token>" \
  -d '{"active": false, "reason": "Incident investigated and mitigated"}'
```

---

## 4. Crash-Window Recovery & Unknown Outcome Reconciliation

If a worker process terminates mid-execution:
1. **Safe Queries (`get_*`, `list_*`):** Automatically rehydrated as safe completions without duplicate external execution.
2. **Mutations (`create_*`, `post_*`):** Transitioned to `status: "UNKNOWN_OUTCOME"` with `reconciliation_required=True` in [`UnknownOutcomeEngine`](file:///root/roboassistant/core/unknown_outcome_engine.py).
3. **Operator Reconciliation:**
```bash
curl -X POST http://127.0.0.1:8080/api/automation/executions/<execution_id>/reconcile \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <valid_token>" \
  -d '{"resolution": "CONFIRMED_SUCCESS", "note": "Verified in ERP portal manually"}'
```
