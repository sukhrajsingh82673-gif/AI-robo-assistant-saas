"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 11 — Workstream B: Cryptographic Approvals & Anti-Replay Gate for High-Risk Actions
Guarantees canonical action hashing, HMAC cryptographic signatures, and atomic single-use nonce consumption.

Constitutional Invariants:
  APPROVAL(A) != AUTHORIZATION(B)
  ACTION_PARAMETER_TAMPERING_INVALIDATES_APPROVAL
  ONE_TIME_NONCE_CONSUMPTION_PREVENTS_REPLAY
  HIGH_RISK_AND_FINANCIAL_ACTIONS_MANDATE_CRYPTOGRAPHIC_APPROVAL
"""

import os
import time
import json
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.db import db

logger = logging.getLogger("zonata.governance.approvals")

class HighRiskActionClass(str, Enum):
    MUTATING = "MUTATING"
    HIGH_RISK = "HIGH_RISK"
    FINANCIAL = "FINANCIAL"
    DESTRUCTIVE = "DESTRUCTIVE"
    IRREVERSIBLE = "IRREVERSIBLE"

class ApprovalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

class CryptographicApprovalException(PermissionError):
    """Base exception for cryptographic approval failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}

class ActionTamperingException(CryptographicApprovalException):
    """Raised when parameters or targets are modified after approval issuance."""
    pass

class SignatureVerificationException(CryptographicApprovalException):
    """Raised when an HMAC cryptographic signature fails validation."""
    pass

class ReplayAttackException(CryptographicApprovalException):
    """Raised when a single-use approval certificate/nonce is replayed."""
    pass

class ApprovalExpiredException(CryptographicApprovalException):
    """Raised when an approval certificate has expired."""
    pass

class ApprovalRevokedException(CryptographicApprovalException):
    """Raised when an approval has been revoked prior to execution."""
    pass

class ApprovalMissingException(CryptographicApprovalException):
    """Raised when a high-risk or financial action lacks mandatory cryptographic approval."""
    pass

@dataclass
class ApprovalCertificate:
    approval_id: str
    tenant_id: str
    action_digest: str
    approver_id: str
    approver_role: str
    nonce: str
    issued_at: float
    expires_at: float
    signature: str
    risk_class: str
    status: str = "ACTIVE"
    consumed_at: Optional[float] = None
    consumed_by_action_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalCertificate':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

