# Coworker 2.0 — Spec vs Implementation Gap Report

Spec source: *URA / ZONATA Autonomous Coworker 2.0 — CEO-Directed Autonomous
Execution, Desktop Intelligence, Tool Discovery, and Cybersecurity Operations*
(16 sections, held at `/tmp/opencode/spec.txt`, extracted from the Antigravity
conversation of 2026-11-04).

Reviewed: 2026-11-06
Scope: §1–§16 of the spec against the code currently on `main`.
Status vocabulary: **Verified** · **Implemented-unverified** · **Partial** ·
**Blocked** · **Not implemented** · **Failed**

A status is only **Verified** when a reproducible command or retained artefact
backs it. "Tests pass" alone is not treated as proof of real-world execution.

---

## Summary table

| § | Area | Status | One-line reason |
|---|---|---|---|
| 1 | Primary objective (CEO-directed autonomous execution) | Partial | Pipeline exists end-to-end; full unattended autonomy not exercised |
| 2 | Authority and command structure | Verified | Policy, approval, kill-switch and tenant gates enforced and tested |
| 3 | Five-level decision engine | Partial | L1/L2/L4/L5 real; L3 discovery has no live web/GitHub research |
| 4 | Advanced desktop computer-use | Partial | 14 primitives dispatch real X11 input; perception is seeded, no OCR/AT-SPI |
| 5 | OpenDots integration | Not implemented | No verifiable OpenDots artefact; shim now labelled honestly |
| 6 | Specialised agent factory | Verified | Ephemeral subworkers inherit scope, parallel execution, tests pass |
| 7 | Storage and resource management | Partial | Workspace tracking, cleanup manifests, protected paths real; no download/install manifests or ownership records |
| 8 | Autonomous cybersecurity defence | Partial | Real AST/secret/entropy scans; no exploit testing or automated response |
| 9 | CEO task queue and idle management | Verified | 12 states enforced; idle now runs the real defence patrol (throttled) |
| 10 | CEO reporting and evidence | Verified | All required report fields present; Merkle ledger sealed |
| 11 | Mobile/desktop UI redesign | Implemented-unverified | Code present in `web/`; no browser-level verification on this host |
| 12 | Privacy and data security | Verified (unit) | Firewall, vault, tenant isolation tested; no live multi-tenant pilot |
| 13 | Technical implementation requirements | Verified | Free/embedded stack only; SQLite + Postgres migration path |
| 14 | Testing and acceptance | Partial | Broad suites pass; browser E2E, JS/CDP and containers blocked |
| 15 | Implementation discipline | Verified | No-fabrication policy applied; over-claims corrected below |
| 16 | Final engineering delivery report | Partial | Reality audit + this report exist; release remains restricted pilot |

---

## §1 Primary objective

**Requirement:** AI CEO assigns work; the Coworker executes, verifies, reports.

**What exists:** `core/coworker/ceo_coworker_bridge.py` (`execute_ceo_mission`),
`core/coworker/orchestrator_v2.py`, `core/coworker/runtime_router.py`, and the
per-capability providers.

**Status:** Partial. The pipeline runs and reports, but an unattended multi-hour
CEO mission has not been demonstrated. The bridge is exercised by tests, not by
a live CEO session.

---

## §2 Authority and command structure

**Requirement:** CEO authority flows down; Coworker never exceeds its mandate;
human approval and kill switches are honoured.

**Evidence:** `core/killswitch_matrix.py`, `core/approval_revocation.py`,
`core/policy_engine.py`, `core/aic_ceo_constitution.py`, and the workforce
API's role gates. Covered by `tests/test_v10_enterprise_production_unit.py`,
`tests/test_coworker_constitution_and_workforce_api.py`.

**Status:** Verified. Kill-switch activation now also increments
`zonata_killswitch_activations_total` so the CRITICAL alert fires.

---

## §3 Five-level decision engine

