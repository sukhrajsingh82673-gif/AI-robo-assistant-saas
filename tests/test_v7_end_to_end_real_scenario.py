"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 End-to-End Real Scenario Test — Autonomous Hotel Revenue Optimization

Full Lifecycle Demonstration:
Human Owner -> AI CEO -> Business Mission -> Workforce Discovery ->
Template Selection -> Real SOP Input -> KPI/KRA Input -> Employee Factory ->
Provisioning -> Manager Assignment -> Colleague Team -> Tool Execution ->
Outcome Verification -> KPI Measurement -> CEO Observation -> Evidence Ledger
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
from core.ceo_workforce_controller import ceo_workforce_controller
from core.workforce_collaboration_hub import workforce_collaboration_hub
from core.ai_employee_os import ai_employee_registry, EmployeeLifecycleState
from core.evidence_service import evidence_service
from core.database_engine import engine, WorkloadType

class TestV7EndToEndRealScenario(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_hotel_{uuid.uuid4().hex[:6]}"
        self.company_id = "comp_royal_hotel_jaipur"

    def test_complete_end_to_end_hotel_revenue_scenario(self):
        """
        Executes the full V7 architectural chain from human intent down to
        verified settled revenue and cryptographic evidence audit.
        """
        # 1. Real SOP Document for the Hotel
        real_sop_content = """
        # Royal Hotel Jaipur — Revenue Management & Dynamic Pricing SOP
        Role: Hotel Revenue Optimization Specialist
        Department: OPERATIONS

        ## Responsibilities
        * Monitor real-time room occupancy and competitive market rates in Jaipur
        * Adjust daily BAR (Best Available Rate) across direct and OTA channels
        * Implement length-of-stay restrictions during peak tourist weekends

        ## Authority and Approvals
        * Spending ceiling up to ₹10,000 for flash promotional discounts
        * Must not discount room rates below base floor of ₹5,500 without COO signoff
        * Coordinate directly with marketing specialists on promotional ad copy

        ## Escalation Triggers
        * Occupancy dropping below 60% with less than 7 days to arrival
        * OTA parity violations detected across third-party portals

        ## KPIs
        * Monthly Direct Booking Revenue: ₹10,00,000
        * Average Daily Rate: ₹8,500
        """

        # 2. SOP Ingestion & Policy Compilation
        sop_result = sop_compiler.compile_sop_text(
            document_title="Royal_Hotel_Jaipur_Revenue_SOP.md",
            text=real_sop_content,
            default_department="OPERATIONS"
        )
        self.assertEqual(sop_result.extracted_role, "Hotel Revenue Optimization Specialist")
        self.assertGreaterEqual(len(sop_result.responsibilities), 3)

        # 3. Create Project-Specific Template from Compiled SOP
        tmpl_id = f"tmpl_jaipur_rev_{uuid.uuid4().hex[:6]}"
        template = EmployeeTemplate(
            template_id=tmpl_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            project_id="proj_jaipur_q4_expansion",
            name="Royal Hotel Jaipur Revenue Optimization Employee",
            version="1.0.0",
            template_type=TemplateType.PROJECT_SPECIFIC,
            status=TemplateStatus.ACTIVE,
            business_purpose="Drive 20% direct booking revenue expansion for Royal Hotel Jaipur",
            role_definition=sop_result.extracted_role,
            department="OPERATIONS",
            job_family="HOSPITALITY_REVENUE",
            responsibilities=sop_result.responsibilities,
            objectives=["Achieve ₹10,00,000 direct revenue in Q4", "Maintain ADR >= ₹8,500"],
            sop_references=[{"doc": "Royal_Hotel_Jaipur_Revenue_SOP.md", "id": sop_result.compilation_id}],
            kras=[{"name": "Revenue Optimization", "responsibility": "Daily pricing and yield"}],
            kpis=[{
                "name": "Direct Booking Revenue",
                "target_value": 1000000.0,
                "unit": "INR",
                "threshold_value": 900000.0,
                "minimum_acceptable_value": 800000.0,
                "warning_threshold": 900000.0,
                "escalation_threshold": 750000.0,
                "data_source": "PMS_SETTLED_LEDGER",
                "verification_method": "LEDGER_RECONCILIATION"
            }],
            success_metrics=["Revenue target met", "Zero parity breaches"],
            failure_conditions=sop_result.constraints,
            required_knowledge=["JAIPUR_HOTEL_MARKET", "OPERA_PMS_SCHEMA"],
            knowledge_sources=["CORPORATE_WIKI"],
            allowed_data_classes=["INTERNAL", "CONFIDENTIAL"],
            required_tools=["PMS_HOTEL_CONNECTOR", "ANALYTICS_QUERY_TOOL"],
            allowed_capabilities=["DYNAMIC_PRICING", "YIELD_MANAGEMENT"],
            authority_scope={"max_risk_class": "MUTATING", "max_single_spend_usd": 1200.0},
            budget_limit=2500.0,
            token_budget=1500000,
            tool_budget=600,
            autonomy_level=3,
            manager_id="CHIEF_OPERATING_OFFICER"
        )
        employee_template_registry.create_template(template)

        # 4. AI CEO Workforce Discovery & Decision
        decision = ceo_workforce_controller.plan_and_assign_mission(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            objective="Optimize Q4 direct room revenue and adjust BAR rates",
            required_capabilities=["DYNAMIC_PRICING", "YIELD_MANAGEMENT"],
            department="OPERATIONS",
            budget_usd=1500.0,
            project_id="proj_jaipur_q4_expansion",
            force_create_template=tmpl_id
        )
        self.assertIsNotNone(decision.created_employee_id)
        emp_id = decision.created_employee_id

        # 5. Verify Employee Factory Provisioned and Activated the Employee
        emp = ai_employee_registry.get_employee(emp_id)
        self.assertIsNotNone(emp)
        self.assertTrue(emp.is_operational())
        self.assertEqual(emp.lifecycle_state, EmployeeLifecycleState.ACTIVE)
        self.assertEqual(emp.department_id, "OPERATIONS")

        # 6. Form Colleague Mission Team: Template Employee + Pre-built Specialists
        team = workforce_collaboration_hub.form_mission_team(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id=decision.mission_id,
            team_name="Royal Hotel Jaipur Revenue Optimization Taskforce",
            mission_lead_employee_id=emp_id,
            specialist_members=[
                emp_id,
                "specialist_Research_Specialist",
                "specialist_Data_Analyst",
                "specialist_Browser_Robot"
            ],
            chief_supervisor="CHIEF_OPERATING_OFFICER",
            collaboration_mode="HYBRID"
        )
        self.assertEqual(team.mission_lead_employee_id, emp_id)
        self.assertEqual(team.chief_supervisor, "CHIEF_OPERATING_OFFICER")

        # 7. Record Verified Business Outcome & KPI Measurement
        # (Settled Revenue = ₹10,50,000, exceeding ₹10,00,000 target!)
        # Query registered KPI
        with engine.connection(workload=WorkloadType.READ) as conn:
            kpi_row = conn.execute("SELECT kpi_id FROM employee_kpis WHERE employee_id = ?", (emp_id,)).fetchone()
            kpi_id = kpi_row["kpi_id"]

        measurement_res = kpi_kra_engine.record_measurement(
            kpi_id=kpi_id,
            measured_value=1050000.0,
            verification_proof={
                "source": "PMS_SETTLED_LEDGER",
                "bank_settlement_ref": "HDFC_BATCH_99214A",
                "audited_by": "NightAuditService"
            },
            mission_id=decision.mission_id
        )
        self.assertEqual(measurement_res["status"], "TARGET_MET")
        self.assertEqual(measurement_res["variance"], 50000.0)

        # 8. CEO Observability: Evaluate Performance Health
        performance = kpi_kra_engine.evaluate_employee_performance(emp_id)
        self.assertEqual(performance["health"], "PERFORMING")
        self.assertEqual(performance["targets_met"], 1)
        self.assertEqual(performance["score"], 100.0)

        # 9. Cryptographic Audit Proof: Verify Evidence Ledger
        with engine.connection(workload=WorkloadType.READ) as conn:
            events = conn.execute(
                "SELECT event_type FROM merkle_evidence_events WHERE tenant_id = ? ORDER BY timestamp ASC",
                (self.tenant_id,)
            ).fetchall()
            event_types = [e["event_type"] for e in events]

        self.assertIn("EMPLOYEE_TEMPLATE_CREATED", event_types)
        self.assertIn("AI_EMPLOYEE_PROVISIONED_FROM_TEMPLATE", event_types)
        self.assertIn("CEO_WORKFORCE_DECISION_RECORDED", event_types)
        self.assertIn("MISSION_TEAM_FORMED", event_types)
        self.assertIn("KPI_MEASUREMENT_RECORDED", event_types)
