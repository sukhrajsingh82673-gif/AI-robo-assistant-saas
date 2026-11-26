"""
ZONATA SOP Compliance Calculator
Computes compliance scores deterministically from immutable step records.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from core.db import db


class SOPComplianceCalculator:
    """
    Computes compliance scores from persisted step execution records.
    Never relies on employee or agent self-reporting.
    A missing step record is a direct compliance failure.
    """

    @classmethod
    def calculate_compliance(
        cls,
        tenant_id: str,
        company_id: str,
        instance_id: str,
        total_expected_steps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculates compliance score from sop_step_records.
        Score = (compliant_steps / total_expected_steps) * 100.0.
        """
        with db.get_connection() as conn:
            # If total_expected_steps is not provided, fetch from instance
            if total_expected_steps is None or total_expected_steps <= 0:
                inst_row = conn.execute(
                    "SELECT total_steps FROM sop_instances WHERE id = ? AND tenant_id = ? AND company_id = ?",
                    (instance_id, tenant_id, company_id)
                ).fetchone()
                total_expected_steps = inst_row["total_steps"] if inst_row and inst_row["total_steps"] else 0

            records = conn.execute(
                """
                SELECT step_number, outcome, preconditions_passed, postconditions_passed
                FROM sop_step_records
                WHERE instance_id = ? AND tenant_id = ? AND company_id = ?
                ORDER BY step_number ASC
                """,
                (instance_id, tenant_id, company_id)
            ).fetchall()

        if total_expected_steps <= 0:
            if records:
                total_expected_steps = max(r["step_number"] for r in records)
            else:
                return {
                    "compliance_score": 0.0,
                    "total_expected_steps": 0,
                    "compliant_steps": 0,
                    "missing_steps": [],
                    "failed_steps": [],
                    "is_fully_compliant": False,
                }

        record_map = {r["step_number"]: r for r in records}
        compliant_steps = 0
        missing_steps: List[int] = []
        failed_steps: List[int] = []

        for step_num in range(1, total_expected_steps + 1):
            if step_num not in record_map:
                missing_steps.append(step_num)
                continue

            rec = record_map[step_num]
            outcome = rec["outcome"]
            pre_ok = bool(rec["preconditions_passed"])
            post_ok = bool(rec["postconditions_passed"])

            if outcome == "PASSED" and pre_ok and post_ok:
                compliant_steps += 1
            else:
                failed_steps.append(step_num)

        score = (compliant_steps / float(total_expected_steps)) * 100.0 if total_expected_steps > 0 else 0.0
        score = round(score, 2)

        return {
            "compliance_score": score,
            "total_expected_steps": total_expected_steps,
            "compliant_steps": compliant_steps,
            "missing_steps": missing_steps,
            "failed_steps": failed_steps,
            "is_fully_compliant": (compliant_steps == total_expected_steps and len(missing_steps) == 0),
        }

    @classmethod
    def recompute_instance_score(
        cls,
        tenant_id: str,
        company_id: str,
        instance_id: str,
    ) -> float:
        """
        Recomputes compliance score from step records and persists back to sop_instances.
        """
        result = cls.calculate_compliance(tenant_id, company_id, instance_id)
        score = result["compliance_score"]

        with db.get_connection() as conn:
            conn.execute(
                "UPDATE sop_instances SET compliance_score = ? WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (score, instance_id, tenant_id, company_id)
            )
            conn.commit()

        return score


sop_compliance_calculator = SOPComplianceCalculator()
