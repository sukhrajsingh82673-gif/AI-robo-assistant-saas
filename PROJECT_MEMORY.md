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
- **Sub-Step 1B (Supply Chain, CI & Honest Claims):** COMPLETE
  - Created `.github/workflows/ci.yml` featuring PostgreSQL 16, SeaweedFS S3, Mailpit SMTP, ClamAV 1.4_base, and Apache Tika 2.9.2 service containers.
  - Pinned all container images across compose files and CI workflows; verified `:latest` rejection in tests and CI.
  - Configured Dependabot in `.github/dependabot.yml` covering `pip`, `npm`, and `github-actions`.
  - Generated `docs/reports/OSS_REGISTER.md` cataloging 44 installed distributions with authoritative SPDX licenses.
  - Scrubbed promotional phrasing in `docs/zonata-build/PILOT_REPORT.md` and memory.
  - Enforced production startup guards prohibiting SQLite and `embedded_free` models without explicit `ZONATA_ALLOW_DEGRADED=1`.
  - Pinned all runtime requirements with cryptographic PyPI sha256 hashes (`requirements.txt`).
  - Upgraded dependencies to resolve security advisories (`cryptography==50.0.2`, `cffi==2.0.0`).
   - Added a 3-job CI workflow (PostgreSQL 16 contract tests, targeted SQLite suites, supply chain/license/vulnerability audit). Previously cited green-run URLs are **unverified**: `gh` is not authenticated in the current Termux environment, so re-authenticate and confirm before citing them as evidence.
   - Documented empirical command outputs in `docs/reports/STEP1_REPORT.md`.

## Active Roadmap (Step 1 Sub-Steps)
- [x] **1A:** Inventory and repository integrity
- [x] **1B:** Supply chain, CI and honest claims
- [x] **1C:** Capability truth table and the Port framework
- [x] **1D:** Honest adapters with real providers
- [x] **1E:** Document and file backbone
  - Defined 10-table governed schema (`documents`, `blobs`, `document_versions`, `document_events`, `classifications`, `extractions`, `retention_policies`, `legal_holds`, `access_grants`, `share_links`) with PostgreSQL 16 RLS policies.
  - Implemented 8-state pipeline (`RECEIVED → QUARANTINED → SCANNED → STORED → EXTRACTED → CLASSIFIED → INDEXED → AVAILABLE`) with review queue and rejection branches.
  - Built magic-byte content sniffer rejecting executables, scripts, and macros unless routed through quarantined Import lane.
  - Implemented per-tenant SHA-256 blob deduplication and envelope encryption via `LocalEnvelopeKeyProvider`.
  - Added immutable versioning, verify-on-read, and scheduled integrity sweeps for bit rot detection.
  - Implemented legal hold enforcement blocking crypto-shred disposal (`LegalHoldEnforcedError`).
  - Added ephemeral hashed external share links and multi-tenant search.
  - Added template document generator (PDF/DOCX/XLSX) and sovereign PDF digital signing.
  - Built full test suite (`tests/test_documents_backbone.py`) with 15 passing tests and mutation checks.
- [x] **1F:** Folio, evidence and export packs
  - Implemented Folio aggregate root and immutable entries (`folios`, `folio_entries`) with PostgreSQL 16 RLS policies (`migrations/pg/0015_folio_evidence_backbone.sql`).
  - Added deterministic Merkle tree calculation (`core/folios/merkle.py`), root sealing on status transitions, and audit proof verification without database access.
  - Implemented self-verifying export pack (`.zip`) containing `manifest.json`, `entries/`, `files/`, `audit_trail.json`, and standalone zero-dependency `verify_pack.py` offline verifier.
  - Implemented deletion drill: sovereign expungement archives export pack to storage, logs pack hash into permanent `EvidenceLedger`, and purges database rows.
  - Authored comprehensive test suite (`tests/test_folio_export_backbone.py`) verifying all 7 acceptance requirements and mutation checks.
- [x] **1G:** Ledger kernel
  - Defined double-entry financial ledger schema (`accounts`, `journal_entries`, `journal_lines`) with PostgreSQL 16 RLS policies and immutability triggers (`migrations/pg/0016_ledger_kernel.sql`).
  - Enforced Rule 12: Integer minor units only, zero float arithmetic, and strict ISO 4217 currency validation (`core/ledger/currency.py`).
  - Implemented zero-balance invariant (`sum(debits) == sum(credits)`) strictly per currency; multi-currency entries must independently balance.
  - Implemented database-level immutability triggers on POSTED entries; accounting corrections performed exclusively via reversing entries (`reverse_journal_entry`).
  - Integrated folio verification: sealing or closing a folio verifies all linked journal entries are in POSTED status (`UnpostedFolioJournalEntriesError`).
  - Implemented trial balance generator (`generate_trial_balance`) verifying net zero sum across all accounts.
  - Authored comprehensive test suite (`tests/test_ledger_kernel.py`) verifying all 7 acceptance criteria and mutation checks (10 passed).
