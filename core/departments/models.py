"""
Canonical Department Data Models (ZONATA Step 7 Department Platform)
====================================================================
Database entities for the 'departments' schema.
Every table enforces:
- tenant_id (multi-tenant boundary)
- company_id (subsidiary boundary)
- Row-Level Security (RLS) invariants
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class DepartmentEntity(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    name: str
    code: str  # e.g. 'FIN', 'SALES', 'HR', 'OPS', 'SCM', 'RND', 'LEGAL', 'BI'
    lead_principal_id: str
    status: str = Field("active", description="'active', 'suspended', 'archived'")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DepartmentMembership(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    department_id: str
    principal_id: str
    role: str  # e.g. 'department_head', 'lead_agent', 'operator', 'auditor'
    allocated_capacity: float = Field(1.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DepartmentBudget(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    department_id: str
    currency: str = Field("INR", min_length=3, max_length=3)
    total_budget: float = Field(..., ge=0.0)
    spend_committed: float = Field(0.0, ge=0.0)
    spend_actual: float = Field(0.0, ge=0.0)
    valid_from: str
    valid_to: str

    def available_budget(self) -> float:
        return max(0.0, self.total_budget - (self.spend_committed + self.spend_actual))

    def commit_spend(self, amount: float) -> bool:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.available_budget() < amount:
            return False
        self.spend_committed += amount
        return True

    def execute_spend(self, amount: float) -> None:
        if amount > self.spend_committed:
            # Settle what was committed, remainder directly from budget
            diff = amount - self.spend_committed
            if diff > self.available_budget():
                raise ValueError("Spend exceeds available budget")
            self.spend_committed = 0.0
        else:
            self.spend_committed -= amount
        self.spend_actual += amount


class DepartmentPolicy(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    department_id: str
    policy_name: str
    policy_type: str  # e.g. 'gateway_gate', 'budget_limit', 'fairness', 'sanctions'
    rules_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DepartmentEvent(BaseModel):
    id: str
    tenant_id: str
    company_id: str
    department_id: str
    event_type: str
    payload_json: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DepartmentRepository:
    """In-memory or SQL repository for Department Platform entities with RLS."""

    def __init__(self):
        self.departments: Dict[str, DepartmentEntity] = {}
        self.memberships: Dict[str, DepartmentMembership] = {}
        self.budgets: Dict[str, DepartmentBudget] = {}
        self.policies: Dict[str, DepartmentPolicy] = {}
        self.events: List[DepartmentEvent] = []

    def create_department(self, dept: DepartmentEntity) -> DepartmentEntity:
        key = f"{dept.tenant_id}:{dept.company_id}:{dept.id}"
        self.departments[key] = dept
        return dept

    def get_department(self, tenant_id: str, company_id: str, dept_id: str) -> Optional[DepartmentEntity]:
        key = f"{tenant_id}:{company_id}:{dept_id}"
        return self.departments.get(key)

    def list_departments(self, tenant_id: str, company_id: str) -> List[DepartmentEntity]:
        prefix = f"{tenant_id}:{company_id}:"
        return [dept for k, dept in self.departments.items() if k.startswith(prefix)]

    def record_budget(self, budget: DepartmentBudget) -> DepartmentBudget:
        key = f"{budget.tenant_id}:{budget.company_id}:{budget.id}"
        self.budgets[key] = budget
        return budget

    def get_budget(self, tenant_id: str, company_id: str, budget_id: str) -> Optional[DepartmentBudget]:
        key = f"{tenant_id}:{company_id}:{budget_id}"
        return self.budgets.get(key)

    def record_event(self, event: DepartmentEvent) -> DepartmentEvent:
        self.events.append(event)
        return event

    def list_events(self, tenant_id: str, company_id: str, department_id: str) -> List[DepartmentEvent]:
        return [
            e for e in self.events
            if e.tenant_id == tenant_id and e.company_id == company_id and e.department_id == department_id
        ]
