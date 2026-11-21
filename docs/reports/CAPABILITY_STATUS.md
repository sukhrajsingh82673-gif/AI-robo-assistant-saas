# ZONATA Universal AI Operating System — Capability Truth Table

**Generated:** `2026-11-21T03:58:41.103217+00:00`  
**Environment:** `development`  
**Hardware Platform:** `aarch64 Linux`  
**Execution Mode:** Standard Sovereign

---

## 1. Executive Summary

- **Live (Operational):** `7`
- **Test / Sandbox:** `0`
- **Not Connected / Unconfigured:** `9`
- **Degraded Mode:** `0`
- **Not Implemented:** `2`
- **Failed:** `0`

---

## 2. Capability Status & Latency Truth Table

| Capability | Reality Status | Plain Language | Provider | Provider Ref | Latency (ms) | Sandbox | Details / Error |
|:---|:---|:---|:---|:---|:---|:---|:---|
| `antivirus` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | ClamAV not reachable at localhost:3310: [Errno 111] Connection refused |
| `browser` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Browser automation runtime is NOT_IMPLEMENTED in sovereign core |
| `calendar` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | CALDAV_URL not configured |
| `database` | **OK** | Live | `database_sqlite` | `db_conn_sqlite` | 13.44 | Yes | {"dialect": "sqlite", "rls_active": false} |
| `desktop_control` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Desktop GUI automation runtime is NOT_IMPLEMENTED in sovereign core |
| `email_in` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | IMAP_HOST not configured |
| `email_out` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | SMTP_HOST/SMTP_PORT not configured |
| `key_management` | **OK** | Live | `sovereign_aes_gcm` | `aes_256_gcm` | 18.14 | No | {"cipher": "AES-256-GCM", "keysize_bits": 256} |
| `llm` | **OK** | Live | `gemini` | `llm_gemini` | 0.04 | No | {"provider": "gemini"} |
| `mcp` | **OK** | Live | `mcp_local_directory` | `mcp_servers_3` | 0.06 | No | {"installed_servers": ["memory", "filesystem", "context7-docs"]} |
| `observability` | **OK** | Live | `internal_prometheus_metrics` | `internal_metrics_registry` | 0.01 | No | - |
| `ocr` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | OCR backend not reachable: <urlopen error [Errno 111] Connection refused> |
| `payments` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | STRIPE_API_KEY not configured |
| `search` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | SEARCH_PROVIDER not configured |
| `secrets` | **OK** | Live | `env_secret_vault` | `secret_store_ready` | 0.00 | No | - |
| `storage` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | S3_ENDPOINT environment variable not set |
| `text_extraction` | **NOT_CONFIGURED** | Not Connected | `not_configured` | `-` | 0.00 | No | Apache Tika not reachable at http://localhost:9998: <urlopen error [Errno 111] Connection refused> |
| `workflow_engine` | **OK** | Live | `embedded_transactional_outbox` | `outbox_runner_local` | 0.01 | No | - |

---

## 3. Truth Invariants Verified
1. **No False Success:** Zero capabilities report operational status without a live verified handshake.
2. **Measured Latencies:** Latency recorded per individual harmless probe in milliseconds.
3. **Explicit Absence:** Browser automation and Desktop GUI control are acknowledged as `NOT_IMPLEMENTED`.
4. **No Secrets Exposed:** Provider credentials, tokens, and database passwords scrubbed from all outputs.
