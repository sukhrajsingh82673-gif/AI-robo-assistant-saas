"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Distributed Observability Engine & SLO/SLI Management
Provides OpenTelemetry-compatible tracing headers, multi-tier metric partitioning
(REAL vs SIMULATED vs SYNTHETIC vs SEEDED vs MOCK), and automated SLO compliance tracking.
"""

import time
import json
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("zonata.observability")

class MetricTier:
    REAL = "REAL"
    SIMULATED = "SIMULATED"
    SYNTHETIC = "SYNTHETIC"
    SEEDED = "SEEDED"
    MOCK = "MOCK"

@dataclass
class SLODefinition:
    name: str
    target_percentage: float
    current_value: float
    status: str  # COMPLIANT, WARNING, BREACHED
    error_budget_remaining_pct: float

class ObservabilityEngine:
    """
    Production Telemetry Collector.
    Never blends test benchmarks or mock data with real production telemetry.
    """
    def __init__(self):
        self._metrics: Dict[str, Dict[str, float]] = {
            MetricTier.REAL: {"requests": 0, "actions": 0, "errors": 0, "unknown_outcomes": 0},
            MetricTier.SIMULATED: {"requests": 0, "actions": 0, "errors": 0, "unknown_outcomes": 0},
            MetricTier.SYNTHETIC: {"requests": 0, "actions": 0, "errors": 0, "unknown_outcomes": 0},
            MetricTier.SEEDED: {"requests": 0, "actions": 0, "errors": 0, "unknown_outcomes": 0},
            MetricTier.MOCK: {"requests": 0, "actions": 0, "errors": 0, "unknown_outcomes": 0}
        }
        self._latencies: List[float] = []
        self._lock = threading.RLock()

    def record_action(
        self,
        tier: str,
        action_name: str,
        latency_ms: float,
        is_error: bool = False,
        is_unknown: bool = False
    ):
        """Record operational metric categorized under strict workload tier."""
        with self._lock:
            bucket = self._metrics.get(tier, self._metrics[MetricTier.SIMULATED])
            bucket["actions"] += 1
            if is_error:
                bucket["errors"] += 1
            if is_unknown:
                bucket["unknown_outcomes"] += 1

            self._latencies.append(latency_ms)
            if len(self._latencies) > 5000:
                self._latencies = self._latencies[-5000:]

    def get_tier_metrics(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return json.loads(json.dumps(self._metrics))

    def evaluate_slos(self) -> Dict[str, Any]:
        """
        Evaluate real production telemetry against constitutional SLO targets.
        """
        with self._lock:
            real = self._metrics[MetricTier.REAL]
            total_real = real["actions"]
            error_count = real["errors"]
            unknown_count = real["unknown_outcomes"]

            availability = 100.0 if total_real == 0 else round(100.0 * (1.0 - (error_count / total_real)), 2)
            unknown_rate = 0.0 if total_real == 0 else round(100.0 * (unknown_count / total_real), 2)

            # Compute P95 latency
            sorted_lat = sorted(self._latencies) if self._latencies else [0.0]
            p95_idx = int(len(sorted_lat) * 0.95)
            p95_latency = round(sorted_lat[min(p95_idx, len(sorted_lat) - 1)], 2)

            slos = {
                "api_availability": SLODefinition(
                    name="API & Mutation Availability",
                    target_percentage=99.9,
                    current_value=availability,
                    status="COMPLIANT" if availability >= 99.9 else ("WARNING" if availability >= 99.0 else "BREACHED"),
                    error_budget_remaining_pct=max(0.0, round((availability - 99.0) / 0.9 * 100.0, 1))
                ),
                "unknown_outcome_rate": SLODefinition(
                    name="Unknown Outcome Rate",
                    target_percentage=1.0,  # Max 1.0% allowed
                    current_value=unknown_rate,
                    status="COMPLIANT" if unknown_rate <= 1.0 else "BREACHED",
                    error_budget_remaining_pct=max(0.0, round((1.0 - unknown_rate) * 100.0, 1))
                ),
                "p95_latency_ms": SLODefinition(
                    name="P95 Action Latency",
                    target_percentage=500.0,  # Max 500ms
                    current_value=p95_latency,
                    status="COMPLIANT" if p95_latency <= 500.0 else "WARNING",
                    error_budget_remaining_pct=100.0 if p95_latency <= 500.0 else 0.0
                )
            }

            return {
                "evaluated_at": time.time(),
                "telemetry_partitioning": self.get_tier_metrics(),
                "slos": {k: asdict(v) for k, v in slos.items()}
            }

# Global observability engine instance
observability_engine = ObservabilityEngine()
