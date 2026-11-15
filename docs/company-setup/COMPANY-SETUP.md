# ZONATA — Company Setup Program (Stages 0–6)

Living tracker. Updated at the end of every stage.
Branch: `ui-redesign` · Base commit at Stage 0: `cbff16b`

Rules of engagement for this program:

1. One stage at a time. Run it, report, stop, wait for "continue".
2. Read the real code first. Reuse existing components, routes, auth, design tokens, settings and translation systems.
3. Nothing is faked. Anything not yet real sits behind an adapter, is marked **Simulated** in development only, and is listed in the Stub Register below.
4. Keep dependencies light (Termux builds), migrations additive and reversible, Neon Postgres-safe, and never lose data for existing companies.

---

## 1. Stage status

| Stage | Scope | Status |
|---|---|---|
| 0 | Audit only (this document) | **Complete** |
| 1 | Data model, API, permissions, drafts | **Complete** |
| 2 | Company switcher + Add company page + entry points + i18n/RTL | **Complete** |
| 3 | Create new company (form, review, build workflow) | **Complete** |
| 4 | Add existing company (form, connections, ingestion shell, diagnosis) | **Complete** |
| 5 | Overview, edit, protected delete + export | **Complete** |
| 6 | Settings wiring, tests, abuse tests, hardening | **Complete** |

---

## 2. Stage 0 — repository audit (as found)

### 2.1 How companies are stored and switched today

**Storage.** Companies live in the `companies` table, defined twice (SQLite in `core/db.py:178`, Postgres in `migrations/pg/0001_postgresql_full_schema.sql:67`). Current columns:

```
company_id, tenant_id, name, country, industry, company_type (NEW|EXISTING),
status (DRAFT|ONBOARDING|OPERATIONAL|ATTENTION|SUSPENDED), currency, timezone,
revenue, cost, contribution, understanding_pct, operating_rules (JSON),
baseline_summary (JSON), created_at
```

Persistence is wrapped by `CompanyPortfolioManager` (`core/portfolio.py`), which registers `OperatingContext` objects (from `core/models.py`) and mirrors them to the DB. A per-tenant portfolio is resolved by `get_portfolio(tenant_id)` (`core/tenancy.py:430`) and cached inside `TenantRuntime`.

**Switching.**

- Frontend canonical context: `web/company_context.js` (`CanonicalCompanyContextManager`). Stores the active id in `localStorage['zonata_active_company_id']`, fetches `/api/companies`, broadcasts to subscribers, and binds a `<select>` (`#globalCompanySelector`) used by other screens.
- The selector includes an extra `All Companies (Group Portfolio)` option — this does **not** match the requested switcher behaviour.
- Sidebar switcher: `web/app_shell.js#openCompanySwitcher()` renders a modal list and falls back to a hardcoded `comp_primary / "ZONATA Technologies"` when `window.state.companies` is empty. That fallback is a fake company in the UI and must go.
- Switching calls `AppShell.selectCompany(...)` → writes the id, refreshes context, re-renders the current view.

**Companies screens.**

- `/company` → `web/company_workspace.js#renderCompanyManagementList()` (list/management).
- `/company/new` → `EntryFlows.renderWelcome` if present, otherwise the two-card mode selection, then a 14-stage onboarding workspace.
- `/company/<id>/<subtab>` → `renderCompanyOperatingWorkspace()` with subtabs (overview/organization/…).
- There is **no** `/company/<id>/edit`, no delete path, and the overview is a read-only telemetry pane.

**Create/activate API.**

- `POST /api/companies/<id>/draft` saves onboarding draft JSON to a per-tenant file (`_draft_path`), with id validation.
- `POST /api/companies/<id>/activate` and `POST /api/onboard` create the company. `/api/onboard` writes the company with the status supplied by the client (defaults to `OPERATIONAL`), i.e. a company is "operational" the moment it is created. There is no `CREATING` state and no build workflow.

**Gaps seen immediately:** no `title`/`description`/`owner`/`website`/revenue-period fields, no build-run table, no deletion request table, no status transition enforcement, no audit trail on company mutations, hardcoded fallback company in the switcher.

### 2.2 Multi-tenant model

- `tenants` table (`tenant_id`, `name`, `plan`, `status`), `users` (`tenant_id`, `email`, `role`), plus `pilot_organizations`.
- Token: HMAC-SHA256 signed `payload.signature`, payload = `{tenant_id, user_id, role, company_id, exp}`. Verification in `UserManager.verify_token` (`core/auth.py:548`), supporting key rotation via `get_verification_keys()`.
- Every request goes through `_get_auth_context()` (`api_server.py:635`), which fails closed: no token → no identity. A header or query `tenant_id` is only honoured if it matches the verified token.
- `_resolve_company_id()` (`api_server.py:676`) trusts only the token's `company_id`; a client-supplied `X-Company-ID` / `?company_id` is accepted only after a DB check that the company belongs to the authenticated tenant. Unknown ids fall back to `comp_<tenant>`.
- `TenantRuntime` (`core/tenancy.py`) scopes portfolio, CEO engine, ledger, workflows, schedules, meetings, assistant per tenant. Ledger files are per tenant (`storage/evidence/tenants/<safe_key>/audit_ledger.jsonl`).
- Role helpers: `can_approve` (OWNER, EXECUTIVE, GLOBAL_ADMIN), `can_mutate_governance` (OWNER, GLOBAL_ADMIN), `can_manage_credentials` (OWNER, GLOBAL_ADMIN), `can_execute_missions`, etc.

**Assessment:** tenant isolation primitives are real and fail closed. What is missing is company-level authorization (owner/admin allow-list per company) and any cross-tenant *mutation* test for the new endpoints.

### 2.3 Workflow / long-running job engine — is "Durable Temporal" real?

Yes, with a caveat.

- `core/durable_workflow_runtime.py` is a real stateful, checkpointed workflow engine (typed channels, interrupts, resource locks, evidence, kill-switch) backed by `workflows`, `workflow_runs`, `workflow_checkpoints`, `workflow_events`, `workflow_approvals`, `workflow_resource_locks`.
- `core/temporal_durable_execution_runtime.py` is an embedded DB-backed durable execution layer (its own `temporal_*` tables, idempotency keys, compensations, worker/task-queue registry).
- `GET /api/temporal/clusters` reports honestly: it lists an external Temporal cluster only if `TEMPORAL_HOST` is set, otherwise the embedded engine. It explicitly does not invent server/SDK versions.
- The UI entry `web/temporal_workspace.js` ("Durable Temporal" nav item) renders real data from those endpoints.

**Conclusion:** it is a real embedded durable engine, not an external Temporal cluster, unless `TEMPORAL_HOST` is configured. The name "Durable Temporal" is therefore slightly misleading but the reporting is honest. Company Build/Onboarding workflows can be built on this engine; no new dependency is needed.

### 2.4 AI CEO, departments, Approvals, Governed Terminal, MCP, Integrations

- **AI CEO:** `core/ceo.py` (command engine), `core/ceo_engine.py` (`CEOExecutiveEngine`, 16-stage executive loop, planning horizons, truth states), `core/ceo_chat.py`. Wired into `TenantRuntime` and `/api/ai-ceo/*`.
- **Departments:** `core/departments.py#DepartmentControlUnit` creates `departments` rows with budgets, manager agent, escalation rules. AI employees: `core/ai_employee_os.py` (`AIEmployee`, `AIEmployeeRegistry`), plus `enterprise_agent_factory.py`, `workforce*.py`, `agent_factory_v2.py`.
- **Approvals:** `core/approvals.py#ApprovalPipeline.create_request/decide_request` on the `approvals` table (statuses PENDING/APPROVED/REJECTED, risk levels, signed grant hash). Decision is role-gated to OWNER/EXECUTIVE/GLOBAL_ADMIN. Served by `/api/approvals`.
- **Governed Terminal:** `web/apple_governed_terminal.js` + backend policy/authority gateway; commands are classified and audited.
- **MCP:** `core/mcp_interoperability_runtime.py` — kill switch, trust states, risk classes, data classification, transport types, security inspector, data minimizer. UI `web/mcp_workspace.js`.
- **Integrations:** `core/enterprise_integrations.py` (marketplace catalogue + `external_connections` table with `auth_status`, `permission_scope`, `field_mappings`), `nango_integration_runtime.py`, `core/automation_fabric/*`. UI `web/integrations_workspace.js`. The marketplace list is a static catalogue; connections are real rows when created, but there is no OAuth flow or encrypted credential storage for third-party tokens today (see 2.7).

### 2.5 Auth, roles, audit log

- Auth/token/roles as in 2.2. `UserRole` includes OWNER, EXECUTIVE, MANAGER, OPERATOR, OBSERVER, AUDITOR, SYSTEM_AGENT, GLOBAL_ADMIN.
- Audit: `core/evidence_ledger.py#EvidenceLedger` — append-only, hash-chained JSONL per tenant, with `verify_full_chain_integrity()`. There is **no** generic `audit_events` SQL table; company deletions would need either ledger entries or a new table (Stage 1 decision).
- Settings changes already have their own audit path (`core/settings/audit.py`, `/api/settings/audit`).

### 2.6 Email, PDF, file storage

- **Email: not implemented.** `comm_smtp_server` / `comm_smtp_port` exist only as settings definitions; there is no `smtplib` usage, no provider SDK, no outbox table. Any "email the export" must be built behind an adapter with an honest "not configured" state.
- **PDF: real.** `core/document_generator.py` is a pure-Python generator (valid PDF/DOCX/XLSX/PPTX/CSV/TXT/MD, `zipfile` already imported). `core/enterprise_reports.py` provides report records and CSV export. No heavyweight dependency.
- **File storage: real but local.** `core/object_storage.py#ObjectStorageService` stores artifacts under a local `storage/` root using S3-compatible key layout `s3://zonata-artifacts/{tenant}/{company}/{mission}/{execution}/{category}/{file}`, with HMAC-signed presigned URLs and lifecycle pruning. It does **not** talk to a real S3/MinIO endpoint. `core/enterprise_files.py` and `core/document_generator.py` provide document vault boundaries (personal vs company).

