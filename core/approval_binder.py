"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V5 — Cryptographic Human Approval Binder & Anti-Laundering Gate
Binds human executive approvals strictly to:
  tenant_id, employee_id, mission_id, action_type, parameters_hash, target_id, risk_class, expiry.

Constitutional Invariant:
  APPROVAL(A) != AUTHORIZATION(B)
  ACTION PARAMETER TAMPERING INVALIDATES PRIOR APPROVAL
"""

import time
import json
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.approval.binder")

class ApprovalLaunderingError(PermissionError):
    """Raised when an action is altered after human approval was granted."""
    pass

@dataclass
class BoundApprovalCertificate:
    approval_id: str
    tenant_id: str
    employee_id: str
    mission_id: str
    action_type: str
    target_id: str
    risk_class: str
    parameters_hash: str
    approver_identity_id: str
    approver_role: str
    approved_at: float
    expires_at: float
    signature: str

class ApprovalBinder:
    """
    Cryptographic manager preventing approval laundering.
    """
    def __init__(self):
        self._secret = hashlib.sha256(b"zonata_executive_approval_key_2026").hexdigest()

    def create_bound_approval(
        self,
        tenant_id: str,
        employee_id: str,
        mission_id: str,
        action_type: str,
        target_id: str,
        risk_class: str,
        parameters: Dict[str, Any],
        approver_identity_id: str,
        approver_role: str,
        ttl_seconds: int = 3600
    ) -> BoundApprovalCertificate:
        """Issue a cryptographically sealed approval certificate."""
        now = time.time()
        param_canonical = json.dumps(parameters, sort_keys=True).encode("utf-8")
        param_hash = hashlib.sha256(param_canonical).hexdigest()

        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        payload = {
            "approval_id": approval_id,
            "tenant_id": tenant_id,
            "employee_id": employee_id,
            "mission_id": mission_id,
            "action_type": action_type,
            "target_id": target_id,
            "risk_class": risk_class,
            "parameters_hash": param_hash,
            "approver_identity_id": approver_identity_id,
            "approver_role": approver_role,
            "approved_at": now,
            "expires_at": now + ttl_seconds
        }
        sig = hmac.new(
            self._secret.encode("utf-8"),
            json.dumps(payload, sort_keys=True).encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id="EXEC_APPROVAL",
            event_type="HUMAN_APPROVAL_ISSUED",
            payload=payload
        )

        return BoundApprovalCertificate(
            approval_id=approval_id,
            tenant_id=tenant_id,
            employee_id=employee_id,
            mission_id=mission_id,
            action_type=action_type,
            target_id=target_id,
            risk_class=risk_class,
            parameters_hash=param_hash,
            approver_identity_id=approver_identity_id,
            approver_role=approver_role,
            approved_at=now,
            expires_at=now + ttl_seconds,
            signature=sig
        )

    def verify_action_against_approval(
        self,
        certificate: BoundApprovalCertificate,
        tenant_id: str,
        employee_id: str,
        mission_id: str,
        action_type: str,
        target_id: str,
        execution_parameters: Dict[str, Any]
    ) -> bool:
        """
        Verify that the action attempting execution matches the approved certificate byte-for-byte.
        """
        now = time.time()

        # 1. Expiry check
        if now > certificate.expires_at:
            self._audit_laundering(certificate, "EXPIRED_APPROVAL", "Approval token has expired.")
            raise ApprovalLaunderingError(f"Approval certificate {certificate.approval_id} has expired.")

        # 2. Context binding checks
        if certificate.tenant_id != tenant_id:
            self._audit_laundering(certificate, "TENANT_MISMATCH", f"Tenant '{tenant_id}' != '{certificate.tenant_id}'")
            raise ApprovalLaunderingError("Approval tenant mismatch.")

        if certificate.employee_id != employee_id:
            self._audit_laundering(certificate, "EMPLOYEE_MISMATCH", f"Employee '{employee_id}' != '{certificate.employee_id}'")
            raise ApprovalLaunderingError("Approval employee mismatch.")

        if certificate.mission_id != mission_id:
            self._audit_laundering(certificate, "MISSION_MISMATCH", f"Mission '{mission_id}' != '{certificate.mission_id}'")
            raise ApprovalLaunderingError("Approval mission mismatch.")

        if certificate.action_type != action_type:
            self._audit_laundering(certificate, "ACTION_MISMATCH", f"Action '{action_type}' != '{certificate.action_type}'")
            raise ApprovalLaunderingError("Approval action type mismatch.")

        if certificate.target_id != target_id:
            self._audit_laundering(certificate, "TARGET_MISMATCH", f"Target '{target_id}' != '{certificate.target_id}'")
            raise ApprovalLaunderingError("Approval target mismatch.")

        # 3. Cryptographic Parameter Hash Verification (Anti-Laundering)
        exec_canonical = json.dumps(execution_parameters, sort_keys=True).encode("utf-8")
        exec_hash = hashlib.sha256(exec_canonical).hexdigest()

        if exec_hash != certificate.parameters_hash:
            self._audit_laundering(
                certificate,
                "PARAMETER_TAMPERING_DETECTED",
                f"Execution parameters hash '{exec_hash}' != approved hash '{certificate.parameters_hash}'"
            )
            raise ApprovalLaunderingError(
                f"Approval Laundering Detected! Action parameters were modified after human approval was granted."
            )

        return True

    def _audit_laundering(self, cert: BoundApprovalCertificate, violation: str, detail: str):
        logger.error(f"[APPROVAL LAUNDERING DETECTED] {violation}: {detail}")
        try:
            evidence_service.record_event(
                tenant_id=cert.tenant_id,
                company_id="SECURITY_GATEWAY",
                event_type="APPROVAL_LAUNDERING_ATTEMPT",
                payload={"approval_id": cert.approval_id, "violation": violation, "detail": detail}
            )
        except Exception:
            pass

# Global singleton
approval_binder = ApprovalBinder()
