# Hardening Report — Real LLM, Tenant Isolation, and Zero Mock Data

**Branch:** `hardening/real-llm-tenant-isolation` (from `main` at `517a24c`)
**Date:** 2026-10-30
**Scope:** `/root/roboassistant` — ZONATA / RoboAssistant SaaS platform

---

## 1. Objective

Make the platform genuinely production-ready on a **free** technology stack:

1. Every feature must work for real, or fail honestly with an explicit code/reason.
2. No mock, simulated, or invented data anywhere in product paths.
3. A free, owner-configurable language model, embedded by default (no API key required).
4. Strict per-tenant isolation for every runtime, dataset, and evidence ledger.

---

## 2. Language Model — Free by Default, Owner-Configurable

New module: `core/llm_runtime.py` (single gateway used by every AI feature).

| Provider key | What it uses | Cost | Key required |
|---|---|---|---|
| `embedded_free` (**default**) | Local Ollama at `127.0.0.1:11434`, else keyless Pollinations (`https://text.pollinations.ai/openai`, `openai-fast`) | Free | No |
| `ollama` | Any local Ollama model (`ZONATA_EMBEDDED_MODEL`, default `qwen2.5:1.5b`) | Free | No |
| `gemini_free` | Google AI Studio free tier | Free tier | Yes |
| `groq_free` | Groq free tier | Free tier | Yes |
| `openrouter_free` | OpenRouter `:free` models | Free tier | Yes |
| `openai_compatible` | Any OpenAI-compatible endpoint (vLLM, LM Studio, llama.cpp, gateway) | Depends | Optional |
| `deterministic` | No model at all — explicit refusal | Free | No |

Behaviour:

* 900 s response cache, 31 s free-tier cooldown, health cache, JSON extraction.
* When **no** provider is reachable the gateway returns `degraded=True` with
  `error="ALL_PROVIDERS_UNAVAILABLE"`. It never invents prose.
* Owner overrides are stored in Enterprise Settings and applied live
  (`GET /api/llm/status`, `GET /api/llm/providers`, `POST /api/llm/test`,
  `POST /api/settings`).
* `scripts/install_embedded_llm.sh` installs Ollama + a small model, and
  `--check` verifies it. With it installed, the default path is fully local and
  zero-egress.

**Missions no longer fabricate deliverables.** `BackgroundMissionDispatcher`
plans through the LLM; if the plan is degraded or the deliverable is empty the
mission becomes `BLOCKED` (`MODEL_UNAVAILABLE` / `DELIVERABLE_FAILED`) — a
terminal state — with no evidence id, no file, and no notification claiming
success.

---

## 3. Per-Tenant Isolation

`core/tenancy.py` introduces a per-tenant runtime registry. All import-time
tenant-scoped singletons in `api_server.py` were removed and replaced with
tenant-scoped helpers: `_cw`, `_ledger_for`, `_temporal`, `_a2a`, `_mcp`,
`_openhands`, `_browser`, `_nango`, `_heartbeat`, `_delegation`.

* Company resolution now always trusts the validated token. `X-Company-ID` /
  body `company_id` are honoured only when the company is proven to belong to
  the authenticated tenant; otherwise the request fails closed to the token's
  own company.
* Node registration forces the authenticated tenant (`TENANT_SCOPE_MISMATCH`).
* Evidence ledgers are per-tenant (`tenant_ledger_path`), with a defensive
  filter that never returns another tenant's records from a legacy ledger.
* `GET /api/coworker/missions` and mission detail are tenant-scoped; a foreign
  mission id returns `404`.

---

## 4. Mock / Simulated Data Removed

