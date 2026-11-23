"""
ZONATA Sovereign Core — Sub-Step 5C: Ownership Transfer & Account Recovery.
===========================================================================
Governed by:
- Rule 44: The owner principal cannot be minted or elevated by any IdP, SCIM payload,
  API call, agent, or support action. Ownership changes require dual control,
  a cooling-off period, and sealed evidence in the EvidenceLedger.
- Multi-channel account recovery (Rule 44): Email alone is strictly prohibited.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.evidence_ledger import EvidenceLedger
from core.identity.types import (
    DualControlApprovalRequiredError,
    OwnershipTransferCoolingOffError,
    RecoveryForbiddenByEmailAloneError,
    RoleTier,
)


@dataclass
class OwnershipTransferRecord:
    request_id: str
    tenant_id: str
    current_owner_id: str
    target_owner_id: str
    reason: str
    initiated_at: float
    cooling_off_seconds: float
    approvals: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "PENDING"  # PENDING, APPROVED, EXECUTED, CANCELLED
    evidence_package_id: Optional[str] = None
    executed_at: Optional[float] = None


class OwnershipGovernance:
    """Manages high-assurance ownership transfers and recovery under Rule 44."""

    def __init__(self, ledger: Optional[EvidenceLedger] = None):
        self.ledger = ledger or EvidenceLedger()
        self._transfers: Dict[str, OwnershipTransferRecord] = {}

    def initiate_transfer(
        self,
        tenant_id: str,
        current_owner_id: str,
        target_owner_id: str,
        reason: str,
        cooling_off_seconds: float = 86400.0,  # 24 hours default
    ) -> OwnershipTransferRecord:
        """Initiate an ownership transfer under dual control and cooling-off period."""
        if not current_owner_id or not target_owner_id:
            raise ValueError("Current and target owner IDs are required")
        if current_owner_id == target_owner_id:
            raise ValueError("Target owner must be distinct from current owner")

        request_id = f"own_xfer_{uuid.uuid4().hex[:12]}"
        now = time.time()
        record = OwnershipTransferRecord(
            request_id=request_id,
            tenant_id=tenant_id,
            current_owner_id=current_owner_id,
            target_owner_id=target_owner_id,
            reason=reason,
            initiated_at=now,
            cooling_off_seconds=cooling_off_seconds,
            approvals=[
                {
                    "approver_id": current_owner_id,
                    "role": RoleTier.OWNER.value,
                    "timestamp": now,
                    "mfa_verified": True,
                }
            ],
            status="PENDING",
        )
        self._transfers[request_id] = record
        return record

    def approve_transfer(
        self,
        request_id: str,
        approver_id: str,
        approver_role: str,
        mfa_verified: bool = True,
    ) -> OwnershipTransferRecord:
        """Add an independent dual-control approval to the transfer request."""
        record = self._transfers.get(request_id)
        if not record:
            raise KeyError(f"Transfer request {request_id} not found")
        if record.status != "PENDING":
            raise ValueError(f"Cannot approve transfer in status {record.status}")
        if not mfa_verified:
            raise ValueError("Dual-control approval requires MFA verification")

        # Must not be the target owner self-approving
        if approver_id == record.target_owner_id:
            raise DualControlApprovalRequiredError(
                "Target owner cannot self-approve ownership transfer"
            )

        # Must not be duplicate approval by the same user
        for existing in record.approvals:
            if existing["approver_id"] == approver_id:
                raise ValueError(f"Approver {approver_id} has already approved this transfer")

        record.approvals.append(
            {
                "approver_id": approver_id,
                "role": approver_role,
                "timestamp": time.time(),
                "mfa_verified": mfa_verified,
            }
        )

        # If we have at least 2 distinct approvals, mark as APPROVED (waiting for cooling-off)
        if len(record.approvals) >= 2:
            record.status = "APPROVED"

        return record

    def execute_transfer(
        self,
        request_id: str,
        executor_id: str,
        current_time: Optional[float] = None,
    ) -> OwnershipTransferRecord:
        """
        Execute the transfer once dual control is satisfied and cooling-off has elapsed.
        Seals immutable evidence to the audit ledger.
        """
        record = self._transfers.get(request_id)
        if not record:
            raise KeyError(f"Transfer request {request_id} not found")

        # 1. Dual control verification
        if len(record.approvals) < 2 or record.status not in ("PENDING", "APPROVED"):
            raise DualControlApprovalRequiredError(
                f"Rule 44: Ownership transfer requires at least 2 distinct approvals (current: {len(record.approvals)})"
            )

        # 2. Cooling-off timer enforcement
        now = current_time if current_time is not None else time.time()
        cooldown_target = record.initiated_at + record.cooling_off_seconds
        if now < cooldown_target:
            remaining = cooldown_target - now
            raise OwnershipTransferCoolingOffError(
                f"Rule 44: Cooling-off period in effect. {remaining:.1f} seconds remaining before execution allowed."
            )

        # 3. Seal evidence in EvidenceLedger
        ev_package = self.ledger.seal_evidence(
            action_id=record.request_id,
            mission_id=f"mission_own_xfer_{record.tenant_id}",
            agent_id=executor_id,
            verifications=[],
            metadata={
                "type": "OWNERSHIP_TRANSFER",
                "tenant_id": record.tenant_id,
                "old_owner": record.current_owner_id,
                "new_owner": record.target_owner_id,
                "approvals": record.approvals,
                "reason": record.reason,
                "cooling_off_seconds": record.cooling_off_seconds,
            },
        )

        record.status = "EXECUTED"
        record.executed_at = now
        record.evidence_package_id = ev_package.evidence_id
        return record

    @staticmethod
    def verify_recovery_channels(channels: List[str]) -> bool:
        """
        Rule 44: Multi-channel recovery. Rejects if recovery relies on email alone.
        Must include at least one hardware/FIDO2/out-of-band factor.
        """
        normalized = {c.strip().lower() for c in channels}
        if not normalized:
            raise RecoveryForbiddenByEmailAloneError("No recovery channels provided")

        if normalized == {"email"} or (len(normalized) == 1 and "email" in normalized):
            raise RecoveryForbiddenByEmailAloneError(
                "Rule 44 Violation: Owner account recovery requires multi-channel verification "
                "(e.g. email + FIDO2 passkey/hardware security key). Email alone is forbidden."
            )

        # Requires email + at least one strong secondary channel
        strong_channels = {"fido2", "passkey", "webauthn", "hardware_key", "security_council", "phone_totp"}
        if not (normalized & strong_channels):
            raise RecoveryForbiddenByEmailAloneError(
                "Rule 44 Violation: Secondary recovery channel must be a strong hardware/cryptographic authenticator"
            )

        return True
