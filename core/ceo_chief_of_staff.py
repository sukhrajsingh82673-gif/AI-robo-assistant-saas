"""
RoboAssistant Company OS 2.0 — AI Chief of Staff
Coordinates the executive inbox, decision queue, cross-department alignment,
deadline tracking, follow-ups, and executive operating priorities.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
from .db import db
from .models import MissionStatus

class ChiefOfStaff:
    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"

    def add_inbox_item(self, item_type: str, title: str, details: str, priority: str = "MEDIUM") -> str:
        item_id = f"cos_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO chief_of_staff_items (
                    item_id, tenant_id, company_id, item_type, title, details, priority, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """,
                (item_id, self.tenant_id, self.company_id, item_type, title, details, priority, time.time())
            )
            conn.commit()
        return item_id

    def list_items(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM chief_of_staff_items WHERE company_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                    (self.company_id, status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM chief_of_staff_items WHERE company_id = ? ORDER BY created_at DESC LIMIT ?",
                    (self.company_id, limit)
                ).fetchall()
            return [dict(r) for r in rows]

    def resolve_item(self, item_id: str, resolution_notes: str = "") -> bool:
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE chief_of_staff_items SET status = 'RESOLVED', details = details || ' | Resolution: ' || ?, resolved_at = ? WHERE item_id = ?",
                (resolution_notes, time.time(), item_id)
            )
            conn.commit()
            return True

    def compile_executive_dossier(self) -> Dict[str, Any]:
        """
        Compiles the complete executive queue:
        - Critical unhandled events
        - Open owner approvals
        - Deadlines & active missions
        - Department coordination conflicts
        """
        with db.get_connection() as conn:
            # 1. Open items from CoS queue
            cos_open = conn.execute(
                "SELECT * FROM chief_of_staff_items WHERE company_id = ? AND status = 'OPEN' ORDER BY priority DESC",
                (self.company_id,)
            ).fetchall()

            # 2. Pending approvals
            pending_approvals = conn.execute(
                "SELECT * FROM approvals WHERE company_id = ? AND status = 'PENDING'",
                (self.company_id,)
            ).fetchall()

            # 3. Active missions
            active_missions = conn.execute(
                "SELECT * FROM missions WHERE company_id = ? AND status NOT IN ('SUCCESS', 'FAILED')",
                (self.company_id,)
            ).fetchall()

            # 4. Unhandled events
            unhandled_events = conn.execute(
                "SELECT * FROM enterprise_events WHERE company_id = ? AND handled = 0 ORDER BY created_at DESC LIMIT 5",
                (self.company_id,)
            ).fetchall()

        return {
            "company_id": self.company_id,
            "timestamp": time.time(),
            "chief_of_staff_queue": [dict(r) for r in cos_open],
            "pending_approvals_count": len(pending_approvals),
            "pending_approvals": [dict(r) for r in pending_approvals],
            "active_missions_count": len(active_missions),
            "active_missions": [dict(r) for r in active_missions],
            "unhandled_events_count": len(unhandled_events),
            "unhandled_events": [dict(r) for r in unhandled_events],
            "executive_summary": (
                f"{len(unhandled_events)} unhandled events, "
                f"{len(pending_approvals)} approvals waiting for owner, "
                f"{len(active_missions)} missions actively progressing."
            )
        }
