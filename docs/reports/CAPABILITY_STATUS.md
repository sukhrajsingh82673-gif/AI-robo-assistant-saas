# ZONATA Universal AI Operating System — Capability Truth Table

**Generated:** `2026-11-21T07:44:05.386866+00:00`  
**Environment:** `development`  
**Hardware Platform:** `aarch64 Linux`  
**Execution Mode:** Standard Sovereign

---

## 1. Executive Summary

- **Live (Operational):** `6`
- **Test / Sandbox:** `0`
- **Not Connected / Unconfigured:** `10`
- **Degraded Mode:** `0`
- **Not Implemented:** `2`
- **Failed:** `0`

---

## 2. Capability Status & Latency Truth Table

| Capability | Reality Status | Plain Language | Provider | Provider Ref | Latency (ms) | Sandbox | Details / Error |
|:---|:---|:---|:---|:---|:---|:---|:---|
| `antivirus` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | CLAMAV_HOST / CLAMAV_PORT not configured |
| `browser` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Browser automation runtime is NOT_IMPLEMENTED in sovereign core |
| `calendar` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | CALDAV_URL not configured |
| `database` | **OK** | Live | `database_sqlite` | `db_conn_sqlite` | 119.52 | Yes | {"dialect": "sqlite", "rls_active": false} |
| `desktop_control` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Desktop GUI automation runtime is NOT_IMPLEMENTED in sovereign core |
| `email_in` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | IMAP_HOST not configured |
| `email_out` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | SMTP_HOST / SMTP_PORT not configured |
| `key_management` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | KMS master key not configured (set KMS_MASTER_KEY or SECRET_VAULT_KEY) |
| `llm` | **OK** | Live | `gemini` | `llm_gemini_models_200` | 393.79 | No | {"provider": "gemini", "verified": true} |
| `mcp` | **OK** | Live | `zonata_mcp_registry` | `mcp_db_servers_198` | 6.87 | No | {"registered_servers": 198} |
| `observability` | **OK** | Live | `internal_prometheus_metrics` | `metrics_exposition_3882b` | 11.44 | No | {"exposition": "prometheus", "otel_endpoint_configured": false, "otel_verified": false} |
| `ocr` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | TIKA_ENDPOINT not configured in environment |
| `payments` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | STRIPE_API_KEY not configured |
| `search` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | SEARCH_ENDPOINT not configured; a provider name alone is not a live check |
| `secrets` | **OK** | Live | `mediated_secret_store` | `sec_1973198609fe` | 7.37 | No | {"backend": "in_memory_mediated"} |
| `storage` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | S3_ENDPOINT not configured in environment |
| `text_extraction` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | TIKA_ENDPOINT not configured in environment |
| `workflow_engine` | **OK** | Live | `embedded_transactional_outbox` | `outbox_events_0` | 78.32 | No | {"outbox_table": "af_outbox", "event_count": 0} |

---

## 3. Truth Invariants Verified
1. **No False Success:** Zero capabilities report operational status without a live verified handshake.
2. **Measured Latencies:** Latency recorded per individual harmless probe in milliseconds.
3. **Explicit Absence:** Browser automation and Desktop GUI control are acknowledged as `NOT_IMPLEMENTED`.
4. **No Secrets Exposed:** Provider credentials, tokens, and database passwords scrubbed from all outputs.
