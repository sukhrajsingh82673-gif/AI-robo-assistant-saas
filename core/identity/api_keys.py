"""
ZONATA Sovereign Core — Sub-Step 5C: Customer Integration API Keys.
===================================================================
Governed by:
- Rule 41: No plaintext secrets stored or logged. Salted SHA-256 hashes only.
- Rule 42: Scoped permissions, prefix lookup, expiration, and last-used tracking.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class APIKeyRecord:
    key_id: str
    prefix: str
    salt: str
    hashed_secret: str
    tenant_id: str
    company_id: str
    name: str
    scopes: List[str]
    created_at: float
    is_live: bool = True
    expires_at: Optional[float] = None
    last_used_at: Optional[float] = None
    revoked: bool = False


class APIKeyManager:
    """Manages secure generation, hashing, and verification of customer API keys."""

    def __init__(self):
        # In-memory store; persistent backing goes to DB tables with RLS
        self._keys_by_id: Dict[str, APIKeyRecord] = {}
        self._keys_by_prefix: Dict[str, APIKeyRecord] = {}

    def generate_key(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        scopes: List[str],
        is_live: bool = True,
        expires_in_seconds: Optional[float] = None,
    ) -> Tuple[str, APIKeyRecord]:
        """
        Generate a new customer API key.
        Returns the plaintext token once. The plaintext token is NEVER stored.
        Format: zonata_{live|test}_sk_{prefix}_{secret}
        """
        mode = "live" if is_live else "test"
        prefix = secrets.token_hex(4)  # 8 hex chars
        secret = secrets.token_hex(32)  # 64 hex chars (high entropy, underscore-free)
        full_token = f"zonata_{mode}_sk_{prefix}_{secret}"

        salt = secrets.token_hex(16)
        hashed_secret = self._hash_secret(secret, salt)

        now = time.time()
        expires_at = (now + expires_in_seconds) if expires_in_seconds else None

        record = APIKeyRecord(
            key_id=f"key_{uuid.uuid4().hex[:12]}",
            prefix=prefix,
            salt=salt,
            hashed_secret=hashed_secret,
            tenant_id=tenant_id,
            company_id=company_id,
            name=name,
            scopes=list(scopes),
            created_at=now,
            is_live=is_live,
            expires_at=expires_at,
            revoked=False,
        )

        self._keys_by_id[record.key_id] = record
        self._keys_by_prefix[record.prefix] = record

        return full_token, record

    def verify_key(self, token: str, required_scope: Optional[str] = None) -> APIKeyRecord:
        """
        Verify the presented API token against stored hash in constant time.
        Validates expiration, revocation, and scope.
        """
        parts = token.split("_", 4)
        # Format: zonata_{live|test}_sk_{prefix}_{secret}
        if len(parts) != 5 or parts[0] != "zonata" or parts[2] != "sk":
            raise ValueError("Malformed API key format")

        prefix = parts[3]
        presented_secret = parts[4]

        record = self._keys_by_prefix.get(prefix)
        if not record:
            raise KeyError("API key not found or invalid prefix")

        if record.revoked:
            raise PermissionError("API key has been revoked")

        if record.expires_at and time.time() > record.expires_at:
            raise PermissionError("API key has expired")

        # Constant-time comparison of salted secret hash
        computed_hash = self._hash_secret(presented_secret, record.salt)
        if not hmac.compare_digest(computed_hash, record.hashed_secret):
            raise PermissionError("Invalid API key secret")

        if required_scope and required_scope not in record.scopes and "*" not in record.scopes:
            raise PermissionError(f"API key lacks required scope: {required_scope}")

        record.last_used_at = time.time()
        return record

    def revoke_key(self, key_id: str, tenant_id: str) -> bool:
        """Revoke an API key."""
        record = self._keys_by_id.get(key_id)
        if not record or record.tenant_id != tenant_id:
            return False
        record.revoked = True
        return True

    @staticmethod
    def _hash_secret(secret: str, salt: str) -> str:
        salted = f"{salt}:{secret}".encode("utf-8")
        return hashlib.sha256(salted).hexdigest()
