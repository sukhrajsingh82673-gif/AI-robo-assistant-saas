# SUMMARY & DECISION REQUEST — ZONATA Agent Factory Phase 1 Audit

**Audit Date:** 2026-11-19  
**Audited Commit:** `6003d16` on branch `agent-factory/audit`  
**Host Environment:** Linux ARM64 (Termux on Android)  
**Deliverables Produced:**
- [`INVENTORY.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/agent-factory/audit/INVENTORY.md)
- [`PORT_MAP.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/agent-factory/audit/PORT_MAP.md)
- [`REUSE_QUESTIONS.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/agent-factory/audit/REUSE_QUESTIONS.md)
- [`API_CONVENTIONS.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/agent-factory/audit/API_CONVENTIONS.md)
- [`LICENCE_GATE.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/agent-factory/audit/LICENCE_GATE.md)
- [`SECURITY_HYGIENE.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/agent-factory/audit/SECURITY_HYGIENE.md)

---

## 1. What Exists & Has Been Verified by Execution

1. **EvidenceLedger (Cryptographic Proof):**
   - Verified append-only Merkle ledger with SHA-256 block digests and `fcntl.flock` file locking.
   - **Real Execution:** Sealed 3 physical verifications into a fresh ledger. Tampering a single hash immediately triggered verification failure with exact fork detection at index 2.
2. **KillSwitchMatrix & Coordination:**
   - 9-level barrier (`GLOBAL`, `TENANT`, `COMPANY`, `SESSION`, `EXECUTION`, `DOMAIN`, `AGENT`, `EMPLOYEE`, `TOOL`).
   - **Real Execution:** Activated `AGENT` kill switch for `agt_rogue_42`; `ZonataActionGateway` instantly aborted action with `ActionGatewayRejection [KILLSWITCH_TRIGGERED]`. Clean recovery on deactivation.
3. **ActionGateway & Policy Enforcement:**
   - Mandatory 20-step pipeline (`core/action_gateway.py`).
   - **Real Execution:** SSRF probe to cloud metadata `169.254.169.254` blocked at Step 7 (`SSRF_BLOCKED`). Safe internal capability succeeded.
4. **Multi-Tenant Isolation:**
   - `TenantRuntime` and tenant-scoped queries.
   - **Real Execution:** Cross-tenant reads between two test tenants returned 0 rows (`Properly Isolated: True`).
5. **Existing UI & Contract Suites:**
   - `npm run test:ui`: 1 passed.
   - `npm run test:assistant`: 41 contract tests + 29 jsdom tests + 12 e2e checks + 79 pytest tests passed (100%).
   - `npm run test:company`: 124 pytest tests + 50 UI checks passed (100%).
   - `test_a2a_interoperability.py`: 54 unit tests passed (100%).

---

## 2. What Is Stubbed / Missing / Constrained

1. **Temporal Daemon:**
   - `temporalio` package is not installed; no external Temporal server is reachable.
   - **Action:** Fall back to `DbQueueOrchestrator` (`af_build` / `af_request` table queue) as required by Master Prompt rule.
2. **Hardware Virtualization & MicroVM Sandboxes:**
   - No Docker daemon or KVM virtualization available on this host.
   - **Action:** Operate strictly in **T0 mode**. Model-generated host code execution is prohibited; the untrusted Import lane remains disabled.
3. **Standalone `AuthorityGateway.authorize()` Signature:**
   - Existing authority checks are embedded inside `ZonataActionGateway.execute_action(envelope)` and route tokens.
   - **Action:** Implement a thin `AuthorityPort` adapter wrapping `ZonataActionGateway` without modifying core authority contracts.
4. **Prior Agent Factory Prototypes:**
   - Three older prototypes exist (`core/agent_factory_runtime.py`, `core/agent_factory_v2.py`, `core/enterprise_agent_factory.py`).
   - **Action:** Put legacy builders behind `AgentBuildPort` and migrate with a strangler pattern (`legacy_agent_id` mapping).

---

## 3. Recommended Architectural Adjustments & Phase 2 Order

1. **Database Schema (Phase 2):**
   - Translate `reference/sql/001_agent_factory_core.sql` (24 `af_*` tables) into the repo's migration tool (`migrations/migration_manager.py`).
   - Ensure tenant isolation queries support SQLite in this local development environment, while maintaining PostgreSQL RLS compatibility for staging/production.
2. **Factory State Transitions:**
   - Implement `agent_factory/domain/transition.py` with evidence-before-effect guarantees. Every lifecycle state change must record a Merkle ledger event before committing.
3. **Queue Orchestration:**
   - Deploy `DbQueueOrchestrator` claiming build jobs using database transactions and heartbeat leases.

---

## 4. Explicit Decision Requests for Gate D1 (Awaiting Human Approval)

- [ ] **Decision D1.1 (Orchestration):** Confirm using `DbQueueOrchestrator` (Postgres/SQLite table queue) since Temporal is not deployed.
- [ ] **Decision D1.2 (Sandbox Tier):** Confirm pilot will operate in **T0 mode** (declarative spec compilation only, zero untrusted host code execution, Import lane disabled).
- [ ] **Decision D1.3 (Legacy Factory):** Confirm placing existing `agent_factory_runtime` and `agent_factory_v2` behind `AgentBuildPort` using a strangler migration pattern.
- [ ] **Decision D1.4 (Phase 2 Go-Ahead):** Approve proceeding to **Phase 2: Foundation & Governance** (creating branch `agent-factory/phase-2`, core schema migrations, ports, adapters, and transition helper).

---

**STATUS: Phase 1 repository audit is complete. STOPPING as instructed to await human approval for Gate D1.**
