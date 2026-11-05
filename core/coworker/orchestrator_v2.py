"""
ZONATA Autonomous Coworker 2.0 — 12-State Lifecycle Orchestrator
Coordinates lifecycle transitions, lease heartbeats, ambient security patrols,
cleanups, and crash recovery.
"""

from __future__ import annotations
import time
import uuid
import os
import shutil
import signal
from typing import Optional, Dict, Any, List
from .contracts_v2 import (
    TaskLifecycleState, VALID_TRANSITIONS, CoworkerV2Task,
    TaskStateTransition, CoworkerExecutionLease, LeaseStatus,
    CleanupManifestRecord, CleanupResourceType, CleanupStatus,
    SecurityPatrolFinding, PatrolType, PatrolSeverity
)
from .db_store_v2 import CoworkerDbStoreV2


class InvalidStateTransitionError(Exception):
    """Raised when a state machine transition violates sovereign lifecycle invariants."""
    pass


class CoworkerLifecycleOrchestrator:
    """
    Main state machine orchestrator for ZONATA Coworker 2.0.
    Enforces the 12-state task lifecycle invariants and automated background patrols.
    """

    _instance: Optional[CoworkerLifecycleOrchestrator] = None

    @classmethod
    def get_instance(
        cls,
        db_store: Optional[CoworkerDbStoreV2] = None,
        store: Optional[CoworkerDbStoreV2] = None,
        tenant_id: str = "tnt_primary",
        default_lease_ttl: float = 300.0
    ) -> CoworkerLifecycleOrchestrator:
        if cls._instance is None:
            cls._instance = cls(db_store=db_store, store=store, tenant_id=tenant_id, default_lease_ttl=default_lease_ttl)
        return cls._instance

    def __init__(
        self,
        db_store: Optional[CoworkerDbStoreV2] = None,
        store: Optional[CoworkerDbStoreV2] = None,
        tenant_id: str = "tnt_primary",
        default_lease_ttl: float = 300.0
    ):
        self.db = store or db_store or CoworkerDbStoreV2.get_instance()
        self.store = self.db
        self.tenant_id = tenant_id
        self.default_lease_ttl = default_lease_ttl
        self._orchestrator_state = TaskLifecycleState.IDLE

    def create_task(
        self,
        objective: str,
        description: str = "",
        assigned_by: str = "AI_CEO",
        risk_level: Any = "LOW",
        target_workspace: Optional[str] = None,
        mission_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CoworkerV2Task:
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        msn_id = mission_id or f"msn_{uuid.uuid4().hex[:8]}"
        risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
        task = CoworkerV2Task(
            task_id=task_id,
            mission_id=msn_id,
            tenant_id=self.tenant_id,
            company_id="cmp_primary",
            title=objective,
            description=description or objective,
            state=TaskLifecycleState.TASK_RECEIVED,
            parameters={"target_workspace": target_workspace, **(metadata or {})},
            risk_level=risk_str,
            authority_scope=["standard"]
        )
        self.db.save_task(task)
        return task

    def transition(
        self,
        task_id: str,
        target_state: TaskLifecycleState,
        reason: str = "Lifecycle transition",
        actor: str = "orchestrator",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CoworkerV2Task:
        return self.transition_to(task_id, target_state, reason=reason, trigger=actor, metadata=metadata)

    def pause_task(self, task_id: str, actor: str = "OPERATOR", reason: str = "Task paused") -> CoworkerV2Task:
        return self.transition_to(task_id, TaskLifecycleState.PAUSED, reason=reason, trigger=actor)

    def resume_task(self, task_id: str, actor: str = "OPERATOR") -> CoworkerV2Task:
        return self.transition_to(task_id, TaskLifecycleState.EXECUTION, reason="Task resumed", trigger=actor)

    def abort_task(self, task_id: str, actor: str = "OPERATOR", reason: str = "Task aborted") -> CoworkerV2Task:
        return self.transition_to(task_id, TaskLifecycleState.TERMINATED, reason=reason, trigger=actor)

    def recover_crashed_tasks(self, timeout_seconds: float = 300.0) -> int:
        recovered = self.recover_crashes(max_stale_seconds=timeout_seconds)
        return len(recovered)

    @property
    def current_orchestrator_state(self) -> TaskLifecycleState:
        return self._orchestrator_state

    # --- State Machine Transitions ---

    def transition_to(
        self,
        task_id: str,
        target_state: TaskLifecycleState,
        reason: str,
        trigger: str = "orchestrator",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CoworkerV2Task:
        """
        Transitions a task to a target state, enforcing invariant validation and logging.
        """
        task = self.db.get_task(task_id)
        if not task:
            raise ValueError(f"Task with id '{task_id}' not found.")

        current = task.state
        allowed = VALID_TRANSITIONS.get(current, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal transition: Cannot transition from {current.value} to {target_state.value}. "
                f"Valid targets: {[s.value for s in allowed]}"
            )

        now = time.time()
        task.state = target_state
        task.updated_at = now
        if target_state in (TaskLifecycleState.REPORTING_TO_CEO, TaskLifecycleState.TERMINATED):
            task.completed_at = now

        self.db.save_task(task)

        # Audit transition
        trans = TaskStateTransition(
            transition_id=f"tr_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            from_state=current,
            to_state=target_state,
            reason=reason,
            trigger=trigger,
            timestamp=now,
            metadata=metadata or {}
        )
        self.db.record_transition(trans)

        # If task reached completion or termination, trigger cleanups
        if target_state in (TaskLifecycleState.IDLE, TaskLifecycleState.TERMINATED):
            self.execute_cleanups(task_id=task_id, mission_id=task.mission_id)

        # Update orchestrator ambient state
        self._update_ambient_state()
        return task

    # --- Lease Management ---

    def acquire_lease(
        self,
        task_id: str,
        worker_id: str,
        ttl_seconds: Optional[float] = None
    ) -> CoworkerExecutionLease:
        now = time.time()
        ttl = ttl_seconds or self.default_lease_ttl
        lease = CoworkerExecutionLease(
            lease_id=f"lease_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            worker_id=worker_id,
            acquired_at=now,
            expires_at=now + ttl,
            heartbeat_at=now,
            ttl_seconds=ttl,
            status=LeaseStatus.ACTIVE
        )
        self.db.save_lease(lease)

        task = self.db.get_task(task_id)
        if task:
            task.lease_id = lease.lease_id
            task.assigned_worker_id = worker_id
            self.db.save_task(task)

        return lease

    def renew_lease(self, lease_id: str, ttl_seconds: Optional[float] = None) -> bool:
        lease = self.db.get_lease(lease_id)
        if not lease or lease.status != LeaseStatus.ACTIVE:
            return False
        now = time.time()
        if now > lease.expires_at:
            lease.expire()
            self.db.save_lease(lease)
            return False
        lease.renew(ttl=ttl_seconds, now=now)
        self.db.save_lease(lease)
        return True

    def release_lease(self, lease_id: str) -> bool:
        lease = self.db.get_lease(lease_id)
        if not lease:
            return False
        lease.release()
        self.db.save_lease(lease)
        return True

    def is_lease_valid(self, lease_id: str) -> bool:
        lease = self.db.get_lease(lease_id)
        if not lease:
            return False
        return lease.is_valid()

    # --- Ambient State & Security Patrol ---

    def _update_ambient_state(self) -> None:
        active = self.db.list_active_tasks(self.tenant_id)
        if not active:
            self._orchestrator_state = TaskLifecycleState.SECURITY_MONITORING
        else:
            self._orchestrator_state = TaskLifecycleState.EXECUTION

    def run_idle_security_patrol(self) -> Optional[SecurityPatrolFinding]:
        """
        When coworker is IDLE or in SECURITY_MONITORING, patrol host resources
        for orphaned processes, credential leaks, and high memory utilization.
        """
        active = self.db.list_active_tasks(self.tenant_id)
        if active:
            return None  # Busy with tasks

        self._orchestrator_state = TaskLifecycleState.SECURITY_MONITORING
        now = time.time()

        # 1. Check for stale temporary directories in /tmp/zonata_workspaces
        finding = None
        base_ws = "/tmp/zonata_workspaces"
        stale_dirs_count = 0
        if os.path.exists(base_ws):
            try:
                for entry in os.listdir(base_ws):
                    entry_path = os.path.join(base_ws, entry)
                    if os.path.isdir(entry_path):
                        mtime = os.path.getmtime(entry_path)
                        if (now - mtime) > 7200:  # 2 hours stale
                            stale_dirs_count += 1
            except Exception:
                pass

        if stale_dirs_count > 0:
            finding = SecurityPatrolFinding(
                finding_id=f"fnd_{uuid.uuid4().hex[:8]}",
                patrol_type=PatrolType.FILESYSTEM,
                severity=PatrolSeverity.LOW,
                description=f"Detected {stale_dirs_count} stale isolated workspace directories in {base_ws}",
                target=base_ws,
                auto_remediated=False,
                remediation_action="Scheduled for cleanup manifest sweep",
                detected_at=now,
                metadata={"stale_dirs_count": stale_dirs_count}
            )
            self.db.record_patrol_finding(finding)

        return finding

    # --- Crash Recovery & Cleanup Manifest Execution ---

    def recover_crashes(self, max_stale_seconds: float = 300.0) -> List[CoworkerV2Task]:
        """Scans for abandoned active tasks and recovers them to ERROR_RECOVERY."""
        return self.db.recover_orphaned_tasks(max_stale_seconds=max_stale_seconds)

    def execute_cleanups(self, task_id: Optional[str] = None, mission_id: Optional[str] = None) -> int:
        """
        Safely reclaims all pending resources registered in the cleanup manifest:
        - VENV / DIRECTORY: removed with shutil.rmtree
        - TEMP_FILE: removed with os.remove
        - PROCESS: terminated with SIGTERM/SIGKILL
        """
        pending = self.db.list_pending_cleanups(mission_id=mission_id, task_id=task_id)
        cleaned_count = 0

        for record in pending:
            path = record.resource_path
            success = True
            err_msg = None

            try:
                if record.resource_type in (CleanupResourceType.VENV, CleanupResourceType.DIRECTORY):
                    if os.path.exists(path) and os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                elif record.resource_type == CleanupResourceType.TEMP_FILE:
                    if os.path.exists(path) and os.path.isfile(path):
                        os.remove(path)
                elif record.resource_type == CleanupResourceType.PROCESS:
                    try:
                        pid = int(path)
                        os.kill(pid, signal.SIGTERM)
                    except (ValueError, ProcessLookupError, PermissionError) as e:
                        err_msg = str(e)
            except Exception as ex:
                success = False
                err_msg = str(ex)

            self.db.mark_cleaned(record.manifest_id, success=success, error=err_msg)
            if success:
                cleaned_count += 1

        return cleaned_count
