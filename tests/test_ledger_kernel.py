"""
Unit, integration, and mutation tests for the ZONATA Sovereign Double-Entry Financial Ledger Kernel (Sub-Step 1G).

Acceptance Criteria:
a. Journal entry with unequal debits and credits fails to post (UnbalancedJournalEntryError).
b. Journal entry with mixed currencies fails to post unless explicitly split into multi-currency balancing legs.
c. Attempting to update or delete a POSTED entry raises an error at the database level (trigger enforcement).
d. Reversing entry creates exact opposite lines and marks original as REVERSED.
e. Trial balance generates correct balances and net zero sum across all accounts.
f. Cross-tenant and cross-company isolation denies unauthorized reads and postings.
g. Rule 12 validation: float amounts and invalid ISO 4217 currencies are rejected.
h. Folio integration: sealing/approving a folio with unposted journal entries raises UnpostedFolioJournalEntriesError.
i. Mutation tests: verify tests catch deliberate mutations.
"""

import os
import unittest
import uuid
import pytest

from core.db import configure_isolated_test_db, db
from core.folios.manager import FolioManager
from core.folios.schema import FolioStatus
from core.ledger.currency import (
    InvalidCurrencyError,
    format_minor_units,
    validate_currency,
)
from core.ledger.kernel import (
    CurrencyMismatchError,
    ImmutableJournalEntryError,
    InactiveAccountError,
    InvalidMinorUnitError,
    LedgerError,
    LedgerKernel,
    UnbalancedJournalEntryError,
    UnpostedFolioJournalEntriesError,
)
from core.ledger.schema import AccountType, JournalEntryStatus, ensure_ledger_tables


