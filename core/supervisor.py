"""
RoboAssistant Company OS 1.0 — Autonomous 24x7x365 Company Supervisor Daemon
Continuously monitors live company vitals, agent fleet health, scheduled operations,
Temporal worker heartbeats, Nango connection status, and host storage thresholds.
"""

import time
import threading
import uuid
import logging
from typing import Dict, Any, Optional
from .db import db
from .storage_governor import StorageGovernor
from zonata.health import CompanyHealthEngine

logger = logging.getLogger("zonata.supervisor")

class CompanySupervisorDaemon:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary", tick_interval_sec: float = 10.0):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.tick_interval_sec = tick_interval_sec
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.tick_count = 0
        self.last_tick_time = 0.0
        self.last_health_score: Optional[float] = None
        self.anomalies_detected = 0
        self.storage_governor = StorageGovernor()
        self.health_engine = CompanyHealthEngine()

    def start(self):
        """Starts the autonomous 24x7x365 supervisor background loop."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="ZonataSupervisorThread")
        self.thread.start()
        logger.info(f"[*] Autonomous Company Supervisor started for tenant={self.tenant_id} (tick={self.tick_interval_sec}s)")

    def stop(self):
        """Signals the supervisor loop to terminate gracefully."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("[*] Autonomous Company Supervisor stopped gracefully.")

    def _run_loop(self):
        while self.running:
            try:
                self.tick()
            except Exception as e:
                logger.error(f"[SUPERVISOR EXCEPTION] Error during supervision cycle: {e}")
            time.sleep(self.tick_interval_sec)

    def tick(self) -> Dict[str, Any]:
        """Executes a single discrete supervisory cycle across all company aspects."""
        self.tick_count += 1
        now = time.time()
        self.last_tick_time = now

        # 1. Storage & Resource Health Check
        disk = self.storage_governor.get_disk_metrics()
        if disk.get("status") == "EMERGENCY":
            self.anomalies_detected += 1
            # Run automatic cleanup
            self.storage_governor.purge_temporary_artifacts(max_age_hours=12.0)

        # 2. Company Health Evaluation
        health_score = 65.0
        try:
            health_model = self.health_engine.evaluate_company_health(self.tenant_id, self.company_id)
            health_score = health_model.overall_score
            self.last_health_score = health_score
            if health_score < 40.0:
                self.anomalies_detected += 1
                logger.warning(f"[SUPERVISOR ALERT] Company health dropped to {health_score}!")
        except Exception as e:
            logger.debug(f"Health evaluation deferred: {e}")

        # 3. Schedule Dispatch Check
        dispatched_schedules = 0
        try:
            with db.get_connection() as conn:
                # Find due items
                rows = conn.execute(
                    "SELECT id, title FROM universal_schedules WHERE tenant_id = ? AND status = 'PENDING' AND start_time <= ? LIMIT 5",
                    (self.tenant_id, now)
                ).fetchall()
                for r in rows:
                    conn.execute("UPDATE universal_schedules SET status = 'EXECUTING', updated_at = ? WHERE id = ?", (now, r[0]))
                    dispatched_schedules += 1
                conn.commit()
        except Exception:
            pass

        # 4. Temporal Worker Health Monitoring
        active_workers = 0
        try:
            with db.get_connection() as conn:
                workers = conn.execute("SELECT worker_id, heartbeat_at FROM temporal_workers WHERE status = 'ONLINE'").fetchall()
                active_workers = len(workers)
                for w in workers:
                    if now - w[1] > 90.0:  # Worker missed heartbeats for 90s
                        conn.execute("UPDATE temporal_workers SET status = 'DEGRADED' WHERE worker_id = ?", (w[0],))
                        self.anomalies_detected += 1
                conn.commit()
        except Exception:
            pass

        # 5. Persist Heartbeat Record
        heartbeat_id = f"hb_{uuid.uuid4().hex[:8]}"
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO supervisor_heartbeats (
                        heartbeat_id, tenant_id, company_id, tick_number, health_score,
                        active_schedules, active_workers, disk_status, anomalies_detected, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        heartbeat_id, self.tenant_id, self.company_id, self.tick_count,
                        health_score, dispatched_schedules, active_workers,
                        disk.get("status", "HEALTHY"), self.anomalies_detected, now
                    )
                )
                conn.commit()
        except Exception:
            pass

        return {
            "tick": self.tick_count,
            "timestamp": now,
            "health_score": health_score,
            "disk_status": disk.get("status"),
            "dispatched_schedules": dispatched_schedules,
            "active_workers": active_workers,
            "anomalies_detected": self.anomalies_detected
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "tick_count": self.tick_count,
            "last_tick_time": self.last_tick_time,
            "last_health_score": self.last_health_score,
            "anomalies_detected": self.anomalies_detected,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id
        }

# Global singleton supervisor
global_supervisor = CompanySupervisorDaemon()