### 2.7 Settings and translation

**Settings** — a mature subsystem:

- Definitions: `core/settings/definitions.py` (canonical catalogue, per-domain categories such as `ai_ceo`, `workforce`, `missions`, `notifications`, `approvals`, `security`, `localization`, `communication`, `enterprise`).
- Resolution: `SettingsService.get_effective_setting(tenant, company, key, default)` with hierarchy company → tenant primary → global host → schema default.
- API: `/api/settings`, `/api/settings/v2`, `/api/settings/category/<id>`, `/api/settings/key/<key>/reset|rotate|revoke`, `/api/settings/effective`, `/api/settings/drift`, `/api/settings/audit`, `/api/settings/action/<...>`.
- Secrets: `core/settings/secrets.py` — AES-GCM, master key from `ZONATA_SETTINGS_MASTER_KEY` (or `0600` key file in dev), write-only, last-4 display metadata, `decrypt_for_runtime` never wired to HTTP. Migrations `0006_settings_v2_append_only.sql`, `0007_settings_v2_tenant_keys.sql`.
- Relevant existing keys: `ceo_autonomy_level`, `ceo_spending_limit`, `fin_high_expense_approval`, `notify_*`, `sec_require_mfa`, `acc_two_factor_method`, `comp_base_currency`, `loc_reporting_timezone`, `ent_data_residency_zone`, `comm_smtp_server`, `comm_smtp_port`, `data_retention_days`.
- Gap: no `quiet hours`, no `number format` (lakh/crore), no `RTL` toggle, no company-setup-specific settings, and nothing consumes `ceo_spending_limit` inside a company build workflow yet.

**Translation / RTL — does not exist.** `web/index.html` is `<html lang="en" data-theme="light">`; there is no i18n module, no locale files, no `dir="rtl"` handling, no `Intl.NumberFormat`. Currency is hardcoded per component (`₹` in `ai_ceo_workspace.js`, `$` elsewhere) and numbers use raw `.toLocaleString()` without a locale. This is net-new work in Stage 2/6 and is the largest single gap against the prompt.

### 2.8 Test setup

- `pytest.ini` → `tests/`, 136 `test_*.py` modules plus JS/jsdom runners. Relevant existing coverage: `test_company_os.py` (multi-tenant isolation, tokens, departments), `test_enterprise_multi_company_controls.py`, `test_direct_object_access_and_tenant_security.py`, `test_phase_16_tenant_fairness.py`.
- JS: hand-rolled runners, no framework — `tests/assistant_floating_ui_test.js`, `assistant_jsdom_smoke_test.js`, `assistant_e2e_test.js` (jsdom), plus `settings_v2_ui_test.js`, `browser_settings_click_test.js`.
- `npm run test:assistant` runs the three JS suites + 4 pytest modules. `npm run typecheck` (`scripts/typecheck.js`) and `npm run lint` (`scripts/lint.js`) are custom Node scripts.
- `playwright.config.ts` exists but **no browser binary is installed in this environment**; jsdom is the fallback. Screenshots are not possible here.
- `tests/test_postgresql_16_live_integration.py` hangs against a live Neon `DATABASE_URL`; excluded from stage gates.

### 2.9 Deployment

`render.yaml` deploys a Docker web service `zonata-staging` (free plan, oregon), health check `/readyz`, with `DATABASE_URL` injected manually and generated `JWT_SECRET` / `SESSION_SECRET` / `ZONATA_AUTH_SECRET` / `METRICS_AUTH_TOKEN`.

Three things to flag now:

1. `render.yaml` now tracks `ui-redesign`, so pushes to this branch deploy directly and the manual fast-forward is no longer required. `engineering/production-readiness-gap-closure` remains a mirror; Render only follows `ui-redesign`.
2. `ZONATA_SETTINGS_MASTER_KEY` is **not** in `render.yaml`. Settings V2 secrets only work in production if it is set. On staging the keyring falls back to a generated key file, which is lost on redeploy and would make previously stored connection secrets undecryptable. Set a 64-hex key in the dashboard before using the connection vault.
3. `ZONATA_COMPANY_EXPORT_DIR` is **not** in `render.yaml`. The free plan has no persistent disk, so exports live on ephemeral storage; they must be downloaded while the instance that created them is still running.

Migrations are versioned files under `migrations/pg/` applied by `migrations/migration_manager.py` with checksum verification, statement-by-statement dialect-aware splitting. New migrations must be added as new numbered files (never edit an applied file — checksum mismatch aborts startup).

---

## 3. Gap list vs the prompt

### Stage 1 — data model, API, permissions

| Requirement | Today | Gap |
|---|---|---|
| Company fields: id, tenant, type, name, title, description, owner(name/email), country, industry, status, created/updated, created_by | Partial (`name`, `country`, `industry`, `company_type`, `status`, `created_at`) | Add `title`, `description`, `owner_name`, `owner_email`, `created_by`, `updated_at`, `website`, `business_model`, `revenue_amount`, `revenue_currency`, `revenue_period` |
| Statuses: draft, creating, onboarding, operational, needs attention, pending export, pending deletion, deleted | DRAFT/ONBOARDING/OPERATIONAL/ATTENTION/SUSPENDED | Remap/add `CREATING`, `NEEDS_ATTENTION`, `PENDING_EXPORT`, `PENDING_DELETION`, `DELETED`; add transition table enforced server-side |
| Related records: build run, connection, uploaded file, legal pack item, deletion request, audit event | `external_connections` exists; `departments`, `workflows` exist | New tables: `company_build_runs`, `company_files`, `company_legal_items`, `company_deletion_requests`, `company_audit_events` (or reuse evidence ledger + a company audit table) |
| API: list/create/read/update/submit/connect/disconnect/request-delete/confirm-step/download-export, tenant-scoped | list/read/draft/activate/onboard only | New routes (see §4); all must call `_resolve_company_id` + tenant check |
| Permissions: owner + allow-listed admins add/edit/delete; agents can draft, never submit/settings/delete | Coarse role helpers only | New per-company authorization helper; no code path lets an agent call company mutations |
| Drafts autosave + duplicate-name warning in tenant | Draft JSON file per company id | Extend draft store to unsaved drafts (client-generated id), add duplicate-name check API |
| Additive, reversible, no data loss | Migration engine supports it | Two migrations: `0008_company_setup.sql` (+ rollback file), `0009_company_setup_rls.sql` if needed |

### Stage 2 — switcher, Add page, entry points, language

| Requirement | Today | Gap |
|---|---|---|
| Switcher: current company on top with type + status badges, others below, empty state, Add always at bottom | Modal exists; current company not pinned; hardcoded fallback; "All Companies" option; Add is inside the modal | Rewrite switcher component; remove fallback; remove "All Companies" or move it behind an explicit Portfolio entry |
| Add page: two large cards, icons, one-line "what you will need", "Not sure which one?" help | `renderModeSelection()` has a 2-card mode chooser inside the onboarding route | New dedicated `/company/add` page matching the spec, keyboard accessible, full page on phone |
| Entry points: switcher, Companies screen, Ctrl/Cmd+K, assistant | Switcher + `/company` exist; palette has assistant entries; assistant exists | Add palette action + assistant intent routing to the page only (never fill/submit) |
| Translate every label, RTL for Arabic | No i18n at all | Introduce i18n module + locale files + `dir` switching + logical CSS properties |

### Stage 3 — create new company

| Requirement | Today | Gap |
|---|---|---|
| One-column phone-friendly form, autosave, hint + example per field | 14-stage onboarding workspace, very different | Replace with a single form + review screen |
| Description: free text **or** guided form → one description | Guided sections exist across stages | Build mode toggle that composes one description string |
| Optional collapsed section (country, industry, website/assets, customers, budget/timeline, files, notes) | Scattered across stages | New collapsible section with upload |
| Submit → validate → review → create with `CREATING` → start Company Build workflow → overview with live progress | `/api/onboard` creates with client-chosen status | New endpoint + workflow definition + progress endpoint + overview progress UI |
| 7 phases: intake, research, plan, build, legal pack, verify, operational | No build workflow | New workflow graph on the durable engine; research/website/legal behind adapters |
| Phase state, plain-language log, waiting-on-me, safe resume after failure | Workflow engine supports checkpoints/interrupts | UI + per-phase log projection |
| Estimate 1–3 days, shown as estimate | None | `company_build_runs.estimate_min/max_days` + copy rules |

### Stage 4 — add existing company (delivered; see 4e)

| Requirement | Today | Gap |
|---|---|---|
| Detailed form, required fields incl. revenue amount/currency/period and my role | Onboarding stages cover some | New form + fields |
| 8 optional skippable sources, each with read/why/never copy, each skip recorded | Data sources exist in `core/models.py` (`DataSource`) | New connection catalogue + `skipped` records |
| Readiness score | None | Compute server-side, return reasons |
| Read-only least-privilege connections, OAuth or encrypted key, never re-shown/logged/prompted | `external_connections.permission_scope`, no credential storage | New `company_connection_secrets` using `core/settings/secrets.py` AES-GCM; adapter interface |
| Connection test, plain error, status, disconnect revokes | None | New endpoints + adapter per provider (stub first) |
| Ownership confirmation; DNS/email verification before private reads | None | Verification token + DNS/email adapter |
| Untrusted content guard, prompt-injection flagging | Some prompt-injection regexes in `temporal_durable_execution_runtime.py`, `settings` toggle | Dedicated ingestion guard for uploaded docs |
| Writes need approval regardless of autonomy | Approval pipeline exists | Route all mutated external ops through it |
| Sensitive data classified, encrypted, region-scoped, role-visible | `data_classification` exists in MCP; settings `ent_data_residency_zone` | Apply to connection data + files |
| Import validation (type/size/malware/bad rows/duplicates) | None | Upload validator + row-level report |
| Workflow Onboarding: connect/verify → study → diagnose → plan → act → operational | None | New workflow definition + diagnosis report page |

