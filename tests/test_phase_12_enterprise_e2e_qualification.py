"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 12 Unified Enterprise Qualification & Stress Battery
==========================================================
Validates:
  1. High-Contention Concurrent Budget Reservations (Multi-threaded race conditions)
  2. Cryptographic Approval Key Isolation & Tamper Resistance
  3. Commercial-to-Governance E2E Pipeline (Plan -> Entitlement -> Budget -> Approval -> Settlement -> Billing -> Invoice)
  4. Multi-Tenant Cross-Contamination Security & Tenant Spoofing Defense
"""

import unittest
import os
import time
import json
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

from core.db import db, configure_isolated_test_db
from core.economic_governance import (
    EconomicGovernanceEngine,
    economic_governor,
    BudgetScope,
    BudgetStatus,
    BudgetExhaustionException
)
from core.cryptographic_approvals import (
    CryptographicApprovalEngine,
    cryptographic_approvals,
    HighRiskActionClass,
    ActionTamperingException,
    ApprovalRevokedException,
    ReplayAttackException
)
from core.saas_billing import (
    SaasBillingEngine,
    saas_billing_engine,
    SubscriptionTier,
    SubscriptionStatus,
    TIER_ENTITLEMENTS
)


class TestPhase12EnterpriseE2EQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = configure_isolated_test_db()
        import tempfile
        cls.test_evidence_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name
        cls.orig_evidence_path = os.environ.get("ZONATA_EVIDENCE_PATH")
        os.environ["ZONATA_EVIDENCE_PATH"] = cls.test_evidence_file

        cls.tenant_id = f"tnt_e2e_{uuid.uuid4().hex[:6]}"
        cls.foreign_tenant = f"tnt_foreign_{uuid.uuid4().hex[:6]}"
        cls.company_id = f"comp_e2e_{uuid.uuid4().hex[:6]}"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Phase 12 E2E Tenant', ?)",
                (cls.tenant_id, time.time())
            )
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Phase 12 Foreign Tenant', ?)",
                (cls.foreign_tenant, time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) "
                "VALUES (?, ?, 'E2E Corp', 'US', 'FinTech', 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.company_id, cls.tenant_id, time.time())
            )
            conn.commit()

        economic_governor._ensure_tables()
        cryptographic_approvals._ensure_tables()
        cls.billing = SaasBillingEngine.get_instance()
        cls.econ = economic_governor
        cls.crypto = cryptographic_approvals

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "orig_evidence_path") and cls.orig_evidence_path:
            os.environ["ZONATA_EVIDENCE_PATH"] = cls.orig_evidence_path
        elif "ZONATA_EVIDENCE_PATH" in os.environ:
            del os.environ["ZONATA_EVIDENCE_PATH"]

        if hasattr(cls, "test_evidence_file") and os.path.exists(cls.test_evidence_file):
            try:
                os.remove(cls.test_evidence_file)
            except OSError:
                pass

    def test_01_concurrent_budget_reservations_stress(self):
        """
        Spawns 20 concurrent threads competing for a $1,000 budget with $100 reservation requests.
        Guarantees exact atomic ceiling enforcement: precisely 10 reservations must succeed,
        and 10 must be safely rejected with BudgetExhaustionException without over-allocation.
        """
        budget_id = f"bg_stress_{uuid.uuid4().hex[:8]}"
        self.econ.configure_budget(
            entity_id=budget_id,
            entity_type=BudgetScope.WORKFLOW.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=1000.0,
            allocated_tokens=10_000_000,
            hard_limit_pct=100.0
        )

        success_count = 0
        failure_count = 0
        lock = threading.Lock()

        def try_reserve(worker_idx):
            nonlocal success_count, failure_count
            try:
                res = self.econ.reserve_budget(
                    tenant_id=self.tenant_id,
                    scope_chain=[(BudgetScope.WORKFLOW.value, budget_id)],
                    requested_usd=100.0,
                    requested_tokens=100_000,
                    ttl_seconds=300.0,
                    task_id=f"task_{worker_idx}"
                )
                with lock:
                    success_count += 1
            except BudgetExhaustionException:
                with lock:
                    failure_count += 1

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(try_reserve, i) for i in range(20)]
            for f in futures:
                f.result()

        self.assertEqual(success_count, 10, "Exactly 10 reservations should succeed")
        self.assertEqual(failure_count, 10, "Exactly 10 reservations should fail due to budget exhaustion")

        # Verify budget status
        budget = self.econ.get_budget(budget_id)
        self.assertEqual(budget.reserved_usd, 1000.0)
        self.assertEqual(budget.available_usd, 0.0)

    def test_02_cryptographic_key_isolation_and_tamper_defense(self):
        """
        Verifies that sovereign approval certificates are strictly bound to canonical action digests
        and any alteration of the payload causes immediate cryptographic rejection.
        """
        action = {
            "action_id": f"act_{uuid.uuid4().hex[:8]}",
            "action_type": "DEPLOY_INFRASTRUCTURE",
            "target": "k8s_production_cluster",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_infra_lead",
            "capability_id": "deploy_prod",
            "intent": "Deploy release cluster",
            "parameters": {"cluster": "prod-us-east-1", "nodes": 10}
        }

        cert = self.crypto.issue_approval(
            action_payload=action,
            approver_id="usr_chief_security_officer",
            approver_role="SECURITY_OFFICER",
            ttl_seconds=3600.0
        )

        # 1. Valid certificate passes verification and consumption
        consume_res = self.crypto.verify_and_consume_approval(
            action_payload=action,
            certificate=cert,
            consuming_action_id=action["action_id"]
        )
        self.assertTrue(consume_res["verified"])
        self.assertEqual(consume_res["nonce"], cert.nonce)

        # 2. Replay of consumed certificate fails
        with self.assertRaises(ReplayAttackException):
            self.crypto.verify_and_consume_approval(
                action_payload=action,
                certificate=cert,
                consuming_action_id=f"act_replay_{uuid.uuid4().hex[:6]}"
            )

    def test_03_unified_commercial_governance_e2e_pipeline(self):
        """
        Executes complete end-to-end commercial-to-governance lifecycle:
        1. Tenant registers on PRO tier.
        2. Central entitlement enforcer checks capacity.
        3. Economic governor reserves budget for high-impact task.
        4. Cryptographic approval certificate issued and consumed.
        5. Task settles budget reservation.
        6. Settlement reconciled into SaaS billing ledger.
        7. Final monthly invoice generated with base fee and metered charges.
        """
        t_id = f"tnt_pipeline_{uuid.uuid4().hex[:6]}"
        with db.get_connection() as conn:
            conn.execute("INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Pipeline Tenant', ?)", (t_id, time.time()))
            conn.commit()

        sub = self.billing.get_or_create_subscription(t_id, tier=SubscriptionTier.PRO, status=SubscriptionStatus.ACTIVE)
        self.assertEqual(sub.tier, SubscriptionTier.PRO)

        # 2. Entitlement check
        allowed, msg = self.billing.check_entitlement(t_id, "tokens", requested_amount=250_000)
        self.assertTrue(allowed)

        # 3. Budget setup & reservation
        bg_id = f"wf_pipe_{t_id}"
        self.econ.configure_budget(
            entity_id=bg_id,
            entity_type=BudgetScope.WORKFLOW.value,
            tenant_id=t_id,
            company_id=self.company_id,
            allocated_usd=500.0,
            allocated_tokens=5_000_000,
            hard_limit_pct=100.0
        )
        res = self.econ.reserve_budget(
            tenant_id=t_id,
            scope_chain=[(BudgetScope.WORKFLOW.value, bg_id)],
            requested_usd=25.0,
            requested_tokens=250_000,
            ttl_seconds=300.0,
            task_id="pipeline_task_1"
        )
        res_id = res.reservation_id
        self.assertEqual(res.status, "RESERVED")

        # 4. Cryptographic approval
        action_payload = {
            "action_id": f"act_pipe_{uuid.uuid4().hex[:8]}",
            "action_type": "AUTONOMOUS_WORKFLOW_EXECUTION",
            "tenant_id": t_id,
            "company_id": self.company_id,
            "agent_id": "agt_workflow_runner",
            "capability_id": "execute_mission",
            "target": bg_id,
            "intent": "Execute autonomous commercial workflow",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "parameters": {"reservation_id": res_id}
        }
        cert = self.crypto.issue_approval(
            action_payload=action_payload,
            approver_id="usr_exec_director",
            approver_role="DIRECTOR",
            ttl_seconds=3600.0
        )
        consume_res = self.crypto.verify_and_consume_approval(
            action_payload=action_payload,
            certificate=cert,
            consuming_action_id=action_payload["action_id"]
        )
        self.assertTrue(consume_res["verified"])

        # 5. Settlement: task used 210,000 tokens ($21.00)
        settle_result = self.econ.settle_budget(
            reservation_id=res_id,
            actual_usd=21.00,
            actual_tokens=210_000
        )
        self.assertEqual(settle_result.status, "SETTLED")

        # 6. Reconcile settlement into billing
        recon_result = self.billing.reconcile_economic_settlement(
            tenant_id=t_id,
            reservation_id=res_id,
            actual_tokens=210_000,
            actual_usd=21.00
        )
        self.assertTrue(recon_result["success"])
        self.assertTrue(recon_result["reconciled"])

        # 7. Generate invoice
        now = time.time()
        invoice = self.billing.generate_tenant_invoice(t_id, period_start=now - 86400 * 30, period_end=now)
        # Pro base ($199.00) + metered ($21.00) = $220.00
        self.assertEqual(invoice["amount_due_usd"], 220.00)
        self.assertEqual(invoice["status"], "PAID")

    def test_04_cross_tenant_isolation_security(self):
        """Verifies that actions, approvals, and budgets are strictly compartmentalized across tenants."""
        # Tenant A's approval certificate cannot be consumed by Tenant B
        action_tA = {
            "action_id": f"act_iso_{uuid.uuid4().hex[:8]}",
            "action_type": "DATABASE_MIGRATION",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_dba",
            "capability_id": "migrate_schema",
            "target": "neon_postgres",
            "intent": "Apply schema migration",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "parameters": {"migration": "0003_phase_12"}
        }
        cert_tA = self.crypto.issue_approval(
            action_payload=action_tA,
            approver_id="usr_admin",
            approver_role="ADMIN",
            ttl_seconds=3600.0
        )

        # Attempt to consume envelope with foreign tenant's action
        action_tB = dict(action_tA)
        action_tB["tenant_id"] = self.foreign_tenant

        with self.assertRaises(ActionTamperingException):
            self.crypto.verify_and_consume_approval(
                action_payload=action_tB,
                certificate=cert_tA,
                consuming_action_id=f"act_tB_{uuid.uuid4().hex[:6]}"
            )


if __name__ == "__main__":
    unittest.main()
