# Project Memory: ZONATA Agent Factory

## Environment
- **Platform:** Android / Termux (Linux ARM64)
- **Active Workspace:** `/data/data/com.termux/files/home/AI-robo-assistant-saas`
- **Git Branch:** `agent-factory/audit` (Audited Commit: `6003d16`)
- **GitHub Account:** `sukhrajsingh82673-gif` (Active PAT configured via `gh`)

## Architecture & Roadmap
- Operating in accordance with `EXECUTIVE_ARCHITECTURE.md` and `OPENCODE_MASTER_IMPLEMENTATION_PROMPT.md`.
- Target: Autonomous ZONATA Agent Factory manufacturing governed AI agents via LangGraph spec compilation, deterministic certification gates, and 24 `af_*` tables.

## Completed Milestones
- **Phase 1 Audit (Completed 2026-11-19):**
  - Read-only repository audit completed without touching application code or main branch.
  - Automated scanner run excluding specification files: 11 routes, 194 tables, 164 test files.
  - Executed real test suites: `test:ui` (passed), `test:assistant` (passed), `test:company` (passed), `test_a2a_interoperability` (passed).
  - Executed 4 live governance probes:
    1. AuthorityGateway / ActionGateway: Blocked SSRF attempt, permitted safe registered action.
    2. EvidenceLedger: Sealed 3 entries, verified Merkle root, verified tamper detection and fork isolation.
    3. KillSwitchMatrix: Verified agent-level execution halt and clean deactivation.
    4. Multi-Tenant Isolation: Verified cross-tenant query boundary returns 0 records.
  - Deliverables generated under `docs/agent-factory/audit/`:
    - `SUMMARY.md`
    - `INVENTORY.md`
    - `PORT_MAP.md`
    - `REUSE_QUESTIONS.md`
    - `API_CONVENTIONS.md`
    - `LICENCE_GATE.md`
    - `SECURITY_HYGIENE.md`

## Next Milestone (Awaiting Human Gate D1 Approval)
- **Phase 2: Foundation & Governance:**
  - Create branch `agent-factory/phase-2`.
  - Apply core 24-table schema (`001_agent_factory_core.sql`) via migration manager.
  - Implement ports, adapters, and `transition()` helper with evidence-before-effect guarantees.