### Stage 5 — overview, edit, delete

| Requirement | Today | Gap |
|---|---|---|
| Overview: identity, key numbers, progress, connections/legal pack, recent activity | Read-only telemetry pane | Rewrite overview with the required blocks |
| Options menu: Edit, Delete | None | New menu (keyboard accessible) |
| Edit: same fields, type fixed, audit, build-running warning, connection add/remove | None | New `/company/<id>/edit` + API + audit |
| Delete: what-will-happen list, name typing, password/2FA, stop work, revoke, export PDF (split + ZIP), email or in-app download, 7-day window (0 = immediate), cancel, purge + final audit | No delete path at all | New deletion state machine, tables, endpoints, export generator, UI wizard, tests |

### Stage 6 — settings wiring, tests, hardening

| Requirement | Today | Gap |
|---|---|---|
| Wire autonomy, payment limit, notifications/quiet hours, reports, 2FA, language, RTL, currency/number formats (lakh/crore), assistant current-company | Settings exist; not consumed by these flows; no quiet hours/RTL/lakh settings | Add keys, consume them, add tests |
| Unit/integration + e2e for add/edit/delete paths | No company-setup tests | New test modules (pytest + jsdom) |
| Abuse tests: cross-tenant, id guessing, step skipping, script injection, oversized uploads, prompt injection, double submit | Partial tenant tests | New adversarial suite |
| 360px layout, Arabic RTL, keyboard-only, paginated lists, non-blocking long workflows | Not covered | Visual/DOM checks in jsdom + CSS work |
| Security review: secrets, logs, headers, rate limits, uploads | Rate limiting exists (`0004`), secrets exist | Focused review + fixes |

---

## 4. Proposed plan (files, routes, tables)

### 4.1 Migrations (additive, reversible)

`migrations/pg/0008_company_setup.sql` (+ `0008_company_setup_rollback.sql`):

- `ALTER TABLE companies ADD COLUMN` for `title`, `description`, `owner_name`, `owner_email`, `created_by`, `updated_at`, `website`, `business_model`, `revenue_amount`, `revenue_currency`, `revenue_period`, `readiness_score`, `deleted_at`. All nullable or defaulted → no data loss.
- New tables:
  - `company_build_runs (build_id, tenant_id, company_id, workflow_id, phase, phase_state, progress, estimate_min_days, estimate_max_days, started_at, finished_at, failure_reason, log JSON)`
  - `company_files (file_id, tenant_id, company_id, kind, filename, mime, size, storage_key, sha256, scan_status, uploaded_by, created_at)`
  - `company_legal_items (item_id, tenant_id, company_id, name, authority, status, instructions, draft_disclaimer, created_at)`
  - `company_connection_secrets (connection_id, tenant_id, company_id, ciphertext, nonce, key_id, last4, created_at)` — reuses `core/settings/secrets.py`
  - `company_deletion_requests (request_id, tenant_id, company_id, status, steps_done JSON, export_status, export_parts, email_status, download_confirmed_at, purge_after, requested_by, created_at, completed_at)`
  - `company_audit_events (event_id, tenant_id, company_id, actor_id, actor_role, action, detail JSON, created_at)` (+ index)
- `ALTER TABLE external_connections ADD COLUMN` `provider_id`, `scope JSON`, `status`, `last_check_at`, `secret_ref`, `verified_at`, `verification_method`, `skipped`.

`migrations/sqlite/` mirror for dev.

### 4.2 Backend modules

- `core/company_setup/__init__.py`
- `core/company_setup/models.py` — dataclasses + status enums + transition table
- `core/company_setup/service.py` — `CompanySetupService` (tenant-scoped CRUD, validation, drafts, duplicate-name check, audit writes)
- `core/company_setup/permissions.py` — `can_add`, `can_edit`, `can_delete`, `company_admin_allowlist`; agents rejected by principal type
- `core/company_setup/build_workflow.py` — 7-phase Company Build graph on `DurableWorkflowRuntime`
- `core/company_setup/onboarding_workflow.py` — 6-phase existing-company graph
- `core/company_setup/connections.py` — adapter interface + `StubConnectionAdapter`, secret storage, test/disconnect
- `core/company_setup/ingestion.py` — upload validation, size/type/malware hook, row-error report, prompt-injection guard
- `core/company_setup/diagnosis.py` — diagnosis report structure (stubbed findings in dev, clearly labelled)
- `core/company_setup/export.py` — PDF export via `DocumentGenerator`, part splitting + ZIP, email adapter
- `core/company_setup/deletion.py` — deletion state machine, purge scheduler hook, final audit
- `core/company_setup/email_adapter.py` — `NullEmailAdapter` (honest "not configured") + SMTP adapter used only when `comm_smtp_*` set and master key present

### 4.3 API routes (all tenant-scoped, all audited when mutating)

Implemented in Stage 1 (`core/company_setup/api.py`). The tenant always comes from the verified token; the path id is checked against `companies.tenant_id`, and a foreign id returns `404` (never `403`, so existence does not leak).

```
GET    /api/v1/companies                          list (paginated, filter, search)
GET    /api/v1/companies/preferences              real tenant/company settings for the UI
POST   /api/v1/companies                          create draft
GET    /api/v1/companies/drafts                   list my drafts
POST   /api/v1/companies/drafts                   autosave (create or update)
GET    /api/v1/companies/drafts/<draft_id>        resume a draft
DELETE /api/v1/companies/drafts/<draft_id>        discard a draft
GET    /api/v1/companies/<id>                     read + permissions + build + deletion
PATCH  /api/v1/companies/<id>                     update
POST   /api/v1/companies/<id>/submit              validate + move draft → creating/onboarding + build run
GET    /api/v1/companies/<id>/build               build/onboarding progress + phases + log
GET    /api/v1/companies/<id>/connections         list connections
POST   /api/v1/companies/<id>/connections         connect (read-only scopes only)
POST   /api/v1/companies/<id>/connections/<cid>/test
DELETE /api/v1/companies/<id>/connections/<cid>   disconnect + revoke secret
GET    /api/v1/companies/<id>/deletion            current deletion request
POST   /api/v1/companies/<id>/delete/request      step 1: what will happen
POST   /api/v1/companies/<id>/delete/confirm-name step 2: exact name
POST   /api/v1/companies/<id>/delete/confirm-identity step 3: password (+ 2FA when enabled)
POST   /api/v1/companies/<id>/delete/cancel       cancel until purge
GET    /api/v1/companies/<id>/export              download (Stage 5; 409 until an export exists)
GET    /api/v1/companies/<id>/audit               recent company audit events
GET    /api/v1/companies/<id>/admins              per-company admin allow-list
POST   /api/v1/companies/<id>/admins              owner grants an admin
DELETE /api/v1/companies/<id>/admins/<user_id>    owner revokes an admin
```

Legacy `/api/companies`, `/api/companies/<id>/draft|activate`, `/api/onboard` stay working unchanged in Stage 1 (deprecated, removed in Stage 6 if unused). The new API is mounted in `api_server.py` for GET/POST/PATCH/PUT/DELETE and reuses the existing token auth, tenant fairness and rate limiting.

### 4.4 Frontend

- `web/company_setup/` new modules (kept separate from the 2 500-line `company_workspace.js`):
  - `switcher.js` — replace `AppShell.openCompanySwitcher` internals (current pinned, others list, empty state, Add at bottom; bottom sheet < 640px)
  - `add_page.js` — two cards, hints, "Not sure which one?"
  - `create_new.js` — form, guided description, optional section, review
  - `add_existing.js` — form, skippable sources, readiness score
  - `connections.js` — connect/test/disconnect
  - `overview.js` — overview + options menu
  - `edit.js`
  - `delete_wizard.js`
- `web/i18n.js` + `web/locales/en.json`, `ar.json` — `t()`, `dir`, `Intl.NumberFormat` with `en-IN` lakh/crore, currency from settings.
- Wire assistant intent + command palette to `navigateTo('/company/add')` only.

### 4.5 Tests

Delivered in Stage 1 as a single suite (`tests/test_company_setup.py`, 45 tests):

- records and validation: create/read/update, duplicate-name conflict + explicit override, pagination/search, immutable type, legacy `ATTENTION` normalisation
- status machine: forbidden transitions, submit validation, new → `CREATING`, existing → `ONBOARDING`, double submit
- tenancy: guessed ids, cross-tenant read/update/delete/connect, foreign list
- permissions: manager blocked, executive needs a grant, owner-only grants, agent draft-only, agent cannot delete even when granted
- drafts: autosave/resume/delete, per-user privacy, API round-trip
- deletion: step skipping, wrong name, removal summary, password check, MFA honesty, cancel, export-not-ready, cross-tenant delete
- connections: read-only scope enforcement, honest "not verified" test result, disconnect
- API router: full new-company journey, unknown route, unauth, validation shape

Planned for later stages:

