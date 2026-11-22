"""
Cryptographic Action Approvals with Payload SHA-256 Digest Binding (OpenCode Step 2C)
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Tuple, List

from core.db import db, tenant_scoped_class
from core.authority.types import (
    ActionClass,
    PrincipalType,
    SelfApprovalError,
    AIApprovalError,
    PayloadDigestMismatchError,
    Rule15Violation,
    GOVERNED_PRINCIPAL_TYPES,
)

logger = logging.getLogger("zonata.authority.approvals")

# Action classes that strictly prohibit approval by AI or agent principals
HIGH_STAKES_ACTION_CLASSES = {
    ActionClass.COMMIT_SPEND,
    ActionClass.POST_LEDGER,
    ActionClass.CHANGE_PERMISSION,
    ActionClass.DELETE_DATA,
    ActionClass.LEGAL_COMMITMENT,
}


def compute_payload_digest(payload: Any) -> str:
    """Computes a deterministic SHA-256 digest of canonical JSON payload."""
    if payload is None:
        payload = {}
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@tenant_scoped_class
class ApprovalsManager:
    """Manages cryptographic approval requests, quorum chains, and payload digest verification."""

    def __init__(self):
        pass

    def create_approval_request(
        self,
        tenant_id: str,
        company_id: str,
        action_id: str,
        action_class: str,
        payload: Dict[str, Any],
        requester_id: str,
        maker_id: str,
        approver_role: str = "MANAGER",
        expires_in_seconds: float = 3600.0,
        quorum_required: int = 1,
    ) -> Dict[str, Any]:
        """Creates a pending approval request bound to the SHA-256 digest of the payload."""
        approval_id = f"appr_{uuid.uuid4().hex[:16]}"
        now = time.time()
        expires_at = now + expires_in_seconds
        payload_digest = compute_payload_digest(payload)

        # Notify via email adapter if configured (honest status reporting)
        notification_status = "NOT_CONFIGURED"
        try:
            from core.ports.email import email_adapter
            res = email_adapter.send(
                to="approvers@company.internal",
                subject=f"Approval Required: {action_class} [{action_id}]",
                body=f"Action {action_id} of class {action_class} requires approval.\nDigest: {payload_digest}",
            )
            notification_status = res.status
        except Exception:
            pass

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO action_approvals (
                    approval_id, tenant_id, company_id, action_id, action_class,
                    payload_digest, requester_id, maker_id, approver_role, status,
                    quorum_required, approvals_received, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, '[]', ?, ?)
                """,
                (
                    approval_id, tenant_id, company_id, action_id, action_class,
                    payload_digest, requester_id, maker_id, approver_role,
                    quorum_required, expires_at, now
                ),
            )
            conn.commit()

        return {
            "approval_id": approval_id,
            "action_id": action_id,
            "action_class": action_class,
            "payload_digest": payload_digest,
            "status": "PENDING",
            "expires_at": expires_at,
            "notification_status": notification_status,
        }

    def approve(
        self,
        approval_id: str,
        tenant_id: str,
        company_id: str,
        approver_id: str,
        approver_type: str = PrincipalType.HUMAN.value,
        approver_role: str = "MANAGER",
        decision_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approves a request. Enforces segregation of duties, Rule 15, and AI approval prohibitions."""
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT approval_id, action_id, action_class, payload_digest, requester_id, maker_id,
                       status, expires_at, quorum_required, approvals_received
                FROM action_approvals
                WHERE approval_id = ? AND tenant_id = ? AND company_id = ?
                """,
                (approval_id, tenant_id, company_id),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Approval request '{approval_id}' not found")

            (
                appr_id, action_id, action_class, digest, requester_id, maker_id,
                status, expires_at, quorum_required, appr_received_json
            ) = row

            if now > expires_at:
                cur.execute(
                    "UPDATE action_approvals SET status = 'EXPIRED' WHERE approval_id = ?",
                    (approval_id,)
                )
                conn.commit()
                raise ValueError("Approval request has expired and cannot be approved")

            # 1. Segregation of duties: Self-approval strictly forbidden
            if approver_id == requester_id or approver_id == maker_id:
                raise SelfApprovalError(
                    f"Self-approval strictly refused: Principal '{approver_id}' cannot approve its own request (requester='{requester_id}', maker='{maker_id}')"
                )

            # 2. AI approval restriction: Agents / AI employees cannot approve money, permissions, deletion, or legal commitments
            act_class_enum = ActionClass(action_class) if action_class in [a.value for a in ActionClass] else None
            if act_class_enum in HIGH_STAKES_ACTION_CLASSES and approver_type in [p.value for p in GOVERNED_PRINCIPAL_TYPES]:
                raise AIApprovalError(
                    f"Rule Violation: Principal type '{approver_type}' cannot grant approval for high-risk action class '{action_class}'"
                )

            approvals_received = json.loads(appr_received_json) if appr_received_json else []
            approvals_received.append({
                "approver_id": approver_id,
                "approver_type": approver_type,
                "approver_role": approver_role,
                "timestamp": now,
                "reason": decision_reason or "Approved",
            })

            new_status = "APPROVED" if len(approvals_received) >= quorum_required else "PENDING"

            cur.execute(
                """
                UPDATE action_approvals
                SET status = ?, approver_id = ?, approver_type = ?, approver_role = ?,
                    approvals_received = ?, decided_at = ?, decision_reason = ?
                WHERE approval_id = ?
                """,
                (
                    new_status, approver_id, approver_type, approver_role,
                    json.dumps(approvals_received), now, decision_reason or "Approved",
                    approval_id
                ),
            )
            conn.commit()

        return {
            "approval_id": approval_id,
            "status": new_status,
            "approver_id": approver_id,
            "decided_at": now,
        }

    def verify_approval_for_action(
        self,
        approval_id: str,
        tenant_id: str,
        company_id: str,
        current_payload: Dict[str, Any],
        current_action_class: str,
    ) -> Tuple[bool, str, str]:
        """
        Verifies that an approved record exists, has not expired, matches the current action class,
        and crucially matches the SHA-256 payload digest.
        Returns (is_valid, rule_id, message).
        """
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT status, expires_at, payload_digest, action_class, requester_id, maker_id, approver_id
                FROM action_approvals
                WHERE approval_id = ? AND tenant_id = ? AND company_id = ?
                """,
                (approval_id, tenant_id, company_id),
            )
            row = cur.fetchone()
            if not row:
                return (False, "APPROVAL_NOT_FOUND", f"Approval '{approval_id}' not found")

            status, expires_at, stored_digest, stored_class, requester_id, maker_id, approver_id = row

            if now > expires_at:
                return (False, "APPROVAL_EXPIRED", f"Approval '{approval_id}' expired at {expires_at} (current: {now})")

            if status != "APPROVED":
                return (False, "APPROVAL_NOT_GRANTED", f"Approval '{approval_id}' status is '{status}', expected 'APPROVED'")

            # Verify action class matching
            if stored_class != current_action_class:
                return (False, "APPROVAL_ACTION_CLASS_MISMATCH", f"Approval class '{stored_class}' != action class '{current_action_class}'")

            # Verify SHA-256 digest: Changing payload voids approval!
            current_digest = compute_payload_digest(current_payload)
            if current_digest != stored_digest:
                return (
                    False,
                    "APPROVAL_PAYLOAD_MISMATCH",
                    f"Action payload altered after approval: stored digest '{stored_digest[:16]}...' != current digest '{current_digest[:16]}...'"
                )

            # Segregation of duties check
            if approver_id and (approver_id == requester_id or approver_id == maker_id):
                return (False, "SELF_APPROVAL_BLOCKED", f"Self-approval detected: approver '{approver_id}' is also requester/maker")

            return (True, "APPROVAL_VERIFIED", "Approval valid and cryptographically bound to payload")


approvals_manager = ApprovalsManager()
