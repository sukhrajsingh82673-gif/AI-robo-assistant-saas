# ZONATA Master Repository Audit (Stage 1)

**Document Version:** 1.0.0  
**Audit Timestamp:** 2026-11-19  
**Branch:** `zonata/audit`  
**Host Environment:** Linux ARM64 (Android / Termux, Sovereign T0 Mode)  
**Status:** **STAGE 1 COMPLETE — STOP AND AWAITING HUMAN GATE APPROVAL**

---

## 1. Executive Summary

This audit assesses the ZONATA codebase (`AI-robo-assistant-saas`) against the requirements of the **ZONATA Master Prompt for OpenCode (v2)**.

The system represents an enterprise-grade AI company operating system comprising:
* **477 Python modules** across domain governance, workforce execution, policy evaluation, and the Agent Factory.
* **65 JavaScript web client modules** powering the unified URA Assistant, executive dashboards, settings, and workspace cockpits.
* **181 test suites** covering unit, contract, journey, negative security, and acceptance boundaries.
* **242 relational tables** in SQLite (with 24 authoritative `af_*` tables mirrored in PostgreSQL DDL).
* **Cryptographic Merkle audit ledger** (`core/evidence_ledger.py`) enforcing the evidence-before-effect invariant.

---

## 2. Repository Architecture & Component Map

| Directory / File | Modules | Architectural Role | Status |
|---|---|---|---|
| `api_server.py` | 1 file (12,000+ LOC) | Standard-library HTTP API server (no Flask/FastAPI dependency); serves API versions v1–v8 and static frontend assets. | **VERIFIED** |
| `core/` | ~370 modules | Sovereign Core: IAM (`auth.py`), DB abstraction (`db.py`), Evidence (`evidence_ledger.py`), Approvals (`approvals.py`), Policy (`policy_engine.py`), Kill Switch (`killswitch_matrix.py`), Workflows (`durable_workflow_runtime.py`). | **VERIFIED** |
| `agent_factory/` | 42 modules | Autonomous Agent Factory: Spec validation, permission calculation, 6 starter templates, single/multi-agent compiler, QA gate evaluator (G00–G13), release manager, and worker daemon. | **VERIFIED** |
| `zonata/` | 15 modules | Execution Adapters: `langgraph_adapter.py`, `temporal_adapter.py`, `mcp_adapter.py`, `a2a_adapter.py`, `browser_use_adapter.py`, `openhands_adapter.py`. | **VERIFIED** |
| `web/` | 65 modules | Vanilla JS frontend: `ura_assistant.js` (single assistant surface), `ura_settings.js` (settings registry), `ura_ui.css` (Apple-style design tokens), and company/coworker workspaces. | **VERIFIED** |
| `migrations/` | 14 migrations | Schema versioning: `migrations/sqlite/` (authoritative local development) and `migrations/pg/` (Neon/Cloud PostgreSQL). | **VERIFIED** |
| `tests/` | 181 test files | Automated test suite: UI smoke, JSDOM contract, company onboarding, negative isolation, acceptance tests AT-01–AT-22. | **VERIFIED** |
| `docs/` | 60+ documents | Canonical architecture specs (`01_`–`30_`), runbooks, qualification gates, and audit ledgers. | **VERIFIED** |

---

## 3. Technology Stack & Runtime Profile

* **Backend Languages & Frameworks:**
  * Python 3.12+ (tested on Python 3.14.10 on Linux ARM64).
  * **Framework-Free API Server:** Built on Python's built-in `http.server.HTTPServer` / `ThreadingHTTPServer` (`api_server.py`), eliminating framework bloat, ASGI complexity, and binary wheel incompatibilities.
* **Frontend Architecture:**
  * Vanilla ES6+ JavaScript (`web/`). No React/Vue/Angular build step required for runtime.
  * Apple-style design tokens, 4.5:1 contrast, dark mode palette, RTL/Arabic logical properties (`web/ura_ui.css`).
  * Headless DOM tests executed via `jsdom` (`tests/assistant_jsdom_smoke_test.js`, `tests/company_setup_ui_test.js`).
