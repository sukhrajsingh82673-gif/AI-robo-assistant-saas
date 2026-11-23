"""
ZONATA Daemon Health Canary Probe
=================================
Executes active synthetic probes against database connectivity,
outbox queue backlog, and cryptographic subsystems.
Emits structured DaemonHealthStatus.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from core.db import db
from core.ports.kms import resolve_kms_provider

logger = logging.getLogger("zonata.daemon.canary")


@dataclass
class DaemonHealthStatus:
    status: str  # 'HEALTHY', 'DEGRADED', 'UNHEALTHY'
    database_connected: bool
    outbox_backlog_size: int
    kms_roundtrip_ok: bool
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == "HEALTHY"


class DaemonCanaryProbe:
    """Active health probe verifying core operational vitals."""

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def check_health(self) -> DaemonHealthStatus:
        """Executes synthetic health verification checks."""
        db_ok = False
        outbox_backlog = 0
        kms_ok = False
        details = {}

        # 1. Database Connectivity Probe
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                row = cur.fetchone()
                db_ok = bool(row and row[0] == 1)

                # Check outbox backlog
                cur.execute("SELECT COUNT(*) FROM outbox_events WHERE status IN ('PENDING', 'FAILED')")
                count_row = cur.fetchone()
                outbox_backlog = int(count_row[0]) if count_row else 0
                details["db_dialect"] = getattr(db.dialect, "value", str(db.dialect))
        except Exception as exc:
            logger.error("Health probe database check failed: %s", exc)
            details["db_error"] = str(exc)

        # 2. KMS Roundtrip Probe
        try:
            kms = resolve_kms_provider()
            test_plain = b"daemon_canary_probe_synthetic_payload"
            res, ciphertext = kms.encrypt(test_plain, context={"tenant_id": self.tenant_id})
            dec_res, decrypted = kms.decrypt(ciphertext, context={"tenant_id": self.tenant_id})
            kms_ok = (decrypted == test_plain)
            details["kms_provider"] = type(kms).__name__
        except Exception as exc:
            logger.error("Health probe KMS check failed: %s", exc)
            details["kms_error"] = str(exc)

        # Determine overall status
        if db_ok and kms_ok:
            status = "HEALTHY"
        elif db_ok and not kms_ok:
            status = "DEGRADED"
        else:
            status = "UNHEALTHY"

        return DaemonHealthStatus(
            status=status,
            database_connected=db_ok,
            outbox_backlog_size=outbox_backlog,
            kms_roundtrip_ok=kms_ok,
            details=details
        )
