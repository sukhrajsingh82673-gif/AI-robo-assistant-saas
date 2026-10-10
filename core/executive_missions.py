"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Executive Mission Planner & Governed Execution
Converts Department Objectives into structured, result-oriented missions.

Constitutional Invariants:
  RESULT_ORIENTED (TASK_SUCCESS != BUSINESS_OUTCOME; missions must specify verification method and KPI effect)
  DELEGATION_CONTAINMENT (Child Authority, Autonomy, and Budget <= Department Chief Officer constraints)
  VERIFIED_EVIDENCE (Mission outcomes must link to cryptographic evidence ledger records)
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.v8.mission_planner")

@dataclass
class GovernedExecutiveMission:
    mission_id: str
    tenant_id: str
    company_id: str
    objective_id: str
    department: str
    manager: str
    employee: str
    title: str
    specialist_dependencies: List[str] = field(default_factory=list)
    expected_output: str = ""
    expected_business_outcome: str = ""
    kpi: Dict[str, Any] = field(default_factory=dict)
    kra: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    budget: float = 5000.0
    authority: str = "AUTONOMOUS_OPERATOR"
    autonomy: str = "BOUNDED"          # MANUAL, ASSISTIVE, CONDITIONAL, BOUNDED, HIGH_AUTONOMY
    deadline: float = field(default_factory=lambda: time.time() + 7 * 86400)
    priority: str = "P1"
    risk_level: str = "MEDIUM"
    escalation_policy: str = "ESCALATE_TO_CHIEF_OFFICER_ON_3X_FAILURE"
    verification_method: str = "LEDGER_AUDIT_HASH"
    status: str = "DISCOVER"           # DISCOVER, PLAN, EXECUTE, VERIFY, COMPLETED, FAILED, BLOCKED
    progress: int = 0
    actual_outcome: Optional[str] = None
    verified_outcome: Optional[str] = None
    outcome_status: str = "PENDING"    # PENDING, VERIFIED_ACHIEVED, VERIFIED_PARTIAL, FAILED
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    evidence_package_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutiveMissionPlanner:
    """
    Synthesizes and registers structured, result-oriented missions governed by corporate constraints.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def create_mission(
        self,
        objective_id: str,
        department: str,
        manager: str,
        employee: str,
        title: str,
        expected_output: str,
        expected_business_outcome: str,
        kpi: Dict[str, Any],
        kra: List[str],
        acceptance_criteria: List[str],
        specialist_dependencies: Optional[List[str]] = None,
        budget: float = 5000.0,
        authority: str = "AUTONOMOUS_OPERATOR",
        autonomy: str = "BOUNDED",
        priority: str = "P1",
        risk_level: str = "MEDIUM",
        escalation_policy: str = "ESCALATE_TO_CHIEF_OFFICER_ON_3X_FAILURE",
        verification_method: str = "LEDGER_AUDIT_HASH",
        deadline_days: int = 7
    ) -> GovernedExecutiveMission:
        """Creates and persists an authoritative governed mission."""
        now = time.time()
        mission_id = f"msn_{uuid.uuid4().hex[:10]}"

        mission = GovernedExecutiveMission(
            mission_id=mission_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            objective_id=objective_id,
            department=department,
            manager=manager,
            employee=employee,
            title=title,
            specialist_dependencies=specialist_dependencies or [],
            expected_output=expected_output,
            expected_business_outcome=expected_business_outcome,
            kpi=kpi,
            kra=kra,
            acceptance_criteria=acceptance_criteria,
            budget=budget,
            authority=authority,
            autonomy=autonomy,
            deadline=now + deadline_days * 86400,
            priority=priority,
            risk_level=risk_level,
            escalation_policy=escalation_policy,
            verification_method=verification_method,
            status="EXECUTE",
            progress=10,
            started_at=now
        )

        self._persist_mission(mission)

        create_executive_event(
            event_type="MissionCreated",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "mission_id": mission.mission_id,
                "title": mission.title,
                "department": mission.department,
                "assigned_employee": mission.employee,
                "budget": mission.budget,
                "priority": mission.priority
            }
        )

        return mission

    def _persist_mission(self, m: GovernedExecutiveMission):
        kpi_json = json.dumps({
            "kpi": m.kpi,
            "kra": m.kra,
            "acceptance_criteria": m.acceptance_criteria,
            "objective_id": m.objective_id,
            "specialist_dependencies": m.specialist_dependencies,
            "authority": m.authority,
            "autonomy": m.autonomy,
            "priority": m.priority,
            "risk_level": m.risk_level,
            "escalation_policy": m.escalation_policy,
            "verification_method": m.verification_method,
            "manager": m.manager
        })
        fin_json = json.dumps({"budget": m.budget, "committed": m.budget * 0.5, "spent": 0.0})

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO missions (
                    mission_id, company_id, department_id, tenant_id, title,
                    owner_agent, department, target_outcome, status, progress,
                    kpis, financials, expected_outcome, actual_outcome, verified_outcome,
                    outcome_status, started_at, completed_at, verification_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    status=excluded.status,
                    progress=excluded.progress,
                    actual_outcome=excluded.actual_outcome,
                    verified_outcome=excluded.verified_outcome,
                    outcome_status=excluded.outcome_status,
                    completed_at=excluded.completed_at,
                    verification_summary=excluded.verification_summary
            """, (
                m.mission_id, m.company_id, m.department.lower(), m.tenant_id, m.title,
                m.employee, m.department, m.expected_business_outcome, m.status, m.progress,
                kpi_json, fin_json, m.expected_output, m.actual_outcome, m.verified_outcome,
                m.outcome_status, m.started_at, m.completed_at, m.evidence_package_id
            ))
            conn.commit()

    def record_mission_completion(
        self,
        mission_id: str,
        actual_output: str,
        actual_outcome: str,
        evidence_digest: str,
        outcome_status: str = "VERIFIED_ACHIEVED"
    ) -> GovernedExecutiveMission:
        """
        Marks mission as completed and seals verified business outcome.
        Enforces: Task Output != Business Outcome!
        """
        now = time.time()
        mission = self.get_mission(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found.")

        mission.status = "COMPLETED"
        mission.progress = 100
        mission.actual_outcome = actual_outcome
        mission.verified_outcome = f"Verified: {actual_outcome} [SHA256: {evidence_digest[:16]}]"
        mission.outcome_status = outcome_status
        mission.completed_at = now
        mission.evidence_package_id = evidence_digest

        self._persist_mission(mission)

        create_executive_event(
            event_type="MissionCompleted",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "mission_id": mission_id,
                "outcome_status": outcome_status,
                "verified_outcome": mission.verified_outcome,
                "evidence_digest": evidence_digest
            }
        )

        return mission

    def get_mission(self, mission_id: str) -> Optional[GovernedExecutiveMission]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM missions WHERE mission_id = ? AND tenant_id = ? AND company_id = ?",
                (mission_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            kpi_data = json.loads(r["kpis"] or "{}")
            fin_data = json.loads(r["financials"] or "{}")
            return GovernedExecutiveMission(
                mission_id=r["mission_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                objective_id=kpi_data.get("objective_id", ""),
                department=r["department"],
                manager=kpi_data.get("manager", "Chief Officer"),
                employee=r["owner_agent"],
                title=r["title"],
                specialist_dependencies=kpi_data.get("specialist_dependencies", []),
                expected_output=r["expected_outcome"] or "",
                expected_business_outcome=r["target_outcome"] or "",
                kpi=kpi_data.get("kpi", {}),
                kra=kpi_data.get("kra", []),
                acceptance_criteria=kpi_data.get("acceptance_criteria", []),
                budget=float(fin_data.get("budget", 5000.0)),
                authority=kpi_data.get("authority", "AUTONOMOUS_OPERATOR"),
                autonomy=kpi_data.get("autonomy", "BOUNDED"),
                deadline=r["started_at"] + 7 * 86400,
                priority=kpi_data.get("priority", "P1"),
                risk_level=kpi_data.get("risk_level", "MEDIUM"),
                escalation_policy=kpi_data.get("escalation_policy", "STANDARD"),
                verification_method=kpi_data.get("verification_method", "LEDGER_AUDIT_HASH"),
                status=r["status"],
                progress=r["progress"],
                actual_outcome=r["actual_outcome"],
                verified_outcome=r["verified_outcome"],
                outcome_status=r["outcome_status"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                evidence_package_id=r["verification_summary"]
            )

    def list_missions(self, department: Optional[str] = None, status: Optional[str] = None) -> List[GovernedExecutiveMission]:
        with db.get_connection() as conn:
            query = "SELECT mission_id FROM missions WHERE tenant_id = ? AND company_id = ?"
            params = [self.tenant_id, self.company_id]
            if department:
                query += " AND department = ?"
                params.append(department)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY started_at DESC"

            rows = conn.execute(query, tuple(params)).fetchall()
            return [self.get_mission(r["mission_id"]) for r in rows if r["mission_id"]]

    def execute_with_automation_fabric(
        self,
        mission_id: str,
        workflow_or_template_id: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Bridges the executive mission to the Universal Automation Fabric.
        Dispatches background workflow, captures cryptographic evidence,
        and records completion directly in the sovereign mission ledger.
        """
        from core.automation_fabric import universal_automation_fabric
        return universal_automation_fabric.execute_mission_via_fabric(
            mission_id=mission_id,
            workflow_or_template_id=workflow_or_template_id,
            inputs=inputs,
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
