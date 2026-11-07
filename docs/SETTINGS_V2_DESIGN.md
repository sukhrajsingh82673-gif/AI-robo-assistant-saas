# Enterprise Settings V2 — Design and Phase 1 Record

**Status:** Phase 1 complete. Checkpoint 2 approval required before backend or UI work.
**Branch:** `feat/enterprise-settings-v2`
**Baseline:** `d054f13` plus the Phase 0 audit (`71084c9`).
**Audit:** [`SETTINGS_AUDIT.md`](SETTINGS_AUDIT.md)
**Dry-run evidence:** [`reports/SETTINGS_MIGRATION_DRY_RUN.md`](reports/SETTINGS_MIGRATION_DRY_RUN.md),
[`reports/SETTINGS_MIGRATION_DRY_RUN.json`](reports/SETTINGS_MIGRATION_DRY_RUN.json)

---

## 1. What Phase 1 delivered

Phase 1 adds the schema, the typed registry, the migration splitter, the
read-only dry-run tool, and the tests that keep them honest. It does **not**
change request handling, the resolver used at runtime, the UI, or any stored
setting value.

| Deliverable | File | State |
|---|---|---|
| Canonical, side-effect-free definitions | `core/settings/definitions.py` | Done |
| Scope/status/models and declarative validation | `core/settings/models.py` | Done |
| Typed registry with enforcement metadata | `core/settings/registry.py` | Done |
| 16-section information architecture | `core/settings/sections.py` | Done |
| Portable Settings V2 schema | `migrations/common/0003_settings_v2_schema.sql` | Done |
| SQLite append-only guards | `migrations/sqlite/0004_settings_v2_append_only.sql` | Done |
| PostgreSQL append-only guards | `migrations/pg/0006_settings_v2_append_only.sql` | Done |
| Dialect-aware SQL splitter | `migrations/migration_manager.py` | Done |
| Idempotent schema helper | `core/settings/schema.py` | Done |
| Read-only migration dry-run | `scripts/settings_migration_dry_run.py` | Done |
| Phase 1 tests | `tests/test_settings_registry_phase1.py` | Done |
| Phase 0 audit | `docs/SETTINGS_AUDIT.md` | Done |

### Verified numbers

| Measure | Value |
|---|---:|
| Setting definitions | 202 |
| Categories | 45 |
| Top-level sections | 16 |
| `live` definitions | 19 |
| `coming_soon` definitions | 177 |
| `hidden` definitions | 4 |
| `action` definitions | 2 |
| Category-to-section coverage | 45 / 45 |
| Phase 1 tests | 31 passing |
| Existing settings center tests | 12 passing |
| Existing settings qualification tests | 22 passing |

The `live` count is still 19 because Phase 1 did not invent enforcement. A
definition becomes `live` only when a runtime reader exists and is listed in
`ENFORCED_BY`. Everything else is explicitly `coming_soon` or `hidden`, which
stops the new UI from presenting decorative controls as working ones.

---

## 2. Canonical registry

### 2.1 Source of truth

`core/settings/definitions.py` contains the same 202 definitions, 45
categories, and 6 legacy groups that used to live inside
`core/settings_service.py`. Importing it has no database side effects. The
legacy service imports the same data, so there is one source of truth during
the transition.

### 2.2 Definition fields

Each `SettingDefinition` carries:

