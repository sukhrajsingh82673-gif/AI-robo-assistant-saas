"""
Statistical Computation Engine for Human-Baseline Benchmarks (Rule 69 & ADR 0045)
Computes sample statistics, pooled standard deviation, Cohen's d effect size,
Welch's t-test p-value approximation, and 95% Confidence Intervals.
"""

from typing import List, Dict, Any, Tuple
import math


class BenchmarkStats:
    """Rigorous statistical calculations for comparative benchmark trials."""

    @staticmethod
    def mean(values: List[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def variance(values: List[float], sample: bool = True) -> float:
        if len(values) < 2:
            return 0.0
        m = BenchmarkStats.mean(values)
        denom = len(values) - 1 if sample else len(values)
        return sum((x - m) ** 2 for x in values) / denom

    @staticmethod
    def std_dev(values: List[float], sample: bool = True) -> float:
        return math.sqrt(BenchmarkStats.variance(values, sample=sample))

    @classmethod
    def cohens_d(cls, group_c: List[float], group_a: List[float]) -> float:
        """
        Computes Cohen's d effect size between Config C and Config A.
        Positive d indicates Config C higher than Config A.
        """
        n1 = len(group_c)
        n2 = len(group_a)
        if n1 < 2 or n2 < 2:
            return 0.0

        v1 = cls.variance(group_c)
        v2 = cls.variance(group_a)

        pooled_var = (((n1 - 1) * v1) + ((n2 - 1) * v2)) / (n1 + n2 - 2)
        pooled_sd = math.sqrt(pooled_var)

        if pooled_sd == 0:
            return 0.0

        return (cls.mean(group_c) - cls.mean(group_a)) / pooled_sd

    @classmethod
    def confidence_interval_95(cls, group_c: List[float], group_a: List[float]) -> Tuple[float, float]:
        """
        Computes 95% Confidence Interval for the difference in means (mean_C - mean_A).
        CI = delta +- 1.96 * SE_diff
        """
        n1 = len(group_c)
        n2 = len(group_a)
        if n1 < 2 or n2 < 2:
            return (0.0, 0.0)

        mean_diff = cls.mean(group_c) - cls.mean(group_a)
        se_diff = math.sqrt((cls.variance(group_c) / n1) + (cls.variance(group_a) / n2))

        margin = 1.96 * se_diff
        return (round(mean_diff - margin, 4), round(mean_diff + margin, 4))

    @classmethod
    def p_value_welch_approx(cls, group_c: List[float], group_a: List[float]) -> float:
        """
        Approximates two-tailed p-value using Welch's t-statistic converted to normal standard distribution.
        """
        n1 = len(group_c)
        n2 = len(group_a)
        if n1 < 2 or n2 < 2:
            return 1.0

        v1 = cls.variance(group_c)
        v2 = cls.variance(group_a)

        se_diff = math.sqrt((v1 / n1) + (v2 / n2))
        if se_diff == 0:
            return 1.0 if cls.mean(group_c) == cls.mean(group_a) else 0.0

        t_stat = abs(cls.mean(group_c) - cls.mean(group_a)) / se_diff

        # Normal CDF complementary error approximation for large N or standard tails
        # p = 2 * (1 - Phi(t))
        # Approximation: 2 * (1 / (1 + exp(1.6 * t)))
        approx_p = 2.0 / (1.0 + math.exp(1.65 * t_stat))
        return min(1.0, max(0.0001, approx_p))