class CryptographicApprovalEngine:
    """
    Cryptographic Human Approval & Anti-Replay Engine.
    Seals high-risk action envelopes with HMAC-SHA256 signatures and tracks single-use nonces in PostgreSQL/SQLite.
    """
    _table_initialized = False

    def __init__(self, secret_key: Optional[str] = None):
        self._secret = secret_key or self._resolve_secret()
        self._ensure_tables()

    def _resolve_secret(self) -> str:
        s = (
            os.environ.get("ZONATA_APPROVAL_SECRET") or
            os.environ.get("ZONATA_AUTH_SECRET") or
            os.environ.get("JWT_SECRET") or
            os.environ.get("SESSION_SECRET") or
            "zonata_cryptographic_approval_master_secret_2026_canonical"
        )
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    def _ensure_tables(self):
        if CryptographicApprovalEngine._table_initialized:
            return
        try:
            with db.get_connection() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS action_approval_nonces (
                    nonce TEXT PRIMARY KEY,
                    approval_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    action_digest TEXT NOT NULL,
                    approver_id TEXT NOT NULL,
                    approver_role TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    risk_class TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    issued_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed_at REAL,
                    consumed_by_action_id TEXT,
                    metadata JSON,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_appr_nonce_tenant ON action_approval_nonces(tenant_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_appr_nonce_status ON action_approval_nonces(status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_appr_nonce_digest ON action_approval_nonces(action_digest);")
                conn.commit()
                CryptographicApprovalEngine._table_initialized = True
        except Exception as e:
            logger.debug(f"Approval nonces table initialization deferred: {e}")

    @classmethod
    def compute_action_digest(cls, action_payload: Dict[str, Any]) -> str:
        """
        Calculates a deterministic SHA-256 digest of canonical action attributes.
        Any modification to tenant, company, agent, target, capability, intent, or parameters
        produces an entirely distinct digest.
        """
        canonical_dict = {
            "action_id": action_payload.get("action_id", ""),
            "agent_id": action_payload.get("agent_id", ""),
            "capability_id": action_payload.get("capability_id", ""),
            "company_id": action_payload.get("company_id", ""),
            "intent": action_payload.get("intent", ""),
            "parameters": action_payload.get("parameters", {}) or {},
            "risk_class": action_payload.get("risk_class", "LOW_RISK"),
            "target": action_payload.get("target", ""),
            "tenant_id": action_payload.get("tenant_id", "")
        }
        canonical_str = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def issue_approval(
        self,
        action_payload: Dict[str, Any],
        approver_id: str,
        approver_role: str,
        ttl_seconds: float = 3600.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalCertificate:
        """
        Cryptographically signs an action envelope, issues a single-use nonce, and registers it.
        """
        self._ensure_tables()
        tenant_id = action_payload.get("tenant_id", "")
        risk_class = action_payload.get("risk_class", "MUTATING")
        action_digest = self.compute_action_digest(action_payload)

        now = time.time()
        expires_at = now + ttl_seconds
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        nonce = f"nonce_{uuid.uuid4().hex[:16]}"

        sig_payload = f"{tenant_id}:{action_digest}:{approver_id}:{approver_role}:{nonce}:{now:.4f}:{expires_at:.4f}:{risk_class}"
        signature = hmac.new(
            self._secret.encode("utf-8"),
            sig_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        cert = ApprovalCertificate(
            approval_id=approval_id,
            tenant_id=tenant_id,
            action_digest=action_digest,
            approver_id=approver_id,
            approver_role=approver_role,
            nonce=nonce,
            issued_at=now,
            expires_at=expires_at,
            signature=signature,
            risk_class=risk_class,
            status="ACTIVE",
            metadata=metadata or {}
        )

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO action_approval_nonces (
                    nonce, approval_id, tenant_id, action_digest, approver_id,
                    approver_role, signature, risk_class, status, issued_at,
                    expires_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
            """, (
                nonce, approval_id, tenant_id, action_digest, approver_id,
                approver_role, signature, risk_class, now, expires_at,
                json.dumps(metadata or {})
            ))
            conn.commit()

        logger.info(f"Issued cryptographic approval {approval_id} for action digest {action_digest[:12]} (nonce: {nonce[:10]})")
        return cert

    def verify_and_consume_approval(
        self,
        action_payload: Dict[str, Any],
        certificate: ApprovalCertificate,
        consuming_action_id: str
    ) -> Dict[str, Any]:
        """
        Enforces cryptographic verification and atomic single-use consumption.
        Fails closed on signature tampering, parameter alteration, expiration, revocation, or replay.
        """
        self._ensure_tables()
        now = time.time()
        risk_class = action_payload.get("risk_class", "LOW_RISK")

        # 1. Digest calculation & tampering detection
        expected_digest = self.compute_action_digest(action_payload)
        if expected_digest != certificate.action_digest:
            raise ActionTamperingException(
                f"Action parameter or context tampering detected! "
                f"Computed digest '{expected_digest[:16]}' does not match approved digest '{certificate.action_digest[:16]}'.",
                details={"computed_digest": expected_digest, "approved_digest": certificate.action_digest}
            )

        # 2. Cryptographic signature check
        sig_payload = f"{certificate.tenant_id}:{certificate.action_digest}:{certificate.approver_id}:{certificate.approver_role}:{certificate.nonce}:{certificate.issued_at:.4f}:{certificate.expires_at:.4f}:{certificate.risk_class}"
        expected_sig = hmac.new(
            self._secret.encode("utf-8"),
            sig_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, certificate.signature):
            raise SignatureVerificationException(
                "Cryptographic approval signature verification failed: signature is invalid or forged."
            )

        # 3. Time-bound validity check
        if now > certificate.expires_at:
            raise ApprovalExpiredException(
                f"Approval certificate '{certificate.approval_id}' has expired (expired at {certificate.expires_at}, current: {now})."
            )

        # 4. Atomic Nonce Consumption (Concurrency-safe and anti-replay)
        with db.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE action_approval_nonces
                SET status = 'CONSUMED',
                    consumed_at = ?,
                    consumed_by_action_id = ?
                WHERE nonce = ?
                  AND tenant_id = ?
                  AND status = 'ACTIVE'
                  AND expires_at >= ?
            """, (now, consuming_action_id, certificate.nonce, certificate.tenant_id, now))
            conn.commit()

            if cursor.rowcount == 0:
                # Query state to provide forensic explanation
                row = conn.execute(
                    "SELECT * FROM action_approval_nonces WHERE nonce = ?",
                    (certificate.nonce,)
                ).fetchone()

                if not row:
                    raise CryptographicApprovalException(f"Approval nonce '{certificate.nonce}' was never registered.")

                current_status = row["status"]
                if current_status == "CONSUMED":
                    raise ReplayAttackException(
                        f"REPLAY ATTACK BLOCKED: Nonce '{certificate.nonce}' was already consumed at {row['consumed_at']} "
                        f"by action '{row['consumed_by_action_id']}'."
                    )
                elif current_status == "REVOKED":
                    raise ApprovalRevokedException(f"Execution DENIED: Approval '{row['approval_id']}' was revoked.")
                elif now > row["expires_at"]:
                    raise ApprovalExpiredException(f"Execution DENIED: Approval '{row['approval_id']}' has expired.")
                elif row["tenant_id"] != certificate.tenant_id:
                    raise CryptographicApprovalException("Tenant isolation mismatch on approval nonce.")
                else:
                    raise CryptographicApprovalException("Unable to atomically consume approval nonce.")

        logger.info(f"Consumed approval nonce {certificate.nonce[:10]} for action {consuming_action_id}")
        return {
            "verified": True,
            "approval_id": certificate.approval_id,
            "nonce": certificate.nonce,
            "approver_id": certificate.approver_id,
            "consumed_at": now,
            "consumed_by_action_id": consuming_action_id
        }

    def revoke_approval(self, approval_id: str, tenant_id: str, revoker_id: str, reason: str = "") -> bool:
        """Revokes an active approval immediately."""
        self._ensure_tables()
        with db.get_connection() as conn:
            res = conn.execute("""
                UPDATE action_approval_nonces
                SET status = 'REVOKED'
                WHERE approval_id = ? AND tenant_id = ? AND status = 'ACTIVE'
            """, (approval_id, tenant_id))
            conn.commit()
            if res.rowcount > 0:
                logger.warning(f"Approval '{approval_id}' revoked by '{revoker_id}': {reason}")
                return True
        return False

# Global singleton instance
cryptographic_approvals = CryptographicApprovalEngine()
