# FAILURE_TRIAGE — Stage-9 Full Baseline

Date: 2026-11-20 · Branch: `zonata/stage-9-pilot` @ `f59156c`
Raw output: `baseline_tests.txt` · Totals: **2051 passed, 50 failed, 26 skipped, 3 errors, 8 subtests passed** (767.87s)

Cause legend:

- **ENV-TMP** — hardcoded `/tmp` is read-only on this Android/Termux host (`OSError [Errno 30]`).
- **ENV-DB** — SQLite DB path is created under `/tmp`, so fixtures fail with `unable to open database file`.
- **ENV-ROOT** — hardcoded `/root/roboassistant/...` (Linux container path, absent on Termux).
- **ENV-DISPLAY** — assumes an X display / `xwininfo`; Termux has `DISPLAY` set without X.
- **ENV-METRIC** — Android `/proc` reports no host hardware metrics, so guards assert `0 > 0`.
- **ENV-EXEC** — host CLI/desktop execution (OpenCode CLI, xdg export) unavailable.
- **DEP-DOTENV** — `python-dotenv` imported but not in `requirements.txt`. Installing it makes the file pass.
- **FLAKY** — passes when the file is run in isolation; failed only under the full contended run.
- **DRIFT-SETTINGS** — test expects 45 categories / 202 settings; registry has 46 / 214 (see F2).
- **DRIFT-SQL** — source still contains 5 `INSERT OR REPLACE` statements (see F1).

| # | Test | Cause | Status |
|---|---|---|---|
| 1 | `test_acceptance_scenarios_v3::scenario_1_hermes` | ENV-DB | env |
| 2 | `test_acceptance_scenarios_v3::scenario_2_opencode` | ENV-TMP | env |
| 3 | `test_acceptance_scenarios_v3::scenario_3_boundaries` | ENV-TMP | env |
| 4 | `test_acceptance_scenarios_v3::scenario_5_stress` | ENV-DB | env |
| 5 | `test_acceptance_scenarios_v3::scenario_7_patrol` | ENV-DB | env |
| 6 | `test_acceptance_scenarios_v3::scenario_8_outbox` | ENV-DB | env |
| 7 | `test_acceptance_scenarios_v3::scenario_9_ledger` | ENV-TMP | env |
| 8 | `test_coworker_fabric::test_16_legacy_desktop_export` | ENV-EXEC | env |
| 9 | `test_coworker_v2_comprehensive::acceptance_03_ladder` | ENV-TMP | env |
| 10 | `test_coworker_v2_comprehensive::acceptance_04b_gui` | ENV-DISPLAY | env |
| 11 | `test_coworker_v2_comprehensive::acceptance_07_resource` | ENV-TMP | env |
| 12 | `test_coworker_v2_comprehensive::acceptance_11_api` | ENV-TMP | env |
| 13 | `test_coworker_v2_phase_a::milestone_2_level_1` | ENV-TMP | env |
| 14 | `test_coworker_v2_phase_a::milestone_2_level_3` | ENV-TMP | env |
| 15 | `test_coworker_v2_phase_a::milestone_2_level_5` | ENV-TMP | env |
| 16 | `test_coworker_v2_phase_b::milestone_5_preflight` | ENV-TMP | env |
| 17 | `test_coworker_v2_phase_b::milestone_5_workspace` | ENV-TMP | env |
| 18 | `test_coworker_v2_phase_b::milestone_5_assets` | ENV-TMP | env |
| 19 | `test_coworker_v2_phase_b::milestone_5_exhausted` | ENV-TMP | env |
| 20 | `test_coworker_v3_acceptance::hermes` | ENV-DB | env |
| 21 | `test_coworker_v3_acceptance::opencode_worktree` | ENV-TMP | env |
| 22 | `test_coworker_v3_acceptance::fleet_5000` | ENV-DB | env |
| 23 | `test_coworker_v3_acceptance::cyber_patrol` | ENV-TMP | env |
| 24 | `test_coworker_v3_acceptance::tenant_isolation` | ENV-TMP | env |
| 25 | `test_coworker_v3_acceptance::frontend_cockpit` | ENV-ROOT | env |
| 26 | `test_coworker_v3_comprehensive::constitutional` | ENV-TMP | env |
| 27 | `test_coworker_v3_comprehensive::7_stage_loop` | ENV-TMP | env |
| 28 | `test_cross_process_concurrency_coordination::test_01` | DEP-DOTENV | **fixed — passes** |
| 29 | `test_enterprise_settings_center::test_01_categories` | DRIFT-SETTINGS | stale test |
| 30 | `test_enterprise_settings_center::test_02_catalog` | DRIFT-SETTINGS | stale test |
| 31 | `test_executive_coworker_acceptance::mission_b` | ENV-DB | env |
| 32 | `test_executive_coworker_acceptance::mission_f` | ENV-EXEC | env |
| 33 | `test_executive_coworker_acceptance::mission_k` | ENV-TMP | env |
| 34 | `test_executive_coworker_acceptance::gap1_rule_engine` | ENV-DB | env |
| 35 | `test_executive_coworker_acceptance::gap2_perception` | ENV-DISPLAY | env |
| 36 | `test_executive_coworker_acceptance::gap5_opencode` | ENV-TMP | env |
| 37 | `test_executive_coworker_acceptance::gap6_outbox` | ENV-DB | env |
| 38 | `test_gemma4_adversarial_qualification::ledger_tamper` | ENV-TMP | env |
| 39 | `test_independent_enterprise_pilot_e2e::test_04_dlp` | FLAKY | **passes isolated** |
| 40 | `test_independent_enterprise_pilot_e2e::test_05_approval` | FLAKY | **passes isolated** |
| 41 | `test_independent_enterprise_pilot_e2e::test_07_failure` | FLAKY | **passes isolated** |
| 42 | `test_phase_14_cross_process_governance::test_01_budget` | FLAKY | **passes isolated** |
| 43 | `test_phase_14_cross_process_governance::test_02_token` | FLAKY | **passes isolated** |
| 44 | `test_postgresql_dialect_compatibility::test_01` | DRIFT-SQL | **F1** |
| 45 | `test_production_infrastructure_qualification::area_f_dr` | ENV-METRIC | env |
| 46 | `test_settings_registry_phase1::counts_are_exact` | DRIFT-SETTINGS | stale test |
| 47 | `test_settings_registry_phase1::every_category_mapped` | DRIFT-SETTINGS | stale test |
| 48 | `test_settings_v2_phase2::registry_effective_and_write` | DRIFT-SETTINGS | stale test |
| 49 | `test_universal_linux_terminal_fabric::test_07_metrics` | ENV-METRIC | env |
| 50 | `test_universal_terminal_operational_qualification::failure_05` | ENV-TMP | env |
| 51 | `test_coworker_v2_enterprise_qualification::enterprise_01` | ENV-TMP | env |
| 52 | `test_coworker_v2_enterprise_qualification::enterprise_02` | ENV-TMP | env |
| 53 | `test_coworker_v2_enterprise_qualification::enterprise_03` | ENV-TMP | env |

## Summary

| Class | Count |
|---|---|
| Environment-only (Termux/Android) | 41 |
| Flaky under full run (pass isolated) | 5 |
| Stale settings assertions | 5 |
| Source invariant drift (`INSERT OR REPLACE`) | 1 |
| Undeclared test dependency (fixed) | 1 |
| **Total** | **53** |

Re-run evidence for classes 2–5: `failures_detail.txt`, `flaky_rerun.txt` (18/18 passed after `pip install python-dotenv`).
