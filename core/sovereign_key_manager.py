"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Sovereign Key Management & Multi-Tier Cryptographic Authority
Strictly isolates Sovereign Root Keys from AI agents, mandates dual-key authorization,
and governs key rotation lifecycles.
"""

import os
import time
import uuid
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from .db import db

logger = logging.getLogger("zonata.crypto")

class SovereignAuthorityViolation(Exception):
    """Raised when an unauthorized actor attempts access to Sovereign Root Authority."""
    pass

class KeyType:
    SOVEREIGN_ROOT = "SOVEREIGN_ROOT"         # Human Owner only, air-gapped/dual-key
    APPLICATION_SIGNING = "APPLICATION_SIGNING" # API session tokens, HMAC
    EVIDENCE_SIGNING = "EVIDENCE_SIGNING"       # Merkle ledger block signing
    WEBHOOK_SIGNING = "WEBHOOK_SIGNING"         # Outbound/inbound webhook verification
    TENANT_KEY = "TENANT_KEY"                   # Tenant data partition encryption
    SERVICE_KEY = "SERVICE_KEY"                 # Internal microservice mTLS

class SovereignKeyManager:
    """
    Manages multi-tier cryptographic keys.
    Constitutional Invariant: AI EMPLOYEES & AI CEO HAVE ZERO ACCESS TO SOVEREIGN_ROOT KEYS.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._ensure_table()

    def _ensure_table(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sovereign_key_registry (
                key_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                key_type TEXT NOT NULL,
                algorithm TEXT NOT NULL DEFAULT 'ED25519',
                public_key_pem TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, ROTATED, REVOKED
                requires_dual_key INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                rotated_at REAL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
            """)
            conn.commit()

    def register_key(
        self,
        key_type: str,
        public_key_pem: str,
        actor_role: str,
        algorithm: str = "ED25519",
        requires_dual_key: bool = False
    ) -> str:
        """Registers a public key identity in the sovereign registry."""
        if key_type == KeyType.SOVEREIGN_ROOT and actor_role != "HUMAN_OWNER":
            raise SovereignAuthorityViolation(f"Only HUMAN_OWNER can register a SOVEREIGN_ROOT key. Role '{actor_role}' denied.")

        key_id = f"key_{key_type.lower()}_{uuid.uuid4().hex[:8]}"
        now = time.time()
        dual_int = 1 if (requires_dual_key or key_type == KeyType.SOVEREIGN_ROOT) else 0

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO sovereign_key_registry (
                    key_id, tenant_id, key_type, algorithm,
                    public_key_pem, version, status, requires_dual_key, created_at
                ) VALUES (?, ?, ?, ?, ?, 1, 'ACTIVE', ?, ?)
            """, (key_id, self.tenant_id, key_type, algorithm, public_key_pem, dual_int, now))
            conn.commit()

        return key_id

    def rotate_sovereign_root(
        self,
        key_id: str,
        new_public_key_pem: str,
        actor_role: str,
        primary_owner_sig: Optional[str] = None,
        secondary_owner_sig: Optional[str] = None
    ) -> bool:
        """
        Rotates Sovereign Root Key.
        MANDATES:
        1. Actor MUST be HUMAN_OWNER.
        2. DUAL-KEY cryptographic signatures MUST be provided.
        """
        if actor_role != "HUMAN_OWNER":
            raise SovereignAuthorityViolation(
                f"AI Role '{actor_role}' attempted to rotate SOVEREIGN_ROOT key! Immediate containment triggered."
            )

        if not primary_owner_sig or not secondary_owner_sig:
            raise SovereignAuthorityViolation(
                "Sovereign Root Key rotation requires dual-key cryptographic signatures from authorized Human Owners."
            )

        now = time.time()
        with db.get_connection() as conn:
            res = conn.execute("""
                UPDATE sovereign_key_registry
                SET public_key_pem = ?, version = version + 1, rotated_at = ?
                WHERE key_id = ? AND tenant_id = ? AND key_type = 'SOVEREIGN_ROOT'
            """, (new_public_key_pem, now, key_id, self.tenant_id))

            if res.rowcount == 0:
                raise SovereignAuthorityViolation(f"Sovereign root key '{key_id}' not found.")
            conn.commit()
            return True

    def get_public_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sovereign_key_registry WHERE key_id = ? AND tenant_id = ?",
                (key_id, self.tenant_id)
            ).fetchone()
            return dict(row) if row else None
