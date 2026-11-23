# Antigravity Step 4 Master Execution Report — Durable Execution, LangGraph + Google ADK Runtimes, MCP, Observability, 24/7 Hardening

**Repo:** `sukhrajsingh82673-gif/AI-robo-assistant-saas`  
**Branch:** `step4-durable-frameworks`  
**Author:** Antigravity (Builder) with OpenCode (Reviewer)  
**Tracking Period:** Sub-Steps 4A through 4J  
**Status:** In Progress (Sub-Step 4A Complete)

---

## Sub-Step 4A: Preflight, Inventory and Architectural Decision Records (ADRs)

### 1. Overview & Objectives
Sub-Step 4A validates all prerequisites for durable execution, multi-agent frameworks, governed MCP tool execution, and OpenTelemetry observability:
- **Foundation Gate Check:** Verifies that all foundational systems from Step 1, Step 2, and Step 3 are present, operational, and non-simulated.
- **Inventory Audit:** Comprehensive catalog of 10 target domains documented in `docs/reports/STEP4_INVENTORY.md`.
- **Architectural Decision Records:** 9 formal ADRs (`ADR 0009` through `ADR 0017`) committed in `docs/architecture/` and mirrored in `docs/adr/`.

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 12 items

tests/test_step4_preflight.py::TestStep4Preflight::test_01_workflow_engine_port_exists PASSED [  8%]
tests/test_step4_preflight.py::TestStep4Preflight::test_02_agent_runtime_and_tool_registry_exist PASSED [ 16%]
tests/test_step4_preflight.py::TestStep4Preflight::test_03_action_gateway_governance_exists PASSED [ 25%]
tests/test_step4_preflight.py::TestStep4Preflight::test_04_llm_gateway_exists PASSED [ 33%]
tests/test_step4_preflight.py::TestStep4Preflight::test_05_job_runner_and_scheduler_exist PASSED [ 41%]
tests/test_step4_preflight.py::TestStep4Preflight::test_06_evidence_ledger_exists PASSED [ 50%]
tests/test_step4_preflight.py::TestStep4Preflight::test_07_capability_truth_table_exists PASSED [ 58%]
tests/test_step4_preflight.py::TestStep4Preflight::test_08_key_and_credential_ports_exist PASSED [ 66%]
tests/test_step4_preflight.py::TestStep4Preflight::test_09_step3_hands_exist_as_tools_or_ports PASSED [ 75%]
tests/test_step4_preflight.py::TestStep4Preflight::test_10_inventory_file_covers_all_ten_domains PASSED [ 83%]
tests/test_step4_preflight.py::TestStep4Preflight::test_11_all_nine_step4_adrs_exist PASSED [ 91%]
tests/test_step4_preflight.py::TestStep4Preflight::test_12_mutation_check_missing_dependency_fails PASSED [100%]