- `tests/company_setup_e2e_test.js` — jsdom journeys for add existing / edit / delete (create-new is covered in `tests/company_setup_ui_test.js`)
- `tests/test_company_setup_build_workflow.py` — delivered as `tests/test_company_build_workflow.py` (Stage 3) and `tests/test_company_onboarding.py` (Stage 4, EXISTING onboarding and retry)
- `tests/test_company_setup_abuse.py` — script injection, oversized upload, prompt injection, double submit (Stage 6)

---

## 4b. Stage 1 — delivered

**New code**

| File | Purpose |
|---|---|
| `core/company_setup/__init__.py` | Package exports |
| `core/company_setup/status.py` | 9 statuses, legacy mapping, transition table, `validate_transition` |
| `core/company_setup/schema.py` | Idempotent table/column bootstrap with a per-database cache |
| `core/company_setup/permissions.py` | `Principal`, agent detection, owner/admin/grant rules, `PermissionDenied` |
| `core/company_setup/audit.py` | Scrubbed append-only company audit events |
| `core/company_setup/service.py` | `CompanySetupService`: records, validation, transitions, drafts, connections, deletion state machine, admins |
| `core/company_setup/api.py` | HTTP dispatcher mounted at `/api/v1/companies` |
| `migrations/pg/0008_company_setup.sql` | Additive Postgres schema (IF NOT EXISTS) |
| `migrations/rollback/pg/0008_company_setup_rollback.sql` | Manual reverse migration (never auto-applied) |
| `tests/test_company_setup.py` | 45 tests |
| `package.json` | `npm run test:company` |

**Touched:** `api_server.py` (five small mount points: GET, POST, PUT, PATCH via PUT, DELETE).

**Tables**

- `companies` — new columns: `title, description, owner_name, owner_email, owner_role, created_by, updated_at, website, business_model, revenue_amount, revenue_currency, revenue_period, readiness_score, deleted_at, deleted_by`
- new: `company_build_runs`, `company_files`, `company_legal_items`, `company_drafts`, `company_admin_grants`, `company_deletion_requests`, `company_audit_events`
- `external_connections` — new columns: `provider_id, scope, status, last_check_at, secret_ref, verified_at, verification_method, skipped, skip_reason`

**Decisions taken (changeable)**

1. Status vocabulary keeps `SUSPENDED` as a ninth status for billing/abuse holds; the eight prompt statuses are all present. `ATTENTION` is normalised to `NEEDS_ATTENTION` on read and migrated forward (reverse map documented in the rollback file).
2. "Admins I allow" = a per-company allow-list (`company_admin_grants`) of existing tenant users, granted by the owner. Creating a company requires tenant OWNER/EXECUTIVE/GLOBAL_ADMIN; editing/deleting requires OWNER (or GLOBAL_ADMIN) or an explicit grant.
3. Agents (`SYSTEM_AGENT`, `AI_AGENT`, `agent_*` ids) can save drafts but are denied create-final, update, submit, settings, connect and delete. Delete is denied even when an agent is mistakenly granted.
4. A newly created company is always `DRAFT`. Submission derives the status from type: `NEW → CREATING`, `EXISTING → ONBOARDING`. The build/onboarding run is created with phase `INTAKE` / `CONNECT_VERIFY`, `phase_state = PENDING`, progress 0 — real state, no fake progress.
5. Duplicate names are blocked with `409 DUPLICATE_COMPANY_NAME` unless the caller passes `allow_duplicate: true` (explicit override; the UI will surface it as a warning).
6. Deletion is a three-step state machine: `request` (removal summary) → `confirm-name` (exact match) → `confirm-identity` (password; 2FA when enabled) → `AWAITING_EXPORT`/`EXPORTING`. With MFA enabled and no verifier configured the endpoint returns `501 TWO_STEP_NOT_CONFIGURED` rather than accepting a dummy code.
7. Connection secrets go through the existing `SettingsSecretVault` (AES-GCM) and are revoked on disconnect; only read-only scopes are accepted in this stage.

**Honest limitations left for later stages**

- Company Build / Onboarding execution engine (Stage 3/4): superseded in Stage 3 for NEW and in Stage 4 for EXISTING; both now start their real workflow on submit.
- Export generation and email delivery (Stage 5): `GET /export` returns `409 EXPORT_NOT_READY`.
- Provider handshakes (Stage 4): superseded; `test` returns `simulated: false`, `available: false`, `verified: false`, "Nothing was read".
- No UI yet (Stage 2+).

**HTTP verification performed** (temporary server, isolated SQLite, strict auth):

```
POST   /api/v1/companies                  -> 201 (draft, INR)
GET    /api/v1/companies                  -> list
PATCH  /api/v1/companies/<id>             -> 200 title updated
POST   /api/v1/companies/<id>/submit      -> 202 CREATING + BUILD run (Stage 1 recorded workflow_started false; Stage 3 starts the build)
GET    /api/v1/companies/<id>/build       -> INTAKE/PENDING, estimate 1-3 days
GET    /api/v1/companies/<id>/audit       -> created + submitted
GET    /api/v1/companies/comp_foreign     -> 404 (foreign tenant)
POST   .../comp_foreign/delete/request    -> 404
GET    /api/v1/companies   (no token)     -> 401
POST   .../delete/request                 -> 200 AWAITING_NAME + removal summary
POST   .../delete/confirm-name (wrong)    -> 400 NAME_MISMATCH
POST   .../delete/confirm-name (exact)    -> 200 AWAITING_IDENTITY
POST   .../delete/confirm-identity (none) -> 403 INVALID_PASSWORD
POST   .../delete/cancel                  -> 200, company status unchanged (CREATING)
POST   /api/v1/companies/drafts           -> draft saved
GET    legacy /api/companies              -> new company visible (portfolio refresh works)
```

---

## 4c. Stage 2 — delivered

**New code**

| File | Purpose |
|---|---|
| `web/i18n.js` | English + Arabic dictionaries, `data-i18n` application, `<html lang/dir>`, language-change event, Indian lakh/crore currency + compact formatting |
| `web/company_setup_switcher.js` | One switcher: current first, real empty state, Add last, phone bottom sheet / desktop dialog, arrow + Tab trap + Escape, sidebar sync, assistant intent matcher |
| `web/company_setup_add.js` | `/company/add` page: two cards, per-card points, "Not sure which one?", permission-aware disabled state, language toggle, flow handoff |
| `web/company_setup.css` | Apple-style switcher sheet/dialog and Add page; 360px phone layout, RTL logical properties, status dot tones, focus/reduced-motion rules |
| `tests/company_setup_ui_test.js` | 16 jsdom/static checks (order, empty, keyboard, permissions, i18n/RTL, lakh/crore, intent, wiring) |

**Touched:** `web/index.html` (CSS/script order, Arabic font, `sidebarCompanyStatus`, real empty labels), `web/app_shell.js` (delegates instead of the fake modal), `web/app.js` (route `/company/add`, current-first dropdown, `syncCompanySurfaces`, palette rows for switch/add, no `comp_primary`), `web/company_context.js` (current-first dropdown, truthful empty state, sidebar sync, empty-state CTA to `/company/add`), `web/entry_flows.js` (`renderWelcome` delegates to the Add page; fake `comp_primary` welcome removed), `web/overview_workspace.js` (empty CTA → `/company/add`), `web/ura_assistant.js` (company intent shortcut before any network call + company suggestions), `package.json` (`test:company` now also runs the UI test).

**Behaviour delivered**

1. The switcher lists the current company first, then the others in server order, with status dot + label. "Current" chip on the active row.
2. No companies: a real empty state and an Add button. No placeholder or fabricated company anywhere in these surfaces.
3. "Add company" is always the last control; on phones the switcher is a bottom sheet, on desktop a centred dialog.
4. Full keyboard support: focus enters the dialog, ArrowUp/Down cycles, Tab is trapped, Escape closes and focus returns.
5. `/company/add` shows the two-card choice with honest expectations (Creating vs Onboarding, read-only connections, editable/deletable later) and a "Not sure which one?" panel.
6. Agents see a disabled state and an explanation; the server remains the real gate.
7. Arabic switches the whole document to `dir="rtl"` and translates the company-setup labels; Arabic font is requested in `index.html`.
8. Currency helpers use Indian grouping (`₹12,00,000`) and lakh/crore compaction (`₹12L`, `₹1.3Cr`).
9. Assistant phrases such as "add a company" / "switch company" open the page or switcher and say nothing was created or switched; no request is sent.
10. The topbar dropdown also lists the current company first and shows a truthful "No company yet — add one" state.

**Handoff note:** Stage 3 replaced the "Create new" card collector with the typed create flow, and Stage 4 replaced the "Add existing" `EntryFlows` hand-off with `/company/existing`. Stage 2 deliberately did not write company rows.

**Gates:** `npm run typecheck` (65 files), `npm run lint`, `npm run test:company` (45 pytest + 16 UI checks), `npm run test:assistant` (79 pytest + 41 UI + 29 jsdom + 12 journey checks).

**Not verifiable here:** no Chromium/Playwright, so no screenshots or true 360px/RTL visual pass. Behaviour is covered in jsdom; visual checks need a device/browser.

---

## 4d. Stage 3 — delivered

**New code**

| File | Purpose |
|---|---|
| `core/company_setup/build_workflow.py` | Company Build graph on `core/durable_workflow_runtime.py` (`StateGraph` + `GovernedLangGraphRuntime`): 7 NEW phases, null research/builder adapters, phase/log/gap projection onto `company_build_runs`, retry as a new attempt |
| `web/company_setup_create.js` | `/company/create`: one-column form, free/guided description (four answers compose one string), collapsed optional section, per-field hints/examples, draft autosave, review screen, duplicate-name handling, submit → build |
| `web/company_setup_progress.js` | `/company/<id>/build`: real phase list, progress bar, plain-language log, "waiting on you" gaps, honest failure, retry, polling only while running |
| `migrations/pg/0009_company_build_workflow.sql` | Additive columns for optional create fields + `company_build_runs.workflow_run_id` |
| `migrations/rollback/pg/0009_company_build_workflow_rollback.sql` | Manual reverse migration (never auto-applied) |
| `tests/test_company_build_workflow.py` | 9 tests: phases, skipped phases never faked, progress/estimate, audit, retry attempt, tenant isolation, EXISTING not started, visible failure |

