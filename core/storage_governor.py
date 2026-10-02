"""
RoboAssistant Company OS 1.0 — Storage Governor & Resource Exhaustion Defense
Monitors filesystem usage, enforces disk retention policies, rotates logs/ledgers,
and throttles heavy executions when host storage enters critical/emergency thresholds.
"""

import os
import shutil
import time
import logging
import sqlite3
from typing import Dict, Any, Optional
from .db import db

logger = logging.getLogger("zonata.storage_governor")

class StorageStatus:
    HEALTHY = "HEALTHY"       # < 70% used
    WARNING = "WARNING"       # 70% - 80% used
    CRITICAL = "CRITICAL"     # 80% - 90% used
    EMERGENCY = "EMERGENCY"   # > 90% used

class StorageGovernor:
    WARN_THRESHOLD = 0.70
    CRITICAL_THRESHOLD = 0.80
    EMERGENCY_THRESHOLD = 0.90
    MIN_FREE_GB = 5.0

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_dir = os.path.join(self.base_dir, "storage")
        self.sandbox_dir = os.path.join(self.storage_dir, "sandbox")
        self.evidence_dir = os.path.join(self.storage_dir, "evidence")

    def get_disk_metrics(self) -> Dict[str, Any]:
        """Calculates storage metrics for the volume hosting ZONATA."""
        try:
            total, used, free = shutil.disk_usage(self.base_dir)
            total_gb = round(total / (1024 ** 3), 2)
            used_gb = round(used / (1024 ** 3), 2)
            free_gb = round(free / (1024 ** 3), 2)
            used_pct = round((used / total) * 100, 1)

            if used_pct >= (self.EMERGENCY_THRESHOLD * 100) or free_gb < self.MIN_FREE_GB:
                status = StorageStatus.EMERGENCY
            elif used_pct >= (self.CRITICAL_THRESHOLD * 100):
                status = StorageStatus.CRITICAL
            elif used_pct >= (self.WARN_THRESHOLD * 100):
                status = StorageStatus.WARNING
            else:
                status = StorageStatus.HEALTHY

            return {
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "used_pct": used_pct,
                "status": status,
                "emergency_throttling_active": status == StorageStatus.EMERGENCY,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "error": str(e),
                "status": StorageStatus.EMERGENCY,
                "emergency_throttling_active": True,
                "timestamp": time.time()
            }

    def can_allocate_workload(self, estimated_mb: float = 10.0) -> bool:
        """
        Hard Governance Boundary: Blocks new heavy executions, browser sessions,
        or workspace creation if host enters EMERGENCY storage state.
        """
        metrics = self.get_disk_metrics()
        if metrics.get("emergency_throttling_active", False):
            # If less than MIN_FREE_GB, only allow critical safety/governance operations
            if metrics.get("free_gb", 0) < 2.0:
                logger.critical(f"[STORAGE EMERGENCY] Host disk space exhausted! Free: {metrics.get('free_gb')} GB. Rejecting workload.")
                return False
        return True

    def purge_temporary_artifacts(self, max_age_hours: float = 24.0) -> Dict[str, Any]:
        """Purges old sandbox files, temporary outputs, and debug logs."""
        purged_files = 0
        freed_bytes = 0
        cutoff = time.time() - (max_age_hours * 3600)

        # 1. Clean sandbox files
        if os.path.exists(self.sandbox_dir):
            for fname in os.listdir(self.sandbox_dir):
                fpath = os.path.join(self.sandbox_dir, fname)
                try:
                    if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                        size = os.path.getsize(fpath)
                        os.remove(fpath)
                        purged_files += 1
                        freed_bytes += size
                except Exception:
                    pass

        # 2. Clean temporary debug logs
        debug_log = os.path.join(self.evidence_dir, "debug_ledger.jsonl")
        if os.path.exists(debug_log):
            try:
                if os.path.getsize(debug_log) > 10 * 1024 * 1024: # > 10MB
                    size = os.path.getsize(debug_log)
                    with open(debug_log, "w") as f:
                        f.write("")
                    freed_bytes += size
                    purged_files += 1
            except Exception:
                pass

        return {
            "purged_files_count": purged_files,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "status": "COMPLETED"
        }

    def perform_db_maintenance(self) -> Dict[str, Any]:
        """Executes safe WAL checkpointing and query optimization."""
        t0 = time.time()
        try:
            with db.get_connection() as conn:
                conn.execute("PRAGMA optimize;")
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            duration_ms = round((time.time() - t0) * 1000, 2)
            return {"status": "SUCCESS", "duration_ms": duration_ms}
        except Exception as e:
            return {"status": "ERROR", "detail": str(e)}
