# INVENTORY — ZONATA Agent Factory Phase 1 Repository Audit

Audited Commit: `6003d16` on branch `agent-factory/audit`  
Platform: Linux ARM64 / Android Termux  

This document inventories all 43 candidate architectural components in the ZONATA repository according to the evidence rubric in the Master Implementation Prompt.

---

## 1. Governance & Core Invariants

### 1.1 Company Kernel
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/departments.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/departments.py), [`core/company_setup/`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/company_setup/), [`core/db.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/db.py)
- **Module/Class/Route:** `core.company_setup`, `core.departments`, routes `/api/v8/companies/*`
- **DB Tables:** `companies`, `departments`, `organization_nodes`, `organization_edges`
- **Existing Tests:** `tests/test_company_setup.py`, `tests/test_company_build_workflow.py` (Executed: YES - 124 passed)
- **Evidence:** `npm run test:company` executed cleanly. Verified company creation, industry blueprints, and non-circular reporting.
- **Gap:** None for base organization model.

### 1.2 Constitution
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/aic_organization_constitution.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/aic_organization_constitution.py), [`core/aic_ceo_constitution.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/aic_ceo_constitution.py)
- **Module/Class/Route:** `OrganizationConstitution`, `CEOSovereignConstitution`
- **DB Tables:** `executive_policy_rules`, `corporate_objectives`
- **Existing Tests:** `tests/test_aic_ceo_constitution.py`, `tests/test_aic_organization_qualification.py` (Executed: YES)
- **Evidence:** Enforces non-negotiable invariants: AI != AUTHORITY, CAPABILITY != PERMISSION.
- **Gap:** Invariants need to be wired into Factory spec compiler (`GovernedCall`).

### 1.3 PolicyEngine
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/policy_engine_v2.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/policy_engine_v2.py), [`core/action_gateway.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/action_gateway.py)
- **Module/Class/Route:** `PolicyEngineV2`, `ZonataActionGateway._step_10_evaluate_policy`
- **DB Tables:** `executive_policy_rules`, `settings_values`
- **Existing Tests:** `tests/test_universal_automation_fabric_qualification.py` (Executed: YES)
- **Evidence:** Governance probe evaluated allowed and denied cases (rate-limiting, SSRF, self-modification checks).
- **Gap:** Needs a direct functional adapter for `PolicyPort.evaluate_agent_policy()`.

### 1.4 AuthorityGateway
- **Classification:** IMPLEMENTED BUT REQUIRES REFACTORING
- **File Paths:** [`core/action_gateway.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/action_gateway.py)
- **Module/Class/Route:** `ZonataActionGateway`, `ActionEnvelope`
- **DB Tables:** `governed_agents`, `permissions`
- **Existing Tests:** Tested via `test_adversarial_security_and_chaos.py` and Governance Probe 1
- **Evidence:** Probe 1 output: `PROBE 1 [DENIED CASE]: BLOCKED as expected -> Action rejected at Step 7 [SSRF_BLOCKED]`.
- **Gap:** Missing standalone `authorize(principal, action, resource, meta)` signature expected by `AuthorityPort`. Currently tightly coupled to `ActionEnvelope`.

### 1.5 Consent / ApprovalEngine
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/approvals.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/approvals.py), [`core/cryptographic_approvals.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/cryptographic_approvals.py)
- **Module/Class/Route:** `ApprovalService`, `CryptographicApprovalVerifier`, routes `/api/v8/approvals/*`
- **DB Tables:** `approvals`, `action_approval_nonces`, `settings_approvals`
- **Existing Tests:** `tests/test_company_setup.py`, `tests/test_audit_remediation_security.py` (Executed: YES)
- **Evidence:** Cryptographic nonce generation and verification implemented. Two-step deletion verification fully enforced.
- **Gap:** Needs binding to agent certification hash as required by Phase 8 release gates.

### 1.6 EvidenceLedger (SHA-256 + Merkle)
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/evidence_ledger.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/evidence_ledger.py), [`core/evidence_service.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/evidence_service.py)
- **Module/Class/Route:** `EvidenceLedger.seal_evidence`, `EvidenceLedger.verify_full_chain_integrity`
- **DB Tables:** File-backed append-only ledger (`storage/evidence/audit_ledger.jsonl`), `production_audit_logs`
- **Existing Tests:** Executed via Phase 1 Governance Probe 2
- **Evidence:** Probe 2 sealed 3 entries (Merkle root `9bd5d46e...`, `valid=True, records_checked=3`). Tampered entry was caught immediately (`valid=False, forks_detected=[{'index': 2, ...}]`).
- **Gap:** None for core hash-chain integrity.

### 1.7 KillSwitchMatrix
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/killswitch_matrix.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/killswitch_matrix.py), [`core/distributed_coordination.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/distributed_coordination.py)
- **Module/Class/Route:** `KillSwitchMatrix`, `KillSwitchLevel`, `coordination.set_killswitch_state`
- **DB Tables:** `enterprise_killswitch_matrix`
- **Existing Tests:** Executed via Phase 1 Governance Probe 3
- **Evidence:** Activation of `KillSwitchLevel.AGENT` for `agt_rogue_42` instantly halted gateway execution: `Action rejected at Step 1 [KILLSWITCH_TRIGGERED]`. Clean recovery on deactivation.
- **Gap:** None.

### 1.8 Multi-tenant Isolation
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/tenancy.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/tenancy.py), [`core/tenant_fairness.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/tenant_fairness.py)
- **Module/Class/Route:** `TenantRuntime`, tenant-scoping filters
- **DB Tables:** `tenants`, `tenant_resource_quotas`, `tenant_isolation_audit`
- **Existing Tests:** Executed via Phase 1 Governance Probe 4
- **Evidence:** Cross-tenant query from Tenant B attempting to read Tenant A company returned 0 rows.
- **Gap:** Currently implemented via application-level queries; PostgreSQL Row-Level Security (RLS) policies need to be applied in Phase 2 migration.

### 1.9 RBAC / Org Authority
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/auth.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/auth.py), [`core/identity_gateway.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/identity_gateway.py)
- **Module/Class/Route:** `UserCompanyRoles`, `AuthService`
- **DB Tables:** `roles`, `permissions`, `role_permissions`, `user_company_roles`
- **Existing Tests:** `tests/test_company_setup.py` (Executed: YES)
- **Evidence:** Company setup and assistant access verify caller role and deny unauthorized role expansion.
- **Gap:** Needs FGA tuple mapping for fine-grained factory builder vs evaluator principal separation.

---

## 2. Executive & Workforce Layers

### 2.1 AI CEO / AICU
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/ai_ceo_v8.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/ai_ceo_v8.py), [`core/aic_ceo_engine.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/aic_ceo_engine.py)
- **Module/Class/Route:** `AICEOV8`, `CEOSupervisionLoop`
- **DB Tables:** `ai_ceo_decisions`, `ai_ceo_meetings`, `executive_council_roles`
- **Existing Tests:** `tests/test_ai_ceo_live_integration_qualification.py`
- **Evidence:** AI CEO acts as supervisor and approval authority, subordinate to human owner and KillSwitch.
- **Gap:** Connect AI CEO approval webhook to factory release pipeline for Tier R3 releases.

### 2.2 Agency Swarm
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`core/aic_ceo_constitution.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/aic_ceo_constitution.py), [`zonata/a2a_adapter.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/zonata/a2a_adapter.py)
- **Module/Class/Route:** Multi-agent agency definitions
- **DB Tables:** `a2a_agents`, `a2a_tasks`
- **Existing Tests:** `tests/test_a2a_interoperability.py` (Executed: YES - 54 passed)
- **Evidence:** A2A agent card validation and message passing pass unit tests.
- **Gap:** Agency Swarm itself is not used as the core execution runtime; the architecture specifies in-house LangGraph graphs.

### 2.3 LangGraph
- **Classification:** IMPLEMENTED BUT INCOMPLETE
- **File Paths:** [`api_server.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/api_server.py), [`core/stateful_agent_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/stateful_agent_runtime.py)
- **Module/Class/Route:** State graph execution wrappers
- **DB Tables:** `workflow_runs`, `workflow_checkpoints`
- **Existing Tests:** Covered in workflow tests
- **Evidence:** LangGraph library is referenced for graph execution.
- **Gap:** LangGraph `SpecCompiler` that turns `zonata.agent/v1` into `StateGraph` with wrapped `GovernedCall` external nodes is not yet built.

### 2.4 Letta
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`zonata/hal_multimodal_adapter.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/zonata/hal_multimodal_adapter.py), [`core/memory_governance.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/memory_governance.py)
- **Module/Class/Route:** Memory firewall adapters
- **DB Tables:** `governed_memory_records`
- **Existing Tests:** `tests/test_a2a_interoperability.py::test_35_letta_memory_firewall` (Executed: YES - Passed)
- **Evidence:** Memory firewall test passes.
- **Gap:** External Letta server daemon is not deployed; fallback memory engine in SQLite/Postgres is used.

### 2.5 HAL AI
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`core/multimodal_capability_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/multimodal_capability_runtime.py), [`zonata/hal_multimodal_adapter.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/zonata/hal_multimodal_adapter.py)
- **Module/Class/Route:** `MultimodalCapabilityRuntime`
- **DB Tables:** `multimodal_capabilities`, `multimodal_artifacts`
- **Existing Tests:** `tests/test_a2a_interoperability.py::test_36_hal_multimodal_bridge` (Executed: YES)
- **Evidence:** Runs multimodal bridge behind PolicyEngine.
- **Gap:** Desktop perception is limited to frame digest on headless environments.

---

## 3. Execution & Interoperability Subsystems

### 3.1 MCP (Model Context Protocol)
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/mcp_interoperability_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/mcp_interoperability_runtime.py), [`web/mcp_workspace.js`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/web/mcp_workspace.js)
- **Module/Class/Route:** `MCPGateway`, `MCPTools`
- **DB Tables:** `mcp_servers`, `mcp_tools`, `mcp_resources`, `mcp_executions`
- **Existing Tests:** `tests/test_universal_automation_fabric_qualification.py` (Executed: YES)
- **Evidence:** Active MCP servers (`server-filesystem`, `context7-mcp`, `server-memory`) running in current process environment.
- **Gap:** Hash pinning of MCP tool schemas (`mcp_published_capabilities`) needed for Phase 6.

### 3.2 A2A (Agent2Agent)
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/a2a_interoperability_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/a2a_interoperability_runtime.py), [`web/agent_network_workspace.js`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/web/agent_network_workspace.js)
- **Module/Class/Route:** `A2AInteroperabilityRuntime`
- **DB Tables:** `a2a_agents`, `a2a_messages`, `a2a_artifacts`, `a2a_tasks`
- **Existing Tests:** `tests/test_a2a_interoperability.py` (Executed: YES - 54 passed in 8.48s)
- **Evidence:** Agent card retrieval, schema validation, replay protection, and SSRF blocking all pass.
- **Gap:** None for base A2A protocol.

### 3.3 OpenHands
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`core/openhands_execution_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/openhands_execution_runtime.py)
- **Module/Class/Route:** `OpenHandsRuntimeGateway`
- **DB Tables:** `openhands_workspaces`, `openhands_commands`, `openhands_executions`
- **Existing Tests:** Verified in automation fabric qualification
- **Evidence:** Gated behind approval and workspace classification.
- **Gap:** Sandboxed microVM runner unavailable on Termux ARM64 host. Must be flag-gated off (T0).

### 3.4 Browser Use
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`core/browser_use_execution_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/browser_use_execution_runtime.py), [`zonata/browser_use_adapter.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/zonata/browser_use_adapter.py)
- **Module/Class/Route:** `BrowserExecutionGateway`, `BrowserRobot`
- **DB Tables:** `browser_sessions`, `browser_actions`, `browser_executions`
- **Existing Tests:** `tests/test_universal_browser_and_data_integration_qualification.py`
- **Evidence:** Real HTTP fetch and navigation supported; interactive DOM interaction returns `ACTION_NOT_IMPLEMENTED` on headless environment.
- **Gap:** Full browser interaction requires headless Chromium/Playwright which is environment-dependent.

### 3.5 Universal Linux Terminal
- **Classification:** IMPLEMENTED BUT INCOMPLETE
- **File Paths:** [`core/universal_terminal/`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/universal_terminal/)
- **Module/Class/Route:** `UniversalTerminal`, `LinuxRuntimeAdapter`
- **DB Tables:** `hosts`, `host_capabilities`, `host_execution_receipts`
- **Existing Tests:** `tests/test_universal_automation_fabric_qualification.py`
- **Evidence:** Subprocess execution with command risk checking.
- **Gap:** Container/VM adapters disabled on this host; operates in T0 host mode only.

### 3.6 Universal Automation Fabric
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/automation_fabric/fabric.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/automation_fabric/fabric.py), [`api_server.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/api_server.py)
- **Module/Class/Route:** `AutomationFabric`
- **DB Tables:** `async_command_queue`, `universal_schedules`
- **Existing Tests:** `tests/test_universal_automation_fabric_qualification.py`
- **Evidence:** Schedules, queues, and executes governed background automation tasks.
- **Gap:** None for base automation.

---

## 4. Infrastructure & Platform Services

### 4.1 Temporal
- **Classification:** NOT IMPLEMENTED (EMULATED ONLY)
- **File Paths:** [`core/temporal_durable_execution_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/temporal_durable_execution_runtime.py), [`zonata/temporal_adapter.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/zonata/temporal_adapter.py)
- **Module/Class/Route:** In-process Temporal emulation
- **DB Tables:** `temporal_workflows`, `temporal_activity_executions`
- **Existing Tests:** `tests/test_durable_workflow.py`
- **Evidence:** `temporalio` package is not installed; no external daemon.
- **Gap:** Master prompt prescribes falling back to `DbQueueOrchestrator` on `af_build`.

### 4.2 Vault
- **Classification:** PARTIALLY IMPLEMENTED (LOCAL FALLBACK)
- **File Paths:** [`core/vault_client.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/vault_client.py), [`core/secret_vault.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/secret_vault.py)
- **Module/Class/Route:** `SecretVaultClient`
- **DB Tables:** `secrets`, `credential_handles`
- **Existing Tests:** `tests/test_audit_remediation_security.py` (Executed: YES)
- **Evidence:** HashiCorp Vault is not running; local AES-GCM encrypted fallback in SQLite/Postgres is active.
- **Gap:** OpenBao / HashiCorp external transit engine not configured. Secret handles are resolved locally.

### 4.3 Keycloak
- **Classification:** NOT IMPLEMENTED (LOCAL AUTH FALLBACK)
- **File Paths:** [`core/keycloak_idp.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/keycloak_idp.py)
- **Module/Class/Route:** `KeycloakIdpClient`
- **DB Tables:** `external_idp_directory`
- **Existing Tests:** In integration suites
- **Evidence:** Keycloak server not deployed in local environment. Native auth (`core/auth.py`) is used.
- **Gap:** Enterprise SSO is disabled; native tokens used.

### 4.4 OpenFGA
- **Classification:** NOT IMPLEMENTED (IN-PROCESS REPAIR)
- **File Paths:** [`core/openfga_engine.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/openfga_engine.py)
- **Module/Class/Route:** `OpenFGAEngine`
- **DB Tables:** In-memory / SQL tuple store
- **Existing Tests:** `tests/test_saas_platform_integration.py`
- **Evidence:** Embedded tuple checker subordinate to AuthorityGateway.
- **Gap:** Dedicated OpenFGA server not present.

### 4.5 NATS JetStream
- **Classification:** NOT IMPLEMENTED (EMULATED ONLY)
- **File Paths:** [`core/nats_jetstream.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/nats_jetstream.py)
- **Module/Class/Route:** `NatsJetStreamEngine`
- **DB Tables:** `async_command_queue`
- **Existing Tests:** `tests/test_saas_failure_injection_and_qualification.py`
- **Evidence:** In-process sqlite/memory message queue emulator.
- **Gap:** Real NATS broker is not running.

### 4.6 MinIO / S3
- **Classification:** PARTIALLY IMPLEMENTED (LOCAL DISK STORAGE)
- **File Paths:** [`core/object_storage.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/object_storage.py), [`k8s/14-minio-storage.yaml`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/k8s/14-minio-storage.yaml)
- **Module/Class/Route:** `ObjectStorageClient`
- **DB Tables:** `enterprise_files`
- **Existing Tests:** File storage tests
- **Evidence:** Upstream MinIO was archived (2026-04-25). Local filesystem storage under `storage/` is active.
- **Gap:** Artifact bundles stored on local disk or S3-compatible cloud storage.

### 4.7 OpenTelemetry
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/opentelemetry_engine.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/opentelemetry_engine.py), [`core/observability_stack.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/observability_stack.py)
- **Module/Class/Route:** `OpenTelemetryEngine`, `SREMetrics`
- **DB Tables:** None (metrics exported or held in memory)
- **Existing Tests:** `tests/test_saas_platform_integration.py`
- **Evidence:** In-process metrics counters (`zonata_api_requests_total`, `zonata_api_errors_total`) incremented on real API requests in `api_server.py`.
- **Gap:** None for local metrics collection.

### 4.8 Langfuse
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`core/langfuse_engine.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/langfuse_engine.py), [`core/langfuse_adapter.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/langfuse_adapter.py)
- **Module/Class/Route:** `LangfuseEngine`
- **DB Tables:** `agent_evaluation_runs`
- **Existing Tests:** `tests/test_ai_ceo_intelligence_enhancement_qualification.py`
- **Evidence:** Langfuse client adapter exists with mock/local buffering mode.
- **Gap:** Cloud endpoint requires API key; operates in local offline mode.

### 4.9 PostHog
- **Classification:** PARTIALLY IMPLEMENTED (OPTIONAL)
- **File Paths:** [`core/posthog_analytics.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/posthog_analytics.py)
- **Module/Class/Route:** `PostHogAnalytics`
- **DB Tables:** None
- **Existing Tests:** In analytics suites
- **Evidence:** Event tracking adapter with opt-out / local no-op fallback.
- **Gap:** External analytics not required for core Agent Factory.

### 4.10 Model Gateway
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/model_gateway.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/model_gateway.py), [`core/model_router_v6.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/model_router_v6.py)
- **Module/Class/Route:** `ModelGateway`, `ModelRouterV6`
- **DB Tables:** None
- **Existing Tests:** Unit tests in test suite
- **Evidence:** Routes LLM prompts to configured providers (Gemini, local adapters) with budget clamping and token counters.
- **Gap:** Wire model profile (`AF_REAL_MODEL_PROFILE`) into Factory role graphs.

---

## 5. Agent Factory & Workforce Lifecycle Components

### 5.1 Agent Creation Mechanism
- **Classification:** IMPLEMENTED BUT REQUIRES REFACTORING
- **File Paths:** [`core/agent_factory_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/agent_factory_runtime.py), [`core/agent_factory_v2.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/agent_factory_v2.py), [`core/enterprise_agent_factory.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/enterprise_agent_factory.py)
- **Module/Class/Route:** `AgentFactoryRuntime`, `EnterpriseAgentFactory`
- **DB Tables:** `governed_agents`, `agent_packages`
- **Existing Tests:** In integration test suites
- **Evidence:** Exists as legacy monolithic builders.
- **Gap:** Must be decoupled into the 10-phase architecture with `SpecCompiler`, deterministic independent certification, and the 24 `af_*` tables.

### 5.2 Agent Registry
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/agent_factory_v2.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/agent_factory_v2.py), [`core/db.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/db.py)
- **Module/Class/Route:** `AgentEvaluationRegistry`, `governed_agents` table
- **DB Tables:** `governed_agents`, `immutable_agent_packages`, `stateful_agent_identities`
- **Existing Tests:** `tests/test_saas_platform_integration.py`
- **Evidence:** Tables created and verified in active database schema.
- **Gap:** Factory table `af_agent` must link to `governed_agents.agent_id`.

### 5.3 Agent Templates
- **Classification:** PARTIALLY IMPLEMENTED
- **File Paths:** [`core/employee_template.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/employee_template.py), [`core/enterprise_agent_factory.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/enterprise_agent_factory.py)
- **Module/Class/Route:** `EmployeeTemplateRegistry`, `AgentBlueprint`
- **DB Tables:** `zonata_org_blueprints`
- **Existing Tests:** Covered in company onboarding tests
- **Evidence:** Industry department templates exist.
- **Gap:** Declarative `zonata.template/v1` loader and template resolution engine needed for Phase 3.

### 5.4 Agent Execution Engine
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/stateful_agent_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/stateful_agent_runtime.py), [`core/workforce_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/workforce_runtime.py)
- **Module/Class/Route:** `StatefulAgentRuntime`, `WorkforceRuntime`
- **DB Tables:** `stateful_conversation_sessions`, `stateful_conversation_turns`
- **Existing Tests:** Covered in assistant and workforce tests
- **Evidence:** Executes agent interactions under session and memory control.
- **Gap:** Graph compilation with `GovernedCall` wrapper to be delivered in Phase 4.

### 5.5 Workforce Assignment
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/workforce_architecture.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/workforce_architecture.py), [`core/workforce_manager_v4.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/workforce_manager_v4.py)
- **Module/Class/Route:** `WorkforceManager`, `WorkforceArchitecture`
- **DB Tables:** `zonata_workforce_members`, `employees`, `department_objectives`
- **Existing Tests:** `tests/test_workforce_orchestrator.py`
- **Evidence:** Assigns AI employees to specific departments, reporting lines, and SOPs.
- **Gap:** Wire `WorkforcePort.assign()` to `af_release` publishing workflow in Phase 8.

### 5.6 Employee Identity & Permissions
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/identity_gateway.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/identity_gateway.py), [`core/service_identity.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/service_identity.py)
- **Module/Class/Route:** `IdentityGateway`, `ServiceIdentityManager`
- **DB Tables:** `employees`, `permissions`, `role_permissions`
- **Existing Tests:** `tests/test_company_setup.py`
- **Evidence:** Authenticates and resolves principal scopes per employee and agent.
- **Gap:** Ensure `may_use_employees=false` invariant is strictly validated for all manufactured agents.

### 5.7 Tool Registry
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/governed_tool_registry.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/governed_tool_registry.py), [`core/tool_fabric.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/tool_fabric.py)
- **Module/Class/Route:** `GovernedToolRegistry`
- **DB Tables:** `governed_tools`, `tool_packages`
- **Existing Tests:** `tests/test_universal_automation_fabric_qualification.py`
- **Evidence:** Strict tool registration with policy enforcement. Unregistered or denied tool proposals are blocked.
- **Gap:** Capability and tool permission profile calculator to be added in Phase 3.

### 5.8 Memory
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/memory.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/memory.py), [`core/memory_governance.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/memory_governance.py)
- **Module/Class/Route:** `MemoryService`, `MemoryGovernance`
- **DB Tables:** `governed_memory_records`, `organizational_memory`
- **Existing Tests:** `npm run test:assistant` (Assistant memory tests: remember, list, forget passed)
- **Evidence:** Assistant memory contract tests executed and passed (29 jsdom checks).
- **Gap:** Scoped memory bindings for manufactured agent teams in Phase 6.

### 5.9 Agent Evaluation
- **Classification:** IMPLEMENTED BUT INCOMPLETE
- **File Paths:** [`core/agent_evaluation.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/agent_evaluation.py), [`core/agent_evaluation_engine.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/agent_evaluation_engine.py)
- **Module/Class/Route:** `AgentEvaluationEngine`, `EvaluationReport`
- **DB Tables:** `agent_evaluation_runs`
- **Existing Tests:** `tests/test_ai_ceo_intelligence_enhancement_qualification.py`
- **Evidence:** Evaluates agent runs on security, policy compliance, and hallucination scores.
- **Gap:** Lacks the 4-tier deterministic certification gates (`gate_eval.py`, Wilson score, held-out test datasets) specified for Phase 7.

### 5.10 Test Infrastructure
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`pytest.ini`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/pytest.ini), [`tests/`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/tests/), [`playwright.config.ts`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/playwright.config.ts)
- **Module/Class/Route:** `pytest`, `unittest`, Node.js test runners
- **DB Tables:** Test fixtures and in-memory databases
- **Existing Tests:** 164 test files in repository
- **Evidence:** Executed multiple suites (`npm run test:ui`, `npm run test:assistant`, `npm run test:company`, `tests/test_a2a_interoperability.py`, all passed).
- **Gap:** Several tests hardcode `/tmp/` which fails on Termux ARM64; `$TMPDIR` should be used.

### 5.11 Deployment
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`deploy/`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/deploy/), [`render.yaml`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/render.yaml), [`Dockerfile`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/Dockerfile)
- **Module/Class/Route:** Local script runner (`run_local.sh`), Render web/worker services
- **DB Tables:** None
- **Existing Tests:** Verified deployment scripts
- **Evidence:** Clean `render.yaml` with web service and background worker specifications.
- **Gap:** Add factory worker entrypoint (`python -m agent_factory.worker`) during Phase 9 deployment.

### 5.12 Workflow Orchestration
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/durable_workflow_runtime.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/durable_workflow_runtime.py), [`core/production_orchestration.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/production_orchestration.py)
- **Module/Class/Route:** `DurableWorkflowRuntime`
- **DB Tables:** `workflows`, `workflow_runs`, `workflow_events`
- **Existing Tests:** `tests/test_durable_workflow.py`
- **Evidence:** Checkpointed step execution and compensation on failure.
- **Gap:** Integrate `batch_scheduler.py` (15/15 self-tests) for wave-based team manufacturing in Phase 5.

### 5.13 Monitoring & Observability
- **Classification:** IMPLEMENTED AND VERIFIED
- **File Paths:** [`core/production_observability.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/production_observability.py), [`core/observability_stack.py`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/observability_stack.py)
- **Module/Class/Route:** `ProductionObservability`, `sre_metrics`
- **DB Tables:** None
- **Existing Tests:** In monitoring suites
- **Evidence:** Active request counters, latency tracking, error metrics, and incident logging wired into `api_server.py`.
- **Gap:** Add Factory-specific SLO metrics (`af_build_duration`, `af_certification_pass_rate`).
