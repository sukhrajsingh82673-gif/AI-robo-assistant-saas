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
- [ ] **1G:** Ledger kernel
- [ ] **1H:** Industry Pack framework
- [ ] **1I:** Always-on baseline
- [ ] **1J:** Step 1 qualification scenario

## Supervision Corrections (2026-11-21)
- Fixed a step-1 regression: missing `import os` in `src/services/agent-engine/agent_engine.py` (caused all 121 full-suite errors).
- Removed the hardcoded KMS fallback master key; an unconfigured KMS now reports `NOT_CONFIGURED` instead of a false `OK`.
- Made LLM, search, payments, secrets, observability, workflow-engine, and MCP probes perform real checks. MCP now reads ZONATA's own `mcp_servers` registry, not an external Antigravity directory.
- Corrected report claims: `2,133` is the collection count, not a full-suite pass count. Full local run before the import fix: `1,958 passed, 59 failed, 31 skipped, 121 errors`. Post-fix targeted run: `33 passed, 4 skipped`.
