"""
ZONATA Universal AI Co-worker Fabric — 24x7 Worker Supervisor & Watchdog
Ensures continuous long-running operation, lease enforcement, worker heartbeats,
mission scheduling, and dead-letter / human escalation queuing.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid
from .contracts import ExecutionLease, TaskNode, ExecutionState, CoworkerProfile

class ExecutionLeaseManager:
    """Manages short-lived execution leases to prevent hung tasks."""

    def __init__(self, default_lease_ttl_sec: float = 900.0, heartbeat_timeout_sec: float = 60.0):
        self.default_ttl = default_lease_ttl_sec
        self.heartbeat_timeout = heartbeat_timeout_sec
        self._leases: Dict[str, ExecutionLease] = {}

    def acquire_lease(self, task_id: str, worker_id: str) -> ExecutionLease:
        now = time.time()
        lease_id = f"lease_{uuid.uuid4().hex[:8]}"
        lease = ExecutionLease(
            lease_id=lease_id,
            task_id=task_id,
            worker_id=worker_id,
            acquired_at=now,
            expires_at=now + self.default_ttl,
            heartbeat_at=now,
            status="ACTIVE"
        )
        self._leases[lease_id] = lease
        return lease

    def record_heartbeat(self, lease_id: str) -> bool:
        lease = self._leases.get(lease_id)
        if not lease or lease.status != "ACTIVE":
            return False
        now = time.time()
        if now > lease.expires_at:
            lease.status = "EXPIRED"
            return False
        lease.heartbeat_at = now
        return True

    def release_lease(self, lease_id: str) -> bool:
        lease = self._leases.get(lease_id)
        if lease:
            lease.status = "RELEASED"
            return True
        return False

    def is_lease_valid(self, lease_id: str) -> bool:
        lease = self._leases.get(lease_id)
        if not lease or lease.status != "ACTIVE":
            return False
        now = time.time()
        # Check overall expiration and heartbeat stall
        if now > lease.expires_at or (now - lease.heartbeat_at) > self.heartbeat_timeout:
            lease.status = "EXPIRED"
            return False
        return True


class WorkerSupervisor:
    """
    24x7 Worker Supervisor & Watchdog.
    Maintains active coworker profiles, queues, and continuous health heartbeats.
    """

    def __init__(self):
        self.lease_mgr = ExecutionLeaseManager()
        self._workers: Dict[str, CoworkerProfile] = {}
        self._schedules: List[Dict[str, Any]] = []

        # Operational queues
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self.retry_queue: List[Dict[str, Any]] = []
        self.recovery_queue: List[Dict[str, Any]] = []
        self.human_escalation_queue: List[Dict[str, Any]] = []

    def register_worker(self, profile: CoworkerProfile):
        self._workers[profile.worker_id] = profile

    def get_worker(self, worker_id: str) -> Optional[CoworkerProfile]:
        return self._workers.get(worker_id)

    def list_workers(self) -> List[CoworkerProfile]:
        return list(self._workers.values())

    def schedule_mission(self, cron_like_schedule: str, mission_objective: str, worker_id: str) -> str:
        sched_id = f"sched_{uuid.uuid4().hex[:8]}"
        self._schedules.append({
            "schedule_id": sched_id,
            "schedule": cron_like_schedule,
            "objective": mission_objective,
            "worker_id": worker_id,
            "active": True,
            "created_at": time.time()
        })
        return sched_id

    def list_schedules(self) -> List[Dict[str, Any]]:
        return self._schedules

    def escalate_to_human(self, task: TaskNode, reason: str, context: Dict[str, Any]):
        self.human_escalation_queue.append({
            "task_id": task.task_id,
            "mission_id": task.mission_id,
            "capability_id": task.capability_id,
            "reason": reason,
            "context": context,
            "timestamp": time.time(),
            "status": "AWAITING_HUMAN"
        })

    def send_to_dead_letter(self, task: TaskNode, reason: str):
        self.dead_letter_queue.append({
            "task_id": task.task_id,
            "mission_id": task.mission_id,
            "reason": reason,
            "timestamp": time.time()
        })

    def run_watchdog_cycle(self) -> Dict[str, Any]:
        """Runs periodic health and lease audit."""
        expired_count = 0
        now = time.time()
        for lease_id, lease in list(self.lease_mgr._leases.items()):
            if lease.status == "EXPIRED" or (lease.status == "ACTIVE" and not self.lease_mgr.is_lease_valid(lease_id)):
                expired_count += 1
                self.recovery_queue.append({
                    "lease_id": lease_id,
                    "task_id": lease.task_id,
                    "worker_id": lease.worker_id,
                    "reason": "Lease heartbeat expired / hung worker",
                    "timestamp": now
                })

        return {
            "timestamp": time.time(),
            "active_workers": len(self._workers),
            "expired_leases_recovered": expired_count,
            "escalations_pending": len(self.human_escalation_queue),
            "dead_letter_count": len(self.dead_letter_queue),
            "recovery_queue_length": len(self.recovery_queue)
        }