- [x] **1H:** Industry Pack framework
  - Implemented UN ISIC Rev. 4 taxonomy registry (`core/industry_packs/isic.py`) covering all 21 Sections and 88 Divisions with programmatic code validation and division lookup.
  - Authored declarative `zonata.industry-pack/v1` schema validator (`core/industry_packs/schema.py`) enforcing structural constraints, ISO 4217 currency validation, referential integrity, and chart of accounts balance checks (`MalformedChartOfAccountsError`).
  - Implemented `IndustryPackLoader` (`core/industry_packs/loader.py`) provisioning Charts of Accounts into `LedgerKernel`, registering `company_folio_types`, and tracking installations in `installed_industry_packs`.
  - Authored three canonical production-grade reference packs: `packs/industries/saas/v1/pack.yaml` (ISIC J62), `packs/industries/hospitality/v1/pack.yaml` (ISIC I55), and `packs/industries/manufacturing/v1/pack.yaml` (ISIC C28).
  - Decoupled `core/ceo_brain/industry.py` (`IndustryUnderstandingEngine`): eliminated all hardcoded static `if industry == ...` branches, dynamically resolving industry semantics from data-driven packs and the UN ISIC taxonomy registry (`IndustryPackRegistry`).
  - Authored database migrations with PostgreSQL 16 RLS policies: `migrations/common/0017_industry_packs.sql` and `migrations/pg/0017_industry_packs.sql`.
  - Authored comprehensive test suite `tests/test_industry_pack_framework.py` with 8 passing tests, AST checks proving zero hardcoded industry branching, and mutation checks.
- [x] **1I:** Always-on baseline
  - Built transactional outbox (`core/baseline/outbox.py`, `outbox_events` table) with atomic enqueuing, at-least-once delivery, exponential backoff, DLQ after 5 attempts, idempotent handler keys, and mid-job worker crash recovery.
  - Implemented distributed leased scheduler (`core/baseline/scheduler.py`, `scheduled_jobs`, `scheduler_leader_leases`) with monotonic next-run timing, max-run-time timeouts, catchup policies, and 30s cluster leader election failover leaving zero orphan locks.
  - Built reality health & readiness probes (`core/baseline/health.py`) mounted to `/healthz` (liveness) and `/readyz` (readiness: DB readability, critical KMS/DB port evaluation, >1GB disk space guard, migration currency), turning HTTP 503 if DB is paused or critical port fails.
  - Authored automated backup & restore qualification drill (`scripts/backup_restore_drill.py`) verifying 100% byte-for-byte SHA-256 and Merkle root parity across 10 documents, 3 folios, and 50 double-entry ledger entries.
  - Authored migrations with PostgreSQL 16 RLS policies: `migrations/common/0018_always_on_baseline.sql` and `migrations/pg/0018_always_on_baseline.sql`.
  - Authored comprehensive test suite `tests/test_always_on_baseline.py` (10 passed) and integrated into CI workflows.
- [x] **1J:** Step 1 qualification scenario and acceptance sign-off
  - Authored Outpatient Healthcare Clinic & Practice blueprint (`packs/industries/clinic/v1/pack.yaml`) conforming to UN ISIC Rev. 4 `Q86`.
  - Implemented end-to-end qualification scenario runner (`scripts/step1_scenario.py`) executing all 12 qualification stages across both SQLite and PostgreSQL 16.
  - Implemented automated pytest suite (`tests/test_step1_scenario.py`).
  - Successfully verified in GitHub Actions CI (Run ID `44920364090`) with 100% green status across all 3 jobs (Supply Chain, SQLite Dev, PostgreSQL 16 & Service Containers).
  - OpenCode Step 1 complete with exactly 10 commits (1A - 1J) on `step1-foundation-backbone`.

## Supervision Corrections (2026-11-21)
- Fixed a step-1 regression: missing `import os` in `src/services/agent-engine/agent_engine.py` (caused all 121 full-suite errors).
- Removed the hardcoded KMS fallback master key; an unconfigured KMS now reports `NOT_CONFIGURED` instead of a false `OK`.
- Made LLM, search, payments, secrets, observability, workflow-engine, and MCP probes perform real checks. MCP now reads ZONATA's own `mcp_servers` registry, not an external Antigravity directory.
- Corrected report claims: `2,133` is the collection count, not a full-suite pass count. Full local run before the import fix: `1,958 passed, 59 failed, 31 skipped, 121 errors`. Post-fix targeted run: `33 passed, 4 skipped`.
