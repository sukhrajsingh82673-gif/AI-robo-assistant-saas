"""
RoboAssistant Company OS 2.0 — Adversarial Governance & Security Invariants Test Suite
Validates constitutional security invariants:
1. Capability != Authority
2. Credential Isolation (Opaque handles only)
3. MFA Human-in-the-Loop integrity (No security bypass)
4. Sandbox filesystem boundary containment
5. Performance evaluation cannot expand authority
"""

import unittest
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.models import ActionContract, AuthorityLevel, HostType
from core.host_fabric import UniversalHostAgent
from core.desktop_robot import UniversalDesktopRobot
from core.credential_broker import CredentialBroker, CredentialStatus
from core.session_broker import SessionBroker, SessionStatus
from core.workforce_intelligence import WorkforceIntelligenceEngine
from core.employee_performance import EmployeePerformanceEngine

class TestAdversarialSecurity(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_sec_{int(time.time()*1000)}"
        self.company_id = "comp_security_test"
        self.host_agent = UniversalHostAgent(tenant_id=self.tenant_id)
        self.robot = UniversalDesktopRobot(self.host_agent)

    def test_credential_isolation_and_no_raw_secrets(self):
        broker = CredentialBroker(tenant_id=self.tenant_id, company_id=self.company_id)
        raw_api_key = "sk_live_very_secret_enterprise_token_999"

        # Register secret
        handle_id = broker.register_credential(
            service_name="Stripe_Gateway",
            account_label="Production Billing",
            secret_value=raw_api_key,
            auth_type="API_KEY",
            mfa_required=False
        )

        self.assertTrue(handle_id.startswith("cred_stripe_gateway_"))

        # Verify listing handles NEVER exposes the raw secret
        handles = broker.list_handles()
        matching = next((h for h in handles if h["handle_id"] == handle_id), None)
        self.assertIsNotNone(matching)
        self.assertNotIn("secret_value", matching)
        self.assertNotIn(raw_api_key, str(matching))

    def test_mfa_interaction_no_bypass(self):
        broker = CredentialBroker(tenant_id=self.tenant_id, company_id=self.company_id)
        sess_broker = SessionBroker(tenant_id=self.tenant_id, company_id=self.company_id)

        handle_id = broker.register_credential(
            service_name="Corporate_Banking",
            account_label="Executive Account",
            secret_value="TreasuryPassword123",
            auth_type="PASSWORD",
            mfa_required=True
        )

        # Attempt to create session -> MUST enter WAITING_FOR_OWNER
        sess_res = sess_broker.create_session(handle_id, host_id=self.host_agent.host_id)
        self.assertTrue(sess_res["success"])
        self.assertEqual(sess_res["status"], SessionStatus.WAITING_FOR_OWNER)
        self.assertTrue(sess_res["requires_owner_intervention"])

        # Cannot be used in active sessions until owner verifies MFA
        active = sess_broker.list_active_sessions()
        self.assertFalse(any(s["session_id"] == sess_res["session_id"] for s in active))

        # Owner explicitly completes MFA
        sess_broker.verify_and_complete_mfa(sess_res["session_id"])
        active_now = sess_broker.list_active_sessions()
        self.assertTrue(any(s["session_id"] == sess_res["session_id"] for s in active_now))

    def test_sandbox_containment_blocks_host_escape(self):
        # Attempt to write to system directory outside sandbox
        escape_contract = ActionContract(
            action_id="act_escape_01",
            mission_id="mis_hack",
            agent_id="agt_malicious",
            capability="file_write",
            target="/etc/malicious_cron.sh",
            host=HostType.LINUX_CLOUD,
            scope="ROOT",
            permissions_required=AuthorityLevel.AUTOMATIC_IDEMPOTENT,
            resources_locked=[],
            expected_outcome="Overwrite root configuration",
            verification_requirements=[]
        )

        res = self.robot.execute_action(escape_contract, {"content": "rm -rf /"})
        self.assertFalse(res["success"])
        self.assertIn("Policy Violation", res["error"])
        self.assertFalse(res["verified"])

    def test_performance_does_not_expand_authority(self):
        wf = WorkforceIntelligenceEngine(tenant_id=self.tenant_id, company_id=self.company_id)
        employee = wf.create_specialized_employee("Autonomous Desktop Operator")
        self.assertEqual(employee.spending_limit, 100.0)

        perf = EmployeePerformanceEngine(tenant_id=self.tenant_id, company_id=self.company_id)

        # Record 10 consecutive verified perfect successes
        for _ in range(10):
            perf.record_mission_outcome(
                agent_id=employee.agent_id,
                verified_success=True,
                cost_incurred=10.0,
                business_contribution=500.0
            )

        summary = perf.get_performance_summary(employee.agent_id)
        self.assertEqual(summary["verification_rate"], 1.0)
        self.assertEqual(summary["recommendation"], "CONTINUE_DEPLOYMENT")

        # Invariant: Contract spending limit MUST remain strictly bounded at ₹100.0
        # Performance engine CANNOT silently elevate authority ceiling!
        self.assertEqual(employee.spending_limit, 100.0)

if __name__ == "__main__":
    unittest.main()
