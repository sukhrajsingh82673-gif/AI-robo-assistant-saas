# OpenCode Step 2 — Preflight & Existing Capabilities Inventory

**Document Version:** 1.0.0  
**Date:** 2026-11-22  
**Branch:** `step2-intelligence-execution`  
**Base Commit (Step 1 Complete):** `70d79b7 feat(step1j): complete step 1 qualification scenario and acceptance signoff`  
**Authoritative CI Run URL:** [Run 44925486054 (100% Green across all 3 jobs)](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/44925486054)

---

## 1. Step 1 Foundation Gate Check

Before constructing the intelligence and execution kernel, the foundational prerequisites from Step 1 (`step1-foundation-backbone`) were verified. Zero regressions and 100% component availability were confirmed.

| Subsystem Component | Path in Codebase | Verification Status | Empirical Evidence |
|:---|:---|:---|:---|
| **Test Collection** | `tests/` | **PASS** | 83 passed, 4 skipped in unit suite; 0 collection errors across entire repository. |
| **Capability Truth Table** | `core/capability_probe.py`, `scripts/reality_probe.py` | **LIVE & OPERATIONAL** | Generates `docs/reports/CAPABILITY_STATUS.md`; reports truthful statuses (`OK`, `SANDBOX`, `NOT_CONFIGURED`, `NOT_IMPLEMENTED`). |
| **Port Framework** | `core/ports/base.py`, `ProviderResult`, `PortStatus` | **LIVE & OPERATIONAL** | Typed status ladder (`OK`, `ACCEPTED_BY_PROVIDER`, `FAILED`, `NOT_CONFIGURED`, `NOT_IMPLEMENTED`, `SANDBOX`, `DEGRADED`). |
| **Six Backbone Adapters** | `core/ports/` (storage, antivirus, tika, ocr, email, kms) | **LIVE & OPERATIONAL** | Verified against real service containers (PostgreSQL 16, SeaweedFS, ClamAV, Apache Tika, Mailpit SMTP). |
| **Job Runner & Outbox** | `core/baseline/scheduler.py`, `core/baseline/outbox.py` | **LIVE & OPERATIONAL** | Leased scheduler with monotonic next-run; durable transactional outbox with 5-attempt DLQ. |
| **Document Store** | `core/documents/manager.py`, `core/documents/pipeline.py` | **LIVE & OPERATIONAL** | 10 governed tables, 8-state pipeline, PostgreSQL 16 RLS, magic-byte sniffer, envelope encryption, bit-rot sweep. |
| **Folio Evidence Backbone** | `core/folios/manager.py`, `core/folios/merkle.py`, `core/folios/export.py` | **LIVE & OPERATIONAL** | Merkle evidence trees, self-contained `.zip` export packs with zero-dependency `verify_pack.py` offline verifier. |
| **Double-Entry Ledger** | `core/ledger/kernel.py`, `core/ledger/currency.py` | **LIVE & OPERATIONAL** | Integer minor units, zero float arithmetic, net-zero balance invariant per currency, DB immutability triggers. |
| **Industry Pack Compiler** | `core/industry_packs/schema.py`, `loader.py`, `isic.py` | **LIVE & OPERATIONAL** | UN ISIC Rev. 4 taxonomy registry (21 Sections, 88 Divisions); schema validator; SaaS (J62), Hospitality (I55), Manufacturing (C28), Clinic (Q86). |
| **Evidence Ledger** | `core/evidence_service.py`, `core/folios/merkle.py` | **LIVE & OPERATIONAL** | Cryptographic hash chaining, Merkle roots, unalterable audit trails. |

*Gate Decision:* **PROCEED WITH STEP 2.** All Step 1 components are verified and operational.

---

## 2. Step 2 Domain Inventory & Existing Subsystem Mapping

Each required domain in sub-steps 2C to 2I was audited across `core/`, `agent_factory/`, `migrations/`, and `tests/`.