**Touched:** `core/company_setup/service.py` (new optional fields, validation, insert/update, `get_build` normalization, submit starts the build, `retry_build`), `core/company_setup/schema.py` (columns + idempotent bootstrap), `core/company_setup/api.py` (`POST /build/retry`), `tests/test_company_setup.py` (submit/retry API expectations), `web/company_setup_add.js` (NEW card → `/company/create`), `web/app.js` (create + build routes, progress teardown), `web/index.html`, `web/i18n.js` (English + Arabic create/build strings), `web/company_setup.css` (form, review, progress, 360px, reduced motion), `tests/company_setup_ui_test.js` (23 checks), `package.json`.

**Behaviour delivered**

1. Form → review → create. Nothing is written until review is confirmed; the review shows exactly what will be submitted.
2. Description can be free text or four guided answers; the guided answers compose one description and show a live preview.
3. Optional details (website, asset links, target customers, budget/currency, timeline, notes) stay collapsed until opened.
4. Drafts autosave through `POST /api/v1/companies/drafts`; if the network fails the brief remains on the device and the status line says so.
5. Client validation mirrors the server rules (name, title, ≥20-character description, owner name, country, industry, URLs, budget) and the server remains the real gate. `409 DUPLICATE_COMPANY_NAME` is shown on the name field; no silent rename or duplicate.
6. Submit creates a `DRAFT`, then submits it: `NEW → CREATING`, and the build starts on the durable runtime. If the build cannot start, the company stays a draft and the UI says so instead of faking progress.
7. Real local phases run: intake, plan, legal drafts (records in `company_legal_items`), verification and the operational transition. Research and website building use null adapters: they are recorded `SKIPPED` with a reason and a gap, never `DONE`.
8. With the adapters unconfigured the company ends `NEEDS_ATTENTION` with the gaps listed. It only becomes `OPERATIONAL` when verification has no gaps.
9. Retry is a new attempt: the previous run is preserved, attempt increments, and only `CREATING` / `NEEDS_ATTENTION` can retry; a running build is never restarted.
10. Progress shows phase state, percent, estimate ("1–3 days, an estimate"), plain-language log, waiting-on-you items; polling runs only while a phase is actually running.

**Gates:** `npm run typecheck` (67 JS files), `npm run lint`, `npm run test:company` (55 pytest + 23 jsdom/static checks), `npm run test:assistant` (79 pytest + 41 UI + 29 jsdom + 12 journey checks).

**Live HTTP verification** (temporary strict-auth server, isolated SQLite):

```
POST /api/v1/companies                          -> 201 DRAFT, budget + asset persisted
POST /api/v1/companies/<id>/submit              -> 202 workflow_started true
GET  /api/v1/companies/<id>/build               -> VERIFY / DONE_WITH_GAPS, attempt 1
phases INTAKE DONE · RESEARCH SKIPPED · PLAN DONE · BUILD SKIPPED · LEGAL_PACK DONE · VERIFY DONE
POST /api/v1/companies/<id>/build/retry         -> 202 workflow_started true, attempt 2 (run 1 kept)
GET  /api/v1/companies/comp_does_not_exist      -> 404
```

**Honest limits**

- Research and website building are skipped until a provider is connected; no findings, assets or websites are invented.
- Legal items are drafts and say so; a qualified professional must verify them.
- The overview rewrite (including an embedded progress block) remains Stage 5; Stage 3 provides the dedicated `/company/<id>/build` page.
- EXISTING companies used the Stage 2 intake until Stage 4 replaced it with `/company/existing` and the real onboarding workflow (see 4e).
- No Chromium/Playwright here: jsdom covers behaviour, but no screenshots, true 360px render or visual RTL pass was possible.
- A build failure leaves the company `CREATING` so retry remains possible; the failure reason is projected on the build row and audited.


---

## 4e. Stage 4 — delivered

**New code**

| File | Purpose |
|---|---|
| `core/company_setup/sources.py` | The eight-source catalogue (accounting, banking, payments, commerce, CRM, workspace, communications, uploads) with `reads` / `why` / `never`, read-only scope, classification and required-verification flags. One contract shared by API and UI. |
| `core/company_setup/connections.py` | `ConnectionAdapter` null adapters, `get_adapter`, `OwnershipVerifier` (`available = False`). Nothing is read and no token is accepted. |
| `core/company_setup/readiness.py` | 0–100 readiness score from profile facts, connection state, skips and uploads, with weighted checks and a named reason for every missing point. |
| `core/company_setup/ingestion.py` | Ingestion validation shell: filename sanitisation, type/size allow-list (25 MB), SHA-256 requirement, duplicate detection, prompt-injection flagging. Records metadata only. |
| `core/company_setup/onboarding_workflow.py` | `CompanyOnboardingWorkflow` on the same durable runtime: CONNECT_VERIFY → STUDY → DIAGNOSE → PLAN → ACT → OPERATIONAL. Connect inventory and plan are real; study/diagnose/act are skipped with reasons. |
| `web/company_setup_existing.js` | `/company/existing`: three steps (business, sources, review), required revenue/currency/period/role/business model, eight source cards with read/why/never and connect/skip/later, skip reason ≥5 characters, review, create + apply choices + submit, draft autosave. |
| `migrations/pg/0010_company_onboarding.sql` | Additive columns: `external_connections.source_id`, `classification`, verification token/request/expiry; `company_files.flags`; two indexes. |
| `migrations/rollback/pg/0010_company_onboarding_rollback.sql` | Manual reverse migration (never auto-applied). |
| `tests/test_company_onboarding.py` | 13 tests: onboarding phases and honest gaps, retry attempt 2, catalogue contract, skip/restore, connected-source skip refusal, null connection test, 501 verification, ingestion accept/duplicate/oversize/blocked/injection, tenant isolation, guessed connection id. |

**Touched:** `core/company_setup/build_workflow.py` (generalised phase specs, `RUN_TYPE`, `DECISION_PHASE`, readiness/diagnosis/study/sources projection), `core/company_setup/service.py` (onboarding dispatch, `ONBOARDING` retry, source/readiness/file methods, honest `test_connection`, least-privilege scope from the catalogue), `core/company_setup/api.py` (catalogue, sources, skip/unskip, readiness, files, verify routes), `core/company_setup/schema.py` (new columns + idempotent bootstrap), `web/company_setup_add.js` (EXISTING card), `web/app.js` (route), `web/index.html`, `web/company_setup_progress.js` (onboarding eyebrow, readiness, diagnosis, sources, ONBOARDING retry), `web/i18n.js` (English + Arabic), `web/company_setup.css`, `tests/company_setup_ui_test.js`, `tests/test_company_setup.py`, `tests/test_company_build_workflow.py`, `package.json`.

**Behaviour delivered**

1. Add Existing opens a real three-step form. Name, title, ≥20-character description, country, industry, business model, revenue amount/currency/period, owner name and role are required on the client and again on the server.
2. Revenue is shown in Indian lakh/crore notation as it is typed; currency and period are server-validated enum values.
3. The eight sources each show what ZONATA would read, why it helps and what is never copied. A source can be connected (read-only record), skipped with a reason (≥5 characters) or left undecided. Nothing is required.
4. Submitting creates the company (`DRAFT`), records each connection or skip, then submits it: `EXISTING → ONBOARDING` and the onboarding workflow starts. If a source choice fails to save, the company still exists and the UI names how many choices failed instead of pretending.
5. Onboarding runs six phases on the shared durable runtime. Connect inventory, readiness and the plan are local and real. STUDY, DIAGNOSE and ACT report `SKIPPED` with a reason and a gap because every adapter is null; no finding, reading or write is invented. The company ends `NEEDS_ATTENTION`, not `OPERATIONAL`.
6. Readiness is computed from facts and returned with checks, counts and named reasons; skipped sources without a reason lower the score.
7. Uploads validate name/type/size/SHA-256/duplicates and flag prompt-injection text; the file is recorded as metadata with `stored: false`, and a flagged file is never sent to a prompt.
8. Ownership verification and connection tests are honest: `501 VERIFICATION_NOT_CONFIGURED`, and `simulated: false / available: false / verified: false` with "Nothing was read".
9. Progress shows onboarding-specific copy, a readiness ring with counts and reasons, the diagnosis gap and saved sources; retry is allowed for `CREATING`, `ONBOARDING` and `NEEDS_ATTENTION` and creates a new attempt while preserving the old run.
10. All Stage 4 surfaces are tenant-scoped; foreign and guessed ids return `404`, and cross-tenant skip/read/write is denied.

**Gates:** `npm run typecheck` (68 JS files), `npm run lint`, `npm run test:company` (68 pytest across 3 files + 28 jsdom/static checks), `npm run test:assistant` (79 pytest + 41 UI + 29 jsdom + 12 journey checks).

**Honest limits**

- Every provider adapter is null: nothing is read from a real source, no OAuth handshake exists, and no diagnosis finding is produced.
- Uploads are metadata only; no object-storage backend is configured, so file bytes are not stored.
- Prompt-injection detection is pattern-based; it flags, it does not prove safety.
- Ownership verification has no DNS/mailbox adapter; request and confirm both return 501.
- No Chromium/Playwright here: jsdom covers behaviour, but no screenshots, true 360px render or visual RTL pass was possible.
- `ZONATA_SETTINGS_MASTER_KEY` is absent from `render.yaml`; connection secrets need it when real providers arrive.

