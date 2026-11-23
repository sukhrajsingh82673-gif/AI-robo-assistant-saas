"""
ZONATA Task Dependency DAG Engine
Validates acyclic dependencies using Kahn's algorithm and verifies prerequisite task completion.
"""

from __future__ import annotations

import collections
from typing import List, Dict, Set, Tuple, Optional
from core.db import db
from core.work.types import (
    TaskStatus,
    TaskDependencyCycleError,
    PrerequisiteNotCompletedError,
)


class TaskDAGService:
    """
    Manages dependency graphs and cycle detection for work tasks.
    Enforces strict DAG topology (no circular delegations).
    """

    @classmethod
    def validate_no_cycles(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        new_dependency_ids: List[str],
    ) -> None:
        """
        Validates that adding new_dependency_ids to task_id will not create a circular dependency.
        Raises TaskDependencyCycleError if a cycle would be created.
        """
        if not new_dependency_ids:
            return

        if task_id in new_dependency_ids:
            raise TaskDependencyCycleError(
                f"CYCLIC_DEPENDENCY_DETECTED: Task '{task_id}' cannot depend on itself."
            )

        with db.get_connection() as conn:
            # Fetch all existing dependency pairs for this company
            rows = conn.execute(
                "SELECT task_id, depends_on_task_id FROM task_dependencies WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id)
            ).fetchall()

        # Build adjacency list: edge from dependency -> dependent task
        # That is: depends_on -> task (depends_on must finish before task can start)
        adj: Dict[str, List[str]] = collections.defaultdict(list)
        all_nodes: Set[str] = {task_id}

        for r in rows:
            t = r["task_id"]
            d = r["depends_on_task_id"]
            adj[d].append(t)
            all_nodes.add(t)
            all_nodes.add(d)

        for dep_id in new_dependency_ids:
            adj[dep_id].append(task_id)
            all_nodes.add(dep_id)

        # Kahn's Algorithm on all_nodes
        in_degree: Dict[str, int] = {node: 0 for node in all_nodes}
        for u in all_nodes:
            for v in adj.get(u, []):
                in_degree[v] = in_degree.get(v, 0) + 1

        queue = collections.deque([node for node, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj.get(curr, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(all_nodes):
            raise TaskDependencyCycleError(
                f"CYCLIC_DEPENDENCY_DETECTED: Adding dependencies {new_dependency_ids} to task '{task_id}' creates a cycle. "
                "Task dependencies must form a strict Directed Acyclic Graph (DAG)."
            )

    @classmethod
    def check_prerequisites_completed(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
    ) -> Tuple[bool, List[str]]:
        """
        Checks whether all tasks on which task_id depends have reached COMPLETED status.
        Returns (is_satisfied, list_of_uncompleted_task_ids).
        """
        with db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT td.depends_on_task_id, wt.status, wt.title
                FROM task_dependencies td
                JOIN work_tasks wt ON wt.id = td.depends_on_task_id AND wt.tenant_id = td.tenant_id AND wt.company_id = td.company_id
                WHERE td.task_id = ? AND td.tenant_id = ? AND td.company_id = ?
                """,
                (task_id, tenant_id, company_id)
            ).fetchall()

        uncompleted = [r["depends_on_task_id"] for r in rows if r["status"] != TaskStatus.COMPLETED.value]
        return (len(uncompleted) == 0, uncompleted)
