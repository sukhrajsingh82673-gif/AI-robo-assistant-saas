"""
Month-End Close Workflow Engine (Deterministic Financial Period Closure)
========================================================================
Steps:
1. AP Cutoff Verification
2. AR Cutoff Verification
3. Fixed Asset Depreciation Calculation
4. Bank Reconciliation Complete Signoff
5. Intercompany Eliminations
6. Trial Balance Verification (Total Debits == Total Credits)
7. Period Lock & Financial Statement Generation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class TrialBalanceAccount(BaseModel):
    account_code: str
    account_name: str
    debit_total: float
    credit_total: float


class TrialBalanceResult(BaseModel):
    total_debits: float
    total_credits: float
    is_balanced: bool
    imbalance_amount: float
    accounts: List[TrialBalanceAccount]


class MonthEndCloseState(BaseModel):
    period: str  # e.g. "2026-10"
    tenant_id: str
    company_id: str
    ap_cutoff_passed: bool = False
    ar_cutoff_passed: bool = False
    depreciation_completed: bool = False
    bank_rec_signed_off: bool = False
    intercompany_eliminated: bool = False
    trial_balance_verified: bool = False
    period_locked: bool = False
    locked_at: Optional[str] = None
    locked_by_principal: Optional[str] = None
    step_history: List[str] = Field(default_factory=list)


class MonthEndCloseEngine:
    """Orchestrates month-end close validation, balancing, and immutable period locking."""

    def __init__(self, tenant_id: str, company_id: str, period: str):
        self.state = MonthEndCloseState(tenant_id=tenant_id, company_id=company_id, period=period)

    def execute_ap_cutoff(self, unposted_invoices_count: int) -> bool:
        if unposted_invoices_count > 0:
            raise ValueError(f"AP Cutoff failed: {unposted_invoices_count} unposted/unmatched invoices remain")
        self.state.ap_cutoff_passed = True
        self.state.step_history.append(f"AP_CUTOFF_VERIFIED:{datetime.now(timezone.utc).isoformat()}")
        return True

    def execute_ar_cutoff(self, pending_billing_runs: int) -> bool:
        if pending_billing_runs > 0:
            raise ValueError(f"AR Cutoff failed: {pending_billing_runs} billing runs pending")
        self.state.ar_cutoff_passed = True
        self.state.step_history.append(f"AR_CUTOFF_VERIFIED:{datetime.now(timezone.utc).isoformat()}")
        return True

    def execute_depreciation(self, assets_count: int, total_depreciation: float) -> float:
        self.state.depreciation_completed = True
        self.state.step_history.append(f"DEPRECIATION_POSTED:{assets_count}_assets:{total_depreciation}_amount")
        return total_depreciation

    def signoff_bank_rec(self, unreviewed_exceptions: int) -> bool:
        if unreviewed_exceptions > 0:
            raise ValueError(f"Bank reconciliation signoff rejected: {unreviewed_exceptions} unreviewed exceptions")
        self.state.bank_rec_signed_off = True
        self.state.step_history.append(f"BANK_REC_SIGNOFF:{datetime.now(timezone.utc).isoformat()}")
        return True

    def execute_intercompany_eliminations(self, cross_entity_balances: Dict[str, float]) -> float:
        eliminated_total = sum(cross_entity_balances.values())
        self.state.intercompany_eliminated = True
        self.state.step_history.append(f"INTERCOMPANY_ELIMINATED:{eliminated_total}")
        return eliminated_total

    def verify_trial_balance(self, accounts: List[TrialBalanceAccount]) -> TrialBalanceResult:
        total_debits = round(sum(a.debit_total for a in accounts), 2)
        total_credits = round(sum(a.credit_total for a in accounts), 2)
        diff = round(abs(total_debits - total_credits), 2)
        balanced = diff < 0.01

        if not balanced:
            raise ValueError(f"Trial balance out of balance: Debits={total_debits}, Credits={total_credits}, Imbalance={diff}")

        self.state.trial_balance_verified = True
        self.state.step_history.append(f"TRIAL_BALANCE_VERIFIED:Debits={total_debits}:Credits={total_credits}")
        return TrialBalanceResult(
            total_debits=total_debits,
            total_credits=total_credits,
            is_balanced=balanced,
            imbalance_amount=diff,
            accounts=accounts
        )

    def lock_period(self, principal_id: str) -> MonthEndCloseState:
        """Locks period immutably. Requires all previous steps to have succeeded."""
        if not (
            self.state.ap_cutoff_passed and
            self.state.ar_cutoff_passed and
            self.state.depreciation_completed and
            self.state.bank_rec_signed_off and
            self.state.intercompany_eliminated and
            self.state.trial_balance_verified
        ):
            raise RuntimeError("Cannot lock financial period: one or more close verification steps are incomplete")

        self.state.period_locked = True
        self.state.locked_at = datetime.now(timezone.utc).isoformat()
        self.state.locked_by_principal = principal_id
        self.state.step_history.append(f"PERIOD_LOCKED_BY:{principal_id}:{self.state.locked_at}")
        return self.state
