# OpenCode Step 1 — Comprehensive Repository Inventory

**Repository:** `sukhrajsingh82673-gif/AI-robo-assistant-saas`  
**Branch:** `step1-foundation-backbone`  
**Date:** 2026-11-21  
**Sub-step:** 1A Inventory and Repository Integrity  

---

## Executive Summary

Before implementing Step 1 (Truth foundation and the Document / File / Folio / Ledger backbone), an exhaustive inventory of the repository was conducted across `core/`, `agent_factory/`, `migrations/`, `packs/`, `scripts/`, `web/`, and `tests/`.

This inventory maps existing capabilities, database tables, test coverage, and gap status (`EXISTS`, `PARTIAL`, `MISSING`) against requirements 1C through 1I. In accordance with Standing Rule 3 (*Reuse before writing*), existing modules will be extended or refactored rather than duplicated.

---

## Domain Analysis & Requirements Mapping

### 1C — Capability Truth Table and the Port Framework

*Requirements:* Base `Port`, typed `ProviderResult`, capability probe, `/api/system/capabilities`, AST lint test, read-before-promise.

| Component | Path | Real Behavior / Role | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Domain Ports | `core/adapters/ports.py` | Abstract domain ports (`PaymentPort`, `EmailPort`, `CalendarPort`, `CRMPort`, `StoragePort`) | None | Yes | `PARTIAL` |
| Factory Ports | `agent_factory/ports/__init__.py` | Security/governance ports (`AuthorityPort`, `PolicyPort`, `EvidenceLedgerPort`, `KillSwitchPort`, etc.) | None | Yes | `PARTIAL` |
| Capability Registry | `agent_factory/capabilities/` | Gateway adapters (`mcp_gateway.py`, `browser_gateway.py`, `a2a_gateway.py`) | `af_capability` | Yes | `PARTIAL` |
| Generic Port Base | `core/ports/base.py` | Unified generic `Port` base class and standard `ProviderResult` dataclass | None | No | `MISSING` |
| Capability Probe | `core/capability_probe.py` | Live diagnostic probe verifying all external integrations | None | No | `MISSING` |
| Reality Probe Script | `scripts/reality_probe.py` | Standalone CLI probe tool reporting capability truth table | None | No | `MISSING` |
| Capabilities API | `GET /api/system/capabilities` | Admin endpoint exposing truthful capability statuses | None | No | `MISSING` |
| AST Anti-Fake Linter | `tests/test_truth_linter.py` | AST checker blocking fake statuses (`DELIVERED`, `STORED`) without receipts | None | No | `MISSING` |
| Read-Before-Promise | Agent Factory / AI CEO planner | Check capability status before planning actions | None | No | `MISSING` |

*Gaps & Action Plan:* Create `core/ports/base.py` with typed `ProviderResult`. Implement `core/capability_probe.py` and `scripts/reality_probe.py`. Add `/api/system/capabilities` route and AST lint test in 1C.

---

### 1D — Honest Adapters with Real Providers

*Requirements:* Replace fake behavior; real SMTP with TLS and delivery webhooks; IMAP/webhook email intake; CalDAV & Google Calendar; S3-compatible storage with SHA-256 verification and short-lived pre-signed URLs; measured step cost.

| Capability | Module Path | Current Real Behavior | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Transactional Email | `core/adapters/providers.py` | Appends to in-memory list (`TransactionalEmailAdapter`); no TLS SMTP | None | Yes | `PARTIAL` |
| Email Inbound | None | No inbound email parser or IMAP polling | None | No | `MISSING` |
| Calendar Provider | `core/calendar_provider.py`, `core/adapters/providers.py` | Google Calendar integration exists; in-memory fallback | None | Yes | `PARTIAL` |
| Object Storage | `core/adapters/providers.py` | S3 compatible adapter with local envelope fallback; generates simulated R2 URLs | None | Yes | `PARTIAL` |
| Process Cost Meter | `core/process_packs/engine.py` | Steps track duration and cost, but historically used fixed step constants | `af_process_instances` | Yes | `PARTIAL` |
| Payments | `core/adapters/providers.py`, `core/connectors.py` | Sandboxed payment adapter with idempotency; Stripe/Razorpay connectors | `af_payment_transactions` | Yes | `EXISTS` (sandbox-only per spec) |

