# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Agent Workforce Runtime & Resource Governor Specification

---

### 1. Scope & Invariants
The `AgentResourceGovernor` (`core/agent_resource_governor.py`) enforces admission control over autonomous agents to prevent recursive explosion, token exhaustion, and noisy-neighbor denial-of-service across tenants.

> [!IMPORTANT]
> **Constitutional Limits**:
> * Maximum Concurrent Agents: 100 per tenant.
> * Maximum Child Spawning: 5 per parent agent.
> * Maximum Delegation Depth: 4 levels.
> * Child Authority: `child_authority <= parent_authority` (Strictly monotonic decay).

---

### 2. Multi-Dimensional Admission Control
Every resource request is evaluated prior to execution:
* **Token Budget**: 100,000 tokens/min rolling window. Evaluated via sliding window in coordination layer.
* **Tool Call Rate**: 500 calls/min rolling window. Throttled with `HTTP 429 Retry-After`.
* **Browser Sessions**: Maximum 10 concurrent headless Chromium containers per tenant.
* **OpenHands Sandboxes**: Maximum 5 concurrent execution workspaces per tenant.
* **Spend Quota**: Daily monetary spending cap ($1,000/day default).
