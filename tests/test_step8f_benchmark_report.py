"""
Tests for Sub-Step 8F: Empirical Benchmark Execution & Report (Rule 67, 68, 69, 72, ADR 0045, ADR 0046)
Validates statistical metrics (Cohen's d, Welch's t, 95% CI), classification state machine,
Critical-Error Veto, report generation, and sealed report integrity.
"""

import pytest
from pathlib import Path

from core.benchmarks.stats import BenchmarkStats
from core.benchmarks.runner import (
    BenchmarkRunner,
    BenchmarkStatus,
    TrialMeasurements,
)
from core.benchmarks.report_generator import BenchmarkReportGenerator


class TestStep8FBenchmarkReport:

    # 1. Statistical Calculations
    def test_01_stats_calculations_mean_sd_cohens_d_ci(self):
        c_durations = [10.0, 12.0, 11.0, 9.0, 10.5]
        a_durations = [100.0, 110.0, 105.0, 95.0, 102.0]

        mean_c = BenchmarkStats.mean(c_durations)
        assert mean_c == 10.5
        mean_a = BenchmarkStats.mean(a_durations)
        assert mean_a == 102.4

        # Cohen's d: large negative value because C takes much less time than A
        d = BenchmarkStats.cohens_d(c_durations, a_durations)
        assert d < -10.0  # Huge effect size

        # 95% CI
        ci_lower, ci_upper = BenchmarkStats.confidence_interval_95(c_durations, a_durations)
        assert ci_lower < ci_upper
        assert ci_upper < 0  # Entire interval indicates C is significantly faster

        # Welch's t p-value approximation
        p = BenchmarkStats.p_value_welch_approx(c_durations, a_durations)
        assert p < 0.001

    # 2. Classification: NO_BASELINE
    def test_02_classification_no_baseline(self):
        # Config A has only 3 samples (< 5 required)
        res = BenchmarkRunner.evaluate_task_comparison(
            task_id="TASK-001",
            task_name="Test Task",
            industry_code="C28",
            config_c=TrialMeasurements(durations_seconds=[10.0]*10, successes=[True]*10),
            config_a=TrialMeasurements(durations_seconds=[100.0]*3, successes=[True]*3),
        )
        assert res["status"] == BenchmarkStatus.NO_BASELINE
        assert "minimum 5 required" in res["reason"]

    # 3. Classification: INSUFFICIENT_EVIDENCE
    def test_03_classification_insufficient_evidence(self):
        # Both have 15 samples (>= 5, but < 30 required for empirical significance)
        res = BenchmarkRunner.evaluate_task_comparison(
            task_id="TASK-002",
            task_name="Small Sample Task",
            industry_code="G47",
            config_c=TrialMeasurements(durations_seconds=[15.0]*15, successes=[True]*15),
            config_a=TrialMeasurements(durations_seconds=[200.0]*15, successes=[True]*15),
        )
        assert res["status"] == BenchmarkStatus.INSUFFICIENT_EVIDENCE
        assert "significance threshold" in res["reason"]

    # 4. Classification: BETTER (Sample Sufficient)
    def test_04_classification_better_statistically_significant(self):
        # 40 samples each, p < 0.05, d < -0.2 (faster), 100% accuracy
        c_times = [20.0 + (i % 3) for i in range(40)]
        a_times = [500.0 + (i % 10) * 10 for i in range(40)]

        res = BenchmarkRunner.evaluate_task_comparison(
            task_id="TASK-003",
            task_name="High Speedup Production Task",
            industry_code="K64",
            config_c=TrialMeasurements(durations_seconds=c_times, successes=[True]*40, costs_minor_usd=[10]*40),
            config_a=TrialMeasurements(durations_seconds=a_times, successes=[True]*38 + [False]*2, costs_minor_usd=[500]*40),
        )
        assert res["status"] == BenchmarkStatus.BETTER
        assert res["speedup_ratio"] > 20.0
        assert res["cost_savings_percent"] > 95.0
        assert res["p_value"] < 0.05
        assert "trial_seal_sha256" in res

    # 5. Critical-Error Veto (Rule 72)
    def test_05_critical_error_veto_disqualification(self):
        # System is 50x faster with 100 samples, but committed 1 critical regulatory violation
        c_times = [10.0 for _ in range(50)]
        a_times = [500.0 for _ in range(50)]

        res = BenchmarkRunner.evaluate_task_comparison(
            task_id="TASK-004-UNSAFE",
            task_name="Adversarial Clinical Boundary Task",
            industry_code="Q86",
            config_c=TrialMeasurements(
                durations_seconds=c_times,
                successes=[True]*50,
                critical_safety_violations=1  # Boundary breach!
            ),
            config_a=TrialMeasurements(durations_seconds=a_times, successes=[True]*50),
        )
        assert res["status"] == BenchmarkStatus.WORSE
        assert res["veto_applied"] is True
        assert "CRITICAL_ERROR_VETO" in res["reason"]
        assert res["critical_safety_violations"] == 1

    # 6. Report Generator and Document Verification
    def test_06_benchmark_report_generation_and_integrity(self):
        report_md = BenchmarkReportGenerator.write_report_file("docs/benchmarks/STEP8_BENCHMARK_REPORT.md")
        assert Path("docs/benchmarks/STEP8_BENCHMARK_REPORT.md").exists()

        assert "# Step 8 Empirical Human-Baseline Benchmark Report" in report_md
        assert "Config C (Zonata Autonomous System) vs Config A" in report_md
        assert "TASK-C28-AP-01" in report_md
        assert "TASK-H52-BOL-01" in report_md
        assert "TASK-Q86-ADMIN-01" in report_md
        assert "Report Seal (SHA-256):" in report_md
        assert "98.6%" in report_md  # AP cost savings