============================== 12 passed in 0.76s ==============================
```

### 3. Decisions & Invariants Enforced
- **Decision D4-1:** Clear runtime division of labor:
  - **Temporal:** Multi-day/month durable business processes (onboarding, collections, month-end close).
  - **LangGraph:** Short-cycle iterative agents (planning loops, critic cycles, researcher/writer).
  - **Google ADK:** Hierarchical agent teams (Agent Factory squads, supervisor-worker topologies).
- **Rule 33 (Replaceable Adapters):** Frameworks hold execution state only; authority and truth remain in ZONATA tables and ActionGateway.
- **Rule 34 (Port Routing):** Frameworks must route through `LLMGateway` and `ActionGateway`.
- **Rule 35 (At-least-once execution):** Idempotency keys enforced on all state-altering executions.
- **Rule 36 (Payload encryption):** Plaintext payloads never logged or stored in workflow histories.
- **Rule 40 (Legal boundaries):** AGPL observability backends (Grafana, Loki, Tempo) isolated strictly across network boundaries with zero in-process library linking.

### 4. Status
Sub-Step 4A verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45137351358](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45137351358) (100% GREEN)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (1m59s)
  - SQLite Dev Profile Test Suite: PASS (2m2s)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (2m38s)
- **Commit:** `16ce16d`

---

## Sub-Step 4B: Runtime Ports, Spec Compilers & Anti-Bypass Guards

### 1. Overview & Objectives
Sub-Step 4B implements the port architecture and compilation pipeline that isolates declarative agent specifications (`zonata.agent/v1`) from underlying runtime execution engines:
- **`AgentRuntimePort` (`core/ports/agent_runtime.py`):** Standard typed port defining `execute_agent`, `stream_agent`, `cancel_agent`, and `get_runtime_status`. Includes `LocalAgentRuntimeAdapter` (sovereign execution), `LangGraphRuntimeAdapter`, `TemporalRuntimeAdapter`, and `GoogleADKRuntimeAdapter` (fail-closed stubs returning `NOT_CONFIGURED` when unconfigured).
- **`AgentSpecCompiler` (`core/agent_spec/compiler.py`):** Translates specifications into `LOCAL`, `LANGGRAPH`, `TEMPORAL`, and `GOOGLE_ADK` execution descriptors, calculating a cryptographic compilation digest.
- **Anti-Bypass AST Linter (`scripts/anti_bypass_linter.py` & `core/security/anti_bypass.py`):** Static analyzer enforcing Standing Rule 34 (disallows direct model SDK imports, unwrapped subprocesses, and raw network calls in framework runtimes).

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 15 items

tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_01_agent_runtime_port_registered PASSED [  6%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_02_local_agent_runtime_executes_successfully PASSED [ 13%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_03_local_agent_runtime_streams_chunks PASSED [ 20%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_04_local_agent_runtime_idempotency_cache PASSED [ 26%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_05_langgraph_adapter_fail_closed_and_sandbox PASSED [ 33%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_06_temporal_adapter_fail_closed_and_sandbox PASSED [ 40%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_07_google_adk_adapter_fail_closed_and_sandbox PASSED [ 46%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_08_compile_to_local_target PASSED [ 53%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_09_compile_to_langgraph_target PASSED [ 60%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_10_compile_to_temporal_target PASSED [ 66%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_11_compile_to_google_adk_target PASSED [ 73%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_12_compiler_rejects_credential_leak PASSED [ 80%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_13_anti_bypass_linter_passes_current_repo PASSED [ 86%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_14_anti_bypass_linter_mutation_catches_direct_model_import PASSED [ 93%]
tests/test_step4_runtime_ports.py::TestStep4RuntimePorts::test_15_anti_bypass_linter_mutation_catches_direct_network_call PASSED [100%]

============================== 15 passed in 9.64s ==============================
```

### 3. Decisions & Invariants Enforced
- **Rule 33 (Replaceable Adapters):** Execution state held only in adapter session wrappers; business authority and evidence logged in ZONATA core tables.
- **Rule 34 (Port Isolation & Anti-Bypass):** Direct model imports, unwrapped subprocesses, and raw network calls strictly forbidden in agent runtimes and enforced via AST linter.
- **Rule 35 (At-least-once Execution):** Deterministic idempotency keys validated and propagated across all runtime adapters.
- **Rule 38 (Versioned Workflows):** `zonata.agent/v1` compilation produces deterministic SHA-256 digests.

### 4. Status
Sub-Step 4B verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45153307058](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45153307058) (100% GREEN)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (1m51s)
  - SQLite Dev Profile Test Suite: PASS (1m43s)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (2m44s)
- **Commit:** `05bfe5a`

---

## Sub-Step 4C: LangGraph Runtime Adapter & Encrypted PostgreSQL Checkpointer

### 1. Overview & Objectives
Sub-Step 4C delivers the sovereign LangGraph-style cyclic execution runtime with encrypted persistence:
- **`PostgresCheckpointer` (`core/langgraph/checkpointer.py`):**
  - Manages `langgraph_checkpoints` and `langgraph_checkpoint_writes` tables with multi-tenant row-level security (`tenant_id`, `company_id`).
  - Implements **Rule 36 (Payload Encryption at Rest)**: state payloads are encrypted via `KeyManagementPort` envelope encryption (`kms.encrypt(...)`), storing base64 ciphertext in the database. Plaintext state never touches database rows.
  - Fail-closed security: if KMS encryption is unconfigured or unavailable, checkpointing raises `RuntimeError` rather than writing unencrypted state.
- **Cyclic Agent Loop (`core/langgraph/adapter.py`):**
  - Executes bounded iterative cycles: **Planner Node** $\rightarrow$ **Tool Executor Node** $\rightarrow$ **Critic Evaluator Node** $\rightarrow$ **Router**.
  - Limits iterations to $\le 5$ (bounded graph execution).
  - Enforces **Rule 34**: 100% of LLM calls route through `LLMGatewayPort`; 100% of tools route through `ActionGateway` and `ToolRegistry`.
  - Enforces **Rule 35**: Deterministic idempotency keys (`{run_id}_{step_id}_{tool_name}`) prevent duplicate execution across replays. Resuming a completed run loads from the encrypted checkpoint cache without redundant execution.
  - Untrusted data tagging: tool outputs are marked untrusted in `AgentState`.
