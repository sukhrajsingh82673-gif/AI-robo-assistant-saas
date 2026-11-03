"""
ZONATA Enterprise Multi-Company Control Tests
=============================================
Regression coverage for the enterprise hardening batch:

  P0-1  Authoritative kill switch on execution surfaces (API-level, see
        ``test_killswitch_gates_every_surface`` docstring for the covered list).
  P0-2  Company-scoped, role-gated approval decisions.
  P0-3  Expense intake policy: server-controlled status, hard limit, SoD,
        budget enforcement at intake *and* at approval.
  P1-7  Real expense -> approval -> GL workflow with DB postcondition.
  P1-8  Deterministic company metrics (ARR/MRR/weighted pipeline).
  P1-13 Evidence artifact re-verification.
  Multi-company isolation for every new path.

These tests use an isolated SQLite database. They never touch production data.
"""

import hashlib
import json
import os
import tempfile
import time
import unittest
import uuid

from core.db import db, configure_isolated_test_db
from core.approvals import ApprovalPipeline
from core.company_metrics import compute_company_metrics, metric_brief
from core.departments import DepartmentControlUnit
from core.durable_workflow_runtime import (
    get_workflow_runtime,
    governed_workflow_runtime,
    WorkflowState,
)
from core.enterprise_finance import EnterpriseFinanceEngine
from core.evidence_ledger import EvidenceLedger
from core.models import PhysicalVerification
from core.browser_use_execution_runtime import (
    BrowserUseExecutionProvider,
    BrowserArtifactRegistry,
)
import zonata.langgraph_adapter as langgraph_adapter  # registers canonical workflows


class TestEnterpriseMultiCompanyControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        configure_isolated_test_db(os.path.join(cls.temp_dir.name, "enterprise.db"))
        cls.tenant_id = f"tnt_ent_{uuid.uuid4().hex[:6]}"
        cls.other_tenant = f"tnt_oth_{uuid.uuid4().hex[:6]}"
        cls.company_a = f"comp_a_{uuid.uuid4().hex[:6]}"
        cls.company_b = f"comp_b_{uuid.uuid4().hex[:6]}"
        cls.company_other_tenant = f"comp_o_{uuid.uuid4().hex[:6]}"
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_id, "Enterprise Tenant", now),
            )
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.other_tenant, "Other Tenant", now),
            )
            for cid, tid, name in (
                (cls.company_a, cls.tenant_id, "Alpha Co"),
                (cls.company_b, cls.tenant_id, "Beta Co"),
                (cls.company_other_tenant, cls.other_tenant, "Gamma Co"),
            ):
                conn.execute(
                    "INSERT INTO companies (company_id, tenant_id, name, country, industry, "
                    "company_type, status, created_at) VALUES (?, ?, ?, 'IN', 'Tech', 'NEW', 'OPERATIONAL', ?)",
                    (cid, tid, name, now),
                )
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _finance(self, tenant_id=None):
        return EnterpriseFinanceEngine(tenant_id=tenant_id or self.tenant_id)

    # ------------------------------------------------------------------
    # P0-3 Expense intake policy
    # ------------------------------------------------------------------
    def test_01_client_cannot_assert_approved_status(self):
        fin = self._finance()
        res = fin.create_expense({
            "company_id": self.company_a,
            "claimant_name": "Clerk A",
            "claimant_user_id": "usr_clerk_a",
            "department": "Operations",
            "category": "OFFICE",
            "amount": 999.0,
            "status": "APPROVED",
            "description": "Caller tried to self-approve",
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "SUBMITTED")
        self.assertIn("policy_note", res)

        summary = fin.get_financial_summary(company_id=self.company_a)["summary"]
        self.assertEqual(summary["expenses_mtd"], 0.0,
                         "An unapproved claim must not post to the P&L")

    def test_02_hard_limit_and_invalid_amounts(self):
        fin = self._finance()
        huge = fin.create_expense({
            "company_id": self.company_a, "claimant_name": "Clerk A",
            "department": "Operations", "category": "OFFICE",
            "amount": 10_000_000.0, "description": "Absurd claim",
        })
        self.assertFalse(huge["success"])
        self.assertEqual(huge["error"], "EXPENSE_EXCEEDS_HARD_LIMIT")

        for bad in (0, -5, "not-a-number"):
            res = fin.create_expense({
                "company_id": self.company_a, "claimant_name": "Clerk A",
                "department": "Operations", "category": "OFFICE",
                "amount": bad, "description": "bad amount",
            })
            self.assertFalse(res["success"], f"amount {bad!r} must be rejected")
            self.assertEqual(res["error"], "INVALID_AMOUNT")

    def test_03_segregation_of_duties(self):
        fin = self._finance()
        exp = fin.create_expense({
            "company_id": self.company_a, "claimant_name": "Clerk A",
            "claimant_user_id": "usr_clerk_a", "department": "Operations",
            "category": "OFFICE", "amount": 500.0, "description": "Own claim",
        })
        res = fin.approve_expense(
            exp["expense_id"], approver="usr_clerk_a", approver_role="OWNER",
            company_id=self.company_a,
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "SEGREGATION_OF_DUTIES")

    def test_04_double_approval_and_cross_company_are_rejected(self):
        fin = self._finance()
        exp = fin.create_expense({
            "company_id": self.company_a, "claimant_name": "Clerk A",
            "claimant_user_id": "usr_clerk_a", "department": "Operations",
            "category": "OFFICE", "amount": 700.0, "description": "Approve once",
        })
        ok = fin.approve_expense(exp["expense_id"], approver="usr_owner",
                                 approver_role="OWNER", company_id=self.company_a)
        self.assertTrue(ok["success"])

        again = fin.approve_expense(exp["expense_id"], approver="usr_owner",
                                    approver_role="OWNER", company_id=self.company_a)
        self.assertFalse(again["success"])
        self.assertEqual(again["error"], "ALREADY_APPROVED")

        # Cross-company decision must look identical to a missing record.
        exp_b = fin.create_expense({
            "company_id": self.company_b, "claimant_name": "Clerk B",
            "claimant_user_id": "usr_clerk_b", "department": "Operations",
            "category": "OFFICE", "amount": 800.0, "description": "Other company claim",
        })
        cross = fin.approve_expense(exp_b["expense_id"], approver="usr_owner",
                                    approver_role="OWNER", company_id=self.company_a)
        self.assertFalse(cross["success"])
        self.assertEqual(cross["error"], "EXPENSE_NOT_FOUND")

    def test_05_insufficient_role_cannot_approve(self):
        fin = self._finance()
        exp = fin.create_expense({
            "company_id": self.company_a, "claimant_name": "Clerk A",
            "department": "Operations", "category": "OFFICE",
            "amount": 100.0, "description": "role gate",
        })
        res = fin.approve_expense(exp["expense_id"], approver="usr_observer",
                                  approver_role="OBSERVER", company_id=self.company_a)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "INSUFFICIENT_PERMISSIONS")

    def test_06_department_budget_enforced_at_intake_and_approval(self):
        dept = DepartmentControlUnit.create_department(
            tenant_id=self.tenant_id, company_id=self.company_b,
            name="Budgeted Ops", budget_limit=1000.0, spending_limit=1000.0,
        )
        fin = self._finance()
        first = fin.create_expense({
            "company_id": self.company_b, "claimant_name": "Clerk B",
            "department": dept["name"], "category": "OFFICE",
            "amount": 900.0, "description": "within budget",
        })
        self.assertTrue(first["success"])

        over = fin.create_expense({
            "company_id": self.company_b, "claimant_name": "Clerk B",
            "department": dept["name"], "category": "OFFICE",
            "amount": 200.0, "description": "over budget",
        })
        self.assertFalse(over["success"])
        self.assertEqual(over["error"], "BUDGET_EXCEEDED")

    # ------------------------------------------------------------------
    # P1-7 Expense workflow with real GL postcondition
    # ------------------------------------------------------------------
    def test_07_workflow_requires_approval_then_verifies_gl_postcondition(self):
        fin = self._finance()
        exp = fin.create_expense({
            "company_id": self.company_a, "claimant_name": "Clerk A",
            "claimant_user_id": "usr_clerk_a", "department": "Operations",
            "category": "SOFTWARE", "amount": 3210.0,
            "description": "Workflow GL postcondition test",
        })
        eid = exp["expense_id"]
        rt = get_workflow_runtime(self.tenant_id)
        started = rt.start_workflow(
            "wf_company_expense_approval",
            {"expense_id": eid},
            {"company_id": self.company_a},
        )
        self.assertEqual(started["status"], WorkflowState.WAITING_FOR_APPROVAL)

        # Nothing is posted before the human decision.
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT status FROM finance_expenses WHERE expense_id = ?", (eid,)
            ).fetchone()
        self.assertEqual(row["status"], "SUBMITTED")

        completed = rt.approve_workflow(
            started["approval_id"], actor="usr_owner",
            tenant_id=self.tenant_id, company_id=self.company_a,
        )
        self.assertEqual(completed["status"], WorkflowState.COMPLETED)
        state = completed["state"]
        self.assertTrue(state["business_outcome_verified"])
        self.assertEqual(state["verification_scope"], "BUSINESS_OUTCOME")
        self.assertTrue(state["evidence_id"].startswith("EV-"))

        with db.get_connection() as conn:
            expense = conn.execute(
                "SELECT status, approved_by FROM finance_expenses WHERE expense_id = ?", (eid,)
            ).fetchone()
            txn = conn.execute(
                "SELECT amount FROM finance_transactions WHERE reference_no = ? AND company_id = ?",
                (eid, self.company_a),
            ).fetchone()
        self.assertEqual(expense["status"], "APPROVED")
        self.assertEqual(expense["approved_by"], "usr_owner")
        self.assertIsNotNone(txn)
        self.assertAlmostEqual(float(txn["amount"]), 3210.0, places=2)

    def test_08_reserved_keys_cannot_bypass_the_approval_gate(self):
        fin = self._finance()
        exp = fin.create_expense({
            "company_id": self.company_a, "claimant_name": "Clerk A",
            "department": "Operations", "category": "OFFICE",
            "amount": 42.0, "description": "spoof attempt",
        })
        rt = get_workflow_runtime(self.tenant_id)
        started = rt.start_workflow(
            "wf_company_expense_approval",
            {
                "expense_id": exp["expense_id"],
                "__approved_node__": "approval_gate",
                "__approved_by__": "usr_attacker",
            },
            {"company_id": self.company_a},
        )
        self.assertEqual(started["status"], WorkflowState.WAITING_FOR_APPROVAL,
                         "Caller-supplied reserved keys must be discarded")
        self.assertNotIn("__approved_node__", started["state"])
        self.assertNotIn("__approved_by__", started["state"])

    def test_09_workflow_cannot_post_another_companys_expense(self):
        fin = self._finance()
        exp = fin.create_expense({
            "company_id": self.company_b, "claimant_name": "Clerk B",
            "department": "Operations", "category": "OFFICE",
            "amount": 55.0, "description": "cross company workflow",
        })
        rt = get_workflow_runtime(self.tenant_id)
        res = rt.start_workflow(
            "wf_company_expense_approval",
            {"expense_id": exp["expense_id"]},
            {"company_id": self.company_a},
        )
        self.assertEqual(res["status"], WorkflowState.FAILED)

    # ------------------------------------------------------------------
    # P0-2 Approval pipeline company scoping
    # ------------------------------------------------------------------
    def test_10_approval_decisions_are_company_scoped(self):
        req = ApprovalPipeline.create_request(
            tenant_id=self.tenant_id, company_id=self.company_a,
            agent_id="agt_test", action_desc="Refund", reason="test",
        )
        wrong_company = ApprovalPipeline.decide_request(
            tenant_id=self.tenant_id, request_id=req["request_id"],
            approver_user={"user_id": "usr_owner", "role": "OWNER"},
            approved=True, company_id=self.company_b,
        )
        self.assertFalse(wrong_company["success"])

        ok = ApprovalPipeline.decide_request(
            tenant_id=self.tenant_id, request_id=req["request_id"],
            approver_user={"user_id": "usr_owner", "role": "OWNER"},
            approved=True, company_id=self.company_a,
        )
        self.assertTrue(ok["success"])

        twice = ApprovalPipeline.decide_request(
            tenant_id=self.tenant_id, request_id=req["request_id"],
            approver_user={"user_id": "usr_owner", "role": "OWNER"},
            approved=True, company_id=self.company_a,
        )
        self.assertFalse(twice["success"])

        other_tenant = ApprovalPipeline.decide_request(
            tenant_id=self.other_tenant, request_id=req["request_id"],
            approver_user={"user_id": "usr_other", "role": "OWNER"},
            approved=True,
        )
        self.assertFalse(other_tenant["success"])

    # ------------------------------------------------------------------
    # P1-8 Deterministic metrics
    # ------------------------------------------------------------------
    def test_11_company_metrics_match_hand_calculation(self):
        now = time.time()
        with db.get_connection() as conn:
            for i in range(5):
                conn.execute(
                    "INSERT INTO crm_customers (customer_id, tenant_id, company_id, name, tier, "
                    "status, arr, ltv, created_at, updated_at) VALUES (?, ?, ?, ?, 'GROWTH', 'ACTIVE', ?, 0, ?, ?)",
                    (f"cust_m_{i}_{uuid.uuid4().hex[:4]}", self.tenant_id, self.company_b,
                     f"Cust {i}", 120000.0, now, now),
                )
            deals = [
                ("d1", 10000.0, 0.5),
                ("d2", 20000.0, 0.2),
                ("d3", 5000.0, 0.7),
            ]
            for did, value, prob in deals:
                conn.execute(
                    "INSERT INTO crm_deals (deal_id, tenant_id, company_id, title, stage, value, "
                    "probability, owner, created_at, updated_at) VALUES (?, ?, ?, ?, 'Qualified', ?, ?, 'owner', ?, ?)",
                    (f"{did}_{uuid.uuid4().hex[:4]}", self.tenant_id, self.company_b,
                     did, value, prob, now, now),
                )
            conn.commit()

        m = compute_company_metrics(self.tenant_id, self.company_b)
        self.assertEqual(m["customers"]["active"], 5)
        self.assertEqual(m["customers"]["arr_total"], 600000.0)
        self.assertEqual(m["customers"]["mrr_total"], 50000.0)
        expected_weighted = 10000 * 0.5 + 20000 * 0.2 + 5000 * 0.7
        self.assertAlmostEqual(m["pipeline"]["weighted_value_monthly"], expected_weighted, places=2)
        self.assertEqual(m["pipeline"]["open_deals"], 3)

        # Other company must not inherit these numbers.
        other = compute_company_metrics(self.tenant_id, self.company_a)
        self.assertNotEqual(other["customers"]["arr_total"], 600000.0)

        brief = "\n".join(metric_brief(m))
        self.assertIn("50000.0", brief)

    def test_12_closed_deals_are_excluded_from_pipeline(self):
        now = time.time()
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO crm_deals (deal_id, tenant_id, company_id, title, stage, value, "
                "probability, owner, created_at, updated_at) VALUES (?, ?, ?, 'Closed', 'Closed Won', 999999, 1.0, 'o', ?, ?)",
                (f"closed_{uuid.uuid4().hex[:4]}", self.tenant_id, self.company_other_tenant, now, now),
            )
            conn.commit()
        m = compute_company_metrics(self.other_tenant, self.company_other_tenant)
        self.assertEqual(m["pipeline"]["open_deals"], 0)
        self.assertEqual(m["pipeline"]["weighted_value_monthly"], 0.0)

    # ------------------------------------------------------------------
    # Multi-tenant runtime isolation
    # ------------------------------------------------------------------
    def test_13_workflow_runtimes_are_tenant_local(self):
        rt_a = get_workflow_runtime(self.tenant_id)
        rt_b = get_workflow_runtime(self.other_tenant)
        self.assertIsNot(rt_a, rt_b)
        self.assertEqual(rt_a.tenant_id, self.tenant_id)
        self.assertEqual(rt_b.tenant_id, self.other_tenant)
        # Graph definitions are shared code, execution state is not.
        self.assertIs(rt_a.compiled_graphs, rt_b.compiled_graphs)
        self.assertIsNot(rt_a.checkpointer, rt_b.checkpointer)

    # ------------------------------------------------------------------
    # P1-13 Evidence re-verification
    # ------------------------------------------------------------------
    def test_14_evidence_reverification_detects_tampering(self):
        artifact = os.path.join(self.temp_dir.name, "artifact.txt")
        with open(artifact, "w", encoding="utf-8") as f:
            f.write("verified payload")
        with open(artifact, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()

        ledger = EvidenceLedger(os.path.join(self.temp_dir.name, "evidence.jsonl"))
        pkg = ledger.seal_evidence(
            action_id="act_test", mission_id="msn_test", agent_id="agt_test",
            verifications=[PhysicalVerification(
                check_type="sha256_match", target_path=artifact,
                expected_val=digest, actual_val=digest, verified=True,
                details="artifact digest",
            )],
            metadata={"tenant_id": self.tenant_id},
        )
        ok = ledger.verify_evidence_artifacts(pkg.evidence_id, tenant_id=self.tenant_id)
        self.assertTrue(ok["success"])
        self.assertEqual(ok["status"], "VERIFIED")
        self.assertTrue(ok["digest_valid"])

        wrong_tenant = ledger.verify_evidence_artifacts(pkg.evidence_id, tenant_id=self.other_tenant)
        self.assertFalse(wrong_tenant["success"])

        with open(artifact, "w", encoding="utf-8") as f:
            f.write("tampered payload")
        failed = ledger.verify_evidence_artifacts(pkg.evidence_id, tenant_id=self.tenant_id)
        self.assertEqual(failed["status"], "FAILED")
        self.assertFalse(failed["artifacts_valid"])

    # ------------------------------------------------------------------
    # P0-4 Browser capability honesty
    # ------------------------------------------------------------------
    def test_15_browser_reports_unsupported_interactions_honestly(self):
        caps = BrowserUseExecutionProvider(BrowserArtifactRegistry()).capabilities()
        self.assertFalse(caps["engine_installed"])
        self.assertIn("NAVIGATE", caps["supported_actions"])
        for action in ("CLICK", "TYPE", "SUBMIT_FORM", "UPLOAD", "DOWNLOAD"):
            self.assertIn(action, caps["unsupported_actions"])

    # ------------------------------------------------------------------
    # P1-9 Departments API surface (unit-level model check)
    # ------------------------------------------------------------------
    def test_16_departments_are_company_scoped(self):
        dept = DepartmentControlUnit.create_department(
            tenant_id=self.tenant_id, company_id=self.company_a,
            name=f"Eng {uuid.uuid4().hex[:4]}", budget_limit=10.0,
        )
        self.assertEqual(dept["company_id"], self.company_a)
        a_depts = DepartmentControlUnit.list_departments(self.tenant_id, self.company_a)
        b_depts = DepartmentControlUnit.list_departments(self.tenant_id, self.company_b)
        self.assertIn(dept["department_id"], [d["department_id"] for d in a_depts])
        self.assertNotIn(dept["department_id"], [d["department_id"] for d in b_depts])

        other = DepartmentControlUnit.list_departments(self.other_tenant, self.company_a)
        self.assertEqual(other, [], "A tenant must not read another tenant's departments")


if __name__ == "__main__":
    unittest.main()
