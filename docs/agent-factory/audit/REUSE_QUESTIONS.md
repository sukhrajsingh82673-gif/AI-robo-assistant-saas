# REUSE_QUESTIONS — ZONATA Agent Factory Phase 1 Audit

## Question 1: Does an agent factory / builder already exist?
**Answer: YES — three prior generation prototypes exist in `core/`.**
- **Existing Implementations:**
  1. `core/agent_factory_runtime.py`: Implements a 12-stage lifecycle (`DESIGNED` -> `VALIDATING` -> `SANDBOXED` -> `TESTING` -> `PENDING_APPROVAL` -> `APPROVED` -> `ACTIVE` -> `DEGRADED` -> `SUSPENDED` -> `QUARANTINED` -> `REVOKED` -> `RETIRED`), quotas, self-modification defenses, and tool synthesis.
  2. `core/agent_factory_v2.py`: Implements `AgentPackage` dataclass, semantic versioning (`v1`, `v2`, `v3`), evaluation scoring via `AgentEvaluationEngine`, and immutable package hashing (`immutable_agent_packages`).
  3. `core/enterprise_agent_factory.py`: Implements `AgentBlueprint` (name, role, department, mission, responsibilities, capabilities, tools, budget, approval threshold, KPIs) and natural-language creation routes.
- **Classification & Strategy:**
  - Prototype / semi-functional implementations; lacks the strict separation of concerns, LangGraph spec compiler, and independent QA gates specified in the Agent Factory architecture.
  - Per master prompt rules: Do **not** delete or replace them. Wrap legacy capabilities behind `AgentBuildPort` and migrate with a strangler pattern (`legacy_agent_id` mapping) via an ADR.

---

## Question 2: Is there an agent registry with identities?
**Answer: YES.**
- **Existing Tables:**
  - `governed_agents` (in `core/db.py` line 3049): `(agent_id, name, version, tenant_id, company_id, role, parent_agent_id, delegation_depth, capabilities, allowed_tools, resource_budget, lifecycle_state, health_status, is_quarantined, created_at, updated_at)`.
  - `immutable_agent_packages` (in `core/db.py` line 3393): `(package_id, tenant_id, company_id, template_id, agent_version, prompt_hash, model_version, tool_package_hashes, policy_version, composite_package_hash, certified_for_production, created_at)`.
  - `stateful_agent_identities`: Used by stateful conversation sessions.
- **Strategy:**
  - The new factory table `af_agent` must maintain reference links (`agent_id`) to `governed_agents` to avoid duplicating identity registries.

---

## Question 3: Does AuthorityGateway expose a callable `authorize` that real routes use?
**Answer: NO.**
- **Finding:**
  - `AuthorityGateway` is referenced extensively across 69+ files as an architectural boundary, but no standalone class `AuthorityGateway` with method `authorize(principal, action, resource, meta) -> Decision` exists in production routes.
  - Subsystem enforcement is executed via `core/action_gateway.py` (`ZonataActionGateway.execute_action(envelope: ActionEnvelope)`) which runs a 20-step pipeline including SSRF defense, rate limits, self-modification checks, and approval gates.
  - API route authentication is enforced via `core/auth.py` and session validation tokens.
- **Strategy:**
  - `AuthorityPort` will wrap `ZonataActionGateway` and create a dedicated, minimal `AuthorityGateway` adapter matching the factory interface without altering core ZONATA authority contracts.

---

## Question 4: Is the EvidenceLedger append-only with a verified hash chain?
**Answer: YES — IMPLEMENTED AND VERIFIED.**
- **Finding:**
  - Implemented in `core/evidence_ledger.py` (`EvidenceLedger`) and `core/evidence_service.py`.
  - Backed by atomic OS file-locking (`fcntl.flock(f.fileno(), fcntl.LOCK_EX)`), SHA-256 block digest chaining (`prev_hash`), and Merkle tree root computation (`get_merkle_root`).
  - Chain integrity verification (`verify_full_chain_integrity`) mathematically detects any forked, deleted, or tampered ledger entries.
- **Verification Evidence:**
  - In Phase 1 governance probe: 3 entries were sealed, verifying valid status. Modifying the `sha256_digest` of entry #1 immediately caused `verify_full_chain_integrity` to return `valid=False` and accurately identify the exact fork at index 2.

---

## Question 5: Is Temporal actually deployed and reachable where the app runs?
**Answer: NO.**
- **Finding:**
  - The `temporalio` package is not installed on this host, and no Temporal server daemon is reachable.
  - The repo contains `core/temporal_durable_execution_runtime.py` and `zonata/temporal_adapter.py`, which provide an in-process SQLite/Postgres emulation layer for durable execution.
- **Decision:**
  - Per master prompt rules: Fall back to `DbQueueOrchestrator` (`af_build` / `af_request` table queue claimed with `SELECT ... FOR UPDATE SKIP LOCKED` or local lock).

---

## Question 6: What is the tenant boundary and how is it enforced (RLS vs app filter)?
**Answer: Application-level query filtering backed by TenantRuntime.**
- **Finding:**
  - In the current SQLite codebase, multi-tenancy is enforced through `core/tenancy.py` (`TenantRuntime`) where bearer tokens resolve `tenant_id` and all queries explicitly filter `WHERE tenant_id = ?`.
  - While PostgreSQL migrations exist in `migrations/pg/`, Row Level Security (`ENABLE ROW LEVEL SECURITY`) with `SET LOCAL zonata.tenant_id = :id` is specified in the Factory Target Architecture (Section 6.1) and must be introduced cleanly during Phase 2 migrations.

---

## Question 7: Is there a sandbox/terminal able to run untrusted code with isolation?
**Answer: T0 (Host execution with policy filtering) ONLY.**
- **Finding:**
  - `core/universal_terminal/runtime_adapters.py` defines `LinuxRuntimeAdapter`, `ContainerRuntimeAdapter`, and `VMRuntimeAdapter`.
  - However, in this Android / Termux ARM64 environment, Docker and QEMU/microVM daemons are unavailable.
  - Execution falls back to host subprocess execution with environment scrubbing and command blacklisting.
- **Decision:**
  - Sandbox Tier = **T0 only**. Code generation in host backend is strictly forbidden. The Import lane and untrusted code execution remain disabled.

---

## Question 8: What language, framework, migration tool, API version, error shape, pagination, and test pattern are in use?
**Answer:**
- **Languages:** Python 3.11+ / Node.js 20+ (vanilla JS client scripts with JSDOM).
- **Web Server Framework:** Native Python `http.server.HTTPServer` / `BaseHTTPRequestHandler` via `RoboAssistantServer` in `api_server.py` (not FastAPI or Flask).
- **Migration Tool:** Custom migration manager in `migrations/migration_manager.py` with SQL dialect splitters for SQLite and PostgreSQL.
- **API Version in Use:** Highest active version is `/api/v8/` (269 routes, handled by `core/v8_api_handler.py`).
- **Error Response Shape:** Standard JSON: `{"error": "<message>", "status": <code/name>, "code": "<CODE>"}`.
- **Pagination Pattern:** Cursor-based / limit-offset using query parameters `limit` and `offset` / `before` / `after`.
- **Test Pattern:**
  - Frontend/UI: Contract assertions with Node.js scripts + JSDOM (`tests/*_test.js`).
  - Backend: `pytest` and `unittest` with test cases in `tests/test_*.py`.
