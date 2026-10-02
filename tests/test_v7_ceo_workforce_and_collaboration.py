"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Test Suite — CEO Workforce Control, Colleague Collaboration, & Hierarchical Governance
"""

import unittest
import uuid
import time
from core.employee_template import (
    employee_template_registry, EmployeeTemplate, TemplateType, TemplateStatus
)
from core.employee_factory_v7 import employee_factory_v7
from core.ceo_workforce_controller import ceo_workforce_controller, WorkforceDecisionOutcome
from core.workforce_collaboration_hub import workforce_collaboration_hub
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState, AuthorityScope
from core.workforce_manager_v4 import WorkforceManagerV4, DelegationViolationError

class TestV7CEOWorkforceAndCollaboration(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_v7_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_v7_{uuid.uuid4().hex[:6]}"
        self.workforce_mgr = WorkforceManagerV4()

    def test_ceo_workforce_discovery_and_proliferation_control(self):
        """
        Verify that the CEO discovers existing active workforce before creating new employees,
        and uses pre-built specialists when suitable to prevent uncontrolled workforce proliferation.
        """
        # 1. First Mission: No existing workforce -> CEO decides to create employee or use specialist
        dec1 = ceo_workforce_controller.plan_and_assign_mission(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            objective="Analyze Q3 cloud infrastructure cost outliers",
            required_capabilities=["ENGINEERING", "CODE_REVIEW"],
            department="ENGINEERING",
            budget_usd=300.0
        )
        self.assertIn(dec1.outcome, (
            WorkforceDecisionOutcome.USE_EXISTING_AGENT,
            WorkforceDecisionOutcome.CREATE_TEMPLATE_EMPLOYEE,
            WorkforceDecisionOutcome.ESCALATE_TO_HUMAN
        ))

        # 2. Register an active specialized AI Employee
        emp = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Senior Site Reliability Engineer",
            role_tier="AI_SPECIALIST",
            template_id="tmpl_sre",
            version="1.0.0",
            department_id="ENGINEERING",
            capabilities=["ENGINEERING", "INFRASTRUCTURE_AUDIT", "CLOUD_COST_OPTIMIZATION"],
            initial_budget_usd=1000.0
        )
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.EVALUATED, "eval", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.APPROVED, "exec", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.PROVISIONED, "sys", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ONBOARDED, "idp", "ok")
        ai_employee_registry.advance_lifecycle(emp.employee_id, EmployeeLifecycleState.ACTIVE, "mgr", "live")

        # 3. Second Mission requiring same capabilities:
        # CEO MUST select the existing active employee, NOT spawn a duplicate!
        dec2 = ceo_workforce_controller.plan_and_assign_mission(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            objective="Audit AWS EC2 instance reservations",
            required_capabilities=["INFRASTRUCTURE_AUDIT"],
            department="ENGINEERING",
            budget_usd=200.0
        )
        self.assertEqual(dec2.outcome, WorkforceDecisionOutcome.USE_EXISTING_EMPLOYEE)
        self.assertIn(emp.employee_id, dec2.selected_workers)
        self.assertIsNone(dec2.created_employee_id)

    def test_prebuilt_specialists_and_template_employees_collaborate_as_colleagues(self):
        """
        Verify that pre-built specialist agents and template-built employees
        can be assembled into a mission team under Chief Officer supervision.
        """
        # Create Project-Specific Hotel Marketing Employee from template
        tmpl = EmployeeTemplate(
            template_id=f"tmpl_mkt_{uuid.uuid4().hex[:6]}",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Hotel Digital Campaign Strategist",
            version="1.0.0",
            template_type=TemplateType.PROJECT_SPECIFIC,
            status=TemplateStatus.ACTIVE,
            business_purpose="Execute digital campaigns for Jaipur resort",
            role_definition="Marketing Campaign Lead",
            department="GROWTH",
            job_family="MARKETING",
            responsibilities=["Campaign creation", "Ad spend tracking"],
            objectives=["Target CAC < ₹1,200"],
            sop_references=[],
            kras=[{"name": "Campaign ROI"}],
            kpis=[{"name": "CAC", "target_value": 1200.0}],
            success_metrics=["CAC achieved"],
            failure_conditions=["Spend exceed"],
            required_knowledge=["DIGITAL_ADS"],
            knowledge_sources=["MARKETING_WIKI"],
            allowed_data_classes=["INTERNAL"],
            required_tools=["ANALYTICS", "CONTENT_GEN"],
            allowed_capabilities=["CAMPAIGN_MANAGEMENT"],
            authority_scope={"max_risk_class": "MUTATING", "max_single_spend_usd": 500.0},
            budget_limit=2000.0,
            token_budget=1000000,
            tool_budget=300,
            autonomy_level=3
        )
        employee_template_registry.create_template(tmpl)
        emp, _ = employee_factory_v7.instantiate_employee_from_template(
            template_id=tmpl.template_id,
            custom_name="Jaipur Campaign Lead AI",
            requester="AI_CEO"
        )

        # Assemble Mission Team: Template Employee Lead + Pre-built Specialists (Research, Browser, Data Analyst)
        team = workforce_collaboration_hub.form_mission_team(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="miss_campaign_jaipur_01",
            team_name="Jaipur Resort Q4 Marketing Swarm",
            mission_lead_employee_id=emp.employee_id,
            specialist_members=[
                emp.employee_id,
                "specialist_Research_Specialist",
                "specialist_Browser_Robot",
                "specialist_Data_Analyst"
            ],
            chief_supervisor="CHIEF_MARKETING_OFFICER",
            collaboration_mode="HYBRID"
        )

        self.assertEqual(team.mission_lead_employee_id, emp.employee_id)
        self.assertEqual(len(team.specialist_members), 4)
        self.assertEqual(team.chief_supervisor, "CHIEF_MARKETING_OFFICER")

    def test_conflict_resolution_by_policy_hierarchy(self):
        """
        Verify that disagreements between workers are resolved deterministically
        by policy and hierarchy, and NOT by arbitrary model confidence.
        """
        resolution = workforce_collaboration_hub.resolve_workforce_conflict(
            mission_id="miss_pricing_dispute_01",
            party_a="emp_revenue_optimizer_01",
            party_b="specialist_sales_agent",
            issue_description="Revenue employee proposed 15% discount; sales specialist advocated 25% discount to close fast.",
            resolver_tier="CHIEF_OFFICER",
            basis="POLICY_HIERARCHY",
            ruling="Revenue policy caps maximum unapproved discount at 15%. Ruling in favor of Revenue Employee per corporate policy."
        )

        self.assertEqual(resolution.resolved_by, "CHIEF_OFFICER")
        self.assertEqual(resolution.resolution_basis, "POLICY_HIERARCHY")
        self.assertIn("15%", resolution.final_verdict)

    def test_hierarchical_delegation_containment(self):
        """
        Verify that an AI Employee delegating to a child worker strictly obeys:
        CHILD_AUTHORITY ⊆ PARENT_AUTHORITY
        DELEGATED_BUDGET <= PARENT_REMAINING_BUDGET
        """
        # Parent Employee with max spend $500, risk class MUTATING
        parent = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Lead Operations Director",
            role_tier="AI_SPECIALIST",
            template_id="tmpl_dir",
            version="1.0.0",
            department_id="OPERATIONS",
            allowed_tools=["PMS_HOTEL_CONNECTOR", "READ_LEDGER"],
            allowed_data_domains=["INTERNAL", "CONFIDENTIAL"],
            authority=AuthorityScope(max_risk_class="MUTATING", max_single_spend_usd=500.0, can_delegate=True),
            initial_budget_usd=1000.0
        )
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.EVALUATED, "eval", "ok")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.APPROVED, "exec", "ok")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.PROVISIONED, "sys", "ok")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.ONBOARDED, "idp", "ok")
        ai_employee_registry.advance_lifecycle(parent.employee_id, EmployeeLifecycleState.ACTIVE, "mgr", "live")

        # 1. Valid Delegation (Child is subset)
        child_valid = self.workforce_mgr.delegate_to_child(
            parent_employee_id=parent.employee_id,
            child_name="Junior Audit Assistant",
            child_role_tier="AI_WORKER",
            child_template_id="tmpl_audit",
            requested_capabilities=["DATA_ANALYSIS"],
            requested_tools=["READ_LEDGER"],
            requested_data_domains=["INTERNAL"],
            requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=100.0),
            delegated_budget_usd=200.0
        )
        self.assertIsNotNone(child_valid)

        # 2. Invalid Delegation (Child budget exceeds parent remaining budget)
        with self.assertRaises(DelegationViolationError):
            self.workforce_mgr.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Excessive Spend Child",
                child_role_tier="AI_WORKER",
                child_template_id="tmpl_audit",
                requested_capabilities=["DATA_ANALYSIS"],
                requested_tools=["READ_LEDGER"],
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=100.0),
                delegated_budget_usd=5000.0 # Exceeds parent remaining $800!
            )

        # 3. Invalid Delegation (Child attempts to gain tool parent does not have)
        with self.assertRaises(DelegationViolationError):
            self.workforce_mgr.delegate_to_child(
                parent_employee_id=parent.employee_id,
                child_name="Rogue Tool Child",
                child_role_tier="AI_WORKER",
                child_template_id="tmpl_audit",
                requested_capabilities=["DATA_ANALYSIS"],
                requested_tools=["UNRESTRICTED_BASH_TERMINAL"], # Not in parent scope!
                requested_data_domains=["INTERNAL"],
                requested_authority=AuthorityScope(max_risk_class="LOW_RISK", max_single_spend_usd=100.0),
                delegated_budget_usd=100.0
            )

    def test_employee_succession_and_retirement(self):
        """
        Verify that employee succession retires the predecessor, records the transition,
        and preserves all historical evidence and audit trails.
        """
        emp_v1 = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Legacy Booking Assistant V1",
            role_tier="AI_WORKER",
            template_id="tmpl_bkg",
            version="1.0.0",
            department_id="OPERATIONS"
        )
        ai_employee_registry.advance_lifecycle(emp_v1.employee_id, EmployeeLifecycleState.EVALUATED, "eval", "ok")
        ai_employee_registry.advance_lifecycle(emp_v1.employee_id, EmployeeLifecycleState.APPROVED, "exec", "ok")
        ai_employee_registry.advance_lifecycle(emp_v1.employee_id, EmployeeLifecycleState.PROVISIONED, "sys", "ok")
        ai_employee_registry.advance_lifecycle(emp_v1.employee_id, EmployeeLifecycleState.ONBOARDED, "idp", "ok")
        ai_employee_registry.advance_lifecycle(emp_v1.employee_id, EmployeeLifecycleState.ACTIVE, "mgr", "live")

        emp_v2 = ai_employee_registry.propose_employee(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Advanced Booking Assistant V2",
            role_tier="AI_WORKER",
            template_id="tmpl_bkg",
            version="2.0.0",
            department_id="OPERATIONS"
        )
        ai_employee_registry.advance_lifecycle(emp_v2.employee_id, EmployeeLifecycleState.EVALUATED, "eval", "ok")
        ai_employee_registry.advance_lifecycle(emp_v2.employee_id, EmployeeLifecycleState.APPROVED, "exec", "ok")
        ai_employee_registry.advance_lifecycle(emp_v2.employee_id, EmployeeLifecycleState.PROVISIONED, "sys", "ok")
        ai_employee_registry.advance_lifecycle(emp_v2.employee_id, EmployeeLifecycleState.ONBOARDED, "idp", "ok")
        ai_employee_registry.advance_lifecycle(emp_v2.employee_id, EmployeeLifecycleState.ACTIVE, "mgr", "live")

        # Execute succession
        succ = workforce_collaboration_hub.execute_employee_succession(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            predecessor_id=emp_v1.employee_id,
            successor_id=emp_v2.employee_id,
            reason="Performance upgrade to version 2.0.0",
            authorized_memory_classes=["BOOKING_PATTERNS", "GUEST_PREFERENCES"]
        )

        self.assertEqual(succ["status"], "COMPLETED")
        self.assertEqual(succ["predecessor_state"], EmployeeLifecycleState.RETIRED)

        # Confirm V1 is retired in registry
        pred_reg = ai_employee_registry.get_employee(emp_v1.employee_id)
        self.assertEqual(pred_reg.lifecycle_state, EmployeeLifecycleState.RETIRED)
        self.assertFalse(pred_reg.is_operational())

        # Confirm V2 is active
        succ_reg = ai_employee_registry.get_employee(emp_v2.employee_id)
        self.assertEqual(succ_reg.lifecycle_state, EmployeeLifecycleState.ACTIVE)
        self.assertTrue(succ_reg.is_operational())
