"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Executive Resource & Budget Allocator
Enforces mathematical budget containment across Tenant -> Company -> Department -> Mission -> Employee.

Constitutional Invariants:
  BUDGET_CONTAINMENT (Child allocation <= Parent allocation constraint; no escalation via delegation)
  ZERO_OVERDRAFT (Cannot commit or spend beyond approved ceiling)
  AUDITED_ALLOCATION (All allocations tracked with currency, commitments, and actual expenditures)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class AllocationScope:
    TENANT = "TENANT"
    COMPANY = "COMPANY"
    DEPARTMENT = "DEPARTMENT"
    MISSION = "MISSION"
    EMPLOYEE = "EMPLOYEE"

@dataclass
class ResourceAllocation:
    allocation_id: str
    tenant_id: str
    company_id: str
    scope_type: str
    scope_id: str
    parent_allocation_id: Optional[str]
    budget_limit: float
    committed_spend: float = 0.0
    actual_spend: float = 0.0
    currency: str = "₹"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.budget_limit - self.actual_spend)

    @property
    def available_to_commit(self) -> float:
        return max(0.0, self.budget_limit - self.committed_spend)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["remaining_budget"] = self.remaining_budget
        d["available_to_commit"] = self.available_to_commit
        return d

class BudgetContainmentViolation(Exception):
    """Raised when child resource allocation exceeds parent budget ceiling."""
    pass

class ExecutiveResourceAllocator:
    """
    Governs hierarchical budget allocation, spending tracking, and containment verification.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def allocate_budget(
        self,
        scope_type: str,
        scope_id: str,
        requested_budget: float,
        parent_allocation_id: Optional[str] = None,
        currency: str = "₹"
    ) -> ResourceAllocation:
        """
        Allocates budget adhering to strict parent containment.
        If parent_allocation_id is supplied, verifies requested_budget <= parent.available_to_commit.
        """
        now = time.time()

        if parent_allocation_id:
            parent = self.get_allocation_by_id(parent_allocation_id)
            if not parent:
                raise BudgetContainmentViolation(f"Parent allocation {parent_allocation_id} not found.")

            # Calculate already allocated child sum
            with db.get_connection() as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(budget_limit), 0.0) FROM executive_resource_allocations WHERE parent_allocation_id = ? AND allocation_id != ?",
                    (parent_allocation_id, f"alloc_{self.tenant_id}_{scope_id}")
                ).fetchone()
                existing_children_budget = row[0]

            if existing_children_budget + requested_budget > parent.budget_limit:
                raise BudgetContainmentViolation(
                    f"Child budget allocation violation: Requested ₹{requested_budget} + existing siblings ₹{existing_children_budget} "
                    f"exceeds parent allocation limit ₹{parent.budget_limit} (Scope: {parent.scope_type}:{parent.scope_id})"
                )

        allocation_id = f"alloc_{self.tenant_id}_{scope_type.lower()}_{scope_id}"

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO executive_resource_allocations (
                    allocation_id, tenant_id, company_id, scope_type, scope_id,
                    parent_allocation_id, budget_limit, committed_spend, actual_spend,
                    currency, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?, ?)
                ON CONFLICT(allocation_id) DO UPDATE SET
                    budget_limit=excluded.budget_limit,
                    parent_allocation_id=excluded.parent_allocation_id,
                    updated_at=excluded.updated_at
            """, (
                allocation_id, self.tenant_id, self.company_id, scope_type, scope_id,
                parent_allocation_id, requested_budget, currency, now, now
            ))
            conn.commit()

        create_executive_event(
            event_type="BudgetThresholdReached" if requested_budget > 100000 else "ResourceAllocated",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            payload={
                "allocation_id": allocation_id,
                "scope_type": scope_type,
                "scope_id": scope_id,
                "budget_limit": requested_budget,
                "currency": currency
            }
        )

        return self.get_allocation_by_id(allocation_id)

    def record_expenditure(self, allocation_id: str, amount: float, is_commitment: bool = False):
        """Records spending or commitment against an allocation."""
        alloc = self.get_allocation_by_id(allocation_id)
        if not alloc:
            raise ValueError(f"Allocation {allocation_id} not found.")

        now = time.time()
        with db.get_connection() as conn:
            if is_commitment:
                if alloc.committed_spend + amount > alloc.budget_limit:
                    raise BudgetContainmentViolation(f"Commitment ₹{amount} exceeds remaining limit ₹{alloc.available_to_commit}")
                conn.execute("""
                    UPDATE executive_resource_allocations
                    SET committed_spend = committed_spend + ?, updated_at = ?
                    WHERE allocation_id = ?
                """, (amount, now, allocation_id))
            else:
                if alloc.actual_spend + amount > alloc.budget_limit:
                    raise BudgetContainmentViolation(f"Spend ₹{amount} exceeds budget limit ₹{alloc.remaining_budget}")
                conn.execute("""
                    UPDATE executive_resource_allocations
                    SET actual_spend = actual_spend + ?, updated_at = ?
                    WHERE allocation_id = ?
                """, (amount, now, allocation_id))
            conn.commit()

    def get_allocation_by_id(self, allocation_id: str) -> Optional[ResourceAllocation]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM executive_resource_allocations WHERE allocation_id = ? AND tenant_id = ? AND company_id = ?",
                (allocation_id, self.tenant_id, self.company_id)
            ).fetchone()
            if not r:
                return None
            return ResourceAllocation(
                allocation_id=r["allocation_id"],
                tenant_id=r["tenant_id"],
                company_id=r["company_id"],
                scope_type=r["scope_type"],
                scope_id=r["scope_id"],
                parent_allocation_id=r["parent_allocation_id"],
                budget_limit=r["budget_limit"],
                committed_spend=r["committed_spend"],
                actual_spend=r["actual_spend"],
                currency=r["currency"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )

    def list_allocations(self) -> List[ResourceAllocation]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM executive_resource_allocations WHERE tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                (self.tenant_id, self.company_id)
            ).fetchall()
            return [
                ResourceAllocation(
                    allocation_id=r["allocation_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    scope_type=r["scope_type"],
                    scope_id=r["scope_id"],
                    parent_allocation_id=r["parent_allocation_id"],
                    budget_limit=r["budget_limit"],
                    committed_spend=r["committed_spend"],
                    actual_spend=r["actual_spend"],
                    currency=r["currency"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ) for r in rows
            ]