| Field | Purpose |
|---|---|
| `key` | Stable setting ID; never renamed by the migration. |
| `section` | One of the 16 top-level navigation sections. |
| `category` | Stable legacy category ID (45 total). |
| `label`, `description` | Display text. |
| `value_type` | `toggle`, `number`, `select`, `text`, `currency`, `multiselect`, `token`, `status`, `slider`, `radio`, `button_action`. |
| `default` | Canonical default. Secret defaults are masked in public output. |
| `validation` | Declarative min/max/options/max-length/integer rules. |
| `allowed_scopes` | Which of Platform, Organization, Company, Department, Agent, User may hold a value. |
| `required_permission` | Permission needed to write the setting. |
| `sensitive` | Redact in audit/API responses (includes secrets and a small explicit PII list). |
| `secret` | Credential: write-only, encrypted, never returned. |
| `requires_restart` | Value needs a restart/reconnect before it takes effect. |
| `enforced_by` | Exact runtime reader; required for `live`. |
| `status` | `live`, `coming_soon`, `hidden`, or `action`. |
| `risk` | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. |
| `editable_by` | Legacy compatibility label. |
| `plan_gate` | Optional plan/feature gate for visibility. |
| `unit` | Display unit for numbers and currency. |
| `legacy_scope` | Original `Host`, `Company`, or `User` label. |
| `requires_approval` | Whether a change needs a human decision. |
| `is_ceo_managed` | Whether the AI CEO may propose changes. |
| `action_id` | Present only for executable danger-zone actions. |

### 2.3 Status policy

```
button_action                      -> action
READ_ONLY or type=status           -> hidden
enforced_by present                -> live
otherwise                          -> coming_soon
```

The registry validator fails construction if:

- a key is duplicated;
- a category or section is unknown;
- a definition has no allowed scopes;
- a permission is not in `KNOWN_PERMISSIONS`;
- a definition is `live` without an `enforced_by` entry or without a matching
  key in `ENFORCED_BY`;
- an `action` has no `action_id`;
- a section other than the intentionally empty Reports & Documents has no
  definitions.

This is intentionally strict. Adding a new visible control requires a real
reader and a test; it cannot silently join the `live` set.

### 2.4 Permissions

`KNOWN_PERMISSIONS` is:

`settings.read`, `settings.write`, `settings.lock`, `secrets.manage`,
`security.manage`, `billing.manage`, `agents.manage`, `users.manage`,
`audit.read`, `infrastructure.manage`, `danger.manage`.

Category defaults map to permissions; secrets always require
`secrets.manage`. Phase 2 will resolve roles from the verified token, never
from `X-User-Role`.

---

## 3. Scope model and resolver

### 3.1 Scope order

```
Platform -> Organization -> Company -> Department -> Agent / Employee -> User
```

`Platform` and `Organization` are broad; `User` is specific. The resolver uses
two orders:

- **Broad to specific** for selecting the broadest lock.
- **Specific to broad** for selecting a value when nothing is locked.

### 3.2 Effective-value algorithm (Phase 2)

```
resolve(key, context):
    definition = registry.require(key)
    scopes     = chain_for(definition.allowed_scopes, context)

    # 1. A lock at any scope wins, broadest first.
    for scope in broad_to_specific(scopes):
        row = read(scope, key)
        if row and row.locked:
            return EffectiveSetting(value=row.value, source=scope,
                                    is_locked=True, locked_by=scope,
                                    provenance="Locked by <scope>")

    # 2. Otherwise the most specific stored value wins.
    for scope in specific_to_broad(scopes):
        row = read(scope, key)
        if row:
            return EffectiveSetting(value=row.value, source=scope,
                                    overridden_here=(scope == context.scope),
                                    provenance="Overridden / Inherited")

    # 3. Platform default, then registry default.
    if env_default(definition):
        return EffectiveSetting(value=env_default, source=Platform,
                                provenance="Platform default (env)")
    return EffectiveSetting(value=definition.default, source=default,
                            provenance="Default")
```

Rules:

- A lock at Platform beats a value at Company.
- A lock at Company beats a value at Department.
- A lock never changes the stored values underneath it; it only wins
  resolution.
- `allowed_scopes` is enforced on write. A User-scoped definition cannot be
  written at Company scope.
- `requires_restart` is carried in the response so the UI can say
  "Restart required" instead of pretending the change is live.

### 3.3 Provenance the UI must show

Every effective value returns:

- `value`;
- `source_scope` and `source_id`;
- `is_locked`, `locked_by_scope`, `locked_by_id`;
- `default_value`;
- `overridden_here`;
- `inherits_from`;
- `provenance` string;
- `version`;
- `requires_restart`;
- `status`.

The four row states are therefore `Default`, `Inherited from <scope>`,
`Overridden here`, and `Locked by <scope>`. "Reset to inherited" deletes the
local row and re-resolves; it does not write the default value.

