"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V4 Test Suite — AI Employee OS, Lifecycle State Machine, & Delegation Containment
"""

import unittest
import uuid
from core.ai_employee_os import (
    ai_employee_registry,
    EmployeeLifecycleState,
    EmployeeRoleTier,
    AuthorityScope
)
from core.workforce_manager_v4 import (
    workforce_manager_v4,
    DelegationViolationError
)
from core.identity_gateway import identity_gateway

class TestV4AIEmployeeLifecycle(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_emp_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_emp_{uuid.uuid4().hex[:6]}"

    def test_full_ten_stage_lifecycle_and_illegal_transitions(self):
        """Test strict sequential lifecycle advancement and blocking of illegal transitions."""
        emp = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Alice AI Analyst",
            role_tier=EmployeeRoleTier.AI_SPECIALIST,
            template_id="analyst_v1",
            version="1.0.0",
            department_id="FINANCE",
            initial_budget_usd=500.0
        )
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.PROPOSED)

        # Illegal jump: PROPOSED -> ACTIVE must be blocked
        with self.assertRaises(PermissionError):
            ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ACTIVE)

        # Stage 2: EVALUATED
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.EVALUATED)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.EVALUATED)

        # Stage 3: APPROVED
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.APPROVED)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.APPROVED)

        # Stage 4: PROVISIONED
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.PROVISIONED)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.PROVISIONED)

        # Stage 5: ONBOARDED (triggers identity registration in directory)
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ONBOARDED)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.ONBOARDED)
        
        # Verify identity exists in identity gateway
        ident = identity_gateway.get_identity(emp.employee_id)
        self.assertIsNotNone(ident)
        self.assertEqual(ident.status, "ACTIVE")

        # Stage 6: ACTIVE
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ACTIVE)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertTrue(emp.is_operational())

        # Stage 7: PAUSED
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.PAUSED)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertFalse(emp.is_operational())

        # Unpause -> ACTIVE
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ACTIVE)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertTrue(emp.is_operational())

        # Stage 8: OFFBOARDED (triggers identity revocation)
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.OFFBOARDED, reason="Project Complete")
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.OFFBOARDED)

        # Check identity is offboarded
        ident = identity_gateway.get_identity(emp.employee_id)
        self.assertEqual(ident.status, "OFFBOARDED")

        # Stage 9: RETIRED
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.RETIRED)
        emp = ai_employee_registry.get_employee(emp.employee_id)
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.RETIRED)

        # Terminus: Cannot transition out of RETIRED
        with self.assertRaises(PermissionError):
            ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ACTIVE)

    def test_delegation_containment_invariants(self):
        """
        Verify mathematical delegation containment:
        CHILD_AUTHORITY ⊆ PARENT_AUTHORITY
        CHILD_TOOL_SCOPE ⊆ PARENT_TOOL_SCOPE
        CHILD_DATA_SCOPE ⊆ PARENT_DATA_SCOPE
        CHILD_BUDGET <= PARENT_REMAINING_BUDGET
        """
        # Create and activate parent employee
        parent = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Lead Autonomous Manager",
            role_tier=EmployeeRoleTier.AI_EXECUTIVE,
            template_id="mgr_v1",
            version="1.0.0",
            department_id="ENGINEERING",
            capabilities=["CODE_REVIEW", "DEPLOY"],
            allowed_tools=["git_cli", "test_runner", "slack_notify"],
            allowed_data_domains=["INTERNAL", "CONFIDENTIAL"],
            authority=AuthorityScope(
                max_risk_class="MUTATING",
                max_single_spend_usd=50.0,
                can_delegate=True,
                can_access_restricted_data=False,
                requires_human_approval=False
            ),
            initial_budget_usd=200.0
        )
        # Advance to ACTIVE
        for state in [
            EmployeeLifecycleState.EVALUATED,
            EmployeeLifecycleState.APPROVED,
            EmployeeLifecycleState.PROVISIONED,
            EmployeeLifecycleState.ONBOARDED,
            EmployeeLifecycleState.ACTIVE
        ]:
            ai_employee_registry.advance_lifecycle(parent.employee_id, state)

        # Invariant 1: Budget containment (child cannot exceed parent budget)
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Overbudget Subordinate",
                child_role_tier=EmployeeRoleTier.AI_WORKER,
                child_template_id="worker_v1",
                requested_capabilities=["CODE_REVIEW"],
                requested_tools=["git_cli"],
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=10.0),
                delegated_budget_usd=350.0  # Parent only has 200.0
            )

        # Invariant 2: Tool scope containment (child cannot request tools parent doesn't have)
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Unauthorized Tool Worker",
                child_role_tier=EmployeeRoleTier.AI_WORKER,
                child_template_id="worker_v1",
                requested_capabilities=["CODE_REVIEW"],
                requested_tools=["git_cli", "aws_production_console"], # Parent doesn't have aws_production_console
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=10.0),
                delegated_budget_usd=20.0
            )

        # Invariant 3: Data scope containment (child cannot access data parent cannot access)
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Overclearance Worker",
                child_role_tier=EmployeeRoleTier.AI_WORKER,
                child_template_id="worker_v1",
                requested_capabilities=["CODE_REVIEW"],
                requested_tools=["git_cli"],
                requested_data_domains=["INTERNAL", "RESTRICTED"], # Parent only has INTERNAL, CONFIDENTIAL
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=10.0),
                delegated_budget_usd=20.0
            )

        # Invariant 4: Risk containment (child cannot exceed parent risk class)
        with self.assertRaises(DelegationViolationError):
            workforce_manager_v4.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Destructive Child",
                child_role_tier=EmployeeRoleTier.AI_WORKER,
                child_template_id="worker_v1",
                requested_capabilities=["CODE_REVIEW"],
                requested_tools=["git_cli"],
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="DESTRUCTIVE"), # Parent is MUTATING
                delegated_budget_usd=20.0
            )

        # Successful delegation conforming to all invariants
        child = workforce_manager_v4.delegate_to_child(
            parent_employee_id=parent.employee_id,
            child_name="Compliant Junior Worker",
            child_role_tier=EmployeeRoleTier.AI_WORKER,
            child_template_id="worker_v1",
            requested_capabilities=["CODE_REVIEW"],
            requested_tools=["git_cli"],
            requested_data_domains=["INTERNAL"],
            requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=10.0),
            delegated_budget_usd=50.0
        )
        self.assertIsNotNone(child)
        self.assertEqual(child.supervisor_id, parent.employee_id)
        self.assertEqual(child.allocated_budget_usd, 50.0)

        # Verify parent's budget was deducted
        updated_parent = ai_employee_registry.get_employee(parent.employee_id)
        self.assertEqual(updated_parent.spent_budget_usd, 50.0)
        self.assertEqual(updated_parent.remaining_budget(), 150.0)

if __name__ == "__main__":
    unittest.main()
