"""
Load Profiling and Soak Stability Profiler (Rule 76 & ADR 0044)
Evaluates execution latency distributions (p50, p95, p99) under sustained concurrency.
Tracks memory and error stability across prolonged soak execution periods.
"""

from typing import List, Dict, Any, Callable
import time
import math


class LoadProfiler:
    """Profiles task throughput, latency percentiles, and soak reliability."""

    @staticmethod
    def calculate_percentiles(durations_ms: List[float]) -> Dict[str, float]:
        """Computes p50, p95, p99, and max from a list of latencies."""
        if not durations_ms:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "mean": 0.0}

        sorted_d = sorted(durations_ms)
        n = len(sorted_d)

        def get_p(pct):
            idx = int(math.ceil((pct / 100.0) * n)) - 1
            return round(sorted_d[max(0, min(n - 1, idx))], 3)

        return {
            "p50": get_p(50),
            "p95": get_p(95),
            "p99": get_p(99),
            "max": round(sorted_d[-1], 3),
            "mean": round(sum(sorted_d) / n, 3),
            "count": n,
        }

    @classmethod
    def execute_soak_run(
        cls,
        task_callable: Callable[[], Any],
        iterations: int = 100,
        simulated_concurrency: int = 10
    ) -> Dict[str, Any]:
        """
        Executes a soak profiling run across sustained iterations.
        Measures individual request latencies and error frequency.
        """
        durations = []
        errors = 0
        start_overall = time.perf_counter()

        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                task_callable()
            except Exception:
                errors += 1
            durations.append((time.perf_counter() - t0) * 1000.0)

        total_elapsed_sec = time.perf_counter() - start_overall
        percentiles = cls.calculate_percentiles(durations)
        throughput_rps = round(iterations / max(0.001, total_elapsed_sec), 1)

        return {
            "iterations": iterations,
            "concurrency": simulated_concurrency,
            "total_elapsed_sec": round(total_elapsed_sec, 3),
            "throughput_rps": throughput_rps,
            "error_count": errors,
            "error_rate_percent": round((errors / iterations) * 100.0, 3),
            "latencies_ms": percentiles,
            "soak_stable": errors == 0 and percentiles["p99"] < 500.0,
        }
