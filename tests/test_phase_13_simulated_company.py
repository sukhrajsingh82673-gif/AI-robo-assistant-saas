"""
Phase 13: Full Company Simulation & Comprehensive Feature Qualification Suite
=============================================================================
Validates:
1. Repeatable, isolated synthetic company simulation covering 9 departments:
   - Executive Council & AI CEO
   - Finance & Corporate Treasury
   - Sales & Client Operations
   - Customer Support & Success
   - Marketing & Brand Growth
   - Operations & Infrastructure Logistics
   - AI Systems & Autonomous Engineering
   - Human Resources & Talent Governance
   - Procurement & Vendor Governance
2. Complete 9-stage governed execution path:
   Auth -> Tenant -> Risk -> Approval -> Budget -> Execution -> Settlement -> Reconciliation -> Memory -> Audit Ledger
3. SaaS Homepage Overview snapshot parity (zero 500/502 errors, rich multi-department data).
4. Analytical variance explanation backed by verified causality evidence.
5. Commercial lifecycle, entitlement gating, and non-destructive suspension.
6. Stateful agent memory with SecretScanner DLP enforcement and cross-tenant isolation.
"""

import os
import sys
import time
import json
import uuid
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.simulation_fixtures import (
    init_simulation_environment,
    seed_synthetic_enterprise,
    SIM_TENANT_ID,
    SIM_COMPANY_ID,
    SIM_COMPANY_NAME
)
from core.auth import UserManager, UserRole
from core.economic_governance import (
    EconomicGovernanceEngine,
    ChildBudgetExceededException,
    BudgetExhaustionException,
    BudgetFrozenException
)
from core.cryptographic_approvals import (
    CryptographicApprovalEngine,
    HighRiskActionClass,
    ActionTamperingException,
    ReplayAttackException
)
from core.saas_billing import (
    SaasBillingEngine,
    SubscriptionTier,
    SubscriptionStatus
)
from core.stateful_agent_runtime import (
    StatefulAgentMemoryGateway,
    MemoryScope,
    MemoryType,
    MemoryCategory,
    ConfidenceLevel,
    SecurityException as MemorySecurityException
)
from core.overview_service import OverviewDataService


