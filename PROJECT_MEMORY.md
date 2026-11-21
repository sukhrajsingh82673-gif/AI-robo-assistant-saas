# Project Memory: ZONATA Enterprise AI Operating System & Agent Factory

## Environment
- **Platform:** Android / Termux (Linux ARM64, Sovereign T0 Mode)
- **Active Workspace:** `/data/data/com.termux/files/home/AI-robo-assistant-saas`
- **Active Git Branch:** `step1-foundation-backbone`
- **Remote Origin:** `https://github.com/sukhrajsingh82673-gif/AI-robo-assistant-saas.git`
- **Execution Status:** Restricted Pilot (Simulation on Android/Termux hardware; not public GA). GitHub Actions CI is the authoritative verification source of truth.

## Architectural Principles & Invariants
1. **Truth Rule:** Nothing reports success it did not achieve. Unconfigured -> `NOT_CONFIGURED`, unbuilt -> `NOT_IMPLEMENTED`. Test fakes permitted only under `ZONATA_TEST_MODE=1` with `sandbox: true`.
2. **Reality Ladder:** Status reflects external confirmation only (e.g., SMTP accepted -> `ACCEPTED_BY_PROVIDER`, webhook -> `DELIVERED`, S3 read-back SHA256 match -> `STORED`).
3. **Port Pattern:** External services sit behind typed `Port -> RealProvider -> NotConfiguredProvider -> SandboxProvider`.
4. **License Boundaries:** Dependency SPDX licenses tracked in `docs/reports/OSS_REGISTER.md`. AGPL/SSPL/BSL services run strictly as isolated network boundaries.
5. **Multi-Tenant Row-Level Security:** Every table carries `tenant_id` and `company_id`. RLS enforced on PostgreSQL 16.
6. **Deterministic Financial Ledger:** Integer minor units, zero-balance constraint per currency, immutable posted entries via triggers, reversing entries for corrections.
7. **Declarative Industry Packs:** Industry logic defined entirely in `zonata.industry-pack/v1` data schemas and UN ISIC Rev. 4 taxonomy; zero hardcoded branching on industry names.

## Completed Milestones

### OpenCode Step 1 — Truth Foundation and Backbone (In Progress)
- **Sub-Step 1A (Inventory & Repository Integrity):** COMPLETE
  - Conducted comprehensive repository inventory across domains 1C to 1I in `docs/reports/STEP1_INVENTORY.md`.
  - Restored tracking of `agent_factory/build/` (`compiler.py`, `governed_call.py`, `pipeline.py`, `signer.py`) in `.gitignore`.
  - Added missing `from typing import Any` import to `agent_factory/capabilities/browser_gateway.py`.
  - Eradicated all hardcoded `/data/data/com.termux/...` and `/root/roboassistant` paths across all Python files; implemented portable dynamic `$PREFIX` resolution.
  - Aligned settings registry test assertions to authoritative count (214 settings, 46 categories, 16 sections).
  - Untracked `storage/roboassistant.db` from git, added to `.gitignore`, and authored `scripts/seed_dev_db.py` to deterministically synthesize dev databases from migrations.
  - Performed full git history secret audit (reporting commit and file only per Rule 10) and cataloged owner rotation recommendations.
  - Upgraded `package.json` `build` script to execute `node --check web/*.js && python3 -m compileall -q .`.
  - Verified 2,133 tests collected with 0 collection errors.
  - Documented empirical command output in `docs/reports/STEP1_REPORT.md`.

## Active Roadmap (Step 1 Sub-Steps)
- [x] **1A:** Inventory and repository integrity
- [ ] **1B:** Supply chain, CI and honest claims
- [ ] **1C:** Capability truth table and the Port framework
- [ ] **1D:** Honest adapters with real providers
- [ ] **1E:** Document and file backbone
- [ ] **1F:** Folio, evidence and export packs
- [ ] **1G:** Ledger kernel
- [ ] **1H:** Industry Pack framework
- [ ] **1I:** Always-on baseline
- [ ] **1J:** Step 1 qualification scenario
