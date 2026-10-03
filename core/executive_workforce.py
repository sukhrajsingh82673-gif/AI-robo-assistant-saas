"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Executive Workforce Planner & Capacity Discovery
Plans workforce assignments by strictly checking existing employees and specialists
before creating new digital employees via V7 EmployeeFactory.

Constitutional Invariants:
  CANONICAL_DECISION_ORDER:
    1. EXISTING_EMPLOYEE
    2. EXISTING_SPECIALIST
    3. CROSS_DEPARTMENT_DELEGATION
    4. EMPLOYEE_TEMPLATE
    5. PROJECT_SPECIFIC_EMPLOYEE
    6. NEW_CAPABILITY_REQUEST
  ANTI_PROLIFERATION (Never instantiate a new employee if existing capacity satisfies capabilities)
  BOUNDED_SUBSET_AUTHORITY (Child authority <= Department Chief Officer authority)
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event
from core.ceo_workforce_controller import CEOWorkforceController, WorkforceDecisionOutcome, CEOWorkforceDecisionRecord
from core.employee_factory_v7 import employee_factory_v7
from core.employee_template import employee_template_registry, TemplateType
from core.workforce_collaboration_hub import WorkforceCollaborationHub

logger = logging.getLogger("zonata.v8.workforce_planner")

class WorkforcePlanningTier:
    EXISTING_EMPLOYEE = "EXISTING_EMPLOYEE"
    EXISTING_SPECIALIST = "EXISTING_SPECIALIST"
    CROSS_DEPARTMENT_DELEGATION = "CROSS_DEPARTMENT_DELEGATION"
    EMPLOYEE_TEMPLATE = "EMPLOYEE_TEMPLATE"
    PROJECT_SPECIFIC_EMPLOYEE = "PROJECT_SPECIFIC_EMPLOYEE"
    NEW_CAPABILITY_REQUEST = "NEW_CAPABILITY_REQUEST"

@dataclass
class WorkforcePlanResult:
    plan_id: str
    tenant_id: str
    company_id: str
    department: str
    objective_id: str
    selected_tier: str
    assigned_worker_ids: List[str]
    created_employee_id: Optional[str]
    workforce_gap_identified: bool
    gap_description: Optional[str]
    rationale: str
    delegation_chain: List[str]
    budget_allocated: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutiveWorkforcePlanner:
    """
    Evaluates departmental workforce requirements and provides governed staffing plans.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.ceo_controller = CEOWorkforceController()
        self.collab_hub = WorkforceCollaborationHub()

    def plan_workforce_for_department_objective(
        self,
        department: str,
        objective_id: str,
        objective_title: str,
        required_capabilities: List[str],
        budget_allocated: float = 15000.0,
        prefer_existing: bool = True
    ) -> WorkforcePlanResult:
        """
        Executes canonical 6-tier workforce discovery:
        1. Check active AI Employees in company matching capabilities.
        2. Check registered Type A specialists.
        3. Check cross-department delegation possibilities.
        4. If gap exists and cannot be met, instantiate from governed Employee Template (Type B).
        5. If specialized project-specific SOP needed, instantiate Type C.
        6. If no template exists, emit NEW_CAPABILITY_REQUEST.
        """
        now = time.time()
        plan_id = f"wf_plan_{uuid.uuid4().hex[:10]}"

        # Step 1 & 2: Use V7 CEOWorkforceController discovery
        decision_rec = self.ceo_controller.plan_and_assign_mission(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            objective=f"Department {department}: {objective_title}",
            required_capabilities=required_capabilities,
            department=department,
            budget_usd=budget_allocated
        )

        outcome = decision_rec.outcome
        assigned_workers = decision_rec.selected_workers
        created_emp_id = decision_rec.created_employee_id
        gap_identified = False
        gap_desc = None
        selected_tier = WorkforcePlanningTier.EXISTING_EMPLOYEE

        if outcome == WorkforceDecisionOutcome.USE_EXISTING_EMPLOYEE:
            selected_tier = WorkforcePlanningTier.EXISTING_EMPLOYEE
            rationale = f"Assigned existing operational employee {assigned_workers} possessing required capabilities {required_capabilities}."
        elif outcome == WorkforceDecisionOutcome.USE_EXISTING_AGENT:
            selected_tier = WorkforcePlanningTier.EXISTING_SPECIALIST
            rationale = f"Assigned pre-built specialist {assigned_workers} from system catalog."
        elif outcome == WorkforceDecisionOutcome.COMBINE_EXISTING_WORKFORCE:
            selected_tier = WorkforcePlanningTier.CROSS_DEPARTMENT_DELEGATION
            rationale = f"Formed collaborative cross-functional team {assigned_workers} uniting specialist and departmental employees."
        elif outcome == WorkforceDecisionOutcome.CREATE_TEMPLATE_EMPLOYEE:
            selected_tier = WorkforcePlanningTier.EMPLOYEE_TEMPLATE
            gap_identified = True
            gap_desc = f"Operational gap in {department} for capabilities {required_capabilities}; instantiated from governed template {decision_rec.template_considered}."
            rationale = f"Created governed employee {created_emp_id} via V7 24-Stage Factory."
        elif outcome == WorkforceDecisionOutcome.CREATE_PROJECT_EMPLOYEE:
            selected_tier = WorkforcePlanningTier.PROJECT_SPECIFIC_EMPLOYEE
            gap_identified = True
            gap_desc = f"Project-specific SOP requirements in {department}; instantiated Project-Specific employee."
            rationale = f"Created tailored employee {created_emp_id}."
        else:
            selected_tier = WorkforcePlanningTier.NEW_CAPABILITY_REQUEST
            gap_identified = True
            gap_desc = f"Unresolved capability requirement: {required_capabilities} exceeds current catalog and templates."
            rationale = "Escalated workforce capability gap to Human Owner."

        delegation_chain = ["AI_CEO", f"CHIEF_{department}_OFFICER"] + assigned_workers

        if gap_identified:
            create_executive_event(
                event_type="WorkforceGapDetected",
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                payload={
                    "department": department,
                    "objective_id": objective_id,
                    "gap_description": gap_desc,
                    "required_capabilities": required_capabilities,
                    "tier_selected": selected_tier
                }
            )

        return WorkforcePlanResult(
            plan_id=plan_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            department=department,
            objective_id=objective_id,
            selected_tier=selected_tier,
            assigned_worker_ids=assigned_workers,
            created_employee_id=created_emp_id,
            workforce_gap_identified=gap_identified,
            gap_description=gap_desc,
            rationale=rationale,
            delegation_chain=delegation_chain,
            budget_allocated=budget_allocated,
            created_at=now
        )
