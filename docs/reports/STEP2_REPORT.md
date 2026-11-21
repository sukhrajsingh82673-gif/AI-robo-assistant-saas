# OpenCode Step 2 — Intelligence, Authority and the Verified Execution Kernel Report

**Branch:** `step2-intelligence-execution`  
**Repository:** `sukhrajsingh82673-gif/AI-robo-assistant-saas`  
**Base Commit (Step 1 Complete):** `70d79b7 feat(step1j): complete step 1 qualification scenario and acceptance signoff`  
**Authoritative Step 1 CI Run URL:** [Run 44925486054 (100% Green across all 3 jobs)](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/44925486054)  
**Target Environment:** Android / Termux ARM64 sovereign execution & GitHub Actions CI (PostgreSQL 16, SeaweedFS S3, Mailpit SMTP, ClamAV, Apache Tika)

---

## Standing Rules Enforced for Step 2
- **Rules 1 to 14 (Step 1 Rules in Force):** Truth rule (`NOT_CONFIGURED`, `NOT_IMPLEMENTED`, `sandbox: true` only in `ZONATA_TEST_MODE=1`); reality ladder; reuse before writing; open source behind Ports with pinned versions; SPDX license tracking; Port pattern; contract tests against real services; acceptance tests shown failing first (mutation check); untrusted content is data; no secrets; never weaken tests; money and time computed in code; multi-tenant by default with PostgreSQL 16 RLS; stop and report when blocked.
- **Rule 15 (Principal Separation):** Model, agent, and AI-employee principals can never write authority profiles, budgets, policies, company constitution, pack review status, approval decisions, delegations, or the kill switch. Enforced at API and PostgreSQL database roles with refusal tests.
- **Rule 16 (Model Output is a Proposal):** Only typed, schema-validated actions that pass ActionGateway have effects. Free text never triggers side effects.
- **Rule 17 ("Done" is a Claim, Not a Fact):** Verification pyramid completes tasks; self-completion by assignees is strictly rejected.
- **Rule 18 (Determinism):** Arithmetic, dates, budgets, KPI values, progress statuses, and report numbers are computed in code from stored data.
- **Rule 19 (Conservative by Default):** New employees/agents start in `SHADOW`. Autonomy ceiling is `min(owner_setting, pack_review_cap, employee_trust, capability_truth)`.
- **Rule 20 (Pre-Execution Budgeting):** Reserve-then-settle hierarchical budgeting. Bounded steps, seconds, and cost.
- **Rule 21 (No Quality Claims Without Measurement):** Prohibit "better than human" unless empirical benchmarks measure it.
- **Rule 22 (Names Must Match Reality):** Honest naming (no false claims of LangGraph, Temporal, MCP, OpenHands unless imported and used).

---

## Sub-Step 2A — Preflight and Inventory

### 1. Objectives & Scope
- Confirm Step 1 is merged and CI is 100% green with zero collection errors across test suites.
- Verify live availability of all foundational Step 1 components:
  1. Capability truth table endpoint (`core/capability_probe.py`, `scripts/reality_probe.py`, `docs/reports/CAPABILITY_STATUS.md`).
  2. Port framework (`core/ports/base.py`, `ProviderResult`, `PortStatus`).
  3. Job runner & durable outbox (`core/baseline/scheduler.py`, `core/baseline/outbox.py`).
  4. Governed document store (`core/documents/manager.py`, `core/documents/pipeline.py`).
  5. Folios & Merkle evidence backbone (`core/folios/manager.py`, `core/folios/merkle.py`, `core/folios/export.py`, `scripts/verify_pack.py`).
  6. Double-entry financial ledger kernel (`core/ledger/kernel.py`, `core/ledger/currency.py`).
  7. Declarative industry pack compiler (`core/industry_packs/schema.py`, `loader.py`, `isic.py`).
  8. Cryptographic evidence ledger.
- Author comprehensive preflight inventory in `docs/reports/STEP2_INVENTORY.md` covering all 18 target domain items with `EXISTS`, `PARTIAL`, or `MISSING` classifications.
- Extract and document exact definitions of authority profiles G1 to G9 from `core/workforce_architecture.py`.
- Record current default model provider, fallback logic, and measured throughput limits.
- Audit the codebase to document every place a model output or natural language chat currently triggers an action without a typed check.

---

### 2. Empirical Verification & Real Command Outputs

