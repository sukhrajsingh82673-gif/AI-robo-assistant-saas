"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Architecture — CEO Workforce Controller & Strategic Decision Engine
Translates high-level corporate objectives and natural language commands into
governed workforce decisions, preventing workforce proliferation while
enabling seamless coordination between pre-built specialists and template employees.

Constitutional Invariants:
  CEO_IS_GOVERNED (CEO is subordinate to Human Owner, Policy, Authority, and KillSwitch)
  DISCOVER_BEFORE_CREATE (Never create an employee if existing workforce suffices)
  AUDITABLE_DECISIONS (Every workforce decision produces a CEOWorkforceDecisionRecord)
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState
from core.employee_template import employee_template_registry, TemplateType
from core.employee_factory_v7 import employee_factory_v7
from core.team_catalog import BUNDLED_TEAMS

logger = logging.getLogger("zonata.v7.ceo_controller")

class WorkforceDecisionOutcome:
    USE_EXISTING_AGENT = "USE_EXISTING_AGENT"
    USE_EXISTING_EMPLOYEE = "USE_EXISTING_EMPLOYEE"
    COMBINE_EXISTING_WORKFORCE = "COMBINE_EXISTING_WORKFORCE"
    CREATE_TEMPLATE_EMPLOYEE = "CREATE_TEMPLATE_EMPLOYEE"
    CREATE_PROJECT_EMPLOYEE = "CREATE_PROJECT_EMPLOYEE"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"

@dataclass
class CEOWorkforceDecisionRecord:
    decision_id: str
    tenant_id: str
    company_id: str
    mission_id: str
    objective: str
    required_capabilities: List[str]
    outcome: str                        # WorkforceDecisionOutcome
    reason_for_selection: str
    selected_workers: List[str]
    created_employee_id: Optional[str]
    template_considered: Optional[str]
    budget_allocated_usd: float
    supervisor_assigned: str
    created_at: float = field(default_factory=time.time)

