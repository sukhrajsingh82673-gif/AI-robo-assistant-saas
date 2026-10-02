# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Emergency Rollback Runbook & Procedures

---

### 1. Rollback Triggers
An immediate rollback is declared if:
1. P95 API latency exceeds 2,500ms for more than 5 consecutive minutes.
2. Error rate exceeds 1.0% of total mutating transactions.
3. Any cross-tenant data boundary violation or Merkle ledger fork is detected.
4. Active Temporal workflows fail to recover across worker deployments.

---

### 2. Tiered Rollback Procedures

#### Tier 1: Agent Package Rollback
To roll back a malfunctioning or regressed AI employee to a previously certified immutable package:
```python
from core.agent_factory_v2 import agent_factory_v2
agent_factory_v2.rollback_agent_version(tenant_id="tnt_primary", agent_id="agt_sales_01", target_version="v1.0.0")
```

#### Tier 2: Deployment Replicas Rollback
```bash
# Roll back Kubernetes deployment to previous release revision
kubectl rollout undo deployment/zonata-api -n zonata-prod
kubectl rollout undo deployment/zonata-workers -n zonata-prod
kubectl rollout undo deployment/zonata-supervisor -n zonata-prod
```

#### Tier 3: Database Schema Migration Rollback
1. Put cluster in maintenance mode (`coordination.set_killswitch_state("GLOBAL", "SYSTEM", True)`).
2. Restore database from pre-migration snapshot:
```bash
python3 -c "from core.disaster_recovery import dr_manager; print(dr_manager.restore_from_backup())"
```
3. Lift maintenance mode.
