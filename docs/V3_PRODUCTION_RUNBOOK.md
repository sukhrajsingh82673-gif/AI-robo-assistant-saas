# ZONATA V3 — Production Operations & Maintenance Runbook

## 1. Daily Cluster Health Checks
1. **Liveness & Readiness:**
   - Execute: `curl -s http://<api-endpoint>/readyz | jq .`
   - Verify: Response HTTP 200 with `"status": "READY"` and database `"HEALTHY"`.
2. **Leader Election Status:**
   - Query supervisor heartbeats:
     ```sql
     SELECT node_id, status, last_tick FROM supervisor_heartbeats ORDER BY last_tick DESC LIMIT 5;
     ```
   - Confirm exactly one node reporting `LEADER` role within the last 15 seconds.
3. **Queue Health & Backpressure:**
   - Check pending jobs in command queue:
     ```sql
     SELECT status, count(*) FROM async_command_queue GROUP BY status;
     ```
   - Verify `QUEUED` count is draining smoothly and `UNKNOWN_OUTCOME` is 0.

---

## 2. Dynamic Plan Quota Adjustment
To modify tenant quota tiers or assign custom resource limits:
```python
from core.agent_resource_governor import resource_governor, PlanTier

# Upgrade tenant to ENTERPRISE tier (500 agents)
resource_governor.set_tenant_tier("tenant_123", PlanTier.ENTERPRISE)

# Set custom parameter overrides (e.g. increase browser sessions)
resource_governor.set_tenant_tier("tenant_123", PlanTier.ENTERPRISE, custom_overrides={
    "max_browser_sessions": 100
})
```

---

## 3. Routine Backups
Execute scheduled cold/warm snapshots:
```bash
python3 -c "from core.disaster_recovery import DisasterRecoveryEngine; snap = DisasterRecoveryEngine().create_snapshot(); print('Snapshot created:', snap)"
```
Verify the output archive in `storage/backups/`.
