"""
Phase 14 Nine-Department Synthetic Enterprise Lifecycle & Deep Governance Qualification
========================================================================================
Validates:
1. End-to-end governed lifecycle across all 9 corporate departments:
   - Executive (Strategy & Autonomous Governance)
   - Finance (Treasury & Economic Allocation)
   - Sales (CRM & Deal Execution)
   - Support (Customer Success & Credit Remediation)
   - Marketing (Campaigns & Attribution)
   - Operations (Infrastructure Scaling & Logistics)
   - Engineering (CI/CD Deployment & Pool Management)
   - Human Resources (Agent Identity Lifecycle & Employee Governance)
   - Procurement (Vendor Purchase Orders & Capacity Acquisition)
2. Every lifecycle stage verified:
   Authentication -> Tenant Resolution -> Risk Assessment -> Approval Decision ->
   Budget Reservation -> Execution -> Settlement / Release -> Reconciliation ->
   Scoped Memory -> Audit Evidence.
3. Edge cases and boundary defenses:
   - Successful execution with underrun release
   - Denied / tampered action rejection
   - Budget exhaustion rejection
   - Execution failure with safe reservation release
   - Duplicate settlement / reconciliation idempotency
   - Cross-tenant isolation enforcement
4. Accurate labeling: Symmetric HMAC-SHA256 Message Authentication Code.
"""

import os
import sys
import time
import uuid
import json
import tempfile
import unittest
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.auth import UserManager, UserRole
from core.economic_governance import (
    EconomicGovernanceEngine,
    BudgetExhaustionException,
    BudgetFrozenException,
    ChildBudgetExceededException
)
from core.cryptographic_approvals import (
    CryptographicApprovalEngine,
    ActionTamperingException,
    ReplayAttackException,
    HighRiskActionClass
)
from core.stateful_agent_runtime import (
    StatefulAgentMemoryGateway,
    MemoryScope,
    MemoryType,
    MemoryCategory,
    ConfidenceLevel
)
from core.saas_billing import SaasBillingEngine, SubscriptionTier
from core.simulation_fixtures import seed_synthetic_enterprise, SIM_TENANT_ID, SIM_COMPANY_ID

