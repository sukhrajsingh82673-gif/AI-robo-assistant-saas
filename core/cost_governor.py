"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Enterprise Cost & Budget Governor
Tracks expenditures across Tenant, Company, Department, Employee, Mission, Model, Tool.
Enforces soft warnings, hard ceilings, and emergency spend stops.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from .db import db

logger = logging.getLogger("zonata.cost")

class BudgetExhaustedException(Exception):
    """Raised when an operation would exceed hard budget ceiling."""
    pass

class CostGovernor:
    """
    Guarantees that autonomous operations halt before financial damage occurs.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._ensure_table()

    def _ensure_table(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_budget_allocations (
                budget_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                scope_type TEXT NOT NULL, -- TENANT, COMPANY, DEPT, EMPLOYEE, MISSION
                scope_id TEXT NOT NULL,
                allocated_budget_inr REAL NOT NULL,
                spent_inr REAL NOT NULL DEFAULT 0.0,
                soft_limit_pct REAL NOT NULL DEFAULT 0.8,
                hard_limit_inr REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, WARNING, EXHAUSTED, FROZEN
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
            """)
            conn.commit()

    def set_budget(
        self,
        company_id: str,
        scope_type: str,
        scope_id: str,
        allocated_inr: float,
        hard_limit_inr: Optional[float] = None
    ) -> str:
        budget_id = f"bgt_{scope_type.lower()}_{scope_id[:8]}"
        hard_limit = hard_limit_inr if hard_limit_inr is not None else allocated_inr
        now = time.time()

        with db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO enterprise_budget_allocations (
                    budget_id, tenant_id, company_id, scope_type, scope_id,
                    allocated_budget_inr, spent_inr, soft_limit_pct,
                    hard_limit_inr, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.8, ?, 'ACTIVE', ?, ?)
            """, (budget_id, self.tenant_id, company_id, scope_type, scope_id, allocated_inr, hard_limit, now, now))
            conn.commit()

        return budget_id

    def record_expenditure_and_check(
        self,
        company_id: str,
        scope_type: str,
        scope_id: str,
        cost_inr: float
    ) -> Dict[str, Any]:
        """
        Records cost and evaluates thresholds.
        Raises BudgetExhaustedException if hard limit would be breached.
        """
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM enterprise_budget_allocations
                WHERE tenant_id = ? AND company_id = ? AND scope_type = ? AND scope_id = ?
            """, (self.tenant_id, company_id, scope_type, scope_id)).fetchone()

            if not row:
                # Default auto-created scope with baseline ₹50,000 ceiling
                self.set_budget(company_id, scope_type, scope_id, 50000.0, 50000.0)
                spent = 0.0
                hard_limit = 50000.0
                soft_pct = 0.8
            else:
                spent = row["spent_inr"]
                hard_limit = row["hard_limit_inr"]
                soft_pct = row["soft_limit_pct"]

            new_spent = spent + cost_inr

            # Check Hard Ceiling
            if new_spent > hard_limit:
                conn.execute("""
                    UPDATE enterprise_budget_allocations
                    SET status = 'EXHAUSTED', updated_at = ?
                    WHERE tenant_id = ? AND company_id = ? AND scope_type = ? AND scope_id = ?
                """, (now, self.tenant_id, company_id, scope_type, scope_id))
                conn.commit()
                raise BudgetExhaustedException(
                    f"Hard budget limit of ₹{hard_limit:,.2f} exceeded for {scope_type}:{scope_id}. Requested spend ₹{cost_inr:,.2f} would bring total to ₹{new_spent:,.2f}."
                )

            # Check Soft Limit
            is_warning = new_spent >= (hard_limit * soft_pct)
            new_status = 'WARNING' if is_warning else 'ACTIVE'

            conn.execute("""
                UPDATE enterprise_budget_allocations
                SET spent_inr = ?, status = ?, updated_at = ?
                WHERE tenant_id = ? AND company_id = ? AND scope_type = ? AND scope_id = ?
            """, (new_spent, new_status, now, self.tenant_id, company_id, scope_type, scope_id))
            conn.commit()

            return {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "cost_incurred_inr": cost_inr,
                "total_spent_inr": new_spent,
                "hard_limit_inr": hard_limit,
                "status": new_status,
                "soft_limit_breached": is_warning
            }
