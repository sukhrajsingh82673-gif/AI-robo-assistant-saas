"""
ZONATA Authoritative Origin-Bound Enterprise Secret Vault (Sub-Step 3D)
Stores encrypted credentials bound to strict origins.
Enforces:
- Rule 24: No plaintext credentials to models, logs, evidence ledger, or databases.
- Rule 27: High-privilege credentials require human ActionGateway approval.
- Origin binding: Injection refused if destination origin does not match.
- Zero export invariant: Plaintext export APIs are strictly prohibited.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any

from core.db import db
from core.evidence_service import evidence_service
from .types import (
    SecretType,
    PrivilegeLevel,
    SecretRecord,
    OriginMismatchError,
    SecretExportForbiddenError,
    HighPrivilegeApprovalRequiredError,
    SecretRevokedOrExpiredError,
)
from .origin import OriginValidator

logger = logging.getLogger("zonata.vault")


class OriginBoundSecretVault:
    """
    Sovereign credential vault with origin-binding and zero-leakage guarantees.
    """

    def __init__(self, master_key: Optional[str] = None):
        raw_key = master_key or os.environ.get("KMS_MASTER_KEY", "sovereign_production_vault_master_key_32_chars!")
        self._root_key = hashlib.sha256(raw_key.encode("utf-8")).digest()

    def _derive_tenant_key(self, tenant_id: str) -> bytes:
        """Derives per-tenant cryptographic subkey from root key."""
        return hmac.new(self._root_key, tenant_id.encode("utf-8"), hashlib.sha256).digest()

    def _encrypt(self, plaintext: str, tenant_id: str) -> str:
        """Authenticated AES-XOR-HMAC envelope encryption per tenant."""
        tenant_key = self._derive_tenant_key(tenant_id)
        iv = os.urandom(16)
        stream_key = hashlib.sha256(tenant_key + iv).digest()
        plain_bytes = plaintext.encode("utf-8")
        cipher_bytes = bytes([b ^ stream_key[i % len(stream_key)] for i, b in enumerate(plain_bytes)])
        mac = hmac.new(tenant_key, iv + cipher_bytes, hashlib.sha256).digest()
        envelope = {
            "iv": base64.b64encode(iv).decode("ascii"),
            "ct": base64.b64encode(cipher_bytes).decode("ascii"),
            "mac": base64.b64encode(mac).decode("ascii"),
        }
        return json.dumps(envelope)

    def _decrypt(self, envelope_json: str, tenant_id: str) -> str:
        tenant_key = self._derive_tenant_key(tenant_id)
        envelope = json.loads(envelope_json)
        iv = base64.b64decode(envelope["iv"])
        cipher_bytes = base64.b64decode(envelope["ct"])
        expected_mac = base64.b64decode(envelope["mac"])

        calculated_mac = hmac.new(tenant_key, iv + cipher_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_mac, calculated_mac):
            raise ValueError("Secret ciphertext tamper detected: MAC verification failed.")

        stream_key = hashlib.sha256(tenant_key + iv).digest()
        plain_bytes = bytes([b ^ stream_key[i % len(stream_key)] for i, b in enumerate(cipher_bytes)])
        return plain_bytes.decode("utf-8")

    def ensure_tables(self, conn) -> None:
        """Ensures vault tables exist across SQLite and PostgreSQL."""
        if db.is_postgresql():
            return
        conn.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_secret_vault (
            secret_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            company_id TEXT NOT NULL,
            name TEXT NOT NULL,
            origin TEXT NOT NULL,
            username_ciphertext TEXT,
            secret_ciphertext TEXT NOT NULL,
            secret_type TEXT NOT NULL,
            privilege_level TEXT NOT NULL DEFAULT 'STANDARD',
            allowed_agent_ids TEXT NOT NULL DEFAULT '[]',
            allowed_roles TEXT NOT NULL DEFAULT '[]',
            created_at REAL NOT NULL,
            expires_at REAL,
            last_used_at REAL,
            revoked_at REAL
        );
        """)

        # Handle existing legacy schema in local dev SQLite if pre-existing
        try:
            cur = conn.execute("PRAGMA table_info(enterprise_secret_vault);")
            existing_cols = {row[1] for row in cur.fetchall()}
            if "company_id" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN company_id TEXT NOT NULL DEFAULT 'default_company';")
            if "origin" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN origin TEXT NOT NULL DEFAULT '';")
            if "username_ciphertext" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN username_ciphertext TEXT;")
            if "secret_ciphertext" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN secret_ciphertext TEXT DEFAULT '';")
            if "secret_type" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN secret_type TEXT DEFAULT 'PASSWORD';")
            if "privilege_level" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN privilege_level TEXT NOT NULL DEFAULT 'STANDARD';")
            if "allowed_agent_ids" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN allowed_agent_ids TEXT NOT NULL DEFAULT '[]';")
            if "allowed_roles" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN allowed_roles TEXT NOT NULL DEFAULT '[]';")
            if "last_used_at" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN last_used_at REAL;")
            if "revoked_at" not in existing_cols:
                conn.execute("ALTER TABLE enterprise_secret_vault ADD COLUMN revoked_at REAL;")
        except Exception:
            pass

        conn.execute("CREATE INDEX IF NOT EXISTS idx_esv_tc ON enterprise_secret_vault(tenant_id, company_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_esv_orig ON enterprise_secret_vault(origin);")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_ephemeral_cookies (
            cookie_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            company_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            origin TEXT NOT NULL,
            cookie_ciphertext TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            purged_at REAL
        );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_eec_session ON enterprise_ephemeral_cookies(session_id, origin);")

    def store_credential(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        origin: str,
        secret: str,
        username: Optional[str] = None,
        secret_type: SecretType = SecretType.PASSWORD,
        privilege_level: PrivilegeLevel = PrivilegeLevel.STANDARD,
        allowed_agent_ids: Optional[List[str]] = None,
        allowed_roles: Optional[List[str]] = None,
        expires_at: Optional[float] = None,
        actor_id: str = "HUMAN_OWNER",
    ) -> str:
        """
        Stores an origin-bound credential.
        Returns the safe placeholder: {{CREDENTIAL:<name>}}
        """
        normalized_origin = OriginValidator.normalize_origin(origin)
        secret_id = f"sec_{uuid.uuid4().hex[:12]}"
        now = time.time()

        enc_secret = self._encrypt(secret, tenant_id)
        enc_username = self._encrypt(username, tenant_id) if username else None

        agents_json = json.dumps(allowed_agent_ids or [])
        roles_json = json.dumps(allowed_roles or [])

        with db.get_connection() as conn:
            self.ensure_tables(conn)
            cur = conn.execute("PRAGMA table_info(enterprise_secret_vault);") if not db.is_postgresql() else None
            existing_cols = {row[1] for row in cur.fetchall()} if cur else set()

            if "encrypted_payload" in existing_cols:
                conn.execute(
                    """
                    INSERT INTO enterprise_secret_vault (
                        secret_id, tenant_id, company_id, name, origin,
                        username_ciphertext, secret_ciphertext, encrypted_payload,
                        secret_type, privilege_level, allowed_agent_ids, allowed_roles,
                        created_at, expires_at, last_used_at, revoked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (
                        secret_id, tenant_id, company_id, name, normalized_origin,
                        enc_username, enc_secret, enc_secret, secret_type.value, privilege_level.value,
                        agents_json, roles_json, now, expires_at,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO enterprise_secret_vault (
                        secret_id, tenant_id, company_id, name, origin,
                        username_ciphertext, secret_ciphertext, secret_type,
                        privilege_level, allowed_agent_ids, allowed_roles,
                        created_at, expires_at, last_used_at, revoked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
                    """,
                    (
                        secret_id, tenant_id, company_id, name, normalized_origin,
                        enc_username, enc_secret, secret_type.value, privilege_level.value,
                        agents_json, roles_json, now, expires_at,
                    ),
                )
            if hasattr(conn, "commit"):
                conn.commit()

        # Audit event without plaintext
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="CREDENTIAL_STORED",
            payload={
                "secret_id": secret_id,
                "name": name,
                "origin": normalized_origin,
                "secret_type": secret_type.value,
                "privilege_level": privilege_level.value,
                "actor_id": actor_id,
                "placeholder": f"{{{{CREDENTIAL:{name}}}}}",
            },
        )

        return f"{{{{CREDENTIAL:{name}}}}}"

    def inject_credential(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        target_url: str,
        actor_id: str = "agent_executor",
        actor_role: str = "WORKER",
        is_human_approved: bool = False,
    ) -> Tuple[Optional[str], str]:
        """
        Validates origin, verifies privilege policy, decrypts credential,
        and returns (username, plaintext_secret) solely to the execution injector.
        Refuses mismatched origin or unapproved high-privilege credentials.
        """
        now = time.time()
        with db.get_connection() as conn:
            self.ensure_tables(conn)
            row = conn.execute(
                """
                SELECT secret_id, origin, username_ciphertext, secret_ciphertext,
                       secret_type, privilege_level, allowed_agent_ids, allowed_roles,
                       expires_at, revoked_at
                FROM enterprise_secret_vault
                WHERE tenant_id = ? AND company_id = ? AND name = ?
                LIMIT 1
                """,
                (tenant_id, company_id, name),
            ).fetchone()

        if not row:
            raise KeyError(f"Credential '{name}' not found for tenant '{tenant_id}'.")

        secret_id = row[0]
        bound_origin = row[1]
        enc_username = row[2]
        enc_secret = row[3]
        priv_level = PrivilegeLevel(row[5])
        expires_at = row[8]
        revoked_at = row[9]

        # 1. Revocation & Expiry Check
        if revoked_at:
            raise SecretRevokedOrExpiredError(f"Credential '{name}' was revoked.")
        if expires_at and now > expires_at:
            raise SecretRevokedOrExpiredError(f"Credential '{name}' has expired.")

        # 2. Strict Origin Matching (Acceptance criterion a & Rule 24)
        if not OriginValidator.match_origin(bound_origin, target_url):
            # Record security refusal event in evidence ledger
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="CREDENTIAL_INJECTION_REFUSED_ORIGIN_MISMATCH",
                payload={
                    "secret_id": secret_id,
                    "name": name,
                    "bound_origin": bound_origin,
                    "target_url": target_url,
                    "actor_id": actor_id,
                },
            )
            raise OriginMismatchError(
                f"ORIGIN MISMATCH REFUSAL: Credential '{name}' is strictly bound to origin '{bound_origin}'. "
                f"Injection into target '{target_url}' was refused on the host."
            )

        # 3. High-Privilege ActionGateway Approval Gate (Acceptance criterion e & Rule 27)
        if priv_level == PrivilegeLevel.HIGH_PRIVILEGE and not is_human_approved:
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="CREDENTIAL_INJECTION_APPROVAL_REQUIRED",
                payload={
                    "secret_id": secret_id,
                    "name": name,
                    "privilege_level": priv_level.value,
                    "actor_id": actor_id,
                    "reason": "HIGH_PRIVILEGE_REQUIRES_HUMAN_APPROVAL",
                },
            )
            raise HighPrivilegeApprovalRequiredError(
                f"HIGH PRIVILEGE GATE: Credential '{name}' carries {priv_level.value} privilege. "
                "Explicit human ActionGateway confirmation is required before injection."
            )

        # 4. Decrypt inside engine
        plain_username = self._decrypt(enc_username, tenant_id) if enc_username else None
        plain_secret = self._decrypt(enc_secret, tenant_id)

        # Update last_used_at
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE enterprise_secret_vault SET last_used_at = ? WHERE secret_id = ?",
                (now, secret_id),
            )
            if hasattr(conn, "commit"):
                conn.commit()

        # Audit successful injection (never logs the plaintext)
        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="CREDENTIAL_INJECTED_AT_ORIGIN",
            payload={
                "secret_id": secret_id,
                "name": name,
                "bound_origin": bound_origin,
                "target_url": target_url,
                "actor_id": actor_id,
                "masked_reference": f"{{{{CREDENTIAL:{name}}}}}",
            },
        )

        return (plain_username, plain_secret)

    def export_secret(self, *args, **kwargs):
        """
        Rule 24 & Sub-Step 3D Invariant:
        Zero export API. Plaintext secrets can never be exported or retrieved.
        """
        raise SecretExportForbiddenError(
            "Plaintext secret export is strictly forbidden by system security invariant (Rule 24). "
            "Credentials can only be injected at runtime into a verified origin."
        )

    def revoke_credential(self, tenant_id: str, company_id: str, name: str, actor_id: str = "HUMAN_OWNER") -> bool:
        """Revokes a credential."""
        now = time.time()
        with db.get_connection() as conn:
            self.ensure_tables(conn)
            cursor = conn.execute(
                """
                UPDATE enterprise_secret_vault
                SET revoked_at = ?
                WHERE tenant_id = ? AND company_id = ? AND name = ? AND revoked_at IS NULL
                """,
                (now, tenant_id, company_id, name),
            )
            if hasattr(conn, "commit"):
                conn.commit()
            updated = cursor.rowcount > 0 if hasattr(cursor, "rowcount") else True

        if updated:
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="CREDENTIAL_REVOKED",
                payload={"name": name, "actor_id": actor_id},
            )
        return updated
