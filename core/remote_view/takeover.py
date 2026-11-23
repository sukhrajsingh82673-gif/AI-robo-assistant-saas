"""
ZONATA Remote View — Human Takeover Manager (Rule 25, Rule 27).

Coordinates human takeover protocol:
1. When human activates takeover, agent commands are instantly suppressed.
2. Human completes action (e.g. solves challenge, completes MFA).
3. Human releases takeover with an explicit state assertion.
4. Complete audit logging in human_takeover_events.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from core.remote_view.types import (
    AgentExecutionSuppressedError,
    RemoteTargetType,
    TakeoverEventType,
    TakeoverHandbackAssertion,
    TakeoverState,
    ViewportBounds,
)


class HumanTakeoverManager:
    """
    Manages session states, human takeover coordination, and audit events.
    """

    def __init__(self, db_conn: Optional[sqlite3.Connection] = None):
        self.db = db_conn or sqlite3.connect(":memory:")
        self._init_db()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def _init_db(self) -> None:
        cur = self.db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS remote_view_sessions (
                session_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                stream_protocol TEXT NOT NULL DEFAULT 'WEBSOCKET_MJPEG',
                viewport_bounds TEXT NOT NULL,
                mask_regions TEXT DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS human_takeover_events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                human_principal_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                handback_state_assertion TEXT,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES remote_view_sessions(session_id)
            );
        """)
        self.db.commit()

    def create_session(
        self,
        tenant_id: str,
        company_id: str,
        target_type: RemoteTargetType,
        target_id: str,
        viewport: ViewportBounds,
    ) -> str:
        """Create a new remote view session."""
        session_id = f"rv_sess_{uuid.uuid4().hex[:12]}"
        bounds_json = json.dumps(viewport.to_dict())

        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO remote_view_sessions (
                session_id, tenant_id, company_id, target_type, target_id, viewport_bounds
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, tenant_id, company_id, target_type.value, target_id, bounds_json))
        self.db.commit()

        self._active_sessions[session_id] = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "target_type": target_type,
            "target_id": target_id,
            "viewport": viewport,
            "state": TakeoverState.AGENT_ACTIVE,
            "active_principal": None,
        }
        return session_id

    def initiate_takeover(self, session_id: str, human_principal_id: str) -> None:
        """Human owner takes over control of session."""
        session = self._active_sessions.get(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")

        session["state"] = TakeoverState.HUMAN_TAKEOVER_ACTIVE
        session["active_principal"] = human_principal_id

        # Record audit event
        event_id = f"evt_to_{uuid.uuid4().hex[:12]}"
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO human_takeover_events (
                event_id, session_id, tenant_id, company_id, human_principal_id, event_type
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            session_id,
            session["tenant_id"],
            session["company_id"],
            human_principal_id,
            TakeoverEventType.TAKEOVER_INITIATED.value,
        ))
        self.db.commit()

    def assert_agent_permitted(self, session_id: str) -> None:
        """Verify whether agent is allowed to execute actions."""
        session = self._active_sessions.get(session_id)
        if not session:
            return  # session unknown or closed, default gate handled upstream

        if session["state"] == TakeoverState.HUMAN_TAKEOVER_ACTIVE:
            raise AgentExecutionSuppressedError(
                f"Agent commands suppressed on session '{session_id}': Human principal '{session['active_principal']}' currently has control."
            )

    def release_takeover_with_assertion(
        self,
        assertion: TakeoverHandbackAssertion,
    ) -> None:
        """Human completes action and returns control with explicit assertion."""
        session = self._active_sessions.get(assertion.session_id)
        if not session:
            raise KeyError(f"Session '{assertion.session_id}' not found.")

        session["state"] = TakeoverState.AGENT_ACTIVE
        session["active_principal"] = None

        # Record audit event with assertion
        event_id = f"evt_to_{uuid.uuid4().hex[:12]}"
        cur = self.db.cursor()
        cur.execute("""
            INSERT INTO human_takeover_events (
                event_id, session_id, tenant_id, company_id, human_principal_id, event_type, handback_state_assertion
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            assertion.session_id,
            session["tenant_id"],
            session["company_id"],
            assertion.human_principal_id,
            TakeoverEventType.CONTROL_RELEASED.value,
            json.dumps(assertion.to_dict()),
        ))
        self.db.commit()

    def close_session(self, session_id: str) -> None:
        """Close remote view session."""
        if session_id in self._active_sessions:
            self._active_sessions[session_id]["state"] = TakeoverState.SESSION_CLOSED

        cur = self.db.cursor()
        cur.execute("""
            UPDATE remote_view_sessions
            SET is_active = 0, closed_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        self.db.commit()

    def get_events(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve audit history for session."""
        cur = self.db.cursor()
        cur.execute("""
            SELECT event_id, session_id, human_principal_id, event_type, handback_state_assertion, recorded_at
            FROM human_takeover_events
            WHERE session_id = ?
            ORDER BY recorded_at ASC
        """, (session_id,))
        rows = cur.fetchall()
        return [
            {
                "event_id": r[0],
                "session_id": r[1],
                "human_principal_id": r[2],
                "event_type": r[3],
                "handback_state_assertion": json.loads(r[4]) if r[4] else None,
                "recorded_at": r[5],
            }
            for r in rows
        ]