*Gaps & Action Plan:* Replace in-memory email sink with real SMTP provider (handling queue IDs, SPF/DKIM/DMARC status check, bounce/delivery webhooks). Add IMAP/webhook intake into document pipeline. Integrate CalDAV. Enforce S3 SHA-256 read-back verification and pre-signed GET/PUT.

---

### 1E — Document and File Backbone

*Requirements:* Governed multi-tenant document system; tables (`documents`, `document_versions`, `blobs`, `document_events`, `classifications`, `extractions`, `retention_policies`, `legal_holds`, `access_grants`, `share_links`); ClamAV quarantine; Apache Tika extraction; OCR; Presidio PII labelling; envelope encryption via `KeyPort`; WORM retention and crypto-shred; PostgreSQL FTS / pgvector; template DOCX/XLSX/PDF generation; PDF signing; prompt-injection delimiters.

| Component | Module Path | Current Real Behavior | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Enterprise Files Engine | `core/enterprise_files.py` | Metadata storage, categorization, duplicate SHA-256 detection, basic versioning | `enterprise_files` | Yes | `PARTIAL` |
| Company Files | `core/company_setup/schema.py` | Files registration during company setup with basic scan flags | `company_files` | Yes | `PARTIAL` |
| Corporate Data Plane | `core/corporate_data_plane.py` | Retention days, legal hold checks, row-level access control | `corporate_data_objects` | Yes | `PARTIAL` |
| Data Lifecycle Manager | `core/data_lifecycle_manager.py` | `set_legal_hold()` and `execute_verified_purge()` | `corporate_data_objects` | Yes | `PARTIAL` |
| Presidio DLP Engine | `core/presidio_dlp_engine.py` | Autonomous PII/PHI detection, anonymization, and tokenization | None | Yes | `EXISTS` |
| Tika / OCR Connector | `core/automation_fabric/enterprise_connectors.py` | `conn_apache_tika_ocr` connector with zip-bomb and path-traversal safety | None | Yes | `PARTIAL` |
| Key Management | `core/sovereign_key_manager.py`, `core/secret_vault.py` | AES-256-GCM tenant encryption keys | `sovereign_keys`, `secret_vault` | Yes | `PARTIAL` |
| Document Generator | `core/document_generator.py` | Native PDF document layout generation | None | Yes | `PARTIAL` |
| Normalized Documents Schema | None | Unified tables (`documents`, `document_versions`, `blobs`, `document_events`, `retention_policies`, `legal_holds`, `access_grants`, `share_links`) | None | No | `MISSING` |
| ClamAV Daemon Port | None | Antivirus scanner port communicating with ClamAV network service | None | No | `MISSING` |
| PDF Signing | None | PKCS#7 / PAdES digital signing using tenant key from KeyPort | None | No | `MISSING` |
| Prompt-Injection Guard | `core/coworker/defense_monitor.py` | Prompt injection detection; requires explicit untrusted boundary encapsulation | None | Yes | `PARTIAL` |

*Gaps & Action Plan:* Define unified normalized migration for documents, immutable versions, deduplicated blobs, and access grants with multi-tenant RLS. Implement `KeyPort` with `LocalEnvelopeKeyProvider`. Build quarantine pipeline with ClamAV service integration and Tika/OCR extraction provenance.

---

### 1F — Folio, Evidence, and Export Packs

*Requirements:* Governed subject folios (`OPEN`, `ON_HOLD`, `CLOSED`, `ARCHIVED`, `DISPOSED`); timeline entries sealing Merkle evidence; completeness checklists; offline ZIP export pack with `manifest.json`, index PDF, CSV ledger extracts, and Merkle proofs; standalone verifier script; company deletion flow wired to export receipts.

| Component | Module Path | Current Real Behavior | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Merkle Evidence Ledger | `core/evidence_service.py`, `core/evidence_ledger.py` | Cryptographically chained Merkle tree with SHA-256 back-hashes | `merkle_evidence_events` | Yes | `EXISTS` |
| Company Deletion Flow | `core/company_setup/service.py` | Multi-step deletion with recovery days, cancellation, and cascade purge | `company_deletion_requests` | Yes | `EXISTS` |
| Company Export Pack | `core/company_setup/export.py` | Generates PDF/JSON bundles with SHA-256 manifest for company data | None | Yes | `PARTIAL` |
| Generic Folio Framework | None (only in `workloads/hospitality.py`) | Cross-industry folio data model (`folios`, `folio_entries`, `folio_checklists`) | None | No | `MISSING` |
| Offline Export Pack Verifier | None | Standalone Python verifier script `scripts/verify_export_pack.py` | None | No | `MISSING` |

