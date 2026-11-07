# Coworker Report Corrections — 2026-11-07

Independent review of the Coworker 2.0 / 3.0 / Executive Coworker reports found
claims that did not survive checking. The reports are kept in place (history is
not rewritten); each over-claiming report now carries a correction banner that
points here and to the authoritative status document.

Authoritative status: [`SPEC_VS_IMPLEMENTATION_GAP_REPORT.md`](SPEC_VS_IMPLEMENTATION_GAP_REPORT.md).

---

## 1. Local inference: rule engine, not a language model

The most serious correction. `core/coworker/local_inference_adapter.py`
contained an embedded "local model" that was a keyword router:

- `LocalModelEngine.DEFAULT_MODEL = "zonata-local-reasoner-v1"`.
- A post-tool turn returned *"Executive Assessment Complete … All operations
  verified against constitutional constraints. Data integrity confirmed."*
  Nothing had been verified.
- `LocalInferenceStatus` reported `available=True`, `provider="zonata_embedded_engine"`,
  `status="ONLINE"` with `enable_embedded_engine=True` by default.
- `LocalOpenAIServer` advertised `zonata-local-reasoner-v1` and `hermes-3-local`
  under `/v1/models` as if they were models.
- `HermesInferenceGateway` therefore returned `available: True`,
  `status: COMPLETED` with no model anywhere in the process.

### What it is now

| Field | Rule engine (embedded or HTTP) | Real LLM (Ollama / endpoint) |
|---|---|---|
| `available` | `False` | `True` |
| `status` | `RULE_ENGINE_ONLY` | `ONLINE` / `COMPLETED` |
| `is_language_model` | `False` | `True` |
| `engine_kind` | `RULES` | `LLM` |
| `capabilities` | `["tool_routing"]` | `["tool_calling", "multi_step_planning"]` |
| `active_model` | `None` | the endpoint's model id |

- The engine id is `zonata-rules-v1`; `/v1/models` returns
  `{"object": "engine", "is_language_model": false}`, and `/health` returns
  `RULE_ENGINE_ONLY`.
- The post-tool turn emits `RULE_ENGINE_DIGEST: N tool result(s) received … No
  language-model analysis was performed; the raw tool output is the
  authoritative result.`
- A prompt with no matching rule emits `RULE_ENGINE_ONLY: … No language model is
  available, so no answer was generated.` It no longer claims constitutional
  compliance, a spending ceiling, or tenant isolation.
- Rule-based tool calls still execute. That is real, deterministic behaviour,
  and it is labelled as such rather than reported as inference.
- The constructor accepts `enable_rule_engine` (`ZONATA_ENABLE_RULE_ENGINE`,
  default on); `enable_embedded_engine` remains as a deprecated alias.

Regression: `tests/test_executive_coworker_acceptance.py::test_gap1_local_rule_engine_and_server`
asserts `available is False`, `is_language_model is False`, `status ==
RULE_ENGINE_ONLY`, exactly one routed `terminal_exec` call, and a real
`git status` exit code of 0.

---

## 2. Frontend "qualified" without a browser

`ZONATA_COWORKER_3_FRONTEND_ACCEPTANCE_REPORT.md` qualifies three viewports and
certifies "fully compliant". This host has no Playwright, Chromium or Chrome.
The DOM ids and CSS were inspected in source; nothing was rendered, resized or
screenshotted. The report now says so. §11 remains **unverified in a browser**.

---

## 3. "100% green" regression claims

Both regression reports list suites that genuinely passed, but:

- the counts are for the listed suites at that commit, not the whole repository;
- some suites are slow or environment-dependent and were run separately;
- passing unit tests are not evidence that external dependencies work.

`ZONATA_COWORKER_FINAL_GAP_REGISTER.md` ("100% GAPS RESOLVED") and
`ZONATA_COWORKER_FINAL_ENTERPRISE_ACCEPTANCE.md` are corrected accordingly. Open
gaps are enumerated in the gap report.

---

## 4. Security verdicts

`ZONATA_COWORKER_ENTERPRISE_SECURITY_REPORT.md` ended with "FULLY VERIFIED AND
OPERATIONAL"; `ZONATA_COWORKER_3_ENTERPRISE_SECURITY_QUALIFICATION.md` presents
unit-test passes as a qualification. Neither was externally audited and no live
attack traffic was generated. In code, incidents are recorded `DETECTED` (not
`CONTAINED`), and remediation is only "verified" when a callable host-state
check confirms it.

---

