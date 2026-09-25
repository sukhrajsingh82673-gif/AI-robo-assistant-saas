"""
RoboAssistant Company OS 2.0 — Employee Performance & Governance Tracking
Monitors verification compliance, execution failure rates, token expenditures,
and business contributions. Invariant: Performance metrics never expand authority.
"""

from typing import Dict, List, Optional, Any
import time
from .db import db

class EmployeePerformanceEngine:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"

    def record_mission_outcome(
        self,
        agent_id: str,
        verified_success: bool,
        cost_incurred: float = 0.0,
        business_contribution: float = 0.0
    ):
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM employee_performance_records WHERE agent_id = ?",
                (agent_id,)
            ).fetchone()

            if not row:
                conn.execute(
                    """
                    INSERT INTO employee_performance_records (
                        record_id, tenant_id, company_id, agent_id, missions_completed,
                        verification_rate, failures, avg_cost, business_contribution, recommendation, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONTINUE_DEPLOYMENT', ?)
                    """,
                    (
                        f"perf_{agent_id}", self.tenant_id, self.company_id, agent_id,
                        1 if verified_success else 0,
                        1.0 if verified_success else 0.0,
                        0 if verified_success else 1,
                        cost_incurred, business_contribution, time.time()
                    )
                )
            else:
                completed = row["missions_completed"] + (1 if verified_success else 0)
                failures = row["failures"] + (0 if verified_success else 1)
                total = completed + failures
                v_rate = completed / total if total > 0 else 1.0
                new_cost = (row["avg_cost"] + cost_incurred) / 2.0
                new_contrib = row["business_contribution"] + business_contribution

                # Formulate governance recommendation
                if v_rate < 0.8:
                    recommendation = "RETRAINING_RECOMMENDED"
                elif failures >= 3:
                    recommendation = "SUSPENSION_REVIEW"
                else:
                    recommendation = "CONTINUE_DEPLOYMENT"

                conn.execute(
                    """
                    UPDATE employee_performance_records SET
                        missions_completed = ?,
                        verification_rate = ?,
                        failures = ?,
                        avg_cost = ?,
                        business_contribution = ?,
                        recommendation = ?,
                        updated_at = ?
                    WHERE agent_id = ?
                    """,
                    (completed, v_rate, failures, new_cost, new_contrib, recommendation, time.time(), agent_id)
                )
            conn.commit()

    def get_performance_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM employee_performance_records WHERE agent_id = ?",
                (agent_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_workforce_performance(self) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM employee_performance_records WHERE company_id = ? ORDER BY verification_rate ASC",
                (self.company_id,)
            ).fetchall()
            return [dict(r) for r in rows]