*Gaps & Action Plan:* Build `folios`, `folio_entries`, and `folio_checklists` schema and engine. Package offline verifiable ZIP export packs sealed with company signing key. Create `scripts/verify_export_pack.py` and enforce download receipt verification before company deletion.

---

### 1G — Ledger Kernel (Financial Record of Truth)

*Requirements:* `LedgerPort`; double-entry kernel (accounts, journals, journal_entries, lines, posting periods, currencies, exchange rates); integer minor units; balanced transactions (`sum(debits) == sum(credits)`); immutable triggers; reversing entries; SQL-computed trial balance & GL; reconciliation framework.

| Component | Module Path | Current Real Behavior | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Enterprise Finance Engine | `core/enterprise_finance.py` | Chart of accounts (COA 1010-6030), single-entry debit/credit recording | `finance_accounts`, `finance_transactions`, `finance_expenses` | Yes | `PARTIAL` |
| External Action Reconciliation | `core/reconciliation_engine.py` | Verifies external side effects against expected database mutations | `reconciliation_receipts` | Yes | `PARTIAL` |
| CEO Financial Analytics | `core/ceo_brain/finance.py` | High-level burn rate and runway projections | None | Yes | `PARTIAL` |
| Balanced Double-Entry Schema | None | Strict `journals`, `journal_entries`, `journal_lines` with deferred balance constraint | None | No | `MISSING` |
| Posting Periods & Locking | None | Closed period posting rejection | None | No | `MISSING` |
| Multi-Currency & Rates Table | None | ISO 4217 minor-unit exponents, exchange rate history | None | No | `MISSING` |
| SQL Trial Balance Report | None | Formal SQL-computed trial balance report | None | No | `MISSING` |
| Statement Reconciliation Engine | None | Bank statement import (CSV/OFX) with deterministic matching rules | None | No | `MISSING` |

*Gaps & Action Plan:* Write ADR comparing kernel against external ERP. Implement `LedgerPort` and PostgreSQL-authoritative double-entry schema with DB triggers enforcing zero balance, immutability, and closed period constraints.

---

### 1H — Industry Pack Framework

*Requirements:* Declarative `zonata.industry-pack/v1` (YAML + JSON Schema); UN ISIC Rev. 4 taxonomy generator; migrate 15 blueprints; 6 reference packs (`DRAFT` with citations); pack compiler and lifecycle (install, upgrade, uninstall); autonomy gating for uncertified packs.

| Component | Module Path | Current Real Behavior | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Process Pack Engine | `core/process_packs/engine.py` | Executes YAML process packs with deterministic gates and Andon stops | `af_process_packs`, `af_process_instances` | Yes | `EXISTS` |
| Process Pack YAMLs | `packs/` | 7 business packs + 3 regional compliance packs (India, US, EU) | None | Yes | `EXISTS` |
| KRA/KPI Benchmarks | `core/aic_ceo_kra_kpi.py` | Dynamic KRA/KPI generation across 6 hardcoded industry archetypes | `kpi_definitions`, `kpi_measurements` | Yes | `PARTIAL` |
| SOP Engine | `core/aic_ceo_sop.py` | Outcome-oriented SOP definitions and versioning | `sop_definitions`, `sop_versions` | Yes | `PARTIAL` |
| Industry Schema & Compiler | None | `zonata.industry-pack/v1` compiler validating taxonomy, folios, COA, KPIs | None | No | `MISSING` |
| UN ISIC Rev. 4 Generator | None | Machine-readable ISIC Rev. 4 taxonomy file and skeleton pack generator | None | No | `MISSING` |
| Pack Autonomy Gating | None | Prevents unreviewed packs from elevating autonomy above supervised | None | No | `MISSING` |

*Gaps & Action Plan:* Define `zonata.industry-pack/v1` schema. Fetch and commit official UN ISIC Rev. 4 taxonomy. Build compiler, skeleton generator for all ISIC divisions, and 6 reference packs at `DRAFT`. Eliminate hardcoded industry branching.

---

### 1I — Always-On Baseline

*Requirements:* Durable job runner on PostgreSQL (`FOR UPDATE SKIP LOCKED`, leases, retries, DLQ); leader lease scheduler; graceful shutdown (drain on SIGTERM); `/healthz`, `/readyz`, structured JSON logs; automated `pg_dump` backup & restore drill script.

