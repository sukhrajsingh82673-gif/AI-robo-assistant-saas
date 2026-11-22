"""
Authority Delegations with Scoped Authority Boundaries (OpenCode Step 2C)
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List

from core.db import db, tenant_scoped_class
from core.authority.types import (
    DelegationAuthorityExceededError,
    DelegationRevokedError,
    PrincipalType,
    Rule15Violation,
    GOVERNED_PRINCIPAL_TYPES,
)
from core.authority.profiles import authority_profile_manager

logger = logging.getLogger("zonata.authority.delegation")


@tenant_scoped_class
class DelegationManager:
    """Manages time-bound, revocable, scoped delegations bounded by delegator authority."""

    def __init__(self):
        pass

    def create_delegation(
        self,
        tenant_id: str,
        company_id: str,
        delegator_id: str,
        delegate_id: str,
        scope: Dict[str, Any],
        starts_at: float,
        expires_at: float,
        delegator_grade: Optional[str] = None,
        caller_principal_type: str = PrincipalType.HUMAN.value,
    ) -> Dict[str, Any]:
        """Creates a time-bound delegation. Enforces Rule 15 and delegator authority ceiling."""
        if caller_principal_type in [p.value for p in GOVERNED_PRINCIPAL_TYPES]:
            msg = f"Rule 15 Violation: Principal type '{caller_principal_type}' is prohibited from writing delegations."
            logger.error(msg)
            raise Rule15Violation(msg)

        if expires_at <= starts_at:
            raise ValueError("Delegation expires_at must be strictly greater than starts_at")

        # 1. Verify delegator's own authority
        delegator_prof = authority_profile_manager.get_profile(
            tenant_id, company_id, delegator_id, grade=delegator_grade
        )

        if not delegator_prof.get("can_delegate", False):
            raise DelegationAuthorityExceededError(
                f"Delegator '{delegator_id}' (grade {delegator_prof['grade']}) lacks delegation privileges"
            )

        delegated_spend = scope.get("max_single_spend_usd", 0)
        if delegated_spend > delegator_prof["single"]:
            raise DelegationAuthorityExceededError(
                f"Delegated single spend limit (${delegated_spend:,}) exceeds delegator's authority limit (${delegator_prof['single']:,})"
            )

        delegation_id = f"del_{uuid.uuid4().hex[:16]}"
        now = time.time()
        scope_json = json.dumps(scope)

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO authority_delegations (
                    delegation_id, tenant_id, company_id, delegator_id, delegate_id,
                    scope, starts_at, expires_at, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (delegation_id, tenant_id, company_id, delegator_id, delegate_id, scope_json, starts_at, expires_at, now),
            )
            conn.commit()

        return {
            "delegation_id": delegation_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "delegator_id": delegator_id,
            "delegate_id": delegate_id,
            "scope": scope,
            "starts_at": starts_at,
            "expires_at": expires_at,
            "is_active": True,
        }

    def revoke_delegation(
        self,
        delegation_id: str,
        tenant_id: str,
        company_id: str,
        revoked_by: str,
        caller_principal_type: str = PrincipalType.HUMAN.value,
    ) -> bool:
        """Revokes an active delegation immediately. Enforces Rule 15."""
        if caller_principal_type in [p.value for p in GOVERNED_PRINCIPAL_TYPES]:
            msg = f"Rule 15 Violation: Principal type '{caller_principal_type}' is prohibited from revoking delegations."
            logger.error(msg)
            raise Rule15Violation(msg)

        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE authority_delegations
                SET is_active = 0, revoked_at = ?, revoked_by = ?
                WHERE delegation_id = ? AND tenant_id = ? AND company_id = ? AND is_active = 1
                """,
                (now, revoked_by, delegation_id, tenant_id, company_id),
            )
            updated = cur.rowcount > 0
            conn.commit()
            return updated

    def get_active_delegation(
        self,
        tenant_id: str,
        company_id: str,
        delegate_id: str,
        at_time: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Returns the currently active unrevoked delegation for the delegate."""
        now = at_time or time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT delegation_id, delegator_id, delegate_id, scope, starts_at, expires_at, is_active, revoked_at
                FROM authority_delegations
                WHERE tenant_id = ? AND company_id = ? AND delegate_id = ?
                  AND is_active = 1 AND revoked_at IS NULL
                  AND starts_at <= ? AND expires_at >= ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (tenant_id, company_id, delegate_id, now, now),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "delegation_id": row[0],
                "delegator_id": row[1],
                "delegate_id": row[2],
                "scope": json.loads(row[3]) if row[3] else {},
                "starts_at": row[4],
                "expires_at": row[5],
                "is_active": bool(row[6]),
            }


delegation_manager = DelegationManager()
