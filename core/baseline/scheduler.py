"""
ZONATA Durable Leased Scheduler (OpenCode Step 1I)
Persisted job schedule with monotonic next-run, max-run-time enforcement,
missed-run catchup policies, and cluster leader lease with 30s dead-node failover.
"""

from dataclasses import dataclass
from enum import Enum
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional
import uuid

from core.db import db, tenant_scoped

logger = logging.getLogger("zonata.baseline.scheduler")


class JobStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


@dataclass
class ScheduledJobRecord:
    job_id: str
    tenant_id: str
    company_id: str
    name: str
    cron_or_interval_seconds: int
    next_run_at: float
    last_run_at: Optional[float]
    max_run_seconds: int
    catchup_policy: str  # 'RUN_ONCE' or 'SKIP_MISSED'
    lease_owner: Optional[str]
    lease_heartbeat_at: Optional[float]
    lease_expires_at: Optional[float]
    status: JobStatus
    created_at: float


def ensure_scheduler_tables(conn: Optional[Any] = None) -> None:
    """Ensures scheduled_jobs and scheduler_leader_leases exist with multi-tenant RLS."""
    import pathlib
    from core.db import db, DatabaseDialect

    migration_file = "0018_always_on_baseline.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    if conn is not None:
        if hasattr(conn, "executescript") and db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                conn.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                conn.execute(sql_path.read_text(encoding="utf-8"))
        return

    with db.get_connection() as connection:
        if db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                connection.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                connection.execute(sql_path.read_text(encoding="utf-8"))


