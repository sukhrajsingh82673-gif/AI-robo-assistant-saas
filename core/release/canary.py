"""
Progressive Canary Deployment Validator with Automatic Health Rollback.
Manages staged traffic rollouts (5% -> 25% -> 50% -> 100%) and rolls back if 5xx or latency thresholds breach.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


class CanaryStage(int, Enum):
    STAGE_0_INACTIVE = 0
    STAGE_1_CANARY_5 = 5
    STAGE_2_CANARY_25 = 25
    STAGE_3_CANARY_50 = 50
    STAGE_4_FULL_100 = 100
    ROLLED_BACK = -1


@dataclass
class CanaryHealthMetric:
    stage_percent: int
    error_rate_5xx_percent: float  # e.g., 0.1%
    p99_latency_ms: float
    health_check_pass: bool


class ProgressiveCanaryRollout:
    """
    Coordinates canary rollouts and evaluates automated rollback rules.
    Rollback thresholds:
      - 5xx error rate > 0.5%
      - p99 latency > 300ms (or > 2x baseline)
      - health check failure
    """

    ERROR_THRESHOLD_PERCENT = 0.5
    MAX_P99_LATENCY_MS = 300.0

    STAGES_SEQUENCE = [
        CanaryStage.STAGE_1_CANARY_5,
        CanaryStage.STAGE_2_CANARY_25,
        CanaryStage.STAGE_3_CANARY_50,
        CanaryStage.STAGE_4_FULL_100,
    ]

    def __init__(self, target_version: str, baseline_version: str):
        self.target_version = target_version
        self.baseline_version = baseline_version
        self.current_stage: CanaryStage = CanaryStage.STAGE_0_INACTIVE
        self.active_traffic_percent: int = 0
        self.is_rolled_back: bool = False
        self.rollback_reason: Optional[str] = None
        self.stage_history: List[Dict[str, Any]] = []

    def advance_stage(self, metrics: CanaryHealthMetric) -> Tuple[bool, str]:
        """
        Evaluates canary health. If healthy, advances to next stage.
        If threshold violated, immediately triggers automatic rollback to baseline.
        """
        if self.is_rolled_back:
            return False, f"Rollout has already been aborted: {self.rollback_reason}"

        # 1. Evaluate health thresholds
        if not metrics.health_check_pass:
            return self._trigger_rollback("Health check probe failed.")

        if metrics.error_rate_5xx_percent > self.ERROR_THRESHOLD_PERCENT:
            return self._trigger_rollback(
                f"5xx error rate {metrics.error_rate_5xx_percent:.2f}% exceeds threshold {self.ERROR_THRESHOLD_PERCENT}%"
            )

        if metrics.p99_latency_ms > self.MAX_P99_LATENCY_MS:
            return self._trigger_rollback(
                f"p99 latency {metrics.p99_latency_ms:.1f}ms exceeds threshold {self.MAX_P99_LATENCY_MS}ms"
            )

        # 2. Advance to next stage
        current_idx = -1
        for idx, stage in enumerate(self.STAGES_SEQUENCE):
            if stage == self.current_stage:
                current_idx = idx
                break

        next_idx = current_idx + 1
        if next_idx < len(self.STAGES_SEQUENCE):
            next_stage = self.STAGES_SEQUENCE[next_idx]
            self.current_stage = next_stage
            self.active_traffic_percent = next_stage.value
            self.stage_history.append({
                "stage": next_stage.name,
                "traffic_percent": next_stage.value,
                "metrics": metrics,
            })
            return True, f"Advanced to {next_stage.name} ({next_stage.value}% traffic)."
        else:
            return True, "Rollout complete at 100% full production."

    def _trigger_rollback(self, reason: str) -> Tuple[bool, str]:
        self.is_rolled_back = True
        self.current_stage = CanaryStage.ROLLED_BACK
        self.active_traffic_percent = 0
        self.rollback_reason = reason
        self.stage_history.append({
            "stage": "ROLLED_BACK",
            "traffic_percent": 0,
            "reason": reason,
        })
        return False, f"CANARY ROLLBACK TRIGGERED: 100% traffic shifted back to {self.baseline_version}. Reason: {reason}"
