"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V6 Test Suite — Autonomy Governor, Model Router V6, & Sanitized Diagnostics
"""

import unittest
import uuid
from core.autonomy_governor import autonomy_governor, AutonomyLevel, AutonomyViolationError
from core.model_router_v6 import model_router_v6
from core.diagnostics_bundle import diagnostics_generator

class TestV6GovernanceAndAutonomy(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_v6_gov_{uuid.uuid4().hex[:6]}"
        self.emp_parent = f"emp_parent_{uuid.uuid4().hex[:6]}"
        self.emp_child = f"emp_child_{uuid.uuid4().hex[:6]}"

    def test_autonomy_governor_level_containment_and_delegation(self):
        """
        Verify that AutonomyGovernor prohibits mutating actions for Level 1/2,
        and enforces CHILD_AUTONOMY_LEVEL <= PARENT_AUTONOMY_LEVEL.
        """
        # Set Parent to Level 3 (Approved Workflows)
        autonomy_governor.set_employee_autonomy(
            employee_id=self.emp_parent,
            tenant_id=self.tenant_id,
            assigned_level=AutonomyLevel.LEVEL_3_APPROVED_WORKFLOW,
            max_permitted=AutonomyLevel.LEVEL_4_AUTONOMOUS_MISSION,
            authorizer_id="cfo_user"
        )

        # Set Child to Level 2 (Reversible only)
        autonomy_governor.set_employee_autonomy(
            employee_id=self.emp_child,
            tenant_id=self.tenant_id,
            assigned_level=AutonomyLevel.LEVEL_2_REVERSIBLE,
            max_permitted=AutonomyLevel.LEVEL_3_APPROVED_WORKFLOW,
            authorizer_id="cfo_user"
        )

        # Level 2 Child can execute non-mutating search
        self.assertTrue(
            autonomy_governor.verify_action_autonomy(
                employee_id=self.emp_child,
                action_type="SEARCH_DOCUMENTS",
                is_mutating=False,
                spend_usd=0.0
            )
        )

        # Level 2 Child attempts mutating wire disbursement -> AutonomyViolationError
        with self.assertRaises(AutonomyViolationError):
            autonomy_governor.verify_action_autonomy(
                employee_id=self.emp_child,
                action_type="DISBURSE_PAYMENT",
                is_mutating=True,
                spend_usd=50.0
            )

        # Delegation Invariant: Parent (Level 3) attempts to spawn Level 4 child -> Violation
        with self.assertRaises(AutonomyViolationError):
            autonomy_governor.verify_delegation_autonomy(
                parent_employee_id=self.emp_parent,
                requested_child_level=AutonomyLevel.LEVEL_4_AUTONOMOUS_MISSION
            )

    def test_model_router_v6_sovereign_enforcement(self):
        """
        Verify that ModelRouterV6 forces SOVEREIGN_LOCAL for RESTRICTED data,
        while routing INTERNAL data to fast cloud endpoints.
        """
        # 1. Restricted Acquisition Data -> Forces Sovereign Local
        decision_restricted = model_router_v6.route_request(
            tenant_id=self.tenant_id,
            task_type="CONTRACT_ANALYSIS",
            data_classification="RESTRICTED",
            prompt_token_count=1500,
            preferred_provider="OPENAI" # Attacker or user requests cloud
        )
        self.assertTrue(decision_restricted.is_sovereign)
        self.assertEqual(decision_restricted.selected_provider, "SOVEREIGN_LOCAL")

        # 2. Internal General Data -> Allowed to use Cloud (e.g. OPENAI or ANTHROPIC)
        decision_internal = model_router_v6.route_request(
            tenant_id=self.tenant_id,
            task_type="CODE_REFACTOR",
            data_classification="INTERNAL",
            prompt_token_count=800,
            preferred_provider="OPENAI"
        )
        self.assertEqual(decision_internal.selected_provider, "OPENAI")
        self.assertFalse(decision_internal.is_sovereign)

    def test_diagnostics_bundle_sanitizes_secrets_and_pii(self):
        """
        Verify that DiagnosticsBundleGenerator scrubs API keys, JWTs, private keys,
        SSNs, and emails from incident context.
        """
        raw_error_context = {
            "error": "Failed during wire transfer processing",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----",
            "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
            "bearer_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThis",
            "customer_ssn": "987-65-4321",
            "contact_email": "alice.smith@enterprise.corp",
            "stack_trace": "ValueError at line 42 in payments.py"
        }

        bundle = diagnostics_generator.generate_incident_bundle(
            tenant_id=self.tenant_id,
            incident_type="WIRE_TRANSFER_EXCEPTION",
            entity_id="act_wire_9981",
            error_context=raw_error_context,
            operator_id="ops_support_lead"
        )

        ctx = bundle["error_context"]
        self.assertEqual(ctx["private_key"], "[REDACTED_RSA_KEY]")
        self.assertEqual(ctx["aws_access_key"], "[REDACTED_AWS_KEY]")
        self.assertEqual(ctx["bearer_token"], "[REDACTED_JWT]")
        self.assertEqual(ctx["customer_ssn"], "[REDACTED_SSN]")
        self.assertEqual(ctx["contact_email"], "[REDACTED_EMAIL]")
        self.assertEqual(ctx["stack_trace"], "ValueError at line 42 in payments.py")
        self.assertEqual(bundle["sanitization_status"], "VERIFIED_SCRUBBED")

if __name__ == "__main__":
    unittest.main()