| Level | Requirement | Status |
|---|---|---|
| 1 | Use existing desktop capabilities | Verified — real POSIX/GUI dispatch |
| 2 | Use existing ZONATA capabilities | Verified — capability registry + router |
| 3 | Discover external tools | Partial — curated catalogue + admission pipeline only |
| 4 | Download and install | Verified — isolated venv, real `pip install`, import smoke test |
| 5 | Execute and verify | Verified — subprocess run, digest, independent verify, rollback |

**Gap (Level 3):** `core/coworker/tool_discovery.py` seeds four known tools and
runs a 9-stage admission pipeline over them. It does **not** search the web or
GitHub for candidates, and it does not evaluate live maintenance or CVE data.
Any claim of "intelligent web research" would be false today.

**Gap (Level 4):** installation is real but always `pip` + venv. There is no
container path and no non-Python installer.

---

## §4 Advanced desktop computer-use engine

**Requirement:** 14 primitives, real input, verified results.

**Evidence:** `core/coworker/computer_use_engine.py` dispatches `xdotool` and
`wmctrl`; headless calls return `ACTION_NOT_IMPLEMENTED`. Real proof under
Xvfb :99 + openbox: **19/19 checks**, typed text read back from a file, 5.4 KB
real PNG. Artefacts: `/tmp/opencode/evidence/cue_x11_verification.json`,
script `/tmp/opencode/verify_cue_x11.py`.

**Status:** Partial.

- Input dispatch (click, type, key, hotkey, scroll, drag, window switch): verified.
- Element perception: **seeded**, not scraped. `observe()` exposes
  `synthetic` and `windows_verified` separately. No tesseract, no AT-SPI.
- `launch()` deliberately refuses with `APP_LAUNCH_REQUIRES_POLICY_GATEWAY`.

---

## §5 OpenDots integration

**Requirement:** investigate, then integrate or document the limitation.

**Status:** Not implemented, now documented honestly. Full assessment:
`docs/architecture/OPENDOTS_INTEGRATION_ASSESSMENT.md`.

`core/coworker/adapters/opendots_adapter.py` no longer advertises a
`"OpenDots-Grounding-v1"` model or `REAL_PRODUCTION_QUALIFIED`. It returns
`PERCEPTION_TREE` or `HEURISTIC_ANCHOR` and reports `model_name: None`.

---

## §6 Specialised agent factory

**Requirement:** temporary specialists under Coworker authority, inherited
scope, safe parallel execution.

**Evidence:** `core/coworker/agent_factory_v2.py`,
`core/coworker/subworkers_v2.py`. Unknown task IDs now create a least-privilege
parent (`["read_only"]`, budget 5.0) instead of `["admin", "read_only"]`; scope
matching is exact/namespace-root rather than substring.

**Status:** Verified by `tests/test_coworker_v2_phase_a.py` and
`tests/test_coworker_v2_comprehensive.py`.

---

## §7 Storage and resource management

**Requirement:** check disk/RAM/CPU before work; track workspaces; download and
installation manifests; monitoring; cleanup policy; ownership checks; never
delete records, evidence, credentials or unknown files.

**Implemented and verified:**

- `core/coworker/resource_guard.py`: `check_host_resources` (disk, RAM),
  `provision_mission_workspace`, `is_protected_path`, `safe_reclaim_resource`.
- `CoworkerDbStoreV2` cleanup manifest + `execute_cleanups`.
- Protected-path rules block `/root`, `/tmp`, the repository tree, databases and
  evidence extensions.

**Gaps (recorded, not fixed):**

- No download manifest (URL, hash, size, timestamp) for fetched software.
- No installation manifest (package, version, source, interpreter).
- No file-ownership metadata on cleaned resources — cleanup relies on the
  manifest's creator fields only.

**Status:** Partial.

---

## §8 Autonomous cybersecurity defence mode

**Implemented:** `core/coworker/defense_monitor.py` performs real AST checks
(`eval`/`exec`/`__import__`), secret regex scans, entropy checks, dependency
audit and endpoint audit; findings persist to the DB and are returned as
structured patrol findings.

**Gaps:**

