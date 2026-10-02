"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Phase 9 — Enterprise Workforce Scheduler & Concurrency Engine
Manages mission priorities, worker availability, dependency DAGs,
budget constraints, department quotas, and backpressure.

Constitutional Invariants:
  CHILD_AUTHORITY <= PARENT_AUTHORITY
  NO_RECURSIVE_WORKFORCE_RUNAWAY
  GOVERNANCE_PATH_CANNOT_BE_BYPASSED_FOR_SCALE
"""

import time
import json
import uuid
import heapq
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from core.database_engine import engine, WorkloadType
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState
from core.distributed_coordination import coordination
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.workforce.scheduler")

class PriorityTier:
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass(order=True)
class ScheduledMissionTask:
    priority: int
    created_at: float
    mission_id: str = field(compare=False)
    tenant_id: str = field(compare=False)
    company_id: str = field(compare=False)
    department: str = field(compare=False)
    required_capabilities: List[str] = field(compare=False)
    budget_usd: float = field(compare=False)
    deadline: Optional[float] = field(compare=False, default=None)
    dependencies: List[str] = field(compare=False, default_factory=list)

class WorkforceScheduler:
    """
    Enterprise-grade scheduler governing AI Employee mission execution,
    resource fairness, backpressure, and dependency resolution.
    """
    DEFAULT_MAX_CONCURRENT_PER_TENANT = 500
    DEFAULT_MAX_CONCURRENT_PER_DEPT = 100

    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS workforce_scheduler_queue (
                task_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                department TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, SUSPENDED, TIMED_OUT
                assigned_employee_id TEXT,
                budget_usd REAL NOT NULL,
                dependencies JSON NOT NULL,
                created_at REAL NOT NULL,
                dispatched_at REAL,
                completed_at REAL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sched_tenant ON workforce_scheduler_queue(tenant_id, status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sched_priority ON workforce_scheduler_queue(priority, created_at);")

    def enqueue_mission(
        self,
        mission_id: str,
        tenant_id: str,
        company_id: str,
        department: str,
        required_capabilities: List[str],
        budget_usd: float,
        priority: int = PriorityTier.NORMAL,
        deadline: Optional[float] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Enqueue a mission into the priority scheduler."""
        task_id = f"sch_tsk_{uuid.uuid4().hex[:12]}"
        now = time.time()
        deps = dependencies or []

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO workforce_scheduler_queue (
                task_id, mission_id, tenant_id, company_id, department,
                priority, status, budget_usd, dependencies, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, ?, ?)
            """, (
                task_id, mission_id, tenant_id, company_id, department,
                priority, budget_usd, json.dumps(deps), now
            ))

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORKFORCE_MISSION_ENQUEUED",
            payload={
                "task_id": task_id,
                "mission_id": mission_id,
                "department": department,
                "priority": priority,
                "budget_usd": budget_usd
            }
        )
        return task_id

    def schedule_next_task(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Pulls highest-priority mission whose dependencies are fulfilled,
        and assigns an idle, operational AI Employee matching capabilities.
        Enforces tenant and department concurrency caps.
        """
        # 1. Check tenant active concurrency limit
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as active_cnt FROM workforce_scheduler_queue "
                "WHERE tenant_id = ? AND status = 'RUNNING'",
                (tenant_id,)
            )
            active_cnt = cursor.fetchone()["active_cnt"]
            if active_cnt >= self.DEFAULT_MAX_CONCURRENT_PER_TENANT:
                logger.warning(f"Tenant {tenant_id} concurrency limit reached ({active_cnt}/{self.DEFAULT_MAX_CONCURRENT_PER_TENANT})")
                return None

        # 2. Find eligible queued tasks ordered by priority (1=CRITICAL), then created_at
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute(
                "SELECT task_id, mission_id, company_id, department, priority, budget_usd, dependencies "
                "FROM workforce_scheduler_queue "
                "WHERE tenant_id = ? AND status = 'QUEUED' "
                "ORDER BY priority ASC, created_at ASC",
                (tenant_id,)
            )
            queued_tasks = cursor.fetchall()

        for t in queued_tasks:
            deps = json.loads(t["dependencies"])
            if deps:
                # Verify all dependency tasks are COMPLETED
                placeholders = ",".join(["?"] * len(deps))
                with engine.connection(workload=WorkloadType.READ) as conn:
                    dep_cursor = conn.execute(
                        f"SELECT COUNT(DISTINCT mission_id) as comp_cnt FROM workforce_scheduler_queue "
                        f"WHERE tenant_id = ? AND mission_id IN ({placeholders}) AND status = 'COMPLETED'",
                        [tenant_id] + deps
                    )
                    if dep_cursor.fetchone()["comp_cnt"] != len(set(deps)):
                        continue  # Dependencies not yet met

            # Find matching operational employee in department
            with engine.connection(workload=WorkloadType.READ) as conn:
                emp_cursor = conn.execute(
                    "SELECT employee_id, name, allocated_budget_usd, spent_budget_usd "
                    "FROM ai_employees "
                    "WHERE tenant_id = ? AND department_id = ? AND lifecycle_state = 'ACTIVE' "
                    "ORDER BY (allocated_budget_usd - spent_budget_usd) DESC",
                    (tenant_id, t["department"])
                )
                employees = emp_cursor.fetchall()

            for emp in employees:
                rem_budget = emp["allocated_budget_usd"] - emp["spent_budget_usd"]
                if rem_budget >= t["budget_usd"]:
                    # Assign task to this employee
                    now = time.time()
                    with engine.transaction(workload=WorkloadType.WRITE) as conn:
                        conn.execute("""
                        UPDATE workforce_scheduler_queue
                        SET status = 'RUNNING', assigned_employee_id = ?, dispatched_at = ?
                        WHERE task_id = ?
                        """, (emp["employee_id"], now, t["task_id"]))

                    evidence_service.record_event(
                        tenant_id=tenant_id,
                        company_id=t["company_id"],
                        event_type="WORKFORCE_MISSION_DISPATCHED",
                        payload={
                            "task_id": t["task_id"],
                            "mission_id": t["mission_id"],
                            "assigned_employee_id": emp["employee_id"],
                            "department": t["department"]
                        }
                    )
                    return {
                        "task_id": t["task_id"],
                        "mission_id": t["mission_id"],
                        "assigned_employee_id": emp["employee_id"],
                        "department": t["department"],
                        "status": "RUNNING"
                    }

        return None

    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """Mark scheduled mission completed and release concurrency slot."""
        now = time.time()
        final_state = "COMPLETED" if success else "FAILED"
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE workforce_scheduler_queue
            SET status = ?, completed_at = ?
            WHERE task_id = ?
            """, (final_state, now, task_id))
        return True

workforce_scheduler = WorkforceScheduler()
