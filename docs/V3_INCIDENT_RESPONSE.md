# ZONATA V3 — Incident Response & Triage Framework

## 1. Severity Classifications
- **SEV-1 (Critical Outage):** Complete inability to execute commands, database corruption, broken cryptographic ledger, or compromise of tenant boundaries.
- **SEV-2 (Major Degradation):** Loss of leader node with failover delay, rate limiting affecting > 20% of traffic, or Temporal worker disconnects.
- **SEV-3 (Minor Disruption):** Single worker pod crash, temporary token refresh retry, or sandbox execution timeout.

---

## 2. Emergency Killswitch Procedures
To immediately halt a runaway agent, compromised integration, or hostile tenant:

### 1. Halt a Runaway Agent
```python
from core.distributed_coordination import coordination
coordination.trip_killswitch("AGENT", "agt_target_id", reason="Runaway token spend detected by governor")
```

### 2. Freeze an Entire Tenant Fleet
```python
from core.distributed_coordination import coordination
coordination.trip_killswitch("TENANT", "tnt_compromised", reason="Security incident isolation")
```

### 3. Revoke External SaaS Integration (Nango)
```python
from core.nango_integration_runtime import IntegrationKillSwitch
IntegrationKillSwitch.kill_connection("tnt_id", "conn_id", reason="Compromised OAuth refresh token")
```

---

## 3. Post-Incident Root-Cause Analysis (RCA) Protocol
1. Export immutable evidence events from `merkle_evidence_events` for the relevant causality and action IDs.
2. Verify previous-hash linkage to confirm no post-incident log alteration.
3. Archive system metrics from `observability_engine` covering latency, CPU, and backpressure.
4. Record formal post-mortem including timeline, root cause, and remediation commits.