### 3.4 Cache

Phase 2 will key the per-process cache by the full scope chain and setting key,
and invalidate it through a `settings_revision` counter plus an in-process
change event. Phase 1 only creates the revision table. No resolver cache is
changed yet.

---

## 4. Schema

### 4.1 `settings_values`

```sql
CREATE TABLE settings_values (
    tenant_id   TEXT NOT NULL,
    company_id  TEXT,
    scope_type  TEXT NOT NULL,
    scope_id    TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    value_json  TEXT NOT NULL,
    locked      INTEGER NOT NULL DEFAULT 0,
    version     INTEGER NOT NULL DEFAULT 1,
    updated_by  TEXT NOT NULL,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (scope_type, scope_id, setting_key)
);
```

- `(scope_type, scope_id, setting_key)` is the uniqueness rule.
- `version` powers optimistic concurrency.
- `locked` is intentionally an integer for SQLite/PostgreSQL portability.
- `tenant_id` and `company_id` are denormalised for scoped queries and audit
  filtering. Scope IDs remain the authoritative identity.

### 4.2 `settings_audit`

Append-only. Columns: `audit_id`, `tenant_id`, `company_id`, `scope_type`,
`scope_id`, `setting_key`, redacted `old_value`/`new_value`, `actor`,
`actor_type`, `reason`, `request_id`, `ip_address`, `version`,
`approval_status`, `previous_hash`, `entry_hash`, `created_at`.

- SQLite: `BEFORE UPDATE` and `BEFORE DELETE` triggers raise `ABORT`.
- PostgreSQL: `CREATE RULE ... DO INSTEAD NOTHING` for `UPDATE` and `DELETE`.
  No PL/pgSQL body is required.
- Phase 2 writes `entry_hash = SHA-256(previous_hash || canonical_event)` and
  keeps one chain per tenant.

### 4.3 `secrets`

Write-only credential storage: `secret_id`, `tenant_id`, `company_id`,
`scope_type`, `scope_id`, `name`, `ciphertext`, `nonce`, `key_id`, `last4`,
`created_by`, `created_at`, `rotated_at`, `last_used_at`, `version`.

- AES-GCM envelope encryption using the existing `cryptography` dependency.
- `last4` is derived at write time; plaintext is never stored.
- No API returns `ciphertext`, `nonce`, or plaintext.
- A missing `ZONATA_SETTINGS_MASTER_KEY` fails closed for secret writes in
  production.

### 4.4 Supporting tables

| Table | Purpose |
|---|---|
| `settings_presets` | Reusable company/industry presets. |
| `roles`, `permissions`, `role_permissions` | Permission model. |
| `user_company_roles` | User membership and role per company. |
| `settings_approvals` | Human decision queue with actor type, risk, required approvals, expiry. |
| `settings_environments` | Staging/production dimension for platform scopes. |
| `settings_revision` | Per-tenant revision counter for cache invalidation. |
| `settings_schema_migrations` | Checksums of the settings migration files applied by `ensure_schema`. |

### 4.5 Migration runner compatibility

`migrations/migration_manager.py` previously split SQL on every semicolon.
That breaks SQLite trigger bodies and PostgreSQL dollar-quoted functions. It
now uses `split_sql_statements()`:

- SQLite: `sqlite3.complete_statement`, which understands `BEGIN ... END`.
- PostgreSQL: a small state machine for strings, line/block comments, and
  dollar-quoted bodies.

File versions are ordered so the append-only migration runs after the table
creation: `common/0003` then `sqlite/0004` or `pg/0006`.

---

## 5. Information architecture

The 16 sections are defined once in `core/settings/sections.py` and mapped from
the stable category IDs:

| # | Section | Categories |
|---|---|---|
| 01 | General & Organization | `account`, `organization`, `localization` |
| 02 | Companies | `company` |
| 03 | Team & Access | `users`, `approvals`, `enterprise` |
| 04 | AI Agents & Employees | `ai`, `ai_providers`, `ai_ceo`, `workforce`, `agent_factory`, `missions`, `workflows`, `tools`, `a2a` |
| 05 | Spending & Budgets | `finance`, `usage` |
| 06 | Integrations | `integrations`, `api`, `webhooks`, `mcp` |
| 07 | Browser & Automation | `desktop`, `browser`, `terminal`, `openhands` |
| 08 | Security & Compliance | `host`, `governance`, `privacy`, `compliance`, `security` |
| 09 | Reports & Documents | *(no legacy category; new definitions later)* |
| 10 | Notifications | `communication`, `notifications` |
| 11 | Data, Storage & Backups | `data`, `files`, `records`, `recovery` |
| 12 | Infrastructure & Stack | `monitoring`, `features`, `diagnostics` |
| 13 | Billing & Plan | `billing` |
| 14 | Appearance & Accessibility | `appearance` |
| 15 | Audit & Activity | `audit` |
| 16 | Advanced & Danger Zone | `advanced`, `danger` |

Category IDs and setting keys are unchanged. Deep links that use the legacy
32-domain aliases keep working through `DOMAIN_ALIASES` and
`DOMAIN_CHILD_CATEGORIES`.

---

## 6. Safe secret migration

### 6.1 Classification

The dry-run reduces every `secret=True` value to one of:

- `configured`;
- `empty`;
- `placeholder`;
- `revoked_or_placeholder`;
- `too_short_for_real_credential`;
- `unreadable`.

No value, prefix, suffix, or length appears in the report. The only source of
truth for "is this configured" is the classification, not the presence of a
non-empty string.

### 6.2 Policy

- `configured` → encrypt with the master key and insert into `secrets` at the
  same scope, then blank the legacy column only after verification.
- `placeholder`, `revoked_or_placeholder`, `too_short_for_real_credential`,
  `empty` → mark unconfigured and require owner re-entry. Do not encrypt a
  placeholder, because that would create the illusion of a working credential.
- The legacy JSON mirror is a compatibility cache, not the source of truth. It
  must stop receiving secret values before production cutover.
- No secret is ever written to a report, log, audit row, or API response.

### 6.3 Key management

- Production requires `ZONATA_SETTINGS_MASTER_KEY` (32 bytes, hex or base64).
- Development may use a `0600` local key file; the service prints a warning.
- If neither exists, secret writes fail closed. Reads of already-encrypted
  secrets fail closed as well rather than returning ciphertext.
- A rotate-master-key command re-wraps data encryption keys without needing the
  old plaintext.

---

## 7. RBAC, approvals, and agent boundaries

### 7.1 RBAC

- Identity comes only from the verified Bearer token; `X-User-Role` is
  ignored and will be removed from the settings path.
- Reads require `settings.read` and company membership.
- Writes require the definition's `required_permission` and write access to the
  target scope.
- Locks require `settings.lock`.
- Secrets require `secrets.manage`.
- Audit reads require `audit.read` and are company-scoped.
- Danger actions require `danger.manage`, typed confirmation, and
  re-authentication.

### 7.2 Approvals

- `requires_approval` is enforced on the write path, not recorded as metadata.
- The approval row stores `actor_type` (`human`, `agent`, `system`).
- Agents may propose changes; they may never apply security, spend,
  permission, or lock changes.
- The AI CEO cannot approve its own proposal and cannot raise
  `ceo_spending_limit`, `ceo_autonomy_level`, or any of its own permissions.
- Two-person rules read `gov_two_person_rule` / `rbac_two_person_rule` once
  those keys become `live`.

### 7.3 Audit

- Every write and lock emits an append-only audit row with the hash chain.
- Old/new values are redacted for `sensitive` definitions.
- Company filter is always applied; a Company A user cannot read Company B's
  settings audit.
- Request ID, actor type, and IP are stored.

---

## 8. API v2 sketch (Phase 2, not implemented yet)