## 5. Desktop perception

`ZONATA_COWORKER_OPENDOTS_DESKTOP_ACCEPTANCE.md` names Pillow/PIL, OpenCV and
OCR. None are installed. Its grounding "accuracy" benchmark compares the
heuristic's fixed relative anchors against coordinates written in the same test,
so a 0 px error is self-agreement, not accuracy; the code now labels it
`HEURISTIC_SELF_CHECK`. What is real: `xwininfo` window enumeration and
dispatched X11 input, verified 14/14 under Xvfb
(`/tmp/opencode/evidence/x11_window_tree_verification.json`). Interactive element
perception inside a window is seeded and labelled `source: seeded_scene`.

---

## 6. Scale, performance and recovery

- 5,000 is a registered identity cap, not 5,000 concurrent workers; the pool is
  bounded at 16 threads.
- Throughput and latency come from short local benchmarks, not a soak test.
- Recovery is tested by simulated process interruption, not power loss.
- The capability matrix's "Level 3" labels describe in-container exercises;
  `openclaw`, Docker/Podman, Playwright/Chromium, Pillow, tesseract and pyatspi
  are not installed.

---

## 7. Report locations

All Coworker report files that used to sit in the repository root now live in
`docs/reports/`. The root holds only `README.md`, `GEMINI.md`,
`anti-gravity-instructions.md` and `THIRD_PARTY_LICENSES.md`.

---

## 8. Additional code corrections from the same review

These were found while checking the reports above.

| Area | Was | Is now |
|---|---|---|
| Capability discovery | Unknown features got a generated stub `def <feature>(*a, **k): return True`, which then "passed" its own test. | `NO_CANDIDATE_IN_CATALOG`; the lifecycle stops at `DISCOVER`. |
| Capability integration | `exec(source_code, ...)` ran untrusted capability code inside the host process. | Module is syntax-checked, AST-inspected, and executed only as a subprocess with a timeout. |
| Capability approval | Docstring claimed PolicyEngine validation; it was a score threshold. | `approval_basis: SECURITY_SCORE_THRESHOLD`; policy-gateway routing remains required. |
| Credential brokering | `broker_database_credential()` returned `authorized: True` unconditionally. | Requires a host-supplied authorization callback; otherwise `CREDENTIAL_BROKER_NOT_CONFIGURED` or `AUTHORIZATION_DENIED`. |
| OpenDots window tree | Invented a `Virtual Root Framebuffer` window on error and sliced titles out of raw lines. | Regex-parsed real windows with geometry; `NO_DISPLAY` when there is no display; unnamed/WM windows excluded. |
| OpenDots screenshot | Hashed a placeholder `FALLBACK_SCREEN_FRAMEBUFFER` and called it a screenshot. | No capture -> `screenshot_sha256: None`, `perception_mode: HEADLESS_SIMULATED`. |
| Grounding "accuracy" | Compared fixed relative anchors with the same coordinates written in the test. | Labelled `HEURISTIC_SELF_CHECK` with `ground_truth_source`; the mission no longer asserts a 2 px "accuracy". |
| Mission names | "Engine Crash Recovery" (nothing crashed), "Sustained … Operation" (12 items). | Renamed to what they exercise; no crash-injection or soak claim. |

## 9. Local inference regression evidence

`tests/test_executive_coworker_acceptance.py::test_gap1_local_rule_engine_and_server`
asserts `available is False`, `is_language_model is False`, `status ==
RULE_ENGINE_ONLY`, one routed `terminal_exec` call, and a real `git status`
exit code of 0. The rule engine still routes; it just no longer pretends to
reason.

---

## 10. Second pass — reports regenerated by the parallel agent

After the first correction pass, a parallel Antigravity session regenerated
several report files both at the repository root and in `docs/reports/`,
reintroducing the claims that had just been corrected. Those files were
corrected again, and the root copies were removed.