class DurableScheduler:
    """Distributed job scheduler with monotonic timing, leader election, and 30s failover."""

    DEFAULT_LEASE_DURATION = 30.0

    def __init__(self, db_conn_factory=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self._handlers: Dict[str, Callable[[ScheduledJobRecord], None]] = {}
        ensure_scheduler_tables()

    @tenant_scoped
    def register_job(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        interval_seconds: int,
        handler: Callable[[ScheduledJobRecord], None],
        max_run_seconds: int = 300,
        catchup_policy: str = "RUN_ONCE",
        first_run_delay_seconds: float = 0.0,
    ) -> str:
        """Registers a durable scheduled job with monotonic next-run timing."""
        now = time.time()
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        next_run = now + first_run_delay_seconds

        self._handlers[name] = handler

        with self.db_conn_factory() as conn:
            cur = conn.cursor()
            # Upsert into scheduled_jobs
            if db.is_postgresql():
                cur.execute(
                    """
                    INSERT INTO scheduled_jobs (
                        job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                        next_run_at, max_run_seconds, catchup_policy, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'IDLE', ?)
                    ON CONFLICT (tenant_id, company_id, name) DO UPDATE SET
                        cron_or_interval_seconds = EXCLUDED.cron_or_interval_seconds,
                        max_run_seconds = EXCLUDED.max_run_seconds,
                        catchup_policy = EXCLUDED.catchup_policy
                    RETURNING job_id
                    """,
                    (
                        job_id,
                        tenant_id,
                        company_id,
                        name,
                        interval_seconds,
                        next_run,
                        max_run_seconds,
                        catchup_policy,
                        now,
                    ),
                )
                row = cur.fetchone()
                job_id = row[0] if row else job_id
            else:
                cur.execute(
                    """
                    INSERT INTO scheduled_jobs (
                        job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                        next_run_at, max_run_seconds, catchup_policy, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'IDLE', ?)
                    ON CONFLICT (tenant_id, company_id, name) DO UPDATE SET
                        cron_or_interval_seconds = excluded.cron_or_interval_seconds,
                        max_run_seconds = excluded.max_run_seconds,
                        catchup_policy = excluded.catchup_policy
                    """,
                    (
                        job_id,
                        tenant_id,
                        company_id,
                        name,
                        interval_seconds,
                        next_run,
                        max_run_seconds,
                        catchup_policy,
                        now,
                    ),
                )
                cur.execute(
                    "SELECT job_id FROM scheduled_jobs WHERE tenant_id = ? AND company_id = ? AND name = ?",
                    (tenant_id, company_id, name),
                )
                row = cur.fetchone()
                if row:
                    job_id = row[0]
            conn.commit()

        return job_id

    # --------------------------------------------------------------------------
    # Leader Election Leases
    # --------------------------------------------------------------------------

    def acquire_or_renew_leader_lease(
        self,
        node_id: str,
        lease_key: str = "cluster_scheduler_leader",
        lease_duration: float = DEFAULT_LEASE_DURATION,
    ) -> bool:
        """Acquires or extends the leader lease.
        
        Returns True if node_id is the active leader, False otherwise.
        If a previous leader's lease has expired (expires_at < now), it is reclaimed.
        """
        now = time.time()
        new_expires_at = now + lease_duration

        with self.db_conn_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT leader_node_id, expires_at FROM scheduler_leader_leases WHERE lease_key = ?",
                (lease_key,),
            )
            row = cur.fetchone()

            if not row:
                # No lease exists: insert
                try:
                    cur.execute(
                        """
                        INSERT INTO scheduler_leader_leases (lease_key, leader_node_id, heartbeat_at, expires_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (lease_key, node_id, now, new_expires_at),
                    )
                    conn.commit()
                    return True
                except Exception:
                    return False

            current_leader, current_expires_at = row[0], row[1]
            if current_leader == node_id:
                # Renew own lease
                cur.execute(
                    """
                    UPDATE scheduler_leader_leases
                    SET heartbeat_at = ?, expires_at = ?
                    WHERE lease_key = ? AND leader_node_id = ?
                    """,
                    (now, new_expires_at, lease_key, node_id),
                )
                conn.commit()
                return True
            elif current_expires_at < now:
                # Previous leader dead (heartbeat expired past 30s): take over
                cur.execute(
                    """
                    UPDATE scheduler_leader_leases
                    SET leader_node_id = ?, heartbeat_at = ?, expires_at = ?
                    WHERE lease_key = ? AND expires_at < ?
                    """,
                    (node_id, now, new_expires_at, lease_key, now),
                )
                conn.commit()
                return cur.rowcount > 0
            else:
                # Another node holds an active lease
                return False

    def release_leader_lease(
        self,
        node_id: str,
        lease_key: str = "cluster_scheduler_leader",
    ) -> None:
        """Voluntarily drops the leader lease on graceful shutdown."""
        with self.db_conn_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM scheduler_leader_leases WHERE lease_key = ? AND leader_node_id = ?",
                (lease_key, node_id),
            )
            conn.commit()

    # --------------------------------------------------------------------------
    # Job Execution, Heartbeats & Orphan Lock Recovery
    # --------------------------------------------------------------------------

    @tenant_scoped
    def tick(
        self,
        node_id: str,
        lease_duration: float = DEFAULT_LEASE_DURATION,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> int:
        """Executes one tick of the scheduler on node_id.
        
        1. Checks/renews leader lease. If not leader, returns 0.
        2. Reclaims orphan jobs from dead nodes (jobs whose lease_expires_at < now or exceeded max_run_seconds).
        3. Identifies and runs due jobs (next_run_at <= now and status == 'IDLE').
        """
        if not self.acquire_or_renew_leader_lease(node_id, lease_duration=lease_duration):
            return 0

        now = time.time()
        executed_count = 0

        with self.db_conn_factory() as conn:
            cur = conn.cursor()

            # 1. Orphan lock reclamation: reset jobs whose worker crashed or timed out
            cur.execute(
                """
                UPDATE scheduled_jobs
                SET status = 'IDLE', lease_owner = NULL, lease_heartbeat_at = NULL, lease_expires_at = NULL
                WHERE status = 'RUNNING'
                  AND (lease_expires_at < ? OR (? - last_run_at > max_run_seconds))
                """,
                (now, now),
            )

            # 2. Find eligible due jobs
            cur.execute(
                """
                SELECT job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                       next_run_at, last_run_at, max_run_seconds, catchup_policy,
                       lease_owner, lease_heartbeat_at, lease_expires_at, status, created_at
                FROM scheduled_jobs
                WHERE status = 'IDLE' AND next_run_at <= ?
                ORDER BY next_run_at ASC
                """,
                (now,),
            )
            rows = cur.fetchall()

            due_jobs: List[ScheduledJobRecord] = []
            for r in rows:
                due_jobs.append(
                    ScheduledJobRecord(
                        job_id=r[0],
                        tenant_id=r[1],
                        company_id=r[2],
                        name=r[3],
                        cron_or_interval_seconds=r[4],
                        next_run_at=r[5],
                        last_run_at=r[6],
                        max_run_seconds=r[7],
                        catchup_policy=r[8],
                        lease_owner=r[9],
                        lease_heartbeat_at=r[10],
                        lease_expires_at=r[11],
                        status=JobStatus(r[12]),
                        created_at=r[13],
                    )
                )

            # Claim jobs
            lease_expiry = now + lease_duration
            for j in due_jobs:
                cur.execute(
                    """
                    UPDATE scheduled_jobs
                    SET status = 'RUNNING', lease_owner = ?, lease_heartbeat_at = ?, lease_expires_at = ?, last_run_at = ?
                    WHERE job_id = ? AND status = 'IDLE'
                    """,
                    (node_id, now, lease_expiry, now, j.job_id),
                )
            conn.commit()

        # Execute claimed jobs
        for job in due_jobs:
            handler = self._handlers.get(job.name)
            job_failed = False
            if handler:
                try:
                    handler(job)
                except Exception as exc:
                    logger.error(f"[Scheduler Node {node_id}] Job {job.name} ({job.job_id}) failed: {exc}")
                    job_failed = True
            else:
                logger.warning(f"No in-process handler registered for job {job.name}")

            fin_time = time.time()

            # Monotonic next run calculation
            if job.catchup_policy == "SKIP_MISSED":
                next_run = fin_time + job.cron_or_interval_seconds
            else:  # RUN_ONCE
                # Monotonic progression based on scheduled slot or current time
                next_run = max(fin_time, job.next_run_at + job.cron_or_interval_seconds)

            new_status = JobStatus.FAILED if job_failed else JobStatus.IDLE

            with self.db_conn_factory() as fin_conn:
                fin_cur = fin_conn.cursor()
                fin_cur.execute(
                    """
                    UPDATE scheduled_jobs
                    SET status = ?, next_run_at = ?, lease_owner = NULL, lease_heartbeat_at = NULL, lease_expires_at = NULL
                    WHERE job_id = ?
                    """,
                    (new_status.value, next_run, job.job_id),
                )
                fin_conn.commit()

            executed_count += 1

        return executed_count

    @tenant_scoped
    def get_job(
        self,
        job_id: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> Optional[ScheduledJobRecord]:
        """Fetches a scheduled job by ID."""
        with self.db_conn_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                       next_run_at, last_run_at, max_run_seconds, catchup_policy,
                       lease_owner, lease_heartbeat_at, lease_expires_at, status, created_at
                FROM scheduled_jobs
                WHERE job_id = ?
                  AND (tenant_id = ? OR ? IS NULL)
                  AND (company_id = ? OR ? IS NULL)
                """,
                (job_id, tenant_id, tenant_id, company_id, company_id),
            )
            r = cur.fetchone()
            if not r:
                return None
            return ScheduledJobRecord(
                job_id=r[0],
                tenant_id=r[1],
                company_id=r[2],
                name=r[3],
                cron_or_interval_seconds=r[4],
                next_run_at=r[5],
                last_run_at=r[6],
                max_run_seconds=r[7],
                catchup_policy=r[8],
                lease_owner=r[9],
                lease_heartbeat_at=r[10],
                lease_expires_at=r[11],
                status=JobStatus(r[12]),
                created_at=r[13],
            )
