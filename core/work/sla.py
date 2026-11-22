"""
ZONATA Task SLA & Escalation Engine
Monitors task SLAs, handles controllable time in tests, and drives the 3-tier escalation ladder:
Assignee's Supervisor -> CEO -> Owner.
"""

from __future__ import annotations

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

from core.db import db
from core.organization.service import organization_service
from core.evidence_service import evidence_service
from core.work.inbox import human_inbox_service
from core.work.types import InboxItemType

logger = logging.getLogger("zonata.work.sla")


class ClockManager:
    """Provides controllable time for testing deterministic timers and SLAs."""
    _time_override: Optional[float] = None

    @classmethod
    def now(cls) -> float:
        if cls._time_override is not None:
            return cls._time_override
        return time.time()

    @classmethod
    def set_time(cls, ts: float) -> None:
        cls._time_override = ts

    @classmethod
    def advance_time(cls, seconds: float) -> float:
        if cls._time_override is None:
            cls._time_override = time.time()
        cls._time_override += seconds
        return cls._time_override

    @classmethod
    def reset(cls) -> None:
        cls._time_override = None

    @classmethod
    @contextmanager
    def controllable_clock(cls, start_time: Optional[float] = None):
        previous = cls._time_override
        cls._time_override = start_time if start_time is not None else time.time()
        try:
            yield cls
        finally:
            cls._time_override = previous


class WorkSLAService:
    """
    Evaluates active task deadlines and executes deterministic SLA escalations.
    """

    @classmethod
    def check_and_escalate_slas(
        cls,
        tenant_id: str,
        company_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Scans for breached task SLAs and escalates up the organizational chain:
        Level 1: Supervisor position
        Level 2: CEO position
        Level 3: Company Owner
        """
        current_ts = ClockManager.now()
        escalated_records: List[Dict[str, Any]] = []

        with db.get_connection() as conn:
            breached_tasks = conn.execute(
                """
                SELECT id, title, owner_id, assignee_type, assignee_id, status,
                       sla_seconds, deadline_ts, sla_expires_at, sla_escalation_level
                FROM work_tasks
                WHERE tenant_id = ? AND company_id = ?
                  AND status IN ('ASSIGNED', 'ACCEPTED', 'IN_PROGRESS', 'SUBMITTED', 'VERIFYING')
                  AND sla_expires_at IS NOT NULL
                  AND sla_expires_at < ?
                """,
                (tenant_id, company_id, current_ts)
            ).fetchall()

        for t in breached_tasks:
            task_id = t["id"]
            current_level = t["sla_escalation_level"] or 0
            next_level = current_level + 1
            assignee_id = t["assignee_id"]

            # Determine escalation target
            target_type = "POSITION"
            target_id = ""

            if next_level == 1:
                # Level 1: Direct supervisor position
                supervisor = None
                if assignee_id:
                    supervisor = organization_service.get_supervisor(tenant_id, company_id, assignee_id)
                if supervisor:
                    target_id = supervisor if isinstance(supervisor, str) else supervisor.get("position_id")
                else:
                    # Fallback to CEO if no direct supervisor
                    ceo = organization_service.get_ceo(tenant_id, company_id)
                    target_id = ceo["position_id"] if ceo else "pos_ceo"

            elif next_level == 2:
                # Level 2: CEO position
                ceo = organization_service.get_ceo(tenant_id, company_id)
                target_id = ceo["position_id"] if ceo else "pos_ceo"

            else:
                # Level 3+: Company Owner
                target_type = "OWNER"
                target_id = "principal_owner"

            # Update task escalation level and extend SLA window to prevent re-triggering within interval
            # Extend SLA deadline by original sla_seconds (or default 3600s) for next escalation
            interval = t["sla_seconds"] or 3600
            new_expires_at = current_ts + interval

            with db.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE work_tasks
                    SET sla_escalation_level = ?, sla_expires_at = ?, updated_at = ?
                    WHERE id = ? AND tenant_id = ? AND company_id = ?
                    """,
                    (next_level, new_expires_at, current_ts, task_id, tenant_id, company_id)
                )

                # Record task event
                event_id = f"ev_task_{uuid.uuid4().hex[:12]}"
                event_details = {
                    "escalation_level": next_level,
                    "target_type": target_type,
                    "target_id": target_id,
                    "breached_at": current_ts,
                    "previous_level": current_level,
                }
                conn.execute(
                    """
                    INSERT INTO task_events (
                        id, tenant_id, company_id, task_id, event_type,
                        from_status, to_status, actor_type, actor_id, details, timestamp
                    ) VALUES (?, ?, ?, ?, 'SLA_BREACH_ESCALATED', ?, ?, 'SYSTEM', 'sla_service', ?, ?)
                    """,
                    (
                        event_id, tenant_id, company_id, task_id,
                        t["status"], t["status"], json.dumps(event_details), current_ts
                    )
                )
                conn.commit()

            # Create Human Inbox item
            inbox_item = human_inbox_service.create_item(
                tenant_id=tenant_id,
                company_id=company_id,
                item_type=InboxItemType.SLA_ESCALATION,
                title=f"SLA Breach Escalation (Level {next_level}): {t['title']}",
                context_data={
                    "task_id": task_id,
                    "task_title": t["title"],
                    "assignee_id": assignee_id,
                    "escalation_level": next_level,
                    "breached_at": current_ts,
                },
                target_principal_type=target_type,
                target_principal_id=target_id,
                decision_needed=f"Intervene or reassign task '{task_id}' due to SLA breach at escalation level {next_level}.",
                task_id=task_id,
                due_date_ts=current_ts + 86400.0,
            )

            # Record in Merkle Evidence Ledger
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="WORK_TASK_SLA_ESCALATED",
                payload={
                    "task_id": task_id,
                    "escalation_level": next_level,
                    "target_type": target_type,
                    "target_id": target_id,
                    "inbox_id": inbox_item["id"],
                },
                action_id=f"sla_esc_{task_id}_{next_level}"
            )

            escalated_records.append({
                "task_id": task_id,
                "escalation_level": next_level,
                "target_type": target_type,
                "target_id": target_id,
                "inbox_id": inbox_item["id"],
            })

        return escalated_records


work_sla_service = WorkSLAService()