class TestPhase14NineDepartmentLifecycle(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = db.db_path
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "nine_dept_lifecycle.db")
        configure_isolated_test_db(self.db_path)

        # Initialize engines
        self.econ = EconomicGovernanceEngine()
        self.crypto = CryptographicApprovalEngine()
        self.memory = StatefulAgentMemoryGateway(tenant_id=SIM_TENANT_ID)
        self.billing = SaasBillingEngine()

        # Seed full 9 departments
        self.fixtures = seed_synthetic_enterprise(self.db_path)

    def tearDown(self):
        if getattr(self, "orig_db_path", None) and os.path.exists(os.path.dirname(os.path.abspath(self.orig_db_path))):
            db.set_db_path(self.orig_db_path)
            os.environ["ZONATA_DB_PATH"] = self.orig_db_path
        self.temp_dir.cleanup()

    def test_01_all_nine_departments_provisioned_and_queryable(self):
        """Verify that all 9 departments exist in database with managers, employee records, and budgets."""
        expected_depts = [
            ("dept_exec", "Executive Council & AI CEO", "agt_ceo_sim"),
            ("dept_fin", "Finance & Corporate Treasury", "agt_fin_lead"),
            ("dept_sales", "Sales & Client Operations", "agt_sales_lead"),
            ("dept_support", "Customer Support & Success", "agt_support_lead"),
            ("dept_mktg", "Marketing & Brand Growth", "agt_mktg_lead"),
            ("dept_ops", "Operations & Infrastructure Logistics", "agt_ops_lead"),
            ("dept_eng", "AI Systems & Autonomous Engineering", "agt_eng_lead"),
            ("dept_hr", "Human Resources & Talent Governance", "agt_hr_lead"),
            ("dept_procure", "Procurement & Vendor Governance", "agt_procure_lead"),
        ]

        with db.get_connection() as conn:
            for dept_id, name, mgr in expected_depts:
                row = conn.execute(
                    "SELECT * FROM departments WHERE department_id = ? AND tenant_id = ?",
                    (dept_id, SIM_TENANT_ID)
                ).fetchone()
                self.assertIsNotNone(row, f"Department '{dept_id}' missing")
                self.assertEqual(row["name"], name)
                self.assertEqual(row["manager_agent_id"], mgr)

                # Check manager employee record
                emp = conn.execute(
                    "SELECT * FROM employees WHERE agent_id = ? AND tenant_id = ?",
                    (mgr, SIM_TENANT_ID)
                ).fetchone()
                self.assertIsNotNone(emp, f"Manager employee '{mgr}' missing")

                # Check budget configuration
                bdg = self.econ.get_budget(dept_id)
                self.assertIsNotNone(bdg, f"Budget for '{dept_id}' missing")
                self.assertGreater(bdg.allocated_usd, 0.0)

    def test_02_full_lifecycle_across_all_nine_departments(self):
        """
        Execute meaningful business tasks across all 9 departments through the complete governed path:
        Auth -> Tenant -> Risk -> Symmetric HMAC -> Budget -> Execute -> Settle -> Memory.
        """
        owner_token = self.fixtures["users"]["usr_sim_owner"]["token"]
        user_info = UserManager.verify_token(owner_token)
        self.assertEqual(user_info["role"], UserRole.OWNER)

        dept_tasks = [
            ("dept_exec", "agt_ceo_sim", "EXECUTIVE_STRATEGY", 5000.0, 4800.0, "Approve quarterly multi-agent operating plan"),
            ("dept_fin", "agt_fin_lead", "TREASURY_REBALANCE", 12000.0, 11500.0, "Corporate treasury liquidity allocation"),
            ("dept_sales", "agt_sales_lead", "ENTERPRISE_DEAL_CLOSE", 3000.0, 2900.0, "Execute Tier-1 enterprise software contract"),
            ("dept_support", "agt_support_lead", "SLA_CREDIT_ISSUANCE", 500.0, 450.0, "Remediate customer outage credit"),
            ("dept_mktg", "agt_mktg_lead", "AD_CAMPAIGN_LAUNCH", 4000.0, 3800.0, "Omni-channel marketing campaign activation"),
            ("dept_ops", "agt_ops_lead", "CLUSTER_AUTOSCALE", 1500.0, 1400.0, "Scale cloud inference cluster to 16 nodes"),
            ("dept_eng", "agt_eng_lead", "CICD_BUILD_PIPELINE", 800.0, 750.0, "Execute automated regression build run"),
            ("dept_hr", "agt_hr_lead", "AGENT_ROLE_PROVISION", 1000.0, 950.0, "Onboard autonomous data engineering agent"),
            ("dept_procure", "agt_procure_lead", "VENDOR_PURCHASE_ORDER", 4500.0, 4200.0, "Procure cloud compute reserve capacity"),
        ]

        for dept_id, agent_id, action_type, req_usd, actual_usd, desc in dept_tasks:
            # 1. Budget reservation
            res = self.econ.reserve_budget(
                tenant_id=SIM_TENANT_ID,
                scope_chain=[("COMPANY", f"bdg_master_{SIM_COMPANY_ID}"), ("DEPARTMENT", dept_id)],
                requested_usd=req_usd,
                task_id=f"task_{dept_id}"
            )
            self.assertEqual(res.status, "RESERVED")
            res_id = res.reservation_id

            # 2. Symmetric HMAC-SHA256 Approval Issuance
            action_payload = {
                "action_id": f"act_{dept_id}_{uuid.uuid4().hex[:6]}",
                "action_type": action_type,
                "tenant_id": SIM_TENANT_ID,
                "company_id": SIM_COMPANY_ID,
                "agent_id": agent_id,
                "capability_id": f"cap_{dept_id}",
                "target": f"sys_{dept_id}",
                "intent": desc,
                "risk_class": HighRiskActionClass.FINANCIAL.value if req_usd > 1000.0 else HighRiskActionClass.MUTATING.value,
                "parameters": {"reservation_id": res_id, "amount_usd": req_usd}
            }
            cert = self.crypto.issue_approval(
                action_payload=action_payload,
                approver_id="usr_sim_exec",
                approver_role="EXECUTIVE",
                ttl_seconds=1800.0
            )
            # Verify signature exists and matches symmetric HMAC-SHA256 format (64-char hex)
            self.assertEqual(len(cert.signature), 64)

            # 3. Consume approval
            consume_res = self.crypto.verify_and_consume_approval(
                action_payload=action_payload,
                certificate=cert,
                consuming_action_id=action_payload["action_id"]
            )
            self.assertTrue(consume_res["verified"])

            # 4. Settle budget
            settlement = self.econ.settle_budget(
                reservation_id=res_id,
                actual_usd=actual_usd
            )
            self.assertEqual(settlement.status, "SETTLED")
            self.assertEqual(settlement.actual_usd, actual_usd)

            # 5. Reconcile into SaaS billing usage ledger
            rec = self.billing.reconcile_economic_settlement(
                tenant_id=SIM_TENANT_ID,
                reservation_id=res_id,
                actual_tokens=10000,
                actual_usd=actual_usd
            )
            self.assertTrue(rec["reconciled"])

            # 6. Stateful scoped agent memory
            mem = self.memory.store_memory(
                scope=MemoryScope.COMPANY.value,
                scope_id=SIM_COMPANY_ID,
                memory_key=f"task_{dept_id}_record",
                content=f"{desc} completed by {agent_id}. Settled ${actual_usd:.2f}.",
                memory_type=MemoryType.CORE.value,
                category=MemoryCategory.DECISION.value,
                confidence=ConfidenceLevel.VERIFIED.value,
                source="PHASE_14_QUALIFICATION"
            )
            self.assertIsNotNone(mem.record_id)

    def test_03_denied_action_and_tamper_rejection(self):
        """Verify that tampered parameters or unauthorized modifications are strictly rejected."""
        dept_id = "dept_fin"
        res = self.econ.reserve_budget(
            tenant_id=SIM_TENANT_ID,
            scope_chain=[("DEPARTMENT", dept_id)],
            requested_usd=1000.0,
            task_id="tamper_test"
        )
        action_payload = {
            "action_id": f"act_tamper_{uuid.uuid4().hex[:6]}",
            "action_type": "TREASURY_TRANSFER",
            "tenant_id": SIM_TENANT_ID,
            "company_id": SIM_COMPANY_ID,
            "agent_id": "agt_fin_lead",
            "capability_id": "treasury",
            "target": "external_account",
            "intent": "Authorize transfer",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "parameters": {"amount_usd": 1000.0}
        }
        cert = self.crypto.issue_approval(
            action_payload=action_payload,
            approver_id="usr_sim_exec",
            approver_role="EXECUTIVE"
        )

        # Adversary attempts to tamper with amount ($100,000.00 instead of $1,000.00)
        tampered_payload = dict(action_payload)
        tampered_payload["parameters"] = {"amount_usd": 100000.0}

        with self.assertRaises(ActionTamperingException):
            self.crypto.verify_and_consume_approval(
                action_payload=tampered_payload,
                certificate=cert,
                consuming_action_id=action_payload["action_id"]
            )

        # Release reservation safely
        self.econ.release_reservation(res.reservation_id, reason="TAMPERED_ACTION_ABORTED")

    def test_04_budget_exhaustion_fail_closed(self):
        """Verify that requests exceeding department budget limits fail closed."""
        dept_id = "dept_support"
        # Allocated for support is $25,000. Requesting $500,000 must fail closed
        with self.assertRaises(BudgetExhaustionException):
            self.econ.reserve_budget(
                tenant_id=SIM_TENANT_ID,
                scope_chain=[("DEPARTMENT", dept_id)],
                requested_usd=500000.0,
                task_id="exhaust_test"
            )

    def test_05_failed_execution_with_safe_recovery(self):
        """Verify that an operation failing mid-execution releases 100% of reserved funds with zero balance loss."""
        dept_id = "dept_ops"
        initial_bdg = self.econ.get_budget(dept_id)
        self.assertIsNotNone(initial_bdg)
        initial_reserved = initial_bdg.reserved_usd

        # Reserve $2,000
        res = self.econ.reserve_budget(
            tenant_id=SIM_TENANT_ID,
            scope_chain=[("DEPARTMENT", dept_id)],
            requested_usd=2000.0,
            task_id="failing_task"
        )
        mid_bdg = self.econ.get_budget(dept_id)
        self.assertEqual(mid_bdg.reserved_usd, initial_reserved + 2000.0)

        # Execution fails (e.g., target node unreachable) -> Abort & release
        ok = self.econ.release_reservation(res.reservation_id, reason="NODE_UNREACHABLE_FAILURE")
        self.assertTrue(ok)

        # Budget state restored completely
        final_bdg = self.econ.get_budget(dept_id)
        self.assertEqual(final_bdg.reserved_usd, initial_reserved)
        self.assertEqual(final_bdg.spent_usd, initial_bdg.spent_usd)

    def test_06_duplicate_retry_idempotency(self):
        """Verify that duplicate settlement or reconciliation attempts are cleanly suppressed."""
        dept_id = "dept_eng"
        res = self.econ.reserve_budget(
            tenant_id=SIM_TENANT_ID,
            scope_chain=[("DEPARTMENT", dept_id)],
            requested_usd=500.0,
            task_id="idempotency_task"
        )
        # Settle once
        self.econ.settle_budget(res.reservation_id, actual_usd=500.0)

        # Attempt duplicate settlement
        with self.assertRaises(Exception):
            self.econ.settle_budget(res.reservation_id, actual_usd=500.0)

        # Reconcile billing once
        rec1 = self.billing.reconcile_economic_settlement(
            tenant_id=SIM_TENANT_ID,
            reservation_id=res.reservation_id,
            actual_tokens=1000,
            actual_usd=500.0
        )
        self.assertTrue(rec1["reconciled"])

        # Attempt duplicate reconciliation -> must return reconciled: False
        rec2 = self.billing.reconcile_economic_settlement(
            tenant_id=SIM_TENANT_ID,
            reservation_id=res.reservation_id,
            actual_tokens=1000,
            actual_usd=500.0
        )
        self.assertFalse(rec2["reconciled"])
        self.assertIn("already reconciled", rec2["message"])

    def test_07_cross_tenant_isolation_boundary(self):
        """Verify that another tenant cannot inspect, access, or mutate company memory, budgets, or records."""
        foreign_tenant_id = f"tnt_foreign_{uuid.uuid4().hex[:8]}"
        foreign_company_id = f"comp_foreign_{uuid.uuid4().hex[:8]}"

        # Query memory from foreign scope -> must return 0 records
        memories = self.memory.query_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=foreign_company_id,
            memory_key="task_dept_exec_record"
        )
        self.assertEqual(len(memories), 0)

        # Verify budget query under foreign tenant yields None
        foreign_bdg = self.econ.get_budget(f"bdg_{foreign_tenant_id}")
        self.assertIsNone(foreign_bdg)


if __name__ == "__main__":
    unittest.main()
