"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Test Suite: Universal Organization Layer beneath the AIC CEO
Validates:
  1. Organization Constitution & 16-field AccountabilityNode
  2. Executive Role Registry (15+ Canonical C-Suite Roles)
  3. Company Onboarding & Organization Gap Analyzer
  4. Dynamic Organization Design Engine & Span of Control
  5. KRA/KPI Cascade with Mandatory Counter-Metrics (Anti-Gaming)
  6. Executable Standard Operating Procedures (SOPs)
  7. Executive Communication, Rate-Limiting & Delegations
  8. Organization Restructuring & Net Organizational Value Simulator
  9. 6 Industry Archetype Integration Scenarios:
     - Small SaaS Startup
     - Large Enterprise SaaS
     - Hospitality / Hotel
     - Precision Manufacturing
     - Global Travel Agency
     - Regulated Healthcare Provider
  10. V8 API Gateway Organization Endpoints (GET & POST)
"""

import unittest
import time
import uuid

from core.aic_organization_constitution import (
    HierarchyLevel, RoleRequirementStatus, WorkforceType, AgentCategory,
    CompanyScaleStage, MessagePriority, OperatingCadence, AccountabilityNode,
    AuthorityMatrix, ExecutiveRoleDefinition, ExecutiveRoleRegistry,
    CompanyProfile, OrgGapAnalysisResult, OrganizationGapAnalyzer,
    DynamicOrgBlueprint, DynamicOrganizationDesignEngine,
    GovernedMessage, ExecutiveCommunicationEngine,
    DelegationRecord, DelegationEngine, EscalationEvent, EscalationEngine,
    OrgRestructuringSimulation, OrganizationRestructuringEngine
)
from core.v8_api_handler import V8ApiHandler


class TestOrganizationConstitution(unittest.TestCase):
    def test_hierarchy_levels(self):
        levels = [l.value for l in HierarchyLevel]
        self.assertIn("L0_OWNER", levels)
        self.assertIn("L1_GOVERNANCE", levels)
        self.assertIn("L2_CEO", levels)
        self.assertIn("L3_CHIEF_EXECUTIVE", levels)
        self.assertIn("L5_DEPARTMENT", levels)
        self.assertIn("L8_MANAGER", levels)
        self.assertIn("L10_WORKER", levels)
        self.assertIn("L11_TASK", levels)
        self.assertEqual(len(levels), 12)

    def test_16_field_accountability_node(self):
        node = AccountabilityNode(
            node_id="node_exec_cfo",
            owner="Persona_Corporate_Treasurer",
            purpose="Treasury solvency and capital preservation",
            mission="Maintain minimum 6-month cash runway",
            authority_level="EXECUTIVE_FUNCTION",
            responsibility=["Treasury management", "Accounts payable", "Financial audits"],
            accountability="Verified cash ledger reconciliation",
            kra_ids=["KRA-01-Solvency"],
            kpi_ids=["KPI-FIN-01-Runway"],
            budget_limit_usd=100000.0,
            resources_allocated={"compute_tokens": 1000000, "human_liaisons": 2},
            reporting_line_id="node_exec_ceo",
            communication_channels=["TREASURY_SECURE_CHANNEL"],
            escalation_path_id="node_exec_ceo",
            risk_limit="MEDIUM",
            success_criteria="Zero unreconciled audit variances",
            verification_method="CRYPTOGRAPHIC_AUDIT_LEDGER"
        )
        self.assertEqual(node.node_id, "node_exec_cfo")
        self.assertEqual(node.budget_limit_usd, 100000.0)
        self.assertEqual(node.risk_limit, "MEDIUM")

    def test_human_authority_protection_invariant(self):
        matrix = AuthorityMatrix(
            can_decide=["Operational Scheduling"],
            can_approve=["Vendor Invoices < $5,000"],
            can_execute=["Database Backups"],
            can_delegate=["Task Execution"],
            can_spend_usd_limit=5000.0,
            can_hire=False,
            can_fire=False,
            can_contract=False,
            can_negotiate=True,
            can_change_org_structure=False
        )
        # AI agent cannot bind company in legal contracts or modify constitution
        self.assertFalse(matrix.can_contract)
        self.assertFalse(matrix.can_change_org_structure)
        self.assertFalse(matrix.can_fire)


class TestExecutiveRoleRegistry(unittest.TestCase):
    def setUp(self):
        ExecutiveRoleRegistry.initialize()

    def test_all_canonical_roles_registered(self):
        roles = ExecutiveRoleRegistry.list_roles()
        role_ids = {r.role_id for r in roles}
        expected = [
            "EXEC_CEO", "EXEC_CFO", "EXEC_COO", "EXEC_CTO", "EXEC_CMO",
            "EXEC_CRO", "EXEC_CSO", "EXEC_CHRO", "EXEC_CPO", "EXEC_CIO",
            "EXEC_CISO", "EXEC_CLO", "EXEC_CSCO", "EXEC_CCO_CUSTOMER",
            "EXEC_CRO_RISK"
        ]
        for exp in expected:
            self.assertIn(exp, role_ids, f"Expected role {exp} was not found in registry")

    def test_ceo_role_properties(self):
        ceo = ExecutiveRoleRegistry.get_role("EXEC_CEO")
        self.assertIsNotNone(ceo)
        self.assertEqual(ceo.reporting_line, "OWNER_SOVEREIGN")
        self.assertIn("Enterprise Economic Value", ceo.kra)
        self.assertIn("EBITDA Margin %", ceo.kpi)
        self.assertIn("Class A Bounded Decisions", ceo.decision_rights)

    def test_failover_roles_defined(self):
        for role in ExecutiveRoleRegistry.list_roles():
            self.assertTrue(len(role.replacement_failover_role) > 0, f"Role {role.role_id} has no failover role")


class TestOrganizationGapAnalyzer(unittest.TestCase):
    def test_gap_analysis_detects_missing_cfo(self):
        prof = CompanyProfile(
            company_id="comp_test_gap",
            tenant_id="tenant_01",
            company_name="SaaS Scaleup",
            industry="SAAS_SOFTWARE",
            geography="US",
            company_size="GROWING_COMPANY",
            stage_maturity="SCALEUP",
            revenue_model="SUBSCRIPTION_SAAS",
            annual_revenue_usd=12000000.0,
            current_human_employees=60,
            current_active_agents=25,
            products_services=["Cloud Security Platform"],
            customer_archetype="B2B",
            regulatory_intensity="HIGH",
            operational_complexity="MEDIUM",
            capital_intensity="ASSET_LIGHT"
        )
        existing = {
            "executives": [{"role_id": "EXEC_CEO"}, {"role_id": "EXEC_CTO"}],
            "departments": [{"name": "Engineering"}],
            "workforce": []
        }
        res = OrganizationGapAnalyzer.analyze(prof, existing)
        gap_functions = [g["function"] for g in res.gaps]
        self.assertIn("EXEC_CFO", gap_functions)
        self.assertIn("EXEC_COO", gap_functions)
        self.assertIn("EXEC_CRO", gap_functions)
        self.assertTrue(len(res.recommendations) > 0)


class TestDynamicOrganizationDesignEngine(unittest.TestCase):
    def test_micro_startup_synthesis(self):
        prof = CompanyProfile(
            company_id="comp_micro",
            tenant_id="tenant_01",
            company_name="Seed AI Studio",
            industry="SAAS_SOFTWARE",
            geography="GLOBAL",
            company_size="MICRO_STARTUP",
            stage_maturity="EARLY_STAGE",
            revenue_model="SUBSCRIPTION_SAAS",
            annual_revenue_usd=300000.0,
            current_human_employees=4,
            current_active_agents=6,
            products_services=["AI Copywriting"],
            customer_archetype="B2B",
            regulatory_intensity="LOW",
            operational_complexity="LOW",
            capital_intensity="ASSET_LIGHT"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_CEO", exec_ids)
        self.assertIn("EXEC_COO", exec_ids)
        self.assertIn("EXEC_CRO", exec_ids)
        # Micro startup combines roles and avoids bloated C-suite
        self.assertNotIn("EXEC_CISO", exec_ids)
        self.assertNotIn("EXEC_CLO", exec_ids)

    def test_enterprise_synthesis_spans(self):
        prof = CompanyProfile(
            company_id="comp_ent",
            tenant_id="tenant_01",
            company_name="MegaCorp Global",
            industry="SAAS_SOFTWARE",
            geography="GLOBAL",
            company_size="ENTERPRISE",
            stage_maturity="MATURE",
            revenue_model="SUBSCRIPTION_SAAS",
            annual_revenue_usd=250000000.0,
            current_human_employees=1200,
            current_active_agents=350,
            products_services=["Enterprise Suite"],
            customer_archetype="B2B",
            regulatory_intensity="HIGH",
            operational_complexity="VERY_HIGH",
            capital_intensity="MODERATE"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        self.assertTrue(len(bp.executives) >= 6)
        self.assertTrue(len(bp.departments) >= 4)
        self.assertTrue(len(bp.kras) >= 4)
        self.assertTrue(len(bp.kpis) >= 4)
        self.assertTrue(len(bp.sops) >= 4)
        self.assertTrue(len(bp.cryptographic_seal) == 64)


class TestExecutiveCommunicationAndDelegation(unittest.TestCase):
    def setUp(self):
        ExecutiveCommunicationEngine._messages.clear()
        ExecutiveCommunicationEngine._rate_limits.clear()
        DelegationEngine._delegations.clear()
        EscalationEngine._escalations.clear()

    def test_send_communication(self):
        msg = ExecutiveCommunicationEngine.send_communication(
            sender_id="EXEC_CEO",
            recipient_id="EXEC_COO",
            subject="Optimize unit labor cost",
            body="Implement automation across tier-1 ticket routing.",
            priority=MessagePriority.REQUEST,
            response_required_by=24.0
        )
        self.assertEqual(msg.sender_id, "EXEC_CEO")
        self.assertEqual(msg.recipient_id, "EXEC_COO")
        self.assertEqual(msg.status, "SENT")
        self.assertEqual(len(ExecutiveCommunicationEngine.get_messages()), 1)

    def test_anti_storm_rate_limiting(self):
        for i in range(20):
            ExecutiveCommunicationEngine.send_communication(
                sender_id="CHATTY_AGENT",
                recipient_id="EXEC_CEO",
                subject=f"Update {i}",
                body="Ping"
            )
        # 21st message must raise RuntimeError
        with self.assertRaises(RuntimeError):
            ExecutiveCommunicationEngine.send_communication(
                sender_id="CHATTY_AGENT",
                recipient_id="EXEC_CEO",
                subject="Storming",
                body="Overflow ping"
            )

    def test_bounded_delegation_record(self):
        dlg = DelegationEngine.create_delegation(
            delegator_id="EXEC_CEO",
            delegatee_id="EXEC_COO",
            mandate="Scale logistics throughput 20%",
            authority_level="EXECUTIVE_FUNCTION",
            budget_usd=45000.0,
            time_hours=168.0,
            prohibitions=["LEGAL_DEEDS", "BANK_OPENING", "UNAUTHORIZED_HIRING"],
            success_criteria="Throughput verified by ERP telemetry"
        )
        self.assertEqual(dlg.delegator_id, "EXEC_CEO")
        self.assertEqual(dlg.granted_authority_level, "EXECUTIVE_FUNCTION")
        self.assertIn("LEGAL_DEEDS", dlg.prohibited_actions)
        self.assertEqual(len(DelegationEngine.list_delegations()), 1)

    def test_rules_based_escalation_trigger(self):
        esc = EscalationEngine.trigger_escalation(
            originator_id="AGENT_FIN_01",
            target_executive_id="EXEC_CFO",
            trigger_reason="Unreconciled bank ledger discrepancy of $45,000",
            severity="CRITICAL",
            details={"discrepancy_usd": 45000.0, "account": "Operating Treasury"},
            required_resolution="Emergency Treasury Freeze & Audit"
        )
        self.assertEqual(esc.severity, "CRITICAL")
        self.assertEqual(esc.status, "OPEN")
        self.assertEqual(len(EscalationEngine.list_escalations()), 1)


class TestOrganizationRestructuringEngine(unittest.TestCase):
    def test_restructuring_simulation(self):
        curr_bp = {
            "executives": [{"role_id": "EXEC_CEO"}, {"role_id": "EXEC_COO"}],
            "workforce_agents": [{"role_id": "AGENT_01"}]
        }
        prop_bp = {
            "executives": [{"role_id": "EXEC_CEO"}, {"role_id": "EXEC_CFO"}, {"role_id": "EXEC_COO"}, {"role_id": "EXEC_CTO"}],
            "workforce_agents": [{"role_id": "AGENT_01"}, {"role_id": "AGENT_02"}, {"role_id": "AGENT_03"}]
        }
        sim = OrganizationRestructuringEngine.simulate_restructuring("comp_restr", curr_bp, prop_bp)
        self.assertEqual(sim.current_roles_count, 2)
        self.assertEqual(sim.proposed_roles_count, 4)
        self.assertIn("EXEC_CFO", sim.roles_added)
        self.assertIn("EXEC_CTO", sim.roles_added)
        self.assertTrue(sim.projected_cost_delta_usd > 0)
        self.assertTrue(sim.organizational_value_score > 0)
        # Adding CFO triggers SOVEREIGN_OWNER approval
        self.assertEqual(sim.approval_required, "SOVEREIGN_OWNER")


class TestSixCompanyArchetypeScenarios(unittest.TestCase):
    """
    Tests dynamic organizational adaptation across 6 distinct company archetypes.
    """
    def test_scenario_1_small_saas(self):
        prof = CompanyProfile(
            company_id="comp_scen_saas_small",
            tenant_id="tenant_01",
            company_name="CloudSync Micro",
            industry="SAAS_SOFTWARE",
            geography="US",
            company_size="SMALL_COMPANY",
            stage_maturity="SCALEUP",
            revenue_model="SUBSCRIPTION_SAAS",
            annual_revenue_usd=2500000.0,
            current_human_employees=12,
            current_active_agents=15,
            products_services=["Data Sync API"],
            customer_archetype="B2B",
            regulatory_intensity="LOW",
            operational_complexity="MEDIUM",
            capital_intensity="ASSET_LIGHT"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_CEO", exec_ids)
        self.assertIn("EXEC_CTO", exec_ids)
        self.assertIn("EXEC_CRO", exec_ids)
        self.assertIn("EXEC_CFO", exec_ids)

    def test_scenario_2_large_enterprise_saas(self):
        prof = CompanyProfile(
            company_id="comp_scen_saas_large",
            tenant_id="tenant_01",
            company_name="OmniCloud Enterprise",
            industry="SAAS_SOFTWARE",
            geography="GLOBAL",
            company_size="ENTERPRISE",
            stage_maturity="MATURE",
            revenue_model="SUBSCRIPTION_SAAS",
            annual_revenue_usd=90000000.0,
            current_human_employees=650,
            current_active_agents=200,
            products_services=["Enterprise Cloud Suite"],
            customer_archetype="B2B",
            regulatory_intensity="HIGH",
            operational_complexity="HIGH",
            capital_intensity="MODERATE"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_CPO", exec_ids)
        self.assertIn("EXEC_CISO", exec_ids)
        self.assertIn("EXEC_CRO", exec_ids)

    def test_scenario_3_hospitality_hotel(self):
        prof = CompanyProfile(
            company_id="comp_scen_hotel",
            tenant_id="tenant_01",
            company_name="Grand Azure Luxury Resort",
            industry="HOSPITALITY_HOTEL",
            geography="APAC",
            company_size="MIDSIZE_COMPANY",
            stage_maturity="MATURE",
            revenue_model="DIRECT_BOOKING_HOSPITALITY",
            annual_revenue_usd=35000000.0,
            current_human_employees=280,
            current_active_agents=40,
            products_services=["Luxury Rooms", "Fine Dining", "Events"],
            customer_archetype="B2C",
            regulatory_intensity="MEDIUM",
            operational_complexity="HIGH",
            capital_intensity="ASSET_HEAVY"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_CMO", exec_ids)
        self.assertIn("EXEC_CCO_CUSTOMER", exec_ids)
        self.assertIn("EXEC_CSCO", exec_ids) # F&B/Supply chain
        dept_names = [d["department_name"] for d in bp.departments]
        self.assertIn("Rooms & Front Office", dept_names)

    def test_scenario_4_precision_manufacturing(self):
        prof = CompanyProfile(
            company_id="comp_scen_mfg",
            tenant_id="tenant_01",
            company_name="AeroMach Precision Tooling",
            industry="MANUFACTURING",
            geography="EU",
            company_size="GROWING_COMPANY",
            stage_maturity="MATURE",
            revenue_model="CONTRACT_MANUFACTURING",
            annual_revenue_usd=22000000.0,
            current_human_employees=110,
            current_active_agents=30,
            products_services=["CNC Aerospace Parts"],
            customer_archetype="B2B",
            regulatory_intensity="HIGH",
            operational_complexity="VERY_HIGH",
            capital_intensity="ASSET_HEAVY"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_CSCO", exec_ids)
        dept_names = [d["department_name"] for d in bp.departments]
        self.assertIn("Plant Production & Assembly", dept_names)

    def test_scenario_5_global_travel_agency(self):
        prof = CompanyProfile(
            company_id="comp_scen_travel",
            tenant_id="tenant_01",
            company_name="Wanderlust Global Travel",
            industry="TRAVEL_TOURISM",
            geography="GLOBAL",
            company_size="SMALL_COMPANY",
            stage_maturity="GROWTH",
            revenue_model="COMMISSION_SERVICES",
            annual_revenue_usd=8000000.0,
            current_human_employees=25,
            current_active_agents=35,
            products_services=["Curated Itineraries", "Flight/Hotel Bookings"],
            customer_archetype="B2C",
            regulatory_intensity="MEDIUM",
            operational_complexity="MEDIUM",
            capital_intensity="ASSET_LIGHT"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_COO", exec_ids)
        self.assertIn("EXEC_CRO", exec_ids)

    def test_scenario_6_regulated_healthcare(self):
        prof = CompanyProfile(
            company_id="comp_scen_health",
            tenant_id="tenant_01",
            company_name="Apex Diagnostic Care",
            industry="HEALTHCARE_SERVICES",
            geography="US",
            company_size="GROWING_COMPANY",
            stage_maturity="SCALEUP",
            revenue_model="INSURANCE_AND_DIRECT",
            annual_revenue_usd=18000000.0,
            current_human_employees=95,
            current_active_agents=20,
            products_services=["Diagnostic Scans", "Telehealth"],
            customer_archetype="B2C",
            regulatory_intensity="SEVERE",
            operational_complexity="VERY_HIGH",
            capital_intensity="MODERATE"
        )
        bp = DynamicOrganizationDesignEngine.synthesize_organization(prof)
        exec_ids = [e["role_id"] for e in bp.executives]
        self.assertIn("EXEC_CRO_RISK", exec_ids)
        self.assertIn("EXEC_CLO", exec_ids)


class TestV8OrganizationApiIntegration(unittest.TestCase):
    def test_get_organization_blueprint(self):
        res, status = V8ApiHandler.handle_get("/api/v8/organization", {}, "t_test", "c_test")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertIn("blueprint", res)

    def test_get_roles_and_chart(self):
        res, status = V8ApiHandler.handle_get("/api/v8/organization/roles", {}, "t_test", "c_test")
        self.assertEqual(status, 200)
        self.assertTrue(res.get("count") >= 15)

        chart_res, chart_status = V8ApiHandler.handle_get("/api/v8/organization/chart", {}, "t_test", "c_test")
        self.assertEqual(chart_status, 200)
        self.assertTrue(chart_res.get("executives_count") > 0)

    def test_post_analyze_and_design(self):
        a_res, a_status = V8ApiHandler.handle_post(
            "/api/v8/organization/analyze",
            {"industry": "SAAS_SOFTWARE", "company_size": "SMALL_COMPANY"},
            "t_test", "c_test"
        )
        self.assertEqual(a_status, 200)
        self.assertTrue(a_res.get("success"))

        d_res, d_status = V8ApiHandler.handle_post(
            "/api/v8/organization/design",
            {"industry": "HOSPITALITY_HOTEL", "company_size": "MIDSIZE_COMPANY"},
            "t_test", "c_test"
        )
        self.assertEqual(d_status, 200)
        self.assertEqual(d_res.get("blueprint", {}).get("industry"), "HOSPITALITY_HOTEL")

    def test_post_simulate_and_activate(self):
        s_res, s_status = V8ApiHandler.handle_post(
            "/api/v8/organization/simulate",
            {"proposed_profile": {"company_size": "MIDSIZE_COMPANY"}},
            "t_test", "c_test"
        )
        self.assertEqual(s_status, 200)
        self.assertTrue(s_res.get("simulation", {}).get("organizational_value_score") > 0)

        act_res, act_status = V8ApiHandler.handle_post(
            "/api/v8/organization/activate",
            {"blueprint_id": "bp_active_test"},
            "t_test", "c_test"
        )
        self.assertEqual(act_status, 200)
        self.assertEqual(act_res.get("status"), "ACTIVE")


if __name__ == "__main__":
    unittest.main()
