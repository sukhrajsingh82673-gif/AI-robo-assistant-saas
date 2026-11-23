"""
ZONATA Workforce Work Service
Authoritative work kernel governing Missions, Projects, Work Tasks,
DAG dependencies, deterministic assignment, human inbox, and verification handoff.
"""

from __future__ import annotations

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.db import db, tenant_scoped_class
from core.ports.base import capability_truth_table
from core.evidence_service import evidence_service
from core.work.types import (
    TaskStatus,
    TaskPriority,
    AssigneeType,
    TaskCreateRequest,
    MissionCreateRequest,
    ProjectCreateRequest,
    TaskNotFoundError,
    MissionNotFoundError,
    ProjectNotFoundError,
    PrerequisiteNotCompletedError,
    CapabilityNotLiveBlockedError,
)
from core.work.state_machine import TaskStateMachine
from core.work.dag import TaskDAGService
from core.work.assignment import TaskAssignmentEngine
from core.work.sla import ClockManager

logger = logging.getLogger("zonata.work.service")


@tenant_scoped_class
class WorkforceWorkService:
    """
    Authoritative service orchestrating the multi-tenant work kernel.
    """

    # =========================================================================
    # MISSIONS & PROJECTS
    # =========================================================================

    @classmethod
    def create_mission(
        cls,
        tenant_id: str,
        company_id: str,
        request: MissionCreateRequest,
    ) -> Dict[str, Any]:
        """Creates a strategic mission."""
        mission_id = f"msn_{uuid.uuid4().hex[:12]}"
        now = ClockManager.now()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO work_missions (
                    id, tenant_id, company_id, title, objective, lead_position_id,
                    sponsor_position_id, status, priority, budget_micro_units,
                    spent_micro_units, target_deadline_ts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PLANNING', ?, ?, 0, ?, ?, ?)
                """,
                (
                    mission_id, tenant_id, company_id, request.title, request.objective,
                    request.lead_position_id, request.sponsor_position_id,
                    request.priority.value if hasattr(request.priority, "value") else str(request.priority),
                    request.budget_micro_units, request.target_deadline_ts, now, now
                )
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORK_MISSION_CREATED",
            payload={"mission_id": mission_id, "title": request.title, "budget": request.budget_micro_units},
            action_id=f"create_mission_{mission_id}"
        )

        return cls.get_mission(tenant_id, company_id, mission_id)

    @classmethod
    def get_mission(cls, tenant_id: str, company_id: str, mission_id: str) -> Dict[str, Any]:
        """Fetches a mission by ID."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM work_missions WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (mission_id, tenant_id, company_id)
            ).fetchone()
        if not row:
            raise MissionNotFoundError(f"Mission '{mission_id}' not found.")
        return dict(row)

    @classmethod
    def create_project(
        cls,
        tenant_id: str,
        company_id: str,
        request: ProjectCreateRequest,
    ) -> Dict[str, Any]:
        """Creates a cross-departmental project."""
        project_id = f"prj_{uuid.uuid4().hex[:12]}"
        now = ClockManager.now()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO work_projects (
                    id, mission_id, tenant_id, company_id, title, description,
                    lead_position_id, status, priority, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PLANNING', ?, ?, ?)
                """,
                (
                    project_id, request.mission_id, tenant_id, company_id, request.title,
                    request.description, request.lead_position_id,
                    request.priority.value if hasattr(request.priority, "value") else str(request.priority),
                    now, now
                )
            )
            conn.commit()

        return cls.get_project(tenant_id, company_id, project_id)

    @classmethod
    def get_project(cls, tenant_id: str, company_id: str, project_id: str) -> Dict[str, Any]:
        """Fetches a project by ID."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM work_projects WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (project_id, tenant_id, company_id)
            ).fetchone()
        if not row:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        return dict(row)

    # =========================================================================
    # WORK TASKS
    # =========================================================================

    @classmethod
    def create_task(
        cls,
        tenant_id: str,
        company_id: str,
        request: TaskCreateRequest,
    ) -> Dict[str, Any]:
        """
        Creates a new work task with DAG cycle verification and live capability checks.
        """
        task_id = f"tsk_{uuid.uuid4().hex[:12]}"
        now = ClockManager.now()

        # 1. DAG Cycle Check
        if request.dependencies:
            TaskDAGService.validate_no_cycles(tenant_id, company_id, task_id, request.dependencies)

        # 2. Check Required Capabilities against CapabilityTruthTable
        initial_status = TaskStatus.ASSIGNED if request.assignee_id else TaskStatus.PROPOSED
        blocked_code: Optional[str] = None
        blocked_detail: Optional[str] = None

        for cap in request.required_capabilities:
            cap_status = capability_truth_table.get_status(cap)
            if cap_status != "LIVE":
                initial_status = TaskStatus.BLOCKED
                blocked_code = "CAPABILITY_NOT_LIVE"
                blocked_detail = f"Required capability '{cap}' is '{cap_status}'. Live provider not configured."
                break

        # Compute SLA window
        sla_expires_at = None
        if request.sla_seconds:
            sla_expires_at = now + float(request.sla_seconds)

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO work_tasks (
                    id, tenant_id, company_id, mission_id, project_id, title,
                    description, owner_id, assignee_type, assignee_id, status,
                    blocked_reason_code, blocked_reason_detail, priority,
                    estimate_seconds, estimate_minor_units, acceptance_criteria,
                    required_capabilities, required_autonomy_level, sla_seconds,
                    deadline_ts, sla_expires_at, sla_escalation_level, linked_folio_id,
                    linked_document_ids, assignment_reasons, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, '{}', ?, ?)
                """,
                (
                    task_id, tenant_id, company_id, request.mission_id, request.project_id,
                    request.title, request.description, request.owner_id,
                    request.assignee_type.value if hasattr(request.assignee_type, "value") else str(request.assignee_type),
                    request.assignee_id, initial_status.value, blocked_code, blocked_detail,
                    request.priority.value if hasattr(request.priority, "value") else str(request.priority),
                    request.estimate_seconds, request.estimate_minor_units,
                    json.dumps(request.acceptance_criteria), json.dumps(request.required_capabilities),
                    request.required_autonomy_level, request.sla_seconds, request.deadline_ts,
                    sla_expires_at, request.linked_folio_id, json.dumps(request.linked_document_ids),
                    now, now
                )
            )

            # Insert dependencies
            for dep_id in request.dependencies:
                dep_row_id = f"td_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO task_dependencies (id, tenant_id, company_id, task_id, depends_on_task_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (dep_row_id, tenant_id, company_id, task_id, dep_id, now)
                )

            # Log creation event
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_CREATED', NULL, ?, 'PRINCIPAL', ?, ?, ?)
                """,
                (event_id, tenant_id, company_id, task_id, initial_status.value, request.owner_id, "{}", now)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORK_TASK_CREATED",
            payload={
                "task_id": task_id,
                "title": request.title,
                "status": initial_status.value,
                "blocked_code": blocked_code,
            },
            action_id=f"create_task_{task_id}"
        )

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def get_task(cls, tenant_id: str, company_id: str, task_id: str) -> Dict[str, Any]:
        """Fetches a task with its dependencies."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM work_tasks WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (task_id, tenant_id, company_id)
            ).fetchone()
            if not row:
                raise TaskNotFoundError(f"Task '{task_id}' not found.")

            deps = conn.execute(
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ? AND tenant_id = ? AND company_id = ?",
                (task_id, tenant_id, company_id)
            ).fetchall()

        data = dict(row)
        data["dependencies"] = [d["depends_on_task_id"] for d in deps]

        for json_col in ("acceptance_criteria", "required_capabilities", "linked_document_ids", "assignment_reasons", "submitted_deliverable"):
            if data.get(json_col) and isinstance(data[json_col], str):
                try:
                    data[json_col] = json.loads(data[json_col])
                except Exception:
                    pass

        return data

    @classmethod
    def assign_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        assignee_id: Optional[str] = None,
        assignee_type: AssigneeType = AssigneeType.POSITION,
        actor_id: str = "system",
        candidate_pool: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Assigns or auto-assigns a task using deterministic scoring.
        """
        task = cls.get_task(tenant_id, company_id, task_id)
        current_status = TaskStatus(task["status"])

        # Determine target assignee
        if assignee_id is None:
            chosen_id, reasons = TaskAssignmentEngine.select_best_assignee(
                tenant_id=tenant_id,
                company_id=company_id,
                estimate_minor_units=task["estimate_minor_units"],
                required_autonomy_level=task["required_autonomy_level"],
                required_capabilities=task["required_capabilities"],
                candidate_pool=candidate_pool,
            )
        else:
            chosen_id = assignee_id
            eligible, reason = TaskAssignmentEngine.evaluate_candidate_eligibility(
                tenant_id=tenant_id,
                company_id=company_id,
                candidate_id=chosen_id,
                estimate_minor_units=task["estimate_minor_units"],
                required_autonomy_level=task["required_autonomy_level"],
                required_capabilities=task["required_capabilities"],
            )
            reasons = {
                "selected_candidate_id": chosen_id,
                "explicitly_assigned": True,
                "eligible": eligible,
                "reason": reason or "Explicitly assigned by user/system.",
            }

        # Check state transition: PROPOSED -> ASSIGNED or ASSIGNED -> ASSIGNED (reassign)
        target_status = TaskStatus.ASSIGNED
        TaskStateMachine.validate_transition(current_status, target_status, actor_id=actor_id)

        now = ClockManager.now()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE work_tasks
                SET assignee_id = ?, assignee_type = ?, status = ?, assignment_reasons = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (
                    chosen_id,
                    assignee_type.value if hasattr(assignee_type, "value") else str(assignee_type),
                    target_status.value,
                    json.dumps(reasons),
                    now,
                    task_id,
                    tenant_id,
                    company_id
                )
            )

            # Record event
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_ASSIGNED', ?, ?, 'SYSTEM', ?, ?, ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, actor_id, json.dumps(reasons), now)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORK_TASK_ASSIGNED",
            payload={"task_id": task_id, "assignee_id": chosen_id, "reasons": reasons},
            action_id=f"assign_task_{task_id}"
        )

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def accept_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        actor_id: str,
    ) -> Dict[str, Any]:
        """
        Accepts an assigned task. Verifies prerequisite tasks are completed.
        Checks capabilities: if not LIVE, transitions to BLOCKED.
        """
        task = cls.get_task(tenant_id, company_id, task_id)
        current_status = TaskStatus(task["status"])

        # Check Prerequisite Completion
        satisfied, uncompleted = TaskDAGService.check_prerequisites_completed(tenant_id, company_id, task_id)
        if not satisfied:
            raise PrerequisiteNotCompletedError(
                f"PREREQUISITE_NOT_COMPLETED: Cannot accept task '{task_id}'. Prerequisites not COMPLETED: {uncompleted}"
            )

        # Check Capabilities
        for cap in task["required_capabilities"]:
            cap_status = capability_truth_table.get_status(cap)
            if cap_status != "LIVE":
                return cls._transition_to_blocked(
                    tenant_id, company_id, task_id, current_status, actor_id,
                    code="CAPABILITY_NOT_LIVE",
                    detail=f"Required capability '{cap}' is '{cap_status}'. Live provider not configured."
                )

        target_status = TaskStatus.ACCEPTED
        TaskStateMachine.validate_transition(current_status, target_status, actor_id=actor_id)

        now = ClockManager.now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE work_tasks SET status = ?, updated_at = ? WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (target_status.value, now, task_id, tenant_id, company_id)
            )
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_ACCEPTED', ?, ?, 'ASSIGNEE', ?, '{}', ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, actor_id, now)
            )
            conn.commit()

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def start_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        actor_id: str,
    ) -> Dict[str, Any]:
        """
        Transitions task from ACCEPTED to IN_PROGRESS.
        """
        task = cls.get_task(tenant_id, company_id, task_id)
        current_status = TaskStatus(task["status"])

        satisfied, uncompleted = TaskDAGService.check_prerequisites_completed(tenant_id, company_id, task_id)
        if not satisfied:
            raise PrerequisiteNotCompletedError(
                f"PREREQUISITE_NOT_COMPLETED: Cannot start task '{task_id}'. Prerequisites not COMPLETED: {uncompleted}"
            )

        for cap in task["required_capabilities"]:
            cap_status = capability_truth_table.get_status(cap)
            if cap_status != "LIVE":
                return cls._transition_to_blocked(
                    tenant_id, company_id, task_id, current_status, actor_id,
                    code="CAPABILITY_NOT_LIVE",
                    detail=f"Required capability '{cap}' is '{cap_status}'."
                )

        target_status = TaskStatus.IN_PROGRESS
        TaskStateMachine.validate_transition(current_status, target_status, actor_id=actor_id)

        now = ClockManager.now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE work_tasks SET status = ?, updated_at = ? WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (target_status.value, now, task_id, tenant_id, company_id)
            )
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_STARTED', ?, ?, 'ASSIGNEE', ?, '{}', ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, actor_id, now)
            )
            conn.commit()

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def submit_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        deliverable: Dict[str, Any],
        actor_id: str,
    ) -> Dict[str, Any]:
        """
        Assignee submits task deliverable. Moves status to SUBMITTED.
        Assignee CANNOT complete its own task (Rule 17).
        """
        task = cls.get_task(tenant_id, company_id, task_id)
        current_status = TaskStatus(task["status"])

        target_status = TaskStatus.SUBMITTED
        TaskStateMachine.validate_transition(current_status, target_status, actor_id=actor_id)

        now = ClockManager.now()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE work_tasks
                SET status = ?, submitted_deliverable = ?, submitted_at = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (target_status.value, json.dumps(deliverable), now, now, task_id, tenant_id, company_id)
            )
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_SUBMITTED', ?, ?, 'ASSIGNEE', ?, ?, ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, actor_id, json.dumps(deliverable), now)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORK_TASK_SUBMITTED",
            payload={"task_id": task_id, "actor_id": actor_id, "deliverable": deliverable},
            action_id=f"submit_task_{task_id}"
        )

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def verify_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        decision: str,  # "APPROVED" or "REJECTED"
        verifier_id: str,
        verification_report_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verification service or authorized human signs off on task.
        Assignee CAN NEVER complete or verify its own task (Rule 17).
        """
        task = cls.get_task(tenant_id, company_id, task_id)
        current_status = TaskStatus(task["status"])

        target_status = TaskStatus.COMPLETED if decision.upper() == "APPROVED" else TaskStatus.REJECTED

        # Enforces Rule 17: Assignee self-completion forbidden check
        TaskStateMachine.validate_transition(
            current_status=current_status,
            target_status=target_status,
            actor_id=verifier_id,
            assignee_id=task.get("assignee_id"),
            is_verifier=True
        )

        now = ClockManager.now()
        completed_at = now if target_status == TaskStatus.COMPLETED else None

        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE work_tasks
                SET status = ?, verification_report_id = ?, completed_by = ?,
                    completed_at = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (
                    target_status.value,
                    verification_report_id,
                    verifier_id if target_status == TaskStatus.COMPLETED else None,
                    completed_at,
                    now,
                    task_id,
                    tenant_id,
                    company_id
                )
            )

            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            details = {
                "decision": decision,
                "verifier_id": verifier_id,
                "verification_report_id": verification_report_id,
                "reason": reason,
            }
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_VERIFIED', ?, ?, 'VERIFIER', ?, ?, ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, verifier_id, json.dumps(details), now)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORK_TASK_VERIFIED",
            payload={
                "task_id": task_id,
                "decision": decision,
                "verifier_id": verifier_id,
                "status": target_status.value,
            },
            action_id=f"verify_task_{task_id}"
        )

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def reassign_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        new_assignee_id: str,
        new_assignee_type: AssigneeType = AssigneeType.POSITION,
        actor_id: str = "system",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reassigns an assigned task to a new assignee."""
        return cls.assign_task(
            tenant_id=tenant_id,
            company_id=company_id,
            task_id=task_id,
            assignee_id=new_assignee_id,
            assignee_type=new_assignee_type,
            actor_id=actor_id,
        )

    @classmethod
    def cancel_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        actor_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancels a task from any non-terminal state."""
        task = cls.get_task(tenant_id, company_id, task_id)
        current_status = TaskStatus(task["status"])

        target_status = TaskStatus.CANCELLED
        TaskStateMachine.validate_transition(current_status, target_status, actor_id=actor_id)

        now = ClockManager.now()
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE work_tasks SET status = ?, updated_at = ? WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (target_status.value, now, task_id, tenant_id, company_id)
            )
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_CANCELLED', ?, ?, 'PRINCIPAL', ?, ?, ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, actor_id, json.dumps({"reason": reason}), now)
            )
            conn.commit()

        return cls.get_task(tenant_id, company_id, task_id)

    @classmethod
    def _transition_to_blocked(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        current_status: TaskStatus,
        actor_id: str,
        code: str,
        detail: str,
    ) -> Dict[str, Any]:
        """Transitions a task to BLOCKED status with machine-readable reasons."""
        target_status = TaskStatus.BLOCKED
        TaskStateMachine.validate_transition(current_status, target_status, actor_id=actor_id)

        now = ClockManager.now()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE work_tasks
                SET status = ?, blocked_reason_code = ?, blocked_reason_detail = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (target_status.value, code, detail, now, task_id, tenant_id, company_id)
            )
            event_id = f"ev_tsk_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO task_events (
                    id, tenant_id, company_id, task_id, event_type, from_status,
                    to_status, actor_type, actor_id, details, timestamp
                ) VALUES (?, ?, ?, ?, 'TASK_BLOCKED', ?, ?, 'SYSTEM', ?, ?, ?)
                """,
                (event_id, tenant_id, company_id, task_id, current_status.value, target_status.value, actor_id, json.dumps({"code": code, "detail": detail}), now)
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="WORK_TASK_BLOCKED",
            payload={"task_id": task_id, "code": code, "detail": detail},
            action_id=f"block_task_{task_id}"
        )

        return cls.get_task(tenant_id, company_id, task_id)


workforce_work_service = WorkforceWorkService()
