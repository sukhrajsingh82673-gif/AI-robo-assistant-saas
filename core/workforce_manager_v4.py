"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 4 — AI Employee Workforce Manager & Mission Orchestration Plane
Implements EmployeeManager, WorkforceManager, MissionManager, and SupervisorManager.

Enforces Formal Delegation Invariants:
  CHILD_AUTHORITY ⊆ PARENT_AUTHORITY
  CHILD_DATA_SCOPE ⊆ PARENT_DATA_SCOPE
  CHILD_TOOL_SCOPE ⊆ PARENT_TOOL_SCOPE
  DELEGATED_BUDGET <= PARENT_REMAINING_BUDGET
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from core.database_engine import engine, WorkloadType
from core.ai_employee_os import ai_employee_registry, AIEmployee, EmployeeLifecycleState, AuthorityScope

logger = logging.getLogger("zonata.workforce.manager.v4")

RISK_LEVELS = {
    "READ_ONLY": 1,
    "LOW_RISK": 2,
    "MUTATING": 3,
    "FINANCIAL": 4,
    "DESTRUCTIVE": 5
}

class DelegationViolationError(PermissionError):
    """Raised when delegation exceeds parent authority, budget, tool, or data scope."""
    pass

class WorkforceManagerV4:
    """
    Enterprise Workforce Manager governing AI Employees, mission delegation, and hierarchy containment.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS workforce_missions (
                mission_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                assigned_employee_id TEXT NOT NULL,
                supervisor_id TEXT,
                status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, PAUSED, COMPLETED, FAILED, ESCALATED
                budget_usd REAL NOT NULL,
                spent_usd REAL NOT NULL DEFAULT 0.0,
                target_outcome JSON NOT NULL,
                actual_outcome JSON,
                created_at REAL NOT NULL,
                completed_at REAL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_wf_miss_emp ON workforce_missions(assigned_employee_id);")

    # -------------------------------------------------------------
    # 1. Governed Delegation (CHILD ⊆ PARENT)
    # -------------------------------------------------------------
    def delegate_to_child(
        self,
        parent_employee_id: str,
        child_name: str,
        child_role_tier: str,
        child_template_id: str,
        requested_capabilities: List[str],
        requested_tools: List[str],
        requested_data_domains: List[str],
        requested_authority: AuthorityScope,
        delegated_budget_usd: float,
        mission_id: Optional[str] = None
    ) -> AIEmployee:
        """
        Formally spawn and delegate authority to a child AI worker.
        Enforces strict mathematical subset containment of authority, tools, data, and budget.
        """
        parent = ai_employee_registry.get_employee(parent_employee_id)
        if not parent:
            raise ValueError(f"Parent employee '{parent_employee_id}' does not exist.")

        if not parent.is_operational():
            raise PermissionError(f"Parent employee '{parent_employee_id}' is not ACTIVE (state: {parent.lifecycle_state}).")

        if not parent.authority.can_delegate:
            raise DelegationViolationError(f"Parent '{parent_employee_id}' does not possess delegation authority ('can_delegate=False').")

        # 1. Budget Containment: DELEGATED_BUDGET <= PARENT_REMAINING_BUDGET
        if delegated_budget_usd > parent.remaining_budget():
            raise DelegationViolationError(
                f"Delegated budget (${delegated_budget_usd:.2f}) exceeds parent remaining budget (${parent.remaining_budget():.2f})."
            )

        # 2. Risk Ceiling Containment: CHILD_RISK <= PARENT_RISK
        parent_risk_score = RISK_LEVELS.get(parent.authority.max_risk_class, 1)
        child_risk_score = RISK_LEVELS.get(requested_authority.max_risk_class, 1)
        if child_risk_score > parent_risk_score:
            raise DelegationViolationError(
                f"Child requested risk level '{requested_authority.max_risk_class}' exceeds parent ceiling '{parent.authority.max_risk_class}'."
            )

        # 3. Financial Ceiling: CHILD_MAX_SPEND <= PARENT_MAX_SPEND
        if requested_authority.max_single_spend_usd > parent.authority.max_single_spend_usd:
            raise DelegationViolationError(
                f"Child single spend limit (${requested_authority.max_single_spend_usd:.2f}) exceeds parent (${parent.authority.max_single_spend_usd:.2f})."
            )

        # 4. Tool Scope Containment: CHILD_TOOL_SCOPE ⊆ PARENT_TOOL_SCOPE
        parent_tools = set(parent.allowed_tools)
        unauthorized_tools = set(requested_tools) - parent_tools
        if unauthorized_tools:
            raise DelegationViolationError(
                f"Child requested tools not available to parent: {list(unauthorized_tools)}"
            )

        # 5. Data Scope Containment: CHILD_DATA_SCOPE ⊆ PARENT_DATA_SCOPE
        parent_data = set(parent.allowed_data_domains)
        unauthorized_data = set(requested_data_domains) - parent_data
        if unauthorized_data:
            raise DelegationViolationError(
                f"Child requested data domains not available to parent: {list(unauthorized_data)}"
            )

        # Deduct budget from parent
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE ai_employees
            SET spent_budget_usd = spent_budget_usd + ?, updated_at = ?
            WHERE employee_id = ?
            """, (delegated_budget_usd, now, parent_employee_id))

        # Propose and immediately approve child under parent supervision
        child = ai_employee_registry.propose_employee(
            tenant_id=parent.tenant_id,
            company_id=parent.company_id,
            name=child_name,
            role_tier=child_role_tier,
            template_id=child_template_id,
            version=parent.version,
            department_id=parent.department_id,
            team_id=parent.team_id,
            supervisor_id=parent.employee_id,
            capabilities=requested_capabilities,
            allowed_tools=requested_tools,
            allowed_data_domains=requested_data_domains,
            authority=requested_authority,
            initial_budget_usd=delegated_budget_usd,
            metadata={"delegated_by": parent.employee_id, "parent_mission_id": mission_id}
        )

        # Fast-track child to ACTIVE through evaluated -> approved -> onboarded -> active
        ai_employee_registry.advance_lifecycle(child.employee_id, EmployeeLifecycleState.EVALUATED, approver_id=parent.employee_id)
        ai_employee_registry.advance_lifecycle(child.employee_id, EmployeeLifecycleState.APPROVED, approver_id=parent.employee_id)
        ai_employee_registry.advance_lifecycle(child.employee_id, EmployeeLifecycleState.PROVISIONED, approver_id=parent.employee_id)
        ai_employee_registry.advance_lifecycle(child.employee_id, EmployeeLifecycleState.ONBOARDED, approver_id=parent.employee_id)
        ai_employee_registry.advance_lifecycle(child.employee_id, EmployeeLifecycleState.ACTIVE, approver_id=parent.employee_id)

        logger.info(f"Successfully delegated work from parent {parent.employee_id} to child {child.employee_id}")
        return ai_employee_registry.get_employee(child.employee_id)

    # -------------------------------------------------------------
    # 2. Mission Management
    # -------------------------------------------------------------
    def create_mission(
        self,
        tenant_id: str,
        company_id: str,
        title: str,
        assigned_employee_id: str,
        budget_usd: float,
        target_outcome: Dict[str, Any],
        supervisor_id: Optional[str] = None
    ) -> str:
        emp = ai_employee_registry.get_employee(assigned_employee_id)
        if not emp or not emp.is_operational():
            raise PermissionError(f"Cannot assign mission to non-active employee: {assigned_employee_id}")

        if budget_usd > emp.remaining_budget():
            raise DelegationViolationError(f"Mission budget (${budget_usd:.2f}) exceeds employee remaining budget (${emp.remaining_budget():.2f}).")

        mission_id = f"msn_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO workforce_missions (
                mission_id, tenant_id, company_id, title, assigned_employee_id,
                supervisor_id, status, budget_usd, spent_usd, target_outcome, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 0.0, ?, ?)
            """, (mission_id, tenant_id, company_id, title, assigned_employee_id, supervisor_id or emp.supervisor_id, budget_usd, json.dumps(target_outcome), now))
        logger.info(f"Created mission {mission_id} assigned to employee {assigned_employee_id}")
        return mission_id

    def suspend_employee(self, employee_id: str, reason: str = "Administrative hold") -> bool:
        """Suspend an employee and pause their active missions."""
        now = time.time()
        ai_employee_registry.advance_lifecycle(employee_id, EmployeeLifecycleState.SUSPENDED, reason=reason)
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE workforce_missions
            SET status = 'PAUSED'
            WHERE assigned_employee_id = ? AND status = 'ACTIVE'
            """, (employee_id,))
        logger.warning(f"Employee {employee_id} suspended. Reason: {reason}")
        return True

    def resume_employee(self, employee_id: str) -> bool:
        """Resume a suspended employee and unpause their active missions."""
        ai_employee_registry.advance_lifecycle(employee_id, EmployeeLifecycleState.ACTIVE)
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE workforce_missions
            SET status = 'ACTIVE'
            WHERE assigned_employee_id = ? AND status = 'PAUSED'
            """, (employee_id,))
        logger.info(f"Employee {employee_id} resumed active status.")
        return True

# Global singleton
workforce_manager_v4 = WorkforceManagerV4()
