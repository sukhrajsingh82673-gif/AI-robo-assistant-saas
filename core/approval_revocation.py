"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Enterprise Approval Lifecycle & Revocation Engine
Enforces time-bound, specific, non-transferable human approvals with real-time revocation.
"""

import time
import uuid
import hashlib
import json
import logging
from typing import Dict, List, Optional, Any
from .db import db

logger = logging.getLogger("zonata.approvals")

class ApprovalDeniedException(Exception):
    """Raised when an operation lacks valid approval or approval was revoked."""
    pass

class ApprovalRevocationEngine:
    """
    Guarantees that actions queued with prior approval are denied if approval is revoked
    before or during execution.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._ensure_table()

    def _ensure_table(self):
        with db.get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS enterprise_action_approvals (
                approval_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                approver_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'APPROVED', -- APPROVED, REVOKED, EXPIRED, CONSUMED
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                revoked_at REAL,
                revoked_by TEXT,
                consumed_at REAL,
                FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
            );
            """)
            conn.commit()

    def grant_approval(
        self,
        company_id: str,
        action_type: str,
        action_payload: Dict[str, Any],
        approver_id: str = "HUMAN_OWNER",
        validity_seconds: float = 3600.0
    ) -> str:
        """Issues a scoped, time-bound cryptographic approval."""
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        payload_hash = hashlib.sha256(json.dumps(action_payload, sort_keys=True).encode("utf-8")).hexdigest()
        now = time.time()
        expires_at = now + validity_seconds

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO enterprise_action_approvals (
                    approval_id, tenant_id, company_id, action_type,
                    payload_hash, approver_id, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?, ?)
            """, (approval_id, self.tenant_id, company_id, action_type, payload_hash, approver_id, now, expires_at))
            conn.commit()

        return approval_id

    def revoke_approval(
        self,
        approval_id: str,
        revoked_by: str = "HUMAN_OWNER",
        reason: str = "Owner emergency revocation"
    ) -> bool:
        """Revokes an active approval immediately."""
        now = time.time()
        with db.get_connection() as conn:
            res = conn.execute("""
                UPDATE enterprise_action_approvals
                SET status = 'REVOKED', revoked_at = ?, revoked_by = ?
                WHERE approval_id = ? AND tenant_id = ? AND status = 'APPROVED'
            """, (now, revoked_by, approval_id, self.tenant_id))
            conn.commit()
            if res.rowcount > 0:
                logger.warning(f"APPROVAL REVOKED: approval_id={approval_id} by {revoked_by}. Reason: {reason}")
                return True
            return False

    def validate_and_consume_approval(
        self,
        approval_id: str,
        company_id: str,
        action_type: str,
        action_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates approval validity and consumes it atomically.
        Raises ApprovalDeniedException on revocation, expiry, or parameter mismatch.
        """
        now = time.time()
        payload_hash = hashlib.sha256(json.dumps(action_payload, sort_keys=True).encode("utf-8")).hexdigest()

        with db.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM enterprise_action_approvals
                WHERE approval_id = ? AND tenant_id = ?
            """, (approval_id, self.tenant_id)).fetchone()

            if not row:
                raise ApprovalDeniedException(f"Approval '{approval_id}' not found.")

            status = row["status"]
            if status == "REVOKED":
                raise ApprovalDeniedException(f"Execution DENIED: Approval '{approval_id}' was REVOKED at {row['revoked_at']} by {row['revoked_by']}.")

            if status == "EXPIRED" or now > row["expires_at"]:
                conn.execute("UPDATE enterprise_action_approvals SET status = 'EXPIRED' WHERE approval_id = ?", (approval_id,))
                conn.commit()
                raise ApprovalDeniedException(f"Execution DENIED: Approval '{approval_id}' has EXPIRED.")

            if status == "CONSUMED":
                raise ApprovalDeniedException(f"Execution DENIED: Single-use approval '{approval_id}' has already been consumed.")

            # Cross-action and payload validation
            if row["company_id"] != company_id:
                raise ApprovalDeniedException(f"Approval company mismatch: expected {row['company_id']}, got {company_id}.")

            if row["action_type"] != action_type:
                raise ApprovalDeniedException(f"Approval action mismatch: approved for '{row['action_type']}', but attempting '{action_type}'.")

            if row["payload_hash"] != payload_hash:
                raise ApprovalDeniedException("Approval payload tampering detected! Parameters do not match authorized approval.")

            # Mark CONSUMED
            conn.execute("""
                UPDATE enterprise_action_approvals
                SET status = 'CONSUMED', consumed_at = ?
                WHERE approval_id = ?
            """, (now, approval_id))
            conn.commit()

            return {
                "authorized": True,
                "approval_id": approval_id,
                "approver_id": row["approver_id"],
                "consumed_at": now
            }
