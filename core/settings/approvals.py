"""Human approval queue for Settings V2.

Agents may propose.  They may never apply a security, spend, permission, lock,
or secret change.  The AI CEO cannot approve its own proposal or raise its own
limits.  Approvals are append-only in intent: a decision updates the queue row,
and the settings audit chain records the resulting change.

Importing this module is side-effect free.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from core.settings import rbac
from core.settings.errors import NotFoundError, PermissionDenied, ValidationError
from core.settings.models import (
    ActorType,
    ApprovalRequest,
    ApprovalStatus,
    ScopeType,
    SettingDefinition,
)

DEFAULT_EXPIRY_SECONDS = 7 * 24 * 3600


def _row_value(row: Any, index: int, name: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(name)
    try:
        return row[name]
    except (KeyError, IndexError, TypeError):
        return row[index]


def _load_json(raw: Any, fallback: Any = None) -> Any:
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict, int, float, bool)):
        return raw
    try:
        return json.loads(str(raw))
    except Exception:
        return fallback


def _dump_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


class SettingsApprovals:
    def __init__(self, clock: Any = time.time) -> None:
        self._clock = clock

    # --------------------------------------------------------------- helpers
    def _required_approvals(self, definition: SettingDefinition, requested: Optional[int]) -> int:
        if requested is not None:
            return max(1, int(requested))
        if str(definition.risk).upper() == "CRITICAL":
            return 2
        return 1

    def _parse(self, row: Any, definition: Optional[SettingDefinition] = None) -> ApprovalRequest:
        approvals = _load_json(_row_value(row, 12, "approvals_json"), [])
        if not isinstance(approvals, list):
            approvals = []
        try:
            scope = ScopeType(str(_row_value(row, 4, "scope_type")))
        except ValueError:
            scope = ScopeType.COMPANY
        key = str(_row_value(row, 3, "setting_key"))
        proposed_value = _load_json(_row_value(row, 6, "proposed_value"))
        if definition is None:
            from core.settings.registry import settings_registry

            definition = settings_registry.get(key)
        sensitive = bool(definition and definition.sensitive)
        try:
            status = ApprovalStatus(str(_row_value(row, 9, "status")).lower())
        except ValueError:
            status = ApprovalStatus.PENDING
        try:
            actor_type = ActorType(str(_row_value(row, 8, "actor_type")).lower())
        except ValueError:
            actor_type = ActorType.HUMAN

        return ApprovalRequest(
            approval_id=str(_row_value(row, 0, "approval_id")),
            key=key,
            scope_type=scope,
            scope_id=str(_row_value(row, 5, "scope_id")),
            proposed_value=("••••••••" if sensitive else proposed_value),
            proposed_by=str(_row_value(row, 7, "proposed_by")),
            actor_type=actor_type,
            risk=str(_row_value(row, 10, "risk") or "MEDIUM"),
            status=status,
            required_approvals=int(_row_value(row, 11, "required_approvals") or 1),
            approvals=tuple(str(item) for item in approvals),
            reason=str(_row_value(row, 13, "reason") or ""),
            created_at=float(_row_value(row, 14, "created_at") or 0.0),
            expires_at=(
                float(_row_value(row, 15, "expires_at"))
                if _row_value(row, 15, "expires_at") is not None
                else None
            ),
            resolved_at=(
                float(_row_value(row, 16, "resolved_at"))
                if _row_value(row, 16, "resolved_at") is not None
                else None
            ),
            resolved_by=_row_value(row, 17, "resolved_by"),
            decision_reason=_row_value(row, 18, "decision_reason"),
            company_id=_row_value(row, 2, "company_id"),
        )

    def _fetch(self, conn: Any, tenant_id: str, approval_id: str) -> Any:
        return conn.execute(
            """
            SELECT approval_id, tenant_id, company_id, setting_key, scope_type,
                   scope_id, proposed_value, proposed_by, actor_type, status, risk,
                   required_approvals, approvals_json, reason, created_at,
                   expires_at, resolved_at, resolved_by, decision_reason
            FROM settings_approvals
            WHERE tenant_id = ? AND approval_id = ?
            """,
            (tenant_id, approval_id),
        ).fetchone()

    # ---------------------------------------------------------------- create
    def create(
        self,
        conn: Any,
        *,
        tenant_id: str,
        company_id: Optional[str],
        principal: Any,
        definition: SettingDefinition,
        scope_type: ScopeType,
        scope_id: str,
        proposed_value: Any,
        reason: str = "",
        required_approvals: Optional[int] = None,
        expires_in: Optional[int] = DEFAULT_EXPIRY_SECONDS,
        commit: bool = False,
    ) -> ApprovalRequest:
        if not tenant_id or not scope_id:
            raise ValidationError("tenant_id and scope_id are required for an approval.")
        if definition.secret:
            raise ValidationError("Secret values are written directly and are never queued as plaintext approvals.")

        now = float(self._clock())
        expires_at = now + float(expires_in) if expires_in else None
        required = self._required_approvals(definition, required_approvals)
        approval_id = f"apr_{_token()}"
        scope_value = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
        actor_type = principal.actor_type.value if isinstance(principal.actor_type, ActorType) else str(principal.actor_type)

        conn.execute(
            """
            INSERT INTO settings_approvals
                (approval_id, tenant_id, company_id, scope_type, scope_id,
                 setting_key, proposed_value, proposed_by, actor_type, risk,
                 status, required_approvals, approvals_json, reason,
                 decision_reason, created_at, expires_at, resolved_at, resolved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, '[]', ?, NULL, ?, ?, NULL, NULL)
            """,
            (
                approval_id,
                tenant_id,
                company_id,
                scope_value,
                scope_id,
                definition.key,
                _dump_json(proposed_value),
                principal.user_id,
                actor_type,
                str(definition.risk or "MEDIUM").upper(),
                required,
                reason or "",
                now,
                expires_at,
            ),
        )
        if commit:
            conn.commit()
        return ApprovalRequest(
            approval_id=approval_id,
            key=definition.key,
            scope_type=scope_type if isinstance(scope_type, ScopeType) else ScopeType(scope_value),
            scope_id=scope_id,
            proposed_value=proposed_value,
            proposed_by=principal.user_id,
            actor_type=principal.actor_type,
            risk=str(definition.risk or "MEDIUM").upper(),
            status=ApprovalStatus.PENDING,
            required_approvals=required,
            approvals=(),
            reason=reason or "",
            created_at=now,
            expires_at=expires_at,
            company_id=company_id,
        )

    # ----------------------------------------------------------------- decide
    def decide(
        self,
        conn: Any,
        *,
        tenant_id: str,
        approval_id: str,
        principal: Any,
        approve: bool,
        decision_reason: str = "",
        commit: bool = False,
    ) -> Tuple[ApprovalRequest, bool]:
        rbac.require_approver(principal)
        row = self._fetch(conn, tenant_id, approval_id)
        if row is None:
            raise NotFoundError(f"Approval '{approval_id}' was not found.")

        current = self._parse(row)
        if current.status is not ApprovalStatus.PENDING:
            raise PermissionDenied(f"Approval '{approval_id}' is already {current.status.value}.")
        now = float(self._clock())
        if current.expires_at is not None and current.expires_at < now:
            conn.execute(
                "UPDATE settings_approvals SET status = 'EXPIRED', decision_reason = ? WHERE approval_id = ?",
                ("Expired before a decision was recorded.", approval_id),
            )
            if commit:
                conn.commit()
            raise PermissionDenied(f"Approval '{approval_id}' has expired.")

        # Two-person rule: the proposer can never decide their own request.
        if current.proposed_by == principal.user_id:
            raise PermissionDenied("The proposer cannot approve or reject their own request.")

        # The AI CEO may not approve its own class of self-limit change even
        # under a different identity token.
        if rbac.is_ceo_self_limit(current.key) and current.actor_type is ActorType.AGENT:
            raise PermissionDenied("An agent may not decide a change to the AI CEO's own limits.")

        if not approve:
            conn.execute(
                """
                UPDATE settings_approvals
                SET status = 'REJECTED', resolved_at = ?, resolved_by = ?, decision_reason = ?
                WHERE approval_id = ?
                """,
                (now, principal.user_id, decision_reason or "Rejected.", approval_id),
            )
            if commit:
                conn.commit()
            updated = self._parse(self._fetch(conn, tenant_id, approval_id))
            return updated, True

        approvals = list(current.approvals)
        if principal.user_id not in approvals:
            approvals.append(principal.user_id)
        is_final = len(approvals) >= current.required_approvals
        status = ApprovalStatus.APPROVED if is_final else ApprovalStatus.PENDING
        conn.execute(
            """
            UPDATE settings_approvals
            SET status = ?, approvals_json = ?, resolved_at = ?, resolved_by = ?, decision_reason = ?
            WHERE approval_id = ?
            """,
            (
                status.value.upper(),
                _dump_json(approvals),
                now if is_final else None,
                principal.user_id if is_final else None,
                decision_reason or "",
                approval_id,
            ),
        )
        if commit:
            conn.commit()
        updated = self._parse(self._fetch(conn, tenant_id, approval_id))
        return updated, is_final

    # ------------------------------------------------------------------ read
    def get(self, conn: Any, tenant_id: str, approval_id: str) -> ApprovalRequest:
        row = self._fetch(conn, tenant_id, approval_id)
        if row is None:
            raise NotFoundError(f"Approval '{approval_id}' was not found.")
        return self._parse(row)

    def raw_proposed_value(self, conn: Any, tenant_id: str, approval_id: str) -> Any:
        """Return the unstripped proposed value for an approved apply.

        ``to_public_dict`` masks sensitive keys; the apply path needs the real
        value, which never leaves the server.
        """
        row = self._fetch(conn, tenant_id, approval_id)
        if row is None:
            raise NotFoundError(f"Approval '{approval_id}' was not found.")
        return _load_json(_row_value(row, 6, "proposed_value"))

    def list(
        self,
        conn: Any,
        tenant_id: str,
        company_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        query = """
            SELECT approval_id, tenant_id, company_id, setting_key, scope_type,
                   scope_id, proposed_value, proposed_by, actor_type, status, risk,
                   required_approvals, approvals_json, reason, created_at,
                   expires_at, resolved_at, resolved_by, decision_reason
            FROM settings_approvals WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if company_id:
            # Tenant-wide proposals have no company id and are relevant to
            # every company in the tenant.
            query += " AND (company_id = ? OR company_id IS NULL)"
            params.append(company_id)
        if status:
            query += " AND status = ?"
            params.append(str(status).upper())
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit or 100), 1000)))
        rows = conn.execute(query, tuple(params)).fetchall()
        return [self._parse(row) for row in rows]

    def expire_stale(self, conn: Any, tenant_id: str) -> int:
        now = float(self._clock())
        cursor = conn.execute(
            """
            UPDATE settings_approvals
            SET status = 'EXPIRED', decision_reason = 'Expired without a decision.'
            WHERE tenant_id = ? AND status = 'PENDING' AND expires_at IS NOT NULL AND expires_at < ?
            """,
            (tenant_id, now),
        )
        return int(getattr(cursor, "rowcount", 0) or 0)


def _token() -> str:
    import uuid

    return uuid.uuid4().hex


settings_approvals = SettingsApprovals()