```
GET    /api/settings/v2/registry
GET    /api/settings/v2/effective?key=&scope=&scope_id=
POST   /api/settings/v2/values            # expected_version required
POST   /api/settings/v2/values/reset      # delete local override
POST   /api/settings/v2/lock              # settings.lock
GET    /api/settings/v2/secrets           # metadata only: last4, configured
POST   /api/settings/v2/secrets           # write-only
POST   /api/settings/v2/secrets/{id}/rotate
GET    /api/settings/v2/approvals
POST   /api/settings/v2/approvals/{id}/decide
GET    /api/settings/v2/audit?company_id=&key=&actor=&from=&to=
GET    /api/settings/v2/diff?scope_a=&scope_b=
```

Legacy `/api/settings*` remains as a compatibility wrapper behind
`ZONATA_SETTINGS_RESOLVER_V2` until parity. The wrapper delegates to the v2
resolver and never trusts spoofable headers.

---

## 9. UI component structure (Phase 3)

```
SettingsShell
├── CommandPalette (Cmd/Ctrl+K)
├── SectionSidebar (16 sections, search, counts)
├── ScopeSwitcher (Organization ▸ Company ▸ Department ▸ Agent ▸ User)
├── SectionView
│   ├── SectionHeader
│   ├── SettingGroup
│   │   └── SettingRow
│   │       ├── Label + description
│   │       ├── Control (switch/segmented/stepper/slider/picker/token)
│   │       ├── StatePill (Default / Inherited / Overridden / Locked)
│   │       ├── ProvenancePopover
│   │       ├── ResetToInherited
│   │       └── LockControl (permission-gated)
│   └── ComingSoonGroup (clearly labelled, no working control)
├── SaveBar (form sections) / UndoToast (instant toggles)
├── ImpactPreview (risky changes)
├── ApprovalInbox
└── AuditDrawer
```

Rules:

- A control is rendered only when `status === "live"`.
- `coming_soon` rows show a label and explanation, not a disabled fake switch.
- `hidden` rows are not rendered.
- `action` rows live in the Danger Zone with typed confirmation and
  re-authentication.
- Secret rows show `Configured` / `Not configured`, `last4`, `Rotate`, and
  `Revoke`; the value is reveal-once at write time only.
- The scope switcher sends a real scope and scope ID; it is not cosmetic.
- "Reset to inherited" deletes the override, then re-fetches the effective
  value.

---

## 10. Migration, rollback, and compatibility

### 10.1 Apply order

1. Create the new tables (`common/0003`, then dialect append-only file).
2. Keep `enterprise_settings` unchanged.
3. Dual-read: resolver reads `settings_values`, falls back to
   `enterprise_settings` only behind the feature flag.
4. Dry-run classification reviewed; configured secrets encrypted.
5. Dual-write with audit; verify legacy and v2 agree.
6. Cut reads over with `ZONATA_SETTINGS_RESOLVER_V2`.
7. Keep the legacy page at `/settings-legacy` until parity.
8. Only after verification, stop writing secrets to the JSON mirror and
   remove plaintext secret values from legacy storage.

### 10.2 Rollback

- Disable the feature flag; the legacy path still exists.
- Drop only the new tables if the migration must be fully reversed:
  `settings_values`, `settings_audit`, `secrets`, `settings_presets`,
  `roles`, `permissions`, `role_permissions`, `user_company_roles`,
  `settings_approvals`, `settings_environments`, `settings_revision`,
  `settings_schema_migrations`.
- The legacy `enterprise_settings` table and JSON mirror are not deleted by
  Phase 1 or Phase 2.
- A backup note is required before any production apply. Phase 1 makes no
  production database change.

### 10.3 Compatibility rules

- 202 setting keys and 45 category IDs remain stable.
- Existing env vars remain fallbacks; the UI will show them as read-only
  platform defaults.
- Existing `/api/settings*` endpoints remain until the v2 wrapper passes
  parity tests.
- Existing tests that encode `X-User-Role` or fake drift will be updated only
  when the hardened contract lands, not by weakening the new tests.

---

## 11. Test plan

### Phase 1 (implemented)

