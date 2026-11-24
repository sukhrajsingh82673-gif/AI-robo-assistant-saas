"""
SLA Escalation Clock Engine
===========================
Tracks Response and Resolution SLA windows and fires automated escalation triggers.
Thresholds:
- 50% window: SLA Warning
- 75% window: Supervisor Alert
- 90% window: Executive Escalation
- 100% window: SLA Breach
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


class SLAConfig(BaseModel):
    priority: str
    response_sla_minutes: int
    resolution_sla_minutes: int


class SLAClockState(BaseModel):
    ticket_id: str
    priority: str
    created_at: str
    response_sla_minutes: int
    resolution_sla_minutes: int
    first_response_at: Optional[str] = None
    resolved_at: Optional[str] = None
    current_status: str = "open"
    escalation_level: str = "nominal"  # 'nominal', 'warning_50', 'alert_75', 'escalation_90', 'breached_100'


class SLAEscalationClock:
    """Calculates SLA percentage elapsed and raises escalation events."""

    DEFAULT_POLICIES = {
        "critical": SLAConfig(priority="critical", response_sla_minutes=15, resolution_sla_minutes=120),
        "high": SLAConfig(priority="high", response_sla_minutes=60, resolution_sla_minutes=480),
        "medium": SLAConfig(priority="medium", response_sla_minutes=240, resolution_sla_minutes=1440),
        "low": SLAConfig(priority="low", response_sla_minutes=480, resolution_sla_minutes=2880),
    }

    def __init__(self, policies: Optional[Dict[str, SLAConfig]] = None):
        self.policies = policies or self.DEFAULT_POLICIES

    def initialize_clock(self, ticket_id: str, priority: str, created_at: Optional[str] = None) -> SLAClockState:
        policy = self.policies.get(priority, self.policies["medium"])
        c_at = created_at or datetime.now(timezone.utc).isoformat()
        return SLAClockState(
            ticket_id=ticket_id,
            priority=priority,
            created_at=c_at,
            response_sla_minutes=policy.response_sla_minutes,
            resolution_sla_minutes=policy.resolution_sla_minutes,
            escalation_level="nominal"
        )

    def evaluate_clock(self, state: SLAClockState, current_time: Optional[datetime] = None) -> Tuple[SLAClockState, float, str]:
        """Evaluates SLA progress against resolution SLA. Returns (state, pct_elapsed, escalation_action)."""
        if state.resolved_at:
            return state, 0.0, "RESOLVED"

        now = current_time or datetime.now(timezone.utc)
        created_dt = datetime.fromisoformat(state.created_at)
        elapsed_minutes = (now - created_dt).total_seconds() / 60.0
        pct_elapsed = elapsed_minutes / float(state.resolution_sla_minutes)

        action = "NOMINAL"
        if pct_elapsed >= 1.0:
            state.escalation_level = "breached_100"
            action = "BREACH_CRITICAL_DISPATCH"
        elif pct_elapsed >= 0.90:
            state.escalation_level = "escalation_90"
            action = "EXECUTIVE_ESCALATION"
        elif pct_elapsed >= 0.75:
            state.escalation_level = "alert_75"
            action = "SUPERVISOR_ALERT"
        elif pct_elapsed >= 0.50:
            state.escalation_level = "warning_50"
            action = "WARNING_INTERNAL_NOTIFICATION"

        return state, round(pct_elapsed, 4), action
