"""
Overall Equipment Effectiveness (OEE) Engine
============================================
OEE = Availability * Performance * Quality
Classifies downtime (planned vs unplanned) and computes manufacturing yield.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class OEEMetrics(BaseModel):
    workstation_id: str
    shift_date: str
    planned_production_minutes: float
    operating_minutes: float
    planned_downtime_minutes: float
    unplanned_downtime_minutes: float
    ideal_cycle_time_seconds: float
    total_units_produced: int
    good_units_produced: int
    scrap_units: int
    availability: float
    performance: float
    quality: float
    oee: float


class OEECalculator:
    """Calculates standardized manufacturing OEE and yield metrics."""

    @staticmethod
    def calculate_oee(
        workstation_id: str,
        shift_date: str,
        scheduled_minutes: float,
        planned_downtime_minutes: float,
        unplanned_downtime_minutes: float,
        ideal_cycle_time_seconds: float,
        total_units_produced: int,
        defective_units: int
    ) -> OEEMetrics:
        # 1. Availability
        planned_production_minutes = max(0.0, scheduled_minutes - planned_downtime_minutes)
        operating_minutes = max(0.0, planned_production_minutes - unplanned_downtime_minutes)

        availability = (operating_minutes / planned_production_minutes) if planned_production_minutes > 0 else 0.0

        # 2. Performance
        # Theoretical time to produce total units = total_units * (ideal_cycle_time_seconds / 60.0)
        ideal_operating_minutes = total_units_produced * (ideal_cycle_time_seconds / 60.0)
        performance = (ideal_operating_minutes / operating_minutes) if operating_minutes > 0 else 0.0
        # Cap performance at 1.0 (or realistic 100%) for standard OEE
        performance = min(1.0, performance)

        # 3. Quality
        good_units = max(0, total_units_produced - defective_units)
        quality = (good_units / total_units_produced) if total_units_produced > 0 else 0.0

        # 4. Total OEE
        oee = availability * performance * quality

        return OEEMetrics(
            workstation_id=workstation_id,
            shift_date=shift_date,
            planned_production_minutes=round(planned_production_minutes, 2),
            operating_minutes=round(operating_minutes, 2),
            planned_downtime_minutes=planned_downtime_minutes,
            unplanned_downtime_minutes=unplanned_downtime_minutes,
            ideal_cycle_time_seconds=ideal_cycle_time_seconds,
            total_units_produced=total_units_produced,
            good_units_produced=good_units,
            scrap_units=defective_units,
            availability=round(availability, 4),
            performance=round(performance, 4),
            quality=round(quality, 4),
            oee=round(oee, 4)
        )