| Domain Item | Existing Path(s) | Real Implementation & Behavior | Tested? | Status |
|:---|:---|:---|:---|:---|
| **LLM Providers & Routing** | `core/model_gateway.py`<br>`core/model_gateway_v4.py`<br>`core/neon_ai_gateway.py` | `ModelGateway` simulates token usage and costs with `len(prompt)//4`; `ModelGatewayV4` has DLP screening and mock responses (`[Governed AI Response...]`); `NeonAIGatewayClient` provides raw HTTP to Databricks/Neon. Missing typed Pydantic output schemas, multi-tier fallbacks (`PLANNER`, `WORKER`, `FAST`, `VISION`, `EMBEDDING`), and hierarchical reserve-then-settle budgeting. | Partially in `test_ports_contracts.py` | **PARTIAL** |
| **ActionGateway** | `core/action_gateway.py` | Conceptual 20-step pipeline (`ZonataActionGateway`). Currently checks basic rate limiting and substring matching on `core.policy`. Does NOT enforce typed action classes (`READ_INTERNAL`, `COMMIT_SPEND`, `POST_LEDGER`, etc.), does NOT evaluate G1–G9 profiles, and lacks Rule 15 principal separation. | Unit mocks in `test_stage9_pilot_run.py` | **PARTIAL** |
| **Authority Profiles (G1–G9)** | `core/workforce_architecture.py` | Defines `GRADE_AUTHORITY` mapping grades G1–G9 to spend limits, hiring rights, and SOP rights. Stored and returned, but **not consulted or enforced** during execution by the ActionGateway, ledger posting, or agent runtimes. | Unit tests in `test_workforce_architecture.py` | **EXISTS (UNENFORCED)** |
| **Approvals** | `core/approvals.py`<br>`core/approval_binder.py`<br>`core/cryptographic_approvals.py` | Provides approval states and cryptographic signatures. Lacks binding to SHA-256 payload digest in ActionGateway, self-approval prevention at the execution kernel, and multi-tier quorum chains. | Unit tests in `test_approvals.py` | **PARTIAL** |
| **Budgets** | `core/spend_governor.py`<br>`core/billing.py` | Floating-point spend tracking. Lacks hierarchical reserve-then-settle transactions (tenant → company → dept → position → mission → task) in integer micro-units with currency conversions and row locks. | Unit tests in `test_billing.py` | **PARTIAL** |
| **Kill Switch** | `core/killswitch_matrix.py`<br>`core/distributed_coordination.py` | Checks agent/tenant kill state in SQLite/PostgreSQL. Missing strict Rule 15 principal separation (agents must not be able to write kill switch) and sub-5s global abort guarantees in agent execution loops. | Basic unit tests | **PARTIAL** |
| **Missions** | `core/executive_missions.py`<br>`core/mission_orchestrator.py` | Table `missions` exists. Lacks deterministic DAG dependency checks, budget reservation, SLA timers linked to Step 1 scheduler, and verification pyramid completion. | Unit tests in `test_executive_missions.py` | **PARTIAL** |
| **Tasks** | `migrations/pg/0005_workforce_architecture.sql` | Table `tasks` exists with simple `TODO/IN_PROGRESS/DONE` states. Missing the mandatory 7-state state machine (`PROPOSED → ASSIGNED → ACCEPTED → IN_PROGRESS → SUBMITTED → VERIFYING → COMPLETED`), machine-checkable acceptance criteria, and self-completion prevention. | Stale tests | **PARTIAL** |
| **SOP Versioning** | `core/sop_compiler.py`<br>`core/aic_ceo_sop.py` | Compiles YAML/Markdown SOPs with hash versions. Not executable step-by-step through ActionGateway; lacks dry-run zero side-effect verification; stubs without steps are not flagged `NOT_EXECUTABLE`. | Unit tests in `test_sop_compiler.py` | **PARTIAL** |
| **KRA/KPI Scoring** | `core/kpi_kra_engine.py`<br>`core/kpis.py`<br>`core/aic_ceo_kra_kpi.py` | Evaluates KPI formulas. Lacks number-lock for narrative generation, baseline verification refusing unmeasurable goals (`INSUFFICIENT_MEASUREMENTS`), and governed views over Step 1 ledger/folios. | Unit tests in `test_kpi_kra_engine.py` | **PARTIAL** |
| **CEO Brain** | `core/ceo_engine.py`<br>`core/ai_ceo_v8.py`<br>`core/ceo_conversation_engine.py` | Orchestrates multi-horizon planning and chat interactions. Free text triggers actions without schema-validated action proposals; ambiguous high-stakes commands guess instead of asking clarifying questions; company constitution document is not versioned in Step 1 store. | Unit tests in `test_ai_ceo_v8.py` | **PARTIAL** |
| **Kaizen** | `tests/test_stage7_kaizen.py` | Continuous improvement suggestions. Mostly simulated without closed-loop empirical verification. | Pilot tests | **PARTIAL** |
| **Agent Instances** | `core/workforce.py`<br>`agent_factory/domain/lifecycle.py` | Tables `governed_agents` and `agent_instances`. Agent runtime lacks bounded loop limits (`max_steps`, `max_seconds`, `max_cost`), idempotency-keyed step replay prevention, crash resumption, and certification checks. | Unit tests in `test_workforce.py` | **PARTIAL** |
| **AI Employees** | `core/ai_employee_os.py`<br>`core/employee_factory_v7.py` | Tables `ai_employees`, `employee_templates`. Lacks Rule 19 conservative autonomy ceiling (`SHADOW` default; minimum of owner setting, pack review cap, trust level, and capability truth) and trust progression. | Unit tests in `test_v4_ai_employee_lifecycle.py` | **PARTIAL** |
| **Org & Roles** | `core/organization_graph.py`<br>`core/aic_organization_constitution.py` | 13-role executive catalog, departments, positions. Lacks cycle rejection in reporting lines, single-CEO constraint enforcement, and formal handover pack generation. | Unit tests in `test_organization_graph.py` | **PARTIAL** |
| **Tool Registry & MCP** | `core/governed_tool_registry.py`<br>`core/tool_fabric.py`<br>`core/mcp_interoperability_runtime.py` | Registers tools and MCP servers. Missing typed contract (input/output JSON Schema, side-effect class, truth-table capability check, action class, cost model). Does not report reasons when capabilities are not `OK`. | Unit tests in `test_governed_tool_registry.py` | **PARTIAL** |
| **Agent Specs (`zonata.agent/v1`)** | `agent_factory/spec/validator.py`<br>`docs/agent-factory/architecture/reference/spec/zonata.agent.v1.example.yaml` | Implements structural and semantic validation for YAML agent definitions. | Tested in `test_agent_factory.py` | **EXISTS** |
| **Workforce Tables** | `migrations/pg/0005_workforce_architecture.sql` | 25 tables defining departments, positions, employees, missions, tasks, SOPs. Lacks PostgreSQL 16 RLS policies and extensions for Step 2 (`model_calls`, `verification_reports`, `kpi_values`, `company_constitutions`). | Migration applied | **PARTIAL** |

