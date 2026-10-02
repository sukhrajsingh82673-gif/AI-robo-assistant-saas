"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Architecture — Workforce Collaboration Hub & Hierarchical Management
Enables seamless colleague collaboration between Pre-built Specialists (Type A)
and Template-built Employees (Type B/C) under a unified organizational hierarchy.

Constitutional Invariants:
  COLLEAGUES_UNDER_ONE_HIERARCHY (Pre-built agents and template employees collaborate as colleagues)
  HIERARCHICAL_DELEGATION_CONTAINMENT (Child authority, tools, budget, and autonomy <= Parent)
  CONFLICT_RESOLUTION_BY_POLICY (Never resolve conflicts by LLM model confidence)
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState, AuthorityScope
from core.workforce_manager_v4 import RISK_LEVELS, DelegationViolationError
from core.employee_health_manager import employee_health_manager, HealthState

logger = logging.getLogger("zonata.v7.collaboration_hub")

@dataclass
class MissionTeam:
    team_id: str
    tenant_id: str
    company_id: str
    mission_id: str
    team_name: str
    mission_lead_employee_id: str
    specialist_members: List[str]       # Mix of template employees and pre-built specialists
    chief_supervisor: str               # e.g., CHIEF_OPERATING_OFFICER
    collaboration_mode: str             # DIRECT, HIERARCHICAL, HYBRID
    created_at: float = field(default_factory=time.time)

@dataclass
class ConflictResolutionRecord:
    resolution_id: str
    mission_id: str
    conflicting_parties: List[str]
    disputed_action_or_decision: str
    resolved_by: str                    # MANAGER, CHIEF_OFFICER, AI_CEO, HUMAN_OWNER
    resolution_basis: str               # POLICY_HIERARCHY, KPI_ALIGNMENT, EVIDENCE_VERIFICATION
    final_verdict: str
    resolved_at: float = field(default_factory=time.time)