---

## 4f. Stage 5 — overview, edit, protected delete, export

**New code**

| File | Purpose |
|---|---|
| `core/company_setup/export.py` | Native PDF writer (no new dependency) with cover, company facts, sources, connections, files, audit and legal sections; numbered parts when the page budget is exceeded; ZIP packaging when split or when non-Latin characters had to be replaced; JSON sidecar of the original values and a SHA-256 manifest; deterministic filenames. |
| `core/company_setup/email_adapter.py` | `ExportEmailAdapter` with a real SMTP backend when `ZONATA_SMTP_USERNAME` / `ZONATA_SMTP_PASSWORD` exist and an honest null backend otherwise (`NOT_CONFIGURED`). Never reports `SENT` without an accepted SMTP send. |
| `web/company_setup_overview.js` | `/company/<id>/overview`: identity, four key numbers, build/onboarding progress, sources and connections, legal drafts, recent audit trail, deletion banner, and one keyboard-accessible options menu for Edit/Delete. |
| `web/company_setup_edit.js` | `/company/<id>/edit`: the same facts in one column, fixed company type, client validation with server as the real gate, duplicate-name mapping, connection add/remove. |
| `web/company_setup_delete.js` | Protected five-step wizard in a bottom sheet on phones and a centred dialog on desktop: what happens → exact name → password (+2FA when configured) → export → recovery window, with cancel and an honest purge. |
| `migrations/pg/0011_company_deletion_export.sql` | Additive `company_deletion_requests` export/email/recovery columns plus indexes. |
| `migrations/rollback/pg/0011_company_deletion_export_rollback.sql` | Manual reverse migration (never auto-applied). |
| `tests/test_company_deletion_export.py` | 15 tests: PDF and ZIP output, split packaging, manifest/checksum, Unicode replacement, email null backend, plan counts, export-before-purge, download confirmation, cancel restore, zero-day windows, tenant isolation and step skipping. |

**Touched:** `core/company_setup/service.py` (deletion plan, export generation, delivery gate, purge, cancel, recovery days, `export_filename`), `core/company_setup/api.py` (`/legal`, `/delete/plan`, `/delete/export`, `/delete/purge`, binary `/export`), `api_server.py` (streams binary export responses), `core/company_setup/schema.py`, `core/company_setup/status.py` (cancel transitions), `core/settings/definitions.py` (`company_delete_recovery_days`, default 7), `web/app.js` (overview/edit routes), `web/index.html`, `web/company_workspace.js` (Overview tab and Reconfigure Profile point at the new pages), `web/i18n.js` (English + Arabic overview/edit/delete/status/activity keys), `web/company_setup.css` (overview grid, edit form, menu, delete sheet, 360px and RTL rules), `tests/company_setup_ui_test.js`, `tests/test_company_setup.py`, `package.json`.

**Behaviour delivered**

1. Overview is the real company home. It reads the company, sources, connections, readiness, legal items, files and audit trail; a failing secondary panel shows a partial-data notice instead of inventing values.
2. Edit shows the current facts, validates name/email/URL/amounts/assets on the client and sends a `PATCH`; clearing an optional field really clears it. Duplicate names map back to the name field and the form stays open.
3. Only the owner or a granted admin sees Edit/Delete; an agent sees "View only" and no menu. The server repeats every permission check.
4. Delete is deliberately multi-step. `GET /delete/plan` is non-mutating and returns real removal counts, the configured recovery window, MFA state and whether email can actually be delivered.
5. The exact company name is compared by the client and again by the server; a wrong name cannot advance.
6. Identity always requires the signed-in account password. When two-step is required but no verifier exists, the server returns `501 TWO_STEP_NOT_CONFIGURED` and the UI says so; it never skips the requirement.
7. After identity, the export is written before anything is removed: PDF (split + zipped when needed), JSON sidecar and manifest. A failed export is shown as failed and blocks purge.
8. Delivery is honest. Email is attempted only for a verified account email and only when SMTP is configured. Otherwise the in-app download is the delivery path; purge waits for an email `SENT` or a confirmed download.
9. The recovery window defaults to 7 days (`0` = immediate). The wizard and overview show the real countdown; cancel restores the company's exact previous status and writes an audit event.
10. Purge removes company-scoped rows and stored references, keeps `companies`, `company_audit_events` and `company_deletion_requests` as a tombstone, nulls sensitive fields, sets `DELETED`, and writes the final audit record.
11. All routes stay tenant-scoped: foreign or guessed ids return `404`, cross-tenant deletion fails, and out-of-order steps return `409`.

**Gates:** `npm run typecheck` (71 JS files), `npm run lint`, `npm run test:company` (83 pytest across 4 files + 41 jsdom/static checks).

**Honest limits**

- `sec_require_mfa` defaults to true and this deployment has no TOTP verifier, so real deletion stops at `501 TWO_STEP_NOT_CONFIGURED`. The UI reports it; it does not bypass it.
- SMTP is only real when credentials are supplied; without them email status is `NOT_CONFIGURED` and the download is used.
- The PDF is intentionally plain: text, rules and page numbers, no layout engine or embedded fonts beyond the built-in set. Non-Latin glyphs that the built-in font cannot represent are replaced and force the ZIP report to say so.
- No Chromium/Playwright here: no screenshots, no true 360px render and no visual RTL pass; jsdom covers behaviour and static wiring.

---

## 4g. Stage 6 — settings wiring, tests, hardening

**New code**

| File | Purpose |
|---|---|
| `tests/test_company_setup_preferences.py` | 11 tests: default preferences, tenant and company overrides, API wrapping, guessed-company `404`, currency/timezone/country defaults, explicit payload wins, non-finite amounts, non-object body rejection. |
| `tests/test_company_setup_abuse.py` | 19 tests (8 subtests): cross-tenant reads/writes/delete/export, guessed ids, script tags, object type confusion, SQL-injection-like search, pagination clamping, double submit, oversized/malformed/traversal-duplicate uploads, prompt injection, deletion step skipping, agent delete denial, audit credential leakage, foreign preferences. |
| `tests/company_setup_ui_test.js` | 7 new checks: number/currency display, local language precedence, live preference loading, escaped hostile text, 360px/RTL/bottom-sheet CSS, create→submit→overview→edit journey, boot/API wiring. |

**Touched:** `core/company_setup/service.py` (`preferences()`, `_effective()` scope resolution, `_currency_meta`, `_timezone_list`, `_locale_country`, server defaults for create/update, finite-number checks, text type hardening), `core/company_setup/api.py` (`GET /preferences`, non-object body `400 INVALID_BODY`, tenant-scope construction), `api_server.py` (removed two local `settings_service` imports that made `/api/settings` writes raise `UnboundLocalError`), `web/i18n.js` (`configure`, `loadPreferences`, `getPreferences`, number-format and currency-display modes), `web/app.js` (boot-time preference loading), `web/company_setup_create.js` / `web/company_setup_existing.js` (currency/country defaults), `web/company_setup_overview.js` / `edit.js` / `delete.js` (company-specific preference load), `package.json`, tracker.

**Route added**

```text
GET    /api/v1/companies/preferences?company_id=<id>   real settings for the active company
```

**Behaviour delivered**

1. Real settings now change the app. `loc_base_locale` drives language/direction (Arabic RTL), `loc_number_format` drives Indian lakh/crore, international or continental grouping, `loc_currency_display` drives symbol, ISO or full-name money, `comp_base_currency` drives the default currency, `comp_operating_timezones` the default timezone and `company_delete_recovery_days` the deletion window. `sec_require_mfa` and the assistant default scope are reported with honest capability flags.
2. New and updated companies inherit the configured currency, timezone and country when the form omits them; an explicit value always wins and an existing company is never rewritten by a setting change.
3. Settings saved in the settings console at the token company are visible to every company. Resolution order is company override → tenant settings scope → tenant primary → global/schema default. A live smoke proved an Arabic + AED + Dubai setting reached both preferences and a newly created company.
4. The UI applies server preferences at boot and on company pages, but an explicit local language choice is never overwritten. Number and currency formatting follow the server setting.
5. `GET /preferences` is tenant-scoped. An explicit guessed or foreign `company_id` returns `404`; the endpoint never silently falls back to another tenant.
6. API hardening: non-object JSON bodies return `400 INVALID_BODY`; object/array values are never stringified into text fields; `NaN`/`Infinity` amounts are rejected; pagination is clamped; search stays parameterised.
7. Abuse suite covers cross-tenant get/update/submit/connections/plan/request/export/audit (`404`), guessed ids, deletion step skipping and wrong names, agent deletion denial, upload limits/type/traversal/duplicates, prompt-injection flagging, double submit (`409 ALREADY_SUBMITTED`) and audit scrubbing (passwords and two-step codes never appear).
8. UI checks cover the create→submit→overview→edit journey, escaped `<script>`/`onerror` text, 360px-safe CSS, RTL sheet rules, reduced motion and visible keyboard focus.
9. Fixed a real settings-write defect: two function-local imports made `POST /api/settings` raise `UnboundLocalError` on every write. Settings writes now return `200` and take effect.

**Gates:** `npm run typecheck` (71 JS files), `npm run lint`, `npm run test:company` (113 pytest across 6 files + 48 jsdom/static checks), `npm run test:assistant` (79 pytest + 41 UI + 29 jsdom + 12 journey). Live strict-auth smoke: preferences defaults, non-object body `400`, tenant settings change → Arabic/AED/Dubai, new-company defaults, recovery `0`, MFA off/plan honesty.

**Honest limits**