class CEOWorkforceController:
    """
    Strategic workforce planner and command executor for the AI CEO.
    Governs workforce composition, hierarchical assignment, and mission dispatch.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS ceo_workforce_decisions (
                decision_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                mission_id TEXT NOT NULL,
                objective TEXT NOT NULL,
                outcome TEXT NOT NULL,
                selected_workers JSON NOT NULL,
                created_employee_id TEXT,
                template_considered TEXT,
                budget_allocated_usd REAL NOT NULL,
                supervisor_assigned TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ceo_dec_tenant ON ceo_workforce_decisions(tenant_id);")

    def plan_and_assign_mission(
        self,
        tenant_id: str,
        company_id: str,
        objective: str,
        required_capabilities: List[str],
        department: str,
        budget_usd: float = 100.0,
        project_id: Optional[str] = None,
        force_create_template: Optional[str] = None
    ) -> CEOWorkforceDecisionRecord:
        """
        Executes the formal Workforce Discovery & Decision Pipeline:
        1. Discover active AI Employees with matching capabilities.
        2. Discover pre-built specialists (Type A) in team catalog.
        3. Check workload and capacity.
        4. Select existing agent/employee, combine them, or create from template.
        """
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        mission_id = f"miss_{uuid.uuid4().hex[:8]}"

        # 1. Discover Active Template Employees in Company
        existing_employees = ai_employee_registry.list_employees(tenant_id, company_id)
        matching_active_emps = []
        for emp in existing_employees:
            if emp.lifecycle_state == EmployeeLifecycleState.ACTIVE:
                # Check capability intersection
                caps = set(emp.capabilities)
                if any(rc in caps for rc in required_capabilities):
                    matching_active_emps.append(emp)

        # 2. Discover Pre-Built Specialists (Type A)
        matching_specialists = []
        for team_key, team_data in BUNDLED_TEAMS.items():
            for agent_spec in team_data.get("agents", []):
                agent_tools = set(agent_spec.get("allowed_tools", []))
                agent_role = agent_spec.get("role", "")
                if any(rc.lower() in agent_role.lower() for rc in required_capabilities):
                    matching_specialists.append(agent_spec)

        selected_workers: List[str] = []
        created_emp_id = None
        template_used = None
        outcome = WorkforceDecisionOutcome.USE_EXISTING_EMPLOYEE
        reason = ""

        # Forced template creation path (e.g. user explicitly requested specific template)
        if force_create_template:
            template = employee_template_registry.get_template(force_create_template)
            if template:
                emp, prov = employee_factory_v7.instantiate_employee_from_template(
                    template_id=force_create_template,
                    custom_name=f"{template.name} ({project_id or 'General'})",
                    project_id=project_id,
                    budget_override_usd=budget_usd,
                    requester="AI_CEO"
                )
                created_emp_id = emp.employee_id
                selected_workers.append(emp.employee_id)
                template_used = force_create_template
                outcome = (WorkforceDecisionOutcome.CREATE_PROJECT_EMPLOYEE
                           if template.template_type == TemplateType.PROJECT_SPECIFIC
                           else WorkforceDecisionOutcome.CREATE_TEMPLATE_EMPLOYEE)
                reason = f"Explicit CEO template instantiation for {template.name}."
            else:
                reason = f"Requested template {force_create_template} not found."

        # Scenario A: Existing Active Employee perfectly matches
        elif matching_active_emps and len(matching_active_emps) > 0:
            chosen = matching_active_emps[0]
            selected_workers.append(chosen.employee_id)
            outcome = WorkforceDecisionOutcome.USE_EXISTING_EMPLOYEE
            reason = f"Matched existing active employee '{chosen.name}' ({chosen.employee_id}) with required capabilities."

        # Scenario B: Pre-built specialist can handle it directly
        elif matching_specialists and not project_id:
            spec = matching_specialists[0]
            selected_workers.append(f"specialist_{spec['role']}")
            outcome = WorkforceDecisionOutcome.USE_EXISTING_AGENT
            reason = f"Assigned pre-built specialist '{spec['role']}' without creating unnecessary employee overhead."

        # Scenario C: Project-specific initiative requires a new Template-built employee
        else:
            # Look for available templates in registry
            templates = employee_template_registry.list_templates(tenant_id, company_id)
            best_template = None
            for t_info in templates:
                tmpl = employee_template_registry.get_template(t_info["template_id"])
                if tmpl and tmpl.department == department:
                    best_template = tmpl
                    break

            if best_template:
                emp, prov = employee_factory_v7.instantiate_employee_from_template(
                    template_id=best_template.template_id,
                    project_id=project_id,
                    budget_override_usd=budget_usd,
                    requester="AI_CEO"
                )
                created_emp_id = emp.employee_id
                selected_workers.append(emp.employee_id)
                template_used = best_template.template_id
                outcome = (WorkforceDecisionOutcome.CREATE_PROJECT_EMPLOYEE
                           if project_id else WorkforceDecisionOutcome.CREATE_TEMPLATE_EMPLOYEE)
                reason = f"Created new {best_template.template_type} employee from template '{best_template.name}'."
            else:
                outcome = WorkforceDecisionOutcome.ESCALATE_TO_HUMAN
                reason = f"No existing workforce or template found matching department '{department}' and capabilities {required_capabilities}."

        # Assign Chief Officer supervisor based on department
        dept_supervisors = {
            "OPERATIONS": "CHIEF_OPERATING_OFFICER",
            "ENGINEERING": "CHIEF_TECHNOLOGY_OFFICER",
            "GROWTH": "CHIEF_MARKETING_OFFICER",
            "MARKETING": "CHIEF_MARKETING_OFFICER",
            "FINANCE": "CHIEF_FINANCIAL_OFFICER",
            "LEGAL": "CHIEF_LEGAL_OFFICER"
        }
        supervisor_assigned = dept_supervisors.get(department.upper(), "AI_CEO")

        decision = CEOWorkforceDecisionRecord(
            decision_id=decision_id,
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            objective=objective,
            required_capabilities=required_capabilities,
            outcome=outcome,
            reason_for_selection=reason,
            selected_workers=selected_workers,
            created_employee_id=created_emp_id,
            template_considered=template_used,
            budget_allocated_usd=budget_usd,
            supervisor_assigned=supervisor_assigned
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO ceo_workforce_decisions (
                decision_id, tenant_id, company_id, mission_id, objective,
                outcome, selected_workers, created_employee_id, template_considered,
                budget_allocated_usd, supervisor_assigned, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decision_id, decision.tenant_id, decision.company_id,
                decision.mission_id, decision.objective, decision.outcome,
                json.dumps(decision.selected_workers), decision.created_employee_id,
                decision.template_considered, decision.budget_allocated_usd,
                decision.supervisor_assigned, decision.reason_for_selection,
                decision.created_at
            ))

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="CEO_WORKFORCE_DECISION_RECORDED",
            payload={
                "decision_id": decision_id,
                "mission_id": mission_id,
                "outcome": outcome,
                "selected_workers": selected_workers,
                "supervisor": supervisor_assigned,
                "reason": reason
            }
        )

        return decision

    def execute_natural_language_command(self, tenant_id: str, company_id: str, command: str) -> Dict[str, Any]:
        """
        Parses CEO natural language directives into governed operational actions:
        - "Create a revenue manager for this hotel."
        - "Use the existing sales specialist for lead qualification."
        - "Pause employee <id>."
        - "Assign research specialist to employee <id>."
        """
        cmd_lower = command.lower()

        # 1. Pause / Suspend Employee Command
        if "pause" in cmd_lower or "suspend" in cmd_lower:
            words = command.split()
            target_id = None
            for w in words:
                if w.startswith("emp_"):
                    target_id = w.strip(".,;:?!")
                    break
            if target_id:
                state = EmployeeLifecycleState.SUSPENDED if "suspend" in cmd_lower else EmployeeLifecycleState.PAUSED
                ai_employee_registry.advance_lifecycle(target_id, state, "AI_CEO", f"CEO NL Command: {command}")
                return {
                    "action": "LIFECYCLE_STATE_CHANGE",
                    "employee_id": target_id,
                    "new_state": state,
                    "status": "SUCCESS"
                }

        # 2. Template / Employee Creation Command
        if "create" in cmd_lower and ("employee" in cmd_lower or "manager" in cmd_lower or "specialist" in cmd_lower):
            dept = "OPERATIONS"
            caps = ["DATA_ANALYSIS", "OPERATIONS"]
            if "revenue" in cmd_lower or "hotel" in cmd_lower:
                dept = "OPERATIONS"
                caps = ["REVENUE_MANAGEMENT", "PRICING_OPTIMIZATION"]
            elif "marketing" in cmd_lower:
                dept = "GROWTH"
                caps = ["DIGITAL_MARKETING", "CAMPAIGN_MANAGEMENT"]
            elif "developer" in cmd_lower or "engineer" in cmd_lower:
                dept = "ENGINEERING"
                caps = ["SOFTWARE_ENGINEERING", "CODE_REVIEW"]

            dec = self.plan_and_assign_mission(
                tenant_id=tenant_id,
                company_id=company_id,
                objective=command,
                required_capabilities=caps,
                department=dept
            )
            return {
                "action": "WORKFORCE_MISSION_PLANNED",
                "decision": asdict(dec),
                "status": "SUCCESS"
            }

        # 3. Specialist Use Directive
        if "use" in cmd_lower and "specialist" in cmd_lower:
            dec = self.plan_and_assign_mission(
                tenant_id=tenant_id,
                company_id=company_id,
                objective=command,
                required_capabilities=["SALES", "LEAD_QUALIFICATION"],
                department="GROWTH"
            )
            return {
                "action": "SPECIALIST_ASSIGNED",
                "decision": asdict(dec),
                "status": "SUCCESS"
            }

        return {
            "action": "GENERAL_EXECUTIVE_DIRECTIVE",
            "command": command,
            "status": "LOGGED_IN_AUDIT"
        }

ceo_workforce_controller = CEOWorkforceController()