| Component | Module Path | Current Real Behavior | Tables Found | Tested | Status |
| :--- | :--- | :--- | :--- | :---: | :---: |
| Transactional Outbox | `core/outbox.py`, `core/coworker/db_store_v2.py` | Outbox message dispatch with idempotency | `transactional_outbox`, `af_outbox`, `coworker_v2_outbox` | Yes | `EXISTS` |
| Distributed Leases | `core/coworker/durable_workflow.py` | Worker heartbeat and concurrency slot locks | `tenant_concurrency_leases`, `coworker_v2_leases` | Yes | `EXISTS` |
| Graceful Shutdown | `api_server.py` | SIGTERM/SIGINT handlers with 3.0s drain window | None | Yes | `EXISTS` |
| Health Probes | `api_server.py` | `/healthz` (liveness), `/readyz` (db readiness), `/livez` | None | Yes | `EXISTS` |
| Backup & WORM Security | `core/backup_security.py` | AES-256-GCM backup envelopes and ransomware detection | `disaster_recovery_manifests` | Yes | `EXISTS` |
| Logical Restore Drill | `scripts/reproducible_isolated_logical_restore_drill.py` | Live `pg_dump` and `psql` restore drill with Merkle verification | None | Yes | `EXISTS` |
| Durable Job Runner | None | PostgreSQL `SKIP LOCKED` worker queue with lease renewals and DLQ | None | No | `MISSING` |
| Cron Scheduler with Lease | `core/workforce_scheduler.py` | Schedule runner; requires leader election lease | `workforce_scheduler_queue` | Yes | `PARTIAL` |

*Gaps & Action Plan:* Unify background processing into a durable PostgreSQL job runner with `FOR UPDATE SKIP LOCKED`. Add leader lease to the scheduler. Run kill test drill in CI.

---

## 3. Keywords Search Audit

A comprehensive search for key domain terms across the entire repository confirmed the following:

| Keyword | Occurrences | Primary Files |
| :--- | :---: | :--- |
| `document` | 420+ | `core/enterprise_files.py`, `core/document_generator.py`, `core/corporate_data_plane.py` |
| `file` / `upload` | 650+ | `core/enterprise_files.py`, `core/company_setup/schema.py`, `api_server.py` |
| `storage` / `blob` | 380+ | `core/adapters/providers.py`, `core/enterprise_files.py` |
| `folio` | 14 | `workloads/hospitality.py` *(missing generic cross-industry folio framework)* |
| `ledger` / `journal` | 210+ | `core/evidence_service.py`, `core/enterprise_finance.py` |
| `evidence` | 510+ | `core/evidence_service.py`, `core/evidence_ledger.py`, `agent_factory/adapters/zonata.py` |
| `retention` / `hold` | 95+ | `core/corporate_data_plane.py`, `core/data_lifecycle_manager.py` |
| `export` | 180+ | `core/company_setup/export.py`, `core/company_setup/service.py` |
| `DLP` | 140+ | `core/presidio_dlp_engine.py`, `core/coworker/defense_monitor.py` |
| `blueprint` / `industry` | 320+ | `core/aic_ceo_kra_kpi.py`, `core/process_packs/loader.py`, `packs/` |
| `outbox` | 115+ | `core/outbox.py`, `core/coworker/db_store_v2.py` |
| `job` / `scheduler` | 290+ | `core/workforce_scheduler.py`, `core/ura_assistant_jobs.py` |
| `health` | 160+ | `api_server.py`, `core/employee_health_manager.py` |
| `backup` | 220+ | `core/backup_security.py`, `core/disaster_recovery.py` |

---

## 4. Verification Checkpoint

1. `agent_factory/build/` is now fully tracked in git after updating `.gitignore`.
2. Missing `from typing import Any` added to `agent_factory/capabilities/browser_gateway.py`.
3. Hardcoded `/data/data/com.termux/...` and `/root/roboassistant` paths eliminated from all `.py` files.
4. Settings registry test expectations updated to reflect authoritative count (214 total, 46 categories, 30 live, 178 coming soon, 4 hidden, 2 action).
5. `storage/roboassistant.db` untracked from git; `scripts/seed_dev_db.py` created and verified.
6. `package.json` `build` script updated to execute `node --check web/*.js && python3 -m compileall -q .`.
7. Test suite collection verifies 2,133 tests collected with 0 collection errors.