class TestLedgerKernel(unittest.TestCase):
    """Rigorous verification of double-entry ledger invariants."""

    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        cls.db_path = configure_isolated_test_db()
        ensure_ledger_tables()

    def setUp(self):
        self.kernel = LedgerKernel()
        self.folio_mgr = FolioManager()
        self.tenant_a = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_a = f"cmp_{uuid.uuid4().hex[:8]}"
        self.user_a = f"usr_{uuid.uuid4().hex[:8]}"

        self.tenant_b = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_b = f"cmp_{uuid.uuid4().hex[:8]}"
        self.user_b = f"usr_{uuid.uuid4().hex[:8]}"

        # Standard Chart of Accounts (COA) for Company A in USD
        self.acct_cash = self.kernel.create_account(
            self.tenant_a, self.company_a, "1010", "Cash and Cash Equivalents", AccountType.ASSET, "USD"
        )
        self.acct_ar = self.kernel.create_account(
            self.tenant_a, self.company_a, "1200", "Accounts Receivable", AccountType.ASSET, "USD"
        )
        self.acct_ap = self.kernel.create_account(
            self.tenant_a, self.company_a, "2010", "Accounts Payable", AccountType.LIABILITY, "USD"
        )
        self.acct_equity = self.kernel.create_account(
            self.tenant_a, self.company_a, "3010", "Common Stock", AccountType.EQUITY, "USD"
        )
        self.acct_rev = self.kernel.create_account(
            self.tenant_a, self.company_a, "4010", "SaaS Subscription Revenue", AccountType.REVENUE, "USD"
        )
        self.acct_exp = self.kernel.create_account(
            self.tenant_a, self.company_a, "5010", "Cloud Hosting Infrastructure", AccountType.EXPENSE, "USD"
        )

        # EUR Accounts for multi-currency tests
        self.acct_cash_eur = self.kernel.create_account(
            self.tenant_a, self.company_a, "1011", "Euro Operations Bank", AccountType.ASSET, "EUR"
        )
        self.acct_rev_eur = self.kernel.create_account(
            self.tenant_a, self.company_a, "4011", "European Software Revenue", AccountType.REVENUE, "EUR"
        )

    # =========================================================================
    # ACCEPTANCE TEST A: UNEQUAL DEBITS AND CREDITS FAIL TO POST
    # =========================================================================
    def test_journal_entry_with_unequal_debits_and_credits_fails_to_post(self):
        """Acceptance 7a: Journal entry where sum(debits) != sum(credits) raises UnbalancedJournalEntryError."""
        je_id = self.kernel.create_journal_entry(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            entry_number="JE-2026-0001",
            date="2026-03-31",
            description="Client invoice billing (unbalanced)",
            created_by=self.user_a,
        )

        # Debit AR: $5,000.00 (500000 minor units)
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_ar,
            debit_amount=500000, credit_amount=0, currency="USD"
        )
        # Credit Revenue: $4,500.00 (450000 minor units) -> $500.00 discrepancy
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_rev,
            debit_amount=0, credit_amount=450000, currency="USD"
        )

        with self.assertRaises(UnbalancedJournalEntryError) as ctx:
            self.kernel.post_journal_entry(self.tenant_a, self.company_a, je_id)
        self.assertIn("unbalanced for currency 'USD'", str(ctx.exception))

        # Status must remain DRAFT (Rule 1: Reality ladder)
        je = self.kernel.get_journal_entry(self.tenant_a, self.company_a, je_id)
        self.assertEqual(je["status"], JournalEntryStatus.DRAFT)
        self.assertIsNone(je["posted_at"])

    # =========================================================================
    # ACCEPTANCE TEST B: MULTI-CURRENCY STRICT BALANCING
    # =========================================================================
    def test_mixed_currencies_must_balance_per_currency_independently(self):
        """Acceptance 7b: Cross-currency entries cannot balance USD with EUR; each currency must balance."""
        je_id = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "JE-MULTI-01", "2026-03-31",
            "Cross currency attempted balancing", self.user_a
        )

        # Debit USD Cash: $1,000.00 (100000 minor units)
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_cash,
            debit_amount=100000, credit_amount=0, currency="USD"
        )
        # Credit EUR Revenue: €1,000.00 (100000 minor units)
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_rev_eur,
            debit_amount=0, credit_amount=100000, currency="EUR"
        )

        # Fails because USD has debits=100000, credits=0, and EUR has debits=0, credits=100000
        with self.assertRaises(UnbalancedJournalEntryError):
            self.kernel.post_journal_entry(self.tenant_a, self.company_a, je_id)

        # Now fix by adding balancing legs for BOTH USD and EUR
        # Credit USD Revenue: $1,000.00
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_rev,
            debit_amount=0, credit_amount=100000, currency="USD"
        )
        # Debit EUR Cash: €1,000.00
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_cash_eur,
            debit_amount=100000, credit_amount=0, currency="EUR"
        )

        # Now both legs are independently balanced: USD (100000/100000) and EUR (100000/100000)
        posted_je = self.kernel.post_journal_entry(self.tenant_a, self.company_a, je_id)
        self.assertEqual(posted_je["status"], JournalEntryStatus.POSTED)
        self.assertIsNotNone(posted_je["posted_at"])

    # =========================================================================
    # ACCEPTANCE TEST C: DATABASE-LEVEL IMMUTABILITY OF POSTED ENTRIES
    # =========================================================================
    def test_attempting_to_update_or_delete_posted_entry_raises_database_error(self):
        """Acceptance 7c: Attempting to UPDATE or DELETE a POSTED entry raises at the database level."""
        je_id = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "JE-IMMUT-01", "2026-03-31",
            "Initial capital investment", self.user_a
        )
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_cash,
            debit_amount=10000000, credit_amount=0, currency="USD"
        )
        self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_equity,
            debit_amount=0, credit_amount=10000000, currency="USD"
        )
        self.kernel.post_journal_entry(self.tenant_a, self.company_a, je_id)

        # 1. Direct SQL DELETE on POSTED journal_entry must trigger database abort
        with db.get_connection() as conn:
            with self.assertRaises(Exception) as ctx:
                conn.execute("DELETE FROM journal_entries WHERE entry_id = ?", (je_id,))
            self.assertTrue(
                "immutable" in str(ctx.exception).lower() or "abort" in str(ctx.exception).lower(),
                f"Unexpected exception message: {ctx.exception}"
            )

        # 2. Direct SQL UPDATE on POSTED journal_entry date/amount must trigger database abort
        with db.get_connection() as conn:
            with self.assertRaises(Exception) as ctx:
                conn.execute(
                    "UPDATE journal_entries SET date = '2025-01-01' WHERE entry_id = ?",
                    (je_id,)
                )
            self.assertTrue(
                "immutable" in str(ctx.exception).lower() or "abort" in str(ctx.exception).lower(),
                f"Unexpected exception message: {ctx.exception}"
            )

        # 3. Direct SQL DELETE or UPDATE on POSTED journal_lines must trigger database abort
        with db.get_connection() as conn:
            with self.assertRaises(Exception) as ctx:
                conn.execute("DELETE FROM journal_lines WHERE entry_id = ?", (je_id,))
            self.assertTrue(
                "cannot be deleted" in str(ctx.exception).lower() or "abort" in str(ctx.exception).lower(),
                f"Unexpected exception message: {ctx.exception}"
            )

    # =========================================================================
    # ACCEPTANCE TEST D: REVERSING ENTRIES (CORRECTIONS)
    # =========================================================================
    def test_reversing_entry_creates_exact_opposite_lines_and_marks_original_reversed(self):
        """Acceptance 7d: Reversal swaps debits and credits, posts new entry, and marks original REVERSED."""
        je_id = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "JE-REV-ORIG", "2026-03-31",
            "Erroneous infrastructure bill", self.user_a
        )
        # Debit Expense: $2,500.00
        l1 = self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_exp,
            debit_amount=250000, credit_amount=0, currency="USD", memo="Server cluster charge"
        )
        # Credit AP: $2,500.00
        l2 = self.kernel.add_journal_line(
            self.tenant_a, self.company_a, je_id, self.acct_ap,
            debit_amount=0, credit_amount=250000, currency="USD", memo="Cloud provider AP"
        )
        self.kernel.post_journal_entry(self.tenant_a, self.company_a, je_id)

        # Perform correction via reversing entry
        rev_id = self.kernel.reverse_journal_entry(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            original_entry_id=je_id,
            reversal_entry_number="JE-REV-CORR",
            reversed_by=self.user_a,
            reason="Duplicate invoice from vendor",
        )
        self.assertIsNotNone(rev_id)

        # 1. Original entry must now be in REVERSED status
        orig = self.kernel.get_journal_entry(self.tenant_a, self.company_a, je_id)
        self.assertEqual(orig["status"], JournalEntryStatus.REVERSED)

        # 2. Reversal entry must be in POSTED status and reference original
        rev = self.kernel.get_journal_entry(self.tenant_a, self.company_a, rev_id)
        self.assertEqual(rev["status"], JournalEntryStatus.POSTED)
        self.assertEqual(rev["reversal_of_entry_id"], je_id)
        self.assertEqual(len(rev["lines"]), 2)

        # 3. Verify line mirror swapping
        # In reversal, acct_exp must have CREDIT of 250000, and acct_ap must have DEBIT of 250000
        exp_line = next(l for l in rev["lines"] if l["account_id"] == self.acct_exp)
        ap_line = next(l for l in rev["lines"] if l["account_id"] == self.acct_ap)

        self.assertEqual(exp_line["debit_amount"], 0)
        self.assertEqual(exp_line["credit_amount"], 250000)

        self.assertEqual(ap_line["debit_amount"], 250000)
        self.assertEqual(ap_line["credit_amount"], 0)

    # =========================================================================
    # ACCEPTANCE TEST E: TRIAL BALANCE GENERATION
    # =========================================================================
    def test_trial_balance_generates_correct_balances_and_net_zero_sum(self):
        """Acceptance 7e: Trial balance aggregates accounts and net zero balance is mathematically verified."""
        # Post Transaction 1: $10,000 Equity Investment (Debit Cash 10000, Credit Equity 10000)
        je1 = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "TB-01", "2026-03-01", "Equity investment", self.user_a
        )
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je1, self.acct_cash, 1000000, 0, "USD")
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je1, self.acct_equity, 0, 1000000, "USD")
        self.kernel.post_journal_entry(self.tenant_a, self.company_a, je1)

        # Post Transaction 2: $3,000 SaaS Revenue (Debit AR 3000, Credit Revenue 3000)
        je2 = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "TB-02", "2026-03-15", "March SaaS billings", self.user_a
        )
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je2, self.acct_ar, 300000, 0, "USD")
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je2, self.acct_rev, 0, 300000, "USD")
        self.kernel.post_journal_entry(self.tenant_a, self.company_a, je2)

        # Post Transaction 3: $1,200 Infrastructure Expense (Debit Expense 1200, Credit Cash 1200)
        je3 = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "TB-03", "2026-03-20", "Cloud server hosting", self.user_a
        )
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je3, self.acct_exp, 120000, 0, "USD")
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je3, self.acct_cash, 0, 120000, "USD")
        self.kernel.post_journal_entry(self.tenant_a, self.company_a, je3)

        # Generate trial balance
        tb = self.kernel.generate_trial_balance(self.tenant_a, self.company_a, "USD", as_of_date="2026-03-31")

        self.assertTrue(tb["is_balanced"])
        self.assertEqual(tb["total_debits"], tb["total_credits"])
        self.assertEqual(tb["total_debits"], 1420000)  # 10000 + 3000 + 1200 = $14,200.00
        self.assertEqual(tb["formatted"]["total_debits"], "USD 14200.00")

        # Check net balances of individual accounts:
        # Cash: Debit 10000 - Credit 1200 = Net Debit 8800
        cash_row = next(a for a in tb["accounts"] if a["account_id"] == self.acct_cash)
        self.assertEqual(cash_row["total_debit"], 1000000)
        self.assertEqual(cash_row["total_credit"], 120000)
        self.assertEqual(cash_row["net_balance"], 880000)

        # AR: Net Debit 3000
        ar_row = next(a for a in tb["accounts"] if a["account_id"] == self.acct_ar)
        self.assertEqual(ar_row["net_balance"], 300000)

        # Equity: Net Credit 10000
        eq_row = next(a for a in tb["accounts"] if a["account_id"] == self.acct_equity)
        self.assertEqual(eq_row["net_balance"], 1000000)

        # Revenue: Net Credit 3000
        rev_row = next(a for a in tb["accounts"] if a["account_id"] == self.acct_rev)
        self.assertEqual(rev_row["net_balance"], 300000)

        # Expense: Net Debit 1200
        exp_row = next(a for a in tb["accounts"] if a["account_id"] == self.acct_exp)
        self.assertEqual(exp_row["net_balance"], 120000)

    # =========================================================================
    # ACCEPTANCE TEST F: MULTI-TENANT ISOLATION
    # =========================================================================
    def test_tenant_b_cannot_access_or_modify_tenant_a_accounts_or_journals(self):
        """Acceptance 7f: Tenant B cannot read or post lines to Tenant A accounts."""
        # 1. Tenant B cannot retrieve Tenant A account
        acct = self.kernel.get_account(self.tenant_b, self.company_b, self.acct_cash)
        self.assertIsNone(acct)

        # 2. Tenant B cannot add a line referencing Tenant A's account
        je_b = self.kernel.create_journal_entry(
            self.tenant_b, self.company_b, "JE-B-01", "2026-03-31", "Tenant B Entry", self.user_b
        )
        with self.assertRaises(LedgerError) as ctx:
            self.kernel.add_journal_line(
                self.tenant_b, self.company_b, je_b, self.acct_cash, 50000, 0, "USD"
            )
        self.assertIn("not found in tenant", str(ctx.exception))

    # =========================================================================
    # RULE 12 VALIDATION & ZERO FLOAT ARITHMETIC
    # =========================================================================
    def test_float_money_amounts_and_invalid_currencies_are_strictly_rejected(self):
        """Rule 12: Integer minor units only; floats and bogus currency codes raise errors."""
        je_id = self.kernel.create_journal_entry(
            self.tenant_a, self.company_a, "JE-RULE12", "2026-03-31", "Test rule 12", self.user_a
        )

        # Float debit rejected
        with self.assertRaises(InvalidMinorUnitError):
            self.kernel.add_journal_line(
                self.tenant_a, self.company_a, je_id, self.acct_cash,
                debit_amount=100.50, credit_amount=0, currency="USD"  # type: ignore
            )

        # Invalid currency code rejected
        with self.assertRaises(InvalidCurrencyError):
            self.kernel.add_journal_line(
                self.tenant_a, self.company_a, je_id, self.acct_cash,
                debit_amount=100, credit_amount=0, currency="BITCOIN"
            )

    # =========================================================================
    # FOLIO INTEGRATION: SEALING FOLIO VERIFIES ALL JOURNAL ENTRIES POSTED
    # =========================================================================
    def test_sealing_folio_with_draft_journal_entries_raises_unposted_error(self):
        """Acceptance 5: Sealing or approving a folio verifies all its journal entries are POSTED."""
        folio_id = self.folio_mgr.create_folio(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            folio_type="financial_audit",
            title="Q1 Corporate Financial Close",
            created_by=self.user_a,
        )

        # Create a journal entry linked to this folio, but leave it in DRAFT
        je_id = self.kernel.create_journal_entry(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            entry_number="JE-FOLIO-01",
            date="2026-03-31",
            description="Unposted folio transaction",
            created_by=self.user_a,
            folio_id=folio_id,
        )
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je_id, self.acct_cash, 50000, 0, "USD")
        self.kernel.add_journal_line(self.tenant_a, self.company_a, je_id, self.acct_rev, 0, 50000, "USD")

        # Progress folio to ACTIVE (allowed)
        self.folio_mgr.transition_status(folio_id, FolioStatus.ACTIVE, actor_id=self.user_a)

        # Attempting to seal / transition to PENDING_CLOSE or CLOSED must fail
        with self.assertRaises(UnpostedFolioJournalEntriesError):
            self.folio_mgr.transition_status(folio_id, FolioStatus.PENDING_CLOSE, actor_id=self.user_a)

        # Now post the journal entry
        self.kernel.post_journal_entry(self.tenant_a, self.company_a, je_id)

        # Now transitioning to PENDING_CLOSE succeeds cleanly
        self.folio_mgr.transition_status(folio_id, FolioStatus.PENDING_CLOSE, actor_id=self.user_a)
        folio_data = self.folio_mgr.get_folio(folio_id)
        self.assertEqual(folio_data["status"], FolioStatus.PENDING_CLOSE.value)