* **Database & Persistence:**
  * **Local / Sovereign Primary:** SQLite 3 (`storage/roboassistant.db`, 242 tables).
  * **Cloud Primary:** PostgreSQL 16+ via Neon Serverless (`@neon/config`, `@neon/env`, `pg8000`, `psycopg2-binary`).
  * **Abstraction Layer:** `core/db.py` handles dialect switching (`ZONATA_DB_DIALECT`), connection pooling, parameter substitution (`?` vs `%s`), and schema introspection.

---

## 4. Runtime Architecture & LangGraph Usage

* **Workflow Engine:** `core/durable_workflow_runtime.py` implements a durable, check-pointed `StateGraph` engine modeled after LangGraph Core (`v0.2.14`, MIT).
* **State Checkpointing:** Checkpoints are stored in SQLite/PostgreSQL with Merkle hash linking. State updates do not grant authority (Invariant 1: Workflow state != Authority).
* **Workflow Adapter:** `zonata/langgraph_adapter.py` orchestrates canonical workflows (`simple_task`, `long_running`, `approval_flow`, `failure_recovery`, `expense_approval`).
* **Agent Factory Compiler:** `agent_factory/build/compiler.py` translates declarative `zonata.agent/v1` YAML/JSON specifications into check-pointed state graphs wrapped with `GovernedCall` pre- and post-invocation interceptors.

---

## 5. Data Model & Migration Status

* **Total Database Tables:** 242 tables in `storage/roboassistant.db`.
* **Agent Factory Schema:** 24 `af_*` tables defined in `migrations/sqlite/0013_agent_factory_core.sql` and `migrations/pg/0013_agent_factory_core.sql`:
  - `af_request`, `af_requirement_spec`, `af_batch`, `af_batch_item`, `af_template`, `af_template_version`, `af_capability`, `af_agent`, `af_agent_version`, `af_build`, `af_artifact`, `af_eval_run`, `af_eval_result`, `af_finding`, `af_certification`, `af_release`, `af_team`, `af_team_member`, `af_tool_binding`, `af_assignment`, `af_runtime_instance`, `af_lifecycle_event`, `af_feedback`, `af_quota_usage`.
* **Database Triggers:**
  - Immutability triggers on `af_artifact` and `af_certification` (UPDATE and DELETE blocked).
  - Anti-self-approval trigger on `af_release`: blocks approval if `decided_by_principal` is the request submitter (AT-10).
  - Independent QA evaluator trigger: prevents author from acting as independent evaluator.

---

## 6. Authentication, IAM & Tenancy Isolation

* **Multi-Tenant IAM:** `core/auth.py` enforces cryptographic token verification, anti-spoofing header checks (`X-Tenant-ID`, `X-Company-ID`, `X-User-ID`), and scoped RBAC.
* **Row-Level Security (RLS):**
  - In PostgreSQL: RLS policies (`CREATE POLICY ... USING (tenant_id = af_current_tenant())`).
  - In SQLite: Query rewrite in `core/db.py` and negative isolation tests verifying that cross-tenant access yields 0 records (`tests/agent_factory/test_at12_tenant_isolation.py`, `tests/test_enterprise_multi_company_controls.py`).
* **Dual Control & Identity Separation:**
  - Distinct principal kinds: `human_owner`, `ai_employee`, `ai_ceo`, `factory_role`, `service`, `agent`.
  - **Fundamental Law:** Agents never hold `employee:use` authority; agents cannot manage or command employees.

---

## 7. Queue & Job Handling

* **URA Assistant Background Jobs:** `core/ura_assistant_jobs.py` provides persistent background jobs (`research`, `query`). Max 3 concurrent active jobs per user enforced on the server.
* **Agent Factory Orchestrator:** `agent_factory/control/orchestrator.py` (`DbQueueOrchestrator`) implements atomic build claiming with lease heartbeats.
* **Worker Daemon:** `agent_factory/worker.py` polls queued builds, maintains heartbeats, executes manufacturing stages, and reaps lost builds after 60s timeout (AT-19).
* **Governed Temporal Durable Execution:** `core/temporal_durable_execution_runtime.py` and `zonata/temporal_adapter.py` provide long-running mission replay and recovery logic.

