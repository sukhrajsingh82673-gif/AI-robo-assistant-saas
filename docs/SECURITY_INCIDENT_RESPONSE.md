# SECURITY INCIDENT RESPONSE PLAYBOOK
**ZONATA Universal AI Company Operating System**  
*Classification: RESTRICTED / INTERNAL INCIDENT RESPONSE*  
*Timestamp: 2026-10-02T11:15:00Z*

---

## 1. Incident Lifecycle

```
[DETECTED] ──► [CONTAINED] ──► [INVESTIGATING] ──► [REMEDIATED] ──► [VERIFIED] ──► [CLOSED]
```

---

## 2. Threat Scenarios & Immediate Containment Actions

### Scenario A: Compromised Agent or Rogue AI Task
1. **Immediate Action**: Trip Agent-level KillSwitch:
   ```python
   from core.nango_integration_runtime import IntegrationKillSwitch
   from core.temporal_durable_execution_runtime import TemporalKillSwitch

   IntegrationKillSwitch.halt("AGENT", agent_id, reason="Security Incident: Compromised Behavior")
   TemporalKillSwitch.trip_agent(agent_id)
   ```
2. Transition Agent state to `QUARANTINED`:
   ```python
   from core.agent_factory_runtime import GovernedAgentFactory, AgentLifecycleState
   GovernedAgentFactory.transition_state(agent_id, AgentLifecycleState.QUARANTINED, reason="Security breach")
   ```
3. Sever all open browser sessions and OpenHands sandboxes associated with the agent.

---

### Scenario B: Leaked API Token or Session Compromise
1. **Immediate Action**: Revoke token ID via `TokenRevocationStore`:
   ```python
   from core.auth import TokenRevocationStore
   TokenRevocationStore.revoke(compromised_token_id)
   ```
2. Rotate secret keys via `core/secrets.py`.
3. Invalidate active Nango connection credentials via `ExternalIntegrationGateway.disconnect_connection()`.

---

### Scenario C: Malicious Inbound Webhook or Replay Attack
1. Verify HMAC-SHA256 signature failure logs in `nango_security_events`.
2. Block source IP or webhook provider endpoint via multi-scope killswitch:
   ```python
   IntegrationKillSwitch.halt("PROVIDER", provider_id, reason="Forged Webhook Signatures Detected")
   ```

---

### Scenario D: Evidence Ledger Integrity Alert / Fork Detected
1. Run emergency cryptographic repair:
   ```python
   from core.evidence_ledger import EvidenceLedger
   ledger = EvidenceLedger()
   repair_res = ledger.repair_and_linearize_ledger()
   ```
2. Verify linearized chain: `ledger.verify_full_chain_integrity()`.
3. Investigate concurrent process execution logs to identify unauthorized un-locked append attempts.
