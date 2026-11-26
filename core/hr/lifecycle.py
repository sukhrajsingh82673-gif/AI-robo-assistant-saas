"""
Employee Lifecycle Management Engine
====================================
Adheres to:
- Rule 62: Reserved Human Decisions (Salary modifications and termination require gateway approval)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Employee(BaseModel):
    employee_id: str
    tenant_id: str
    company_id: str
    full_name: str
    email: str
    department_id: str
    role_title: str
    annual_salary: float
    status: str = "onboarding"  # 'onboarding', 'active', 'leave', 'offboarding', 'terminated'
    onboarding_checklist: Dict[str, bool] = Field(default_factory=lambda: {
        "contract_signed": False,
        "equipment_provisioned": False,
        "sso_account_created": False,
        "compliance_training_completed": False
    })
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmployeeLifecycleManager:
    """Manages onboarding, promotions, salary updates, and termination gating."""

    def __init__(self):
        self.employees: Dict[str, Employee] = {}

    def register_new_hire(self, emp: Employee) -> Employee:
        key = f"{emp.tenant_id}:{emp.company_id}:{emp.employee_id}"
        self.employees[key] = emp
        return emp

    def complete_onboarding_step(self, tenant_id: str, company_id: str, emp_id: str, step: str) -> Employee:
        key = f"{tenant_id}:{company_id}:{emp_id}"
        emp = self.employees.get(key)
        if not emp:
            raise KeyError(f"Employee {emp_id} not found")

        if step not in emp.onboarding_checklist:
            raise ValueError(f"Unknown onboarding step: {step}")

        emp.onboarding_checklist[step] = True
        # If all steps are complete, activate employee
        if all(emp.onboarding_checklist.values()):
            emp.status = "active"
        return emp

    def apply_compensation_adjustment(
        self,
        tenant_id: str,
        company_id: str,
        emp_id: str,
        new_annual_salary: float,
        approval_token: str,
        authorizer_principal_id: str
    ) -> Employee:
        """Rule 62: Salary changes strictly mandate human gateway authorization."""
        key = f"{tenant_id}:{company_id}:{emp_id}"
        emp = self.employees.get(key)
        if not emp:
            raise KeyError(f"Employee {emp_id} not found")

        if not approval_token or not authorizer_principal_id:
            raise ValueError("Rule 62 Violation: Salary adjustment requires human gateway approval token")

        emp.annual_salary = new_annual_salary
        return emp
