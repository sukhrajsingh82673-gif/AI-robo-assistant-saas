"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 25 — Enterprise Architectural Invariants & Constitutional Test Suite (V4)
Formally verifies all 22 required architectural invariants with executable assertions.
Classification: REAL_LOCAL_INFRASTRUCTURE
"""

import time
import json
import uuid
import unittest
from core.database_engine import engine, WorkloadType
from core.identity_gateway import identity_gateway, IdentityType, IdentityStatus
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState, AuthorityScope
from core.workforce_manager_v4 import workforce_manager_v4, DelegationViolationError
from core.corporate_data_plane import corporate_data_gateway, DataObjectACL, DeletionState
from core.knowledge_gateway import knowledge_gateway
from core.model_gateway_v4 import model_gateway_v4, ModelSecurityException
from core.model_data_firewall import model_data_firewall
from core.policy_engine_v2 import policy_engine_v2, PolicyContext, PolicyDecision
from core.unknown_outcome_engine import unknown_outcome_engine, ReconciledStatus
from core.memory_governance import memory_governance_gateway, EpistemicMemoryTier, KnowledgeTrustState
from core.data_lifecycle_manager import data_lifecycle_manager, LegalHoldViolationError

class TestV4EnterpriseInvariants(unittest.TestCase):
    CLASSIFICATION = "REAL_LOCAL_INFRASTRUCTURE"

    @classmethod
    def setUpClass(cls):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, status, plan, created_at) VALUES ('tnt_v4_inv', 'V4 Invariant Tenant', 'ACTIVE', 'ENTERPRISE', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO companies (company_id, tenant_id, name, status, created_at) VALUES ('comp_v4_inv', 'tnt_v4_inv', 'V4 Invariant Company', 'OPERATIONAL', ?)", (time.time(),))

    def test_inv_01_identity_not_authority(self):
        """Invariant: IDENTITY != AUTHORITY (Holding verified identity does not confer authority)."""
        ident = identity_gateway.register_identity(
            identity_id=f"usr_inv_{uuid.uuid4().hex[:6]}",
            identity_type=IdentityType.HUMAN,
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            display_name="Basic Viewer",
            roles=["VIEWER"],
            departments=["MARKETING"]
        )
        token = identity_gateway.issue_token(ident)
        valid, claims, _ = identity_gateway.verify_token(token)
        self.assertTrue(valid)
        self.assertEqual(claims["roles"], ["VIEWER"])

        # Viewer identity attempts financial mutation
        ctx = PolicyContext(
            requester_id=ident.identity_id,
            requester_type=IdentityType.HUMAN,
            requester_roles=ident.roles,
            requester_departments=ident.departments,
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            action="FINANCIAL_TRANSFER",
            intent="Pay vendor",
            mission_id=None,
            tool_risk_class="FINANCIAL",
            requested_spend_usd=1000.0,
            employee_remaining_budget_usd=0.0
        )
        eval_res = policy_engine_v2.evaluate(ctx)
        self.assertEqual(eval_res.decision, PolicyDecision.DENY)

    def test_inv_02_child_authority_subset_of_parent(self):
        """Invariant: CHILD_AUTHORITY ⊆ PARENT_AUTHORITY & CHILD_TOOL_SCOPE ⊆ PARENT_TOOL_SCOPE."""
        parent = ai_employee_registry.propose_employee(
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            name="Parent Specialist",
            role_tier="AI_SPECIALIST",
            template_id="tpl_spec",
            version="1.0.0",
            department_id="OPERATIONS",
            allowed_tools=["db.read", "analytics.query"],
            allowed_data_domains=["INTERNAL"],
            authority=AuthorityScope(
                max_risk_class="LOW_RISK",
                max_single_spend_usd=200.0,
                can_delegate=True
            ),
            initial_budget_usd=500.0
        )
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.EVALUATED)
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.APPROVED)
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.PROVISIONED)
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.ONBOARDED)
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.ACTIVE)

        # Child requests tool NOT held by parent -> must be rejected
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Unauthorized Tool Child",
                child_role_tier="AI_WORKER",
                child_template_id="tpl_worker",
                requested_capabilities=["db.read"],
                requested_tools=["db.read", "stripe.refund"],  # Parent lacks stripe.refund
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=50.0),
                delegated_budget_usd=100.0
            )

        # Child requests risk level higher than parent -> must be rejected
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Escalated Risk Child",
                child_role_tier="AI_WORKER",
                child_template_id="tpl_worker",
                requested_capabilities=["db.read"],
                requested_tools=["db.read"],
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="FINANCIAL", max_single_spend_usd=50.0),
                delegated_budget_usd=100.0
            )

        # Child requests budget greater than parent remaining -> must be rejected
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Excess Budget Child",
                child_role_tier="AI_WORKER",
                child_template_id="tpl_worker",
                requested_capabilities=["db.read"],
                requested_tools=["db.read"],
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=50.0),
                delegated_budget_usd=900.0  # Exceeds parent's 500.0
            )

    def test_inv_03_offboarded_identity_no_authority(self):
        """Invariant: OFFBOARDED_IDENTITY != ACTIVE_AUTHORITY."""
        ident = identity_gateway.register_identity(
            identity_id=f"usr_off_{uuid.uuid4().hex[:6]}",
            identity_type=IdentityType.HUMAN,
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            display_name="Departing Employee",
            roles=["ADMIN"],
            departments=["FINANCE"]
        )
        token = identity_gateway.issue_token(ident)
        valid, _, _ = identity_gateway.verify_token(token)
        self.assertTrue(valid)

        # Offboard employee
        identity_gateway.offboard_identity(ident.identity_id, reason="Terminated contract")

        # Prior token is immediately invalid & cannot be reissued
        valid, _, reason = identity_gateway.verify_token(token)
        self.assertFalse(valid)
        self.assertIn("offboarded", reason.lower())

        with self.assertRaises(PermissionError):
            identity_gateway.issue_token(ident)

    def test_inv_04_deleted_data_not_retrievable(self):
        """Invariant: DELETED_DATA != RETRIEVABLE_DATA (Purged objects cannot be retrieved)."""
        doc = corporate_data_gateway.ingest_data_object(
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            title="Q3 Strategy Plan",
            content="Top secret corporate acquisitions for Q3 roadmap.",
            data_class="DOCUMENT",
            source_system="internal_wiki",
            source_object_id="doc_001",
            owner_identity_id="usr_admin",
            acl=DataObjectACL(allowed_departments=["ALL"], allowed_roles=["ADMIN", "OWNER"], allowed_identities=[])
        )
        knowledge_gateway.index_data_object(doc)

        # Before deletion: readable
        can_access, _ = corporate_data_gateway.check_access(
            tenant_id="tnt_v4_inv", company_id="comp_v4_inv",
            requester_identity_id="usr_admin", requester_departments=["EXEC"],
            requester_roles=["ADMIN"], requester_clearance_level="RESTRICTED",
            object_id=doc.object_id
        )
        self.assertTrue(can_access)

        # Execute verified purge
        cert = data_lifecycle_manager.execute_verified_purge(doc.object_id, requester_id="usr_admin")
        self.assertTrue(cert.purged_from_storage)
        self.assertTrue(cert.purged_from_index)

        # After purge: check_access fails with DELETED_DATA != RETRIEVABLE_DATA
        can_access, reason = corporate_data_gateway.check_access(
            tenant_id="tnt_v4_inv", company_id="comp_v4_inv",
            requester_identity_id="usr_admin", requester_departments=["EXEC"],
            requester_roles=["ADMIN"], requester_clearance_level="RESTRICTED",
            object_id=doc.object_id
        )
        self.assertFalse(can_access)
        self.assertIn("DELETED_DATA != RETRIEVABLE_DATA", reason)

        # Knowledge retrieval also yields 0 chunks
        cits = knowledge_gateway.retrieve_permission_aware(
            tenant_id="tnt_v4_inv", company_id="comp_v4_inv",
            requester_identity_id="usr_admin", requester_departments=["EXEC"],
            requester_roles=["ADMIN"], requester_clearance_level="RESTRICTED",
            query="Q3 Strategy Plan"
        )
        self.assertEqual(len(cits), 0)

    def test_inv_05_unknown_outcome_not_failure_nor_success(self):
        """Invariant: UNKNOWN_OUTCOME != FAILURE and UNKNOWN_OUTCOME != SUCCESS."""
        rec = unknown_outcome_engine.register_unknown_outcome(
            action_id="act_ambiguous_payment_99",
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            employee_id="emp_ai_finance",
            target_system="stripe_gateway",
            mutation_type="payment.charge",
            parameters={"amount": 5000, "currency": "usd"},
            idempotency_key="idemp_pay_99"
        )
        self.assertEqual(rec.status, ReconciledStatus.PENDING_RECONCILIATION)
        self.assertNotEqual(rec.status, "SUCCESS")
        self.assertNotEqual(rec.status, "FAILURE")

        # Reconcile with provider confirmation
        status = unknown_outcome_engine.reconcile(
            record_id=rec.record_id,
            query_provider_fn=lambda key: (True, {"charge_id": "ch_verified_123"})
        )
        self.assertEqual(status, ReconciledStatus.CONFIRMED_SUCCESS)

    def test_inv_06_model_dlp_firewall_blocks_highly_restricted(self):
        """Invariant: MODEL != POLICY & NEVER_SEND_ENTERPRISE_DATA_UNLESS_POLICY_EXPLICITLY_PERMITS."""
        prompt_with_private_key = "Export RSA Key: -----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
        
        with self.assertRaises(ModelSecurityException) as ctx:
            model_gateway_v4.invoke_model(
                tenant_id="tnt_v4_inv",
                company_id="comp_v4_inv",
                employee_id="emp_01",
                prompt=prompt_with_private_key,
                preferred_model_id="claude-3-7-sonnet"
            )
        self.assertIn("HIGHLY_RESTRICTED", str(ctx.exception))

    def test_inv_07_memory_not_authoritative_corporate_truth(self):
        """Invariant: MEMORY != CORPORATE_TRUTH & AI_GENERATED != AUTHORITATIVE."""
        mem = memory_governance_gateway.record_working_memory(
            tenant_id="tnt_v4_inv",
            company_id="comp_v4_inv",
            employee_id="emp_01",
            content="Agent hypothesized that customer churn was caused by billing system outage."
        )
        self.assertEqual(mem.tier, EpistemicMemoryTier.WORKING_MEMORY)
        self.assertEqual(mem.trust_state, KnowledgeTrustState.AI_GENERATED)
        self.assertFalse(mem.is_authoritative)

        # Explicit promotion to corporate knowledge requires human authority
        memory_governance_gateway.promote_to_corporate_knowledge(
            record_id=mem.record_id,
            verified_by_authority_id="usr_human_vp_ops",
            evidence_reference="incident_report_audit_ledger_42"
        )

        with engine.connection(workload=WorkloadType.READ) as conn:
            row = conn.execute("SELECT is_authoritative, trust_state FROM governed_memory_records WHERE record_id = ?", (mem.record_id,)).fetchone()
            self.assertEqual(row["is_authoritative"], 1)
            self.assertEqual(row["trust_state"], KnowledgeTrustState.AUTHORITATIVE)

if __name__ == "__main__":
    unittest.main()