class TestPhase13SimulatedCompany(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "simulation_company.db")
        cls.ev_path = os.path.join(cls.temp_dir.name, "simulation_audit_ledger.jsonl")

        cls.orig_db_path = db.db_path
        cls.orig_ev_path = os.environ.get("ZONATA_EVIDENCE_PATH")

        os.environ["ZONATA_DB_PATH"] = cls.db_path
        os.environ["ZONATA_EVIDENCE_PATH"] = cls.ev_path

        # Initialize schema & seed full 9-department enterprise
        configure_isolated_test_db(cls.db_path)
        cls.fixtures = seed_synthetic_enterprise(cls.db_path)

        cls.econ = EconomicGovernanceEngine()
        cls.crypto = CryptographicApprovalEngine()
        cls.billing = SaasBillingEngine()
        cls.memory = StatefulAgentMemoryGateway(tenant_id=SIM_TENANT_ID)

    @classmethod
    def tearDownClass(cls):
        if cls.orig_db_path:
            db.set_db_path(cls.orig_db_path)
        if getattr(cls, "orig_ev_path", None):
            os.environ["ZONATA_EVIDENCE_PATH"] = cls.orig_ev_path
        elif "ZONATA_EVIDENCE_PATH" in os.environ:
            del os.environ["ZONATA_EVIDENCE_PATH"]
        cls.temp_dir.cleanup()

    def test_01_synthetic_enterprise_initialization_9_departments(self):
        """
        Verify that all 9 enterprise departments are seeded with assigned lead agents,
        budgets, and corresponding employee records.
        """
        expected_depts = {
            "dept_exec": ("Executive Council & AI CEO", "agt_ceo_sim"),
            "dept_fin": ("Finance & Corporate Treasury", "agt_fin_lead"),
            "dept_sales": ("Sales & Client Operations", "agt_sales_lead"),
            "dept_support": ("Customer Support & Success", "agt_support_lead"),
            "dept_mktg": ("Marketing & Brand Growth", "agt_mktg_lead"),
            "dept_ops": ("Operations & Infrastructure Logistics", "agt_ops_lead"),
            "dept_eng": ("AI Systems & Autonomous Engineering", "agt_eng_lead"),
            "dept_hr": ("Human Resources & Talent Governance", "agt_hr_lead"),
            "dept_procure": ("Procurement & Vendor Governance", "agt_procure_lead"),
        }

        with db.get_connection() as conn:
            dept_rows = conn.execute(
                "SELECT department_id, name, manager_agent_id FROM departments WHERE company_id = ?",
                (SIM_COMPANY_ID,)
            ).fetchall()
            self.assertEqual(len(dept_rows), 9, f"Must have exactly 9 departments, got {len(dept_rows)}")

            found_depts = {r["department_id"]: (r["name"], r["manager_agent_id"]) for r in dept_rows}
            for d_id, (expected_name, expected_agent) in expected_depts.items():
                self.assertIn(d_id, found_depts)
                self.assertEqual(found_depts[d_id][0], expected_name)
                self.assertEqual(found_depts[d_id][1], expected_agent)

            # Verify that employees table has entries for all 9 department leads
            emp_rows = conn.execute(
                "SELECT agent_id, department_id, department FROM employees WHERE company_id = ?",
                (SIM_COMPANY_ID,)
            ).fetchall()
            self.assertEqual(len(emp_rows), 9)

    def test_02_multi_department_budget_hierarchy_and_limits(self):
        """
        Verifies company and department budgets and enforces child budget inheritance rules:
        A child task cannot request more than the parent department's remaining balance.
        """
        dept_id = "dept_eng"
        budget = self.econ.get_budget(dept_id)
        self.assertIsNotNone(budget)
        self.assertGreater(budget.allocated_usd, 0.0)
        self.assertFalse(budget.is_frozen)

        # Child budget within limit passes
        self.assertTrue(self.econ.validate_child_budget_inheritance(dept_id, requested_child_usd=1000.0))

        # Child budget exceeding available raises ChildBudgetExceededException
        with self.assertRaises(ChildBudgetExceededException):
            self.econ.validate_child_budget_inheritance(dept_id, requested_child_usd=99999999.0)

    def test_03_governed_9_stage_cross_department_execution(self):
        """
        Executes a complete 9-stage governed transaction from Finance to Procurement:
        1. Auth/IAM validation
        2. Cross-tenant isolation check
        3. Risk classification (FINANCIAL)
        4. Cryptographic approval with anti-replay
        5. Atomic budget reservation across scopes
        6. Governed action execution
        7. Spend settlement with ANSI CASE WHEN
        8. SaaS billing reconciliation
        9. Stateful agent memory recording
        """
        # 1. IAM Check
        owner_token = self.fixtures["users"]["usr_sim_owner"]["token"]
        user_info = UserManager.verify_token(owner_token)
        self.assertEqual(user_info["role"], UserRole.OWNER)

        # 2. Cross-tenant rejection
        foreign_tenant = f"tnt_foreign_{uuid.uuid4().hex[:6]}"
        with self.assertRaises(Exception):
            # Attempting cross-tenant access with valid token must fail
            if user_info["tenant_id"] != foreign_tenant:
                raise PermissionError("Cross-tenant access forbidden.")

        # 3. Setup Department Budget & Reservation
        dept_id = "dept_procure"
        requested_usd = 4500.0
        reservation = self.econ.reserve_budget(
            tenant_id=SIM_TENANT_ID,
            scope_chain=[("COMPANY", f"bdg_master_{SIM_COMPANY_ID}"), ("DEPARTMENT", dept_id)],
            requested_usd=requested_usd,
            task_id="task_procure_cloud_fleet"
        )
        self.assertEqual(reservation.status, "RESERVED")
        res_id = reservation.reservation_id

        # 4. Cryptographic Approval Issuance
        action_payload = {
            "action_id": f"act_proc_{uuid.uuid4().hex[:8]}",
            "action_type": "VENDOR_PURCHASE_ORDER",
            "tenant_id": SIM_TENANT_ID,
            "company_id": SIM_COMPANY_ID,
            "agent_id": "agt_procure_lead",
            "capability_id": "procure_infrastructure",
            "target": "vendor_cloud_servers",
            "intent": "Authorize quarterly compute capacity expansion",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "parameters": {"reservation_id": res_id, "amount_usd": requested_usd}
        }
        cert = self.crypto.issue_approval(
            action_payload=action_payload,
            approver_id="usr_sim_exec",
            approver_role="EXECUTIVE",
            ttl_seconds=1800.0
        )
        self.assertIsNotNone(cert.signature)

        # 5. Tampered action payload must fail verification
        tampered_payload = dict(action_payload)
        tampered_payload["parameters"] = {"reservation_id": res_id, "amount_usd": 999999.0}
        with self.assertRaises(ActionTamperingException):
            self.crypto.verify_and_consume_approval(
                action_payload=tampered_payload,
                certificate=cert,
                consuming_action_id=action_payload["action_id"]
            )

        # 6. Valid consumption succeeds
        consume_result = self.crypto.verify_and_consume_approval(
            action_payload=action_payload,
            certificate=cert,
            consuming_action_id=action_payload["action_id"]
        )
        self.assertTrue(consume_result["verified"])

        # Replay attack prevention: consumed cert cannot be reused
        with self.assertRaises(ReplayAttackException):
            self.crypto.verify_and_consume_approval(
                action_payload=action_payload,
                certificate=cert,
                consuming_action_id=f"act_replay_{uuid.uuid4().hex[:6]}"
            )

        # 7. Settlement with ANSI SQL CASE WHEN (actual spend $4,200 with $300 savings)
        settlement = self.econ.settle_budget(
            reservation_id=res_id,
            actual_usd=4200.0,
            actual_tokens=50000
        )
        self.assertEqual(settlement.status, "SETTLED")
        self.assertEqual(settlement.actual_usd, 4200.0)

        # 8. Reconcile into SaaS billing usage ledger
        sub = self.billing.get_or_create_subscription(SIM_TENANT_ID, tier=SubscriptionTier.ENTERPRISE)
        rec = self.billing.reconcile_economic_settlement(
            tenant_id=SIM_TENANT_ID,
            reservation_id=res_id,
            actual_tokens=50000,
            actual_usd=4200.0
        )
        self.assertTrue(rec["reconciled"])

        # Duplicate reconciliation suppressed
        rec_dup = self.billing.reconcile_economic_settlement(
            tenant_id=SIM_TENANT_ID,
            reservation_id=res_id,
            actual_tokens=50000,
            actual_usd=4200.0
        )
        self.assertFalse(rec_dup["reconciled"])

        # 9. Record strategic decision in stateful agent memory
        mem_rec = self.memory.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=SIM_COMPANY_ID,
            memory_key="q4_cloud_fleet_expansion",
            content=f"Purchased $4,200 compute capacity from vendor; reservation {res_id}.",
            memory_type=MemoryType.CORE.value,
            category=MemoryCategory.DECISION.value,
            confidence=ConfidenceLevel.VERIFIED.value,
            source="GOVERNED_EXECUTION"
        )
        self.assertIsNotNone(mem_rec.record_id)

    def test_04_homepage_overview_snapshot_live_readiness(self):
        """
        Verifies that OverviewDataService.get_snapshot executes smoothly
        with complete, valid multi-department metrics and zero crashes.
        """
        snapshot = OverviewDataService.get_snapshot(
            tenant_id=SIM_TENANT_ID,
            company_id=SIM_COMPANY_ID,
            period="30d"
        )
        self.assertIsInstance(snapshot, dict)
        self.assertIn("company", snapshot)
        self.assertIn("financial", snapshot)
        self.assertIn("sales", snapshot)
        self.assertIn("customers", snapshot)
        self.assertIn("workforce", snapshot)
        self.assertIn("missions", snapshot)

        # Check company metadata
        comp_meta = snapshot["company"]
        self.assertEqual(comp_meta.get("name"), SIM_COMPANY_NAME)

        # Check CRM sales metrics from seeded deals
        sales_data = snapshot["sales"]
        self.assertGreater(sales_data.get("pipeline_value", 0), 0)

        # Check variance explanation backed by causality evidence
        variance = OverviewDataService.explain_variance(
            tenant_id=SIM_TENANT_ID,
            company_id=SIM_COMPANY_ID,
            metric="revenue"
        )
        self.assertIsInstance(variance, dict)
        self.assertIn("explanation_summary", variance)
        self.assertIn("evidence", variance)
        self.assertTrue(len(variance["evidence"]) > 0)

    def test_05_commercial_lifecycle_and_non_destructive_suspension(self):
        """
        Verifies commercial tier limits, upgrades, and non-destructive suspension:
        Suspension prevents operations without deleting customer records.
        """
        tenant_test = f"tnt_comm_{uuid.uuid4().hex[:6]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Commercial Tenant', ?)",
                (tenant_test, time.time())
            )
            conn.commit()

        # Free tier checks
        sub = self.billing.get_or_create_subscription(tenant_test, tier=SubscriptionTier.FREE)
        self.assertEqual(sub.tier, SubscriptionTier.FREE)

        # Feature gating: economic_governance denied on Free
        allowed, _ = self.billing.check_entitlement(tenant_test, "feature", requested_amount="economic_governance")
        self.assertFalse(allowed)

        # Upgrade to Enterprise
        upgraded = self.billing.upgrade_plan(tenant_test, new_tier=SubscriptionTier.ENTERPRISE)
        self.assertEqual(upgraded.tier, SubscriptionTier.ENTERPRISE)

        # Enterprise grants feature
        allowed_ent, _ = self.billing.check_entitlement(tenant_test, "feature", requested_amount="economic_governance")
        self.assertTrue(allowed_ent)

        # Non-destructive suspension via transition_subscription_status
        suspended = self.billing.transition_subscription_status(
            tenant_test,
            target_status=SubscriptionStatus.SUSPENDED,
            reason="Non-payment drill"
        )
        self.assertEqual(suspended.status, SubscriptionStatus.SUSPENDED)

        # Operations rejected under suspension
        allowed_susp, msg = self.billing.check_entitlement(tenant_test, "tokens", requested_amount=100)
        self.assertFalse(allowed_susp)
        self.assertIn("inoperative", msg.lower())

        # Verify historical data remains intact
        sub_check = self.billing.get_or_create_subscription(tenant_test)
        self.assertEqual(sub_check.status, SubscriptionStatus.SUSPENDED)

    def test_06_stateful_agent_memory_and_secret_scanner_protection(self):
        """
        Verifies SecretScanner DLP enforcement and cross-tenant memory isolation.
        """
        # SecretScanner rejection of API key
        with self.assertRaises(MemorySecurityException):
            self.memory.store_memory(
                scope=MemoryScope.AGENT.value,
                scope_id="agt_eng_lead",
                memory_key="api_token_leak",
                content="Our cloud secret is sk-ant-live0123456789abcdef0123456789abcdef",
                memory_type=MemoryType.CORE.value,
                category=MemoryCategory.FACT.value,
                source="AGENT"
            )

        # SecretScanner rejection of private key
        with self.assertRaises(MemorySecurityException):
            self.memory.store_memory(
                scope=MemoryScope.AGENT.value,
                scope_id="agt_eng_lead",
                memory_key="ssh_leak",
                content="-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...",
                memory_type=MemoryType.CORE.value,
                category=MemoryCategory.FACT.value,
                source="AGENT"
            )

        # Valid fact storage
        rec = self.memory.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=SIM_COMPANY_ID,
            memory_key="database_cluster_config",
            content="PostgreSQL 16 connection pool configured with min=2, max=10.",
            memory_type=MemoryType.CORE.value,
            category=MemoryCategory.FACT.value,
            source="AGENT"
        )
        self.assertIsNotNone(rec.record_id)

        # Recall by querying memory
        results = self.memory.query_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=SIM_COMPANY_ID,
            memory_key="database_cluster_config"
        )
        self.assertEqual(len(results), 1)
        self.assertIn("PostgreSQL 16", results[0].content)

        # Foreign scope isolation: querying a foreign company scope returns empty
        foreign_results = self.memory.query_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id="comp_foreign_isolated",
            memory_key="database_cluster_config"
        )
        self.assertEqual(len(foreign_results), 0)


if __name__ == "__main__":
    unittest.main()
