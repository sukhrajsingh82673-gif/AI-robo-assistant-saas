"""
ZONATA Cross-Department Mission Orchestrator & Delegation DAG Engine
"""
import time
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from core.db import db

class DelegationCycleDetectedError(ValueError):
    """Raised when cyclical dependencies are injected into an employee task DAG."""
    pass

class CorporateMissionOrchestrator:
    """
    Governs strategic cross-functional missions, task delegation DAGs,
    and multi-department SLA collaborations beneath executive sponsors.
    """

    @classmethod
    def validate_delegation_dag(cls, tasks: List[Dict[str, Any]]) -> bool:
        """
        Kahn's Algorithm for Topological Sort & Cycle Detection.
        Strict Invariant: Delegation DAGs must never contain cycles.
        """
        in_degree = {t["task_id"]: 0 for t in tasks}
        adj_list = {t["task_id"]: [] for t in tasks}

        for t in tasks:
            deps = t.get("dependency_task_ids") or []
            if isinstance(deps, str):
                deps = json.loads(deps)
            for dep in deps:
                if dep in adj_list:
                    adj_list[dep].append(t["task_id"])
                    in_degree[t["task_id"]] += 1

        queue = [t_id for t_id, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            curr = queue.pop(0)
            visited_count += 1
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(tasks):
            raise DelegationCycleDetectedError(
                "DELEGATION_CYCLE_DETECTED: Cyclic task dependencies are strictly prohibited under constitutional governance."
            )
        return True

    @classmethod
    def create_mission(
        cls,
        tenant_id: str,
        company_id: str,
        title: str,
        objective_statement: str,
        lead_employee_id: str,
        sponsor_executive_role: str = "EXEC_CEO",
        budget_limit_usd: float = 1000.0,
        priority_level: str = "P1",
        target_delivery_hours: float = 72.0
    ) -> Dict[str, Any]:
        now = time.time()
        mission_id = f"msn_{uuid.uuid4().hex[:12]}"
        target_ts = now + (target_delivery_hours * 3600.0)

        with db.get_connection() as conn:
            conn.execute("""
            INSERT INTO corporate_missions (
                mission_id, tenant_id, company_id, title, objective_statement,
                lead_employee_id, sponsor_executive_role, status, priority_level,
                budget_limit_usd, spent_budget_usd, progress_percentage,
                target_delivery_timestamp, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PLANNING', ?, ?, 0.0, 0.0, ?, ?, ?)
            """, (mission_id, tenant_id, company_id, title, objective_statement,
                  lead_employee_id, sponsor_executive_role, priority_level,
                  budget_limit_usd, target_ts, now, now))
            conn.commit()

        return {
            "mission_id": mission_id,
            "title": title,
            "status": "PLANNING",
            "lead_employee_id": lead_employee_id,
            "budget_limit_usd": budget_limit_usd,
            "created_at": now
        }

    @classmethod
    def append_task(
        cls,
        mission_id: str,
        tenant_id: str,
        company_id: str,
        title: str,
        assigned_employee_id: str,
        delegator_employee_id: str,
        dependency_task_ids: Optional[List[str]] = None,
        risk_level: str = "LOW"
    ) -> Dict[str, Any]:
        now = time.time()
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        deps = dependency_task_ids or []

        with db.get_connection() as conn:
            # Verify mission exists and belongs to tenant/company
            mission = conn.execute(
                "SELECT mission_id FROM corporate_missions WHERE mission_id = ? AND tenant_id = ? AND company_id = ?",
                (mission_id, tenant_id, company_id)
            ).fetchone()
            if not mission:
                raise ValueError(f"Mission '{mission_id}' not found for tenant '{tenant_id}'.")

            # Fetch existing tasks for this mission to validate DAG
            existing = conn.execute(
                "SELECT task_id, dependency_task_ids FROM employee_tasks WHERE mission_id = ? AND tenant_id = ? AND company_id = ?",
                (mission_id, tenant_id, company_id)
            ).fetchall()
            candidate_list = [{"task_id": r["task_id"], "dependency_task_ids": r["dependency_task_ids"]} for r in existing]
            candidate_list.append({"task_id": task_id, "dependency_task_ids": deps})

            # Run Kahn's Cycle Detection
            cls.validate_delegation_dag(candidate_list)

            conn.execute("""
            INSERT INTO employee_tasks (
                task_id, mission_id, tenant_id, company_id, title,
                assigned_employee_id, delegator_employee_id, dependency_task_ids,
                status, risk_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', ?, ?)
            """, (task_id, mission_id, tenant_id, company_id, title,
                  assigned_employee_id, delegator_employee_id, json.dumps(deps),
                  risk_level, now))
            conn.commit()

        return {"task_id": task_id, "mission_id": mission_id, "status": "QUEUED"}

mission_orchestrator = CorporateMissionOrchestrator()
