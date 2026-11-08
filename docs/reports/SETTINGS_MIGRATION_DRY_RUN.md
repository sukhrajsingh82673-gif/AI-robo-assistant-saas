# Settings Migration Dry-Run Report

Generated: `2026-11-07T11:26:30Z`

> **Read-only.** This report was produced without writing to the database, the JSON mirror, or any settings table. Secret values are never printed; they are reduced to a classification.

## 1. Registry readiness

| Status | Count |
|---|---:|
| `live` | 19 |
| `coming_soon` | 177 |
| `hidden` | 4 |
| `action` | 2 |
| **total** | **202** |
| categories | 45 |
| sections | 16 |

## 2. Stored data

- Source database: `storage/roboassistant.db`
- Legacy table present: `True`
- Rows: **204**
- Tenants: **3**
- Registered companies: `tnt_primary`=5, `tnt_test_settings`=0, `tnt_primary_ceo`=1

| Tenant | Companies |
|---|---|
| `tnt_primary` | `comp_alpha`, `comp_beta`, `comp_primary`, `comp_secondary` |
| `tnt_primary_ceo` | `comp_primary_ceo` |
| `tnt_test_settings` | `comp_alpha`, `comp_beta` |

| Stored scope label | Rows |
|---|---:|
| `Company` | 121 |
| `Host` | 70 |
| `User` | 13 |

## 3. Proposed scope handling

| Action | Rows / keys |
|---|---:|
| Keep at Company scope | 198 |
| Move configured secret to vault | 0 |
| Seed Organization default | 0 |
| Danger-zone action rows | 2 |
| Unknown registry keys | 0 |

Host-labelled rows are kept at Company scope. An Organization default is seeded only when every company in the tenant stores the same value. No locks are created.

### Organization default candidates

_None. Organization defaults will be seeded from the registry instead._

## 4. Secret review

No secret value, prefix, suffix, or length is included below.

| Key | Tenant | Company | Classification | Proposed action |
|---|---|---|---|---|
| `ai_gemini_api_token` | `tnt_primary` | `comp_primary` | `placeholder` | `mark_unconfigured` |
| `api_developer_key_vault` | `tnt_primary` | `comp_primary` | `revoked_or_placeholder` | `mark_unconfigured` |
| `integ_webhook_signature_secret` | `tnt_primary` | `comp_primary` | `placeholder` | `mark_unconfigured` |
| `mcp_auth_token` | `tnt_primary` | `comp_primary` | `placeholder` | `mark_unconfigured` |

## 5. Conflicts and review items

| Kind | Key / scope | Tenant | Action |
|---|---|---|---|
| `secret_not_configured` | `ai_gemini_api_token` | `tnt_primary` | require re-entry; do not migrate the value |
| `secret_not_configured` | `api_developer_key_vault` | `tnt_primary` | require re-entry; do not migrate the value |
| `secret_not_configured` | `integ_webhook_signature_secret` | `tnt_primary` | require re-entry; do not migrate the value |
| `secret_not_configured` | `mcp_auth_token` | `tnt_primary` | require re-entry; do not migrate the value |

## 6. Legacy JSON mirror

- Present: `True`
- Registry setting keys: **46**
- Non-setting keys (category/domain aliases): 13
- Keys only in DB (149): `a2a_cross_company_allowed`, `a2a_inter_agent_auth`, `a2a_message_encryption_cipher`, `a2a_peer_discovery_mode`, `a2a_rate_limit_per_min`, `acc_density`, `acc_email`, `acc_keyboard_shortcuts_enabled`, `acc_secondary_timezones`, `acc_session_timeout_min`, `acc_timezone`, `acc_two_factor_method`, `adv_debug_logging`, `adv_isolate_quarantine_mode`, `adv_kernel_cache_ttl_sec`, `adv_verbose_kernel_traces`, `af_mandatory_simulation`, `ai_circuit_breaker_retries`, `ai_fallback_provider`, `ai_master_enablement` …
  The JSON mirror is a legacy compatibility cache; it is not the source of truth.

## 7. Warnings

- More than one tenant is present. Organisation-default seeding is evaluated per tenant.
- No key has an identical value across every company, so no Organization default will be seeded automatically.

## 8. Next gate

Phase 1 ends here. No migration has been applied. Phase 2 (resolver, RBAC, secrets vault, audit chain, approvals, API v2) requires checkpoint 2 approval.
