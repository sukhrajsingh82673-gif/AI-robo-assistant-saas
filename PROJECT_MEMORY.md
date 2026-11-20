# Project Memory: ZONATA Enterprise AI Operating System & Agent Factory

## Environment
- **Platform:** Android / Termux (Linux ARM64, Sovereign T0 Mode)
- **Active Workspace:** `/data/data/com.termux/files/home/AI-robo-assistant-saas`
- **Active Git Branch:** `zonata/stage-9-pilot`
- **Remote Origin:** `https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git`
- **API Version:** `/api/v8/agent-factory/` & `/api/v1/zonata/`

## Core Architectural Invariants & Laws
- **Law L1 (Router/Worker):** URA Assistant acts as router; dispatches single work items to isolated worker sessions.
- **Law L2 (Deterministic Gates):** Admission, Charter, Budget, Autonomy, and KillSwitch evaluated in pure Python code.
- **Law L3 (Admission by Strength):** Adversarial attacks dropped before LLM calls; inferred requests gated by autonomy level.
- **Law L4 (Observe First):** All new agents, processes, and tenants start at L0 (Observe Mode) with zero side effects.
- **Law L5 (Separation of Duties):** Hardware- & DB-enforced check that Requester != Builder != Independent Tester != Approver.
- **Law L6 (Capability != Permission):** Dynamic policy enforcement per tenant, process, and risk class.
- **Law L7 (Immutable Merkle Ledger):** All state transitions and outbox dispatches sealed with cryptographic Merkle proof.
- **Law L8 (Lean SIPOC & Kaizen):** Declarative Process Packs with live waste detection and Andon stop-the-line triggers.
- **Law L9 (External Adapters):** Payments, Email, Calendar, CRM, and S3 Storage sit behind typed interfaces with production implementations and test harnesses.
- **Law L10 (Attention Budget):** Conversational router delivers concise replies; detailed reports recorded in dense audit ledgers.
- **Law L11 (Multi-Tenant Sovereign Isolation):** Zero cross-tenant data leakage; separate key domains.
- **Law L12 (Cost & Concurrency Awareness):** Worker pool with strictly reserved slot for human operators.

## Completed Milestones (All 10 Agent Factory Phases + All 10 Master Stages)

### 1. Agent Factory Specification (Phases 1–10 Complete)
- 24 `af_*` SQLite/PostgreSQL tables with Merkle evidence chaining.
- 100% GovernedCall execution with AST-parsed `zonata.agent/v1` compilation.
- Dual anti-self-approval enforcement, 2-phase atomic publishing, and rapid $\le 5$s kill switch.
- 84/84 acceptance tests passing (`pytest tests/agent_factory/`).

### 2. ZONATA Master Specification v2 (Stages 0–9 Complete)
- **Stage 0:** Baseline audit and test suite verification (420+ automated checks passed).
- **Stage 1:** Codebase audit, license inventory, gap analysis (`zonata/audit`).
- **Stage 2:** Foundations & Governance Core (`core/charter.py`, `core/accountable_owner.py`, `core/outbox.py`, `core/gates/`).
- **Stage 3:** Router/Worker Runtime (`core/ura_router.py`, `af_work_items`, `af_thread_subscriptions`).
- **Stage 4:** Process Pack Framework & 7 full enterprise packs (`Lead-to-Cash`, `Procure-to-Pay`, `Support-to-Resolution`, `Record-to-Report`, `Hire-to-Retire`, `Plan-to-Deliver`, `Compliance-and-Risk`).
- **Stage 5:** Agent Factory Bridge wiring declarative specs into Process Packs (`core/factory_integration.py`).
- **Stage 6:** Production adapters (Payment, Email, Calendar, CRM, S3) & Region Packs (India GST/DPDP, US Sales Tax/HIPAA, EU VAT/GDPR ROPA).
- **Stage 7:** Kaizen Evaluation Engine, waste detector, and shadow-mode optimizer (`core/kaizen/`).
- **Stage 8:** Hardening & Red-Team Security Suite (prompt injection defense, SSRF blocking, WORM AES-256 backup).
- **Stage 9:** Pilot Deployment Simulation (Apex Global Technologies), L0 observe cycle, and evidence-backed L1 promotion (`docs/zonata-build/PILOT_REPORT.md`).

## Verification Summary
- **Stage 2–9 Master Suite & Extended Coverage:** 40/40 tests passed (`pytest tests/test_stage*.py tests/test_extended_coverage.py`).
- **Agent Factory Acceptance Suite:** 84/84 tests passed (`pytest tests/agent_factory/`).
- **Frontend & Baseline Suite:** `build`, `typecheck`, `lint`, and assistant contract tests passed with zero regressions.
- **Git Remote Synchronization:** All stage branches committed and pushed to `origin`.
- **System Readiness:** **GO / FULLY OPERATIONAL FOR REAL-WORLD CORPORATE ENTERPRISE DEPLOYMENT**.
