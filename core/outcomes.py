"""
RoboAssistant Company OS 1.0 — Business Outcome Engine
Strict Distinction: TASK_SUCCESS != BUSINESS_OUTCOME.
Measures Expected vs Actual vs Verified Business Impact.
"""

from typing import Dict, Any, Optional
import time
from .db import db

class BusinessOutcomeEngine:
    @staticmethod
    def evaluate_mission_outcome(
        tenant_id: str,
        company_id: str,
        mission_id: str,
        task_success: bool,
        expected_metric: Dict[str, Any],
        actual_measured_metric: Dict[str, Any],
        verified_evidence_metric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesizes machine execution status with real verified economic outcomes.
        """
        # Distinguish execution from outcome
        variance = 0.0
        exp_val = expected_metric.get("value", 0.0)
        ver_val = verified_evidence_metric.get("value", 0.0)

        if isinstance(exp_val, (int, float)) and isinstance(ver_val, (int, float)) and exp_val > 0:
            variance = ((ver_val - exp_val) / exp_val) * 100.0

        if not task_success:
            outcome_status = "FAILED_EXECUTION"
        elif ver_val >= exp_val and exp_val > 0:
            outcome_status = "VERIFIED_ACHIEVED"
        elif ver_val > 0:
            outcome_status = "VERIFIED_PARTIAL"
        else:
            outcome_status = "TASK_COMPLETE_OUTCOME_PENDING"

        record = {
            "mission_id": mission_id,
            "task_success": task_success,
            "expected": expected_metric,
            "actual_measured": actual_measured_metric,
            "verified": verified_evidence_metric,
            "variance_pct": round(variance, 2),
            "outcome_status": outcome_status,
            "evaluated_at": time.time()
        }

        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE missions
                SET outcome_status = ?, expected_outcome = ?, actual_outcome = ?, verified_outcome = ?
                WHERE tenant_id = ? AND mission_id = ?
                """,
                (outcome_status, str(expected_metric), str(actual_measured_metric), str(verified_evidence_metric), tenant_id, mission_id)
            )
            conn.commit()

        return record