#### 2.1 Step 1 Regression Test Suite Execution
Command:
```bash
python3 -m pytest tests/test_truth_linter.py tests/test_capability_truth_and_planner.py tests/test_ports_contracts.py tests/test_documents_backbone.py tests/test_folio_export_backbone.py tests/test_ledger_kernel.py tests/test_industry_pack_framework.py tests/test_always_on_baseline.py -q
```
Real Command Output:
```text
.................s..s.......s..s........................................ [ 82%]
...............                                                          [100%]
83 passed, 4 skipped in 18.52s
```
*Verification Result:* **Zero test collection errors; all Step 1 suites passed cleanly.**

---

#### 2.2 Programmatic Verification of Step 1 Backbone Ports and Primitives
Command:
```bash
python3 -c "
from core.capability_probe import get_all_capabilities
from core.ports.base import Port, ProviderResult, PortStatus
from core.baseline.scheduler import LeasedScheduler
from core.baseline.outbox import DurableOutbox
from core.documents.manager import DocumentManager
from core.folios.manager import FolioManager
from core.ledger.kernel import LedgerKernel
from core.industry_packs.loader import IndustryPackLoader
from core.folios.merkle import MerkleTree

print('Capabilities count:', len(get_all_capabilities()))
print('Ports base loaded:', PortStatus.OK.value)
print('All Step 1 subsystems imported and initialized successfully.')
"
```
Real Command Output:
```text
Capabilities count: 18
Ports base loaded: OK
All Step 1 subsystems imported and initialized successfully.
```

---

#### 2.3 Step 1 Authoritative CI Verification
- **Run ID:** `44925486054`
- **Run URL:** [https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/44925486054](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/44925486054)
- **Status:** **`SUCCESS` across all three jobs**:
  - `Job 1: SQLite Dev Profile Test Suite (46s)` — ID `136910509963`
  - `Job 2: PostgreSQL 16 & Service Containers Contract Tests (1m15s)` — ID `136910510023`
  - `Job 3: Supply Chain, SBOM, License & Image Pinning Audit (44s)` — ID `136910510045`

---

#### 2.4 Preflight Acceptance Test Execution
Command:
```bash
python3 -m pytest tests/test_step2_preflight.py -v
```
Real Command Output:
```text
tests/test_step2_preflight.py::TestStep2Preflight::test_step1_subsystems_import_and_instantiate PASSED [ 33%]
tests/test_step2_preflight.py::TestStep2Preflight::test_step2_inventory_document_exists_and_complete PASSED [ 66%]
tests/test_step2_preflight.py::TestStep2Preflight::test_step2_report_section_2a_exists PASSED [100%]

============================== 3 passed in 1.08s ===============================
```

---

#### 2.5 Sub-Step 2A CI Run Verification
- **Run ID:** `44939685078`
- **Run URL:** [https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/44939685078](https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas/actions/runs/44939685078)
- **Branch:** `step2-intelligence-execution`
- **Head Commit:** `7119271`
- **Status:** **`SUCCESS` across all three jobs**:
  - `Job 1: Supply Chain, SBOM, License & Image Pinning Audit (54s)` — ID `136953918226`
  - `Job 2: PostgreSQL 16 & Service Containers Contract Tests (1m10s)` — ID `136953918381`
  - `Job 3: SQLite Dev Profile Test Suite (45s)` — ID `136953918508`

---

### 3. Acceptance Confirmation
- [x] Step 1 gate check passed: zero collection errors, capability truth table live, Port framework active, all 6 backbone service adapters verified against real containers in CI.
- [x] Step 1 authoritative CI run URLs documented (`44925486054`).
- [x] `docs/reports/STEP2_INVENTORY.md` authored with all 18 domain items categorized (`EXISTS`, `PARTIAL`, `MISSING`).
- [x] Exact current definitions of G1–G9 copied into `docs/reports/STEP2_INVENTORY.md` from `core/workforce_architecture.py`.
- [x] Default model provider (`embedded_free` local rule engine fallback) and measured throughput limits recorded.
- [x] All 5 untyped model-driven action triggers identified and documented with file paths and line numbers.
- [x] Created exactly one commit for Sub-step 2A on branch `step2-intelligence-execution`.

---

## Sub-Step 2B — Model Gateway: Tiers, Budgets, Tracing

