"""
RoboAssistant Company OS 1.0 — Hierarchical Financial Controls & Budget Engine
Enforces multi-tier spending caps:
Platform -> Company -> Department -> Employee -> Mission
Lower-tier allocations can never exceed parent budget limits.
"""

from typing import Dict, Any, List, Optional
import time

class BudgetHierarchyEngine:
    @staticmethod
    def validate_allocation(
        company_budget: float,
        dept_budget: float,
        employee_budget: float,
        mission_budget: float
    ) -> Dict[str, Any]:
        """
        Validates the strict hierarchy:
        Company >= Dept >= Employee >= Mission.
        """
        if dept_budget > company_budget:
            return {
                "valid": False,
                "error": f"BUDGET_CEILING_VIOLATION: Department budget (₹{dept_budget}) exceeds company budget (₹{company_budget})."
            }
        if employee_budget > dept_budget:
            return {
                "valid": False,
                "error": f"BUDGET_CEILING_VIOLATION: Employee budget (₹{employee_budget}) exceeds department budget (₹{dept_budget})."
            }
        if mission_budget > employee_budget:
            return {
                "valid": False,
                "error": f"BUDGET_CEILING_VIOLATION: Mission budget (₹{mission_budget}) exceeds employee allocation (₹{employee_budget})."
            }
        return {"valid": True, "error": None}

    @staticmethod
    def check_spend_threshold(incurred: float, budget_limit: float) -> Dict[str, Any]:
        """Calculates consumption percentage and triggers graduated alerts."""
        if budget_limit <= 0:
            return {"percentage": 0.0, "alert_level": "NONE", "can_proceed": True, "message": "No budget limit configured."}

        pct = (incurred / budget_limit) * 100.0
        if pct >= 100.0:
            return {
                "percentage": pct,
                "alert_level": "CRITICAL_HALT",
                "can_proceed": False,
                "message": f"CRITICAL HALT: Budget exceeded at {pct:.1f}% consumption. Non-critical tasks stopped."
            }
        elif pct >= 90.0:
            return {
                "percentage": pct,
                "alert_level": "HIGH_WARNING",
                "can_proceed": True,
                "message": f"HIGH WARNING: Spend has reached {pct:.1f}% of allocated ceiling."
            }
        elif pct >= 80.0:
            return {
                "percentage": pct,
                "alert_level": "WARNING",
                "can_proceed": True,
                "message": f"WARNING: Spend has reached {pct:.1f}% of allocated ceiling."
            }
        elif pct >= 70.0:
            return {
                "percentage": pct,
                "alert_level": "NOTICE",
                "can_proceed": True,
                "message": f"NOTICE: Spend has reached {pct:.1f}% of allocated ceiling."
            }
        return {
            "percentage": pct,
            "alert_level": "NORMAL",
            "can_proceed": True,
            "message": f"NORMAL: Spend is within safe limits ({pct:.1f}%)."
        }