---

## 3. Authoritative G1–G9 Authority Profile Definitions

The authoritative definitions of authority profiles G1 to G9 are extracted directly from `core/workforce_architecture.py` (lines 40–59):

```python
# Grade -> (authority tier, single-spend limit USD, monthly limit USD,
#           can_hire, can_delegate, can_modify_sops)
GRADE_AUTHORITY: Dict[str, Dict[str, Any]] = {
    "G1": {
        "tier": "OWNER",
        "single": 1_000_000,
        "monthly": 5_000_000,
        "can_hire": True,
        "can_delegate": True,
        "can_modify_sops": True,
    },
    "G2": {
        "tier": "EXECUTIVE",
        "single": 250_000,
        "monthly": 1_000_000,
        "can_hire": True,
        "can_delegate": True,
        "can_modify_sops": True,
    },
    "G3": {
        "tier": "EXECUTIVE",
        "single": 100_000,
        "monthly": 400_000,
        "can_hire": True,
        "can_delegate": True,
        "can_modify_sops": True,
    },
    "G4": {
        "tier": "MANAGER",
        "single": 25_000,
        "monthly": 100_000,
        "can_hire": False,
        "can_delegate": True,
        "can_modify_sops": True,
    },
    "G5": {
        "tier": "MANAGER",
        "single": 10_000,
        "monthly": 50_000,
        "can_hire": False,
        "can_delegate": True,
        "can_modify_sops": False,
    },
    "G6": {
        "tier": "MANAGER",
        "single": 2_500,
        "monthly": 15_000,
        "can_hire": False,
        "can_delegate": True,
        "can_modify_sops": False,
    },
    "G7": {
        "tier": "EMPLOYEE",
        "single": 500,
        "monthly": 5_000,
        "can_hire": False,
        "can_delegate": False,
        "can_modify_sops": False,
    },
    "G8": {
        "tier": "EMPLOYEE",
        "single": 250,
        "monthly": 2_500,
        "can_hire": False,
        "can_delegate": False,
        "can_modify_sops": False,
    },
    "G9": {
        "tier": "EMPLOYEE",
        "single": 100,
        "monthly": 1_000,
        "can_hire": False,
        "can_delegate": False,
        "can_modify_sops": False,
    },
}

TIER_RANK = {"EMPLOYEE": 0, "MANAGER": 1, "EXECUTIVE": 2, "OWNER": 3}
```

