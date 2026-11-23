"""
ZONATA Enterprise Autonomous 24/7 Supervisor Daemon
===================================================
Coordinates cluster leadership election, leased job scheduling,
transactional outbox draining, and self-healing recovery.
Gracefully handles OS termination signals.
"""

import time
import signal
import logging
import threading
from typing import Dict, Any, Optional, Callable, List

from core.db import db
from core.daemon.leader_elector import LeaderElector
from core.daemon.dlq_processor import OutboxDLQProcessor
from core.daemon.self_healing import SelfHealingSupervisor
from core.daemon.canary_probe import DaemonCanaryProbe, DaemonHealthStatus

logger = logging.getLogger("zonata.daemon.autonomous")


class AutonomousDaemon:
    """Enterprise 24/7 autonomous supervisor daemon."""

    def __init__(
        self,
        node_id: Optional[str] = None,
        tenant_id: str = "tnt_primary",
        company_id: str = "comp_primary",
        tick_interval_sec: float = 5.0,
    ):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.tick_interval_sec = tick_interval_sec

        self.leader_elector = LeaderElector(node_id=node_id)
        self.node_id = self.leader_elector.node_id
        self.dlq_processor = OutboxDLQProcessor(worker_id=self.node_id)
        self.self_healing = SelfHealingSupervisor()
        self.canary_probe = DaemonCanaryProbe(tenant_id=tenant_id, company_id=company_id)

        self._job_handlers: Dict[str, Callable[[], None]] = {}
        self.running = False
        self._thread: Optional[threading.Thread] = None

        # Telemetry metrics
        self.tick_count = 0
        self.last_tick_time = 0.0
        self.total_jobs_executed = 0
        self.last_health_status: Optional[DaemonHealthStatus] = None

    def register_job_handler(self, job_name: str, handler: Callable[[], None]):
        """Registers a callable execution handler for a named scheduled job."""
        self._job_handlers[job_name] = handler

    def start(self):
        """Starts background daemon loop."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"ZonataDaemon-{self.node_id[:8]}"
        )
        self._thread.start()
        logger.info("AutonomousDaemon %s started (tick=%.1fs)", self.node_id, self.tick_interval_sec)

    def stop(self):
        """Signals daemon to terminate gracefully and releases leader lease."""
        if not self.running:
            return
        logger.info("Stopping AutonomousDaemon %s gracefully...", self.node_id)
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        # Release leadership lease
        self.leader_elector.release_lease()
        logger.info("AutonomousDaemon %s stopped and leadership lease released.", self.node_id)

    def _run_loop(self):
        while self.running:
            try:
                self.tick()
            except Exception as exc:
                logger.error("Unhandled exception in AutonomousDaemon tick: %s", exc)
            time.sleep(self.tick_interval_sec)

    def tick(self, now: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes a single discrete supervisory cycle.
        Returns detailed execution report for the cycle.
        """
        self.tick_count += 1
        current_time = now if now is not None else time.time()
        self.last_tick_time = current_time

        report: Dict[str, Any] = {
            "tick": self.tick_count,
            "timestamp": current_time,
            "node_id": self.node_id,
            "is_leader": False,
            "self_healing": {},
            "jobs_executed": 0,
            "outbox": {},
        }

        # 1. Attempt leadership acquisition or renewal
        is_leader = self.leader_elector.try_acquire_or_renew(ttl_seconds=30.0)
        report["is_leader"] = is_leader

        if not is_leader:
            return report

        # 2. Leader Tasks: Run Self-Healing
        report["self_healing"] = self.self_healing.run_healing_cycle()

        # 3. Leader Tasks: Execute Scheduled Jobs
        report["jobs_executed"] = self._execute_ready_scheduled_jobs(current_time)
        self.total_jobs_executed += report["jobs_executed"]

        # 4. Leader Tasks: Process Outbox & DLQ
        report["outbox"] = self.dlq_processor.process_batch(batch_size=50)

        # 5. Health Canary Check (every 5 ticks)
        if self.tick_count % 5 == 1:
            self.last_health_status = self.canary_probe.check_health()
            report["health_status"] = self.last_health_status.status

        return report

    def _execute_ready_scheduled_jobs(self, now: float) -> int:
        """Executes jobs whose next_run_at <= now, enforcing catchup policies."""
        executed_count = 0
        with db.get_connection() as conn:
            cur = conn.cursor()

            # Ensure table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    cron_or_interval_seconds INTEGER NOT NULL,
                    next_run_at REAL NOT NULL,
                    last_run_at REAL,
                    max_run_seconds INTEGER NOT NULL DEFAULT 300,
                    catchup_policy TEXT NOT NULL DEFAULT 'RUN_ONCE',
                    lease_owner TEXT,
                    lease_heartbeat_at REAL,
                    lease_expires_at REAL,
                    status TEXT NOT NULL DEFAULT 'IDLE',
                    created_at REAL NOT NULL
                )
            """)

            cur.execute(
                """
                SELECT job_id, name, cron_or_interval_seconds, next_run_at, max_run_seconds, catchup_policy
                FROM scheduled_jobs
                WHERE status = 'IDLE' AND next_run_at <= ?
                ORDER BY next_run_at ASC
                LIMIT 10
                """,
                (now,),
            )
            ready_jobs = cur.fetchall()

            for job_id, name, interval_sec, next_run, max_run, catchup in ready_jobs:
                lease_expires = now + max_run
                # Lock job
                cur.execute(
                    """
                    UPDATE scheduled_jobs
                    SET status = 'RUNNING', lease_owner = ?, lease_heartbeat_at = ?, lease_expires_at = ?
                    WHERE job_id = ? AND status = 'IDLE'
                    """,
                    (self.node_id, now, lease_expires, job_id),
                )
                conn.commit()

                # Execute handler if registered
                handler = self._job_handlers.get(name)
                job_status = "IDLE"
                if handler:
                    try:
                        handler()
                    except Exception as e:
                        logger.error("Scheduled job '%s' raised exception: %s", name, e)
                        job_status = "FAILED"

                # Calculate next_run_at based on catchup policy
                if catchup == "SKIP_MISSED":
                    # Monotonic forward jump from current time
                    new_next_run = now + interval_sec
                else:
                    # RUN_ONCE: advance from scheduled time
                    new_next_run = next_run + interval_sec
                    if new_next_run < now:
                        new_next_run = now + interval_sec

                cur.execute(
                    """
                    UPDATE scheduled_jobs
                    SET status = ?, last_run_at = ?, next_run_at = ?, lease_owner = NULL, lease_expires_at = NULL
                    WHERE job_id = ?
                    """,
                    (job_status, now, new_next_run, job_id),
                )
                conn.commit()
                executed_count += 1

        return executed_count

    def register_signal_handlers(self):
        """Attaches clean shutdown hooks to SIGINT and SIGTERM."""
        def _handler(signum, frame):
            logger.info("Received termination signal %d; shutting down daemon...", signum)
            self.stop()

        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
        except Exception as e:
            logger.warning("Could not register OS signal handlers: %s", e)
