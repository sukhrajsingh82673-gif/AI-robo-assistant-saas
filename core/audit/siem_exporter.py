"""
ZONATA Sovereign Core — Sub-Step 5F: Audit Logging & SIEM Ingestion Exporter.
=============================================================================
Governed by:
- Merkle audit chains & cryptographically verifiable event sequencing.
- Common Event Format (CEF) and OpenTelemetry (OTel) structured emission.
- SIEM integration (Splunk HEC, Datadog, Sentinel, Elastic).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.db import db

logger = logging.getLogger("zonata.audit.siem")


class AuditChainTamperedError(Exception):
    """Raised when cryptographic hash-chain verification fails on audit logs."""
    pass


@dataclass
class AuditEvent:
    event_id: str
    timestamp: float
    actor_id: str
    actor_role: str
    tenant_id: str
    company_id: str
    action: str
    target_resource: str
    status: str  # "SUCCESS", "DENIED", "ERROR"
    prev_event_hash: str
    event_hash: str = ""
    evidence_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 hash over canonical fields."""
        canonical_str = (
            f"{self.event_id}:{self.timestamp:.6f}:{self.actor_id}:{self.actor_role}:"
            f"{self.tenant_id}:{self.company_id}:{self.action}:{self.target_resource}:"
            f"{self.status}:{self.prev_event_hash}:{self.evidence_id or ''}:"
            f"{json.dumps(self.details, sort_keys=True)}"
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def to_cef(self) -> str:
        """
        Formats event according to Micro Focus Common Event Format (CEF:0).
        CEF:Version|Device Vendor|Device Product|Device Version|Device Event Class ID|Name|Severity|Extension
        """
        severity = "3" if self.status == "SUCCESS" else ("7" if self.status == "DENIED" else "8")
        extension_parts = [
            f"src={self.actor_id}",
            f"srole={self.actor_role}",
            f"cs1={self.tenant_id}",
            f"cs1Label=TenantID",
            f"cs2={self.company_id}",
            f"cs2Label=CompanyID",
            f"act={self.action}",
            f"target={self.target_resource}",
            f"outcome={self.status}",
            f"cn1={self.timestamp:.3f}",
            f"cn1Label=Timestamp",
            f"hash={self.event_hash}",
        ]
        if self.evidence_id:
            extension_parts.append(f"cs3={self.evidence_id}")
            extension_parts.append("cs3Label=EvidenceID")

        ext_str = " ".join(extension_parts)
        return f"CEF:0|ZONATA|SovereignOS|1.0|{self.action}|{self.action}|{severity}|{ext_str}"


class SIEMExporter:
    """Manages hash-chained audit logging and SIEM distribution."""

    GENESIS_HASH = "GENESIS_ZONATA_AUDIT_ROOT_0000000000000000000000000000000000000000"

    def __init__(self):
        self._events: List[AuditEvent] = []
        self._last_hash = self.GENESIS_HASH
        self._init_db()

    def _init_db(self) -> None:
        """Create a durable append-only backing table for audit events."""
        with db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS siem_audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_resource TEXT NOT NULL,
                    status TEXT NOT NULL,
                    prev_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    evidence_id TEXT,
                    details_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _persist_event(self, event: AuditEvent) -> None:
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO siem_audit_events (
                    event_id, timestamp, actor_id, actor_role, tenant_id, company_id,
                    action, target_resource, status, prev_event_hash, event_hash,
                    evidence_id, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.timestamp,
                    event.actor_id,
                    event.actor_role,
                    event.tenant_id,
                    event.company_id,
                    event.action,
                    event.target_resource,
                    event.status,
                    event.prev_event_hash,
                    event.event_hash,
                    event.evidence_id,
                    json.dumps(event.details, sort_keys=True),
                ),
            )
            conn.commit()

    def log_event(
        self,
        actor_id: str,
        actor_role: str,
        tenant_id: str,
        company_id: str,
        action: str,
        target_resource: str,
        status: str = "SUCCESS",
        evidence_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> AuditEvent:
        """Appends a new hash-chained audit event."""
        now = timestamp if timestamp is not None else time.time()
        event_id = f"aud_{uuid.uuid4().hex[:12]}"

        event = AuditEvent(
            event_id=event_id,
            timestamp=now,
            actor_id=actor_id,
            actor_role=actor_role,
            tenant_id=tenant_id,
            company_id=company_id,
            action=action,
            target_resource=target_resource,
            status=status,
            prev_event_hash=self._last_hash,
            evidence_id=evidence_id,
            details=dict(details or {}),
        )
        event.event_hash = event.compute_hash()

        self._persist_event(event)
        self._events.append(event)
        self._last_hash = event.event_hash
        return event

    def get_events(self) -> List[AuditEvent]:
        return list(self._events)

    def export_cef_stream(self) -> List[str]:
        """Exports all events as a list of CEF-formatted lines."""
        return [evt.to_cef() for evt in self._events]

    def export_to_siem(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> Dict[str, Any]:
        """POST the hash-chained CEF stream to a configured SIEM collector.

        No endpoint means no distribution: the caller receives an explicit
        NOT_CONFIGURED result rather than a fabricated success.
        """
        target = endpoint or os.environ.get("SIEM_ENDPOINT")
        if not target:
            return {"status": "NOT_CONFIGURED", "exported": 0, "error": "SIEM_ENDPOINT not set"}

        lines = self.export_cef_stream()
        body = "\n".join(lines).encode("utf-8")
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        auth_token = token or os.environ.get("SIEM_TOKEN")
        if auth_token:
            headers["Authorization"] = f"Splunk {auth_token}"

        request = urllib.request.Request(target, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status_code = response.status
        except Exception as exc:
            return {"status": "FAILED", "exported": 0, "error": str(exc)}

        if status_code >= 300:
            return {"status": "FAILED", "exported": 0, "error": f"HTTP {status_code}"}
        return {"status": "OK", "exported": len(lines)}

    @staticmethod
    def verify_chain(events: List[AuditEvent]) -> bool:
        """
        Cryptographically verifies the linear integrity of an audit event chain.
        Fails closed on hash mutation or link breakage.
        """
        if not events:
            return True

        expected_prev = SIEMExporter.GENESIS_HASH
        for idx, evt in enumerate(events):
            if evt.prev_event_hash != expected_prev:
                raise AuditChainTamperedError(
                    f"Audit chain broken at event {idx} ({evt.event_id}): "
                    f"expected prev_hash {expected_prev}, got {evt.prev_event_hash}"
                )
            recalculated = evt.compute_hash()
            if evt.event_hash != recalculated:
                raise AuditChainTamperedError(
                    f"Audit event {idx} ({evt.event_id}) hash altered: "
                    f"recorded {evt.event_hash}, calculated {recalculated}"
                )
            expected_prev = evt.event_hash

        return True
