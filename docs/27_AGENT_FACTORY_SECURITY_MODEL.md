# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
## Agent Factory Security Model (V2)

---

### 1. Invariants & Security Boundaries
* **AGENT CREATION != ACTIVATION**: Creating an agent specification merely produces a `CANDIDATE` artifact; activation requires passing the 13-vector evaluation engine.
* **AGENT != AUTHORITY**: An agent cannot grant itself capabilities, tools, or financial budgets.
* **MONOTONIC PRIVILEGE DECAY**: `child_authority <= parent_authority`. A parent agent cannot spawn a child with higher permissions than its own.
* **IMMUTABLE SIGNING**: Every promoted agent artifact is signed (`sig_factory_v2_...`). Tampering with the on-disk or database specification invalidates the signature and triggers immediate quarantine.