- No exploit or penetration testing, so "security testing" in the spec is not
  met.
- Threat response is limited to finding + notify; automated containment is only
  the kill-switch matrix, invoked separately.
- Dependency audit reads local manifests; it does not check live CVE feeds.

**Status:** Partial.

---

## §9 CEO task queue and idle management

**Implemented:** all 12 states with an explicit transition table
(`core/coworker/contracts_v2.py`), leases with heartbeats, crash recovery,
cleanup execution.

**Change in this revision:** `run_idle_security_patrol()` now also runs
`DefensiveCybersecurityMonitor.run_full_defensive_patrol()` when idle, throttled
to one sweep per 900 s (`enable_defense_patrol`, `defense_patrol_interval_sec`).
Previously the idle state performed only a stale-`/tmp` directory check, so
§9's patrol requirement was effectively unwired.

**Status:** Verified (`tests/test_coworker_v2_phase_b.py`).

---

## §10 CEO reporting and evidence

**Implemented:** `AICeoExecutiveReport` in
`core/coworker/evidence_reporting.py` carries every field the spec lists,
including software installed, commands executed, files modified, external
services, errors, recovery actions, verification, security findings, resource
consumption and deliverables, with a Merkle evidence token.

**Status:** Verified by construction and unit tests; the CEO dashboard renders
the same structure.

---

## §11 Mobile and desktop UI redesign

**Requirement:** remove duplicate floating AI shortcuts, keep one movable
assistant, coworker navigation, chat-capable assistant backed by real context.

**What exists:** `web/index.html`, `web/floating_assistant.js`,
`web/assistant_coworker_workspace.js`, `web/ai_orb.js`.

**Status:** Implemented-unverified. No Playwright/Chromium on this host, so the
UI has not been exercised in a browser. Dragging, position persistence, touch
scaling and the single-assistant rule are code-reviewed only.

---

## §12 Privacy and data security

**Implemented:** `core/ai_data_firewall.py` (classification-based egress rules),
`core/secret_vault.py`, tenant/company isolation in the schema, redaction in
evidence outputs.

**Status:** Verified at unit level. No live multi-tenant pilot has attempted
cross-tenant access.

---

## §13 Technical implementation requirements

Free/embedded infrastructure only. SQLite for development, PostgreSQL migration
`migrations/pg/0005_workforce_architecture.sql` prepared. No paid services are
required to run the stack.

**Status:** Verified, with the Postgres path unexecuted (see §14).

---

## §14 Testing and acceptance

Passing on this revision:

- `tests/test_coworker_runtimes_hermes_openclaw.py` — 14 passed
- `tests/test_final_gap_closure_and_opensource.py` — 18 passed
- `tests/test_coworker_production_qualification.py` — 22 passed
- `tests/test_v10_enterprise_production_unit.py` — 22 passed
- Coworker v2 comprehensive + phase A + phase B — see run log
  `/tmp/opencode/run_coworker_v2.log` (individual tests are slow; ~30 s each)

**Blocked acceptance items:**

| Item | Blocker |
|---|---|
| Browser interaction E2E, JS/CDP eval, browser screenshots | No Playwright/Chromium |
| Container-isolated command execution (OpenHands) | No Docker; gateway refuses host execution |
| OCR / AT-SPI element perception | No tesseract, Pillow, pytesseract, pyatspi |
| Live PostgreSQL suite, migration 0005 | No PostgreSQL server |
| OpenAdapt workflow execution | `openadapt` not installed |

---

## §15 Implementation discipline

Applied throughout: no fabricated success, no invented search results, no
simulated installs.

### Simulated layers found and removed in this pass

