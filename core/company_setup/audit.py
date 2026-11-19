"""Company audit trail.

Every sensitive company action (create, update, submit, connect, disconnect,
status change, delete step, purge) is appended here. The detail payload is
scrubbed so credentials never reach the audit log.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from core.db import db

SENSITIVE_KEYS = (
    "password",
    "passcode",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "private_key",
    "ciphertext",
    "nonce",
    "two_step_code",
    "otp",
)

MAX_DETAIL_CHARS = 4000
MAX_STRING_CHARS = 500


def _scrub(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if any(marker in key_str.lower() for marker in SENSITIVE_KEYS):
                cleaned[key_str] = "[redacted]"
            else:
                cleaned[key_str] = _scrub(item, depth + 1)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_scrub(item, depth + 1) for item in list(value)[:50]]
    if isinstance(value, str):
        return value[:MAX_STRING_CHARS]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:MAX_STRING_CHARS]


def _json_load(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def record_event(
    tenant_id: str,
    company_id: Optional[str],
    actor_id: str,
    actor_role: str,
    action: str,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Append an audit event and return the stored record."""
    event = {
        "event_id": f"cae_{uuid.uuid4().hex[:16]}",
        "tenant_id": tenant_id,
        "company_id": company_id,
        "actor_id": actor_id or "usr_unknown",
        "actor_role": (actor_role or "UNKNOWN").upper(),
        "action": action,
        "detail": _scrub(detail or {}),
        "created_at": time.time(),
    }
    payload = json.dumps(event["detail"])
    if len(payload) > MAX_DETAIL_CHARS:
        event["detail"] = {"truncated": True, "action": action}
        payload = json.dumps(event["detail"])
    with db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO company_audit_events
                (event_id, tenant_id, company_id, actor_id, actor_role, action, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                tenant_id,
                company_id,
                event["actor_id"],
                event["actor_role"],
                action,
                payload,
                event["created_at"],
            ),
        )
        conn.commit()
    return event


def list_events(
    tenant_id: str,
    company_id: str,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 50), 200))
    safe_offset = max(0, int(offset or 0))
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_id, company_id, actor_id, actor_role, action, detail, created_at
            FROM company_audit_events
            WHERE tenant_id = ? AND company_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (tenant_id, company_id, safe_limit, safe_offset),
        ).fetchall()
    events: List[Dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "event_id": row["event_id"],
                "company_id": row["company_id"],
                "actor_id": row["actor_id"],
                "actor_role": row["actor_role"],
                "action": row["action"],
                "detail": _json_load(row["detail"], {}),
                "created_at": row["created_at"],
            }
        )
    return events


def count_events(tenant_id: str, company_id: str) -> int:
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM company_audit_events WHERE tenant_id = ? AND company_id = ?",
            (tenant_id, company_id),
        ).fetchone()
    return int(row["n"] if row else 0)


def purge_events(tenant_id: str, company_id: str, keep_final: bool = True) -> int:
    """Remove audit detail on purge while keeping the minimal final record.

    The final record is written by the deletion flow before this runs, so the
    company never disappears without a trace.
    """
    with db.get_connection() as conn:
        if keep_final:
            cursor = conn.execute(
                "DELETE FROM company_audit_events WHERE tenant_id = ? AND company_id = ? AND action <> 'company.purged'",
                (tenant_id, company_id),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM company_audit_events WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id),
            )
        conn.commit()
        return int(getattr(cursor, "rowcount", 0) or 0)