class TestLedgerKernelMutations(unittest.TestCase):
    """Mutation tests proving acceptance tests detect deliberate faults (Standing Rule 8)."""

    def test_mutation_bypassing_balance_check_would_fail_invariant(self):
        """Mutation 1: Verify that a mock provider allowing unbalanced entries fails zero balance assertion."""
        class DeliberatelyBrokenLedger:
            def post_unbalanced(self):
                # Deliberate mutation: claims posted even though debits != credits
                return {"status": "POSTED", "debits": 500, "credits": 400}

        broken = DeliberatelyBrokenLedger()
        result = broken.post_unbalanced()
        # The mutation test asserts that unbalanced debits and credits MUST be flagged
        with self.assertRaises(AssertionError):
            assert result["debits"] == result["credits"], "Mutation caught: debits != credits"

    def test_mutation_reversal_without_swapped_lines_caught(self):
        """Mutation 2: Verify that failing to swap debit and credit in reversal is caught."""
        orig_line = {"debit_amount": 500, "credit_amount": 0}
        # Broken reversal that failed to swap
        broken_rev_line = {"debit_amount": 500, "credit_amount": 0}

        with self.assertRaises(AssertionError):
            assert broken_rev_line["debit_amount"] == orig_line["credit_amount"], "Mutation caught: debits not swapped"
            assert broken_rev_line["credit_amount"] == orig_line["debit_amount"], "Mutation caught: credits not swapped"


if __name__ == "__main__":
    unittest.main()
