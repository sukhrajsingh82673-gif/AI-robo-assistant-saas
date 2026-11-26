"""
ZONATA Human Inbox & Notification Engine
Manages tasks requiring human attention, approvals, escalations, reminders,
and durable acknowledgement/resolution tracking.
"""

from __future__ import annotations

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from core.db import db
from core.ports.email import resolve_email_provider, EmailMessage
from core.work.types import (
    InboxItemType,
    InboxStatus,
    InboxItemNotFoundError,
)

logger = logging.getLogger("zonata.work.inbox")


class HumanInboxService:
    """
    Manages durable inbox items for human intervention, approvals, and escalations.
    """

    @classmethod
    def create_item(
        cls,
        tenant_id: str,
        company_id: str,
        item_type: InboxItemType,
        title: str,
        context_data: Dict[str, Any],
        target_principal_type: str,
        target_principal_id: str,
        decision_needed: str,
        task_id: Optional[str] = None,
        due_date_ts: Optional[float] = None,
        recipient_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a durable human inbox item, persisting to the database and
        dispatching notification via the email port.
        """
        inbox_id = f"inb_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO human_inbox (
                    id, tenant_id, company_id, task_id, item_type, title,
                    context_data, target_principal_type, target_principal_id,
                    decision_needed, status, due_date_ts, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inbox_id, tenant_id, company_id, task_id,
                    item_type.value if isinstance(item_type, InboxItemType) else str(item_type),
                    title, json.dumps(context_data),
                    target_principal_type, target_principal_id,
                    decision_needed, InboxStatus.PENDING.value,
                    due_date_ts, now, now
                )
            )
            conn.commit()

        # Send notification email via EmailPort
        target_email = recipient_email or f"{target_principal_id.lower()}@zonata.internal"
        try:
            email_port = resolve_email_provider()
            subject = f"[{item_type.value}] Action Required: {title}"
            body_text = (
                f"Human intervention required for company '{company_id}'.\n\n"
                f"Task ID: {task_id or 'N/A'}\n"
                f"Item Type: {item_type.value}\n"
                f"Title: {title}\n"
                f"Decision/Deliverable Needed: {decision_needed}\n"
                f"Due Date: {due_date_ts}\n\n"
                f"Context:\n{json.dumps(context_data, indent=2)}\n"
            )
            email_port.send(
                to=[target_email],
                subject=subject,
                body=body_text,
                metadata={"inbox_id": inbox_id, "task_id": task_id, "tenant_id": tenant_id}
            )
        except Exception as e:
            logger.warning(f"Could not dispatch email notification for inbox item {inbox_id}: {e}")

        return cls.get_item(tenant_id, company_id, inbox_id)

    @classmethod
    def get_item(cls, tenant_id: str, company_id: str, inbox_id: str) -> Dict[str, Any]:
        """Fetches a specific inbox item."""
        with db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, tenant_id, company_id, task_id, item_type, title,
                       context_data, target_principal_type, target_principal_id,
                       decision_needed, status, due_date_ts, acknowledged_at,
                       acknowledged_by, resolved_at, resolved_by, resolution_data,
                       created_at, updated_at
                FROM human_inbox
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (inbox_id, tenant_id, company_id)
            ).fetchone()

        if not row:
            raise InboxItemNotFoundError(f"Inbox item '{inbox_id}' not found.")

        data = dict(row)
        if data.get("context_data") and isinstance(data["context_data"], str):
            try:
                data["context_data"] = json.loads(data["context_data"])
            except Exception:
                pass
        if data.get("resolution_data") and isinstance(data["resolution_data"], str):
            try:
                data["resolution_data"] = json.loads(data["resolution_data"])
            except Exception:
                pass
        return data

    @classmethod
    def list_items(
        cls,
        tenant_id: str,
        company_id: str,
        target_principal_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists inbox items matching optional filters."""
        query = "SELECT id, tenant_id, company_id, task_id, item_type, title, context_data, target_principal_type, target_principal_id, decision_needed, status, due_date_ts, acknowledged_at, acknowledged_by, resolved_at, resolved_by, resolution_data, created_at, updated_at FROM human_inbox WHERE tenant_id = ? AND company_id = ?"
        params: List[Any] = [tenant_id, company_id]

        if target_principal_id:
            query += " AND target_principal_id = ?"
            params.append(target_principal_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        with db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            if d.get("context_data") and isinstance(d["context_data"], str):
                try:
                    d["context_data"] = json.loads(d["context_data"])
                except Exception:
                    pass
            results.append(d)
        return results

    @classmethod
    def acknowledge(
        cls,
        tenant_id: str,
        company_id: str,
        inbox_id: str,
        actor_id: str,
    ) -> Dict[str, Any]:
        """Records human acknowledgement of an inbox item."""
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT id, status FROM human_inbox WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (inbox_id, tenant_id, company_id)
            ).fetchone()
            if not row:
                raise InboxItemNotFoundError(f"Inbox item '{inbox_id}' not found.")

            conn.execute(
                """
                UPDATE human_inbox
                SET status = ?, acknowledged_at = ?, acknowledged_by = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (InboxStatus.ACKNOWLEDGED.value, now, actor_id, now, inbox_id, tenant_id, company_id)
            )
            conn.commit()

        return cls.get_item(tenant_id, company_id, inbox_id)

    @classmethod
    def resolve(
        cls,
        tenant_id: str,
        company_id: str,
        inbox_id: str,
        actor_id: str,
        resolution_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolves an inbox item with human decision data."""
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT id, status FROM human_inbox WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (inbox_id, tenant_id, company_id)
            ).fetchone()
            if not row:
                raise InboxItemNotFoundError(f"Inbox item '{inbox_id}' not found.")

            conn.execute(
                """
                UPDATE human_inbox
                SET status = ?, resolved_at = ?, resolved_by = ?, resolution_data = ?, updated_at = ?
                WHERE id = ? AND tenant_id = ? AND company_id = ?
                """,
                (InboxStatus.RESOLVED.value, now, actor_id, json.dumps(resolution_data), now, inbox_id, tenant_id, company_id)
            )
            conn.commit()

        return cls.get_item(tenant_id, company_id, inbox_id)


human_inbox_service = HumanInboxService()
