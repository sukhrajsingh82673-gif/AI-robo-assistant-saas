"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Test Suite — Employee Templates, SOP Compiler, KPI/KRA Engine, & Employee Factory
"""

import unittest
import uuid
import time
from core.employee_template import (
    employee_template_registry, EmployeeTemplate, TemplateType, TemplateStatus
)
from core.sop_compiler import sop_compiler
from core.kpi_kra_engine import kpi_kra_engine, StructuredKPI, StructuredKRA
from core.employee_factory_v7 import employee_factory_v7
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState

class TestV7EmployeeTemplateAndFactory(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_v7_{uuid.uuid4().hex[:6]}"
        self.company_id = f"comp_v7_{uuid.uuid4().hex[:6]}"

    def test_universal_and_project_template_creation_and_immutable_versioning(self):
        """
        Verify creation of Universal and Project-Specific templates,
        and confirm that modifications create immutable new versions without mutating V1.
        """
        # 1. Create Universal Sales Template V1
        tmpl_v1 = EmployeeTemplate(
            template_id=f"tmpl_sales_{uuid.uuid4().hex[:6]}",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Universal B2B Sales Executive",
            version="1.0.0",
            template_type=TemplateType.UNIVERSAL,
            status=TemplateStatus.ACTIVE,
            business_purpose="Drive inbound and outbound enterprise SaaS sales pipeline.",
            role_definition="Executive Sales Specialist",
            department="GROWTH",
            job_family="SALES",
            responsibilities=["Lead discovery", "Product demos", "Contract closing"],
            objectives=["Achieve $50k monthly ARR additions"],
            sop_references=[],
            kras=[{"name": "Pipeline Conversion", "target": "25%"}],
            kpis=[{"name": "Monthly ARR", "target_value": 50000.0, "unit": "USD"}],
            success_metrics=["ARR target met"],
            failure_conditions=["Unapproved discounting > 15%"],
            required_knowledge=["SAAS_PRICING", "PRODUCT_CATALOG"],
            knowledge_sources=["CORPORATE_WIKI"],
            allowed_data_classes=["INTERNAL", "CONFIDENTIAL"],
            required_tools=["SALESFORCE_CRM", "EMAIL_CLIENT"],
            allowed_capabilities=["SALES_ENGAGEMENT", "LEAD_QUALIFICATION"],
            authority_scope={"max_risk_class": "MUTATING", "max_single_spend_usd": 1000.0},
            budget_limit=2500.0,
            token_budget=1000000,
            tool_budget=500,
            autonomy_level=3
        )
        created_v1 = employee_template_registry.create_template(tmpl_v1)
        self.assertEqual(created_v1.version, "1.0.0")
        self.assertTrue(len(created_v1.version_hash) == 64)
        hash_v1 = created_v1.version_hash

        # 2. Immutably publish Version 1.1.0 with updated budget
        tmpl_v2 = EmployeeTemplate(
            template_id=created_v1.template_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="Universal B2B Sales Executive",
            version="1.1.0",
            template_type=TemplateType.UNIVERSAL,
            status=TemplateStatus.ACTIVE,
            business_purpose="Drive inbound and outbound enterprise SaaS sales pipeline.",
            role_definition="Executive Sales Specialist",
            department="GROWTH",
            job_family="SALES",
            responsibilities=["Lead discovery", "Product demos", "Contract closing", "Partner co-selling"],
            objectives=["Achieve $75k monthly ARR additions"],
            sop_references=[],
            kras=[{"name": "Pipeline Conversion", "target": "30%"}],
            kpis=[{"name": "Monthly ARR", "target_value": 75000.0, "unit": "USD"}],
            success_metrics=["ARR target met"],
            failure_conditions=["Unapproved discounting > 10%"],
            required_knowledge=["SAAS_PRICING", "PRODUCT_CATALOG"],
            knowledge_sources=["CORPORATE_WIKI"],
            allowed_data_classes=["INTERNAL", "CONFIDENTIAL"],
            required_tools=["SALESFORCE_CRM", "EMAIL_CLIENT", "PARTNER_PORTAL"],
            allowed_capabilities=["SALES_ENGAGEMENT", "LEAD_QUALIFICATION"],
            authority_scope={"max_risk_class": "MUTATING", "max_single_spend_usd": 2000.0},
            budget_limit=5000.0,
            token_budget=2000000,
            tool_budget=1000,
            autonomy_level=3
        )
        created_v2 = employee_template_registry.create_version(created_v1.template_id, tmpl_v2, actor="AI_CEO")
        self.assertEqual(created_v2.version, "1.1.0")
        self.assertNotEqual(created_v2.version_hash, hash_v1)

        # 3. Verify V1 is still intact and queryable
        queried_v1 = employee_template_registry.get_template(created_v1.template_id, "1.0.0")
        self.assertIsNotNone(queried_v1)
        self.assertEqual(queried_v1.version, "1.0.0")
        self.assertEqual(queried_v1.budget_limit, 2500.0)

        # 4. Verify Latest defaults to 1.1.0
        latest = employee_template_registry.get_template(created_v1.template_id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.version, "1.1.0")
        self.assertEqual(latest.budget_limit, 5000.0)

    def test_sop_compiler_ingestion_and_ambiguity_flagging(self):
        """
        Verify that raw SOP text is parsed into structured responsibilities,
        constraints, tools, and that ambiguous statements are safely flagged.
        """
        raw_sop = """
        # Royal Hotel Jaipur — Front Office Operations Manual
        Role: Front Office Operations Specialist
        Department: OPERATIONS

        ## Responsibilities
        * Manage guest check-in and check-out procedures
        * Ensure VIP guests receive welcome package within 15 minutes of arrival
        * Monitor PMS room inventory and flag maintenance issues

        ## Authority and Approvals
        * Spending ceiling up to ₹5,000 for guest service recovery without supervisor approval
        * Must not offer room upgrades beyond Deluxe category without manager signoff
        * Handle VIP complaints at discretion whenever necessary

        ## Escalation Triggers
        * Unresolved billing discrepancies exceeding ₹10,000
        * System outages on PMS booking gateway

        ## Metrics
        * Guest Satisfaction: 95%
        * Response Time: <5m
        """
        compilation = sop_compiler.compile_sop_text(
            document_title="Royal_Hotel_Front_Office_SOP.md",
            text=raw_sop,
            default_department="OPERATIONS"
        )

        self.assertEqual(compilation.extracted_role, "Front Office Operations Specialist")
        self.assertEqual(compilation.extracted_department, "OPERATIONS")
        self.assertGreaterEqual(len(compilation.responsibilities), 3)
        self.assertIn("PMS_HOTEL_CONNECTOR", compilation.required_tools)

        # Check financial authority was parsed
        self.assertTrue(any(a.get("limit_usd") == 5000.0 for a in compilation.authorities))

        # Check hard constraint was captured
        self.assertTrue(any("beyond deluxe" in c.lower() for c in compilation.constraints))

        # Check ambiguity was flagged ("Handle VIP complaints at discretion whenever necessary")
        self.assertGreaterEqual(len(compilation.ambiguities_requiring_review), 1)
        ambig = compilation.ambiguities_requiring_review[0]
        self.assertIn("discretion", ambig["statement"].lower())

    def test_kpi_kra_engine_measurement_and_variance(self):
        """
        Verify that the KPI engine measures actual verified outcomes,
        computes variance, and determines performance health correctly.
        """
        emp_id = f"emp_rev_{uuid.uuid4().hex[:6]}"
        kpi = StructuredKPI(
            kpi_id=f"kpi_{uuid.uuid4().hex[:8]}",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            employee_id=emp_id,
            name="Room Revenue Target",
            definition="Total settled room booking revenue for the cycle",
            unit="INR",
            target_value=1000000.0,
            threshold_value=900000.0,
            measurement_frequency="DAILY",
            data_source="PMS_SETTLED_LEDGER",
            owner=emp_id,
            calculation_method="SUM",
            minimum_acceptable_value=800000.0,
            warning_threshold=900000.0,
            escalation_threshold=750000.0,
            verification_method="LEDGER_RECONCILIATION"
        )
        kpi_kra_engine.register_kpi(kpi)

        # 1. Record Target Met measurement
        res1 = kpi_kra_engine.record_measurement(
            kpi_id=kpi.kpi_id,
            measured_value=1050000.0,
            verification_proof={"source": "PMS_LEDGER", "batch_tx_id": "tx_99812"}
        )
        self.assertEqual(res1["status"], "TARGET_MET")
        self.assertEqual(res1["variance"], 50000.0)

        # 2. Record Warning measurement
        res2 = kpi_kra_engine.record_measurement(
            kpi_id=kpi.kpi_id,
            measured_value=920000.0,
            verification_proof={"source": "PMS_LEDGER", "batch_tx_id": "tx_99813"}
        )
        self.assertEqual(res2["status"], "WARNING")

        # 3. Evaluate aggregate employee health
        health = kpi_kra_engine.evaluate_employee_performance(emp_id)
        self.assertEqual(health["total_measurements"], 2)
        self.assertIn(health["health"], ("PERFORMING", "DEGRADED", "REVIEW_REQUIRED"))

    def test_24_stage_employee_factory_provisioning(self):
        """
        Verify that EmployeeFactoryV7 successfully executes the full 24-stage
        validation pipeline and provisions an active, governed AI Employee.
        """
        tmpl = EmployeeTemplate(
            template_id=f"tmpl_hotel_{uuid.uuid4().hex[:6]}",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            project_id="proj_jaipur_resort",
            name="Hotel Revenue Optimizer",
            version="1.0.0",
            template_type=TemplateType.PROJECT_SPECIFIC,
            status=TemplateStatus.ACTIVE,
            business_purpose="Maximize RevPAR and direct bookings for Royal Hotel Jaipur",
            role_definition="Hotel Revenue Specialist",
            department="OPERATIONS",
            job_family="HOSPITALITY_REVENUE",
            responsibilities=["Daily dynamic pricing", "OTA channel parity", "Direct booking conversion"],
            objectives=["Increase direct booking share by 20%"],
            sop_references=[{"title": "Pricing Rules", "id": "sop_pr_01"}],
            kras=[{"name": "RevPAR Maximization", "target": "₹8,500"}],
            kpis=[{"name": "RevPAR", "target_value": 8500.0, "unit": "INR"}],
            success_metrics=["Direct booking share > 35%"],
            failure_conditions=["OTA rate undercutting > 5%"],
            required_knowledge=["HOSPITALITY_PMS", "JAIPUR_SEASONALITY"],
            knowledge_sources=["PMS_DOCS"],
            allowed_data_classes=["INTERNAL", "CONFIDENTIAL"],
            required_tools=["PMS_HOTEL_CONNECTOR", "BOOKING_ENGINE_API"],
            allowed_capabilities=["DYNAMIC_PRICING", "INVENTORY_MANAGEMENT"],
            authority_scope={"max_risk_class": "MUTATING", "max_single_spend_usd": 500.0},
            budget_limit=1500.0,
            token_budget=1000000,
            tool_budget=400,
            autonomy_level=3
        )
        employee_template_registry.create_template(tmpl)

        # Provision through 24-stage factory
        emp, prov = employee_factory_v7.instantiate_employee_from_template(
            template_id=tmpl.template_id,
            custom_name="Jaipur Royal Revenue AI Specialist",
            project_id="proj_jaipur_resort",
            budget_override_usd=1200.0,
            requester="AI_CEO"
        )

        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.ACTIVE)
        self.assertEqual(emp.allocated_budget_usd, 1200.0)
        self.assertEqual(len(prov.stages_executed), 24)
        self.assertTrue(prov.compliance_passed)
        self.assertEqual(prov.stages_executed[-1].stage_name, "ACTIVATION")
        self.assertEqual(prov.stages_executed[-1].status, "PASSED")

        # Confirm operational state in AI employee registry
        registered = ai_employee_registry.get_employee(emp.employee_id)
        self.assertIsNotNone(registered)
        self.assertTrue(registered.is_operational())
