"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V4 Test Suite — Policy Engine ABAC, Model Gateway, DLP Firewall, & Causal Lineage
"""

import unittest
import uuid
from core.policy_engine_v2 import policy_engine_v2, PolicyContext, PolicyDecision
from core.model_data_firewall import model_data_firewall, ModelDataFirewall
from core.model_gateway_v4 import model_gateway_v4, ModelResponse
from core.data_lineage_graph import data_lineage_graph

class TestV4PolicyLineageAndDLP(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_pol_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_pol_{uuid.uuid4().hex[:6]}"

    def test_abac_policy_engine_evaluation(self):
        """Test multi-dimensional ABAC evaluation across WHO, WHAT, WHY, DATA, TOOL, RISK."""
        # 1. Low-risk query by authorized analyst -> Must be ALLOW
        ctx_permit = PolicyContext(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            requester_id="emp_analyst_01",
            requester_type="AI_EMPLOYEE",
            requester_roles=["ANALYST"],
            requester_departments=["FINANCE"],
            action="GENERATE_REPORT",
            intent="Weekly performance summary",
            mission_id="miss_123",
            data_classification="INTERNAL",
            tool_risk_class="LOW_RISK",
            requested_spend_usd=0.05,
            employee_remaining_budget_usd=100.0
        )
        res_permit = policy_engine_v2.evaluate(ctx_permit)
        self.assertEqual(res_permit.decision, PolicyDecision.ALLOW)

        # 2. Destructive operation -> Must be REQUIRE_APPROVAL
        ctx_destructive = PolicyContext(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            requester_id="emp_analyst_01",
            requester_type="AI_EMPLOYEE",
            requester_roles=["ANALYST"],
            requester_departments=["FINANCE"],
            action="DELETE_ALL_TABLES",
            intent="Maintenance",
            mission_id="miss_123",
            data_classification="RESTRICTED",
            tool_risk_class="DESTRUCTIVE",
            requested_spend_usd=0.0,
            employee_remaining_budget_usd=100.0
        )
        res_destructive = policy_engine_v2.evaluate(ctx_destructive)
        self.assertEqual(res_destructive.decision, PolicyDecision.REQUIRE_APPROVAL)

        # 3. High spend (>= $5000) -> Must be ESCALATE
        ctx_escalate = PolicyContext(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            requester_id="emp_analyst_01",
            requester_type="AI_EMPLOYEE",
            requester_roles=["ANALYST"],
            requester_departments=["FINANCE"],
            action="PURCHASE_EQUIPMENT",
            intent="Server procurement",
            mission_id="miss_123",
            data_classification="INTERNAL",
            tool_risk_class="LOW_RISK",
            requested_spend_usd=6000.0,
            employee_remaining_budget_usd=10000.0
        )
        res_escalate = policy_engine_v2.evaluate(ctx_escalate)
        self.assertEqual(res_escalate.decision, PolicyDecision.ESCALATE)

    def test_dlp_firewall_blocks_highly_restricted_to_external_models(self):
        """Test DLP firewall forbids transmission of highly restricted keys/certs to cloud providers."""
        # RSA Private key leaked into prompt
        leak_prompt = "Here is our secret configuration: -----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
        
        result = model_data_firewall.inspect_and_filter(
            raw_prompt=leak_prompt,
            tenant_id=self.tenant_id,
            provider_name="OPENAI",
            is_sovereign_local_model=False
        )
        self.assertFalse(result.is_allowed)
        self.assertIn("HIGHLY_RESTRICTED", result.blocking_reason)

        # Redaction of SSN in prompt
        ssn_prompt = "Customer Social Security Number is 987-65-4321 for loan application."
        redact_res = model_data_firewall.inspect_and_filter(
            raw_prompt=ssn_prompt,
            tenant_id=self.tenant_id,
            provider_name="ANTHROPIC",
            is_sovereign_local_model=False
        )
        self.assertTrue(redact_res.is_allowed)
        self.assertIn("[REDACTED_SSN]", redact_res.sanitized_prompt)
        self.assertNotIn("987-65-4321", redact_res.sanitized_prompt)

    def test_model_gateway_routing_and_budget_deduction(self):
        """Test Model Gateway completes prompt routing and tracks token spend."""
        resp = model_gateway_v4.invoke_model(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            employee_id="emp_test_worker",
            prompt="Analyze the quarterly trends and summarize key drivers in 3 bullets.",
            preferred_model_id="claude-3-7-sonnet",
            max_tokens=200
        )
        self.assertIsNotNone(resp.content)
        self.assertGreater(resp.prompt_tokens + resp.completion_tokens, 0)
        self.assertGreaterEqual(resp.total_cost_usd, 0.0)

    def test_data_lineage_graph_provenance_trace(self):
        """Test recording causal steps and querying upstream provenance trail."""
        mission_id = f"miss_{uuid.uuid4().hex[:8]}"
        action_id = f"act_{uuid.uuid4().hex[:8]}"

        # Record step: mission initiated action
        data_lineage_graph.record_step(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            source_id=mission_id,
            source_type="MISSION",
            source_label="Quarterly Payroll Audit",
            target_id=action_id,
            target_type="TOOL_ACTION",
            target_label="Sync Nango Records",
            relationship="INVOKED_TOOL",
            metadata={"tool": "sync_nango_records", "status": "SUCCESS"}
        )

        # Trace provenance
        trail = data_lineage_graph.get_provenance_trail(action_id)
        self.assertEqual(len(trail), 1)
        self.assertEqual(trail[0]["source_id"], mission_id)
        self.assertEqual(trail[0]["relationship"], "INVOKED_TOOL")

if __name__ == "__main__":
    unittest.main()
