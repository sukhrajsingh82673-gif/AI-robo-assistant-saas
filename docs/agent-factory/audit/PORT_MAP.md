# PORT_MAP — ZONATA Agent Factory Phase 1 Audit

This document maps each port required by the ZONATA Agent Factory Target Architecture to existing production classes and functions in the repository, or defines the minimal adapter required.

---

## 1. Port Mapping Summary

| Port Name | Target Role | Existing Class / Function | File & Line | Status / Minimal Adapter Required |
|---|---|---|---|---|
| **`CompanyKernelPort`** | Read company hierarchy, positions, reporting lines, departments | `core.db.db` / `core.departments` | [`core/departments.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/departments.py#L1) | **Available**: Wrap SQL queries against `companies`, `departments`, `organization_nodes`. |
| **`PolicyPort`** | Evaluate agent policies and risk profile limits | `PolicyEngineV2` / `ZonataActionGateway._step_10_evaluate_policy` | [`core/action_gateway.py:179`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/action_gateway.py#L179), [`core/policy_engine_v2.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/policy_engine_v2.py#L1) | **Available**: Adapter maps factory risk tier & permissions to PolicyEngine rules. |
| **`AuthorityPort`** | Provide `authorize(principal, action, resource, meta)` | `ZonataActionGateway` | [`core/action_gateway.py:36`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/action_gateway.py#L36) | **Adapter Needed**: Wrap `ZonataActionGateway.execute_action` or provide a lightweight `authorize()` delegating to `ActionEnvelope`. |
| **`ApprovalPort`** | Submit human/owner approval requests, query decision | `ApprovalEngine` / `approval_service` | [`core/approvals.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/approvals.py#L1), [`core/cryptographic_approvals.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/cryptographic_approvals.py#L1) | **Available**: Insert pending approval into `approvals` table with cryptographic nonce verification. |
| **`EvidenceLedgerPort`** | Append cryptographic evidence events & verify chain | `EvidenceLedger` | [`core/evidence_ledger.py:27`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/evidence_ledger.py#L27) | **Available & Verified**: Calls `EvidenceLedger.seal_evidence()` with SHA-256 Merkle root. |
| **`KillSwitchPort`** | Query and assert kill switch status for agent/team/tenant | `KillSwitchMatrix` & `coordination` | [`core/killswitch_matrix.py:30`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/killswitch_matrix.py#L30), [`core/distributed_coordination.py:216`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/distributed_coordination.py#L216) | **Available & Verified**: Calls `KillSwitchMatrix.is_activated()` and `coordination.is_killed()`. |
| **`WorkforcePort`** | Provision/assign manufactured agents to departments/SOPs | `WorkforceArchitecture` / `WorkforceManager` | [`core/workforce_architecture.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/workforce_architecture.py#L1), [`core/workforce_manager_v4.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/workforce_manager_v4.py#L1) | **Available**: Assigns certified agent to `zonata_workforce_members` and employees table. |
| **`RuntimePort`** | Deploy compiled LangGraph agents to active execution runtime | `StatefulAgentRuntime` / `WorkforceRuntime` | [`core/stateful_agent_runtime.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/stateful_agent_runtime.py#L1), [`core/workforce_runtime.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/workforce_runtime.py#L1) | **Available**: Mounts compiled `StateGraph` in agent execution pool. |
| **`SecretsPort`** | Secret referencing, signature verification keys | `SecretVault` / `secret_manager` | [`core/secret_vault.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/secret_vault.py#L1), [`core/secret_manager.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/secret_manager.py#L1) | **Available**: Reference-only secret resolution via handle without exposing raw keys. |
| **`OrchestratorPort`** | Background queue and stage state machine | `DbQueueOrchestrator` (fallback) | New in `agent_factory/control/` | **Adapter Required**: Table-backed job queue on `af_build` with `SELECT ... FOR UPDATE SKIP LOCKED` (or sqlite transaction lock). |
| **`SandboxPort`** | Isolated code execution / tool package validation | `LinuxRuntimeAdapter` | [`core/universal_terminal/runtime_adapters.py:66`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/universal_terminal/runtime_adapters.py#L66) | **Constrained**: T0 host adapter only. Returns `AF-SANDBOX-UNAVAILABLE` for T1/T2 requirements. |
| **`IdentityPort`** | Mint short-lived agent principal tokens | `IdentityGateway` / `AuthService` | [`core/identity_gateway.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/identity_gateway.py#L1), [`core/auth.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/auth.py#L1) | **Available**: Mints signed short-lived JWT / capability token for agent principal. |
| **`DlpPort`** | Data loss prevention scan for input/output | `ModelDataFirewall` / `AiDlpGateway` | [`core/model_data_firewall.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/model_data_firewall.py#L1), [`core/ai_dlp_gateway.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/ai_dlp_gateway.py#L1) | **Available & Verified**: Scans prompt arguments and tool outputs for PII/tokens. |
| **`TelemetryPort`** | Metric recording and trace spans | `SREMetrics` / `OpenTelemetryEngine` | [`core/observability_stack.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/observability_stack.py#L1), [`core/opentelemetry_engine.py:1`](file:///data/data/com.termux/files/home/AI-robo-assistant-saas/core/opentelemetry_engine.py#L1) | **Available**: Ingests spans, counters, and stage latencies. |

---

## 2. Authentication, Tenancy & Connection Pooling Conventions

1. **Service Principal Authentication:**
   - Internal service calls from the Agent Factory use internal principal format: `factory.<role_name>` (e.g. `factory.requirement_analyst`, `factory.director`).
   - Principal identity is authenticated against `IdentityGateway` without bypassing tenant boundaries.

2. **Per-Transaction Tenant Context:**
   - On PostgreSQL: Each transaction must execute `SET LOCAL zonata.tenant_id = :id;` (or `SELECT set_config('zonata.tenant_id', :id, true)`) within the connection block.
   - On SQLite: In-memory/file connections resolve `tenant_id` from `TenantRuntime` and append explicit parameterized `WHERE tenant_id = ?` clauses.

3. **Connection Pooling Rule:**
   - Transaction-mode poolers (e.g. Neon, PgBouncer) reset session state between transactions. Therefore, session-level `SET zonata.tenant_id` is prohibited; only transaction-local scoping (`SET LOCAL`) is permitted.
