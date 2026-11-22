"""
ZONATA Host Grant Manager
=========================
OpenCode Step 3B: Host grants management enforcing Rule 15 (Principal separation)
and Rule 23 (Consent enforced on host).
"""

from __future__ import annotations
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any

from core.db import db, tenant_scoped
from core.authority.types import Rule15Violation
from core.host.types import (
    GrantMode,
    GrantScope,
    GrantEventType,
    HostGrantRecord,
    HostSecurityViolation,
    ensure_host_permission_tables,
)

logger = logging.getLogger("zonata.host.grants")


class HostGrantManager:
    """Manages host grants, time windows, allowed scope lists, and revocation."""

    @classmethod
    @tenant_scoped
    def create_grant(
        cls,
        device_id: str,
        tenant_id: str,
        company_id: str,
        scope_type: GrantScope,
        mode: GrantMode,
        allowed_apps: List[str],
        allowed_folders: List[str],
        allowed_domains: List[str],
        allowed_actions: List[str],
        created_by_principal_id: str,
        created_by_principal_type: str,
        valid_duration_seconds: float = 3600.0,
    ) -> HostGrantRecord:
        """
        Creates an explicit grant for a paired device.
        RULE 15 ENFORCEMENT: Grants can ONLY be created by an authenticated human principal.
        Agents, employees, or AI CEO principals cannot create or widen grants.
        """
        if str(created_by_principal_type).upper() != "HUMAN":
            raise Rule15Violation(
                f"RULE 15 VIOLATION: Principal '{created_by_principal_id}' of type "
                f"'{created_by_principal_type}' is not authorized to create host grants. "
                "Only authenticated human owners can issue or widen grants."
            )

        now = time.time()
        grant_id = f"grant_{uuid.uuid4().hex[:12]}"
        valid_from = now
        valid_until = now + valid_duration_seconds

        sql_grant = """
        INSERT INTO host_grants (
            grant_id, device_id, tenant_id, company_id, scope_type,
            mode, allowed_apps, allowed_folders, allowed_domains,
            allowed_actions, created_by_principal_id, created_by_principal_type,
            valid_from, valid_until, status, created_at
        ) VALUES (
            :grant_id, :device_id, :tenant_id, :company_id, :scope_type,
            :mode, :allowed_apps, :allowed_folders, :allowed_domains,
            :allowed_actions, :created_by_principal_id, :created_by_principal_type,
            :valid_from, :valid_until, 'ACTIVE', :created_at
        )
        """
        sql_event = """
        INSERT INTO grant_events (
            event_id, grant_id, device_id, tenant_id, company_id,
            event_type, details, actor_id, actor_type, timestamp
        ) VALUES (
            :event_id, :grant_id, :device_id, :tenant_id, :company_id,
            :event_type, :details, :actor_id, :actor_type, :timestamp
        )
        """
        with db.get_connection() as conn:
            ensure_host_permission_tables(conn)
            conn.execute(
                sql_grant,
                {
                    "grant_id": grant_id,
                    "device_id": device_id,
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "scope_type": scope_type.value if isinstance(scope_type, GrantScope) else str(scope_type),
                    "mode": mode.value if isinstance(mode, GrantMode) else str(mode),
                    "allowed_apps": json.dumps(allowed_apps),
                    "allowed_folders": json.dumps(allowed_folders),
                    "allowed_domains": json.dumps(allowed_domains),
                    "allowed_actions": json.dumps(allowed_actions),
                    "created_by_principal_id": created_by_principal_id,
                    "created_by_principal_type": created_by_principal_type,
                    "valid_from": valid_from,
                    "valid_until": valid_until,
                    "created_at": now,
                },
            )
            event_id = f"gev_{uuid.uuid4().hex[:12]}"
            conn.execute(
                sql_event,
                {
                    "event_id": event_id,
                    "grant_id": grant_id,
                    "device_id": device_id,
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "event_type": GrantEventType.GRANT_CREATED.value,
                    "details": json.dumps({
                        "scope": str(scope_type),
                        "mode": str(mode),
                        "allowed_apps": allowed_apps,
                        "valid_duration_seconds": valid_duration_seconds,
                    }),
                    "actor_id": created_by_principal_id,
                    "actor_type": created_by_principal_type,
                    "timestamp": now,
                },
            )
            if hasattr(conn, "commit"):
                conn.commit()

        logger.info(f"Created grant {grant_id} for device {device_id} by human {created_by_principal_id}")
        return HostGrantRecord(
            grant_id=grant_id,
            device_id=device_id,
            tenant_id=tenant_id,
            company_id=company_id,
            scope_type=GrantScope(scope_type) if isinstance(scope_type, str) else scope_type,
            mode=GrantMode(mode) if isinstance(mode, str) else mode,
            allowed_apps=allowed_apps,
            allowed_folders=allowed_folders,
            allowed_domains=allowed_domains,
            allowed_actions=allowed_actions,
            created_by_principal_id=created_by_principal_id,
            created_by_principal_type=created_by_principal_type,
            valid_from=valid_from,
            valid_until=valid_until,
            status="ACTIVE",
            created_at=now,
        )

    @classmethod
    @tenant_scoped
    def revoke_grant(
        cls,
        grant_id: str,
        revoked_by_principal_id: str,
        revoked_by_principal_type: str,
    ) -> bool:
        """Revokes an active grant. Only humans or emergency safety controllers can revoke."""
        now = time.time()
        sql_select = "SELECT device_id, tenant_id, company_id FROM host_grants WHERE grant_id = :grant_id"
        sql_update = """
        UPDATE host_grants
        SET status = 'REVOKED',
            revoked_at = :now,
            revoked_by_principal_id = :revoked_by
        WHERE grant_id = :grant_id
        """
        sql_event = """
        INSERT INTO grant_events (
            event_id, grant_id, device_id, tenant_id, company_id,
            event_type, details, actor_id, actor_type, timestamp
        ) VALUES (
            :event_id, :grant_id, :device_id, :tenant_id, :company_id,
            :event_type, :details, :actor_id, :actor_type, :timestamp
        )
        """
        with db.get_connection() as conn:
            row = conn.execute(sql_select, {"grant_id": grant_id}).fetchone()
            if not row:
                return False

            conn.execute(sql_update, {
                "grant_id": grant_id,
                "now": now,
                "revoked_by": revoked_by_principal_id,
            })
            conn.execute(sql_event, {
                "event_id": f"gev_{uuid.uuid4().hex[:12]}",
                "grant_id": grant_id,
                "device_id": row["device_id"],
                "tenant_id": row["tenant_id"],
                "company_id": row["company_id"],
                "event_type": GrantEventType.GRANT_REVOKED.value,
                "details": json.dumps({"revocation_reason": "USER_INITIATED"}),
                "actor_id": revoked_by_principal_id,
                "actor_type": revoked_by_principal_type,
                "timestamp": now,
            })
            if hasattr(conn, "commit"):
                conn.commit()

        logger.info(f"Revoked grant {grant_id} by {revoked_by_principal_id}")
        return True

    @classmethod
    @tenant_scoped
    def get_active_grants(cls, device_id: str) -> List[HostGrantRecord]:
        now = time.time()
        sql = """
        SELECT grant_id, device_id, tenant_id, company_id, scope_type,
               mode, allowed_apps, allowed_folders, allowed_domains,
               allowed_actions, created_by_principal_id, created_by_principal_type,
               valid_from, valid_until, status, revoked_at, revoked_by_principal_id, created_at
        FROM host_grants
        WHERE device_id = :device_id
          AND status = 'ACTIVE'
          AND valid_from <= :now
          AND valid_until > :now
        ORDER BY created_at DESC
        """
        grants = []
        with db.get_connection() as conn:
            rows = conn.execute(sql, {"device_id": device_id, "now": now}).fetchall()
            for r in rows:
                grants.append(HostGrantRecord(
                    grant_id=r["grant_id"],
                    device_id=r["device_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    scope_type=GrantScope(r["scope_type"]),
                    mode=GrantMode(r["mode"]),
                    allowed_apps=json.loads(r["allowed_apps"]),
                    allowed_folders=json.loads(r["allowed_folders"]),
                    allowed_domains=json.loads(r["allowed_domains"]),
                    allowed_actions=json.loads(r["allowed_actions"]),
                    created_by_principal_id=r["created_by_principal_id"],
                    created_by_principal_type=r["created_by_principal_type"],
                    valid_from=r["valid_from"],
                    valid_until=r["valid_until"],
                    status=r["status"],
                    revoked_at=r["revoked_at"],
                    revoked_by_principal_id=r["revoked_by_principal_id"],
                    created_at=r["created_at"],
                ))
        return grants
