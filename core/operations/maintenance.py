"""
Preventive Maintenance & Reliability Engine (MTBF / MTTR)
=========================================================
Tracks scheduled maintenance, machine failures, MTBF, and MTTR.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MaintenanceTask(BaseModel):
    task_id: str
    workstation_id: str
    task_name: str
    interval_days: int
    last_completed_at: str
    next_due_at: str
    is_completed: bool = False


class BreakdownEvent(BaseModel):
    event_id: str
    workstation_id: str
    occurred_at: str
    repair_started_at: str
    repair_completed_at: str
    downtime_hours: float
    failure_cause: str


class ReliabilityMetrics(BaseModel):
    workstation_id: str
    total_operating_hours: float
    failure_count: int
    total_repair_hours: float
    mtbf_hours: float  # Mean Time Between Failures
    mttr_hours: float  # Mean Time To Repair
    availability_ratio: float


class MaintenanceReliabilityManager:
    """Computes equipment reliability metrics and tracks preventive maintenance."""

    @staticmethod
    def calculate_reliability(
        workstation_id: str,
        total_operating_hours: float,
        breakdowns: List[BreakdownEvent]
    ) -> ReliabilityMetrics:
        failure_count = len(breakdowns)
        total_repair_hours = sum(b.downtime_hours for b in breakdowns)

        # MTBF = Total Operating Hours / Number of Failures
        mtbf = (total_operating_hours / failure_count) if failure_count > 0 else total_operating_hours
        # MTTR = Total Repair Hours / Number of Failures
        mttr = (total_repair_hours / failure_count) if failure_count > 0 else 0.0

        total_time = total_operating_hours + total_repair_hours
        avail_ratio = (total_operating_hours / total_time) if total_time > 0 else 1.0

        return ReliabilityMetrics(
            workstation_id=workstation_id,
            total_operating_hours=round(total_operating_hours, 2),
            failure_count=failure_count,
            total_repair_hours=round(total_repair_hours, 2),
            mtbf_hours=round(mtbf, 2),
            mttr_hours=round(mttr, 2),
            availability_ratio=round(avail_ratio, 4)
        )
