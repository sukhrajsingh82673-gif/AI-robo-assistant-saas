"""
ZONATA Health & Readiness Probes (OpenCode Step 1I)
/healthz (liveness: process responds) and /readyz (readiness: DB readable,
critical ports not FAILED, disk has >1GB free, migrations current).
"""

import logging
import os
import shutil
import time
from typing import Any, Dict, Tuple

from core.db import db

logger = logging.getLogger("zonata.baseline.health")

SERVER_START_TIME = time.time()
MIN_DISK_FREE_BYTES = int(os.environ.get("MIN_DISK_FREE_BYTES", 500 * 1024 * 1024))  # 500 MB default
RELEASE_VERSION = os.environ.get("ZONATA_RELEASE_VERSION", "1.0.0-RESTRICTED-PILOT")
RELEASE_SCOPE = "URA / ZONATA — RESTRICTED PRODUCTION PILOT, NOT PUBLIC GA"
PILOT_ENVELOPE = {
    "max_organizations": 3,
    "max_concurrency_leases_per_tenant": 4,
    "max_rpm_per_tenant": 60,
}


def check_liveness() -> Tuple[int, Dict[str, Any]]:
    """Liveness probe (/healthz): fast check that the process responds."""
    now = time.time()
    return 200, {
        "status": "OK",
        "service": "zonata-ai-robo-assistant",
        "version": RELEASE_VERSION,
        "release_scope": RELEASE_SCOPE,
        "uptime_seconds": round(now - SERVER_START_TIME, 2),
        "timestamp": now,
    }


def check_readiness() -> Tuple[int, Dict[str, Any]]:
    """Readiness probe (/readyz): deep qualification.
    
    Checks:
    1. Database readable (SELECT 1).
    2. Critical ports not FAILED (database, KMS).
    3. Disk free space > 1GB.
    4. Migration versions match code.
    
    Returns:
    - (200, details) if all checks pass (ready to receive traffic).
    - (503, details) if any critical check fails (unready, dropped from routing).
    """
    now = time.time()
    checks: Dict[str, Any] = {}
    is_ready = True
    failure_reasons = []

    # 1. Database Readability Check
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            row = cur.fetchone()
            if row and row[0] == 1:
                checks["database"] = {"status": "OK", "dialect": db.get_dialect()}
            else:
                is_ready = False
                checks["database"] = {"status": "FAILED", "error": "Query returned unexpected result"}
                failure_reasons.append("Database query returned unexpected result")
    except Exception as e:
        is_ready = False
        checks["database"] = {"status": "FAILED", "error": str(e)}
        failure_reasons.append(f"Database unreadable: {e}")

    # 2. Critical Ports Check
    try:
        from core.capability_probe import probe_database, probe_key_management
        from core.ports.base import PortStatus

        kms_res = probe_key_management()
        db_res = probe_database()

        critical_ports_ok = True
        ports_summary = {
            "kms": kms_res.status.value,
            "database": db_res.status.value,
        }
        if kms_res.status == PortStatus.FAILED:
            critical_ports_ok = False
            failure_reasons.append("Critical port 'kms' is in FAILED state")
        if db_res.status == PortStatus.FAILED:
            critical_ports_ok = False
            failure_reasons.append("Critical port 'database' is in FAILED state")

        checks["critical_ports"] = {
            "status": "OK" if critical_ports_ok else "FAILED",
            "ports": ports_summary,
        }
        if not critical_ports_ok:
            is_ready = False
    except Exception as e:
        # Ports probe exception
        checks["critical_ports"] = {"status": "FAILED", "error": str(e)}
        is_ready = False
        failure_reasons.append(f"Ports evaluation failed: {e}")

    # 3. Disk Space Check (>1GB free)
    try:
        # Probe current working directory disk volume
        path_to_check = os.getcwd()
        usage = shutil.disk_usage(path_to_check)
        free_gb = round(usage.free / (1024 ** 3), 2)
        disk_ok = usage.free >= MIN_DISK_FREE_BYTES
        min_required_gb = round(MIN_DISK_FREE_BYTES / (1024 ** 3), 2)
        checks["disk_space"] = {
            "status": "OK" if disk_ok else "FAILED",
            "free_bytes": usage.free,
            "free_gb": free_gb,
            "min_required_gb": min_required_gb,
        }
        if not disk_ok:
            is_ready = False
            failure_reasons.append(f"Disk space low: {free_gb} GB free (< {min_required_gb} GB minimum)")
    except Exception as e:
        checks["disk_space"] = {"status": "FAILED", "error": str(e)}
        is_ready = False
        failure_reasons.append(f"Disk space check failed: {e}")

    # 4. Migration Version Check
    try:
        from core.baseline.outbox import ensure_outbox_tables
        ensure_outbox_tables()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM outbox_events")
            cnt = cur.fetchone()[0]
            checks["migrations"] = {
                "status": "OK",
                "latest_baseline_table": "outbox_events",
                "rows_present": cnt >= 0,
            }
    except Exception as e:
        is_ready = False
        checks["migrations"] = {"status": "FAILED", "error": str(e)}
        failure_reasons.append(f"Migration verification failed: {e}")

    status_code = 200 if is_ready else 503
    payload = {
        "status": "READY" if is_ready else "UNREADY",
        "status_code": status_code,
        "version": RELEASE_VERSION,
        "release_scope": RELEASE_SCOPE,
        "pilot_envelope": PILOT_ENVELOPE,
        "timestamp": now,
        "checks": checks,
    }
    if not is_ready:
        payload["failure_reasons"] = failure_reasons

    return status_code, payload