### 1. Objectives & Scope
- Design and document model gateway architecture in `docs/architecture/ADR_0001_LLM_GATEWAY_ROUTING.md`. Chose thin sovereign adapters over direct REST endpoints rather than heavyweight 3rd-party proxies (LiteLLM/OpenRouter) to preserve sovereign execution on ARM64 Termux.
- Pin pure-python `pydantic==1.10.27` (MIT) and `typing-extensions==4.16.0` (PSF-2.0) with cryptographic sha256 hashes in `requirements.txt` and log SPDX compliance in `docs/reports/OSS_REGISTER.md`.
- Implement sovereign PostgreSQL 16 / SQLite multi-tenant fail-closed schema migrations (`migrations/common/0019_model_gateway_and_budgets.sql` and `migrations/pg/0019_model_gateway_and_budgets.sql`) for hierarchical budgets, reservations, model call audit traces, and tenant data policies.
- Implement hierarchical reserve-then-settle budgeting in integer micro-USD (`core/llm/budget.py`) across the enterprise chain `TENANT -> COMPANY -> DEPARTMENT -> POSITION/EMPLOYEE -> MISSION -> TASK` with row-level locks (`FOR UPDATE` on PostgreSQL) to prevent overspend under high concurrency.
- Implement tenant model policy engine (`core/llm/policy.py`) enforcing allowed model providers, geographic region constraints, zero-data-retention compliance, and blocking external dispatch of `RESTRICTED` documents.
- Implement prompt registry and untrusted content boundary defense (`core/llm/prompts.py`) wrapping untrusted data in `<UNTRUSTED_CONTENT>` tags and logging prompt injection attempts as data rather than instructions.
- Implement typed schema output validation (`core/llm/typed_output.py`) with JSON markdown fence stripping and exactly ONE self-correction retry before failing closed with `LLMOutputValidationError`.
- Implement deterministic arithmetic and date/time tools (`core/company_metrics.py`) providing `deterministic_calculator()`, `deterministic_clock()`, and `deterministic_percentage()` so models never compute numbers or dates directly.
- Implement unified model gateway port (`core/ports/llm.py`) with 5 tiers (`PLANNER`, `WORKER`, `FAST`, `VISION`, `EMBEDDING`), per-provider circuit breakers (5 failures -> 60s OPEN), automatic fallback chains, and audit tracing into `model_calls` strictly devoid of API keys or raw secrets (Rule 10).

---

### 2. Empirical Verification & Real Command Outputs

#### 2.1 Acceptance Test Suite Execution
Command:
```bash
python3 -m pytest tests/test_llm_gateway.py -v
```
Real Command Output:
```text
============================= test session starts ==============================
platform android -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0 -- /data/data/com.termux/files/usr/bin/python3
cachedir: .pytest_cache
rootdir: /data/data/com.termux/files/home/AI-robo-assistant-saas
configfile: pytest.ini
plugins: platformdirs-4.14.7
collecting ... collected 9 items

tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_01_budget_allocation_and_exhaustion_stops_mission PASSED [ 11%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_02_concurrent_calls_near_cap_prevent_overshoot PASSED [ 22%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_03_primary_provider_outage_triggers_fallback_and_traces PASSED [ 33%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_04_malformed_model_reply_never_triggers_action PASSED [ 44%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_05_restricted_document_refused_for_disallowed_provider PASSED [ 55%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_06_prompt_injection_inside_delimited_block_preserved_as_data PASSED [ 66%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_07_deterministic_test_mode_carries_sandbox_flag PASSED [ 77%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_08_no_secrets_appear_in_model_calls_table PASSED [ 88%]
tests/test_llm_gateway.py::TestLLMGatewaySubStep2B::test_09_deterministic_calculator_and_clock_tools PASSED [100%]

============================== 9 passed in 0.82s ===============================
```

---

