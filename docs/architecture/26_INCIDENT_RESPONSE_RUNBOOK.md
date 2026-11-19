# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Security Incident Response Runbook (V2)

---

### 1. Incident Classification & Severity Levels
* **SEV-1 (CRITICAL)**: Cross-tenant data breach, Merkle ledger tampering, rogue agent self-modification attempt, active API key leak.
* **SEV-2 (HIGH)**: API rate limit saturation, supervisor lease oscillation, single worker pool degradation.
* **SEV-3 (MEDIUM)**: Elevated transient 500s from external SaaS providers, disk warning (>70%).
* **SEV-4 (LOW)**: Minor telemetry formatting warnings, non-critical background job delay.

---

### 2. Immediate Containment Playbooks

#### Scenario A: Rogue Agent Containment (Distributed KillSwitch)
```python
from core.distributed_coordination import coordination
# Instantly halt the rogue agent across all cluster nodes in <100ms
coordination.set_killswitch_state("AGENT", "agt_rogue_id", is_killed=True, reason="SEV-1 Security Containment")
```

#### Scenario B: Compromised SaaS Credential
```python
from core.auth import TokenRevocationStore
from core.distributed_coordination import coordination
# 1. Trip provider killswitch
coordination.set_killswitch_state("PROVIDER", "hubspot", is_killed=True, reason="Token compromise")
# 2. Revoke associated session tokens
TokenRevocationStore.revoke("tok_compromised_handle")
```

#### Scenario C: Tenant Suspension
```python
from core.distributed_coordination import coordination
coordination.set_killswitch_state("TENANT", "tnt_bad_actor", is_killed=True, reason="Payment fraud / Abuse")
```