- There is no quiet-hours setting in this codebase and no notification dispatcher in these flows. The endpoint returns `quiet_hours: null` and `quiet_hours_supported: false` instead of pretending a schedule is enforced.
- `two_step_configured` is always `false` until a real TOTP/WebAuthn verifier exists; deletion still stops honestly at `501 TWO_STEP_NOT_CONFIGURED` when MFA is required.
- Preferences are fetched with the normal authenticated `fetch`; on a cold offline start the UI keeps its local defaults until the request succeeds.
- No browser is available, so the 360px/RTL checks are DOM/CSS assertions, not screenshots.

---

## 5. Risks

1. **Deploy branch switched in the blueprint, not yet in the dashboard.** `render.yaml` now tracks `ui-redesign`; a Render blueprint sync is still required for the running service to follow it. Until then the service keeps deploying `engineering/production-readiness-gap-closure` (a mirror of the same commits).
2. **Status remap is the most dangerous migration.** Existing rows use `DRAFT|ONBOARDING|OPERATIONAL|ATTENTION|SUSPENDED`. Adding `CREATING|NEEDS_ATTENTION|PENDING_EXPORT|PENDING_DELETION|DELETED` must not orphan existing rows; map `ATTENTION → NEEDS_ATTENTION` in a data migration with a reversible reverse map, and keep old values readable.
3. **Email is only real when SMTP credentials exist.** The adapter now sends through SMTP when `ZONATA_SMTP_USERNAME` / `ZONATA_SMTP_PASSWORD` are present and reports `NOT_CONFIGURED` otherwise. The in-app download remains the delivery path on deployments without mail; purge waits for one of them.
4. **Exports do not survive a redeploy on the free plan.** `storage/company_exports/` is ephemeral unless `ZONATA_COMPANY_EXPORT_DIR` points at a persistent disk. A pending deletion whose export file disappeared must be re-exported, not purged, or the user loses the export-before-purge guarantee.
5. **Encrypted connection secrets do not survive a redeploy without a key.** Without `ZONATA_SETTINGS_MASTER_KEY`, staging generates a key file that is lost with the instance. Set a stable 64-hex key in the Render dashboard.
6. **No i18n infrastructure.** Arabic RTL is net-new and touches every screen in scope. Scoping it to the company-setup surfaces first avoids a repo-wide rewrite in this program.
7. **PDF export of a whole company could be large.** `DocumentGenerator` is pure Python and in-memory; a big company may blow memory. Stage 5 splits the PDF into numbered parts and zips them, but generation still happens in memory before streaming.
8. **`/api/onboard` currently trusts client `status`.** Anyone authenticated can set `OPERATIONAL`. The new submit endpoint must derive status server-side.
9. **Company-scoped admin allow-list does not exist.** Roles are tenant-wide. Stage 1 adds an allow-list; until then "admins I allow" means tenant OWNER/EXECUTIVE with an explicit per-company grant.
10. **Prompt-injection guarding is partial.** Existing regexes are in the durable runtime; uploaded documents need their own sanitizer before any LLM prompt.
11. **Draft storage is file-based per tenant.** Multi-instance Render deploys would not share it unless the volume is shared. Stage 1 should move drafts into Postgres (additive table) while keeping the file store as a fallback.
12. **Test environment has no browser.** Playwright e2e cannot run here; jsdom is the substitute. Real 360px/RTL visual verification must be done by you on a device.
11. **Purge is evaluated lazily.** `purge_due` runs when a deletion is read (company detail, deletion status) or after a download/purge call; there is no background scheduler in this deployment. A company whose window expires while nobody opens it stays in `PENDING_DELETION` until the next read. This delays removal but never destroys data early. A cron/worker should call `purge_due` per tenant before production.
12. **Tenant settings live on the token company.** The settings console writes tenant-wide values against the token's company id, not `comp_primary`. Company setup now resolves company → token company → `comp_primary` → global, but any other subsystem that reads `get_effective_setting` directly may still miss settings saved at the token company. Stage 6 fixes company setup only; a shared resolver should be made authoritative later.
13. **No quiet hours.** Notification and quiet-hour behaviour is not dispatched by anything in these flows, so Stage 6 reports `quiet_hours_supported: false` rather than storing a schedule that would never run.

---

## 6. Open questions for you

Answers assumed in Stage 1 are marked **[assumed]**; change them at any time, they are cheap to adjust now.

1. **Status vocabulary.** **[assumed]** Keep `SUSPENDED` as a ninth status for billing/abuse holds. All eight prompt statuses are implemented and enforced.
2. **"Admins I allow".** **[assumed]** Per-company allow-list of existing tenant users, granted by the owner. Per-company invited users (not tenant-wide) can be added later without changing the API.
3. **Ownership verification for existing companies.** Not decided yet (Stage 4). Plan: DNS TXT and email-on-domain both supported, DNS preferred when both are possible.
4. **Recovery window default.** Not decided yet (Stage 5). Default will be 7 days, per-company override, `0 = immediate`.
5. **Email provider.** Not decided yet (Stage 5). SMTP adapter against `comm_smtp_server`/`comm_smtp_port` keeps dependencies at zero; a transactional API would sit behind the same interface.
6. **Export contents.** Not decided yet (Stage 5). Proposed: company profile, departments, workforce, workflows + events, files, connections, reports, audit. Chat transcripts only if you want them.
7. **Data region.** Not decided yet (Stage 4). `ent_data_residency_zone` exists as a declared setting; storage is local today.
8. **Existing onboarding screens.** Not decided yet (Stage 2). Recommendation: keep `/company/new` hidden for one release, delete in Stage 6.
9. **Agent draft permission.** Not decided yet (Stage 2/3). Current backend allows agent drafts; the UI label ("Prepared by the Assistant — needs your review") is a Stage 2 decision.
10. **Brand assets upload.** Not decided yet (Stage 3). Local object storage with presigned URLs works today; no CDN.

---

## 7. Stub register

| Capability | Planned adapter | Real today | Stage | Dev label |
|---|---|---|---|---|
| AI market/competitor research | `ResearchAdapter` (null until configured) | No; phase is `SKIPPED` with a reason and a gap | 3 | Skipped — not simulated, not invented |
| Website builder / base systems | `WebsiteBuilderAdapter` (null until configured) | No (some in-house tooling exists in `inhouse_tools/`, to be inspected) | 3 | Skipped — nothing built |
| Legal document generator | `LegalPackAdapter` | Local draft checklist and legal items only; no external generator | 3 | Draft: verify with a qualified professional |
| Email delivery (export, first report) | `ExportEmailAdapter` (Null + SMTP) | SMTP sends are real when `ZONATA_SMTP_USERNAME` / `ZONATA_SMTP_PASSWORD` are set; otherwise `NOT_CONFIGURED` and the in-app download is used | 5 | Real when configured; otherwise not configured |
| Company export PDF/ZIP | `core/company_setup/export.py` | Real native PDF (split into numbered parts when needed), ZIP with JSON sidecar and SHA-256 manifest, integrity checked before serving | 5 | Real |
| Two-step code verification | TOTP verifier | No (`501 TWO_STEP_NOT_CONFIGURED`); even a correctly shaped code is refused, never accepted from a dummy | 5 | Not configured |
| OAuth / read-only API connections (accounting, banking, payments, commerce, CRM, workspace, communications) | `ConnectionAdapter` per provider in `core/company_setup/connections.py` | Connection and skip records are real; every adapter is null (`available: false`, `verified: false`, nothing read) | 4 | Unavailable — not simulated |
| DNS/domain ownership verification | `OwnershipVerifier` in `core/company_setup/connections.py` | Request/confirm return `501 VERIFICATION_NOT_CONFIGURED`; no token is accepted | 4 | Not configured |
| Malware scanning of uploads | `ScanAdapter` | Metadata validation, type/size allow-list, SHA-256 duplicate refusal and prompt-injection flagging are real; bytes are not stored and no AV engine runs | 4 | Unscanned — no bytes stored |
| Diagnosis findings (profit leaks) | `DiagnosisAdapter` in `core/company_setup/onboarding_workflow.py` | No findings: the phase is `SKIPPED` with a reason and a gap | 4 | Unavailable — nothing invented |
| Object storage backend (S3/MinIO) | `ObjectStorageService` backend swap | File metadata is recorded (`stored: false`); `company_files.storage_key` stays empty | 4/6 | Metadata only — bytes not stored |
| Company Build / Onboarding execution | `DurableWorkflowRuntime` graph | NEW: 7-phase build. EXISTING: 6-phase onboarding. Both real, both honest about null-adapter gaps | 3/4 | Real graphs; provider phases skipped with reasons |
| Browser e2e / screenshots | Playwright runner | No (no Chromium in this environment); jsdom contract + journey tests stand in | 6 | Not available |
| Quiet hours / notification scheduling | Notification policy engine | No dispatcher in these flows; preferences report `quiet_hours: null` and `quiet_hours_supported: false` | 6 | Unavailable — no schedule is stored or claimed |
| Real browser preference pass | `GET /api/v1/companies/preferences` | Preferences, number/currency formatting, RTL, server defaults and local-language precedence are real and tested | 6 | Real |

---

## 8. Stage log

### Stage 0 — audit
- Read: company storage/switching, tenancy/auth, workflow engines, Temporal reporting, AI CEO, departments, approvals, MCP, integrations, evidence ledger, email, PDF, storage, settings (definitions/service/secrets/API), frontend shell and company workspace, migration manager, tests, render blueprint.
- Wrote this tracker. **No application code changed.**
- Key finding: the platform primitives (tenancy, durable workflows, approvals, settings, secrets, PDF) are real and reusable; the gaps are company lifecycle (statuses/build workflow), company-scoped permissions, deletion/export, email, i18n/RTL and the switcher/add/overview UI.
- Waiting for "continue" before Stage 1.

