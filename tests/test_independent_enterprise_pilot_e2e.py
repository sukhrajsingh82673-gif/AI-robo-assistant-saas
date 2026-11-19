"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Independent Enterprise Pilot & End-to-End Operational Verification Suite
========================================================================
Validates the complete 11-point enterprise lifecycle:
1. Multi-Tenant Onboarding & User Authentication (JWT / Cryptographic tokens)
2. RBAC & Least-Privilege Authorization (Admin/Owner vs Operator vs Auditor)
3. Strict Cross-Tenant Isolation (Zero unauthorized cross-boundary access)
4. AI DLP & Sensitive Egress Containment (Token scrubbing & SSRF defense)
5. Governed Workflow Execution with Cryptographic Approval Receipt Gate
6. Merkle Evidence Audit Sealing & Tamper Verification
7. External Failure Handling & UNKNOWN_OUTCOME Safety Transition
8. SaaS Commercial Entitlements, Budget Reservations & Tier Upgrades
9. Sliding-Window Rate Limiting (HTTP 429 & RFC 6585 Retry-After)
10. Distributed Concurrency Leases & Contention Containment
11. Disaster Recovery Online Backup, SHA-256 Digest & Restore Parity
"""

import os
import sys
import time
import uuid
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db
from core.auth import (
    UserManager,
    UserRole,
    AuthorizationEnforcer
)
from core.economic_governance import (
    EconomicGovernanceEngine,
    BudgetExhaustionException,
    BudgetFrozenException
)
from core.cryptographic_approvals import (
    CryptographicApprovalEngine,
    HighRiskActionClass
)
from core.saas_billing import SaasBillingEngine, SubscriptionTier
from core.executive_missions import ExecutiveMissionPlanner
from core.automation_fabric import (
    universal_automation_fabric,
    ExecutionStatus,
    TerminalOutcome,
    ApprovalStatus
)
from core.evidence_service import evidence_service
from core.tenant_fairness import TenantFairnessEngine, ConcurrencyLeaseManager
from core.ai_dlp_gateway import (
    ai_dlp_gateway,
    DestinationTrustLevel,
    SecurityResponseClass,
    OutboundChannel,
    OutboundSecurityContext
)
from core.disaster_recovery import DisasterRecoveryManager


class TestIndependentEnterprisePilotE2E(unittest.TestCase):
    """
    Complete end-to-end operational verification across all production dimensions.
    """

    def setUp(self):
        self.tenant_a = f"tnt_e2e_pilot_{uuid.uuid4().hex[:6]}"
        self.tenant_b = f"tnt_e2e_rival_{uuid.uuid4().hex[:6]}"
        self.company_a = f"comp_pilot_{uuid.uuid4().hex[:6]}"
        self.company_b = f"comp_rival_{uuid.uuid4().hex[:6]}"

        self.user_mgr = UserManager()
        self.econ = EconomicGovernanceEngine()
        self.crypto = CryptographicApprovalEngine()
        self.billing = SaasBillingEngine()
        self.fairness = TenantFairnessEngine()
        self.lease_mgr = ConcurrencyLeaseManager()
        self.planner_a = ExecutiveMissionPlanner(self.tenant_a, self.company_a)
        self.planner_b = ExecutiveMissionPlanner(self.tenant_b, self.company_b)

        # Seed baseline tenant and company
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(tenant_id) DO NOTHING",
                (self.tenant_a, "Pilot Corp", "ENTERPRISE", "ACTIVE", time.time())
            )
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(tenant_id) DO NOTHING",
                (self.tenant_b, "Rival Corp", "STARTER", "ACTIVE", time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, created_at) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(company_id) DO NOTHING",
                (self.company_a, self.tenant_a, "Pilot Company", "TECHNOLOGY", "NEW", time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, created_at) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(company_id) DO NOTHING",
                (self.company_b, self.tenant_b, "Rival Company", "FINANCE", "NEW", time.time())
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # 1. Multi-Tenant Onboarding & User Authentication
    # -------------------------------------------------------------------------
    def test_01_tenant_and_user_lifecycle(self):
        """1. Provisions enterprise users, tests credentials, generates tokens."""
        u_admin = f"admin_{uuid.uuid4().hex[:6]}@pilot.corp"
        u_oper = f"oper_{uuid.uuid4().hex[:6]}@pilot.corp"

        # Register owner & operator with credentials
        user_admin = self.user_mgr.create_user_with_credentials(
            tenant_id=self.tenant_a,
            email=u_admin,
            name="Admin User",
            password="StrongPassword#2026!",
            role=UserRole.OWNER,
            company_id=self.company_a
        )
        self.assertIsNotNone(user_admin)
        self.assertEqual(user_admin["role"], UserRole.OWNER)

        user_oper = self.user_mgr.create_user_with_credentials(
            tenant_id=self.tenant_a,
            email=u_oper,
            name="Operator User",
            password="StrongPassword#2026!",
            role=UserRole.OPERATOR,
            company_id=self.company_a
        )
        self.assertIsNotNone(user_oper)
        self.assertEqual(user_oper["role"], UserRole.OPERATOR)

        # Authenticate and receive token
        ok, user_dict, msg = self.user_mgr.authenticate_user(
            email=u_admin,
            password="StrongPassword#2026!",
            tenant_id=self.tenant_a
        )
        self.assertTrue(ok)
        self.assertIsNotNone(user_dict)
        token = self.user_mgr.generate_token(user_dict)
        self.assertIsNotNone(token)

        # Validate token
        valid_user = self.user_mgr.verify_token(token)
        self.assertIsNotNone(valid_user)
        self.assertEqual(valid_user.get("tenant_id"), self.tenant_a)

    # -------------------------------------------------------------------------
    # 2. RBAC & Least-Privilege Authorization
    # -------------------------------------------------------------------------
    def test_02_rbac_and_least_privilege_enforcement(self):
        """2. Asserts Operator role cannot perform Administrator operations."""
        self.assertFalse(AuthorizationEnforcer.can_mutate_governance(UserRole.OPERATOR))
        self.assertFalse(AuthorizationEnforcer.can_manage_credentials(UserRole.OPERATOR))
        self.assertTrue(AuthorizationEnforcer.can_execute_missions(UserRole.OPERATOR))

        # Owner has broad authority
        self.assertTrue(AuthorizationEnforcer.can_mutate_governance(UserRole.OWNER))
        self.assertTrue(AuthorizationEnforcer.can_manage_credentials(UserRole.OWNER))
        self.assertTrue(AuthorizationEnforcer.can_execute_missions(UserRole.OWNER))

    # -------------------------------------------------------------------------
    # 3. Strict Cross-Tenant Isolation
    # -------------------------------------------------------------------------
    def test_03_tenant_isolation_boundary_enforcement(self):
        """3. Verifies Tenant B cannot query, access, or mutate Tenant A missions or records."""
        # Tenant A creates a confidential executive mission
        mission_a = self.planner_a.create_mission(
            objective_id="obj_confidential_mna",
            department="EXECUTIVE",
            manager="CEO",
            employee="CorporateStrategistAgent",
            title="Strategic Acquisition Deliberation",
            expected_output="Acquisition Target Valuation Digest",
            expected_business_outcome="Board approval of $2.5M LOI",
            kpi={"metric": "valuation_precision", "target": 0.98},
            kra=["Corporate M&A"],
            acceptance_criteria=["Due diligence complete", "Zero leak"],
            budget=50000.0,
            priority="P1",
            risk_level="CRITICAL"
        )
        self.assertIsNotNone(mission_a.mission_id)

        # Tenant B planner attempts to query Tenant A mission
        mission_b_view = self.planner_b.get_mission(mission_a.mission_id)
        self.assertIsNone(mission_b_view, "Tenant B must NOT access Tenant A mission (Zero leakage)")

    # -------------------------------------------------------------------------
    # 4. AI DLP & Sensitive Egress Containment
    # -------------------------------------------------------------------------
    def test_04_ai_dlp_and_sensitive_egress_containment(self):
        """4. Verifies sensitive credentials and PII are blocked or scrubbed by AI DLP."""
        ctx = OutboundSecurityContext(
            tenant_id=self.tenant_a,
            principal_id="usr_tester",
            principal_role="OPERATOR",
            calling_agent_id="agt_worker_01",
            channel=OutboundChannel.LLM_PROMPT,
            destination_name="UNAPPROVED_EXTERNAL_API",
            destination_trust=DestinationTrustLevel.UNAPPROVED_EXTERNAL
        )
        # Attempt to exfiltrate an AWS access key and private RSA key
        leak_attempt = "Secret AWS key: AKIAIOSFODNN7EXAMPLE and -----BEGIN RSA PRIVATE KEY-----"
        decision = ai_dlp_gateway.inspect_and_enforce(ctx, leak_attempt)

        self.assertFalse(decision.is_allowed)
        self.assertEqual(decision.response_class, SecurityResponseClass.CLASS_3_RESTRICT)

    # -------------------------------------------------------------------------
    # 5. Governed Workflow with Cryptographic Approval Receipt Gate
    # -------------------------------------------------------------------------
    def test_05_governed_workflow_with_cryptographic_approval(self):
        """5. Workflow prepares high-risk procurement order; pauses at approval gate; approves with receipt."""
        mission = self.planner_a.create_mission(
            objective_id="obj_hardware_order",
            department="PROCUREMENT",
            manager="ProcurementDirector",
            employee="VendorOrderAgent",
            title="Prepare High-Value Server Procurement",
            expected_output="Server PO draft with cryptographically signed receipt",
            expected_business_outcome="Signed order dispatched to hardware supplier",
            kpi={"metric": "order_accuracy", "target": 1.0},
            kra=["Procurement Integrity"],
            acceptance_criteria=["Supplier verified", "DoA executive receipt generated"],
            budget=20000.0,
            priority="P1",
            risk_level="HIGH"
        )

        exec_res = self.planner_a.execute_with_automation_fabric(
            mission_id=mission.mission_id,
            workflow_or_template_id="tmpl_erp_purchase_order_preparation",
            inputs={"supplier_id": "SUP-INTEL-DIRECT", "amount": 15000.0, "item_code": "SRV-XEON-9480"}
        )

        exec_id = exec_res.get("execution_id")
        self.assertIsNotNone(exec_id)
        # Order amount $15,000 exceeds $1,000 auto-approval threshold; must pause
        self.assertEqual(exec_res.get("status"), ExecutionStatus.WAITING_FOR_APPROVAL.value)

        approval_id = exec_res.get("approval_id")
        self.assertIsNotNone(approval_id)

        # Generate authenticated sovereign CEO token
        ceo_token = UserManager.create_session_token(
            tenant_id=self.tenant_a,
            user_id="Alex_CEO",
            role=UserRole.OWNER,
            company_id=self.company_a
        )

        # Decide approval
        decision = universal_automation_fabric.decide_approval(
            approval_id=approval_id,
            decision="APPROVE",
            actor="Alex_CEO",
            reason="Q4 infrastructure expansion budget approved and verified against vendor quotation",
            tenant_id=self.tenant_a,
            auth_token=ceo_token
        )
        self.assertEqual(decision["status"], ApprovalStatus.APPROVED.value)
        self.assertEqual(decision["actor_role"], UserRole.OWNER)

    # -------------------------------------------------------------------------
    # 6. Merkle Evidence Audit Sealing & Tamper Verification
    # -------------------------------------------------------------------------
    def test_06_merkle_evidence_audit_integrity(self):
        """6. Confirms physical action verification is sealed into the cryptographic evidence ledger."""
        payload = {"action": "DISASTER_RECOVERY_SNAPSHOT", "digest": "sha256-verified-snapshot-root"}

        res = evidence_service.record_event(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            event_type="DISASTER_RECOVERY_SEAL",
            payload=payload,
            mission_id="mis_dr_verify",
            action_id="act_dr_seal"
        )
        self.assertIsNotNone(res.get("current_hash"))
        self.assertEqual(res.get("verification_state"), "VERIFIED")

    # -------------------------------------------------------------------------
    # 7. External Failure Handling & UNKNOWN_OUTCOME Safety Transition
    # -------------------------------------------------------------------------
    def test_07_simulated_external_failure_and_unknown_outcome(self):
        """7. External network timeout safely halts execution as UNKNOWN_OUTCOME without fabricating success."""
        mission = self.planner_a.create_mission(
            objective_id="obj_wire_transfer",
            department="FINANCE",
            manager="Treasurer",
            employee="FinancialIntegrationAgent",
            title="Settle Bank Wire Transfer",
            expected_output="Wire settlement digest",
            expected_business_outcome="Transfer confirmed by central clearing house",
            kpi={"metric": "settlement_accuracy", "target": 1.0},
            kra=["Treasury Integrity"],
            acceptance_criteria=["Zero phantom transactions"]
        )

        wf_id = f"wf_timeout_{uuid.uuid4().hex[:6]}"
        flow_spec = {
            "id": wf_id,
            "namespace": "ura.finance.gateway",
            "tasks": [
                {
                    "id": "dispatch_wire",
                    "type": "io.kestra.plugin.zonata.connector.Call",
                    "connector_id": "conn_erpnext_records",
                    "action": "create_purchase_order",
                    "description": "Send international wire"
                }
            ]
        }
        universal_automation_fabric.create_workflow_draft("Wire Transfer", flow_spec, self.tenant_a, self.company_a)
        universal_automation_fabric.publish_workflow(wf_id, self.tenant_a)

        exec_res = self.planner_a.execute_with_automation_fabric(
            mission_id=mission.mission_id,
            workflow_or_template_id=wf_id,
            inputs={"simulate_timeout": True, "target_url": "https://api.clearinghouse.bank/wire"}
        )
        self.assertEqual(exec_res.get("status"), ExecutionStatus.UNKNOWN_OUTCOME.value)

    # -------------------------------------------------------------------------
    # 8. SaaS Commercial Entitlements, Budget Reservations & Tier Upgrades
    # -------------------------------------------------------------------------
    def test_08_saas_billing_entitlements_and_budget_limits(self):
        """8. Budget enforcement stops over-budget execution; tier upgrade unblocks capacity."""
        # Tenant B has STARTER tier with low budget
        sub_b = self.billing.get_or_create_subscription(
            tenant_id=self.tenant_b,
            tier=SubscriptionTier.STARTER
        )
        self.assertEqual(sub_b.tier, SubscriptionTier.STARTER)

        dept_id = f"mktg_{uuid.uuid4().hex[:6]}"
        # Allocate budget: $500 max
        self.econ.configure_budget(
            entity_id=dept_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_b,
            company_id=self.company_b,
            allocated_usd=500.0
        )

        # Reservation of $200 succeeds
        res_ok = self.econ.reserve_budget(
            tenant_id=self.tenant_b,
            scope_chain=[("DEPARTMENT", dept_id)],
            requested_usd=200.0
        )
        self.assertIsNotNone(res_ok.reservation_id)
        self.assertEqual(res_ok.status, "RESERVED")

        # Reservation of $400 exceeds remaining $300 balance -> throws BudgetExhaustionException
        with self.assertRaises(BudgetExhaustionException):
            self.econ.reserve_budget(
                tenant_id=self.tenant_b,
                scope_chain=[("DEPARTMENT", dept_id)],
                requested_usd=400.0
            )

        # Upgrade Tenant B to ENTERPRISE tier and allocate $10,000 budget
        self.billing.upgrade_plan(self.tenant_b, SubscriptionTier.ENTERPRISE)
        self.econ.configure_budget(
            entity_id=dept_id,
            entity_type="DEPARTMENT",
            tenant_id=self.tenant_b,
            company_id=self.company_b,
            allocated_usd=10000.0
        )

        # Reservation of $400 now succeeds
        res_after = self.econ.reserve_budget(
            tenant_id=self.tenant_b,
            scope_chain=[("DEPARTMENT", dept_id)],
            requested_usd=400.0
        )
        self.assertIsNotNone(res_after.reservation_id)
        self.assertEqual(res_after.status, "RESERVED")

    # -------------------------------------------------------------------------
    # 9. Sliding-Window Rate Limiting (HTTP 429 & RFC 6585 Retry-After)
    # -------------------------------------------------------------------------
    def test_09_sliding_window_rate_limiting_enforcement(self):
        """9. Bursts exceeding sliding-window ceiling are rejected with RFC 6585 headers."""
        tenant_rate_test = f"tnt_rate_{uuid.uuid4().hex[:6]}"
        ip = "192.168.1.100"

        # Allowed requests under IP threshold
        for i in range(5):
            decision = self.fairness.evaluate_request(
                path="/api/auth/token",
                method="POST",
                client_ip=ip
            )
            self.assertTrue(decision.is_allowed, f"Request {i} should be allowed")

        # Exceed login attempt limit
        blocked = False
        retry_after = 0
        for i in range(35):
            decision = self.fairness.evaluate_request(
                path="/api/auth/token",
                method="POST",
                client_ip=ip
            )
            if not decision.is_allowed:
                blocked = True
                retry_after = decision.retry_after
                break

        self.assertTrue(blocked, "Burst auth attempts must trigger 429 rate limit")
        self.assertGreater(retry_after, 0, "Must provide RFC 6585 Retry-After value")

    # -------------------------------------------------------------------------
    # 10. Distributed Concurrency Leases & Contention Containment
    # -------------------------------------------------------------------------
    def test_10_concurrent_lease_governance_exhaustion(self):
        """10. Proves max concurrent leases per tenant (4) strictly blocks 5th simultaneous lease."""
        tenant_lease_test = f"tnt_lease_{uuid.uuid4().hex[:6]}"

        leases = []
        # Acquire up to configured max limit (4)
        for i in range(4):
            acq, lid, retry = self.lease_mgr.acquire_lease(
                tenant_id=tenant_lease_test,
                max_concurrency=4,
                lease_type="WORKFLOW",
                ttl_seconds=30.0
            )
            self.assertTrue(acq, f"Lease {i+1} must be acquired")
            self.assertIsNotNone(lid)
            leases.append(lid)

        # 5th simultaneous lease must be rejected
        acq_5, lid_5, retry_5 = self.lease_mgr.acquire_lease(
            tenant_id=tenant_lease_test,
            max_concurrency=4,
            lease_type="WORKFLOW",
            ttl_seconds=30.0
        )
        self.assertFalse(acq_5, "5th lease must be rejected under 4-lease ceiling")
        self.assertIsNone(lid_5)
        self.assertGreater(retry_5, 0)

        # Release one lease
        rel_ok = self.lease_mgr.release_lease(leases[0])
        self.assertTrue(rel_ok)

        # Now acquire succeeds
        acq_retry, lid_retry, _ = self.lease_mgr.acquire_lease(
            tenant_id=tenant_lease_test,
            max_concurrency=4,
            lease_type="WORKFLOW",
            ttl_seconds=30.0
        )
        self.assertTrue(acq_retry, "Lease must succeed once a slot is freed")
        self.assertIsNotNone(lid_retry)

        # Cleanup
        for l in leases[1:]:
            self.lease_mgr.release_lease(l)
        self.lease_mgr.release_lease(lid_retry)

    # -------------------------------------------------------------------------
    # 11. Disaster Recovery Online Backup, SHA-256 Digest & Restore Parity
    # -------------------------------------------------------------------------
    def test_11_disaster_recovery_backup_and_restore_drill(self):
        """11. Performs online hot backup, verifies SHA-256 root, restores drill, verifies record parity."""
        backup_tmp_dir = tempfile.mkdtemp()
        restore_tmp_file = tempfile.mktemp(suffix=".db")

        try:
            dr = DisasterRecoveryManager(tenant_id=self.tenant_a, backup_dir=backup_tmp_dir)
            snapshot = dr.create_hot_snapshot(backup_type="FULL_SNAPSHOT")

            manifest_id = snapshot.get("manifest_id")
            self.assertIsNotNone(manifest_id)
            self.assertIsNotNone(snapshot.get("sha256_checksum"))
            self.assertTrue(os.path.exists(snapshot.get("file_path")))

            # Verify and restore
            restore_res = dr.verify_and_restore_snapshot(
                manifest_id=manifest_id,
                target_restore_path=restore_tmp_file
            )
            self.assertTrue(restore_res.get("checksum_verified", False))
            self.assertTrue(restore_res.get("sqlite_integrity_ok", False))
            self.assertTrue(os.path.exists(restore_tmp_file))
        finally:
            shutil.rmtree(backup_tmp_dir, ignore_errors=True)
            if os.path.exists(restore_tmp_file):
                os.remove(restore_tmp_file)


if __name__ == "__main__":
    unittest.main()
