"""
URA / ZONATA Universal AI Company Operating System
Public GA Integrity and Financial Accounting Regression Test Suite

Verifies:
1. Merkle ledger anti-tamper detection on synthetic chain.
2. Dynamic multi-epoch Merkle integrity verification.
3. Strict fail-closed rejection on corrupted cryptographic blocks.
4. Financial expense lifecycle (SUBMITTED -> APPROVED -> General Ledger posting).
5. Chart of Accounts reconciliation and statutory accounting invariants.
"""

import unittest
import time
import uuid
import tempfile
import json
import os

from core.db import db, configure_isolated_test_db
from core.evidence_ledger import EvidenceLedger
from core.models import PhysicalVerification
from core.enterprise_finance import EnterpriseFinanceEngine


class TestPublicGAIntegrityAndFinance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "ga_test.db")
        configure_isolated_test_db(cls.test_db_path)
        cls.tenant_id = f"tnt_ga_{uuid.uuid4().hex[:6]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_id, "Public GA Enterprise", time.time())
            )
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_01_synthetic_ledger_tamper_detection(self):
        """Proves that any corrupted record in a synthetic ledger produces non-success state."""
        ledger_path = os.path.join(self.temp_dir.name, "synthetic_ledger.jsonl")
        ledger = EvidenceLedger(ledger_path)
        v = [PhysicalVerification(
            check_type="file_exists",
            target_path="/tmp/test",
            expected_val="exists",
            actual_val="exists",
            verified=True,
            details="Synthetic test verification"
        )]
        pkg1 = ledger.seal_evidence("ACT-1", "MSN-1", "agt_test", v)
        pkg2 = ledger.seal_evidence("ACT-2", "MSN-1", "agt_test", v)

        # Baseline: untampered chain is valid
        audit_res = ledger.verify_full_chain_integrity()
        self.assertTrue(audit_res["valid"], "Untampered ledger must be valid")
        self.assertEqual(len(audit_res["forks_detected"]), 0)

        # Corrupt record 1's prev_hash
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        lines[1]["prev_hash"] = "TAMPERED_FORGED_PREV_HASH"
        with open(ledger_path, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

        corrupted_ledger = EvidenceLedger(ledger_path)
        corrupted_audit = corrupted_ledger.verify_full_chain_integrity()
        self.assertFalse(corrupted_audit["valid"], "Tampered ledger must return valid=False")
        self.assertGreater(len(corrupted_audit["forks_detected"]), 0, "Forks must be detected")
        self.assertFalse(corrupted_ledger.verify_ledger_integrity(), "verify_ledger_integrity must be False")

    def test_02_expense_accounting_lifecycle_reconciliation(self):
        """Verifies statutory expense lifecycle: Submitted (pending) vs Approved (posted to GL)."""
        fin = EnterpriseFinanceEngine(tenant_id=self.tenant_id)
        s0 = fin.get_financial_summary()["summary"]
        self.assertEqual(s0["expenses_mtd"], 0.0, "Initial expenses MTD must be zero")
        self.assertEqual(s0["expenses_pending_approval"], 0.0, "Initial pending expenses must be zero")

        # Step 1: Submit reimbursement claim for ₹350
        create_res = fin.create_expense({
            "amount": 350.0,
            "category": "OFFICE",
            "status": "SUBMITTED",
            "description": "Stationery supplies claim"
        })
        self.assertTrue(create_res["success"])
        exp_id = create_res["expense_id"]

        # Statutory invariant: Submitted claim is pending approval, NOT posted to P&L
        s1 = fin.get_financial_summary()["summary"]
        self.assertEqual(s1["expenses_mtd"], 0.0, "Submitted claim must not hit MTD expenses")
        self.assertEqual(s1["expenses_pending_approval"], 350.0, "Pending approval must reflect ₹350")

        # Step 2: Approve the expense claim
        app_res = fin.approve_expense(exp_id, approver="Finance Director")
        self.assertTrue(app_res["success"])
        self.assertEqual(app_res["status"], "APPROVED")

        # Statutory invariant: Approved claim posts to GL and updates MTD expenses
        s2 = fin.get_financial_summary()
        summary2 = s2["summary"]
        self.assertEqual(summary2["expenses_mtd"], 350.0, "Approved claim must hit MTD expenses")
        self.assertEqual(summary2["expenses_pending_approval"], 0.0, "Pending claims must return to zero")

        # Verify Chart of Accounts posting to General Admin/Office (acc_6030)
        office_acc = next((a for a in s2["chart_of_accounts"] if a["code"] == "6030"), None)
        self.assertIsNotNone(office_acc)
        self.assertEqual(office_acc["balance"], 350.0, "GL account 6030 balance must reflect ₹350 debit")

        # Verify transaction journal entry was created
        txs = s2["recent_transactions"]
        self.assertGreater(len(txs), 0, "Journal entry must be posted")
        self.assertEqual(txs[0]["reference_no"], exp_id)
        self.assertEqual(txs[0]["amount"], 350.0)


if __name__ == "__main__":
    unittest.main()