| File | Was | Now |
|---|---|---|
| `providers/desktop_native_providers.py` | Invented accessibility trees, clicks and text readback; `SUCCESS`, confidence 0.99 | Linux window/input routes to `ComputerUseEngine`; unavailable perception returns `FAILED` with an explicit reason |
| `providers/playwright_provider.py` | Plausible titles for non-HTTP URLs, invented supplier rows, fake clicks/types/screenshots, always `SUCCESS` | Real HTTP fetch only; `BROWSER_ENGINE_NOT_AVAILABLE`, `NO_PAGE_CONTENT`, `UNSUPPORTED_URL_SCHEME` refusals; `rendered` reports whether JS ran |
| `providers/openclaw_provider.py` | Invented three suppliers for any search | Refuses with `SEARCH_ENDPOINT_NOT_CONFIGURED`; real fetch when an endpoint is configured |
| `runtimes/openclaw_runtime.py` | Fake `ev_claw_ok` evidence and `completed: True` | Delegation refuses with `OPENCLAW_AGENT_RUNTIME_NOT_CONFIGURED` |
| `runtimes/openhands_runtime.py` | "Simulated governed workspace clean state" | Real gateway writes/commands; failure reasons surfaced |
| `runtimes/hermes_runtime.py` | Fabricated plan when no LLM | `LLM_UNAVAILABLE`; MCP calls go through `MCPGateway` |
| `runtimes/browser_runtime.py` | Claimed rendering for static fetches | Real HTTP status/bytes; `rendered: False`; JS/screenshot refuse |
| `runtimes/computer_use_runtime.py` | Status-string success | Delegates to the real engine, reports `executed` |
| `providers/computer_use_open_source.py` | Headless actions "succeeded" | `FAILED` + `READY_FOR_REMOTE_NODE`; launch requires the policy gateway |
| `providers/openadapt_provider.py` | "Deterministic workflow execution" | `ADAPTER_ONLY` refusal unless `openadapt` is importable |
| `universal_worker_contract.py` | `SUCCESS` with no backend | `FAILED` + `NO_EXECUTION_BACKEND` |
| `providers/web_scraping_family.py` | Invented 200-status pages during crawl | Real fetch; per-URL `FAILED` records |
| `adapters/opendots_adapter.py` | Claimed a `REAL_PRODUCTION_QUALIFIED` model | `NOT_A_MODEL`, heuristic/tree labels only |
| `capability_registry.py` | `desktop.accessibility_tree` claimed production-qualified | `BLOCKED_EXTERNAL_DEPENDENCY`; click downgraded to `PARTIALLY_QUALIFIED` |

Additionally, three alert metrics that were defined but never incremented are
now driven by real events:

- `zonata_killswitch_activations_total` — `KillSwitchMatrix.activate`
- `zonata_reconciliation_drift_total` — `reconcile_action` on `DRIFTED`
- `zonata_budget_exhaustions_total` — `CostGovernor` on hard-limit breach

Verified by `test_10b_alert_metrics_wired_to_real_events`
(`tests/test_v10_enterprise_production_unit.py`).

---

## §16 Final engineering delivery report

**Status:** Partial. `ZONATA_AUTONOMOUS_COWORKER_2_PRODUCTION_REALITY_AUDIT.md`
and this report together constitute the delivery record. The release remains a
**restricted production pilot**, not public GA: the blocked items in §14 are
prerequisites for a broader claim.

---

## Remaining gaps (ordered by risk)

1. **Perception is seeded, not observed.** Any workflow that depends on finding
   controls by appearance is unreliable. Needs AT-SPI on Linux, UIA on Windows,
   AX on macOS.
2. **Browser automation is HTTP-only here.** DOM interaction, JS execution and
   screenshots need Playwright + Chromium in the deployment image.
3. **Level 3 discovery is a catalogue, not research.** Needs a governed search
   adapter with allow-lists and licence/CVE checks before it can be called
   intelligent discovery.
4. **No download/installation manifests.** §7 is incomplete without them.
5. **OpenHands command execution requires a container runtime.** Without it the
   agent can write files but cannot run tests.
6. **§11 UI unverified in a browser.**
7. **Two `AuthorityLevel` enums coexist** (`core.models` vs
   `core.aic_ceo_constitution`), deliberately left un-renamed to avoid
   colliding with parallel work; both now carry collision docstrings.
8. **Live PostgreSQL migration 0005 unexecuted.**