- Registry counts, uniqueness, category/section mapping.
- `live` implies `enforced_by`; `ENFORCED_BY` and live keys agree.
- Actions have action IDs and are not treated as values.
- Permissions and scopes are valid.
- Secret defaults are masked; sensitive text is redacted but not vaulted.
- Declarative validation for numbers, selects, toggles, and text.
- SQL splitter handles SQLite trigger bodies, PostgreSQL dollar quotes,
  strings, and comments.
- Schema creation is idempotent, verifies every required table, rejects
  checksum drift, and enforces append-only audit.
- Dry-run is read-only, never contains a secret value, classifies secrets,
  reports conflicts, and treats actions separately.
- Importing `core.settings` does not import the legacy settings service.

### Phase 2 (required before UI)

- Resolver precedence for all six scopes and broadest-lock rule.
- Lock/unlock permission and audit.
- RBAC: non-owner denial, company membership, secret permission.
- Secret redaction in search, category detail, audit, logs, errors.
- Append-only audit and hash-chain continuity.
- Approval and AI-CEO self-limit tests.
- Optimistic concurrency and atomic bulk writes.
- Migration up/down on SQLite; PostgreSQL apply in staging.

### Phase 3+ (required before release)

- UI state tests: Default/Inherited/Overridden/Locked, reset to inherited.
- E2E: scope switch, override, lock, bulk apply, secret rotate, approvals.
- Accessibility: keyboard, labels, contrast, 360 px layout.
- Performance: resolver cache hit rate, settings page load.
- Security review of every new endpoint.

---

## 12. Dry-run result against the tracked database

The report was generated read-only against `storage/roboassistant.db`:

- 204 stored rows across 3 tenants (`tnt_primary`, `tnt_primary_ceo`,
  `tnt_test_settings`).
- Stored scope labels: `Company` 121, `Host` 70, `User` 13.
- 2 danger-zone action rows, separated from configuration.
- 4 secret rows, all classified as placeholder or revoked; none are proposed
  for encryption. They must be re-entered by the owner.
- 0 Organization-default candidates, because no key has an identical value
  across every registered company in a tenant. Organization defaults will be
  seeded from the registry instead.
- The legacy JSON mirror has 46 registry keys plus 13 category/domain aliases;
  it is not the source of truth.
- The database contains test tenants and test companies. The report labels
  this explicitly; it does not treat test data as production configuration.

No secret values appear in the JSON or Markdown report. The tool opens the
database in SQLite read-only mode and has no `--apply` path.

---

## 13. Known limitations of Phase 1

- PostgreSQL migrations are written and reviewed but not executed here: this
  environment has no PostgreSQL server. They must be applied in staging.
- The resolver, RBAC, secrets vault, audit writer, approvals, and API v2 are
  designed but not implemented. The legacy runtime still uses
  `get_effective_setting()` and still trusts `X-User-Role`.
- The 177 `coming_soon` definitions remain stored in the legacy table. They
  are not visible as working controls in the new UI, but they are still
  readable through the legacy API until Phase 2 wraps it.
- The tracked database contains test tenants. It is evidence for the dry-run,
  not a production snapshot.
- The JSON mirror still contains a placeholder secret value in this snapshot.
  Phase 1 does not rewrite it; Phase 2 stops writing secrets there and the
  owner must re-enter the credential.

---

## 14. Checkpoint 2 approval requested

Approve the following before Phase 2 starts:

1. The schema in §4, including the append-only audit, encrypted secrets table,
   approval table, and revision counter.
2. The registry fields and strict `live` policy in §2.
3. The six-scope resolver and broadest-lock-first algorithm in §3.
4. The permission model and the rule that `X-User-Role` is never trusted.
5. The secret policy in §6: placeholders are unconfigured; configured values
   move to the vault; the JSON mirror stops receiving secrets.
6. The migration order and rollback in §10.
7. The rule that only `live` definitions get working controls; everything else
   is `coming_soon` or hidden.
8. Building sections 1–6 first, then 7–16.

After approval, Phase 2 starts with the resolver, RBAC, secrets vault, audit
chain, approvals, and `/api/settings/v2/*`, then stops for a backend
verification checkpoint before the UI shell.
