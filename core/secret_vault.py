"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Enterprise Secret Vault & Secret Reference Engine
Enforces encrypted storage of credentials, secret referencing (secret:// URI scheme),
rotation, audit logging, and automated leakage prevention.
"""

import os
import time
import uuid
import json
import base64
import hashlib
import hmac
import logging
from typing import Dict, List, Optional, Any, Tuple
from .db import db

logger = logging.getLogger("zonata.secrets")

class SecretVaultException(Exception):
    pass

class SecretVault:
    """
    Manages tenant and system secrets using secure vault references.
    Plaintext secrets are never stored in plain database fields or returned in plain logs.
    """

    def __init__(self, tenant_id: str = "tnt_primary", master_key: Optional[str] = None):
        self.tenant_id = tenant_id
        # Derive encryption key or use fallback for sovereign offline
        raw_key = master_key or os.environ.get("SECRET_VAULT_KEY", "sovereign_production_vault_master_key_32_chars!")
        self._key = hashlib.sha256(raw_key.encode()).digest()
        self._ensure_table()

    def _ensure_table(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_secret_vault (
                secret_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                encrypted_payload TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, ROTATED, REVOKED, EXPIRED
                created_at REAL NOT NULL,
                expires_at REAL,
                rotated_at REAL,
                last_accessed_at REAL,
                access_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
            """)
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(enterprise_secret_vault)").fetchall()]
            except Exception:
                cols = []
            if "encrypted_payload" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN encrypted_payload TEXT NOT NULL DEFAULT ''")
            if "version" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
            if "status" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE'")
            if "company_id" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN company_id TEXT NOT NULL DEFAULT ''")
            if "origin" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN origin TEXT NOT NULL DEFAULT 'internal'")
            if "secret_ciphertext" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN secret_ciphertext TEXT NOT NULL DEFAULT ''")
            if "secret_type" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN secret_type TEXT NOT NULL DEFAULT 'API_KEY'")
            if "rotated_at" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN rotated_at REAL")
            if "access_count" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN access_count INTEGER NOT NULL DEFAULT 0")
            if "last_accessed_at" not in cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN last_accessed_at REAL")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_secret_access_audit (
                audit_id TEXT PRIMARY KEY,
                secret_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL, -- READ, ROTATE, REVOKE
                timestamp REAL NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
            """)
            conn.commit()

    def _encrypt(self, plaintext: str) -> str:
        """Lightweight XOR + HMAC envelope simulation of authenticated symmetric encryption."""
        iv = os.urandom(16)
        stream_key = hashlib.sha256(self._key + iv).digest()
        plain_bytes = plaintext.encode("utf-8")
        # Repeating key XOR
        cipher_bytes = bytes([b ^ stream_key[i % len(stream_key)] for i, b in enumerate(plain_bytes)])
        mac = hmac.new(self._key, iv + cipher_bytes, hashlib.sha256).digest()
        envelope = {
            "iv": base64.b64encode(iv).decode(),
            "ct": base64.b64encode(cipher_bytes).decode(),
            "mac": base64.b64encode(mac).decode()
        }
        return json.dumps(envelope)

    def _decrypt(self, envelope_json: str) -> str:
        envelope = json.loads(envelope_json)
        iv = base64.b64decode(envelope["iv"])
        cipher_bytes = base64.b64decode(envelope["ct"])
        expected_mac = base64.b64decode(envelope["mac"])

        calculated_mac = hmac.new(self._key, iv + cipher_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_mac, calculated_mac):
            raise SecretVaultException("Secret integrity validation failed! MAC mismatch.")

        stream_key = hashlib.sha256(self._key + iv).digest()
        plain_bytes = bytes([b ^ stream_key[i % len(stream_key)] for i, b in enumerate(cipher_bytes)])
        return plain_bytes.decode("utf-8")

    def store_secret(
        self,
        name: str,
        value: str,
        expires_in_seconds: Optional[float] = None,
        actor_id: str = "SYSTEM_ADMIN"
    ) -> str:
        """Stores a secret and returns a safe reference URI (e.g. secret://tenant_id/sec_xyz)."""
        secret_id = f"sec_{uuid.uuid4().hex[:12]}"
        now = time.time()
        expires_at = now + expires_in_seconds if expires_in_seconds else None
        encrypted = self._encrypt(value)

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO enterprise_secret_vault (
                    secret_id, tenant_id, company_id, name, origin,
                    secret_ciphertext, encrypted_payload, secret_type,
                    version, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, 'internal', ?, ?, 'API_KEY', 1, 'ACTIVE', ?, ?)
            """, (secret_id, self.tenant_id, self.tenant_id, name, encrypted, encrypted, now, expires_at))

            conn.execute("""
                INSERT INTO enterprise_secret_access_audit (
                    audit_id, secret_id, tenant_id, actor_id, action, timestamp, success
                ) VALUES (?, ?, ?, ?, 'CREATE', ?, 1)
            """, (f"aud_{uuid.uuid4().hex[:8]}", secret_id, self.tenant_id, actor_id, now))
            conn.commit()

        return f"secret://{self.tenant_id}/{secret_id}"

    def retrieve_secret(self, secret_ref: str, actor_id: str = "WORKER") -> str:
        """Resolves a secret:// URI into plaintext with audit logging and expiry check."""
        if not secret_ref.startswith(f"secret://{self.tenant_id}/"):
            raise SecretVaultException(f"Cross-tenant or invalid secret reference: {secret_ref}")

        secret_id = secret_ref.split("/")[-1]
        now = time.time()

        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM enterprise_secret_vault WHERE secret_id = ? AND tenant_id = ?",
                (secret_id, self.tenant_id)
            ).fetchone()

            if not row:
                raise SecretVaultException(f"Secret reference '{secret_ref}' not found.")

            status = row["status"]
            if status == "REVOKED":
                raise SecretVaultException(f"Secret '{secret_ref}' has been REVOKED.")

            expires_at = row["expires_at"]
            if expires_at and now > expires_at:
                conn.execute("UPDATE enterprise_secret_vault SET status = 'EXPIRED' WHERE secret_id = ?", (secret_id,))
                conn.commit()
                raise SecretVaultException(f"Secret '{secret_ref}' has EXPIRED.")

            # Record successful access audit
            conn.execute("""
                UPDATE enterprise_secret_vault
                SET access_count = access_count + 1, last_accessed_at = ?
                WHERE secret_id = ?
            """, (now, secret_id))

            conn.execute("""
                INSERT INTO enterprise_secret_access_audit (
                    audit_id, secret_id, tenant_id, actor_id, action, timestamp, success
                ) VALUES (?, ?, ?, ?, 'READ', ?, 1)
            """, (f"aud_{uuid.uuid4().hex[:8]}", secret_id, self.tenant_id, actor_id, now))
            conn.commit()

            return self._decrypt(row["encrypted_payload"])

    def rotate_secret(self, secret_ref: str, new_value: str, actor_id: str = "SYSTEM_ADMIN") -> str:
        """Rotates a secret to a new version."""
        secret_id = secret_ref.split("/")[-1]
        now = time.time()
        encrypted = self._encrypt(new_value)

        with db.get_connection() as conn:
            res = conn.execute("""
                UPDATE enterprise_secret_vault
                SET encrypted_payload = ?, version = version + 1, rotated_at = ?, status = 'ACTIVE'
                WHERE secret_id = ? AND tenant_id = ?
            """, (encrypted, now, secret_id, self.tenant_id))

            if res.rowcount == 0:
                raise SecretVaultException(f"Secret '{secret_ref}' not found for rotation.")

            conn.execute("""
                INSERT INTO enterprise_secret_access_audit (
                    audit_id, secret_id, tenant_id, actor_id, action, timestamp, success
                ) VALUES (?, ?, ?, ?, 'ROTATE', ?, 1)
            """, (f"aud_{uuid.uuid4().hex[:8]}", secret_id, self.tenant_id, actor_id, now))
            conn.commit()

        return secret_ref

    def revoke_secret(self, secret_ref: str, actor_id: str = "SYSTEM_ADMIN") -> bool:
        """Revokes a secret immediately."""
        secret_id = secret_ref.split("/")[-1]
        now = time.time()

        with db.get_connection() as conn:
            res = conn.execute(
                "UPDATE enterprise_secret_vault SET status = 'REVOKED' WHERE secret_id = ? AND tenant_id = ?",
                (secret_id, self.tenant_id)
            )
            if res.rowcount == 0:
                return False

            conn.execute("""
                INSERT INTO enterprise_secret_access_audit (
                    audit_id, secret_id, tenant_id, actor_id, action, timestamp, success
                ) VALUES (?, ?, ?, ?, 'REVOKE', ?, 1)
            """, (f"aud_{uuid.uuid4().hex[:8]}", secret_id, self.tenant_id, actor_id, now))
            conn.commit()
            return True

    @staticmethod
    def scan_for_secret_leakage(text: str, known_secrets: List[str]) -> List[str]:
        """Scans logs, prompts, or traces to verify zero plaintext leakage."""
        detected = []
        for s in known_secrets:
            if s and len(s) >= 8 and s in text:
                detected.append(s[:4] + "***" + s[-2:])
        return detected
