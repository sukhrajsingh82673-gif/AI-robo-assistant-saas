# ZONATA V3 — Agent Factory & Workforce Lifecycle Validation

## 1. Subsystem Architecture
- **Component:** `core.agent_factory_v2.AgentFactoryV2` & `core.agent_resource_governor.AgentResourceGovernor`
- **Scope:** Dynamic AI employee generation, specification synthesis, capability binding, and lifecycle admission control.
- **Dynamic Plan Tiers:**
  - `DEV`: 10 agents
  - `STARTER`: 25 agents
  - `PROFESSIONAL`: 100 agents
  - `ENTERPRISE`: 500 agents
  - `HYPERSCALE`: 5,000 agents
  - `UNLIMITED`: Unlimited (sovereign / dedicated tenant)

---

## 2. Invariant & Test Verification Matrix
| Invariant | Test Target | Verification Method | Status | Classification |
|---|---|---|---|---|
| **INV-AGT-01** | Specification Validation | Rejection of agents without required role/capabilities | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-AGT-02** | Authority Level Bounding | Prohibiting privilege escalation past department head | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-AGT-03** | Dynamic Quota Enforcement | Tiered limits rejecting registrations exceeding plan quota | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-AGT-04** | Lifecycle Transitions | Clean registration, state tracking, and quota release on termination | PASS | `REAL_LOCAL_INFRASTRUCTURE` |
| **INV-AGT-05** | Distributed Registration | Concurrent agent registrations across multiple workers | PASS | `REAL_LOCAL_INFRASTRUCTURE` |

---

## 3. Quota Evaluation & Results
- In `tests/test_v3_multi_process_resilience.py::test_01_dynamic_agent_quota_and_tier_enforcement`:
  - 25 agents registered under `STARTER` tier: All admitted (`ADMIT`).
  - 26th agent attempt under `STARTER` tier: Rejected with `capacity (25) reached`.
  - Upgrade to `ENTERPRISE`: 26th agent admitted immediately.
  - De-registration: All allocated slots reclaimed cleanly.
- **Classification:** `REAL_LOCAL_INFRASTRUCTURE`
