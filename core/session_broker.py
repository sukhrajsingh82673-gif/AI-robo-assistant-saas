"""
RoboAssistant Company OS 2.0 — Governed Session Broker
Manages application, CLI, and browser profile sessions. Supports MFA interactions
by entering WAITING_FOR_OWNER states rather than attempting security bypass.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
from .db import db
from .credential_broker import CredentialBroker, CredentialStatus

class SessionStatus:
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    WAITING_FOR_OWNER = "WAITING_FOR_OWNER"

class SessionBroker:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"
        self.cred_broker = CredentialBroker(tenant_id, company_id)

    def create_session(self, handle_id: str, host_id: str, session_type: str = "BROWSER", duration_seconds: int = 3600) -> Dict[str, Any]:
        """
        Initiates a session using an approved credential handle.
        """
        with db.get_connection() as conn:
            handle = conn.execute(
                "SELECT * FROM credential_handles WHERE handle_id = ?",
                (handle_id,)
            ).fetchone()

        if not handle or handle["status"] != CredentialStatus.ACTIVE:
            return {
                "success": False,
                "error": f"Credential handle '{handle_id}' is invalid or not active"
            }

        session_id = f"sess_{session_type.lower()}_{uuid.uuid4().hex[:8]}"
        now = time.time()
        expires_at = now + duration_seconds

        # If MFA is required, session enters WAITING_FOR_OWNER
        status = SessionStatus.WAITING_FOR_OWNER if handle["mfa_required"] else SessionStatus.ACTIVE

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO active_sessions (
                    session_id, handle_id, host_id, session_type, status, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, handle_id, host_id, session_type, status, expires_at, now)
            )
            conn.commit()

        return {
            "success": True,
            "session_id": session_id,
            "handle_id": handle_id,
            "host_id": host_id,
            "status": status,
            "expires_at": expires_at,
            "mfa_required": bool(handle["mfa_required"]),
            "requires_owner_intervention": (status == SessionStatus.WAITING_FOR_OWNER)
        }

    def verify_and_complete_mfa(self, session_id: str) -> bool:
        """Owner confirms MFA / token approval."""
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE active_sessions SET status = 'ACTIVE' WHERE session_id = ? AND status = 'WAITING_FOR_OWNER'",
                (session_id,)
            )
            conn.commit()
            return True

    def terminate_session(self, session_id: str) -> bool:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE active_sessions SET status = 'TERMINATED' WHERE session_id = ?",
                (session_id,)
            )
            conn.commit()
            return True

    def list_active_sessions(self, host_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            if host_id:
                rows = conn.execute(
                    "SELECT * FROM active_sessions WHERE host_id = ? AND status = 'ACTIVE' AND expires_at > ?",
                    (host_id, time.time())
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM active_sessions WHERE status = 'ACTIVE' AND expires_at > ?",
                    (time.time(),)
                ).fetchall()
            return [dict(r) for r in rows]
