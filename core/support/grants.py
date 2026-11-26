"""
Consented Dual-Control Support Access Grant Engine (Rule 82).
Mandates time-boxed, tenant-issued support tokens for platform operator access.
Explicitly prohibits support operators from acting as Owner for reserved actions.
"""

import time
import uuid
import hmac
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Set


@dataclass
class SupportGrantToken:
    grant_id: str
    tenant_id: str
    authorized_operator_id: str
    scope: str  # read_diagnostics, inspect_queue, debug_workflow
    purpose: str
    issued_at: float
    expires_at: float
    issued_by_user_id: str
    signature: str
    revoked: bool = False


class SupportGrantEngine:
    """
    Engine for issuing and validating tenant-consented support grants.
    """

    MAX_GRANT_DURATION_SECONDS = 14400  # 4 hours max

    # Actions strictly reserved for tenant Owners: Support staff CANNOT perform these even with a grant
    RESERVED_OWNER_ACTIONS: Set[str] = {
        "TRANSFER_OWNERSHIP",
        "UPDATE_BANKING_DETAILS",
        "APPROVE_MONEY_TRANSFER",
        "DELETE_COMPANY_DATA",
        "DEMOTE_OWNER",
    }

    def __init__(self, signing_secret: str):
        self.signing_secret = signing_secret
        # grant_id -> SupportGrantToken
        self._grants: Dict[str, SupportGrantToken] = {}

    def _generate_signature(self, grant_id: str, tenant_id: str, operator_id: str, expires_at: float) -> str:
        payload = f"{grant_id}|{tenant_id}|{operator_id}|{expires_at:.0f}"
        return hmac.new(self.signing_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def issue_support_grant(
        self,
        tenant_id: str,
        issued_by_user_id: str,
        user_role: str,
        operator_id: str,
        purpose: str,
        duration_seconds: int = 3600,
        scope: str = "read_diagnostics",
        current_time: Optional[float] = None,
    ) -> SupportGrantToken:
        """
        Only tenant Owner or Admin can issue a support grant.
        """
        if user_role not in ("Owner", "Admin"):
            raise PermissionError(f"Role '{user_role}' is not authorized to grant support access. Requires Owner or Admin.")

        effective_duration = min(duration_seconds, self.MAX_GRANT_DURATION_SECONDS)
        now = current_time if current_time is not None else time.time()
        expires = now + effective_duration
        grant_id = f"grant_{uuid.uuid4().hex[:12]}"
        signature = self._generate_signature(grant_id, tenant_id, operator_id, expires)

        token = SupportGrantToken(
            grant_id=grant_id,
            tenant_id=tenant_id,
            authorized_operator_id=operator_id,
            scope=scope,
            purpose=purpose,
            issued_at=now,
            expires_at=expires,
            issued_by_user_id=issued_by_user_id,
            signature=signature,
            revoked=False,
        )
        self._grants[grant_id] = token
        return token

    def revoke_grant(self, grant_id: str, revoked_by_user_id: str) -> bool:
        grant = self._grants.get(grant_id)
        if not grant:
            return False
        grant.revoked = True
        return True

    def validate_access(
        self,
        grant_id: str,
        operator_id: str,
        tenant_id: str,
        attempted_action: str,
        current_time: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Validates operator access.
        1. Checks grant exists and is not revoked.
        2. Checks tenant_id and operator_id match.
        3. Checks signature authenticity.
        4. Checks expiration.
        5. Checks Rule 82 reserved action barrier.
        """
        # Rule 82 Barrier: Support can NEVER execute reserved owner decisions
        if attempted_action in self.RESERVED_OWNER_ACTIONS:
            return False, f"Rule 82 Violation: Action '{attempted_action}' is strictly reserved for tenant Owners. Support cannot act as Owner."

        grant = self._grants.get(grant_id)
        if not grant:
            return False, "DENIED: Support grant not found."

        if grant.revoked:
            return False, "DENIED: Support grant has been explicitly revoked by tenant."

        now = current_time if current_time is not None else time.time()
        if now >= grant.expires_at:
            return False, f"DENIED: Support grant expired at {grant.expires_at:.0f}."

        if grant.tenant_id != tenant_id or grant.authorized_operator_id != operator_id:
            return False, "DENIED: Support grant credentials do not match operator or tenant context."

        expected_sig = self._generate_signature(grant_id, tenant_id, operator_id, grant.expires_at)
        if not hmac.compare_digest(grant.signature, expected_sig):
            return False, "DENIED: Cryptographic grant signature validation failed."

        return True, "Authorized dual-control support session."
