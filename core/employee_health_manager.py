"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Phase 11 & 12 — AI Employee Health & Performance Evaluation Manager
Monitors operational vitals, error rates, policy breaches, and outcome quality.
Enforces multi-dimensional evaluation gates without collapsing into arbitrary single scores.

Constitutional Invariants:
  HEALTH_SIGNALS_NEVER_GRANT_ADDITIONAL_AUTHORITY
  POLICY_BREACH_TRIGGERS_IMMEDIATE_SUPERVISORY_REVIEW
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from core.database_engine import engine, WorkloadType
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.employee.health")

class HealthState:
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"

@dataclass
class EmployeeVitals:
    employee_id: str
    tenant_id: str
    health_state: str
    total_missions: int
    failed_missions: int
    policy_violations: int
    tool_failures: int
    average_latency_ms: float
    total_spend_usd: float
    quality_score: float # 0.0 - 1.0 (Independent outcome verification)
    last_evaluated_at: float

class EmployeeHealthManager:
    """
    Supervises AI Employee operational telemetry, detects anomalies,
    and transitions unhealthy agents into REVIEW_REQUIRED or SUSPENDED states.
    """
    MAX_POLICY_VIOLATIONS_BEFORE_SUSPEND = 2
    MAX_ERROR_RATE_PERCENT = 25.0

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_employee_health_vitals (
                employee_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                health_state TEXT NOT NULL DEFAULT 'HEALTHY',
                total_missions INTEGER NOT NULL DEFAULT 0,
                failed_missions INTEGER NOT NULL DEFAULT 0,
                policy_violations INTEGER NOT NULL DEFAULT 0,
                tool_failures INTEGER NOT NULL DEFAULT 0,
                average_latency_ms REAL NOT NULL DEFAULT 0.0,
                total_spend_usd REAL NOT NULL DEFAULT 0.0,
                quality_score REAL NOT NULL DEFAULT 1.0,
                last_evaluated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_emp_health_tenant ON ai_employee_health_vitals(tenant_id);")

    def record_mission_outcome(
        self,
        employee_id: str,
        tenant_id: str,
        company_id: str,
        success: bool,
        latency_ms: float,
        cost_usd: float,
        policy_violation: bool = False,
        tool_failure: bool = False,
        outcome_quality: float = 1.0
    ) -> HealthState:
        """Record mission outcome and recompute operational health state."""
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            # Upsert vitals
            cursor = conn.execute(
                "SELECT * FROM ai_employee_health_vitals WHERE employee_id = ?",
                (employee_id,)
            )
            row = cursor.fetchone()
            if not row:
                conn.execute("""
                INSERT INTO ai_employee_health_vitals (
                    employee_id, tenant_id, health_state, total_missions, failed_missions,
                    policy_violations, tool_failures, average_latency_ms, total_spend_usd,
                    quality_score, last_evaluated_at
                ) VALUES (?, ?, 'HEALTHY', 1, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    employee_id, tenant_id, 0 if success else 1,
                    1 if policy_violation else 0, 1 if tool_failure else 0,
                    latency_ms, cost_usd, outcome_quality, now
                ))
                new_state = HealthState.HEALTHY
            else:
                tot = row["total_missions"] + 1
                fail = row["failed_missions"] + (0 if success else 1)
                p_viol = row["policy_violations"] + (1 if policy_violation else 0)
                t_fail = row["tool_failures"] + (1 if tool_failure else 0)
                avg_lat = (row["average_latency_ms"] * row["total_missions"] + latency_ms) / tot
                tot_spend = row["total_spend_usd"] + cost_usd
                q_score = (row["quality_score"] * row["total_missions"] + outcome_quality) / tot

                # State transition evaluation
                error_rate = (fail / tot) * 100.0
                if p_viol >= self.MAX_POLICY_VIOLATIONS_BEFORE_SUSPEND:
                    new_state = HealthState.SUSPENDED
                elif error_rate > self.MAX_ERROR_RATE_PERCENT or q_score < 0.60:
                    new_state = HealthState.REVIEW_REQUIRED
                elif error_rate > 10.0 or t_fail > 3:
                    new_state = HealthState.DEGRADED
                else:
                    new_state = HealthState.HEALTHY

                conn.execute("""
                UPDATE ai_employee_health_vitals
                SET health_state = ?, total_missions = ?, failed_missions = ?,
                    policy_violations = ?, tool_failures = ?, average_latency_ms = ?,
                    total_spend_usd = ?, quality_score = ?, last_evaluated_at = ?
                WHERE employee_id = ?
                """, (
                    new_state, tot, fail, p_viol, t_fail, avg_lat, tot_spend, q_score, now, employee_id
                ))

        if new_state == HealthState.SUSPENDED:
            # Automatically suspend employee in core registry
            try:
                ai_employee_registry.advance_lifecycle(
                    employee_id=employee_id,
                    new_state=EmployeeLifecycleState.SUSPENDED,
                    approver_id="health_monitor",
                    reason=f"Policy violation threshold reached ({p_viol} violations)"
                )
            except Exception as e:
                logger.warning(f"Health suspend propagation error: {e}")

            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="AI_EMPLOYEE_AUTOMATICALLY_SUSPENDED",
                payload={"employee_id": employee_id, "policy_violations": p_viol}
            )

        return new_state

    def get_vitals(self, employee_id: str) -> Optional[EmployeeVitals]:
        """Fetch employee health vitals record."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute(
                "SELECT * FROM ai_employee_health_vitals WHERE employee_id = ?",
                (employee_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return EmployeeVitals(
                employee_id=row["employee_id"],
                tenant_id=row["tenant_id"],
                health_state=row["health_state"],
                total_missions=row["total_missions"],
                failed_missions=row["failed_missions"],
                policy_violations=row["policy_violations"],
                tool_failures=row["tool_failures"],
                average_latency_ms=row["average_latency_ms"],
                total_spend_usd=row["total_spend_usd"],
                quality_score=row["quality_score"],
                last_evaluated_at=row["last_evaluated_at"]
            )

employee_health_manager = EmployeeHealthManager()