- **Database Migrations:**
  - `migrations/common/0032_langgraph_checkpoints.sql`
  - `migrations/pg/0032_langgraph_checkpoints.sql`

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 7 items

tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_01_checkpointer_tables_created PASSED [ 14%]
tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_02_checkpointer_put_and_get PASSED [ 28%]
tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_03_encryption_at_rest_rule_36 PASSED [ 42%]
tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_04_cyclic_execution_loop PASSED [ 57%]
tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_05_resumption_from_checkpoint_rule_35 PASSED [ 71%]
tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_06_streaming_chunks PASSED [ 85%]
tests/test_step4_langgraph_runtime.py::TestStep4LangGraphRuntime::test_07_mutation_check_unconfigured_kms_fails_closed PASSED [100%]

============================== 7 passed in 0.98s ===============================
```

### 3. Decisions & Invariants Enforced
- **Rule 33 (Replaceable Adapters):** LangGraph execution state lives strictly in the checkpointer; authority, ledger, and business truth remain in ZONATA tables.
- **Rule 34 (Port Routing):** Every model prompt routes via `llm_gateway.generate()` and every tool call routes through `action_gateway.evaluate_decision_gate()` followed by `tool_registry.execute()`.
- **Rule 35 (At-least-once Execution & Idempotency):** Checkpoint resumption checks for completed thread state; identical run IDs return cached checkpoint results without repeating external actions.
- **Rule 36 (Payload Encryption at Rest):** Direct database inspection confirms `checkpoint_blob` is base64-encoded ciphertext produced by KMS envelope encryption; zero plaintext leakage.
- **Rule 37 (Adoption Honesty):** `docs/reports/ADOPTION_STATUS.md` updated with LangGraph / PostgresCheckpointer marked `ADOPTED`.

### 4. Status
Sub-Step 4C verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45158634030](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45158634030) (100% GREEN)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (1m54s)
  - SQLite Dev Profile Test Suite: PASS (2m9s)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (2m49s)
- **Commit:** `e8943c7`

---

## Sub-Step 4D: Temporal Durable Execution Engine & Workers

### 1. Overview & Objectives
Sub-Step 4D delivers the enterprise durable execution engine for long-running workflows, scheduled multi-day business processes, and resilient distributed worker dispatch:
- **`TemporalActivities` (`core/temporal/activities.py`):**
  - Implements durable activities: `llm_generation_activity`, `tool_execution_activity`.
  - Enforces **Rule 34 (Port Routing)**: 100% of LLM calls route through `LLMGatewayPort`; 100% of tools route through `ActionGateway` and `ToolRegistry`.
  - Enforces **Rule 35 (At-least-once Execution & Idempotency)**: Replayed or retried activities with identical idempotency keys return cached output without repeating external side effects.
  - Fail-closed security: policy violations raise `NonRetryableActivityError`.
- **`ZonataAgentWorkflow` (`core/temporal/workflows.py`):**
  - Enforces **Rule 38 (Versioned Workflows)**: Carries explicit `workflow_version = "1.0.0"`.
  - Coordinates activities deterministically; generates per-step deterministic idempotency keys (`{workflow_id}_step{idx}_{action}`).
  - Respects kill switch: active kill switches halt workflow execution with `HALTED_BY_KILL_SWITCH`.
- **`TemporalRuntimeAdapter` (`core/temporal/adapter.py`):**
  - Bridges `AgentRuntimePort` to Temporal Durable Execution engine.
  - Probes live Temporal cluster or provides sovereign deterministic simulation under `ZONATA_TEST_MODE=1`.
  - Fails closed when unconfigured (Truth Rule 1).
- **`core/ports/agent_runtime.py`:**
  - Delegates `TemporalRuntimeAdapter` cleanly to `core.temporal.adapter.TemporalRuntimeAdapter`.
- **`docs/reports/ADOPTION_STATUS.md`:**
  - Updated Temporal Durable Execution to `ADOPTED`.

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 9 items

tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_01_probe_fail_closed_and_sandbox PASSED [ 11%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_02_workflow_execution_success PASSED [ 22%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_03_activity_dispatch_through_action_gateway PASSED [ 33%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_04_idempotent_activity_replay_rule_35 PASSED [ 44%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_05_workflow_versioning_rule_38 PASSED [ 55%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_06_kill_switch_halts_workflow PASSED [ 66%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_07_streaming_chunks PASSED [ 77%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_08_mutation_check_unauthorized_tool_rejected PASSED [ 88%]
tests/test_step4_temporal_runtime.py::TestStep4TemporalRuntime::test_09_mutation_check_unconfigured_runtime_fails_closed PASSED [100%]

============================== 9 passed in 1.08s ===============================
```

