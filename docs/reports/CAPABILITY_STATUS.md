# ZONATA Universal AI Operating System — Capability Truth Table

**Generated:** `2026-11-24T05:20:54.630028+00:00`  
**Environment:** `development`  
**Hardware Platform:** `aarch64 Linux`  
**Execution Mode:** Sandbox / Test

---

## 1. Executive Summary

- **Live (Operational):** `5`
- **Test / Sandbox:** `11`
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
| `calendar` | **SANDBOX** | Test Only | `caldav_sandbox` | `sandbox_calendar_1795497654` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `database` | **OK** | Live | `database_sqlite` | `db_conn_sqlite` | 14.46 | Yes | {"dialect": "sqlite", "rls_active": false} |
| `desktop_control` | **NOT_IMPLEMENTED** | Not Implemented | `none` | `-` | 0.00 | No | Desktop GUI automation runtime is NOT_IMPLEMENTED in sovereign core |
| `email_in` | **SANDBOX** | Test Only | `imap_sandbox` | `sandbox_email_in_1795497654` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `email_out` | **SANDBOX** | Test Only | `sandbox_smtp` | `sandbox_smtp_sink` | 0.10 | Yes | {"sandbox": true} |
| `key_management` | **OK** | Live | `sovereign_aes_gcm_kms` | `kms_kdf_sha256_356cb12c3a42df39` | 0.06 | No | {"cipher": "AES-256-GCM", "envelope_kms": true} |
| `llm` | **SANDBOX** | Test Only | `sandbox_llm_gateway` | `sandbox_tiers_active` | 0.07 | Yes | {"tiers": ["PLANNER", "WORKER", "FAST", "VISION", "EMBEDDING"], "primary_provider": "anthropic", "primary_model": "claude-3-7-sonnet", "sandbox": true} |
| `mcp` | **SANDBOX** | Test Only | `mcp_sandbox` | `sandbox_mcp_1795497654` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `observability` | **OK** | Live | `internal_prometheus_metrics` | `metrics_exposition_3881b` | 12.98 | No | {"exposition": "prometheus", "otel_endpoint_configured": false, "otel_verified": false} |
| `ocr` | **SANDBOX** | Test Only | `sandbox_ocr` | `sandbox_ocr_v1` | 0.10 | Yes | {"sandbox": true} |
| `payments` | **SANDBOX** | Test Only | `stripe_sandbox` | `sandbox_payments_1795497654` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `search` | **SANDBOX** | Test Only | `search_sandbox` | `sandbox_search_1795497654` | 0.50 | Yes | {"sandbox": true, "note": "Simulation mode"} |
| `secrets` | **OK** | Live | `sandbox_openbao` | `secrets://probe_46bc17b6b22ced34` | 6.87 | Yes | {"backend": "sandbox_openbao", "cycle": "write_read_rotate_revoke_verified"} |
| `storage` | **SANDBOX** | Test Only | `sandbox_storage` | `sandbox_store_0` | 0.10 | Yes | {"items_count": 0} |
| `text_extraction` | **SANDBOX** | Test Only | `sandbox_tika` | `sandbox_tika_v2.9.2` | 0.10 | Yes | {"sandbox": true} |
| `workflow_engine` | **OK** | Live | `embedded_transactional_outbox` | `outbox_events_0` | 59.23 | Yes | {"outbox_table": "af_outbox", "event_count": 0} |

---

## 3. Truth Invariants Verified
1. **No False Success:** Zero capabilities report operational status without a live verified handshake.
2. **Measured Latencies:** Latency recorded per individual harmless probe in milliseconds.
3. **Explicit Absence:** Browser automation and Desktop GUI control are acknowledged as `NOT_IMPLEMENTED`.
4. **No Secrets Exposed:** Provider credentials, tokens, and database passwords scrubbed from all outputs.