### Stage 1 — data model, API, permissions, drafts
- Added `core/company_setup/` (7 modules), migration `0008` + manual rollback, `tests/test_company_setup.py` (45 tests), `npm run test:company`.
- Mounted `/api/v1/companies` in `api_server.py` for GET/POST/PATCH/PUT/DELETE with the existing token auth and rate limiting.
- Statuses: all eight prompt statuses plus `SUSPENDED`; server-side transition table; `ATTENTION → NEEDS_ATTENTION` normalised and migrated.
- Permissions: owner/global admin always; executive only with an explicit per-company grant; agents draft-only and never delete.
- Deletion: request → exact name → password (+2FA when verifiable); export/email/purge intentionally return honest "not ready" until Stage 5.
- Gates: 45 company tests, 44 existing company/tenant tests, typecheck 61 JS files, lint, `npm run test:assistant` (79 pytest + 41 JS checks). Live HTTP journey verified against a temporary strict-auth server; foreign-tenant ids return 404 and the legacy `/api/companies` list sees new companies.
- Stub note: build execution, export/email and provider handshakes are not implemented yet; no fake success is shown.

### Stage 2 — switcher, Add page, entry points, i18n/RTL
- Added `web/i18n.js`, `web/company_setup_switcher.js`, `web/company_setup_add.js`, `web/company_setup.css` and `tests/company_setup_ui_test.js`.
- Rewired `index.html`, `app_shell.js`, `app.js`, `company_context.js`, `entry_flows.js`, `overview_workspace.js`, `ura_assistant.js`. Removed the fabricated `comp_primary / ZONATA Technologies` fallbacks from the company surfaces.
- Switcher: current first, real empty state, Add always last, phone bottom sheet, desktop dialog, arrow/Tab/Escape keyboard model, focus return, status tones, sidebar sync.
- Add page: two cards with honest expectations, help panel, language toggle, agent-disabled state, intent persisted. The NEW card hands off to the Stage 3 create flow; EXISTING still uses `EntryFlows` until Stage 4.
- i18n/RTL: Arabic dictionaries, `<html dir="rtl">`, `data-i18n` application, Arabic font request, Indian lakh/crore currency and compact formatting.
- Entry points: sidebar switcher, topbar dropdown, Companies empty states, command palette (Switch/Add), assistant intent shortcut (navigation only; nothing is created).
- Gates: typecheck 65 JS files, lint, `npm run test:company` (45 pytest + 16 jsdom/static), `npm run test:assistant` (79 pytest + 41 + 29 + 12 checks).
- Honest limits: no Chromium/Playwright here, so no screenshots or true 360px/RTL visual verification; jsdom covers the behaviour. The Add cards still use the legacy intake until Stage 3.

### Stage 3 — create new company + build workflow
- Added `core/company_setup/build_workflow.py`, `web/company_setup_create.js`, `web/company_setup_progress.js`, migrations `0009` (+ rollback) and `tests/test_company_build_workflow.py`.
- Submit now creates the company, derives `NEW → CREATING`, and runs the 7-phase build on the existing durable runtime. Research and website phases are `SKIPPED` behind null adapters with gaps; the company ends `NEEDS_ATTENTION`, never a fake `OPERATIONAL`.
- Create flow: free/guided description, collapsed optional details, hints/examples, client + server validation, duplicate-name handling, draft autosave, review screen, submit.
- Progress: real phases, percent, estimate, plain-language log, waiting-on-you gaps, visible failure, retry as a new attempt, polling only while running.
- Routes: `/company/create`, `/company/<id>/build`; NEW card wired to the create flow. Overview rewrite stays Stage 5.
- Gates: typecheck 67 JS files, lint, `npm run test:company` (55 pytest + 23 jsdom/static), `npm run test:assistant` (79 pytest + 41 + 29 + 12). Live strict-auth HTTP journey verified (submit, build, retry attempt 2, foreign id 404).
- Honest limits: providers are null adapters (research/build skipped with reasons), legal items are drafts, no browser visual/RTL pass here, EXISTING onboarding is Stage 4.
- Waiting for "continue" before Stage 4.

### Stage 4 — add existing company + onboarding workflow
- Added `core/company_setup/sources.py`, `connections.py`, `readiness.py`, `ingestion.py`, `onboarding_workflow.py`, `web/company_setup_existing.js`, migrations `0010` (+ rollback) and `tests/test_company_onboarding.py`.
- Add Existing is now a three-step flow (business, eight sources, review) with required revenue/currency/period/role/business model, connect/skip/decide-later per source, skip reasons and draft autosave.
- Submit records the source choices and starts the 6-phase onboarding workflow on the shared durable runtime. Connect inventory, readiness and plan are real; study, diagnose and act are `SKIPPED` behind null adapters with gaps. The company ends `NEEDS_ATTENTION`, never a fake `OPERATIONAL`.
- Progress gained onboarding copy, a readiness score with named reasons, the diagnosis gap and saved sources; retry now also accepts `ONBOARDING`.
- Uploads validate type/size/SHA-256/duplicates and flag prompt-injection text; metadata only, bytes are not stored. Ownership verification and connection tests return honest 501/unavailable results.
- Routes: `/company/existing`; EXISTING card wired to it. Overview rewrite stays Stage 5.
- Gates: typecheck 68 JS files, lint, `npm run test:company` (68 pytest across 3 files + 28 jsdom/static), `npm run test:assistant` (79 pytest + 41 + 29 + 12).
- Honest limits: all provider adapters are null, uploads are metadata-only, verification has no DNS/mailbox adapter, no browser visual/RTL pass here, `ZONATA_SETTINGS_MASTER_KEY` missing from `render.yaml`.
- Waiting for "continue" before Stage 5.

### Stage 5 — overview, edit, protected delete, export
- Added `core/company_setup/export.py`, `core/company_setup/email_adapter.py`, `web/company_setup_overview.js`, `web/company_setup_edit.js`, `web/company_setup_delete.js`, migration `0011` (+ manual rollback) and `tests/test_company_deletion_export.py`.
- Overview replaced the legacy telemetry pane: real identity, four key numbers, build/onboarding progress, sources and connections, legal drafts, audit trail, a deletion banner and one keyboard-accessible Edit/Delete menu. A failing secondary panel yields a partial-data notice, not invented values.
- Edit shows the recorded facts, validates on the client and again on the server, clears optional fields honestly, maps duplicate names to the name field, and can add/remove read-only connections.
- Delete is a five-step protected sheet: real plan counts, exact company name, signed-in password (+2FA when configured), export, recovery window. Wrong names never reach the server; a missing verifier returns `501 TWO_STEP_NOT_CONFIGURED` and stops the flow.
- Export is real: native multi-page PDF, numbered splits and ZIP when needed, JSON sidecar, SHA-256 manifest and an integrity check before serving. Email sends only through configured SMTP for a verified account email; otherwise the in-app download is the delivery path.
- Purge waits for email `SENT` or a confirmed download and the recovery window (default 7 days, `0` = immediate). Cancel restores the exact previous status. Purge keeps `companies`, `company_audit_events` and `company_deletion_requests`, nulls sensitive fields and writes the final audit record.
- Routes: `/company/<id>/overview`, `/company/<id>/edit`; Overview tab and "Reconfigure Profile" now point at them.
- Gates: typecheck 71 JS files, lint, `npm run test:company` (83 pytest across 4 files + 41 jsdom/static), `npm run test:assistant`.
- Honest limits: deletion stops at `501` while `sec_require_mfa` is true and no TOTP verifier exists; SMTP is real only when configured; the PDF uses built-in fonts and reports replaced characters; purge is evaluated lazily (no background scheduler); no browser visual/RTL pass here.
- Waiting for "continue" before Stage 6.

### Stage 6 — settings wiring, tests, hardening
- Added tenant/company-scoped `GET /api/v1/companies/preferences` and the `CompanySetupService.preferences()` resolver. It reports real locale, language/direction, number format, currency code/symbol/name/display, default currency, timezone, recovery window, MFA state and assistant default scope, with honest nulls for quiet hours and two-step verification.
- Wired real settings into creation and editing: currency, timezone and country defaults come from `comp_base_currency`, `comp_operating_timezones` and `loc_base_locale`; explicit payload values win and existing records keep their own values.
- Fixed tenant settings scope: settings written by the settings console at the token company now resolve for every company (company override → token company → `comp_primary` → global/schema). Live smoke: Arabic + AED + Dubai settings reached preferences and a new company.
- `web/i18n.js` gained `configure`, `loadPreferences`, `getPreferences`, Indian/international/continental grouping and symbol/ISO/full-name currency display. The app applies server preferences at boot and on company pages without overriding an explicit local language choice.
- Hardened input: non-object bodies `400 INVALID_BODY`, no object/array stringification into text, finite-number checks for budget/revenue, parameterised search, clamped pagination.
- Added `tests/test_company_setup_preferences.py` (11) and `tests/test_company_setup_abuse.py` (19, 8 subtests); extended `tests/company_setup_ui_test.js` to 48 checks with a create→submit→overview→edit journey, XSS escaping, RTL/360px CSS and preference loading.
- Fixed `POST /api/settings` raising `UnboundLocalError` because two function-local imports shadowed the module-level settings service. Settings writes now succeed and take effect.
- Gates: typecheck 71 JS files, lint, 113 company pytest across 6 files, 48 company UI checks, assistant 79 pytest + 41 UI + 29 jsdom + 12 journey.
- Honest limits: no quiet-hours engine exists; no TOTP verifier; jsdom stands in for a browser; other subsystems still read settings through the older resolver.
- End of the Company Setup program (stages 0–6).
