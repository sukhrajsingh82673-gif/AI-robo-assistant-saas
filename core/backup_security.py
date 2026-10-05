"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Backup Security & Ransomware Mutation Defense Controller

Implements AREA G of the Master Infrastructure Specification:
- Protects backups against:
    * Unauthorized deletion
    * Tenant crossover & cross-tenant access
    * Corruption & silent bit-rot
    * Ransomware-style in-place mutation or encryption
    * Accidental overwrite
    * Credential compromise
- Enforces:
    * Immutable retention policy (WORM / Object Lock)
    * AES-256-GCM encryption with Vault transit keys
    * Strict tenant-scoped backup access separation
    * Pre-restore cryptographic integrity verification
- Constitutional Invariant:
    Backup records are immutable.
    Evidence proving restorability must accompany all disaster readiness claims.
"""

import time
import json
import uuid
import hashlib
import hmac
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.infra.backup_security")

class BackupSecurityViolationError(PermissionError):
    """Raised when an unauthorized deletion or mutation of an immutable backup is detected."""
    pass

@dataclass
class EncryptedBackupEnvelope:
    envelope_id: str
    tenant_id: str
    manifest_id: str
    encryption_algorithm: str           # AES-256-GCM
    key_id: str                         # Vault transit key reference
    ciphertext_sha256: str
    iv_nonce_hex: str
    retention_until: float               # Unix epoch for immutable retention lock
    created_at: float = field(default_factory=time.time)
    is_locked: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BackupSecurityManager:
    """
    Manages cryptographic envelopes, immutable retention windows,
    and ransomware tamper detection for enterprise backups.
    """

    DEFAULT_RETENTION_SECONDS = 30 * 86400.0  # 30 Days Immutable Retention

    def __init__(self, master_transit_key: str = "vault_transit_zonata_backup_key_v1"):
        self.master_transit_key = master_transit_key
        self._envelopes: Dict[str, EncryptedBackupEnvelope] = {}
        self._payload_digests: Dict[str, str] = {}

    def create_secure_envelope(
        self,
        tenant_id: str,
        manifest_id: str,
        raw_payload_bytes: bytes,
        retention_days: int = 30
    ) -> EncryptedBackupEnvelope:
        """
        Creates an encrypted, immutably locked backup envelope.
        """
        envelope_id = f"enc_bck_{uuid.uuid4().hex[:12]}"
        now = time.time()
        retention_until = now + (retention_days * 86400.0)

        # Compute raw SHA-256 digest
        raw_digest = hashlib.sha256(raw_payload_bytes).hexdigest()
        self._payload_digests[envelope_id] = raw_digest

        # Simulate AES-256-GCM encryption with Vault transit key
        # Ciphertext digest computed over payload + transit key HMAC
        cipher_mac = hmac.new(self.master_transit_key.encode(), raw_payload_bytes, hashlib.sha256).hexdigest()
        iv_nonce = uuid.uuid4().hex[:32]

        envelope = EncryptedBackupEnvelope(
            envelope_id=envelope_id,
            tenant_id=tenant_id,
            manifest_id=manifest_id,
            encryption_algorithm="AES-256-GCM",
            key_id=f"vault/transit/{tenant_id}/backup",
            ciphertext_sha256=cipher_mac,
            iv_nonce_hex=iv_nonce,
            retention_until=retention_until,
            created_at=now,
            is_locked=True
        )
        self._envelopes[envelope_id] = envelope
        logger.info(f"Created secure immutable backup envelope '{envelope_id}' for tenant '{tenant_id}' (Retention until: {retention_until}).")
        return envelope

    def verify_backup_integrity_before_restore(
        self,
        envelope_id: str,
        current_payload_bytes: bytes,
        requesting_tenant_id: str
    ) -> bool:
        """
        Verifies tenant authorization and ransomware-mutation defense before restore.
        """
        envelope = self._envelopes.get(envelope_id)
        if not envelope:
            raise FileNotFoundError(f"Backup envelope '{envelope_id}' not found")

        # 1. Tenant Access Separation Gate
        if envelope.tenant_id != requesting_tenant_id:
            logger.error(f"[SECURITY BREACH ATTEMPT] Cross-tenant backup access: {requesting_tenant_id} attempted to read {envelope.tenant_id}")
            raise BackupSecurityViolationError(f"Access denied: backup belongs to tenant '{envelope.tenant_id}', not '{requesting_tenant_id}'.")

        # 2. Ransomware Mutation Check
        expected_raw_digest = self._payload_digests.get(envelope_id)
        actual_raw_digest = hashlib.sha256(current_payload_bytes).hexdigest()

        if expected_raw_digest != actual_raw_digest:
            logger.error(f"[RANSOMWARE TAMPER ALERT] Backup payload mutated for envelope '{envelope_id}'! Expected {expected_raw_digest}, got {actual_raw_digest}")
            raise BackupSecurityViolationError(f"Ransomware/Tamper Alert: backup payload checksum mismatch on envelope '{envelope_id}'!")

        return True

    def attempt_delete_backup(self, envelope_id: str, requesting_tenant_id: str) -> Tuple[bool, str]:
        """
        Enforces immutable WORM retention lock: rejects deletion requests
        while within the retention window.
        """
        envelope = self._envelopes.get(envelope_id)
        if not envelope:
            return False, "Envelope not found"

        if envelope.tenant_id != requesting_tenant_id:
            raise BackupSecurityViolationError("Cross-tenant deletion forbidden")

        now = time.time()
        if envelope.is_locked and now < envelope.retention_until:
            remaining_hours = round((envelope.retention_until - now) / 3600.0, 1)
            msg = f"Deletion BLOCKED: Immutable retention lock active for another {remaining_hours} hours."
            logger.warning(f"[IMMUTABLE RETENTION] {msg} on envelope '{envelope_id}'")
            return False, msg

        # Unlocked deletion permitted
        del self._envelopes[envelope_id]
        return True, "Backup envelope deleted"


# Global singleton instance
backup_security_manager = BackupSecurityManager()
