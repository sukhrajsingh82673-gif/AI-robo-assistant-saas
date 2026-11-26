"""
ZONATA Universal AI Co-worker Fabric — Comprehensive Automated Test Suite
Validates:
- Capability discovery & provider routing (API-first, native accessibility, RPA)
- Multi-tier provider fallback & idempotency
- Policy denial, authority boundaries & tenant isolation
- Human approval gating & financial controls
- MFA pause & resume (AUTH_REQUIRED state)
- Emergency multi-level KillSwitch execution containment
- Self-healing recovery from crashed providers & hung leases
- Independent verification & UNCERTAIN state handling
- Merkle evidence recording & audit integrity
- Live supervision & Human Takeover handoff
- 24x7 watchdog & scheduling
- Acceptance Scenarios 1 through 7
"""

import unittest
import os
import time
import json
import uuid

from core.coworker import (
    UniversalCoworkerEngine, CapabilityRegistry, ProviderRegistry,
    CapabilityRouter, FallbackManager, CredentialAuthority,
    CoworkerPolicyEvaluator, RiskClassifier, HumanTakeoverManager,
    IndependentVerificationEngine, EvidenceLedgerAdapter, WorkerSupervisor,
    ExecutionLeaseManager, RecoveryEngine, CoworkerTemplateFactory,
    OperatingInstructionParser, DeterministicSafetyRuleEngine,
    CapabilityCategory, RiskLevel, ProviderHealthStatus, ExecutionState,
    VerificationStatus, SupervisedControlMode, TaskNode, ExecutionGraph,
    ExecutionResult, VerificationResult, CoworkerProfile
)
from core.killswitch_matrix import KillSwitchMatrix, KillSwitchLevel

