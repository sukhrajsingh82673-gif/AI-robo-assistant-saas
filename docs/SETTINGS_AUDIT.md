# ZONATA Settings Audit (Phase 0)

**Status:** Audit complete. No code, migration, or UI change has been made.
**Snapshot:** `main` @ `d054f13` (2026-11-07).
**Scope:** The Settings system only — registry, storage, resolver, API, UI,
secrets, audit, approvals, and the settings-related tests.
**Authority:** This document plus the user's Enterprise Settings master prompt.
**Next gate:** Explicit approval of this audit and the plan in §8 before any
migration or UI work begins.

---

## 0. Verdict

The current Settings center is a **large, well-presented configuration catalogue
with a thin enforcement layer**. It is not yet an enterprise control plane.

The headline numbers from the code (not from the UI's marketing copy):

| Measure | Reality |
|---|---|
| Backend categories | **45** across 6 groups (docstrings say "43"; one test name still says "43" but asserts 45) |
| UI domains | **32** domains in 6 pillars; the 45 backend categories are merged into them |
| Setting definitions | **202** |
| Keys with a runtime reader outside the settings subsystem | **19** |
| Keys with no runtime reader at all | **183** (2 of those are executable actions, not values) |
| Keys that are only used to display a fabricated "effective" status | **4** |
| `enforced_by` references in the registry | **0** |
| `required_permission` references | **0** |
| `allowed_scopes` declarations | **0** |
| Lock mechanism | **None** |
| Scope levels actually resolved | Company → tenant primary company → global primary company → default |
| Secret storage | **Plaintext** in SQLite and in a tracked JSON file |
| Real secret read-back protection | **No** — `/api/settings/search` returns the raw secret value |
| Server-side permission check on settings reads | **None** (authentication only) |
| Server-side permission check on settings writes | A coarse `editable_by=OWNER` check fed by a **spoofable `X-User-Role` header**, defaulting to `OWNER` |
| Audit append-only guarantee | Application convention only; no DB trigger, no hash chain |
| Runtime drift verification | Always returns `IN_SYNC` |

**Bottom line:** 19 settings are genuinely wired. 181 configuration keys are
decorative. The security model for Settings is weaker than the UI claims, and
the secret model is not safe for production. This must be fixed before adding
more visible controls.

---

## 1. Method and confidence

The audit was static and read-only:

1. Parsed `SETTINGS_DEFINITIONS` and `CATEGORIES_CATALOG` directly from
   `core/settings_service.py` (AST/literal extraction, so counts are exact).
2. Cross-referenced every setting key against all Python, JavaScript, HTML and
   TypeScript files under `core/`, `web/`, `api_server.py`, `cli.py`,
   `serve_web.py`, and `scripts/`, **excluding** the settings service itself,
   the settings UI, and tests. A key was counted as "wired" only when a
   non-settings runtime file reads it.
3. Read the settings API handlers in `api_server.py`, the service methods in
   `core/settings_service.py`, the UI in `web/settings_enterprise.js`, the
   existing schema in `core/db.py`, the migration system in `migrations/`, and
   the settings tests.
4. Compared the result against the master prompt's scope hierarchy, registry,
   data model, security rules, and 16-section information architecture.
5. Checked what is actually persisted in `storage/enterprise_settings.json` and
   the tracked `storage/roboassistant.db` (key names and row counts only;
   secret values are deliberately not reproduced here).

**Confidence:** High for code paths and counts. Medium for deployment-specific
behaviour (this environment has no PostgreSQL server, browser, or production
credentials). Anything described as "not enforced" means "no reader was found
in the repository"; it does not rely on runtime observation.

**Assumptions used below:** `tenant_id` is the organization boundary;
`tnt_primary` is the platform/root tenant; `comp_primary` is being used as a
proxy for organization defaults. The database has `companies`, `departments`,
`employees`, and `users` tables, so Department and Agent/Employee scopes can be
modelled without inventing new entities.

---

## 2. Stack and system map

### 2.1 Detected stack

| Layer | What exists | Decision |
|---|---|---|
| HTTP server | Python standard-library HTTP server in `api_server.py` | Keep |
| Backend services | Python modules under `core/` | Keep |
| Database | SQLite in development, PostgreSQL path via `core/db.py` / `core/database_engine.py`; schema + `migrations/` | Keep, extend with reversible migrations |
| Frontend | Vanilla JS modules in `web/`, one HTML shell (`web/index.html`), hand-written CSS | Keep |
| Crypto | `cryptography==50.0.2` already in `requirements.txt` | Use for secret envelope encryption |
| `package.json` | Only `@neon/config` and `@neon/env`; build is a one-line echo | Not an application framework |

**No new framework is needed or justified.** The enterprise redesign can be
delivered with the existing Python/JS stack. A component framework would be a
large, unproven rewrite of a working UI and is not required by the audit.
The only library-level addition is none: `cryptography` is already installed.

### 2.2 Settings system map

```
Browser
  └── web/settings_enterprise.js  (2,581 lines, 32 UI domains)
        └── /api/settings*  (api_server.py)
              └── core/settings_service.py  (2,858 lines)
                    ├── SETTINGS_DEFINITIONS  (202 entries, line 266)
                    ├── CATEGORIES_CATALOG    (45 entries, line 169)
                    ├── enterprise_settings table
                    ├── settings_audit_events table
                    ├── settings_proposals table
                    └── storage/enterprise_settings.json  (legacy flat cache)
```

Runtime readers are scattered:

| Runtime | Keys it reads |
|---|---|
| `core/llm_runtime.py` | `llm_provider`, `llm_model`, `llm_base_url`, `llm_api_key`, `llm_temperature`, `llm_max_tokens`, `llm_timeout_seconds`, `ai_master_enablement` |
| `core/executive_decision.py` | `host_emergency_stop`, `ceo_autonomy_level`, `ceo_spending_limit`, `fin_high_expense_approval` |
| `core/spend_governor.py` | `host_emergency_stop`, `host_killswitch_finances`, `cost_global_budget_monthly` (hard-coded `tnt_primary`/`comp_primary`) |
| `core/agent_factory_runtime.py` | `host_emergency_stop`, `wf_autonomous_spawning`, `wf_max_concurrent_agents` |
| `core/browser_use_execution_runtime.py` | `host_emergency_stop`, `gov_kill_switch_active` |
| `core/enterprise_finance.py` | `fin_high_expense_approval` |
| `api_server.py` terminal route | `host_emergency_stop`, `term_execution_enabled`, `term_max_lease_seconds` |
| `core/coworker/background_dispatcher.py` | `llm_max_tokens` |

Those 19 unique keys are the **entire** real enforcement surface.

### 2.3 Existing settings surfaces

| Surface | Location | Notes |
|---|---|---|
| Main settings page | `web/index.html` → `view-settings`, `settings_enterprise.js` | One route, modal/drawer based |
| Settings API (read) | `api_server.py:2192–2250` | `/api/settings`, `/search`, `/category/*`, `/audit`, `/effective`, `/drift` |
| Settings API (write) | `api_server.py:5810–5935` | `/api/settings`, `/category/*`, `/key/*`, `/propose`, `/proposal/*/resolve`, `/test/*`, `/action/*` |
| Legacy JSON mirror | `storage/enterprise_settings.json` | Written on every settings change; **tracked in git** |
| SQLite tables | `enterprise_settings`, `settings_audit_events`, `settings_proposals` | Created in `_ensure_schema()` |
| Existing architecture doc | `docs/architecture/ENTERPRISE_SETTINGS_SPEC.md` | A 1,758-line requirements dump, not an implementation record |

---

## 3. Current inventory

### 3.1 Registry shape

Every definition currently carries only these fields:

`id`, `category`, `name`, `type`, `default`, `scope`, `editable_by`, `risk`,
and optionally `desc`, `min`, `max`, `unit`, `options`, `secret`,
`requires_approval`, `is_ceo_managed`, `doc`.

Field coverage:

| Field | Definitions with it |
|---|---|
| `desc` | 161 / 202 |
| `min` / `max` | 59 / 202 |
| `options` | 47 / 202 |
| `secret` | 5 / 202 |
| `requires_approval` | 4 / 202 |
| `is_ceo_managed` | 2 / 202 |
| `enforced_by` | **0** |
| `required_permission` | **0** |
| `allowed_scopes` | **0** |
| `sensitive` (separate from secret) | **0** |
| `requires_restart` | **0** |
| `validation` (declarative) | **0** |
| `plan` / feature gate | **0** |

### 3.2 Distribution

**By declared scope:** Company 101, Host 88, User 13.

These are only labels today. The resolver ignores the `scope` column for
resolution; it stores whatever `scope` was last written (default `"Company"`)
and always walks the company chain.

**By editability:** `OWNER` 193, `SHARED` 5, `READ_ONLY` 4.

`SHARED` has no gate at all; `OWNER` is checked once in
`update_single_setting`; `READ_ONLY` is correctly rejected.

**By risk:** LOW 75, MEDIUM 48, HIGH 60, CRITICAL 19.

**By control type:** toggle 70, number 50, select 39, text 15, currency 7,
multiselect 6, token 5, status 4, radio 2, slider 2, button_action 2.

### 3.3 Categories

The 45 backend categories collapse into 32 UI domains. This is helpful for a
migration: category IDs and setting keys can stay stable while the UI is
reorganized. The existing service already has `DOMAIN_ALIASES` and
`DOMAIN_CHILD_CATEGORIES` for exactly this mapping.

| Group | Category | Settings | Declared scope |
|---|---|---:|---|
| Identity | `account` — Account | 8 | User:8 |
| Identity | `host` — Host & Sovereignty | 4 | Host:4 |
| Identity | `company` — Company | 10 | Company:10 |
| Identity | `organization` — Organization | 2 | Company:2 |
| Identity | `users` — Users & Access | 6 | Company:6 |
| AI Executive | `ai` — AI Global Policy | 3 | Host:3 |
| AI Executive | `ai_providers` — AI Models & Providers | 13 | Host:13 |
| AI Executive | `ai_ceo` — AI CEO | 6 | Company:6 |
| AI Executive | `workforce` — AI Workforce | 5 | Company:5 |
| AI Executive | `agent_factory` — Agent Factory | 1 | Company:1 |
| AI Executive | `missions` — Missions & Autonomy | 2 | Company:2 |
| Execution | `workflows` — Automation & Workflows | 5 | Company:5 |
| Execution | `tools` — Tools & Capabilities | 5 | Host:2, Company:3 |
| Execution | `mcp` — MCP Servers | 5 | Company:5 |
| Execution | `a2a` — A2A / Agent Network | 5 | Company:5 |
| Execution | `desktop` — Desktop / Coworker | 5 | Host:5 |
| Execution | `browser` — Browser & Web Execution | 5 | Host:5 |
| Execution | `terminal` — Governed Terminal | 5 | Host:5 |
| Execution | `openhands` — OpenHands / Code Execution | 1 | Company:1 |
| Business | `integrations` — Integrations | 5 | Company:5 |
| Business | `data` — Data & Knowledge | 5 | Company:5 |
| Business | `files` — Files & Documents | 1 | Company:1 |
| Business | `records` — Records & Business Data | 1 | Company:1 |
| Business | `communication` — Communication & Dispatch | 5 | Company:5 |
| Business | `finance` — Finance & Ledgers | 5 | Company:5 |
| Business | `notifications` — Notifications & Alerts | 5 | Company:5 |
| Governance | `approvals` — Approvals & Decision Center | 1 | Company:1 |
| Governance | `governance` — Governance & Constitution | 5 | Host:5 |
| Governance | `privacy` — Privacy & Data Protection | 5 | Company:5 |
| Governance | `compliance` — Compliance & Regulations | 1 | Company:1 |
| Governance | `audit` — Audit & Evidence Ledger | 5 | Host:5 |
| Governance | `security` — Security & Identity Policy | 6 | Host:6 |
| Platform | `usage` — Usage & AI Costs | 2 | Host:1, Company:1 |
| Platform | `billing` — Billing & Subscriptions | 3 | Company:3 |
| Platform | `api` — API & Developer Platform | 5 | Host:5 |
| Platform | `webhooks` — Webhooks & Events | 5 | Company:5 |
| Platform | `localization` — Localization & Locale | 7 | Company:7 |
| Platform | `appearance` — Appearance & UX | 5 | User:5 |
| Platform | `recovery` — Backup & Disaster Recovery | 5 | Host:5 |
| Platform | `monitoring` — Monitoring & Reliability | 5 | Host:5 |
| Platform | `enterprise` — Enterprise Administration | 7 | Host:7 |
| Platform | `features` — Feature Flags | 1 | Host:1 |
| Platform | `advanced` — Advanced & Diagnostics | 4 | Host:4 |
| Platform | `diagnostics` — System Diagnostics | 5 | Host:5 |
| Platform | `danger` — Danger Zone | 2 | Host:2 |

### 3.4 Storage and resolution today

`enterprise_settings` is keyed by `(tenant_id, company_id, setting_key)`.
`scope` is a free-text column (`Host`, `Company`, `User`) but is not part of the
key and is not used for resolution.

`get_effective_setting(tenant, company, key)` walks:

1. exact `(tenant, company, key)`;
2. `(tenant, "comp_primary", key)` if the company is not `comp_primary`;
3. `("tnt_primary", "comp_primary", key)` if the tenant is not `tnt_primary`;
4. the registry default;
5. the supplied fallback.

Consequences:

- There is **no Organization scope**, **no Department scope**, **no Agent
  scope**, **no User scope**, and **no lock**.
- The "primary company" is being used as a stand-in for organization defaults.
- A new tenant with no values inherits `tnt_primary`'s values. If the platform
  tenant has configured `llm_api_key`, a new tenant can inherit the platform's
  provider credential. That is a cross-tenant configuration and secret bleed,
  not just a defaulting convenience.
- The in-process cache is a plain dict with no TTL, no bound, and no
  cross-process invalidation. Writes clear exact keys in one process; other
  worker processes can serve stale values indefinitely.

### 3.5 API surface today

Read endpoints (authenticated, but **no permission check**):

- `GET /api/settings`
- `GET /api/settings/search?q=`
- `GET /api/settings/category/{category}`
- `GET /api/settings/audit?category=&actor=&risk_level=&limit=`
- `GET /api/settings/effective`
- `GET /api/settings/drift`

Write/action endpoints:

- `POST /api/settings` — accepts a nested or flat object; loops over keys.
- `POST /api/settings/category/{category}` — bulk save.
- `POST /api/settings/category/{category}/reset` — rewrites defaults.
- `POST /api/settings/key/{key}/reset` — rewrites one default.
- `POST /api/settings/key/{key}/rotate` — invents a `tok_sec_…` value.
- `POST /api/settings/key/{key}/revoke` — writes `"REVOKED_BY_HOST"`.
- `POST /api/settings/action/{action}` — danger-zone actions.
- `POST /api/settings/key/{key}` — single value write.
- `POST /api/settings/propose` — create proposal.
- `POST /api/settings/proposal/{id}/resolve` — approve/reject.
- `POST /api/settings/test/{target}` — run a live diagnostic.

### 3.6 UI surface today

`web/settings_enterprise.js` is a single 2,581-line module. It has:

- a hub of 32 domains in 6 pillars;
- domain detail pages with cards, controls, an inspector drawer, a change
  preview modal, an audit drawer, and a diagnostics modal;
- a settings search box with `Cmd/Ctrl+K`;
- a scope dropdown in the domain header (`Host`, `Company`, `Department`,
  `User`);
- a bottom save bar and a dirty-state machine.

The scope dropdown is **cosmetic**: `setScope()` only re-renders with a new
`activeScope`; the value is never sent to the server and never affects
resolution. The header also hardcodes
`"Inherited: Host Sovereign Baseline"`. `resetToInherited()` calls the
category reset endpoint, which writes registry defaults rather than deleting
the company override. The per-card "Effective Runtime" bar and
"Merkle Evidence: SHA-256 Ledger Sealed" text are generated from service fields
that are not proof of enforcement.

---

## 4. What is real vs decorative

### 4.1 The 19 keys with a runtime reader

These are the only settings that can currently change system behaviour:

| Key | Reader | What actually happens | Caveat |
|---|---|---|---|
| `ai_master_enablement` | `core/llm_runtime.py:230` | Sets LLM `enabled` | Only gates LLM calls, not agents/browser/terminal |
| `llm_provider` | `core/llm_runtime.py:218` | Selects provider | Env fallback; provider list is code-driven |
| `llm_model` | `core/llm_runtime.py:219` | Selects model | No per-role routing |
| `llm_base_url` | `core/llm_runtime.py:220` | Custom endpoint | No URL allowlist |
| `llm_api_key` | `core/llm_runtime.py:221` | Provider credential | Plaintext at rest; see §5 |
| `llm_temperature` | `core/llm_runtime.py:222` | Sampling temperature | No per-agent override |
| `llm_max_tokens` | `core/llm_runtime.py:223`, `core/coworker/background_dispatcher.py` | Token cap | Global, not per-role |
| `llm_timeout_seconds` | `core/llm_runtime.py:224` | Request timeout | No retry/backoff setting |
| `ceo_autonomy_level` | `core/executive_decision.py:131` | Adds human approval for Levels 0–2 | String matching, not a typed enum |
| `ceo_spending_limit` | `core/executive_decision.py:132` | CEO approval threshold | Company-scoped, but no lock |
| `fin_high_expense_approval` | `core/executive_decision.py:133`, `core/enterprise_finance.py:237` | Approval threshold | Currency/units mixed (USD/INR) |
| `host_emergency_stop` | 4 runtime readers + terminal route | Halts missions, browser, spend, terminal | One global flag; no per-company pause |
| `host_killswitch_finances` | `core/spend_governor.py:102` | Halts financial spend | Hard-coded `tnt_primary`/`comp_primary` |
| `gov_kill_switch_active` | `core/browser_use_execution_runtime.py:433` | Halts browser | Not read by terminal or spend |
| `cost_global_budget_monthly` | `core/spend_governor.py:105` | Per-request spend cap | Compared per request, not against monthly accumulated spend; global across companies |
| `wf_max_concurrent_agents` | `core/agent_factory_runtime.py:125` | Caps active agents | `min(tenant quota, setting)`; tenant quota is env-only |
| `wf_autonomous_spawning` | `core/agent_factory_runtime.py:121` | Blocks child agents when off | Only when `parent_agent_id` is set |
| `term_execution_enabled` | `api_server.py:6223` | Blocks terminal execution | One route; other executors may bypass |
| `term_max_lease_seconds` | `api_server.py:6228–6239` | Caps command timeout | Only the HTTP terminal route |

Every one of these is still missing a lock, a scope-specific override, a
permission check on the write path, and a provenance display. So even the
"real" 19 are only half-real.

### 4.2 The 183 keys without an external reader

Of these:

- **2** are executable actions, not values: `danger_revoke_all_sessions`,
  `danger_purge_telemetry`. They are handled inside
  `execute_button_action()` in the settings service. They are not configuration
  and should move to a separate Danger Zone action API with re-authentication.
- **4** are read only by the settings service to display an "effective" value:
  `browser_ssrf_protection`, `sec_require_mfa`, `audit_immutability_mode`,
  `audit_ledger_hashing`.
- **177** have no reader at all, inside or outside the settings subsystem.
  They are pure decoration: the UI shows a control, the value is persisted, and
  nothing consumes it.

Examples of high-risk decorative settings that are currently shown as if they
work:

| Key | Shown default | Why it matters |
|---|---|---|
| `sec_require_mfa` | `true` | No MFA enforcement path reads it; the "runtime" helper returns `True` unconditionally |
| `sec_enforce_ip_allowlist` | `false` | No IP allowlist enforcement |
| `sec_session_duration_hours` | `12` | Auth token lifetime is not read from this key |
| `usr_require_hardware_passkey` | `false` | No passkey enforcement |
| `priv_pii_masking` | `true` | No masking path reads it |
| `data_pii_auto_redaction` | `true` | No redaction path reads it |
| `browser_ssrf_protection` | `true` | Browser SSRF guard has no reader |
| `term_network_isolated` | `true` | Terminal sandbox network policy has no reader |
| `tools_authority_ceiling` | `ASK_ME` | Tool authority is not gated by this value |
| `gov_two_person_rule` | `true` | No two-person approval path reads it |
| `rbac_two_person_rule` | `true` | No two-person approval path reads it |
| `audit_immutability_mode` | `STRICT_APPEND_ONLY` | Table has no append-only trigger |
| `audit_ledger_hashing` | `SHA-256 (Merkle Tree)` | No Merkle chain is maintained for settings |
| `rec_auto_snapshot_frequency` | `Every 6 Hours` | No scheduler reads it |
| `ent_saml_sso_enforced` | `false` | No SAML/OIDC enforcement path |
| `cost_hard_stop_at_threshold` | `true` | Spend governor does not read it |
| `notify_critical_sms` | `true` | No notification dispatcher reads it |
| `mcp_enforce_tls` | `true` | No MCP transport check reads it |

This is the single largest product-risk finding: **the UI currently promises
security, compliance, backup, and spend controls that do not exist.**

### 4.3 Fabricated or misleading proof surfaces

These are separate from "decorative" and are more serious because they assert
that enforcement was verified:

1. **Hard-coded category summaries.**
   `_get_category_summary_value()` returns strings such as
   `"Primary: Gemini 3.8 Flash"`, `"Max Agents: 16"`, `"Monthly Cap: ₹100,000"`,
   `"MFA: Passkey Required"`, `"Snapshot: Every 6h"`, and
   `"SCIM Sync: Active"`. These are not derived from stored values. Several
   contradict the registry defaults (the default provider is
   `Embedded Free (zero-config)`, and the spend cap is USD, not INR).

2. **Drift check always succeeds.**
   `check_runtime_drift()` never compares runtime state to stored state. It
   returns `status: "IN_SYNC"` and `drift_detected: False` unconditionally.
   The qualification test `test_gate_l_runtime_drift_verification` asserts this
   fake success.

3. **Fake runtime verification.**
   `_get_effective_runtime_value()` returns:
   - `sec_require_mfa` → `True`, `"ACTIVE"` regardless of the configured value;
   - `audit_ledger_hashing` → `"SHA-256 (Merkle Tree)"`, `"VERIFIED"`;
   - `audit_immutability_mode` → `"STRICT_APPEND_ONLY"`, `"VERIFIED"`.

   The UI renders these in the "Effective Runtime" bar as if they were live
   proof.

4. **Unconditional audit approval.**
   Every `settings_audit_events` row is written with
   `approval_status = 'APPROVED'`, and `requires_approval` is never consulted
   on write. The 4 settings marked `requires_approval` can be changed directly.

5. **Unconditional "sealed" language.**
   The UI card says "Merkle Evidence: SHA-256 Ledger Sealed". The audit row
   stores `sha256(tenant:company:key:old:new:time:actor)` with no previous-hash
   link. It detects nothing if a row is edited, deleted, or reordered; the
   table accepts `UPDATE` and `DELETE`.

---

## 5. Security findings

Ordered by severity. File:line references are from the snapshot above.

### S1 — Critical: role spoofing on settings writes

`api_server.py:5889` and `:5827` read the caller's role from the
`X-User-Role` request header and default to `"OWNER"`. The service then uses
that value for its `editable_by=OWNER` gate. The verified Bearer token also
contains a role, but it is not used here.

Impact: any authenticated user of any role can send `X-User-Role: OWNER` and
change any `OWNER`-only setting, including spend caps, autonomy, emergency
stops, and security policy. `X-User-Name` is likewise trusted for the audit
actor. The generic `POST /api/settings` handler does not pass a role at all, so
it falls through to the default `OWNER`.

The qualification tests currently encode this design by sending
`X-User-Role` themselves; they do not prove that a real non-owner is blocked.

### S2 — Critical: no server-side permission model for reads

Every authenticated user can `GET /api/settings`, every category, every audit
event within the tenant, and every search result. There is no
`settings.read`, `audit.read`, or `secrets.manage` check. A company user can
read another company's settings inside the same tenant because the audit and
search paths are tenant-scoped, not company-scoped, and because any authenticated
user can request any `company_id` that belongs to the tenant.

### S3 — Critical: secrets are plaintext at rest and in git

The 5 secret-classified keys are stored as ordinary JSON in
`enterprise_settings.setting_value_json`. `_propagate_to_runtime()` then writes
the same values to `storage/enterprise_settings.json`, which **is tracked in
git**. The tracked `storage/roboassistant.db` also contains the rows. The
snapshot contains values for `ai_gemini_api_token`,
`api_developer_key_vault`, `mcp_auth_token`, and
`integ_webhook_signature_secret` (some are test placeholders, but the storage
model is the problem). `llm_api_key` is also accepted and written the same way.

There is no encryption, no key ID, no last-4, no rotation history, and no
usage tracking. `secret=True` only masks the value in two display paths.

The registry also ships **look-alike secret defaults** in source:
`"AIzaSy••••…"`, `"mcp_sec_live_…"`, `"whsec_live_…"`, and
`"zapi_live_…"`. They are stored as real default values and displayed as
configured credentials. They should be treated as unconfigured and never
seeded.

### S4 — Critical: secret read-back through search

`search_settings()` returns `configured_value` and `effective_value` for every
matching definition, without applying the `secret` mask. Therefore:

```
GET /api/settings/search?q=api
```

can return the raw stored secret for `llm_api_key`, `ai_gemini_api_token`,
`mcp_auth_token`, `integ_webhook_signature_secret`, and
`api_developer_key_vault`. The category detail endpoint masks the same values,
so the leak is easy to miss in UI review.

### S5 — High: cross-tenant fallback can leak platform configuration

`get_effective_setting()` falls back to `("tnt_primary", "comp_primary", key)`
for every other tenant. A newly created tenant with no value for
`llm_api_key`, `llm_base_url`, or any other key inherits the platform tenant's
configured value. At minimum this is configuration bleed; for secrets it is a
credential leak. Every tenant must have its own resolved values or an explicit
platform-level default that is safe to share.

### S6 — High: approval and AI-CEO boundaries are metadata only

- `requires_approval` is never checked on write.
- `resolve_proposal()` accepts any `decision` string, from any authenticated
  user, with no role or actor-type check.
- `proposed_by` is free text supplied by the client; an agent can claim to be a
  human.
- An AI CEO can create a proposal to raise `ceo_spending_limit` or
  `ceo_autonomy_level` and a human can approve it; the code does not prevent the
  CEO from proposing or self-approving.
- `is_ceo_managed` is unused.
- No `actor_type` (human/agent/system) is stored, so the audit cannot
  distinguish them.

### S7 — High: the audit ledger is not append-only and is not company-scoped

- `settings_audit_events` has no trigger preventing `UPDATE` or `DELETE`.
- `evidence_hash` is a single SHA-256 over a concatenated string; it is not
  chained to the previous event, so deletion/reordering is undetectable.
- No `request_id`, IP, user agent, actor type, or approval ID is stored.
- `get_audit_events()` filters by `tenant_id` only; the `company_id` parameter
  is accepted but not used. A user in Company A can read Company B's settings
  audit within the same tenant.
- Only `secret=True` values are redacted. Text settings that contain PII
  (email, phone, SMTP host, domain names) are stored in the clear, and there is
  no `sensitive` classification.

### S8 — High: bulk writes are not atomic and errors are swallowed

- `bulk_save_category()` calls `update_single_setting()` per key; each call
  commits. A failure in the middle leaves earlier keys written and later keys
  untouched, but the API returns an error as if nothing was saved.
- `POST /api/settings` loops over keys and **ignores every result**, then
  returns `{"success": true, "saved": true}` even if all writes failed.
- The UI's `commitBatchSave()` does not send `expected_version`, so the
  optimistic-concurrency mechanism is effectively unused by the product.
- The UI does not send `X-User-Role`; the server defaults it to `OWNER` (see
  S1). A non-owner using the UI therefore writes as `OWNER`.

### S9 — High: secret rotation and revocation are destructive placeholders

- `rotate_secret_token()` invents `tok_sec_<random>` and stores it as the
  provider credential. It does not call the provider, and the invented token
  will not authenticate. A rotation silently breaks the integration.
- `revoke_secret_token()` stores the string `"REVOKED_BY_HOST"`. That is a
  non-empty string, so it is passed to providers as an API key and causes
  authentication failures rather than a clean "revoked" state.
- Neither action records a new secret version, last-4, or usage.

### S10 — Medium: no dedicated settings write protection

Authentication is enforced for `/api/*`, and state-changing routes require a
Bearer token, which mitigates classic cookie CSRF. However:

- there is no dedicated rate limit for settings writes (only generic tenant
  fairness);
- there is no `Origin`/`Referer` check on state-changing requests;
- body size is capped at 10 MB globally, but there is no per-field limit beyond
  the 2,048-character check for text/token values;
- the dangerous action endpoint has no typed confirmation, re-authentication,
  or `security.manage` check;
- no CSRF token exists for any future cookie-based flow.

### S11 — Medium: backend/deployment settings are env-only and invisible

`.env.production.example` exposes platform controls that are not in the
settings registry and are not shown in the UI:

- `ZONATA_SANDBOX_TIMEOUT_SECONDS`, `ZONATA_RATE_LIMIT_PER_MINUTE`,
  `ZONATA_ENFORCE_CONTAINER_SANDBOX`, `ZONATA_ALLOW_HOST_FALLBACK`,
  `ZONATA_CLEAN_STARTUP`, `NATS_URL`, `S3_ACCESS_KEY`, and
  `OTEL_EXPORTER_OTLP_ENDPOINT` are defined in the template but **not read
  anywhere** in the repository.
- `PILOT_MAX_CONCURRENCY`, `PILOT_MAX_RPM`, `MAX_DESIGN_PARTNER_ORGS`,
  `TEMPORAL_HOST`, some `S3_*` names, and `DATABASE_URL` are read by
  infrastructure code but have no read-only platform display.
- `ZONATA_LLM_*` env vars are fallbacks in `llm_runtime` but are not surfaced
  as "Platform default (env)" values.

The prompt requires existing env vars to keep working and to appear as
read-only platform defaults. Today they keep working but are invisible.

### S12 — Medium: no environment separation for settings

There is no staging/production dimension. A value written from a staging
deployment is stored in the same table as production values. The prompt asks
for environment-scoped platform/infrastructure settings.

---

## 6. Gaps against the requested information architecture

The prompt's 16 top-level sections versus what exists:

| # | Requested section | Current coverage | Gap |
|---|---|---|---|
| 1 | General & Organization | `account`, `company`, `organization`, `localization` | No org profile/branding, no company presets, no fiscal-year/date-format enforcement |
| 2 | Companies | `company` (10 keys) | No list/switcher in Settings, no clone/export, no ownership transfer, no status lifecycle UI |
| 3 | Team & Access | `users`, `enterprise`, `security` | No member/invite UI, no role-permission matrix, no SSO/SCIM enforcement, no MFA enforcement, no session policy enforcement, no guest/auditor access |
| 4 | AI Agents & Employees | `ai_ceo`, `workforce`, `agent_factory`, `missions`, `workflows`, `tools`, `mcp`, `a2a`, `desktop`, `browser`, `terminal`, `openhands` | Autonomy and caps exist partially; no speed presets, no model routing, no behavior/tone policy, no permission matrix, no SOP/KRA templates, no memory isolation, no open-source agent install policy, no per-company pause |
| 5 | Spending & Budgets | `usage`, `finance`, `billing` | No scope budgets, no soft/hard caps, no daily/per-task limits, no alert thresholds, no auto-pause, no cost breakdown, no forecasting, no allocation tags |
| 6 | Integrations | `integrations`, `api`, `webhooks`, `mcp` | No connector health/OAuth status, no per-company mapping, no provider-key rotation/usage, no public API token scopes/IP allowlist, no MCP registry/allowlist/review queue, no tool catalogue |
| 7 | Browser & Automation | `browser`, `desktop` | No browsing style/live view, domain allow/block lists, politeness, proxy/region, cookie vault, download policy, screenshot retention, per-action approval, desktop permissions |
| 8 | Security & Compliance | `security`, `privacy`, `compliance`, `governance`, `audit` | No posture score, key management, IP allowlist, egress policy, terminal sandbox, dependency scanning, anomaly alerts, prompt-injection level, DLP, residency, compliance packs, incident response |
| 9 | Reports & Documents | none dedicated | No scheduled reports, templates, PDF/DOCX/XLSX output, email delivery/SPF/DKIM, share-link policy, export formats, retention |
| 10 | Notifications | `notifications` | No channel credentials, per-event matrix, quiet hours, digests, escalation chains, owner assistant channel |
| 11 | Data, Storage & Backups | `data`, `files`, `records`, `recovery` | No storage dashboard/quota, add-on storage, auto-expand, retention tiers, S3 config, backup schedule/restore/test, RPO/RTO, per-company backups, erasure workflow |
| 12 | Infrastructure & Stack | `monitoring`, `diagnostics`, `advanced`, `features` | No environment separation, deployment info, provider adapters, release channel, custom domains/SSL, maintenance mode, health dashboard, tracing/error tracking |
| 13 | Billing & Plan | `billing`, `usage` | No plan/seats/invoices/payment methods/tax IDs/add-ons/chargeback/agency mode |
| 14 | Appearance & Accessibility | `appearance` | Theme/high-contrast/reduced-motion/density/font-scale exist as records but are not applied by the app |
| 15 | Audit & Activity | `audit` | Read-only list exists; no company filter, search, export, SIEM webhook, retention, or append-only guarantee |
| 16 | Advanced & Danger Zone | `advanced`, `danger` | 2 actions exist; no experimental flags, event bus, ownership transfer, delete/reset company flows |

The current IA is not the requested IA. The 32-domain UI is a reasonable
starting point, but the 16-section structure needs to become the top-level
navigation.

---

## 7. Migration and compatibility risks

### R1 — Ambiguous Host-scope rows

Today `scope="Host"` is stored per company. It is not clear whether a row means
"platform default", "organization default", or "this company's value". If the
migration promotes all Host rows to Organization scope, one company's value can
silently become the default for every company in the tenant. If it keeps them
at Company scope, the "organization default" concept remains empty.

**Mitigation:** dry-run the migration, produce a diff report per tenant/company,
keep `enterprise_settings` untouched during the transition, and default to
Company scope + explicit organization defaults seeded from the registry. Lock
nothing automatically.

### R2 — Removing the `tnt_primary` fallback changes behaviour

Tenants that currently rely on the global fallback will start seeing registry
defaults instead of the platform tenant's values. This is the correct security
behaviour, but it can change provider/model/spend behaviour. Seed explicit
organization values for `tnt_primary` before cutting over, and show a
"Platform default" provenance for env-derived values.

### R3 — Secrets cannot be migrated blindly

Some values are real, some are test placeholders (`REVOKED_BY_HOST`,
`AIzaSy••••…`, `mcp_sec_live_…`, `whsec_live_…`, `zapi_live_…`). Encrypting
placeholders creates the illusion of configured credentials. **Mitigation:**
classify each value as real / placeholder / revoked; migrate only real values;
mark the rest unconfigured; require the owner to re-enter. Keep a backup note
and never delete the old column until the new vault is verified.

### R4 — Master-key loss makes secrets unrecoverable

Envelope encryption needs a stable master key
(`ZONATA_SETTINGS_MASTER_KEY`, 32 bytes, or a 0600 key file in development).
If the key is lost, existing ciphertext cannot be recovered. **Mitigation:**
document the key location, fail closed on secret writes without a key, and
provide a re-encrypt/rotate-master-key command that does not require the old
plaintext.

### R5 — Existing tests encode the current (insecure) behaviour

- `tests/test_settings_enterprise_qualification.py` sends `X-User-Role` and
  expects it to authorize writes (S1).
- `test_gate_l_runtime_drift_verification` asserts the fake `IN_SYNC`.
- `tests/test_enterprise_settings_center.py` expects 45 categories and the
  current category IDs.
- The qualification suite isolates its database and `ZONATA_SETTINGS_PATH`, but
  other suites and direct service imports can still write the tracked
  `storage/roboassistant.db` and evidence ledger. Those artifacts must be
  restored before commits.

**Mitigation:** preserve category IDs, setting keys, and the
`settings_service` facade; update only the tests whose expected contract is
being deliberately hardened; run tests against the isolated DB helper; restore
tracked artifacts before commits.

### R6 — Two database engines

The code supports SQLite and PostgreSQL. DDL, triggers, and `ON CONFLICT`
syntax must be provided for both. This environment has no PostgreSQL server,
so the PostgreSQL migration can be written and reviewed but not executed here.
**Mitigation:** add dialect-specific migration files; test SQLite locally; mark
PostgreSQL verification as a staging gate.

### R7 — UI rewrite risk

The current settings UI is 2,581 lines and is the only settings surface. A
big-bang replacement risks losing working flows (search, dirty state, audit
drawer). **Mitigation:** keep the legacy page at `/settings-legacy` behind a
flag until the new shell has parity for the enforced settings; migrate
incrementally.

### R8 — In-process cache and multi-worker staleness

The current cache has no invalidation across processes. A new resolver with a
DB revision counter and change events is required before running multiple
workers. Until then, settings changes can appear applied in one worker and not
another.

---

## 8. Proposed implementation plan (approval gate)

### 8.1 Principles and decisions

1. **Keep the stack.** Python stdlib + vanilla JS + SQLite/PostgreSQL +
   existing `cryptography`. No React/Vue/Next, no new state library.
2. **Stable keys, new IA.** Keep all 202 setting IDs and 45 category IDs as
   aliases. Add the 16 top-level sections as navigation; map categories into
   them. This avoids breaking deep links, tests, and existing data.
3. **No decorative controls.** The registry gains a `status` field:
   `live`, `coming_soon`, or `hidden`. A setting may be `live` only if it has a
   non-empty `enforced_by` and an integration test. Everything currently
   decorative becomes `coming_soon` and is rendered in a clearly labelled
   "Coming soon" group, not as a working control.
4. **Additive, reversible migrations.** New tables first; dual-read/dual-write;
   feature flag `ZONATA_SETTINGS_RESOLVER_V2`; keep
   `enterprise_settings` unchanged until verification.
5. **Fail closed on security.** No secret write without a master key; no
   agent write to security/spend/permission/lock keys; no read of a secret
   after save.
6. **No data deletion.** Migration only copies and classifies. A separate,
   explicitly approved cleanup step removes plaintext after verification and a
   backup note.

### 8.2 Phase 1 — Schema, registry, and migration design (checkpoint 2)

Deliverables:

- `core/settings/` package:
  - `registry.py` — typed definitions, validation functions, `enforced_by`,
    `allowed_scopes`, `required_permission`, `sensitive`, `requires_restart`,
    `status`, `plan_gate`.
  - `models.py` — `ScopeType` (`platform`, `organization`, `company`,
    `department`, `agent`, `user`), `EffectiveSetting`, `SecretRef`,
    `ApprovalRequest`.
- Migration files (common + pg):
  - `settings_values` as specified in the prompt, with
    `unique(scope_type, scope_id, key)` and `version`.
  - `settings_audit` append-only, with actor type, request ID, IP, redacted
    old/new, reason, version, previous hash.
  - `secrets` with ciphertext, nonce, key ID, last4, created/rotated/last-used.
  - `settings_presets`, `roles`, `permissions`, `role_permissions`,
    `user_company_roles`, `settings_approvals`.
  - `settings_environments` (staging/production) for platform scopes.
  - Add `settings_migrations` records and a down migration.
- A **dry-run migration tool**:
  - reads `enterprise_settings`;
  - classifies Host/Company/User rows;
  - writes a JSON report of proposed scope moves and conflicts;
  - writes nothing unless `--apply`.
- Registry coverage report: for each key, `enforced_by` status, current reader,
  and proposed status (`live` / `coming_soon` / `hidden`).

Exit criteria: schema applies cleanly on SQLite; dry-run report reviewed;
existing tests still pass with the legacy service; no UI change yet.

### 8.3 Phase 2 — Backend services

Deliverables:

- **Resolver** (`core/settings/resolver.py`):
  - broadest-lock-first, then most-specific-value, then default;
  - typed return with provenance, lock owner, version, restart flag;
  - per-process cache keyed by full scope context, invalidated by a DB revision
    counter and an in-process change event;
  - env-derived platform defaults for existing `ZONATA_*` keys, read-only.
- **RBAC** (`core/settings/rbac.py`):
  - permissions seeded as listed in the prompt;
  - role resolution from the verified token, never a header;
  - scope-aware checks and company membership;
  - `settings.read/write/lock`, `secrets.manage`, `security.manage`,
    `billing.manage`, `agents.manage`.
- **Secrets vault** (`core/settings/secrets.py`):
  - AES-GCM envelope encryption via `cryptography`;
  - write-only API, last4, rotation, usage tracking;
  - no plaintext in logs, audit, JSON mirror, or API responses;
  - explicit "unconfigured" state for placeholders.
- **Audit** (`core/settings/audit.py`):
  - hash chain per tenant; append-only trigger; request metadata; redaction.
- **Approvals** (`core/settings/approvals.py`):
  - human/agent actor types; sensitive-key policy; two-person rule; AI CEO
    cannot approve its own proposal or raise its own limits.
- **API v2** under `/api/settings/v2/*`:
  - registry, effective + provenance, scoped write with version, lock/unlock,
    bulk apply with impact preview, presets/copy, secrets, approvals, audit,
    compare.
  - Legacy `/api/settings*` remains as a compatibility wrapper but delegates to
    the resolver and never trusts `X-User-Role`.
- **Runtime wiring** for the 19 live keys first, then the highest-risk
  decorative keys (security, spend, emergency controls). Each gets an explicit
  `enforced_by` entry and a test.

Exit criteria: resolver and lock precedence tests pass; RBAC tests prove
non-owner denial; secret redaction test passes; audit immutability test passes;
all 19 existing live keys still behave the same or better.

### 8.4 Phase 3 — UI shell and design system

Deliverables (vanilla JS, existing tokens extended):

- New settings route with the 16-section sidebar, colored icon tiles, search at
  the top, inset grouped rows, 10–12 px radii, hairline separators.
- Scope switcher `Organization ▸ [Company ▾]` plus Department/Agent/User
  context where applicable.
- Row states: Default / Inherited from X / Overridden here / Locked by Owner;
  effective-value popover with provenance; "Reset to inherited"; lock control
  for owners.
- Controls: switch, segmented, stepper, slider, picker, token/chip input,
  masked secret + reveal-once + rotate, usage meter, status pill, empty state,
  skeleton.
- Instant-apply toggles with Undo toast; Save/Cancel for forms; impact preview
  for risky changes; confirmation sheets with typed confirmation and
  re-authentication for critical actions.
- Command palette (`Cmd/Ctrl+K`), deep-linkable URLs, compare view, dark mode,
  reduced motion, keyboard navigation, screen-reader labels, 360 px responsive.
- Legacy page available behind a flag until parity.

Exit criteria: accessibility pass (keyboard + labels + contrast); no control is
rendered without a `live` registry status; screenshot review in light/dark.

### 8.5 Phase 4 — Sections 1–6, wired to enforcement

Order per the prompt:

1. General & Organization — org profile, branding, language/timezone/currency,
   fiscal year, formats, defaults for new companies, presets.
2. Companies — list/switcher, profile, industry, mode, status, residency,
   clone/export, ownership transfer.
3. Team & Access — members, invites, role/permission matrix, SSO/SCIM,
   MFA enforcement, session policy, guest/auditor, per-user tokens, approvals.
4. AI Agents & Employees — autonomy/escalation, speed presets (Eco/Balanced/
   Turbo), model routing, behavior/tone, permission matrix, SOP/KRA/KPI,
   memory, OSS-agent install policy, emergency pause/kill switch.
5. Spending & Budgets — scoped budgets, soft/hard caps, daily/monthly/per-task
   limits, alerts, auto-pause, approval thresholds, cost breakdown,
   forecasting, allocation tags, currency.
6. Integrations — connectors, OAuth/health/sync, provider keys, public API
   tokens, webhooks, MCP registry/allowlists/review queue, tool catalogue.

For each section: wire existing keys where real code exists; add new keys only
with an enforcement point; mark the rest `coming_soon`. No section is "done"
because the UI renders.

### 8.6 Phase 5 — Sections 7–16

7. Browser & Automation
8. Security & Compliance
9. Reports & Documents
10. Notifications
11. Data, Storage & Backups
12. Infrastructure & Stack
13. Billing & Plan
14. Appearance & Accessibility
15. Audit & Activity
16. Advanced & Danger Zone

Same rule: enforcement first, UI second. Where a provider owns the value (for
example Render or Neon), show read-only status with a link-out or an adapter;
never fake a control.

### 8.7 Phase 6 — Hardening

- Resolver and lock precedence tests (all six scopes, broadest-lock rule).
- RBAC tests for every permission and every scope.
- Secret redaction tests, including search, category detail, audit, logs, and
  error responses.
- Audit completeness and append-only tests (UPDATE/DELETE rejected).
- Migration up/down tests on SQLite; PostgreSQL migration reviewed and run in
  staging.
- E2E: scope switch, override, lock, reset to inherited, bulk apply with
  preview, secret rotate, approval inbox.
- Accessibility audit, performance check (resolver cache hit rate), and a
  security review of the new endpoints.
- Update the tests that encoded `X-User-Role` and fake drift.

### 8.8 Phase 7 — Documentation and final report

- `docs/SETTINGS.md`: registry, how to add a setting, scope rules, permission
  model, secret handling, migration and rollback.
- Regenerate `docs/README.md` index.
- Final report: what was built; what is hidden/`coming_soon` and why; remaining
  security and migration risks; verification evidence.

### 8.9 Branch, commits, and flags

- Feature branch: `feat/enterprise-settings-v2`.
- Small commits: `audit`, `schema`, `registry`, `resolver`, `rbac`, `secrets`,
  `audit-log`, `approvals`, `api`, `ui-shell`, then one per section group.
- Every checkpoint keeps staging deployable. No destructive migration is
  applied without a backup note and a down path.
- Feature flags: `ZONATA_SETTINGS_RESOLVER_V2`, `ZONATA_SETTINGS_UI_V2`,
  `ZONATA_SETTINGS_SECRETS_V2`. Legacy paths remain until verification.

### 8.10 What I will not do without a separate approval

- Delete or rewrite `storage/enterprise_settings.json`,
  `storage/roboassistant.db`, or any existing setting row.
- Rotate or revoke a real provider credential.
- Change production authentication/roles for live users.
- Apply a migration to a production database.
- Remove the legacy settings page.

---

## 9. Defaults I will use unless you object

1. **IA:** 16 top-level sections from the prompt; keep the 45 category IDs and
   202 keys as aliases/sub-sections.
2. **Host-row migration:** keep values at Company scope; seed Organization
   defaults from the registry; copy a value to Organization only when every
   company in the tenant has the same value. Lock nothing automatically.
3. **Secrets:** treat the four look-alike defaults and `REVOKED_BY_HOST` as
   unconfigured; migrate only values that pass a "looks real and not a
   placeholder" check; require re-entry otherwise.
4. **Master key:** require `ZONATA_SETTINGS_MASTER_KEY` in production; in
   development, generate a 0600 local key file and print a warning. Fail closed
   for secret writes if neither exists.
5. **Legacy compatibility:** keep the old `/api/settings*` endpoints as
   wrappers during the transition; never let them bypass the new resolver or
   RBAC.
6. **Rollout:** ship the new UI behind `ZONATA_SETTINGS_UI_V2` with
   `/settings-legacy` available; cut over after the enforced sections pass.
7. **Scope labels:** use "Organization" for the tenant root, "Company" for a
   company, "Department", "Agent / Employee", and "User". "Host" becomes a
   platform-level display label, not a resolution scope.
8. **Environment:** platform/infrastructure settings get a
   `staging`/`production` dimension; company/department/agent/user settings do
   not.

---

## 10. Approval requested

Phase 0 is complete. I am stopping here as instructed. I have **not** run a
migration, changed the database, edited the registry, or touched the UI.

To proceed, I need approval of:

- the audit findings and severity ordering in §5;
- the IA and key-preservation decision in §8.1 and §9.1;
- the Host-row and secret migration defaults in §9.2–§9.4;
- the phase order and the rule that decorative controls become
  `coming_soon` rather than being left live.

After approval I will start with Phase 1 (schema + registry + dry-run migration
report) on `feat/enterprise-settings-v2`, and stop again at checkpoint 2 for
approval before backend/UI implementation.

---

## Appendix A — Evidence index

| Claim | Evidence |
|---|---|
| 202 definitions, 45 categories, 6 groups | `core/settings_service.py:169`, `:266`, `:1442`; AST extraction of the two literals |
| 19 external readers | Cross-reference of all 202 IDs against `core/`, `web/`, `api_server.py` excluding settings service/UI/tests |
| 183 without external reader | Same cross-reference; includes 2 actions and 4 display-only keys |
| 0 `enforced_by` / `required_permission` / `allowed_scopes` | Field-coverage count over all 202 definitions |
| No lock, limited scope chain | `get_effective_setting()` at `core/settings_service.py:1690` |
| Always-`IN_SYNC` drift | `check_runtime_drift()` at `:1898` |
| Fake runtime status | `_get_effective_runtime_value()` at `:1918` |
| Hard-coded summaries | `_get_category_summary_value()` at `:1561` |
| Plaintext secrets in DB/JSON | `update_single_setting()` at `:1932`; `_propagate_to_runtime()` at `:2178`; tracked `storage/enterprise_settings.json` and `storage/roboassistant.db` |
| Secret leak via search | `search_settings()` at `:2341`; `configured_value` / `effective_value` at `:2398–2399` returned unmasked |
| Role spoofing | `api_server.py:5827`, `:5889`, default `"OWNER"`; service gate at `core/settings_service.py:1955` |
| Bulk non-atomic / swallowed errors | `bulk_save_category()` at `:2092`; `POST /api/settings` at `api_server.py:5810` |
| Approval metadata unused | `requires_approval`/`is_ceo_managed` appear only in definitions; `resolve_proposal()` at `:2239` |
| Audit not company-scoped | `get_audit_events()` at `:2296` filters `tenant_id` only |
| Rotation/revocation placeholders | `rotate_secret_token()` at `:2484`; `revoke_secret_token()` at `:2510` |
| UI scope is cosmetic | `setScope()` at `web/settings_enterprise.js:1893`; `commitBatchSave()` at `:1997` does not send scope/version/role |
| Tests encode current behaviour | `tests/test_settings_enterprise_qualification.py:533` (drift), `:102–105` / `:264` (role header) |
| Env-only controls | `.env.production.example`; `core/llm_runtime.py:202–208`; `api_server.py:812–814` |
| No PostgreSQL/browser in this environment | Environment limitation noted in the workspace; no live PostgreSQL or Playwright run was used for this audit |

## Appendix B — Files read for this audit

- `core/settings_service.py`
- `web/settings_enterprise.js`
- `web/index.html`
- `api_server.py` (settings routes, auth context, terminal route)
- `core/db.py` (schema for `users`, `companies`, `departments`, `employees`, `schema_migrations`)
- `core/auth.py` (roles and enforcer)
- `core/llm_runtime.py`, `core/executive_decision.py`, `core/spend_governor.py`,
  `core/agent_factory_runtime.py`, `core/browser_use_execution_runtime.py`,
  `core/enterprise_finance.py`, `core/coworker/background_dispatcher.py`
- `tests/test_enterprise_settings_center.py`
- `tests/test_settings_enterprise_qualification.py`
- `docs/architecture/ENTERPRISE_SETTINGS_SPEC.md`
- `.env.production.example`
- `storage/enterprise_settings.json` and `storage/roboassistant.db` (key names
  and row counts only)
