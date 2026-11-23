# Sub-Step 4A Review: Preflight, Inventory and Architectural Decision Records (ADRs)

**Sub-Step:** 4A  
**Branch:** `step4-durable-frameworks`  
**Reviewer:** OpenCode (Independent Architecture Reviewer)  
**Date:** 2026-11-23  
**Verdict:** **PASS**  

---

## 1. Audit Against Acceptance Criteria

| Criteria | Required Invariant | Audit Findings | Result |
| :--- | :--- | :--- | :--- |
| **Gate Check** | All foundations from Steps 1–3 must be confirmed present and green. | Verified via `tests/test_step4_preflight.py`: `WorkflowEnginePort`, `tool_registry`, `action_gateway`, `llm_gateway`, `DurableScheduler`, `DurableOutbox`, `EvidenceLedger`, 18 capabilities truth table, `OriginBoundSecretVault`, and Step 3 hands all verified active. | **PASS** |
| **Inventory Report** | `docs/reports/STEP4_INVENTORY.md` must audit all 10 required domains with current state and migration plans. | Audit covers LangGraph adapter, Temporal simulation, hand-written MCP, A2A code, Compose services, transactional outbox, Agent Factory compiler, workflow state tables, Google ADK, and OpenTelemetry. | **PASS** |
| **ADR 0009 (Temporal Topology)** | Self-hosted server topology, namespaces, worker roles, MIT license. | Fully documented in `docs/architecture/ADR_0009_TEMPORAL_TOPOLOGY.md`. | **PASS** |
| **ADR 0010 (Framework Split D4-1)** | Formal division of labor across Temporal (long business cycles), LangGraph (local iteration), Google ADK (hierarchical teams). | Fully documented in `docs/architecture/ADR_0010_FRAMEWORK_SPLIT_DECISION_D4_1.md`. | **PASS** |
| **ADR 0011 (LangGraph Checkpointer)** | PostgreSQL checkpointer with RLS and encryption, MIT license. | Fully documented in `docs/architecture/ADR_0011_LANGGRAPH_CHECKPOINTER.md`. | **PASS** |
| **ADR 0012 (Google ADK Extension)** | Extension points, wrappers, governance routing, Apache-2.0 license. | Fully documented in `docs/architecture/ADR_0012_ADK_EXTENSION_POINTS.md`. | **PASS** |
| **ADR 0013 (MCP SDK & Rug-Pull)** | Official `mcp` SDK, schema hash pinning, reviewed description override, MIT license. | Fully documented in `docs/architecture/ADR_0013_MCP_SPEC_AND_SDK.md`. | **PASS** |
| **ADR 0014 (A2A Interop)** | A2A evaluation, sovereign bridge, untrusted payload sanitization. | Fully documented in `docs/architecture/ADR_0014_A2A_INTEROP_EVALUATION.md`. | **PASS** |
| **ADR 0015 (OpenTelemetry Conventions)** | GenAI semantic conventions, context propagation, canary spans, Apache-2.0 license. | Fully documented in `docs/architecture/ADR_0015_OPENTELEMETRY_CONVENTIONS_AND_CANARY.md`. | **PASS** |
| **ADR 0016 (Observability & AGPL)** | Clear boundary isolation for Prometheus/Jaeger (Apache-2.0) vs Grafana/Loki/Tempo (AGPL-3.0). | Fully documented in `docs/architecture/ADR_0016_OBSERVABILITY_BACKENDS_AND_AGPL_BOUNDARY.md`. | **PASS** |
| **ADR 0017 (Outbox vs NATS)** | Selection of transactional PostgreSQL outbox for transactional ACID safety, retaining outbox pattern. | Fully documented in `docs/architecture/ADR_0017_NATS_VS_POSTGRES_OUTBOX.md`. | **PASS** |
| **Acceptance Testing** | Unit tests verifying gate dependencies, inventory coverage, ADR validity, and mutation checks. | `tests/test_step4_preflight.py` ran 12 tests in 0.76s with 100% PASS. | **PASS** |

---

## 2. Reviewer Verdict

**STATUS: PASS.**  
Sub-Step 4A satisfies all gate requirements, inventory documentation, architectural decision records, and acceptance testing. The builder is authorized to commit Sub-Step 4A and proceed to Sub-Step 4B (`Runtime ports, spec compilers & anti-bypass guards`).
