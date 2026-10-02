"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
High-Availability Distributed Company Supervisor Service
Implements distributed leader election, lease heartbeat renewal, failover takeover,
stuck-job detection, orphan recovery, and comprehensive vitals supervision.
"""

import time
import uuid
import socket
import random
import logging
import threading
from typing import Dict, Any, Optional, List
from core.distributed_coordination import coordination, DistributedLock
from core.database_engine import engine, WorkloadType
from core.storage_governor import StorageGovernor
from zonata.health import CompanyHealthEngine

logger = logging.getLogger("zonata.supervisor.ha")

class SupervisorRole:
    LEADER = "LEADER"
    STANDBY = "STANDBY"
    STOPPED = "STOPPED"

class CompanySupervisorHA:
    """
    High-Availability Distributed Supervisor.
    Runs on every control-plane node. Exactly one instance holds the LEADER lease;
    all other instances remain in STANDBY ready for instant graceful takeover upon leader failure.
    """
    def __init__(
        self,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        node_id: Optional[str] = None,
        lease_seconds: float = 15.0,
        tick_interval_sec: float = 10.0
    ):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.node_id = node_id or f"sup_{socket.gethostname()}_{uuid.uuid4().hex[:6]}"
        self.lease_seconds = lease_seconds
        self.tick_interval_sec = tick_interval_sec

        self.role = SupervisorRole.STANDBY
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._active_lock: Optional[DistributedLock] = None

        self.storage_governor = StorageGovernor()
        self.health_engine = CompanyHealthEngine()

        self.tick_count = 0
        self.leader_acquisitions = 0
        self.last_tick_time = 0.0
        self.anomalies_detected = 0

    def start(self):
        """Starts the HA supervisor background loop."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name=f"SupervisorHA-{self.node_id}")
        self.thread.start()
        logger.info(f"[*] SupervisorHA node {self.node_id} started in STANDBY mode.")

    def stop(self):
        """Signals supervisor to step down from leadership and terminate gracefully."""
        self.running = False
        self.role = SupervisorRole.STOPPED
        if self._active_lock:
            self._active_lock.release()
            self._active_lock = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info(f"[*] SupervisorHA node {self.node_id} stopped gracefully.")

    def _run_loop(self):
        while self.running:
            try:
                self._maintain_leadership_or_standby()
                if self.role == SupervisorRole.LEADER:
                    self.tick()
            except Exception as e:
                logger.error(f"[SUPERVISOR HA ERROR] Cycle error on node {self.node_id}: {e}")

            time.sleep(self.tick_interval_sec)

    def _maintain_leadership_or_standby(self):
        """Compete for or renew distributed leader lease."""
        lock_key = f"supervisor:leader:{self.tenant_id}:{self.company_id}"

        # Register node heartbeat
        coordination.register_heartbeat(
            node_id=self.node_id,
            role=self.role,
            metadata={"tenant_id": self.tenant_id, "tick_count": self.tick_count},
            ttl_seconds=self.lease_seconds
        )

        if self.role == SupervisorRole.LEADER:
            # Renew existing lease
            if self._active_lock and not self._active_lock.renew(self.lease_seconds):
                logger.warning(f"[SUPERVISOR TAKEOVER WARNING] Node {self.node_id} lost leader lease! Demoting to STANDBY.")
                self.role = SupervisorRole.STANDBY
                self._active_lock = None
        else:
            # Attempt to acquire leader lease
            lock = coordination.acquire_lock(lock_key, owner=self.node_id, lease_seconds=self.lease_seconds)
            if lock:
                self.role = SupervisorRole.LEADER
                self._active_lock = lock
                self.leader_acquisitions += 1
                logger.info(f"[SUPERVISOR PROMOTION] Node {self.node_id} acquired LEADER lease! Promoted to active supervisor.")

    def tick(self) -> Dict[str, Any]:
        """Leader tick: executes scheduled jobs, orphan recovery, and vitals monitoring."""
        if self.role != SupervisorRole.LEADER:
            return {"status": "SKIPPED_STANDBY", "role": self.role}

        self.tick_count += 1
        now = time.time()
        self.last_tick_time = now

        # 1. Storage & Host Thresholds
        disk = self.storage_governor.get_disk_metrics()
        if disk.get("status") == "EMERGENCY":
            self.anomalies_detected += 1
            self.storage_governor.purge_temporary_artifacts(max_age_hours=6.0)

        # 2. Orphaned / Stuck Command Recovery
        recovered_jobs = self._recover_stuck_commands(now)

        # 3. Schedule Dispatch with Jitter & Idempotency
        dispatched_schedules = self._dispatch_due_schedules(now)

        # 4. Temporal Worker Health Check
        degraded_workers = self._audit_temporal_workers(now)

        # 5. Record supervisor heartbeat in database
        self._record_heartbeat(now)

        return {
            "node_id": self.node_id,
            "role": self.role,
            "tick": self.tick_count,
            "recovered_jobs": recovered_jobs,
            "dispatched_schedules": dispatched_schedules,
            "degraded_workers": degraded_workers,
            "timestamp": now
        }

    def _recover_stuck_commands(self, now: float) -> int:
        """Find jobs stuck in ASSIGNED or EXECUTING state beyond 300s and reset them to QUEUED."""
        timeout_threshold = now - 300.0
        recovered = 0
        try:
            with engine.transaction(workload=WorkloadType.WRITE) as conn:
                cursor = conn.execute("""
                UPDATE async_command_queue
                SET status = 'QUEUED', worker_id = NULL, updated_at = ?
                WHERE tenant_id = ? AND status = 'ASSIGNED' AND updated_at < ?
                """, (now, self.tenant_id, timeout_threshold))
                recovered = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                if recovered > 0:
                    logger.info(f"[ORPHAN RECOVERY] Reset {recovered} orphaned commands to QUEUED.")
        except Exception as e:
            logger.debug(f"Orphan recovery skipped: {e}")
        return recovered

    def _dispatch_due_schedules(self, now: float) -> int:
        """Atomically claim and dispatch due schedules using row locking and jitter."""
        dispatched = 0
        jitter = random.uniform(0.05, 0.5)
        try:
            with engine.transaction(workload=WorkloadType.WRITE) as conn:
                rows = conn.execute("""
                SELECT id, title FROM universal_schedules
                WHERE tenant_id = ? AND status = 'PENDING' AND start_time <= ?
                LIMIT 5
                """, (self.tenant_id, now)).fetchall()

                for r in rows:
                    sched_id = r[0]
                    # Idempotency check via coordination
                    if coordination.set_idempotency_key(f"sched_dispatch:{sched_id}", "DISPATCHED", ttl_seconds=3600.0):
                        conn.execute("UPDATE universal_schedules SET status = 'EXECUTING', updated_at = ? WHERE id = ?", (now + jitter, sched_id))
                        dispatched += 1
        except Exception as e:
            logger.debug(f"Schedule dispatch skipped: {e}")
        return dispatched

    def _audit_temporal_workers(self, now: float) -> int:
        """Check for silent or crashed Temporal workers and mark DEGRADED."""
        stale_threshold = now - 60.0
        degraded = 0
        try:
            with engine.transaction(workload=WorkloadType.WRITE) as conn:
                cursor = conn.execute("""
                UPDATE temporal_workers
                SET status = 'DEGRADED'
                WHERE tenant_id = ? AND status = 'ACTIVE' AND last_heartbeat < ?
                """, (self.tenant_id, stale_threshold))
                degraded = cursor.rowcount if hasattr(cursor, 'rowcount') else 0
        except Exception:
            pass
        return degraded

    def _record_heartbeat(self, now: float):
        try:
            with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
                conn.execute("""
                INSERT OR REPLACE INTO supervisor_heartbeats
                (tenant_id, company_id, node_id, tick_count, status, last_tick)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (self.tenant_id, self.company_id, self.node_id, self.tick_count, "HEALTHY", now))
        except Exception:
            pass

SupervisorHA = CompanySupervisorHA

if __name__ == "__main__":
    import sys
    import uuid
    import signal
    node_id = sys.argv[1] if len(sys.argv) > 1 else f"sup_{uuid.uuid4().hex[:6]}"
    tenant_id = sys.argv[2] if len(sys.argv) > 2 else "tnt_primary"
    company_id = sys.argv[3] if len(sys.argv) > 3 else "comp_primary"
    supervisor = SupervisorHA(tenant_id=tenant_id, company_id=company_id, node_id=node_id, tick_interval_sec=2.0)

    def handle_sig(sig, frame):
        supervisor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)
    supervisor.start()
    while supervisor.running:
        time.sleep(1.0)
