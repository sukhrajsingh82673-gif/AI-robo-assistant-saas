"""
Service Level Objective (SLO) and Error Budget Tracking Engine.
Computes 99.9% availability, p95/p99 latency compliance, and enforces deployment freezes when budget burns out.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class ServiceLevelObjective:
    name: str
    target_percent: float  # e.g., 99.9%
    total_events: int = 0
    good_events: int = 0

    @property
    def current_sli_percent(self) -> float:
        if self.total_events == 0:
            return 100.0
        return (self.good_events / self.total_events) * 100.0

    @property
    def error_budget_remaining_percent(self) -> float:
        # Allowed error rate = (100 - target_percent)
        allowed_error_rate = 100.0 - self.target_percent
        if allowed_error_rate <= 0:
            return 0.0
        actual_error_rate = 100.0 - self.current_sli_percent
        # Remaining budget = 100 * (1 - actual_error_rate / allowed_error_rate)
        remaining = 100.0 * (1.0 - (actual_error_rate / allowed_error_rate))
        return max(-100.0, min(100.0, remaining))


@dataclass
class ErrorBudgetStatus:
    slo_name: str
    target_percent: float
    current_sli_percent: float
    budget_remaining_percent: float
    is_deployment_frozen: bool
    burn_rate_alert: Optional[str] = None


class SloTracker:
    """
    Tracks platform SLOs and governs deployment freeze triggers based on error budget health.
    """

    def __init__(self):
        # slo_name -> ServiceLevelObjective
        self._slos: Dict[str, ServiceLevelObjective] = {
            "api_availability": ServiceLevelObjective("api_availability", 99.9),
            "p99_latency": ServiceLevelObjective("p99_latency", 99.0),
            "webhook_delivery": ServiceLevelObjective("webhook_delivery", 99.5),
        }

    def record_event(self, slo_name: str, is_good: bool, count: int = 1):
        slo = self._slos.get(slo_name)
        if not slo:
            raise KeyError(f"Unknown SLO '{slo_name}'. Registered: {list(self._slos.keys())}")
        slo.total_events += count
        if is_good:
            slo.good_events += count

    def get_budget_status(self, slo_name: str) -> ErrorBudgetStatus:
        slo = self._slos.get(slo_name)
        if not slo:
            raise KeyError(f"Unknown SLO '{slo_name}'")

        sli = slo.current_sli_percent
        budget_remaining = slo.error_budget_remaining_percent

        # Deployment freeze if error budget is exhausted (< 0%)
        is_frozen = budget_remaining <= 0.0

        # Burn rate alerts
        burn_alert = None
        if budget_remaining <= 10.0 and not is_frozen:
            burn_alert = f"WARNING: Error budget critical ({budget_remaining:.1f}% remaining). High burn rate detected."
        elif is_frozen:
            burn_alert = f"ALERT: Error budget EXHAUSTED ({budget_remaining:.1f}%). Deployments FROZEN."

        return ErrorBudgetStatus(
            slo_name=slo_name,
            target_percent=slo.target_percent,
            current_sli_percent=round(sli, 3),
            budget_remaining_percent=round(budget_remaining, 2),
            is_deployment_frozen=is_frozen,
            burn_rate_alert=burn_alert,
        )

    def is_release_permitted(self) -> Tuple[bool, str]:
        """Deployment gate: blocks releases if ANY customer-facing SLO has exhausted its error budget."""
        for name in self._slos:
            status = self.get_budget_status(name)
            if status.is_deployment_frozen:
                return False, f"Deployment BLOCKED: Error budget for '{name}' is exhausted ({status.budget_remaining_percent}%)."
        return True, "All SLO error budgets healthy. Release permitted."
