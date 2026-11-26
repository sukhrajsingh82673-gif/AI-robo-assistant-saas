# Sub-Step 8F Handoff: Benchmark Execution & Report

## 1. Files Changed
```text
 core/benchmarks/__init__.py
 core/benchmarks/report_generator.py
 core/benchmarks/runner.py
 core/benchmarks/stats.py
 docs/benchmarks/STEP8_BENCHMARK_REPORT.md
 tests/test_step8f_benchmark_report.py
 docs/reports/STEP8_REPORT.md
```

## 2. Commands to Re-run
```bash
PYTHONPATH=. pytest -v tests/test_step8f_benchmark_report.py tests/test_preservation_step8.py
```

## 3. Claims & Evidence
1. **Statistical Computation Accuracy:** Mean, SD, Cohen's $d$, 95% Confidence Intervals, and Welch's t p-value verified (`test_01`).
2. **Missing Baseline Handling:** Samples $N_A < 5$ classify as `NO_BASELINE` (`test_02`).
3. **Statistical Sample Sufficiency Gate:** Samples $N < 30$ or $p > 0.05$ classify as `INSUFFICIENT_EVIDENCE` (`test_03`).
4. **Empirical Improvement Status:** Large speedup with non-inferior accuracy and $N \ge 30, p < 0.05$ classifies as `BETTER` (`test_04`).
5. **Critical-Error Veto:** Any critical safety or sector boundary violation immediately vetoes the trial to `WORSE` (`test_05`).
6. **Delivered Benchmark Report:** `docs/benchmarks/STEP8_BENCHMARK_REPORT.md` rendered with complete statistical tables, cost comparisons, safety audit, and SHA-256 seal (`test_06`).
7. **Preservation Invariant:** All 2,137 Step 1–7 baseline files remain cryptographically untouched (`test_preservation_step8.py`).

## 4. Known Gaps
- None. Golden tasks span Discrete Manufacturing, Logistics, and Healthcare Operations.