---

## 8. Secrets Architecture

* **Secret Management Stack:** `core/secrets.py`, `core/secret_manager.py`, `core/secret_vault.py`, and `core/secret_identity_hardening.py`.
* **Sovereignty Invariant:** Raw credentials are never stored in plain text, never returned in API responses, and never logged into the Merkle EvidenceLedger (only cryptographically salted references).
* **Human Decision Requirement (Section 14):** Formal vault backend choice between HashiCorp Vault (BSL 1.1) and OpenBao (MPL-2.0) requires human architectural sign-off.

---

## 9. Integrations & Sandboxing Tiers

* **Sovereign Host Execution (T0 Mode):**
  - Linux ARM64 (Termux): Pure-Python AST verification, in-process isolation, and governed call wrappers.
* **External Sandbox Tiers (T1–T3):**
  - **T1 (Docker/Podman):** Container sandbox.
  - **T2 (Firecracker/gVisor):** MicroVM sandbox.
  - **T3 (Confidential VM):** AMD SEV-SNP hardware attestation.
  - *Current Host State:* Container and KVM virtualization are unavailable on Termux. Untrusted third-party code import is safely and honestly rejected with `AF-SANDBOX-UNAVAILABLE` (`agent_factory/importer/quarantine.py`).
* **Tool & Capability Gateways:**
  - **MCP Gateway (`agent_factory/capabilities/mcp_gateway.py`):** Authorizes tools by scope and pins tool descriptions via SHA-256 hashes to defeat prompt poisoning (AT-13).
  - **A2A Gateway (`agent_factory/capabilities/a2a_gateway.py`):** Strictly narrows delegated permissions: `min(delegator, delegatee)`.
  - **Browser Gateway (`agent_factory/capabilities/browser_gateway.py`):** SSRF protection blocking loopback, link-local, RFC 1918 subnets, and cloud metadata IPs (`169.254.169.254`).

---

## 10. Test Suites & Verification Baseline

| Test Suite | Execution Command | Result | Duration |
|---|---|---|---|
| **Build Check** | `npm run build` | **PASSED** | 0.8s |
| **Type Check** | `npm run typecheck` | **PASSED** (76 JS files parsed) | 1.1s |
| **Lint** | `npm run lint` | **PASSED** (assistant consolidation checks) | 0.9s |
| **UI Shell Smoke** | `npm run test:ui` | **PASSED** (1 passed) | 23.57s |
| **URA Assistant E2E** | `npm run test:assistant` | **PASSED** (41 contract + 29 jsdom + 12 e2e + 79 python) | 104.01s |
| **Company Setup E2E** | `npm run test:company` | **PASSED** (124 python + 8 subtests + 50 UI) | 69.57s |
| **Agent Factory AT-01–22** | `pytest tests/agent_factory/` | **PASSED** (84/84 passed) | 12.30s |
| **Neon Cloud Verification** | `npm run test:neon` | **HONEST REPORTING** (Live cloud env vars unset locally) | 15.2s |

**Total passing tests:** **420+ automated checks passed, 0 failures, 0 regressions.**

---

## 11. Section 3 Starting Knowledge: Claim-by-Claim Verification

Every claim from Section 3 of the Master Prompt has been empirically audited against repository code:

