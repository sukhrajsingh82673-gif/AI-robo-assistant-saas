"""
Billing Lifecycle State Machine (Rule 78).
Guarantees billing failure NEVER deletes data, provides grace period, read-only mode,
export window, and enforces the legal hold invariant.
"""

import time
from enum import Enum
from typing import Dict, Any, Optional, Tuple


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAST_DUE_GRACE = "PAST_DUE_GRACE"
    RESTRICTED_READ_ONLY = "RESTRICTED_READ_ONLY"
    EXPORT_ONLY = "EXPORT_ONLY"
    TERMINATED_PENDING_PURGE = "TERMINATED_PENDING_PURGE"


class BillingLifecycleManager:
    """
    Manages tenant subscription delinquency lifecycle stages.
    """

    DEFAULT_GRACE_PERIOD_DAYS = 14
    DEFAULT_READ_ONLY_DAYS = 30

    def __init__(self):
        # tenant_id -> account status info
        self._accounts: Dict[str, Dict[str, Any]] = {}

    def register_account(self, tenant_id: str, legal_hold: bool = False):
        self._accounts[tenant_id] = {
            "status": AccountStatus.ACTIVE,
            "legal_hold": legal_hold,
            "delinquent_since": None,
            "grace_period_until": None,
            "read_only_until": None,
        }

    def set_legal_hold(self, tenant_id: str, hold: bool):
        """Legal hold status. Under Rule 78, legal holds ALWAYS prevent data purge."""
        if tenant_id in self._accounts:
            self._accounts[tenant_id]["legal_hold"] = hold

    def is_legal_hold(self, tenant_id: str) -> bool:
        return self._accounts.get(tenant_id, {}).get("legal_hold", False)

    def mark_payment_failed(self, tenant_id: str, current_time: Optional[float] = None) -> AccountStatus:
        """
        Initiates delinquency sequence: starts 14-day grace period. Workflows remain active.
        """
        now = current_time if current_time is not None else time.time()
        acc = self._accounts.setdefault(tenant_id, {
            "status": AccountStatus.ACTIVE,
            "legal_hold": False,
        })

        if acc["status"] == AccountStatus.ACTIVE:
            acc["status"] = AccountStatus.PAST_DUE_GRACE
            acc["delinquent_since"] = now
            acc["grace_period_until"] = now + (self.DEFAULT_GRACE_PERIOD_DAYS * 86400)

        return acc["status"]

    def evaluate_lifecycle(self, tenant_id: str, current_time: Optional[float] = None) -> AccountStatus:
        """
        Evaluates elapsed delinquency time and advances account status safely.
        """
        now = current_time if current_time is not None else time.time()
        acc = self._accounts.get(tenant_id)
        if not acc:
            return AccountStatus.ACTIVE

        status = acc["status"]
        grace_until = acc.get("grace_period_until")
        read_only_until = acc.get("read_only_until")

        # 1. Grace period expiry -> RESTRICTED_READ_ONLY
        if status == AccountStatus.PAST_DUE_GRACE and grace_until and now >= grace_until:
            acc["status"] = AccountStatus.RESTRICTED_READ_ONLY
            acc["read_only_until"] = now + (self.DEFAULT_READ_ONLY_DAYS * 86400)
            status = AccountStatus.RESTRICTED_READ_ONLY

        # 2. Read-only expiry -> EXPORT_ONLY
        if status == AccountStatus.RESTRICTED_READ_ONLY and read_only_until and now >= read_only_until:
            acc["status"] = AccountStatus.EXPORT_ONLY
            status = AccountStatus.EXPORT_ONLY

        return status

    def can_purge_tenant_data(self, tenant_id: str) -> Tuple[bool, str]:
        """
        Rule 78 verification: Data purge check.
        Legal holds ALWAYS win and block deletion. Active/grace/read-only tenants cannot be purged.
        """
        acc = self._accounts.get(tenant_id)
        if not acc:
            return False, "Tenant does not exist."

        if acc.get("legal_hold"):
            return False, "DENIED: Tenant is under active Legal Hold. Data preservation is legally mandated."

        if acc["status"] in (AccountStatus.ACTIVE, AccountStatus.PAST_DUE_GRACE, AccountStatus.RESTRICTED_READ_ONLY):
            return False, f"DENIED: Cannot purge data in status '{acc['status']}'. Customer data must be retained."

        if acc["status"] == AccountStatus.EXPORT_ONLY:
            return False, "DENIED: Tenant is in Export Window. Customer has mandatory right to data export."

        if acc["status"] == AccountStatus.TERMINATED_PENDING_PURGE:
            return True, "Purge authorized: tenant subscription fully terminated without legal hold."

        return False, "DENIED: Unknown status."