| Area | Before | After |
|---|---|---|
| Mission deliverables | Fabricated report written and marked `COMPLETED` | `BLOCKED` + `MODEL_UNAVAILABLE`; no file, no evidence |
| Billing adapters | Fake success responses | Real HTTP only with credentials; `NOT_CONFIGURED` otherwise, fails closed |
| Connectors | Fixture numbers, `(Mock/Simulated)` names | Empty payloads, `NOT_CONFIGURED`/`BLOCKED`, `is_mock=False` |
| A2A | Simulated replies | Real HTTP+JSON `message/send`; `REMOTE_AGENT_UNREACHABLE` on failure (injection only under `ZONATA_TEST_MODE=1`) |
| A2A health | Hardcoded `ONLINE` | Real TCP probe (`ONLINE`/`OFFLINE`/`UNVERIFIED`, `404 AGENT_NOT_FOUND`) |
| Plugins test-connection | Fabricated 38 ms / 99.2 % handshake | Real TCP probe; `sync_connection` → `NOT_IMPLEMENTED`, 0 records |
| Desktop robot | Synthetic telemetry | `DISPLAY_NOT_AVAILABLE`, `WINDOW_MANAGER_NOT_AVAILABLE`, `INPUT_CHANNEL_NOT_AVAILABLE` |
| Browser robot | `SIMULATED` navigation, fixture page items, fake viewport hash | Real HTTP GET (`LIVE_HTTP`/`REAL_HTTP_GET`, real status code); extraction/form/viewport return `NOT_EXECUTED` codes |
| Browser-use runtime | Fabricated PNG "screenshot" | Real capture only (scrot/import/gnome-screenshot/grim); otherwise `screenshot_status=NOT_CAPTURED`, `screenshot_id=null` |
| Tool fabric | Invented `/usr/bin/<tool>` path | `NOT_AVAILABLE` when the binary is missing |
| Control kernel | Fabricated remote ACK | `NOT_CONNECTED` |
| Tool discovery | Fabricated wrapper source | Real `importlib.util.find_spec` dependency check; `BLOCKED_EXTERNAL_DEPENDENCY`; capabilities `PARTIALLY_QUALIFIED` |
| Terminal tool admission | Synthetic hash, invented manifest path | SHA-256 of the real installed artifact; missing artifact blocks admission |
| Chaos injector | `recovered: True` | `recovered: None` + note that recovery is measured elsewhere |
| Health/readiness | Hardcoded commit/branch/`CONNECTED` | `_git_metadata()` + `_database_status()` (live) |
| Temporal clusters | Invented versions | Embedded vs configured external, no invented values |
| Company resolution | Auto-created fake companies | `409 NO_COMPANY` |
| Heartbeat / webhooks verify | Placeholder identity, implicit secret | `MISSING_AGENT_IDENTITY`, `MISSING_SECRET` |
| CEO mission bridge | Invented node names, `cost = estimate × 0.85`, "success" summary, `ev_merkle_` token | Real registered nodes only, `cost=0.0` + "not metered" warning, plan-record wording, real sealed `EV-…` evidence id |
| Web UI | Fabricated fleet node, fake bootstrap token, fake voice transcript | Real nodes (with empty state), placeholder `<YOUR_FLEET_TOKEN>`, explicit "speech recognition unavailable" notice |
| Reference workloads | Unlabelled synthetic financial figures | `data_provenance: REFERENCE_SCENARIO_FIXTURE`, `is_reference_data: true`; Workload E now uses the real `python3` binary and measures real host latency |

Workload E (`workloads/universal_computer.py`) previously required the missing
`sqlite3` CLI; it now provisions the genuinely installed `python3` and records
measured command latency instead of invented node telemetry.

---

## 5. Reliability and Schema Fixes Found During Verification

* Added `coworker_background_missions` to the canonical schema so global search
  works on any fresh database (previously only created lazily by the dispatcher).
* `MultimodalCapabilityRegistry.list_capabilities()` re-seeds when the active
  database has no rows yet (fresh boot / test isolation).
* `EmployeeHealthManager` verifies its table lazily, so a database switch cannot
  leave it writing to a closed schema.
* `business_causality` and `browser_use_execution_runtime` upsert tenant/company
  scope rows before inserting FK-linked records.
* `Employees`, `Temporal`, `A2A`, `MCP`, `OpenHands`, `Browser`, `Nango`,
  `Heartbeat`, `Delegation`, `Multimodal` runtimes are now per-tenant.
* Test isolation: `tests/conftest.py` now creates **one** isolated database per
  process and shares it through `tests/schema_bootstrap.py`, eliminating a
  double-database bug that made module-level singletons write to
  `storage/roboassistant.db` while tests ran against a temp database.
* Baseline `tnt_primary` / `comp_primary` rows are seeded for isolated runs so
  FK-constrained inserts work from an empty database.

---

## 6. Test Results

Full suite executed file-by-file (memory-safe), branch
`hardening/real-llm-tenant-isolation`:

* **102 test files, 1399 tests passed, 0 failed**
* `tests/test_settings_enterprise_qualification.py` (22 tests) verified in four
  gate chunks (8 + 6 + 8) — all passed. Running that single file in one process
  exceeds the sandbox's ~3.5 GB RAM (swap thrash), which is an environment
  limit, not a product failure.
