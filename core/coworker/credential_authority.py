"""
ZONATA Universal AI Co-worker Fabric — Credential Authority
Provides scoped, short-lived tokens, secret vault reference URI resolution,
credential revocation, and MFA pause/resume state handling.
Strict invariant: Never exposes raw owner credentials to an LLM context.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import uuid
import hashlib
from ..secret_vault import SecretVault

class CredentialAuthority:
    """
    Sovereign Credential Authority.
    Mediates access to third-party services, desktop login sessions, and APIs.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._vault = SecretVault(tenant_id)
        self._active_tokens: Dict[str, Dict[str, Any]] = {}
        self._mfa_challenges: Dict[str, Dict[str, Any]] = {}

    def issue_scoped_token(
        self,
        worker_id: str,
        service: str,
        scope: List[str],
        ttl_seconds: int = 300
    ) -> str:
        """Issues a short-lived scoped token for a worker."""
        token_id = f"tok_{uuid.uuid4().hex[:12]}"
        now = time.time()
        self._active_tokens[token_id] = {
            "worker_id": worker_id,
            "service": service,
            "scope": scope,
            "issued_at": now,
            "expires_at": now + ttl_seconds,
            "status": "ACTIVE"
        }
        return token_id

    def validate_token(self, token_id: str, required_scope: str) -> Tuple[bool, Optional[str]]:
        """Validates that a scoped token is active and not expired."""
        record = self._active_tokens.get(token_id)
        if not record:
            return False, "Token not found"
        if record["status"] != "ACTIVE":
            return False, f"Token is {record['status']}"
        if time.time() > record["expires_at"]:
            record["status"] = "EXPIRED"
            return False, "Token has expired"
        if required_scope not in record["scope"] and "*" not in record["scope"]:
            return False, f"Scope '{required_scope}' not granted"
        return True, None

    def revoke_token(self, token_id: str, reason: str = "Manual revocation"):
        if token_id in self._active_tokens:
            self._active_tokens[token_id]["status"] = "REVOKED"
            self._active_tokens[token_id]["revocation_reason"] = reason

    def request_mfa_authentication(self, mission_id: str, service: str, prompt: str) -> str:
        """Pauses execution in AUTH_REQUIRED state awaiting human MFA completion."""
        challenge_id = f"mfa_{uuid.uuid4().hex[:8]}"
        self._mfa_challenges[challenge_id] = {
            "mission_id": mission_id,
            "service": service,
            "prompt": prompt,
            "status": "PENDING",
            "created_at": time.time()
        }
        return challenge_id

    def fulfill_mfa_challenge(self, challenge_id: str, confirmation_token: str) -> bool:
        """Human submits MFA confirmation to resume paused Mission."""
        if challenge_id not in self._mfa_challenges:
            return False
        challenge = self._mfa_challenges[challenge_id]
        if challenge["status"] != "PENDING":
            return False
        challenge["status"] = "FULFILLED"
        challenge["fulfilled_at"] = time.time()
        challenge["token"] = hashlib.sha256(confirmation_token.encode()).hexdigest()
        return True

    def get_challenge_status(self, challenge_id: str) -> Optional[str]:
        return self._mfa_challenges.get(challenge_id, {}).get("status")
