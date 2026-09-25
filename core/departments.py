"""
RoboAssistant Company OS 1.0 — Organizational Control Units (Departments)
First-class Control Units with dedicated budgets, manager agents, and escalation rules.
"""

from typing import List, Dict, Any, Optional
import time
import uuid
from .db import db

class DepartmentControlUnit:
    @staticmethod
    def create_department(
        tenant_id: str,
        company_id: str,
        name: str,
        manager_agent_id: Optional[str] = None,
        budget_limit: float = 0.0,
        spending_limit: float = 0.0
    ) -> Dict[str, Any]:
        dept_id = f"dept_{uuid.uuid4().hex[:8]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO departments (
                    department_id, company_id, tenant_id, name,
                    manager_agent_id, budget_limit, spending_limit, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (dept_id, company_id, tenant_id, name, manager_agent_id, budget_limit, spending_limit, "ACTIVE", now)
            )
            conn.commit()
        return {
            "department_id": dept_id,
            "company_id": company_id,
            "tenant_id": tenant_id,
            "name": name,
            "manager_agent_id": manager_agent_id,
            "budget_limit": budget_limit,
            "spending_limit": spending_limit,
            "status": "ACTIVE"
        }

    @staticmethod
    def list_departments(tenant_id: str, company_id: str) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM departments WHERE tenant_id = ? AND company_id = ? ORDER BY created_at ASC",
                (tenant_id, company_id)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_department(tenant_id: str, department_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM departments WHERE tenant_id = ? AND department_id = ?",
                (tenant_id, department_id)
            ).fetchone()
            if row:
                return dict(row)
        return None