---

## 4. Default Model Provider & Measured Throughput Limits

### Current Default Model Provider
- **Configured Default:** `embedded_free` (heuristic local rule engine).
- **Fallback Behavior:** If `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY` are not set in the environment, `core/capability_probe.py` selects `embedded_free`. In production (`APP_ENV=production`), this reports `PortStatus.DEGRADED` unless `ZONATA_ALLOW_DEGRADED=1`.

### Measured Throughput Limits
1. **`embedded_free` (Rule Engine / Local):**
   - **Throughput:** Infinite in theory (CPU-bound on device), ~0.05 ms latency per evaluation.
   - **Cost:** $0.00.
   - **Capability:** Deterministic static heuristic rules only; incapable of reasoning, extraction of novel schemas, or multi-modal analysis.
2. **Google Gemini Free Tier (Standard Fallback when Key Provided):**
   - **Requests Per Minute (RPM):** 15 RPM.
   - **Tokens Per Minute (TPM):** 1,000,000 TPM.
   - **Requests Per Day (RPD):** 1,500 RPD.
3. **Anthropic Claude Tier 1 (when Key Provided):**
   - **RPM:** 50 RPM.
   - **TPM:** 20,000 TPM (Sonnet).
4. **OpenAI Tier 1 (when Key Provided):**
   - **RPM:** 500 RPM.
   - **TPM:** 30,000 TPM (GPT-4o).

---

## 5. Audit: Untyped Action Triggers from Model Outputs

The audit discovered several locations where a model response, chat turn, or raw string currently triggers side effects or action execution without schema validation through the ActionGateway:

1. **`core/ceo_conversation_engine.py` (lines 299–307):**
   ```python
   for tool_name in structured_dec.required_tools[:2]:
       self.tool_registry.authorize_and_dispatch(
           tool_id=tool_name,
           parameters={"goal": instruction},
           spending_limit_inr=spending_limit_inr
       )
   ```
   *Defect:* Unvalidated string parameters and tool IDs dispatched directly to `tool_registry` without ActionEnvelope creation or ActionGateway evaluation.

2. **`core/ceo_conversation_engine.py` (line 320):**
   ```python
   mission_rec.progress = 100
   ```
   *Defect:* Directly claims mission completion immediately after dispatching tools without going through the Verification Pyramid (violates Rule 17: "Done is a claim, not a fact").

3. **`core/ai_ceo_v8.py` (lines 362–369):**
   ```python
   scenario_res = self.execute_closed_loop_scenario(owner_goal=message)
   ```
   *Defect:* Unchecked natural language chat messages directly initiate a 22-step mutation sequence without schema validation.

4. **`core/ceo_engine.py` (line 182):**
   ```python
   base_res = self.legacy_command_engine.execute_directive(directive_text)
   ```
   *Defect:* Raw directive text dispatched to legacy execution engine without typed action classes.

5. **`core/coworker/acceptance_missions.py` (line 180):**
   ```python
   turn = hermes.execute_turn("Run git status via terminal to verify repository health")
   ```
   *Defect:* Rule-based text strings trigger CLI terminal execution without parameter schema typing.

---

## 6. Conclusion & Architectural Roadmap for Step 2

To satisfy the requirements of OpenCode Step 2:
1. **Sub-Step 2B:** Implement typed `LLMGateway` Port supporting tiers (`PLANNER`, `WORKER`, `FAST`, `VISION`, `EMBEDDING`), Pydantic output schemas, multi-tier reserve-then-settle budgeting in integer micro-units, and prompt registries with untrusted content isolation.
2. **Sub-Step 2C:** Upgrade `ActionGateway` to strictly enforce typed action classes, fixed-order policy decisions, G1–G9 authority profiles, segregation of duties, payload SHA-256 bound approvals, and Rule 15 principal separation.
3. **Sub-Step 2D:** Implement acyclic organizational reporting, single CEO constraint, and formal handover packs.
4. **Sub-Step 2E:** Implement bounded agent runtime (`max_steps`, `max_seconds`, `max_cost`) with idempotency and crash recovery.
5. **Sub-Step 2F–2H:** Implement 7-state work kernel, executable SOPs with compliance scoring, and the 5-level Verification Pyramid (L1–L5).
6. **Sub-Step 2I–2K:** Implement deterministic KPI engine with number-lock, AI CEO executive brain, and comprehensive evals.
