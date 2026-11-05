# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Distributed Chaos Engineering & Fault Injection Plan

---

### 1. Objective & Hypothesis
Validate that the ZONATA Universal AI Company Operating System survives abrupt infrastructure failures without tenant data leakage, broken Merkle audit chains, duplicate mutations, or orphaned mission workflows.

---

### 2. Fault Injection Scenarios

| Scenario ID | Fault Injected | Target Component | Expected System Behavior | Verification Assertion |
| :--- | :--- | :--- | :--- | :--- |
| **CHAOS-01** | `SIGKILL` on active Leader | `CompanySupervisorHA` | Standby node detects expired lease and assumes `LEADER` role within 15s | 0 duplicate schedule dispatches; supervisor continues ticking |
| **CHAOS-02** | Abrupt network timeout during CRM lead creation | `NangoAdapter` | Action transitions to `UNKNOWN_OUTCOME`; blind retry blocked | Record created in `temporal_reconciliations`; reconciliation probe initiated |
| **CHAOS-03** | Rapid concurrent token revocation | `core/auth.py` | Tokens revoked across all nodes via `auth_revoked_tokens` and in-memory cache | Immediate `401 Unauthorized` on next request across all replica nodes |
| **CHAOS-04** | Distributed Killswitch trigger under heavy load | `coordination.set_killswitch_state` | All active worker threads halt before next mutating step | 0 new external side effects; existing in-flight transitions logged |
| **CHAOS-05** | Host disk capacity emergency (95% full) | `StorageGovernor` | Automatic cleanup of temporary browser screenshots; non-essential writes throttled | System stays online; database files protected from `ENOSPC` |
| **CHAOS-06** | Database connection timeout burst | `DatabaseConnectionPool` | Connection pool admission control rejects excess requests with `ConnectionPoolExhausted` | Control-plane health queries remain isolated and responsive |
