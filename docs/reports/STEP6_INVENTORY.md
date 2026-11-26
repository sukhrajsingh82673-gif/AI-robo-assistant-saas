# Step 6 Evolution Layer — Comprehensive Subsystem Inventory

**Date:** 2026-11-24  
**Author:** Antigravity (Senior Systems Architect & Autonomous Builder)  
**Target Reviewer:** OpenCode Arbiter & Security Reviewer  
**Governing Standard:** Antigravity Step 6 — Sub-Step 6A & Standing Rule 49 (Preservation Contract)

---

## 1. Ten-Domain Evolution Inventory Matrix

| Domain # | Functional Domain | Primary Code Paths | Status | Test Coverage | Step 6 Gap Analysis & Role |
|:---:|---|---|:---:|---|---|
| **1** | **Kaizen & Self-Healing** | `core/kaizen/`, `core/daemon/self_healing.py` | `PARTIAL` | `tests/test_step4_autonomous_daemon.py` | Basic task retry and orphaned lock recovery exist; needs structured failure taxonomy ingestion and clustering (6C). |
| **2** | **Memory & Knowledge Store** | `core/memory/` (unstructured) | `MISSING` | None | No structured pgvector or `zonata.playbook/v1` store exists; needs governed playbooks, lessons, and exemplars (6E). |
| **3** | **Agent Specs & Factory Gates** | `agent_factory/build/`, `core/agent_spec/compiler.py` | `PARTIAL` | `tests/test_step3_agent_import.py`, `tests/test_step4_runtime_ports.py` | AST compilation and runtime validation exist; needs static prohibition against widening tools/privileges during self-improvement (6F). |
| **4** | **Import Lane (Step 3G)** | `core/agent_import/`, `core/ports/agent_import.py` | `EXISTS` | `tests/test_step3_agent_import.py` | Static scanning and quarantine exist; serves as foundation for Open-Source Agent intake ("Agent Zoo") in 6G. |
| **5** | **Eval Harness (Step 2K)** | `core/evals/`, `scripts/run_evals.py` | `EXISTS` | `tests/test_eval_harness.py`, `tests/test_step2_scenario.py` | Golden evals exist; needs held-out test sets and semantic-floor regression gates that improvers cannot see (6F). |
| **6** | **Evidence Ledger Events** | `core/evidence_ledger.py`, `core/evidence_service.py` | `EXISTS` | `tests/test_ledger_kernel.py`, `tests/test_step5_incident_response_resilience.py` | Merkle-chained immutable evidence ledger exists; consumes forensic quarantine and execution receipts. |
| **7** | **Outbox & Coordination Events** | `core/daemon/dlq_processor.py`, `core/daemon/autonomous_daemon.py` | `EXISTS` | `tests/test_step4_autonomous_daemon.py` | Outbox DLQ and distributed coordination exist; provides event emission for failure intelligence subscription. |
| **8** | **Failure & Audit Logs** | `core/audit/siem_exporter.py`, `core/incident/playbooks.py` | `EXISTS` | `tests/test_step5_audit_privacy_compliance.py`, `tests/test_step5_incident_response_resilience.py` | Merkle hash-chained CEF audit events exist; feeds failure event ingestion pipeline (6C). |
| **9** | **GitHub Integration** | `core/identity/workload.py` (`GitHubAppTokenManager`) | `EXISTS` | `tests/test_step5_identity_access.py` | Scoped GitHub App installation tokens exist; needs governed PR generation, untrusted issue triage, and public-repo hygiene (6I). |
| **10** | **Self-Improvement / Optimization** | `core/optimization/` | `MISSING` | None | No DSPy/GEPA optimization stack exists; needs sandboxed prompt/skill tuning engine under Rule 56 budget (6F). |

---

## 2. Preserved Boundaries & Extension Points

Under the **Preservation Contract (Rule 49)**, existing modules in Domains 3, 4, 5, 6, 7, 8, and 9 remain frozen:
- Step 6 will **not** modify `core/evidence_ledger.py`, `core/evals/`, `core/action_gateway.py`, or `core/db.py`.
- Step 6 will subscribe to existing event outboxes and audit streams via non-invasive listeners.
- New capabilities (failure ingestion, playbooks, DSPy optimizer, clean-room replicator, GitHub PR author) will reside exclusively in new namespaced packages (`core/evolution/`, `core/knowledge/`, `core/cleanroom/`).
