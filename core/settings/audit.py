"""Append-only, hash-chained audit writer for Settings V2.

Every settings mutation is recorded once and never updated.  The database
enforces that with triggers (SQLite) or rules (PostgreSQL); this module is the
single writer and adds a per-tenant SHA-256 hash chain on top.

The module is intentionally storage-light: it accepts an open connection and
never commits unless explicitly asked, so the caller can make a value write and
its audit row part of the same transaction.

Importing this module is side-effect free.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence

from core.settings.errors import ValidationError

REDACTED = "••••••••"

AUDIT_COLUMNS = (
    "audit_id",
    "tenant_id",
    "company_id",
    "scope_type",
    "scope_id",
    "setting_key",
    "old_value",
    "new_value",
    "actor",
    "actor_type",
    "reason",
    "request_id",
    "ip_address",
    "version",
    "approval_status",
    "previous_hash",
    "entry_hash",
    "created_at",
)


def _row_value(row: Any, index: int, name: str) -> Any:
    """Read a column from sqlite3.Row, a dict-like row, or a tuple."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(name)
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return row[index]


def _row_to_dict(row: Any) -> Dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, dict):
        return dict(row)
    return {name: _row_value(row, index, name) for index, name in enumerate(AUDIT_COLUMNS)}


def serialize_value(value: Any) -> Optional[str]:
    """Canonical JSON for an audit value.  ``None`` stays ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return str(value)


def canonical_payload(record: Dict[str, Any]) -> str:
    """Stable byte representation of one audit event.

    The entry hash binds every stored field except the hash fields themselves,
    so a change to any value, actor, scope, or timestamp breaks verification.
    """
    payload = {
        "audit_id": record["audit_id"],
        "tenant_id": record["tenant_id"],
        "company_id": record.get("company_id"),
        "scope_type": record["scope_type"],
        "scope_id": record["scope_id"],
        "setting_key": record["setting_key"],
        "old_value": record.get("old_value"),
        "new_value": record.get("new_value"),
        "actor": record["actor"],
        "actor_type": record.get("actor_type") or "human",
        "reason": record.get("reason"),
        "request_id": record.get("request_id"),
        "ip_address": record.get("ip_address"),
        "version": int(record.get("version") or 1),
        "approval_status": record.get("approval_status") or "APPROVED",
        "created_at": float(record["created_at"]),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(previous_hash: Optional[str], record: Dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update((previous_hash or "").encode("utf-8"))
    digest.update(canonical_payload(record).encode("utf-8"))
    return digest.hexdigest()


class SettingsAudit:
    """Write and read the append-only settings audit chain."""

    def __init__(self, clock: Any = time.time) -> None:
        self._clock = clock

    # ---------------------------------------------------------------- writes
    def write(
        self,
        conn: Any,
        *,
        tenant_id: str,
        company_id: Optional[str],
        scope_type: str,
        scope_id: str,
        setting_key: str,
        actor: str,
        old_value: Any = None,
        new_value: Any = None,
        actor_type: str = "human",
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        version: int = 1,
        approval_status: str = "APPROVED",
        sensitive: bool = False,
        audit_id: Optional[str] = None,
        commit: bool = False,
    ) -> Dict[str, Any]:
        if not tenant_id:
            raise ValidationError("tenant_id is required for an audit event.")
        if not actor:
            raise ValidationError("actor is required for an audit event.")
        if not setting_key:
            raise ValidationError("setting_key is required for an audit event.")

        created_at = self._next_created_at(conn, str(tenant_id))
        record: Dict[str, Any] = {
            "audit_id": audit_id or f"evt_{uuid.uuid4().hex}",
            "tenant_id": str(tenant_id),
            "company_id": str(company_id) if company_id else None,
            "scope_type": str(scope_type),
            "scope_id": str(scope_id),
            "setting_key": str(setting_key),
            "old_value": REDACTED if sensitive and old_value is not None else serialize_value(old_value),
            "new_value": REDACTED if sensitive and new_value is not None else serialize_value(new_value),
            "actor": str(actor),
            "actor_type": str(actor_type or "human"),
            "reason": reason,
            "request_id": request_id,
            "ip_address": ip_address,
            "version": int(version or 1),
            "approval_status": str(approval_status or "APPROVED").upper(),
            "created_at": created_at,
            "previous_hash": None,
            "entry_hash": "",
        }
        record["previous_hash"] = self._last_hash(conn, record["tenant_id"])
        record["entry_hash"] = compute_entry_hash(record["previous_hash"], record)

        conn.execute(
            """
            INSERT INTO settings_audit
                (audit_id, tenant_id, company_id, scope_type, scope_id,
                 setting_key, old_value, new_value, actor, actor_type, reason,
                 request_id, ip_address, version, approval_status,
                 previous_hash, entry_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["audit_id"],
                record["tenant_id"],
                record["company_id"],
                record["scope_type"],
                record["scope_id"],
                record["setting_key"],
                record["old_value"],
                record["new_value"],
                record["actor"],
                record["actor_type"],
                record["reason"],
                record["request_id"],
                record["ip_address"],
                record["version"],
                record["approval_status"],
                record["previous_hash"],
                record["entry_hash"],
                record["created_at"],
            ),
        )
        if commit:
            conn.commit()
        return record

    def _next_created_at(self, conn: Any, tenant_id: str) -> float:
        """Return a timestamp strictly greater than the tenant's last event.

        The hash chain is ordered by ``created_at``.  If two events share a
        timestamp, their order becomes ambiguous and verification can report a
        false break.  A frozen or coarse clock must not be able to fork the
        chain, so the stored maximum wins over the wall clock.
        """
        row = conn.execute(
            "SELECT MAX(created_at) FROM settings_audit WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        last = float(_row_value(row, 0, "created_at") or 0.0) if row is not None else 0.0
        now = float(self._clock())
        return now if now > last else last + 0.000001

    def _last_hash(self, conn: Any, tenant_id: str) -> Optional[str]:
        row = conn.execute(
            """
            SELECT entry_hash FROM settings_audit
            WHERE tenant_id = ?
            ORDER BY created_at DESC, audit_id DESC
            LIMIT 1
            """,
            (tenant_id,),
        ).fetchone()
        value = _row_value(row, 0, "entry_hash") if row is not None else None
        return str(value) if value else None

    # ----------------------------------------------------------------- reads
    def list_events(
        self,
        conn: Any,
        tenant_id: str,
        company_id: Optional[str] = None,
        setting_key: Optional[str] = None,
        actor: Optional[str] = None,
        actor_type: Optional[str] = None,
        from_ts: Optional[float] = None,
        to_ts: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if not tenant_id:
            raise ValidationError("tenant_id is required to read the audit log.")
        limit = max(1, min(int(limit or 100), 1000))
        query = f"SELECT {', '.join(AUDIT_COLUMNS)} FROM settings_audit WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]
        # Company scope is a hard boundary: a Company A reader never sees
        # Company B rows.  Platform and organization events carry no company
        # id; they affect every company and are included in each company view.
        if company_id:
            query += " AND (company_id = ? OR company_id IS NULL)"
            params.append(company_id)
        if setting_key:
            query += " AND setting_key = ?"
            params.append(setting_key)
        if actor:
            query += " AND actor = ?"
            params.append(actor)
        if actor_type:
            query += " AND actor_type = ?"
            params.append(actor_type)
        if from_ts is not None:
            query += " AND created_at >= ?"
            params.append(float(from_ts))
        if to_ts is not None:
            query += " AND created_at <= ?"
            params.append(float(to_ts))
        query += " ORDER BY created_at DESC, audit_id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
        return [_row_to_dict(row) for row in rows]

    def verify_chain(self, conn: Any, tenant_id: str) -> Dict[str, Any]:
        """Recompute the per-tenant chain and report the first broken link."""
        rows = conn.execute(
            f"""
            SELECT {', '.join(AUDIT_COLUMNS)} FROM settings_audit
            WHERE tenant_id = ?
            ORDER BY created_at ASC, audit_id ASC
            """,
            (tenant_id,),
        ).fetchall()
        previous: Optional[str] = None
        checked = 0
        for row in rows:
            record = _row_to_dict(row)
            expected = compute_entry_hash(previous, record)
            if str(record.get("previous_hash") or "") != str(previous or ""):
                return {
                    "ok": False,
                    "tenant_id": tenant_id,
                    "checked": checked,
                    "broken_at": record.get("audit_id"),
                    "reason": "previous_hash does not match the prior entry",
                }
            if expected != record.get("entry_hash"):
                return {
                    "ok": False,
                    "tenant_id": tenant_id,
                    "checked": checked,
                    "broken_at": record.get("audit_id"),
                    "reason": "entry_hash does not match the stored event",
                }
            previous = str(record.get("entry_hash"))
            checked += 1
        return {"ok": True, "tenant_id": tenant_id, "checked": checked, "broken_at": None, "reason": None}

    # ------------------------------------------------------------- revisions
    def bump_revision(self, conn: Any, tenant_id: str) -> int:
        """Increment and return the per-tenant settings revision."""
        now = float(self._clock())
        conn.execute(
            """
            INSERT INTO settings_revision (tenant_id, revision, updated_at)
            VALUES (?, 1, ?)
            ON CONFLICT (tenant_id) DO UPDATE SET
                revision = settings_revision.revision + 1,
                updated_at = excluded.updated_at
            """,
            (tenant_id, now),
        )
        row = conn.execute(
            "SELECT revision FROM settings_revision WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        return int(_row_value(row, 0, "revision") or 0)

    def current_revision(self, conn: Any, tenant_id: str) -> int:
        row = conn.execute(
            "SELECT revision FROM settings_revision WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        return int(_row_value(row, 0, "revision") or 0)


settings_audit = SettingsAudit()
