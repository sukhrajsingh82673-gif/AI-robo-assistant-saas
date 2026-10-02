"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V5 Test Suite — Enterprise Reality, Service Identity, Deletion Proof, & Anti-Laundering
"""

import unittest
import uuid
import time
from core.enterprise_idp_client import enterprise_idp_client
from core.service_identity import service_identity_gateway, ServiceSecurityViolation
from core.approval_binder import approval_binder, ApprovalLaunderingError
from core.deletion_verifier import deletion_verifier
from core.corporate_data_plane import corporate_data_gateway
from core.data_lifecycle_manager import data_lifecycle_manager

class TestV5EnterpriseReality(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_v5_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_v5_{uuid.uuid4().hex[:6]}"

    def test_scim_lifecycle_and_measured_revocation_latency(self):
        """
        Test SCIM 2.0 provisioning, role synchronization, and measured revocation latency.
        Critical Test: Disabled user loses ZONATA authority within configured SLO (<100ms).
        """
        # 1. SCIM Provision user
        user = enterprise_idp_client.provision_user(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            username="john.doe@enterprise.corp",
            display_name="John Doe",
            email="john.doe@enterprise.corp",
            department="FINANCE",
            groups=["Employees", "Finance-Managers"],
            roles=["MANAGER"]
        )
        self.assertTrue(user.scim_id.startswith("scim_usr_"))

        # 2. SCIM Role update / sync
        synced = enterprise_idp_client.sync_group_and_roles(
            scim_id=user.scim_id,
            new_groups=["Employees", "Finance-Directors"],
            new_roles=["DIRECTOR"],
            new_department="FINANCE"
        )
        self.assertTrue(synced)

        # 3. Offboard / Deactivate user and measure revocation latency
        report = enterprise_idp_client.deactivate_user_with_latency_measurement(
            scim_id=user.scim_id,
            reason="Employee Departed"
        )
        self.assertTrue(report["is_revoked"])
        self.assertTrue(report["is_offboarded_in_db"])
        # Revocation latency must be well below enterprise 100ms SLO
        self.assertLess(report["revocation_latency_ms"], 100.0)
        print(f"\n[MEASURED REVOCATION LATENCY] {report['revocation_latency_ms']:.3f} ms")

    def test_enterprise_service_identity_and_rejection_vectors(self):
        """
        Test M2M Service Identity verification:
        Must strictly reject expired, wrong audience, wrong tenant, revoked, and replayed credentials.
        """
        svc_token = service_identity_gateway.issue_service_token(
            service_id="svc_api_worker_01",
            service_name="api_worker",
            target_audience="zonata:storage",
            tenant_id=self.tenant_id,
            allowed_actions=["READ_BLOB", "WRITE_BLOB"],
            ttl_seconds=10
        )

        # 1. Valid service token verification
        claims = service_identity_gateway.verify_service_token(
            token_str=svc_token,
            expected_audience="zonata:storage",
            expected_tenant_id=self.tenant_id,
            required_action="READ_BLOB"
        )
        self.assertEqual(claims.sub, "svc_api_worker_01")

        # 2. Replay attack rejection: Using the same token again fails because JTI was consumed
        with self.assertRaises(ServiceSecurityViolation):
            service_identity_gateway.verify_service_token(
                token_str=svc_token,
                expected_audience="zonata:storage",
                expected_tenant_id=self.tenant_id,
                required_action="READ_BLOB"
            )

        # 3. Wrong audience rejection
        fresh_token = service_identity_gateway.issue_service_token(
            service_id="svc_api_worker_02",
            service_name="api_worker",
            target_audience="zonata:database",
            tenant_id=self.tenant_id,
            allowed_actions=["QUERY"]
        )
        with self.assertRaises(ServiceSecurityViolation):
            service_identity_gateway.verify_service_token(
                token_str=fresh_token,
                expected_audience="zonata:storage", # Wrong target
                expected_tenant_id=self.tenant_id
            )

        # 4. Wrong tenant rejection
        with self.assertRaises(ServiceSecurityViolation):
            service_identity_gateway.verify_service_token(
                token_str=fresh_token,
                expected_audience="zonata:database",
                expected_tenant_id="tnt_foreign_tenant" # Wrong tenant boundary
            )

        # 5. Revoked service rejection
        revoked_svc_token = service_identity_gateway.issue_service_token(
            service_id="svc_compromised_01",
            service_name="compromised_worker",
            target_audience="zonata:database",
            tenant_id=self.tenant_id,
            allowed_actions=["QUERY"]
        )
        service_identity_gateway.revoke_service_identity("svc_compromised_01", "Security Incident", "ciso_admin")
        with self.assertRaises(ServiceSecurityViolation):
            service_identity_gateway.verify_service_token(
                token_str=revoked_svc_token,
                expected_audience="zonata:database",
                expected_tenant_id=self.tenant_id
            )

    def test_human_approval_anti_laundering_binding(self):
        """
        Verify that human approval cryptographically binds to parameters.
        Modifying action parameters after approval raises ApprovalLaunderingError.
        """
        approved_params = {"vendor_id": "vend_123", "amount_usd": 450.0, "invoice_id": "inv_998"}
        
        cert = approval_binder.create_bound_approval(
            tenant_id=self.tenant_id,
            employee_id="emp_buyer_01",
            mission_id="miss_procure_01",
            action_type="DISBURSE_PAYMENT",
            target_id="sys_accounts_payable",
            risk_class="FINANCIAL",
            parameters=approved_params,
            approver_identity_id="exec_cfo_01",
            approver_role="CFO"
        )
        self.assertTrue(cert.approval_id.startswith("appr_"))

        # Valid action matching approved parameters
        verified = approval_binder.verify_action_against_approval(
            certificate=cert,
            tenant_id=self.tenant_id,
            employee_id="emp_buyer_01",
            mission_id="miss_procure_01",
            action_type="DISBURSE_PAYMENT",
            target_id="sys_accounts_payable",
            execution_parameters=approved_params
        )
        self.assertTrue(verified)

        # Approval Laundering Attack: Attacker alters amount_usd to 45000.0
        tampered_params = {"vendor_id": "vend_123", "amount_usd": 45000.0, "invoice_id": "inv_998"}
        with self.assertRaises(ApprovalLaunderingError):
            approval_binder.verify_action_against_approval(
                certificate=cert,
                tenant_id=self.tenant_id,
                employee_id="emp_buyer_01",
                mission_id="miss_procure_01",
                action_type="DISBURSE_PAYMENT",
                target_id="sys_accounts_payable",
                execution_parameters=tampered_params
            )

    def test_multi_layer_deletion_verification(self):
        """
        Test multi-layer deletion proof across:
        Relational DB, Knowledge index, Distributed cache, and Scratch space.
        """
        doc = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Q3 Interim Strategy",
            content="Sensitive strategy notes to be purged after quarterly review.",
            data_class="STRATEGY"
        )

        # Execute verified purge
        data_lifecycle_manager.execute_verified_purge(doc.object_id, requester_id="legal_compliance")

        # Multi-layer audit verification
        report = deletion_verifier.verify_object_deletion(
            object_id=doc.object_id,
            tenant_id=self.tenant_id
        )
        self.assertTrue(report.logical_deletion_verified)
        self.assertTrue(report.cryptographic_erasure_verified)
        self.assertTrue(report.physical_index_purged)
        self.assertTrue(report.cache_evicted)
        self.assertTrue(report.scratch_files_unlinked)
        self.assertTrue(report.immutable_audit_preserved)
        self.assertEqual(report.status, "VERIFIED_DELETED")

    def test_legal_hold_blocks_destruction_and_release_permits(self):
        """
        Enterprise Test: Active legal hold strictly blocks cryptographic deletion.
        Removing legal hold permits deletion according to retention governance.
        """
        from core.data_lifecycle_manager import LegalHoldViolationError

        doc = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Litigation Hold Evidence Doc",
            content="Confidential subpoena documents under active federal investigation.",
            data_class="LEGAL"
        )

        # 1. Apply Legal Hold
        applied = data_lifecycle_manager.set_legal_hold(
            object_id=doc.object_id,
            hold_status=True,
            hold_reason="DOJ Inquiry 2026-X",
            authority_id="gen_counsel_01"
        )
        self.assertTrue(applied)

        # 2. Attempt Purge -> Must be strictly blocked
        with self.assertRaises(LegalHoldViolationError):
            data_lifecycle_manager.execute_verified_purge(doc.object_id, requester_id="ops_admin")

        # 3. Release Legal Hold
        released = data_lifecycle_manager.set_legal_hold(
            object_id=doc.object_id,
            hold_status=False,
            hold_reason="Inquiry Concluded",
            authority_id="gen_counsel_01"
        )
        self.assertTrue(released)

        # 4. Attempt Purge Again -> Permitted
        cert = data_lifecycle_manager.execute_verified_purge(doc.object_id, requester_id="ops_admin")
        self.assertTrue(cert.purged_from_storage)
        self.assertTrue(cert.purged_from_index)

    def test_cross_department_delegation_containment(self):
        """
        Adversarial Workforce Test: Finance parent delegates to child worker.
        Child attempts to acquire HR data scope, prohibited tool, or excessive budget.
        Must raise DelegationViolationError (CHILD ⊆ PARENT).
        """
        from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState, AuthorityScope
        from core.workforce_manager_v4 import workforce_manager_v4, DelegationViolationError

        # Create active parent employee in Finance
        parent = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Finance Lead AI",
            role_tier="AI_SPECIALIST",
            template_id="tmpl_fin_ctrl",
            version="1.0.0",
            department_id="FINANCE",
            capabilities=["FINANCIAL_ANALYSIS", "BUDGET_PLANNING"],
            allowed_tools=["db_query", "excel_calc", "generate_report"],
            allowed_data_domains=["FINANCE", "GENERAL"],
            authority=AuthorityScope(
                max_risk_class="MUTATING",
                max_single_spend_usd=500.0,
                can_delegate=True,
                can_access_restricted_data=True
            ),
            initial_budget_usd=1000.0
        )
        # Advance to ACTIVE
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.EVALUATED, "eval_bot", "Benchmark passed")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.APPROVED, "cfo_user", "Executive signoff")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.PROVISIONED, "sys_admin", "Sandbox ready")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.ONBOARDED, "idp_sync", "SCIM ready")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.ACTIVE, "ops_mgr", "Go live")

        # 1. Attack Vector: Child requests HR restricted data domain (not in parent scope)
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Unauthorized HR Snooper",
                child_role_tier="JUNIOR",
                child_template_id="tmpl_worker",
                requested_capabilities=["FINANCIAL_ANALYSIS"],
                requested_tools=["db_query"],
                requested_data_domains=["FINANCE", "HR_RESTRICTED"], # Breach
                requested_authority=parent.authority,
                delegated_budget_usd=100.0
            )

        # 2. Attack Vector: Child requests tool 'shell_exec' not granted to parent
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Unauthorized Tool Escalator",
                child_role_tier="JUNIOR",
                child_template_id="tmpl_worker",
                requested_capabilities=["FINANCIAL_ANALYSIS"],
                requested_tools=["db_query", "shell_exec"], # Breach
                requested_data_domains=["FINANCE"],
                requested_authority=parent.authority,
                delegated_budget_usd=100.0
            )

        # 3. Attack Vector: Child requests budget > parent remaining budget
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Budget Exhaustion Worker",
                child_role_tier="JUNIOR",
                child_template_id="tmpl_worker",
                requested_capabilities=["FINANCIAL_ANALYSIS"],
                requested_tools=["db_query"],
                requested_data_domains=["FINANCE"],
                requested_authority=parent.authority,
                delegated_budget_usd=2500.0 # Exceeds parent's $1,000 budget
            )

    def test_controlled_tenant_export_and_offboarding_sequence(self):
        """
        Enterprise Test: Controlled tenant data export and formal 9-step offboarding sequence.
        Verifies all data objects are purged and verified with zero remnants.
        """
        from core.identity_gateway import identity_gateway, IdentityType
        from core.enterprise_admin_gateway import enterprise_admin_gateway

        # Issue OWNER token for admin operations
        admin_identity = identity_gateway.register_identity(
            identity_id=f"usr_owner_{uuid.uuid4().hex[:6]}",
            identity_type=IdentityType.HUMAN,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            display_name="Enterprise Owner",
            roles=["OWNER", "ADMIN"],
            departments=["EXECUTIVE"]
        )
        admin_token = identity_gateway.issue_token(admin_identity)

        # Ingest tenant data
        doc = corporate_data_gateway.ingest_data_object(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            title="Tenant Proprietary Blueprint",
            content="Sensitive architectural drawings for customer deployment.",
            data_class="ENGINEERING"
        )

        # 1. Controlled tenant export
        export = enterprise_admin_gateway.export_tenant_data(admin_token, self.tenant_id)
        self.assertEqual(export["tenant_id"], self.tenant_id)
        self.assertEqual(len(export["corporate_data_objects"]), 1)
        self.assertEqual(export["corporate_data_objects"][0]["object_id"], doc.object_id)

        # 2. Formal 9-step tenant offboarding
        offboarding_result = enterprise_admin_gateway.execute_tenant_offboarding(
            admin_token=admin_token,
            target_tenant_id=self.tenant_id,
            reason="Customer contract completed"
        )
        self.assertEqual(offboarding_result["status"], "OFFBOARDED")
        self.assertEqual(len(offboarding_result["steps_completed"]), 9)
        self.assertIn("STOP_ACTIVE_MISSIONS", offboarding_result["steps_completed"])
        self.assertIn("STOP_AI_EMPLOYEES", offboarding_result["steps_completed"])
        self.assertIn("REVOKE_IDENTITIES", offboarding_result["steps_completed"])
        self.assertIn("PURGE_DATA", offboarding_result["steps_completed"])
        self.assertIn("VERIFY_DELETION", offboarding_result["steps_completed"])
        self.assertIn("CLOSE_TENANT", offboarding_result["steps_completed"])
        self.assertGreaterEqual(offboarding_result["verified_purges"], 1)

    def test_unknown_outcome_reconciliation_protocol(self):
        """
        Enterprise Test: Ambiguous mutation produces UNKNOWN_OUTCOME.
        Blind retries are prohibited; deterministic reconciliation confirms outcome.
        """
        from core.unknown_outcome_engine import unknown_outcome_engine, ReconciledStatus

        action_id = f"act_wire_{uuid.uuid4().hex[:8]}"
        record = unknown_outcome_engine.register_unknown_outcome(
            action_id=action_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            employee_id="emp_cfo_bot",
            target_system="FedwireGateway",
            mutation_type="DISBURSE_FUNDS",
            parameters={"amount_usd": 15000.0, "recipient_account": "ACT-9921"},
            idempotency_key=f"idem_wire_{uuid.uuid4().hex[:8]}"
        )
        self.assertEqual(record.status, ReconciledStatus.PENDING_RECONCILIATION)

        # Deterministic reconciliation confirms success on external confirmation
        reconciled_status = unknown_outcome_engine.reconcile(
            record_id=record.record_id,
            query_provider_fn=lambda idemp: (True, {"bank_tx_id": "TX-1092837", "cleared": True})
        )
        self.assertEqual(reconciled_status, ReconciledStatus.CONFIRMED_SUCCESS)

if __name__ == "__main__":
    unittest.main()

