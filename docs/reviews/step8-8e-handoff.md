# Sub-Step 8E Handoff: Human-Baseline Benchmark Program

## 1. Files Changed
```text
 core/benchmarks/__init__.py
 core/benchmarks/calibration.py
 core/benchmarks/claims.py
 core/benchmarks/recorder.py
 core/benchmarks/vault.py
 docs/benchmarks/HUMAN_BASELINE_METHOD.md
 tests/test_step8e_benchmark_program.py
 docs/reports/STEP8_REPORT.md
```

## 2. Commands to Re-run
```bash
PYTHONPATH=. pytest -v tests/test_step8e_benchmark_program.py tests/test_preservation_step8.py
```

## 3. Claims & Evidence
1. **Four Canonical Configurations:** Specified in `docs/benchmarks/HUMAN_BASELINE_METHOD.md`. Comparison is strictly Config C vs A or D vs A (`test_01`).
2. **Benchmark Vault Security:** Envelope encryption, role-based ACLs (`BENCHMARK_AUTHOR`, `BENCHMARK_EVALUATOR`, etc.), and MAC tamper detection verified (`test_02`).
3. **Informed Consent Gate:** Recording without consent blocked under `ParticipantConsentMissingError` (`test_03`).
4. **Ethical Telemetry & PII Scrubbing:** Irreversible participant pseudonymization and regex scrubbing of emails, cards, passwords verified (`test_04`).
5. **External Calibration Adapters:** TAC, GDPval, and Remote Labor Index adapters execute cleanly (`test_05`).
6. **Spend Cap Enforcement:** Hard dollar budget ceiling blocks runaway evaluations with `EvaluationBudgetExceededError` (`test_06`).
7. **Governed Claims Registry:** Validates sample sizes $N \ge 30$, 0 critical safety violations, and valid baseline comparisons (`test_07`).
8. **Anti-Marketing / Anti-Superhuman Shield:** Blocks invalid comparisons against Config B and under-sampled claims (`test_08`).
9. **Preservation Invariant:** All 2,137 Step 1–7 baseline files remain cryptographically untouched (`test_preservation_step8.py`).

## 4. Known Gaps
- None. Live external calibration uses simulated endpoints during CI runs to respect network boundaries.