* **Total: 1421 passing tests.**
* 13 skipped, all infrastructure-gated: `test_docker_staging_qualification.py`
  (8, no Docker daemon) and `test_postgresql_wal_pitr_drill.py` (5, no Postgres
  server). `test_postgresql_*` live suites skip when `DATABASE_URL` is absent.

Notable suites: `test_saas_platform_integration` (38), `test_coworker_production_qualification` (22),
`test_a2a_interoperability` (54), `test_mcp_interoperability` (36), `test_hal_multimodal` (50),
`test_temporal_durable_execution` (20), `test_ai_ceo_live_integration_qualification` (15),
`test_universal_terminal_master_qualification` (18), `test_phase_12_commercial_billing` (25),
`test_durable_workflow` (55), `test_adversarial_security_and_chaos` (11),
`test_direct_object_access_and_tenant_security` (14).

Tests that encoded fixture behaviour were rewritten to assert honest behaviour
(for example `BLOCKED`/`NOT_INSTALLED` outcomes instead of `SUCCESS`, and real
sealed evidence ids instead of `ev_merkle_` tokens). Mission tests use an
in-process deterministic LLM double (`patch("core.llm_runtime.LLMRuntime.chat", …)`),
so they exercise the real pipeline without network access.

---

## 7. Live End-to-End Verification (fresh database, real HTTP)

Two tenants (`tnt_alpha`/`comp_alpha`, `tnt_beta`/`comp_beta`), server on
`127.0.0.1:8099`, `APP_ENV=development`, fresh SQLite database:

```
healthz                      HEALTHY / database CONNECTED / real commit+branch
readyz                       200 HEALTHY
openapi                      200 — 83 paths
llm_status                   200 — configured_provider=embedded_free, model=openai-fast,
                             available=[embedded_free, deterministic]
llm_test                     200 — degraded, provider=deterministic,
                             error=ALL_PROVIDERS_UNAVAILABLE (honest, no key, no local model)
ceo_chat                     200 — degraded=true (no model reachable)
mission_alpha                200 — RUNNING → step
mission_alpha_final          BLOCKED — "no language model provider is available", evidence_id=null
mission_isolation            alpha sees 1 mission, beta sees 0
cross_tenant_mission_detail  404 — "Mission 'msn_…' not found"
evidence_alpha / evidence_beta  200, unbroken_integrity=true, 0 records each
cross_tenant_kpis            200 — requested comp_alpha with beta token → served comp_beta (fail-closed)
LIVE_VERIFICATION_OK
```

The absent model is reported truthfully rather than papered over; with
`scripts/install_embedded_llm.sh` run once, the same calls return real model
output because Ollama becomes reachable.

---

## 8. Known Environment Limitations

* **No Ollama / no local model in this sandbox.** The embedded path therefore
  falls back to keyless Pollinations, which is rate-limited to roughly one
  request per 30 s per IP; under test load it legitimately reports
  `ALL_PROVIDERS_UNAVAILABLE`.
* **Not installed here:** `pypdf`, `PyPDF2`, `pdfplumber`, `duckdb`, `cv2`,
  `pyaudio`, `edge_tts`. Tool admission correctly blocks them rather than
  pretending to install or execute.
* **No Docker / Postgres server**, so container and live-Postgres suites skip.
* **Sandbox memory ~3.5 GB** — long single-process test runs must be chunked.
* `.env.local` currently holds live Neon credentials in plaintext and is not
  git-tracked. Treat them as exposed and rotate them before any shared use.

---

## 9. How to Use the Free Model

```bash
# one-time, fully local, no API key, no data egress
./scripts/install_embedded_llm.sh

# verify
./scripts/install_embedded_llm.sh --check
```

Then in **Settings → AI Models & Providers** choose:

* `Embedded Free (zero-config)` — local Ollama first, keyless fallback second.
* `Local Self-Hosted (Ollama / vLLM)` — your own endpoint and model name.
* `Gemini Free` / `Groq Free` / `OpenRouter Free` — paste a free-tier key.
* `Deterministic (no model)` — explicitly refuse generation.

---

## 10. Commit Contents

* New: `core/llm_runtime.py`, `core/tenancy.py`, `core/ceo_chat.py`,
  `core/openapi_spec.py`, `scripts/install_embedded_llm.sh`,
  `tests/schema_bootstrap.py`.
* Hardened: `api_server.py` and 20+ `core/*` runtimes/services listed above.
* Tests: 20 suites rewritten for honest expectations, plus isolation fixes.
* UI: honest fleet/settings/tools/plugins/overview surfaces, no fabricated
  telemetry or fake speech transcripts.
* Reference workloads: provenance-labelled; Workload E measures real host data.