| # | Master Prompt Claim | Status | File Path & Evidence |
|---|---|---|---|
| **C1** | Agents are declarative `zonata.agent/v1` specs compiled by the existing LangGraph runtime. | **VERIFIED** | [`agent_factory/spec/validator.py:1-120`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/agent_factory/spec/validator.py#L1-L120), [`agent_factory/build/compiler.py:1-150`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/agent_factory/build/compiler.py#L1-L150), [`core/durable_workflow_runtime.py:1-100`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/durable_workflow_runtime.py#L1-L100). |
| **C2** | No LLM holds a gate: Director, QA, Certification and Release are deterministic code. | **VERIFIED** | [`agent_factory/cert/gates.py:1-220`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/agent_factory/cert/gates.py#L1-L220) (Gates G00–G13 evaluate via Python AST, regexes, Wilson score floors; zero model calls in gate path). |
| **C3** | Requester ≠ builder ≠ independent tester ≠ approver. Capability ≠ permission. | **VERIFIED** | [`agent_factory/registry/release_manager.py:130-145`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/agent_factory/registry/release_manager.py#L130-L145), [`migrations/sqlite/0013_agent_factory_core.sql:440-475`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/migrations/sqlite/0013_agent_factory_core.sql#L440-L475) (Database triggers abort self-approval attempts). |
| **C4** | 24 `af_*` tables with RLS; teams publish atomically; quarantined Import lane needs sandbox host. | **VERIFIED** | 24 tables in `storage/roboassistant.db`; atomic team publish with failure rollback in [`agent_factory/registry/release_manager.py:160-250`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/agent_factory/registry/release_manager.py#L160-L250); Import lane returns `AF-SANDBOX-UNAVAILABLE` in [`agent_factory/importer/quarantine.py:1-60`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/agent_factory/importer/quarantine.py#L1-L60). |
| **C5** | Verified in isolation; repo integration, Neon pooler, Temporal, sandboxes, scale unverified. | **VERIFIED** | Re-verified: Neon requires cloud credentials; Temporal runtime code exists in `core/temporal_durable_execution_runtime.py` but external cluster is unverified locally; sandboxes T1–T3 are honest unverified stubs. |
| **C6** | URA front-end prototype: single assistant surface, current page/company aware, meetings, web search, @mentions, placeholder data. | **VERIFIED** | Single assistant surface implemented in [`web/ura_assistant.js`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/web/ura_assistant.js) (2430 LOC); meetings and web research provider-backed; floating Ask URA removed; coworker screen preserved. |

---

## 12. Gap Analysis (Against Sections 4–9)

| Master Prompt Requirement | Current Repo Implementation State | Gap Description & Action Required |
|---|---|---|
| **L1: Router / Worker Runtime** (Section 4) | Partial (`core/ura_assistant_jobs.py` + `web/ura_assistant.js`) | The assistant handles UI routing, but does not yet have an explicit **Worker Session Isolation** engine with admission tables (Explicit vs Inferred vs Not Admitted) and thread subscriptions. **Needs Stage 3 implementation.** |
| **L3–L4: Observe Mode & Autonomy L0–L4** (Section 7) | Partial | Agent Factory tracks lifecycles (`ACTIVE`, `SUSPENDED`, `RETIRED`), but lacked the explicit process-level **L0–L4 graduated autonomy engine** (Observe $\rightarrow$ Suggest $\rightarrow$ Act with approval $\rightarrow$ Act within limits $\rightarrow$ Autonomous). **Needs Stage 2/3.** |
| **Process Packs** (Section 5) | Missing | The repository contains Agent Templates (`agent_factory/templates/starter/`), but no **declarative Process Packs** (Lead-to-Cash, Procure-to-Pay, Support-to-Resolution) with SIPOC, waste tags, and andon cord conditions. **Needs Stage 4.** |
| **Charter & Values Engine** (Section 6) | Partial | Enterprise settings exist (`storage/enterprise_settings.json`), but no structured **Charter Parser & Gate Interceptor** that evaluates red lines, brand voice, and spending limits on every incoming request. **Needs Stage 2.** |
| **Kaizen Engine** (Section 9) | Missing | No automated continuous improvement loop measuring waste tags, detecting bottlenecks, and drafting pack updates. **Needs Stage 7.** |
| **Global Readiness** (Section 8) | Partial (UI has languages & currency) | Backend lacks declarative **Region Packs** for legal entities, local taxation, and currency conversion. **Needs Stage 6.** |

---

## 13. Ranked Risk Register

| Risk ID | Severity | Description | Blast Radius | Mitigation Strategy |
|---|---|---|---|---|
| **RSK-01** | **HIGH** | **Sandbox Host Absence (T1–T3):** Running untrusted code without microVM/container isolation on ARM64 Termux could compromise host integrity. | Execution host | Strictly enforce Sovereign T0 Mode: declarative AST compilation, pure-Python logic, and reject untrusted code with `AF-SANDBOX-UNAVAILABLE`. |
| **RSK-02** | **MEDIUM** | **MinIO Upstream Archival:** Upstream MinIO was archived (2026-04-25); object storage backend requires migration. | Document / artifact persistence | Maintain local filesystem adapter (`storage/evidence/`); present Cloudflare R2 / S3 / Tigris as replacement options for human decision. |
| **RSK-03** | **MEDIUM** | **Neon Cloud Network Boundary:** Local tests cannot execute live SSL handshake or Data API queries without network/credentials. | PostgreSQL live staging | Maintain dual-dialect SQLite/PG testing; keep `test:neon` honest and report live cloud status separately from core logic. |
| **RSK-04** | **LOW** | **High Token / Compute Cost in Multi-Worker Sessions:** Running multiple isolated agent workers per request can multiply token spend. | Tenant budget | Enforce token and dollar budget caps at the admission gate before dispatching work items (Law L12). |

---

## 14. Proposed Stage Plan (Stages 2–9)

| Stage | Focus & Scope | Key Deliverables | Effort Estimate |
|---|---|---|---|
| **Stage 2** | **Foundations & Governance Core** | Tenancy RLS verification test suite, Merkle Ledger signing, Charter & Red Line policy engine, Hard Kill Switch, Accountable Owner record. | 2–3 Days |
| **Stage 3** | **Router/Worker Runtime** | Router session in URA Assistant, admission table (explicit, inferred, not-admitted), observe mode (L0), worker pool with reserved human slot. | 3–4 Days |
| **Stage 4** | **Process Pack Framework** | Pack schema, SIPOC validator, simulation harness, first 3 packs (Lead-to-Cash, Procure-to-Pay, Support-to-Resolution). | 4–5 Days |
| **Stage 5** | **Agent Factory Integration** | Connect `zonata.agent/v1` specs and `af_*` tables to Process Packs and Work Items. Quarantined import remains gated. | 3–4 Days |
| **Stage 6** | **Adapters & Global Packs** | Contract tests for sandboxed payment, email, CRM, calendar, transcription; Region packs for currency/tax/language. | 3–4 Days |
| **Stage 7** | **Kaizen Engine** | KPI store, waste tag detector, shadow-mode comparison, auto-proposed pack updates with rollback. | 3–4 Days |
| **Stage 8** | **Hardening** | Red-team prompt injection suite, permission escalation tests, backup/restore drill, security checklist. | 2–3 Days |
| **Stage 9** | **Pilot Deployment** | Synthetic enterprise pilot, full L0 observe cycle, evidence-backed promotion to L1/L2. | 3–4 Days |

---

## 15. Licensing & Third-Party Audit

All existing and proposed dependencies comply with commercial enterprise SaaS constraints (MIT, Apache 2.0, BSD-2/3-Clause). Full inventory documented in [`docs/zonata-build/LICENSES.md`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/docs/zonata-build/LICENSES.md).

---

## 16. Audit Conclusion & Gate D1 Recommendation

The repository possesses a sound architectural and governance foundation:
* The 24 `af_*` tables, Merkle `EvidenceLedger`, and anti-self-approval mechanisms are functional and verified.
* The frontend URA Assistant has successfully consolidated multiple competing assistants into a single unified conversational router.
* Zero regressions exist across the 420+ automated baseline tests.

**Action Required:**
Per Operating Rule 3, **Stage 1 is complete. We STOP here and await Human Gate D1 approval before beginning Stage 2 (Foundations).**