| Report | Correction applied |
|---|---|
| `HERMES_LOCAL_INFERENCE_VERIFICATION.md` | “Air-gapped network” is false: outbound HTTPS works (github.com returned HTTP 200). No weights were downloaded. The engine is a keyword router, not a planning model; the 8088 server serves rules, not completions. Mission L did not inject a crash. |
| `ENTERPRISE_ARCHITECTURE.md` | The component table's “VERIFIED … (100% Green)” means an in-container test. The inference section now separates the rule engine from a real model endpoint. |
| `CAPABILITY_INTEGRATION_MATRIX.md` | “Level 3 = Production” relabelled as “end-to-end test with sealed evidence, not production-proven”. Rows for Hermes, local inference, air-gap, OpenDots and “crash recovery” corrected. |
| `OPENDOTS_DESKTOP_ACCEPTANCE.md` | Pillow/OpenCV/OCR are absent; the verified display is 1280x800, with 1920x1080 only a configuration. Dialog recovery is partial, and the DLP engine does not scan pixels. |
| `FINAL_GAP_REGISTER.md` | “100% GAPS RESOLVED” replaced with the real position: fixes with passing in-repo tests, several requirements Partial/Blocked. |
| `24H_SOAK.md` | No 24-hour soak was run; added to the correction set. |
| `ENTERPRISE_SECURITY_REPORT.md` | “100% detection” rows are sample matches by AST/pattern rules, not measured rates. Closing “VERIFIED OPERATIONAL” verdict replaced with the actual test scope. |
| `FINAL_ENTERPRISE_ACCEPTANCE.md` | “APPROVED FOR PRODUCTION” → “restricted production pilot”; the crash-recovery claim for Mission L removed (no crash injected). |
| `FULL_SYSTEM_REGRESSION_REPORT.md` | “100% GREEN” reworded as “listed suites passed in this container”; Mission L name corrected. |
| `PERFORMANCE_AND_RECOVERY_REPORT.md` | Section 4.1 rewritten: Mission L does not kill a process or replay a journal. Recovery table now says which failures were actually tested. |

Root cleanup: the 19 `ZONATA_COWORKER_*.md` files that reappeared at the
repository root were removed; the maintained copies live in `docs/reports/`.
The root now holds only `README.md`, `GEMINI.md`, `anti-gravity-instructions.md`
and `THIRD_PARTY_LICENSES.md`.

`/ZONATA_COWORKER_*.md` is now ignored at the repository root so a regenerated
copy cannot be committed by accident. If the parallel agent regenerates
root-level reports, re-run this correction pass rather than trusting the files.

---

## 11. Autonomy runtime — scope of the word “automatic”

The new `CoworkerAutonomySupervisor` removes the *request-driven* conditions:
missions, the executive queue and security patrols are ticked by a tenant-scoped
daemon instead of waiting for an HTTP call.

It does **not** remove governance or infrastructure conditions. Specifically:

* A `WAITING` / `AWAITING_APPROVAL` mission or a Delegation-of-Authority work
  item stays held until a human decides. The supervisor only reports it.
* A KillSwitch at GLOBAL / TENANT / COMPANY level stops work on the next tick,
  and the mission dispatcher re-checks the matrix for direct step calls.
* A mission that cannot produce a deliverable without an LLM is marked
  `BLOCKED` with the reason; it is not completed or fabricated.
* Browser/OCR/container capabilities remain blocked by missing host tooling.
* Duplicate-run protection is a host-local `flock`; it is not a distributed
  lease. Multi-host deployments still need PostgreSQL advisory locking.

“Automatic” therefore means **automatically scheduled inside the existing
gates**, not “ungoverned” or “independent of model availability”.

---

## 12. CEO mission `COMPLETED` means “plan record sealed”, not “objective achieved”

The executive work-item pipeline exposed a pre-existing wording problem in
`execute_ceo_mission()`. The bridge writes a `MISSION_PLAN_RECORD` JSON file,
re-reads it, verifies its SHA-256 and seals it in the evidence ledger. It then
returned:

* `execution_status = "COMPLETED"`
* `final_outcome.message = "Executive objective '…' fulfilled. Deliverable report sealed."`
* evidence metadata `action = "CEO_MISSION_COMPLETED"`

That reads as a business success even when no research, transaction or external
action occurred. The record itself was already labelled `MISSION_PLAN_RECORD`
and its summary said it was not proof of achievement, but the surrounding
strings contradicted that.

Corrected:

* `final_outcome.message` now says the plan record was created and sealed and
  explicitly that this is not proof the business objective was achieved.
* `final_outcome.objective_achieved = false` is always present.
* Evidence metadata action is `CEO_MISSION_PLAN_RECORD_SEALED` and carries
  `objective_achieved: false`.
* The autonomy supervisor copies `objective_achieved` into `queue_results`, so
  an API caller sees the distinction without reading the deliverable.

`execution_status` keeps the value `COMPLETED` because existing contract tests
assert it; it denotes “the pipeline contract completed and a hash-verified plan
record exists”. It must not be quoted as evidence that the objective was
achieved.

