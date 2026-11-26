"""
ZONATA Autonomous Self-Healing & Fault-Recovery Supervisor
=========================================================
Monitors running jobs and distributed locks.
Automatically reclaims orphaned leases, resets stalled outbox locks,
and manages circuit breakers for third-party dependencies.
"""

import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from core.db import db

logger = logging.getLogger("zonata.daemon.self_healing")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, fast-reject calls
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


class CircuitBreaker:
    """Manages failure thresholds and automatic cooldown recovery for external dependencies."""

    def __init__(self, name: str, failure_threshold: int = 3, cooldown_sec: float = 5.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_sec = cooldown_sec
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.successful_trials = 0

    def can_execute(self) -> bool:
        """Determines whether a call can proceed through the circuit."""
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.cooldown_sec:
                logger.info("Circuit breaker '%s' entering HALF_OPEN state after cooldown", self.name)
                self.state = CircuitState.HALF_OPEN
                self.successful_trials = 0
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self):
        """Records a successful operation; closes circuit if in HALF_OPEN."""
        if self.state == CircuitState.HALF_OPEN:
            self.successful_trials += 1
            if self.successful_trials >= 2:
                logger.info("Circuit breaker '%s' healed: resetting to CLOSED", self.name)
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self):
        """Records a failure; trips circuit to OPEN if threshold reached."""
        self.last_failure_time = time.time()
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            logger.warning("Circuit breaker '%s' TRIPPED to OPEN (failures: %d)", self.name, self.failure_count)
            self.state = CircuitState.OPEN


class SelfHealingSupervisor:
    """Scans and heals orphaned database resources, crashed worker locks, and external circuits."""

    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Retrieves or initializes a circuit breaker for a service."""
        if service_name not in self._circuit_breakers:
            self._circuit_breakers[service_name] = CircuitBreaker(service_name)
        return self._circuit_breakers[service_name]

    def reclaim_orphaned_jobs(self) -> int:
        """
        Detects scheduled jobs with status='RUNNING' whose lease_expires_at has expired.
        Resets them to 'IDLE' so other nodes can execute them cleanly.
        """
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
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
                UPDATE scheduled_jobs
                SET status = 'IDLE', lease_owner = NULL, lease_expires_at = NULL
                WHERE status = 'RUNNING' AND lease_expires_at < ?
                """,
                (now,),
            )
            conn.commit()
            reclaimed = cur.rowcount
            if reclaimed > 0:
                logger.info("SelfHealingSupervisor reclaimed %d orphaned scheduled jobs", reclaimed)
            return reclaimed

    def reclaim_stalled_outbox_locks(self) -> int:
        """
        Detects outbox events locked in 'PROCESSING' whose locked_until has expired.
        Resets status to 'PENDING' for re-processing.
        """
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS outbox_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    last_error TEXT,
                    next_retry_at REAL NOT NULL,
                    locked_by TEXT,
                    locked_until REAL,
                    dispatched_at REAL,
                    created_at REAL NOT NULL
                )
            """)

            cur.execute(
                """
                UPDATE outbox_events
                SET status = 'PENDING', locked_by = NULL, locked_until = NULL
                WHERE status = 'PROCESSING' AND locked_until < ?
                """,
                (now,),
            )
            conn.commit()
            reclaimed = cur.rowcount
            if reclaimed > 0:
                logger.info("SelfHealingSupervisor reclaimed %d stalled outbox event locks", reclaimed)
            return reclaimed

    def run_healing_cycle(self) -> Dict[str, int]:
        """Runs a complete self-healing sweep."""
        reclaimed_jobs = self.reclaim_orphaned_jobs()
        reclaimed_events = self.reclaim_stalled_outbox_locks()
        return {
            "reclaimed_jobs": reclaimed_jobs,
            "reclaimed_outbox_events": reclaimed_events,
        }
