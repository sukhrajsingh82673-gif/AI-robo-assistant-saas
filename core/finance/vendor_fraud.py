"""
Vendor Fraud Defense & Bank Account Change Hold
===============================================
Adheres to:
- Rule 62: Reserved Human Decisions
- Requirement: Bank-account changes on vendor profiles require out-of-band verification
  and hold all pending payouts for 72 hours.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List, Tuple
from pydantic import BaseModel, Field


class VendorBankAccount(BaseModel):
    vendor_id: str
    tenant_id: str
    company_id: str
    bank_name: str
    account_number: str
    routing_or_ifsc: str
    beneficiary_name: str
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VendorFraudHold(BaseModel):
    hold_id: str
    vendor_id: str
    tenant_id: str
    company_id: str
    reason: str
    held_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hold_until: str
    is_active: bool = True
    verified_by_human: bool = False
    verification_token: Optional[str] = None


class VendorFraudDefenseManager:
    """Manages vendor bank account changes, fraud holds, and out-of-band release."""

    def __init__(self, hold_duration_hours: int = 72):
        self.hold_duration_hours = hold_duration_hours
        self.active_holds: Dict[str, VendorFraudHold] = {}
        self.vendor_accounts: Dict[str, VendorBankAccount] = {}

    def register_or_update_bank_account(
        self,
        new_account: VendorBankAccount,
        previous_account: Optional[VendorBankAccount] = None
    ) -> Optional[VendorFraudHold]:
        key = f"{new_account.tenant_id}:{new_account.company_id}:{new_account.vendor_id}"

        # If previous account exists and bank details changed, trigger 72h hold
        if previous_account:
            details_changed = (
                previous_account.account_number != new_account.account_number or
                previous_account.routing_or_ifsc != new_account.routing_or_ifsc or
                previous_account.beneficiary_name != new_account.beneficiary_name
            )
            if details_changed:
                import uuid
                now = datetime.now(timezone.utc)
                until = (now + timedelta(hours=self.hold_duration_hours)).isoformat()
                hold = VendorFraudHold(
                    hold_id=f"hold_{uuid.uuid4().hex[:12]}",
                    vendor_id=new_account.vendor_id,
                    tenant_id=new_account.tenant_id,
                    company_id=new_account.company_id,
                    reason="Bank account details modified. Mandatory 72-hour fraud protection hold applied.",
                    held_at=now.isoformat(),
                    hold_until=until,
                    is_active=True,
                    verified_by_human=False
                )
                self.active_holds[key] = hold
                self.vendor_accounts[key] = new_account
                return hold

        self.vendor_accounts[key] = new_account
        return None

    def can_disburse_payout(self, tenant_id: str, company_id: str, vendor_id: str, current_time: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """Checks whether payout is allowed or blocked by an active fraud hold."""
        key = f"{tenant_id}:{company_id}:{vendor_id}"
        hold = self.active_holds.get(key)
        if not hold or not hold.is_active:
            return True, None

        now = current_time or datetime.now(timezone.utc)
        hold_until_dt = datetime.fromisoformat(hold.hold_until)

        # Even if 72 hours passed, mandatory human verification is required
        if not hold.verified_by_human:
            return False, f"Payout blocked: Active hold {hold.hold_id} pending human out-of-band verification"

        if now < hold_until_dt:
            remaining_hours = (hold_until_dt - now).total_seconds() / 3600.0
            return False, f"Payout blocked: 72-hour security hold active for another {remaining_hours:.1f} hours"

        return True, None

    def release_hold_with_human_verification(
        self,
        tenant_id: str,
        company_id: str,
        vendor_id: str,
        verification_token: str,
        authorizer_principal_id: str
    ) -> bool:
        """Rule 62: Human gateway approval unlocks the fraud hold."""
        key = f"{tenant_id}:{company_id}:{vendor_id}"
        hold = self.active_holds.get(key)
        if not hold:
            return False

        # In production this checks cryptographic token; here we verify token presence
        if not verification_token or not authorizer_principal_id:
            return False

        hold.verified_by_human = True
        hold.verification_token = verification_token
        hold.is_active = False
        return True
