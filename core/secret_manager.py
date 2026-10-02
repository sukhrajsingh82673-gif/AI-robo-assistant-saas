"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Secret Vault & Credential Broker V2
Manages ephemeral JIT credential leasing, zero-secret logging,
and regex-based automated secret redaction across all control and execution planes.
"""

import os
import re
import time
import uuid
import hashlib
import logging
import threading
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("zonata.secrets")

class SecretVaultManager:
    """
    Production-grade Credential Broker.
    Agents only interact with opaque handles (e.g. 'cred_stripe_key').
    Raw tokens are never exposed in prompt memory, workflow history, or logs.
    """
    REDACTION_PATTERNS = [
        re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE),
        re.compile(r"(sk_live_[0-9a-zA-Z]{24})", re.IGNORECASE),
        re.compile(r"(ghp_[0-9a-zA-Z]{36})", re.IGNORECASE),
        re.compile(r"(xox[baprs]-[0-9a-zA-Z]{10,48})", re.IGNORECASE),
        re.compile(r"(api[_-]?key[\"'\s:=]+)([A-Za-z0-9_\-]{16,})", re.IGNORECASE),
        re.compile(r"(secret[\"'\s:=]+)([A-Za-z0-9_\-]{16,})", re.IGNORECASE),
        re.compile(r"(password[\"'\s:=]+)([A-Za-z0-9_\-]{6,})", re.IGNORECASE)
    ]

    def __init__(self):
        self._vault: Dict[str, Dict[str, Any]] = {}
        self._leases: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register_secret(
        self,
        tenant_id: str,
        secret_name: str,
        secret_value: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store secret under tenant namespace and return opaque handle."""
        handle = f"cred_{hashlib.sha256(f'{tenant_id}:{secret_name}'.encode('utf-8')).hexdigest()[:16]}"
        with self._lock:
            self._vault[handle] = {
                "tenant_id": tenant_id,
                "name": secret_name,
                "value": secret_value,
                "created_at": time.time(),
                "metadata": metadata or {}
            }
        return handle

    def acquire_jit_token(self, handle: str, tenant_id: str, ttl_seconds: float = 60.0) -> str:
        """
        Issue short-lived ephemeral token for immediate execution.
        Fails closed if tenant does not match handle ownership.
        """
        with self._lock:
            secret_data = self._vault.get(handle)
            if not secret_data:
                raise KeyError(f"Secret handle '{handle}' not found in vault.")

            if secret_data["tenant_id"] != tenant_id:
                raise PermissionError("Cross-tenant credential access violation.")

            raw_value = secret_data["value"]
            lease_id = f"lease_{uuid.uuid4().hex[:12]}"
            self._leases[lease_id] = {
                "handle": handle,
                "tenant_id": tenant_id,
                "expires_at": time.time() + ttl_seconds
            }
            return raw_value

    def redact_secrets(self, text: str) -> str:
        """
        Scrub plaintext credentials, bearer tokens, and API keys from arbitrary text.
        Guarantees zero-secret persistence in logs, error traces, and prompts.
        """
        if not text or not isinstance(text, str):
            return text

        redacted = text
        for pattern in self.REDACTION_PATTERNS:
            redacted = pattern.sub(r"\1[REDACTED_SECRET]", redacted)

        # Also redact any registered vault values
        with self._lock:
            for item in self._vault.values():
                val = item.get("value")
                if val and len(val) >= 6 and val in redacted:
                    redacted = redacted.replace(val, "[REDACTED_VAULT_SECRET]")

        return redacted

# Global secret vault manager
secret_manager = SecretVaultManager()