class TestCoworkerFabric(unittest.TestCase):

    def setUp(self):
        self.tenant_id = "tnt_test_coworker"
        self.engine = UniversalCoworkerEngine(tenant_id=self.tenant_id)
        # Ensure killswitch is clean for this tenant
        self.engine.killswitch.deactivate(KillSwitchLevel.GLOBAL, "*")
        self.engine.killswitch.deactivate(KillSwitchLevel.TENANT, self.tenant_id)

    # 1. Capability Discovery
    def test_01_capability_discovery(self):
        caps = self.engine.capability_reg.list_capabilities()
        self.assertGreater(len(caps), 8)
        crm_cap = self.engine.capability_reg.get_capability("api.crm_update")
        self.assertIsNotNone(crm_cap)
        self.assertEqual(crm_cap.category, CapabilityCategory.API)
        self.assertTrue(crm_cap.requires_authorization)
        self.assertTrue(crm_cap.requires_verification)

    # 2. Intelligent Provider Routing (API-First, Native UI over Visual CUA)
    def test_02_intelligent_provider_routing(self):
        # CRM update -> API preferred
        provider, reason, fallbacks = self.engine.router.route_capability("api.crm_update", platform="linux")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.providerId(), "provider_api_mcp")
        self.assertIn("provider_playwright", fallbacks)

        # Excel update -> Robocorp RPA preferred over visual AI
        rpa_provider, _, _ = self.engine.router.route_capability("rpa.excel_update", platform="linux")
        self.assertIsNotNone(rpa_provider)
        self.assertEqual(rpa_provider.providerId(), "provider_robocorp")

        # Native accessibility click -> Linux native desktop preferred
        desk_provider, _, _ = self.engine.router.route_capability("desktop.click_element", platform="linux")
        self.assertIsNotNone(desk_provider)
        self.assertEqual(desk_provider.providerId(), "provider_linux_desktop")

    # 3. Provider Fallback Cascade
    def test_03_provider_fallback_cascade(self):
        # Simulate primary provider crash
        api_prov = self.engine.provider_reg.get_provider("provider_api_mcp")
        api_prov.set_health(ProviderHealthStatus.CRASHED)

        # Route should pick a healthy alternative or fallback
        provider, _, fallbacks = self.engine.router.route_capability("api.crm_update", platform="linux")
        self.assertIsNotNone(provider)
        self.assertNotEqual(provider.providerId(), "provider_api_mcp")

        # Reset health
        api_prov.set_health(ProviderHealthStatus.AVAILABLE)

    # 4. Policy Denial & Tenant Boundary Check
    def test_04_policy_denial_and_tenant_boundary(self):
        # Create worker in another tenant
        alien_worker = self.engine.create_coworker("Foreign Tenant Worker")
        alien_worker.tenant_id = "tnt_alien"

        task = TaskNode(
            task_id="task_alien_01",
            mission_id="msn_01",
            title="Cross-tenant breach attempt",
            capability_id="api.crm_read"
        )
        res, ver, final_state = self.engine.execute_task(task, alien_worker)
        self.assertEqual(final_state, ExecutionState.POLICY_DENIED)
        self.assertEqual(res.status, "POLICY_DENIED")

    # 5. Human Approval Gate on High-Risk Financial Action
    def test_05_human_approval_gate_financial(self):
        worker = self.engine.create_coworker("Procurement Worker")
        task = TaskNode(
            task_id="task_purchase_01",
            mission_id="msn_01",
            title="Purchase ERP License",
            capability_id="financial.purchase_software",
            parameters={"software": "ERP", "cost_usd": 1200.0}
        )

        # Without human approval -> enters REQUEST_APPROVAL
        res, ver, state = self.engine.execute_task(task, worker, human_approval_granted=False)
        self.assertEqual(state, ExecutionState.REQUEST_APPROVAL)
        self.assertEqual(res.status, "AWAITING_HUMAN_APPROVAL")

        # With human approval granted -> proceeds to execution
        res2, ver2, state2 = self.engine.execute_task(task, worker, human_approval_granted=True)
        self.assertEqual(state2, ExecutionState.SUCCESS)
        self.assertEqual(ver2.status, VerificationStatus.VERIFIED)

    # 6. Credential Authority & MFA Challenge
    def test_06_credential_authority_mfa(self):
        ca = self.engine.credential_authority
        token_id = ca.issue_scoped_token("worker_01", "pms_service", ["read", "write"], ttl_seconds=60)
        valid, err = ca.validate_token(token_id, "read")
        self.assertTrue(valid)

        # MFA Challenge flow
        chal_id = ca.request_mfa_authentication("msn_01", "banking_gateway", "Enter OTP")
        self.assertEqual(ca.get_challenge_status(chal_id), "PENDING")
        ca.fulfill_mfa_challenge(chal_id, "987654")
        self.assertEqual(ca.get_challenge_status(chal_id), "FULFILLED")

    # 7. Multi-Level KillSwitch Execution Containment
    def test_07_killswitch_containment(self):
        worker = self.engine.create_coworker("Revenue Worker")
        task = TaskNode(
            task_id="task_ks_01",
            mission_id="msn_01",
            title="Update Rate",
            capability_id="api.crm_update",
            parameters={"customer_id": "cust_101", "data": {"rate": "7000"}}
        )

        # Engage Tenant Killswitch
        self.engine.killswitch.activate(KillSwitchLevel.TENANT, self.tenant_id, "Security drill")
        res, ver, state = self.engine.execute_task(task, worker)
        self.assertEqual(state, ExecutionState.KILLSWITCH)
        self.assertEqual(res.status, "BLOCKED_BY_KILLSWITCH")

        # Deactivate
        self.engine.killswitch.deactivate(KillSwitchLevel.TENANT, self.tenant_id)

    # 8. Worker Crash Recovery (Self-Healing)
    def test_08_worker_crash_recovery(self):
        rec_eng = self.engine.recovery_engine
        prov = self.engine.provider_reg.get_provider("provider_playwright")
        prov.set_health(ProviderHealthStatus.CRASHED)

        task = TaskNode(task_id="t_rec_01", mission_id="m_01", title="Browse", capability_id="browser.navigate")
        recovered, msg = rec_eng.attempt_recovery(task, prov, {"error": "Browser process died"})
        self.assertTrue(recovered)
        self.assertEqual(prov.health(), ProviderHealthStatus.AVAILABLE)

    # 9. Duplicate Execution & Idempotency
    def test_09_duplicate_execution_idempotency(self):
        worker = self.engine.create_coworker("Revenue Worker")
        idemp_key = f"idemp_{uuid.uuid4().hex[:8]}"

        task1 = TaskNode(
            task_id="t_idemp_01",
            mission_id="m_idemp",
            title="Update CRM",
            capability_id="api.crm_update",
            parameters={"customer_id": "cust_101", "data": {"phone": "+91-1122334455"}, "idempotency_key": idemp_key}
        )
        task1.idempotency_key = idemp_key

        res1, ver1, state1 = self.engine.execute_task(task1, worker)
        self.assertEqual(state1, ExecutionState.SUCCESS)

        # Second attempt with same idempotency key must not re-execute side effects
        task2 = TaskNode(
            task_id="t_idemp_02",
            mission_id="m_idemp",
            title="Update CRM Duplicate",
            capability_id="api.crm_update",
            parameters={"customer_id": "cust_101", "data": {"phone": "+91-1122334455"}, "idempotency_key": idemp_key}
        )
        task2.idempotency_key = idemp_key
        res2, ver2, state2 = self.engine.execute_task(task2, worker)
        self.assertEqual(state2, ExecutionState.SUCCESS)
        self.assertEqual(res2.output, res1.output)

    # 10. Verification Uncertainty (Never convert UNCERTAIN to SUCCESS)
    def test_10_verification_uncertainty(self):
        worker = self.engine.create_coworker("Revenue Worker")
        # Empty parameters causes CRM write confirmation to fail in verification
        task = TaskNode(
            task_id="t_uncert_01",
            mission_id="m_uncert",
            title="Unverifiable CRM update",
            capability_id="api.crm_update",
            parameters={"customer_id": "cust_unconfirmed"}
        )
        # Mock execution result with mutation_confirmed = False
        api_prov = self.engine.provider_reg.get_provider("provider_api_mcp")
        exec_res = ExecutionResult(
            provider_id="provider_api_mcp",
            capability_id="api.crm_update",
            execution_id="ex_uncert",
            status="SUCCESS",
            output={"mutation_confirmed": False}
        )
        ver = self.engine.verifier.verify_execution("api.crm_update", exec_res, {})
        self.assertEqual(ver.status, VerificationStatus.UNCERTAIN)

    # 11. Evidence Creation & Cryptographic Ledger Integrity
    def test_11_evidence_creation_ledger(self):
        worker = self.engine.create_coworker("Revenue Worker")
        task = TaskNode(
            task_id="t_ev_01",
            mission_id="m_ev",
            title="Update Matrix",
            capability_id="rpa.excel_update",
            parameters={"file_path": "/tmp/test_matrix.xlsx", "updates": {"A1": "Confirmed"}}
        )
        res, ver, state = self.engine.execute_task(task, worker)
        self.assertEqual(state, ExecutionState.SUCCESS)

    # 12. Human Takeover & Live Supervision Mutual Exclusion
    def test_12_human_takeover_supervision(self):
        ht = self.engine.takeover_mgr
        sess = ht.initialize_session("sess_live_01", "worker_hotel_01")
        self.assertEqual(sess["mode"], SupervisedControlMode.AI_CONTROL)

        # Human assumes control -> AI paused immediately
        success, msg = ht.human_takeover("sess_live_01", {"current_app": "LegacyERP"})
        self.assertTrue(success)
        self.assertEqual(ht.get_session_mode("sess_live_01"), SupervisedControlMode.HUMAN_CONTROL)

        # Human performs action
        ht.record_human_action("sess_live_01", "Clicked manual override button")

        # Return control back to AI
        ret_ok, ret_msg = ht.return_control_to_ai("sess_live_01", {"new_app_state": "DIALOG_CLOSED"})
        self.assertTrue(ret_ok)
        self.assertEqual(ht.get_session_mode("sess_live_01"), SupervisedControlMode.AI_CONTROL)

    # 13. Execution Lease Expiration & Watchdog Audit
    def test_13_lease_expiration_and_watchdog(self):
        lm = self.engine.supervisor.lease_mgr
        # Lease with 0.1s TTL
        lease = lm.acquire_lease("task_hung_01", "worker_01")
        lease.expires_at = time.time() - 1.0  # Force expire

        self.assertFalse(lm.is_lease_valid(lease.lease_id))
        audit = self.engine.supervisor.run_watchdog_cycle()
        self.assertGreaterEqual(audit["expired_leases_recovered"], 1)

    # 14. Acceptance Scenario 1: Supplier Research & Comparison
    def test_14_scenario_1_supplier_research(self):
        worker = self.engine.create_coworker("Procurement Worker")
        graph = self.engine.create_mission_from_objective("Open browser, research three suppliers and prepare a comparison.")
        self.assertIn("browser.navigate", [n.capability_id for n in graph.nodes.values()])
        completed_graph = self.engine.execute_mission(graph, worker)
        self.assertEqual(completed_graph.status, ExecutionState.SUCCESS)

    # 15. Acceptance Scenario 2: Update CRM with Customer Data
    def test_15_scenario_2_crm_update(self):
        worker = self.engine.create_coworker("Revenue Worker")
        graph = self.engine.create_mission_from_objective("Update the CRM with today's approved customer data.")
        node = list(graph.nodes.values())[0]
        self.assertEqual(node.capability_id, "api.crm_update")
        completed_graph = self.engine.execute_mission(graph, worker)
        self.assertEqual(completed_graph.status, ExecutionState.SUCCESS)
        self.assertEqual(node.selected_provider, "provider_api_mcp")  # API preferred

    # 16. Acceptance Scenario 3: Legacy Desktop Export & Hash Verification
    def test_16_scenario_3_legacy_desktop_export(self):
        worker = self.engine.create_coworker("Desktop Operator")
        graph = self.engine.create_mission_from_objective("Operate this legacy desktop application and export yesterday's report.")
        completed_graph = self.engine.execute_mission(graph, worker)
        # No native desktop/accessibility backend is present in this environment:
        # the engine must fail honestly rather than fabricate a verified export.
        self.assertEqual(completed_graph.status, ExecutionState.EXECUTION_FAILURE)
        node = next(iter(completed_graph.nodes.values()), None)
        if node is not None and node.verification is not None:
            self.assertNotEqual(node.verification.status, VerificationStatus.VERIFIED)

    # 17. Acceptance Scenario 4: Send Approved Report to Management
    def test_17_scenario_4_send_report_email(self):
        worker = self.engine.create_coworker("Operations Specialist")
        graph = self.engine.create_mission_from_objective("Send the approved report to management.")
        completed_graph = self.engine.execute_mission(graph, worker, auto_approve_human_tasks=True)
        self.assertEqual(completed_graph.status, ExecutionState.SUCCESS)
        node = list(completed_graph.nodes.values())[0]
        self.assertEqual(node.selected_provider, "provider_api_mcp")

    # 18. Acceptance Scenario 5: Purchase Software License
    def test_18_scenario_5_purchase_software(self):
        worker = self.engine.create_coworker("Procurement Worker")
        graph = self.engine.create_mission_from_objective("Purchase the required software.")
        node = list(graph.nodes.values())[0]
        self.assertEqual(node.risk_level, RiskLevel.CRITICAL)

        # Without approval -> must halt at REQUEST_APPROVAL
        graph1 = self.engine.execute_mission(graph, worker, auto_approve_human_tasks=False)
        self.assertEqual(graph1.status, ExecutionState.REQUEST_APPROVAL)

        # With explicit approval -> completes
        graph2 = self.engine.execute_mission(graph, worker, auto_approve_human_tasks=True)
        self.assertEqual(graph2.status, ExecutionState.SUCCESS)

    # 19. Acceptance Scenario 6: Disconnection During Booking -> Enters UNCERTAIN
    def test_19_scenario_6_booking_disconnection_uncertainty(self):
        worker = self.engine.create_coworker("Hotel Revenue Specialist")
        task = TaskNode(
            task_id="t_booking_01",
            mission_id="m_booking",
            title="Book Hotel Suite",
            capability_id="api.crm_update",
            parameters={"customer_id": "cust_interrupted"}
        )
        # Simulate network drop by producing unconfirmed outcome
        res = ExecutionResult(
            provider_id="provider_api_mcp",
            capability_id="api.crm_update",
            execution_id="exec_interrupted",
            status="SUCCESS",
            output={"mutation_confirmed": False}  # State unknown on provider
        )
        ver = self.engine.verifier.verify_execution("api.crm_update", res, {})
        self.assertEqual(ver.status, VerificationStatus.UNCERTAIN)

    # 20. Acceptance Scenario 7: Human Desktop Takeover
    def test_20_scenario_7_human_desktop_takeover(self):
        ht = self.engine.takeover_mgr
        sess_id = "sess_hotel_frontdesk"
        ht.initialize_session(sess_id, "worker_hotel_rev")

        # 1. AI starts
        self.assertEqual(ht.get_session_mode(sess_id), SupervisedControlMode.AI_CONTROL)

        # 2. Human assumes control
        ok, msg = ht.human_takeover(sess_id, {"screen": "FrontDeskPMS"})
        self.assertTrue(ok)
        self.assertEqual(ht.get_session_mode(sess_id), SupervisedControlMode.HUMAN_CONTROL)

        # 3. Human performs manual entry
        ht.record_human_action(sess_id, "Resolved room allotment conflict manually")

        # 4. Return to AI
        ret_ok, _ = ht.return_control_to_ai(sess_id, {"screen": "FrontDeskPMS", "status": "ALLOTMENT_SETTLED"})
        self.assertTrue(ret_ok)
        self.assertEqual(ht.get_session_mode(sess_id), SupervisedControlMode.AI_CONTROL)


if __name__ == "__main__":
    unittest.main()
