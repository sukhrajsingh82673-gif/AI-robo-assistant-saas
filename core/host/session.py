"""
ZONATA Host Session & Cryptographic Framing Manager
===================================================
OpenCode Step 3B: Host session tracking, monotonic sequence validation,
anti-replay protection, and Ed25519 signature verification.
"""

from __future__ import annotations
import base64
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Set

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from core.db import db, tenant_scoped
from core.host.types import (
    HostSessionRecord,
    HostSessionStatus,
    GrantEventType,
    ReplayDetectedError,
    HostSecurityViolation,
)

logger = logging.getLogger("zonata.host.session")


class HostSessionManager:
    """Manages host agent sessions with anti-replay, monotonic sequencing, and crypto verification."""

    # In-memory nonce cache with TTL to prevent replay attacks across sessions
    _SEEN_NONCES: Dict[str, float] = {}
    NONCE_WINDOW_SECONDS = 120.0

    @classmethod
    def _clean_stale_nonces(cls, now: float) -> None:
        stale = [n for n, ts in cls._SEEN_NONCES.items() if now - ts > cls.NONCE_WINDOW_SECONDS]
        for n in stale:
            cls._SEEN_NONCES.pop(n, None)

    @classmethod
    def canonical_envelope_bytes(
        cls,
        session_id: str,
        sequence_no: int,
        timestamp: float,
        nonce: str,
        payload: Dict[str, Any],
    ) -> bytes:
        """Constructs canonical deterministic payload byte representation for signing."""
        canonical_json_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        envelope_str = f"{session_id}:{sequence_no}:{timestamp:.4f}:{nonce}:{canonical_json_str}"
        return envelope_str.encode("utf-8")

    @classmethod
    @tenant_scoped
    def create_session(cls, device_id: str, tenant_id: str, company_id: str) -> HostSessionRecord:
        session_id = f"hsess_{uuid.uuid4().hex[:12]}"
        now = time.time()
        sql = """
        INSERT INTO host_sessions (
            session_id, device_id, tenant_id, company_id,
            status, last_sequence_no, last_heartbeat_at, created_at
        ) VALUES (
            :session_id, :device_id, :tenant_id, :company_id,
            'ACTIVE', 0, :now, :now
        )
        """
        with db.get_connection() as conn:
            conn.execute(sql, {
                "session_id": session_id,
                "device_id": device_id,
                "tenant_id": tenant_id,
                "company_id": company_id,
                "now": now,
            })
            if hasattr(conn, "commit"):
                conn.commit()

        logger.info(f"Created active host session {session_id} for device {device_id}")
        return HostSessionRecord(
            session_id=session_id,
            device_id=device_id,
            tenant_id=tenant_id,
            company_id=company_id,
            status=HostSessionStatus.ACTIVE,
            last_sequence_no=0,
            last_heartbeat_at=now,
            created_at=now,
        )

    @classmethod
    @tenant_scoped
    def get_session(cls, session_id: str) -> Optional[HostSessionRecord]:
        sql = """
        SELECT session_id, device_id, tenant_id, company_id,
               status, last_sequence_no, last_heartbeat_at, created_at
        FROM host_sessions
        WHERE session_id = :session_id
        """
        with db.get_connection() as conn:
            row = conn.execute(sql, {"session_id": session_id}).fetchone()
            if not row:
                return None
            return HostSessionRecord(
                session_id=row["session_id"],
                device_id=row["device_id"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                status=HostSessionStatus(row["status"]),
                last_sequence_no=row["last_sequence_no"],
                last_heartbeat_at=row["last_heartbeat_at"],
                created_at=row["created_at"],
            )

    @classmethod
    @tenant_scoped
    def halt_session(cls, session_id: str, reason: str, actor_id: str = "SYSTEM") -> bool:
        now = time.time()
        sql_select = "SELECT device_id, tenant_id, company_id FROM host_sessions WHERE session_id = :session_id"
        sql_update = """
        UPDATE host_sessions
        SET status = 'HALTED',
            last_heartbeat_at = :now
        WHERE session_id = :session_id
        """
        sql_event = """
        INSERT INTO grant_events (
            event_id, grant_id, device_id, tenant_id, company_id,
            event_type, details, actor_id, actor_type, timestamp
        ) VALUES (
            :event_id, NULL, :device_id, :tenant_id, :company_id,
            :event_type, :details, :actor_id, :actor_type, :timestamp
        )
        """
        with db.get_connection() as conn:
            row = conn.execute(sql_select, {"session_id": session_id}).fetchone()
            if not row:
                return False

            conn.execute(sql_update, {"session_id": session_id, "now": now})
            conn.execute(sql_event, {
                "event_id": f"gev_{uuid.uuid4().hex[:12]}",
                "device_id": row["device_id"],
                "tenant_id": row["tenant_id"],
                "company_id": row["company_id"],
                "event_type": GrantEventType.KILL_SWITCH_ENGAGED.value,
                "details": json.dumps({"session_id": session_id, "halt_reason": reason}),
                "actor_id": actor_id,
                "actor_type": "HUMAN_OR_SAFETY",
                "timestamp": now,
            })
            if hasattr(conn, "commit"):
                conn.commit()

        logger.warning(f"Session {session_id} HALTED due to: {reason}")
        return True

    @classmethod
    @tenant_scoped
    def verify_and_record_envelope(
        cls,
        session_id: str,
        sequence_no: int,
        timestamp: float,
        nonce: str,
        payload: Dict[str, Any],
        signature_hex: str,
        public_key_hex: str,
    ) -> bool:
        """
        Validates incoming cryptographic envelope:
        1. Checks active session status
        2. Enforces monotonic sequence numbers
        3. Rejects duplicate nonces (anti-replay)
        4. Validates timestamp drift (< 30s)
        5. Verifies Ed25519 digital signature
        """
        now = time.time()
        cls._clean_stale_nonces(now)

        # 1. Active session status
        session = cls.get_session(session_id)
        if not session:
            raise HostSecurityViolation(f"Session {session_id} does not exist.")
        if session.status != HostSessionStatus.ACTIVE:
            raise HostSecurityViolation(f"Session {session_id} is {session.status.value}, cannot process commands.")

        # 2. Monotonic sequence check
        if sequence_no <= session.last_sequence_no:
            raise ReplayDetectedError(
                f"Out-of-order or duplicate sequence number: received {sequence_no}, expected > {session.last_sequence_no}"
            )

        # 3. Nonce anti-replay check
        if nonce in cls._SEEN_NONCES:
            raise ReplayDetectedError(f"Duplicate nonce '{nonce}' detected. Potential replay attack blocked.")
        cls._SEEN_NONCES[nonce] = now

        # 4. Timestamp drift check (30-second window)
        if abs(now - timestamp) > 30.0:
            raise HostSecurityViolation(
                f"Timestamp drift exceeds 30.0s window: current {now:.2f}, packet {timestamp:.2f}"
            )

        # 5. Ed25519 signature verification
        canonical_bytes = cls.canonical_envelope_bytes(session_id, sequence_no, timestamp, nonce, payload)
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            signature_bytes = bytes.fromhex(signature_hex)
            pub_key.verify(signature_bytes, canonical_bytes)
        except (ValueError, TypeError, InvalidSignature) as exc:
            raise HostSecurityViolation(f"Cryptographic signature verification failed: {exc}")

        # Update last sequence number and heartbeat
        update_sql = """
        UPDATE host_sessions
        SET last_sequence_no = :sequence_no,
            last_heartbeat_at = :now
        WHERE session_id = :session_id
        """
        with db.get_connection() as conn:
            conn.execute(update_sql, {"sequence_no": sequence_no, "now": now, "session_id": session_id})
            if hasattr(conn, "commit"):
                conn.commit()

        return True
