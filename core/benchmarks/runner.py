"""
Benchmark Execution Runner and Classification Engine (Rule 69, Rule 72, ADR 0045)
Executes comparative trial analysis between Config C (Zonata Autonomous System)
and Config A (Unassisted Human Baseline). Enforces Critical-Error Veto and statistical gates.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import hashlib
import json
from core.benchmarks.stats import BenchmarkStats


class BenchmarkStatus:
    NO_BASELINE = "NO_BASELINE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    WORSE = "WORSE"
    EQUIVALENT = "EQUIVALENT"
    BETTER = "BETTER"


@dataclass
class TrialMeasurements:
    durations_seconds: List[float] = field(default_factory=list)
    successes: List[bool] = field(default_factory=list)
    costs_minor_usd: List[int] = field(default_factory=list)
    defects_count: int = 0
    critical_safety_violations: int = 0


class BenchmarkRunner:
    """Executes and classifies empirical benchmarks comparing Config C vs Config A."""

    MIN_BASELINE_COUNT = 5
    MIN_SIGNIFICANCE_COUNT = 30
    EQUIVALENCE_MARGIN_RATIO = 0.05  # +/- 5%

    @classmethod
    def evaluate_task_comparison(
        cls,
        task_id: str,
        task_name: str,
        industry_code: str,
        config_c: TrialMeasurements,
        config_a: TrialMeasurements,
    ) -> Dict[str, Any]:
        """
        Evaluates task performance comparison between Config C and Config A.
        Applies Critical-Error Veto and derives statistical classification.
        """
        n_c = len(config_c.durations_seconds)
        n_a = len(config_a.durations_seconds)

        # 1. Check for missing baseline
        if n_a < cls.MIN_BASELINE_COUNT:
            return {
                "task_id": task_id,
                "task_name": task_name,
                "industry_code": industry_code,
                "status": BenchmarkStatus.NO_BASELINE,
                "reason": f"Config A human baseline has only N={n_a} samples (minimum {cls.MIN_BASELINE_COUNT} required).",
                "n_c": n_c,
                "n_a": n_a,
            }

        # 2. Check for Critical-Error Veto (Rule 72)
        if config_c.critical_safety_violations > 0:
            return {
                "task_id": task_id,
                "task_name": task_name,
                "industry_code": industry_code,
                "status": BenchmarkStatus.WORSE,
                "veto_applied": True,
                "reason": f"CRITICAL_ERROR_VETO: System recorded {config_c.critical_safety_violations} critical safety or regulatory violations. Automatic disqualification.",
                "n_c": n_c,
                "n_a": n_a,
                "critical_safety_violations": config_c.critical_safety_violations,
            }

        # 3. Calculate metrics
        mean_time_c = BenchmarkStats.mean(config_c.durations_seconds)
        mean_time_a = BenchmarkStats.mean(config_a.durations_seconds)
        sd_time_c = BenchmarkStats.std_dev(config_c.durations_seconds)
        sd_time_a = BenchmarkStats.std_dev(config_a.durations_seconds)

        # Speedup ratio: Human Time / System Time
        speedup_ratio = round(mean_time_a / max(0.001, mean_time_c), 2)

        # Success rate
        succ_rate_c = (sum(1 for s in config_c.successes if s) / n_c) * 100.0 if n_c > 0 else 0.0
        succ_rate_a = (sum(1 for s in config_a.successes if s) / n_a) * 100.0 if n_a > 0 else 0.0

        # Cost reduction: (Cost_A - Cost_C) / Cost_A
        mean_cost_c = BenchmarkStats.mean([float(c) for c in config_c.costs_minor_usd])
        mean_cost_a = BenchmarkStats.mean([float(c) for c in config_a.costs_minor_usd])
        cost_savings_pct = (
            round(((mean_cost_a - mean_cost_c) / max(0.01, mean_cost_a)) * 100.0, 2)
            if mean_cost_a > 0
            else 0.0
        )

        # Statistical inference
        # In speedup, lower duration is better, so invert duration for effect size or use Cohen's d directly on speed
        # Duration Cohen's d: negative d means system takes less time (faster)
        d_duration = BenchmarkStats.cohens_d(config_c.durations_seconds, config_a.durations_seconds)
        ci_95 = BenchmarkStats.confidence_interval_95(config_c.durations_seconds, config_a.durations_seconds)
        p_val = BenchmarkStats.p_value_welch_approx(config_c.durations_seconds, config_a.durations_seconds)

        # 4. Check statistical sample sufficiency
        if n_c < cls.MIN_SIGNIFICANCE_COUNT or n_a < cls.MIN_SIGNIFICANCE_COUNT or p_val > 0.05:
            status = BenchmarkStatus.INSUFFICIENT_EVIDENCE
            reason = f"Sample size (N_C={n_c}, N_A={n_a}) or p-value (p={p_val:.4f}) does not meet significance threshold (N >= 30, p < 0.05)."
        else:
            # High sample size and p < 0.05
            # Faster completion (d_duration < -0.2) AND equal or better success rate
            if d_duration < -0.2 and succ_rate_c >= succ_rate_a - 1.0:
                status = BenchmarkStatus.BETTER
                reason = f"Statistically significant speedup ({speedup_ratio}x) with non-inferior accuracy (p={p_val:.4f}, d={d_duration:.2f})."
            elif abs(d_duration) <= 0.2 and abs(succ_rate_c - succ_rate_a) <= 5.0:
                status = BenchmarkStatus.EQUIVALENT
                reason = "Performance within standard +/- 5% equivalence band."
            else:
                status = BenchmarkStatus.WORSE
                reason = f"System underperformed human baseline (p={p_val:.4f}, d={d_duration:.2f})."

        result = {
            "task_id": task_id,
            "task_name": task_name,
            "industry_code": industry_code,
            "status": status,
            "reason": reason,
            "n_c": n_c,
            "n_a": n_a,
            "mean_duration_c_sec": round(mean_time_c, 3),
            "mean_duration_a_sec": round(mean_time_a, 3),
            "sd_duration_c": round(sd_time_c, 3),
            "sd_duration_a": round(sd_time_a, 3),
            "speedup_ratio": speedup_ratio,
            "success_rate_c_percent": round(succ_rate_c, 2),
            "success_rate_a_percent": round(succ_rate_a, 2),
            "cost_savings_percent": cost_savings_pct,
            "cohens_d": round(d_duration, 3),
            "ci_95": ci_95,
            "p_value": round(p_val, 4),
            "critical_safety_violations": config_c.critical_safety_violations,
        }

        # Deterministic trial digest
        canonical = json.dumps(result, sort_keys=True)
        result["trial_seal_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return result