### 3. Decisions & Invariants Enforced
- **Rule 33 (Replaceable Adapters):** Temporal manages execution state only; business truth, approvals, and budget live in ZONATA tables.
- **Rule 34 (Port Isolation & Anti-Bypass):** Direct model imports or unrouted tool calls are strictly forbidden and verified by AST linter.
- **Rule 35 (At-least-once Execution & Idempotency):** Activities with identical idempotency keys return cached execution records without repeating side effects.
- **Rule 36 (Payload Reference Hygiene):** Payloads pass opaque IDs and references; never raw plaintext secrets.
- **Rule 37 (Adoption Honesty):** `docs/reports/ADOPTION_STATUS.md` tracks Temporal Durable Execution as `ADOPTED`.
- **Rule 38 (Versioned Workflows):** Workflows carry explicit version `"1.0.0"` in records and metadata.

### 4. Status
Sub-Step 4D verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45160750438](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45160750438) (100% GREEN)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (3m10s)
  - SQLite Dev Profile Test Suite: PASS (3m57s)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (3m13s)
- **Commit:** `9296fe5`

---

## Sub-Step 4E: Framework Split Qualification & Chaos Test

### 1. Overview & Objectives
Sub-Step 4E qualifies the runtime framework division of labor (Decision D4-1 / ADR 0009) and executes fault-injection chaos drills to prove crash resilience and idempotency invariants:
- **`FrameworkRouter` (`core/framework_router.py`):**
  - Enforces the constitutional division of labor across all 4 runtimes:
    - `TEMPORAL`: Long-running durable business processes (timeout > 3600s, `is_durable=True`, `workflow_type="durable"`).
    - `LANGGRAPH`: Short-cycle iterative agents (planning loops, critic cycles, `workflow_type="cyclic"`).
    - `GOOGLE_ADK`: Hierarchical multi-agent squads (`workflow_type="hierarchical"` or `requires_team=True`).
    - `LOCAL`: Standard in-process sequential utility agents.
  - Rejects mismatches and out-of-bound workloads (`RoutingValidationError` on unbounded loops >10, multi-day ephemeral routing, unknown runtimes).
- **Chaos Engineering & Fault Injection (`core/chaos/simulator.py`):**
  - **LangGraph Mid-Cycle Worker Crash:** Injects simulated process termination (`SimulatedWorkerCrash`), restarts a fresh adapter from checkpointer, and verifies seamless resumption from saved state without re-executing already-completed steps (Rule 35).
  - **Temporal Activity Crash & Replay:** Simulates worker termination after tool activity completion, replays with identical idempotency key, and verifies cached output return with `cached_replay=True` and zero duplicate side-effects.
- **Multi-Tenant RLS Isolation Under Chaos:**
  - Proves that checkpoint state created during fault injection remains strictly isolated by `tenant_id` and `company_id`.

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 9 items

tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_01_router_assigns_temporal_for_durable_or_long_running PASSED [ 11%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_02_router_assigns_langgraph_for_cyclic_loops PASSED [ 22%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_03_router_assigns_google_adk_for_hierarchical_teams PASSED [ 33%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_04_router_assigns_local_for_sequential_tasks PASSED [ 44%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_05_router_rejects_architectural_mismatches PASSED [ 55%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_06_langgraph_chaos_crash_and_recovery PASSED [ 66%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_07_temporal_chaos_activity_crash_and_replay PASSED [ 77%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_08_multi_tenant_isolation_under_chaos PASSED [ 88%]
tests/test_step4_framework_split_chaos.py::TestStep4FrameworkSplitChaos::test_09_mutation_check_unauthorized_bypass_attempt_fails PASSED [100%]

============================== 9 passed in 0.84s ===============================
```

### 3. Decisions & Invariants Enforced
- **Decision D4-1:** Runtimes are assigned strictly according to lifecycle requirements; invalid workloads fail closed.
- **Rule 33 (Replaceable Adapters):** Execution state held only in adapter session wrappers; business authority and evidence logged in ZONATA core tables.
- **Rule 35 (At-least-once Execution & Idempotency):** Injected crash drills prove that replays and resumptions never duplicate tool calls or ledger postings.
- **Multi-Tenant Isolation:** Crash recovery respects RLS bounds (`tenant_id`, `company_id`).

### 4. Status
Sub-Step 4E verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45164337104](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45164337104) (100% GREEN)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (1m47s)
  - SQLite Dev Profile Test Suite: PASS (2m5s)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (2m30s)
- **Commit:** `f0d4232`

---

## Sub-Step 4F: Google ADK Hierarchical Teams & Loops

### 1. Overview & Objectives
Sub-Step 4F delivers the sovereign Google ADK hierarchical team engine for multi-agent squads, supervisor-worker topologies, and bounded critic loops:
- **`HierarchicalTeamCoordinator` (`core/adk/coordinator.py`):**
  - Orchestrates multi-agent squads with specialized roles:
    - **Supervisor:** Analyzes goal, decomposes tasks, and directs workers.
    - **Worker:** Executes tasks and calls tools via `ZonataADKToolWrapper`.
    - **Critic:** Evaluates output against quality criteria; provides revision feedback or approves completion.
  - Constitutional Bounds:
    - **Max Tree Depth $\le 3$:** Prohibits runaway recursive sub-agent nesting attacks (`TeamTopologyError`).
    - **Max Feedback Loops $\le 5$:** Prohibits infinite supervisor-critic debate loops.
  - Generates deterministic per-action idempotency keys: `{team_run_id}_worker_{step_id}_{tool}`.
- **Port Isolation & Gateway Routing (`core/adk/model.py` & `core/adk/tool_wrapper.py`):**
  - **`ZonataADKModel`:** 100% of LLM calls route through `LLMGatewayPort` with token accounting and ModelTier enforcement (Rule 34).
  - **`ZonataADKToolWrapper`:** 100% of tools route through `ActionEnvelope` -> `ActionGateway` -> `ToolRegistry`. Replayed calls return cached results (Rule 35).
- **`ZonataADKSessionService` (`core/adk/session.py`):**
  - Manages multi-tenant conversation histories with RLS isolation.
  - Enforces Rule 36: session payloads are encrypted at rest with per-tenant KMS keys. Cross-tenant access attempts return `None`.
- **`GoogleADKRuntimeAdapter` (`core/adk/adapter.py`):**
  - Connects `AgentRuntimePort` to Google ADK team engine.
  - Probes live Google ADK or provides sovereign deterministic simulation in test mode.
  - Fails closed when unconfigured (Truth Rule 1).
- **`docs/reports/ADOPTION_STATUS.md`:**
  - Updated Google ADK to `ADOPTED`.

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 10 items

tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_01_probe_fail_closed_and_sandbox PASSED [ 10%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_02_hierarchical_team_execution_success PASSED [ 20%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_03_tool_execution_through_adk_wrapper PASSED [ 30%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_04_tree_depth_bound_enforced PASSED [ 40%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_05_critic_loop_bound_enforced PASSED [ 50%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_06_kill_switch_halts_team PASSED [ 60%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_07_multi_tenant_session_isolation PASSED [ 70%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_08_streaming_chunks PASSED [ 80%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_09_mutation_check_unregistered_tool_rejected PASSED [ 90%]
tests/test_step4_google_adk_runtime.py::TestStep4GoogleADKRuntime::test_10_mutation_check_unconfigured_runtime_fails_closed PASSED [100%]

============================== 10 passed in 2.23s ==============================
```

### 3. Decisions & Invariants Enforced
- **Rule 33 (Replaceable Adapters):** ADK manages in-flight team collaboration only; authority and truth live in ZONATA tables and ActionGateway.
- **Rule 34 (Port Routing):** Model generation routes through `ZonataADKModel`; tools route through `ZonataADKToolWrapper` -> `ActionGateway`.
- **Rule 35 (At-least-once Execution & Idempotency):** Deterministic per-agent idempotency keys prevent duplicate executions.
- **Rule 36 (Payload Confidentiality):** Session state is encrypted with KMS; zero plaintext sensitive data in database rows.
- **Rule 37 (Adoption Honesty):** `docs/reports/ADOPTION_STATUS.md` tracks Google ADK as `ADOPTED`.
- **Rule 38 (Versioned Topologies):** Team topologies carry explicit version `"1.0.0"`.
- **Constitutional Bounds:** Tree depth $\le 3$ and feedback loops $\le 5$ enforced.

### 4. Status
Sub-Step 4F verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45169236544](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45169236544) (100% GREEN)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (2m21s)
  - SQLite Dev Profile Test Suite: PASS (2m16s)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (2m30s)
- **Commit:** `943c102`

---

## Sub-Step 4G: Governed MCP Client & Sandboxed Server

### 1. Overview & Objectives
Sub-Step 4G delivers the enterprise-governed Model Context Protocol (MCP) subsystem, enforcing strict boundaries against prompt injection and untrusted tool definitions:
- **`GovernedMCPClient` (`core/mcp/client.py`):**
  - Manages `mcp_server_registrations` and `mcp_pinned_tools` with multi-tenant RLS isolation.
  - Implements **Rule 39 (Untrusted External Metadata)**:
    - **Schema Hash Pinning:** Computes deterministic SHA-256 hash (`schema_hash`) of tool schemas. Schema alterations raise `SchemaTamperingError`.
    - **Prompt Injection Defense:** Model-facing tool descriptions are replaced with verified sovereign descriptions (`verified_description`), completely neutralizing embedded prompt injection.
  - Implements **Rule 34 (Port Routing)**: MCP tool execution evaluates `ActionEnvelope` via `ActionGateway` and executes through `ToolRegistry`.
  - Implements **Rule 35 (At-least-once Execution & Idempotency)**: Replayed calls with identical idempotency keys return cached execution records without repeating side effects.
- **`SandboxedMCPServer` (`core/mcp/server.py`):**
  - Responds to standard MCP JSON-RPC 2.0 requests (`tools/list`, `tools/call`).
  - Defensively wraps all tool outputs with `wrap_untrusted_tool_output(...)` to prevent delimiter breakout attacks.
- **Database Migrations:**
  - `migrations/common/0033_mcp_governance.sql`
  - `migrations/pg/0033_mcp_governance.sql`
- **`docs/reports/ADOPTION_STATUS.md`:**
  - Updated Governed MCP Client to `ADOPTED`.

### 2. Real Execution Output
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 8 items

tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_01_server_registration_and_schema_hash_pinning PASSED [ 12%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_02_prompt_injection_neutralization_rule_39 PASSED [ 25%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_03_schema_tampering_detection_fails_closed PASSED [ 37%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_04_unpinned_tool_rejected PASSED [ 50%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_05_execution_through_action_gateway_rule_34 PASSED [ 62%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_06_idempotent_replay_rule_35 PASSED [ 75%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_07_sandboxed_server_json_rpc_roundtrip PASSED [ 87%]
tests/test_step4_governed_mcp.py::TestStep4GovernedMCP::test_08_mutation_check_unapproved_tool_execution_blocked PASSED [100%]

============================== 8 passed in 2.06s ===============================
```

### 3. Decisions & Invariants Enforced
- **Rule 39 (Untrusted External Metadata):** External tool descriptions and schemas are untrusted data; schema tampering is rejected with `SchemaTamperingError`; descriptions are overridden by verified sovereign text.
- **Rule 34 (Port Isolation & Anti-Bypass):** MCP tools execute through `ActionEnvelope` evaluated by `ActionGateway`.
- **Rule 35 (At-least-once Execution & Idempotency):** Deterministic per-action idempotency keys prevent duplicate executions.
- **Defensive Output Wrapping:** Tool responses from `SandboxedMCPServer` are framed within `<<<UNTRUSTED_CONTENT>>>` wrappers.
- **Rule 37 (Adoption Honesty):** `docs/reports/ADOPTION_STATUS.md` tracks Governed MCP Client as `ADOPTED`.

### 4. Status
Sub-Step 4G verification complete. OpenCode review verdict: PASS.
- **GitHub Actions CI Run:** [45176513573](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/45176513573) (100% GREEN)
  - PostgreSQL 16 & Service Containers Contract Tests: PASS (2m33s)
  - SQLite Dev Profile Test Suite: PASS (2m3s)
  - Supply Chain, SBOM, License & Image Pinning Audit: PASS (1m46s)
- **Commit:** `4cf0b70`

---

## Sub-Step 4H: OpenTelemetry Instrumentation & Secret Canary

### 1. Overview & Objectives
Sub-Step 4H delivers enterprise distributed tracing and telemetry sanitization across ZONATA's multi-framework execution stack:
- **W3C TraceContext Propagation (`core/telemetry/context.py`):**
  - Generates and parses standard W3C `traceparent` headers (`00-{trace_id32}-{span_id16}-{flags02}`).
  - Injects and extracts correlation contexts across asynchronous carrier boundaries (HTTP headers, activity payloads, and task messages).
- **Rule 24 & Rule 36 Redaction Engine (`core/telemetry/sanitizer.py`):**
  - Sanitizes attributes against credentials, passwords, private keys, API keys, and canary tokens.
  - Enforces prompt and completion body gating based on tenant privacy policy (`tenant_allow_prompt_capture`).
  - Fails closed in strict mode (`TelemetryLeakageError`) when unredacted secrets are detected.
- **Dual-Mode Distributed Tracer (`core/telemetry/tracer.py`):**
  - Emits stable, forward-compatible `zonata.*` namespace attributes on 100% of spans.
  - Emits official OpenTelemetry GenAI semantic conventions (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.total_tokens`) behind `OTEL_GENAI_CONVENTIONS_ENABLED=1`.
- **Secret Canary Probe & Scanner (`core/telemetry/canary.py`):**
  - Generates high-entropy canary secrets (`ZONATA_CANARY_*`).
  - Executes active end-to-end drills injecting canary secrets into spans and proves 0% leak rate in serialized OTLP payloads.
- **Runtime Interceptors (`core/telemetry/interceptor.py`):**
  - `@instrument_llm_call` and `@instrument_tool_call` decorators and `trace_span` context managers.
- **Standing Rule 40 / ADR 0016 Legal/AGPL Isolation:**
  - Automated AST scanner verifies zero in-process imports of AGPL packages (`grafana`, `loki`, `tempo`).
- **Adoption Log (`docs/reports/ADOPTION_STATUS.md`):**
  - Updated `OpenTelemetry GenAI` to `ADOPTED`.

### 2. Real Execution Output
```text
======================================================================
ZONATA Rule 34 Audit — Port Egress & Framework Anti-Bypass Linter
Scanning directory: core
======================================================================
[PASS] Zero Rule 34 port bypass violations found across all frameworks.
======================================================================

============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 8 items

tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_01_w3c_traceparent_propagation PASSED [ 12%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_02_span_creation_and_hierarchical_linking PASSED [ 25%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_03_genai_semantic_conventions_flag PASSED [ 37%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_04_secret_canary_probe_zero_leakage_rule_24 PASSED [ 50%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_05_tenant_policy_prompt_body_gating_rule_36 PASSED [ 62%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_06_runtime_interceptors_and_decorators PASSED [ 75%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_07_standing_rule_40_agpl_isolation_check PASSED [ 87%]
tests/test_step4_opentelemetry.py::TestStep4OpenTelemetry::test_08_mutation_check_strict_leakage_fails_closed PASSED [100%]

============================== 8 passed in 8.45s ===============================
```

### 3. Decisions & Invariants Enforced
- **Standing Rule 24 (Zero Plaintext Secrets):** Telemetry attributes never contain raw API keys, bearer tokens, or passwords; canary injection drills verify 0 leaks.
- **Standing Rule 36 (Attribute Allow-List & Privacy Gating):** Prompt and completion bodies are redacted to `[BODY_OMITTED_BY_TENANT_POLICY]` by default, captured only under explicit tenant opt-in.
- **Standing Rule 40 / ADR 0016 (AGPL Network Boundary):** AST checks enforce zero linking of AGPL libraries in application code; Prometheus, Alertmanager, and Jaeger serve as Apache-2.0 telemetry core; Grafana/Loki/Tempo remain external boundary containers.
- **ADR 0015 (Stable zonata.* vs GenAI Conventions):** Forward-compatible `zonata.*` metrics always emitted; `gen_ai.*` emitted under explicit feature flag.
- **Standing Rule 37 (Adoption Honesty):** `docs/reports/ADOPTION_STATUS.md` tracks OpenTelemetry GenAI as `ADOPTED`.

### 4. Status
Sub-Step 4H verification complete. OpenCode review verdict: PASS.
Proceeding to Sub-Step 4I: 24/7 autonomous daemon & self-healing.
