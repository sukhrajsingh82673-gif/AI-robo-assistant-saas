# ZONATA Universal AI Operating System — Capability Truth Table

**Generated:** `2026-11-21T16:34:58.414320+00:00`  
**Environment:** `development`  
**Hardware Platform:** `aarch64 Linux`  
**Execution Mode:** Sandbox / Test

---

## 1. Executive Summary

- **Live (Operational):** `7`
- **Test / Sandbox:** `9`
- **Not Connected / Unconfigured:** `0`
- **Degraded Mode:** `0`
- **Not Implemented:** `2`
- **Failed:** `0`

---

## 2. Capability Status & Latency Truth Table

| Capability | Reality Status | Plain Language | Provider | Provider Ref | Latency (ms) | Sandbox | Details / Error |
|:---|:---|:---|:---|:---|:---|:---|:---|
| `antivirus` | **SANDBOX** | Test Only | `sandbox_antivirus` | `sandbox_clamav_v1.4` | 0.10 | Yes | {"sandbox": true, "verdict": "CLEAN"} |
| `browser` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Browser automation runtime is NOT_IMPLEMENTED in sovereign core |
| `calendar` | **SANDBOX** | Test Only | `caldav_sandbox` | `sandbox_calendar_1795278897` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `database` | **OK** | Live | `database_sqlite` | `db_conn_sqlite` | 13.43 | Yes | {"dialect": "sqlite", "rls_active": false} |
| `desktop_control` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Desktop GUI automation runtime is NOT_IMPLEMENTED in sovereign core |
| `email_in` | **SANDBOX** | Test Only | `imap_sandbox` | `sandbox_email_in_1795278897` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `email_out` | **SANDBOX** | Test Only | `sandbox_smtp` | `sandbox_smtp_sink` | 0.10 | Yes | {"sandbox": true} |
| `key_management` | **OK** | Live | `sovereign_aes_gcm_kms` | `kms_kdf_sha256_356cb12c3a42df39` | 0.04 | No | {"cipher": "AES-256-GCM", "envelope_kms": true} |
| `llm` | **OK** | Live | `gemini` | `llm_gemini_models_200` | 910.48 | No | {"provider": "gemini", "verified": true} |
| `mcp` | **OK** | Live | `zonata_mcp_registry` | `mcp_db_servers_198` | 14.74 | No | {"registered_servers": 198} |
| `observability` | **OK** | Live | `internal_prometheus_metrics` | `metrics_exposition_3882b` | 19.42 | No | {"exposition": "prometheus", "otel_endpoint_configured": false, "otel_verified": false} |
| `ocr` | **SANDBOX** | Test Only | `sandbox_ocr` | `sandbox_ocr_v1` | 0.10 | Yes | {"sandbox": true} |
| `payments` | **SANDBOX** | Test Only | `stripe_sandbox` | `sandbox_payments_1795278898` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `search` | **SANDBOX** | Test Only | `search_sandbox` | `sandbox_search_1795278897` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `secrets` | **OK** | Live | `mediated_secret_store` | `sec_9f871af95914` | 5.43 | No | {"backend": "in_memory_mediated"} |
| `storage` | **SANDBOX** | Test Only | `sandbox_storage` | `sandbox_store_0` | 0.10 | Yes | {"items_count": 0} |
| `text_extraction` | **SANDBOX** | Test Only | `sandbox_tika` | `sandbox_tika_v2.9.2` | 0.10 | Yes | {"sandbox": true} |
| `workflow_engine` | **OK** | Live | `embedded_transactional_outbox` | `outbox_events_0` | 122.80 | Yes | {"outbox_table": "af_outbox", "event_count": 0} |

---

## 3. Truth Invariants Verified
1. **No False Success:** Zero capabilities report operational status without a live verified handshake.
2. **Measured Latencies:** Latency recorded per individual harmless probe in milliseconds.
3. **Explicit Absence:** Browser automation and Desktop GUI control are acknowledged as `NOT_IMPLEMENTED`.
4. **No Secrets Exposed:** Provider credentials, tokens, and database passwords scrubbed from all outputs.
