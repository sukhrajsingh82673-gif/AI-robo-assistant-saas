# ZONATA Step 4 Inventory: Durable Frameworks, Runtimes, MCP & Observability

**Date:** 2026-11-23  
**Context:** OpenCode Step 4A — Preflight & Architecture Gap Audit  
**Author:** Antigravity (Builder)  
**Reviewer:** OpenCode (Independent Reviewer)

---

## 1. Executive Summary

This inventory assesses the existing repository components targeted by OpenCode Step 4. It establishes the exact gap between legacy/home-built simulations and official governed framework adapters (Temporal, LangGraph, Google ADK, official MCP Python SDK, OpenTelemetry SDK).

In accordance with Standing Rule 1 (Truth Rule), Rule 33 (Frameworks as replaceable runtime adapters), Rule 34 (Anti-bypass guards), and Rule 37 (Adoption honesty), every item is audited for real package imports, test coverage, and constitutional boundaries.

---

## 2. Component Inventory Table

| # | Target Domain / Component | File Path(s) | Actual Capability & Architectural Reality | Tested? | Status |
|:---|:---|:---|:---|:---:|:---:|
| **1** | **LangGraph Adapter** | `zonata/langgraph_adapter.py`<br>`core/durable_workflow_runtime.py` | **Audit Verdict: Home-built simulation.** It defines internal `StateGraph`, `NodeType`, and `Command` classes over `core/durable_workflow_runtime.py`. It **never imports `langgraph`**. Needs honest renaming/fallback and replacement with official `langgraph` package in 4E. | Partial | **PARTIAL** |
| **2** | **Temporal Workflow Code** | `core/temporal_durable_execution_runtime.py`<br>`zonata/temporal_adapter.py` | **Audit Verdict: Simulated engine.** 1,817 lines of custom in-memory and SQLite-backed workflow scheduling. It **never imports `temporalio`**. Claims constants `TEMPORAL_SERVER_VERSION = "1.26.2"`, but runs internally. Needs replacement behind `WorkflowEnginePort` with real `temporalio` SDK in 4C. | Partial (`test_temporal_durable_execution.py`) | **PARTIAL** |
| **3** | **Hand-written MCP Client** | `core/mcp_interoperability_runtime.py`<br>`zonata/mcp_adapter.py`<br>`agent_factory/capabilities/mcp_gateway.py` | **Audit Verdict: Custom JSON-RPC implementation.** 2,140 lines of manual HTTP/stdio JSON-RPC framing via `urllib.request`. Does not use the official Model Context Protocol Python SDK (`mcp`). Needs replacement with official `mcp` SDK v1.x and RFC 9728 OAuth resource-server metadata in 4G. | Partial (`test_mcp_interoperability.py`) | **PARTIAL** |
| **4** | **Agent-to-Agent (A2A) Code** | `core/a2a_interoperability_runtime.py`<br>`zonata/a2a_adapter.py`<br>`agent_factory/capabilities/a2a_gateway.py` | **Audit Verdict: Custom simulation of A2A v1.0 spec.** 1,488 lines implementing agent cards, HMAC signatures, and task endpoints. Upstream Python SDK is pre-v0.4. Per Decision D4-1, internal agent communication uses ZONATA ports. A2A is restricted to optional external interop or designated `NOT_ADOPTED` in 4F. | Partial (`test_a2a_interoperability.py`) | **PARTIAL** |
| **5** | **Compose Services (Temporal, NATS, OTel, Prom, Grafana)** | `deploy/compose/docker-compose.cloud-staging.yml`<br>`deploy/compose/docker-compose.cloud-production.yml` | **Audit Verdict: Existing service definitions.**<br>• `temporalio/auto-setup:1.24.0` (Pinned; needs update to latest stable 1.26+ in 4I)<br>• `nats:2.10.18-alpine` (Pinned; unneeded per ADR 0017)<br>• `otel/opentelemetry-collector-contrib:0.96.0` (Pinned; needs update to 0.110+)<br>• `prom/prometheus:v2.51.0` (Pinned; Apache-2.0)<br>• `prom/alertmanager:v0.27.0` (Pinned; Apache-2.0)<br>• `grafana/grafana:10.4.0` (Pinned; AGPL-3.0 boundary service) | Verified in compose config tests | **EXISTS** |
| **6** | **Transactional Outbox Implementations** | `core/baseline/outbox.py`<br>`core/outbox.py`<br>`core/transactional_outbox.py` | **Audit Verdict: Redundant legacy files.** `core/baseline/outbox.py` is the canonical, verified Step 1 outbox with DLQ, exponential backoff, and idempotent keys (`outbox_events`). `core/outbox.py` and `core/transactional_outbox.py` are legacy duplicates. | Tested (`test_always_on_baseline.py`) | **EXISTS** |
| **7** | **Agent Factory Compiler & `zonata.agent/v1` Spec** | `agent_factory/build/compiler.py`<br>`agent_factory/spec/validator.py`<br>`core/agents/runtime.py` | **Audit Verdict: Functional declarative spec pipeline.** Validates `zonata.agent/v1` YAML/JSON documents against schema, enforcing permission profiles and compiling into governed graphs. Ready to be extended with LangGraph and Google ADK compilation targets in 4B. | Tested (`test_stage5_factory_integration.py`, `test_agent_runtime.py`) | **EXISTS** |
| **8** | **Workflow & Run State Tables** | PostgreSQL 16 & SQLite Schemas (`migrations/pg/0001_...`, `0023_work_kernel.sql`) | **Audit Verdict: 11 distinct state tables exist:**<br>1. `workflows` (Workflow definitions)<br>2. `workflow_runs` (Run instances)<br>3. `workflow_checkpoints` (Step checkpoints)<br>4. `workflow_events` (Append-only audit trail)<br>5. `workflow_approvals` (Approval gates)<br>6. `workflow_resource_locks` (Concurrency control)<br>7. `temporal_workflows` (Legacy Temporal records)<br>8. `temporal_workflow_events` (Legacy event stream)<br>9. `work_items` (Step 2 work kernel items)<br>10. `sop_instances` / `sop_instance_steps` (SOP state)<br>11. `agent_runs` (Step 4B run tracking table to add) | Tested across Step 1 and Step 2 suites | **EXISTS** |
| **9** | **Google ADK Framework** | N/A (New target in Step 4) | **Audit Verdict: Not yet installed or wrapped.** Google Agent Development Kit (ADK) will be adopted behind `AgentRuntimePort` for multi-agent department teams and Step 3 research teams per Decision D4-1. | Untested (New) | **MISSING** |
| **10** | **OpenTelemetry SDK Instrumentation** | N/A (New target in Step 4) | **Audit Verdict: Collector exists in compose, but application code lacks official OTel SDK instrumentation.** Need `opentelemetry-api` and `opentelemetry-sdk` integration with stable `zonata.*` attributes and `gen_ai.*` feature flags. | Untested (New) | **MISSING** |

---

## 3. Findings & Architectural Realities

1. **Simulated vs Real Frameworks:**
   - Both `zonata/langgraph_adapter.py` and `core/temporal_durable_execution_runtime.py` are comprehensive internal emulations that do not import their respective upstream SDKs.
   - In accordance with Standing Rule 37 (Adoption Honesty), these will be refactored: the real upstream packages (`temporalio`, `langgraph`) will be pinned, wrapped behind ZONATA ports, and integrated into the qualification scenario.
2. **NATS Redundancy:**
   - Compose services contain NATS (`nats:2.10.18-alpine`), but ZONATA's transactional PostgreSQL outbox (`core/baseline/outbox.py`) provides sufficient throughput and atomic database transaction guarantees without introducing cluster coordination complexity. ADR 0017 formally decides against NATS.
3. **Observability Licensing Boundary:**
   - Prometheus and Jaeger are Apache-2.0. Grafana, Loki, and Tempo are AGPL-3.0. In accordance with Standing Rule 5 and Rule 14, AGPL components must operate strictly as isolated network services without Python library linking.