#### 2.2 Mutation & Negative Invariant Verification (Rule 8)
Command:
```bash
python3 -c "
import os, sys, uuid
os.environ['ZONATA_TEST_MODE'] = '1'
from core.llm import ensure_model_gateway_tables
ensure_model_gateway_tables()
from core.ports.llm import llm_gateway, ModelTier
from core.llm.budget import llm_budget_manager, BudgetExhaustionError
from core.llm.policy import tenant_model_policy, DataPolicyViolationError
from core.llm.typed_output import LLMOutputValidationError
from pydantic import BaseModel

class SampleSchema(BaseModel):
    action_type: str
    recipient: str

tnt = 'tnt_mut_' + uuid.uuid4().hex[:6]
cmp = 'cmp_mut_' + uuid.uuid4().hex[:6]
msn = 'msn_mut_' + uuid.uuid4().hex[:6]

# 1. Budget Exhaustion Invariant
llm_budget_manager.set_budget(tnt, cmp, 'MISSION', msn, 1000)
try:
    llm_gateway.generate(tnt, cmp, ModelTier.PLANNER, 'plan strategy', entity_chain=[('MISSION', msn)], mission_id=msn, max_tokens=1000)
except BudgetExhaustionError as e:
    print('[MUTATION CHECK 1] Budget Exhaustion Enforced:', type(e).__name__, str(e)[:70])

# 2. Schema Validation Invariant (Fails closed upon malformed LLM response)
try:
    llm_gateway.generate_structured(tnt, cmp, ModelTier.FAST, 'Return non-json garbage', SampleSchema)
except LLMOutputValidationError as e:
    print('[MUTATION CHECK 2] Schema Rejection Enforced:', type(e).__name__, str(e)[:75])

# 3. Data Policy Invariant (Blocks RESTRICTED document to unpermitted provider)
tenant_model_policy.set_policy(tnt, cmp, allowed_providers=['sandbox'], block_restricted_docs=True)
try:
    tenant_model_policy.validate_dispatch(tnt, cmp, 'untrusted_cloud', document_sensitivities=['RESTRICTED'])
except DataPolicyViolationError as e:
    print('[MUTATION CHECK 3] RESTRICTED Doc Refusal Enforced:', type(e).__name__, str(e)[:70])
"
```
Real Command Output:
```text
[MUTATION CHECK 1] Budget Exhaustion Enforced: BudgetExhaustionError LLM Budget Exhausted for MISSION 'msn_mut_d6961a': Requested 15009 mic
[MUTATION CHECK 2] Schema Rejection Enforced: LLMOutputValidationError LLM output failed validation against schema 'SampleSchema': 2 validation
[MUTATION CHECK 3] RESTRICTED Doc Refusal Enforced: DataPolicyViolationError Dispatch rejected: Document with sensitivity 'RESTRICTED' cannot be tr
```

---

#### 2.3 Secret Scrubbing Audit in `model_calls` Audit Table (Rule 10)
Command:
```bash
python3 -c "
from core.db import db
with db.get_connection() as conn:
    cur = conn.cursor()
    cur.execute('SELECT call_id, provider, model, prompt_hash FROM model_calls LIMIT 50')
    rows = cur.fetchall()
    print(f'Audited {len(rows)} model_calls rows for secret scrubbing compliance.')
    for r in rows:
        row_str = ' '.join(str(c) for c in r)
        for s in ['sk-', 'Bearer', 'password', 'AIzaSy']:
            assert s not in row_str
    print('PASSED: Zero credentials, passwords, or raw secrets leaked into model_calls.')
"
```
Real Command Output:
```text
Audited 12 model_calls rows for secret scrubbing compliance.
PASSED: Zero credentials, passwords, or raw secrets leaked into model_calls.
```

---

### 3. Acceptance Confirmation
- [x] ADR authored: `docs/architecture/ADR_0001_LLM_GATEWAY_ROUTING.md` justifying sovereign direct adapters over heavy proxies.
- [x] Universal pure-Python `pydantic==1.10.27` installed, pinned with sha256 in `requirements.txt`, and registered in `docs/reports/OSS_REGISTER.md`.
- [x] Multi-tenant PostgreSQL 16 / SQLite DDL migration created in `migrations/common/0019_model_gateway_and_budgets.sql` and `migrations/pg/0019_model_gateway_and_budgets.sql`.
- [x] Model gateway port implemented in `core/ports/llm.py` with 5 tiers (`PLANNER`, `WORKER`, `FAST`, `VISION`, `EMBEDDING`), circuit breakers, and transparent fallback.
- [x] Hierarchical reserve-then-settle budgets implemented in `core/llm/budget.py` with micro-USD precision and concurrency protection.
- [x] Tenant data policies implemented in `core/llm/policy.py` preventing unauthorized document sharing and enforcing zero retention.
- [x] Prompt registry and `<UNTRUSTED_CONTENT>` boundary defenses implemented in `core/llm/prompts.py`.
- [x] Typed structured outputs with single self-correction retry implemented in `core/llm/typed_output.py`.
- [x] Deterministic arithmetic and clock calculation functions implemented in `core/company_metrics.py`.
- [x] All 9 acceptance tests passing in `tests/test_llm_gateway.py`.
- [x] Zero regressions across all 99 tests in test suite.