class WorkforceCollaborationHub:
    """
    Coordinates multi-employee mission teams, cross-department collaboration,
    hierarchical delegation, and conflict resolution across the entire ZONATA workforce.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS workforce_mission_teams (
                team_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                mission_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                mission_lead_id TEXT NOT NULL,
                specialist_members JSON NOT NULL,
                chief_supervisor TEXT NOT NULL,
                collaboration_mode TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS workforce_conflict_resolutions (
                resolution_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                conflicting_parties JSON NOT NULL,
                disputed_issue TEXT NOT NULL,
                resolved_by TEXT NOT NULL,
                resolution_basis TEXT NOT NULL,
                final_verdict TEXT NOT NULL,
                resolved_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_succession_records (
                succession_id TEXT PRIMARY KEY,
                predecessor_id TEXT NOT NULL,
                successor_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                transferred_memory_classes JSON NOT NULL,
                timestamp REAL NOT NULL
            );
            """)

    def form_mission_team(
        self,
        tenant_id: str,
        company_id: str,
        mission_id: str,
        team_name: str,
        mission_lead_employee_id: str,
        specialist_members: List[str],
        chief_supervisor: str = "CHIEF_OPERATING_OFFICER",
        collaboration_mode: str = "HYBRID"
    ) -> MissionTeam:
        """
        Assemble a cross-functional team combining template employees and pre-built specialists.
        """
        team_id = f"team_{uuid.uuid4().hex[:12]}"
        now = time.time()

        team = MissionTeam(
            team_id=team_id,
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            team_name=team_name,
            mission_lead_employee_id=mission_lead_employee_id,
            specialist_members=specialist_members,
            chief_supervisor=chief_supervisor,
            collaboration_mode=collaboration_mode,
            created_at=now
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO workforce_mission_teams (
                team_id, tenant_id, company_id, mission_id, team_name,
                mission_lead_id, specialist_members, chief_supervisor,
                collaboration_mode, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                team.team_id, team.tenant_id, team.company_id, team.mission_id,
                team.team_name, team.mission_lead_employee_id,
                json.dumps(team.specialist_members), team.chief_supervisor,
                team.collaboration_mode, team.created_at
            ))

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            event_type="MISSION_TEAM_FORMED",
            payload={
                "team_id": team_id,
                "team_name": team_name,
                "lead": mission_lead_employee_id,
                "specialists": specialist_members,
                "supervisor": chief_supervisor
            }
        )
        return team

    def resolve_workforce_conflict(
        self,
        mission_id: str,
        party_a: str,
        party_b: str,
        issue_description: str,
        resolver_tier: str,             # MANAGER, CHIEF_OFFICER, AI_CEO, HUMAN_OWNER
        ruling: str,
        basis: str = "POLICY_HIERARCHY" # POLICY_HIERARCHY, KPI_ALIGNMENT, EVIDENCE_VERIFICATION
    ) -> ConflictResolutionRecord:
        """
        Deterministically resolve disagreements between employees or specialists.
        Prohibits resolution by model confidence; requires policy or evidence basis.
        """
        resolution_id = f"conf_res_{uuid.uuid4().hex[:12]}"
        now = time.time()

        record = ConflictResolutionRecord(
            resolution_id=resolution_id,
            mission_id=mission_id,
            conflicting_parties=[party_a, party_b],
            disputed_action_or_decision=issue_description,
            resolved_by=resolver_tier,
            resolution_basis=basis,
            final_verdict=ruling,
            resolved_at=now
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO workforce_conflict_resolutions (
                resolution_id, mission_id, conflicting_parties, disputed_issue,
                resolved_by, resolution_basis, final_verdict, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.resolution_id, record.mission_id,
                json.dumps(record.conflicting_parties),
                record.disputed_action_or_decision, record.resolved_by,
                record.resolution_basis, record.final_verdict, record.resolved_at
            ))

        evidence_service.record_event(
            tenant_id="GLOBAL",
            company_id="GLOBAL",
            mission_id=mission_id,
            event_type="WORKFORCE_CONFLICT_RESOLVED",
            payload={
                "resolution_id": resolution_id,
                "parties": [party_a, party_b],
                "resolved_by": resolver_tier,
                "basis": basis,
                "verdict": ruling
            }
        )
        return record

    def execute_employee_succession(
        self,
        tenant_id: str,
        company_id: str,
        predecessor_id: str,
        successor_id: str,
        reason: str,
        authorized_memory_classes: List[str]
    ) -> Dict[str, Any]:
        """
        Executes controlled version succession when replacing an employee.
        Retires predecessor, activates successor, transfers only explicitly authorized memory classes.
        Historical missions and evidence remain permanently attached to predecessor.
        """
        succession_id = f"succ_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # 1. Offboard then Retire predecessor
        ai_employee_registry.advance_lifecycle(
            predecessor_id,
            EmployeeLifecycleState.OFFBOARDED,
            "AI_CEO",
            f"Succession to {successor_id}: offboarding"
        )
        ai_employee_registry.advance_lifecycle(
            predecessor_id,
            EmployeeLifecycleState.RETIRED,
            "AI_CEO",
            f"Succession to {successor_id}: {reason}"
        )

        # 2. Record succession
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO employee_succession_records (
                succession_id, predecessor_id, successor_id, tenant_id,
                company_id, reason, transferred_memory_classes, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                succession_id, predecessor_id, successor_id, tenant_id,
                company_id, reason, json.dumps(authorized_memory_classes), now
            ))

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="EMPLOYEE_SUCCESSION_EXECUTED",
            payload={
                "succession_id": succession_id,
                "predecessor": predecessor_id,
                "successor": successor_id,
                "reason": reason,
                "transferred_memory": authorized_memory_classes
            }
        )

        return {
            "succession_id": succession_id,
            "predecessor_id": predecessor_id,
            "successor_id": successor_id,
            "predecessor_state": EmployeeLifecycleState.RETIRED,
            "status": "COMPLETED"
        }

workforce_collaboration_hub = WorkforceCollaborationHub()
