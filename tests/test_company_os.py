"""
RoboAssistant Company OS 1.0 — Architecture & Governance Test Suite
Verifies Multi-Tenancy, IAM, Control Units, Approvals, Epistemic Truth,
Budget Hierarchies, Outcomes, Memory Isolation, Model Gateway, Digital Twin,
Connectors, Agent Bus, Governed Evolution, and Overnight Shift.
"""

import os
import sys
import unittest
import time
import uuid
import tempfile

sys.path.insert(0, "/roboassistant")

from core.db import db, configure_isolated_test_db
from core.auth import TenantManager, UserManager, AuthorizationEnforcer, UserRole

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "company_os_test_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()

from core.knowledge_graph import CompanyKnowledgeGraph, TruthState
from core.departments import DepartmentControlUnit
from core.approvals import ApprovalPipeline
from core.financials import BudgetHierarchyEngine
from core.outcomes import BusinessOutcomeEngine
from core.intelligence import OpportunityEngine, RiskEngine
from core.memory import OrganizationalMemory, MemoryTier, MemoryType
from core.billing import UsageMeteringEngine
from core.portfolio import CompanyPortfolioManager, CompanyOnboardingEngine
from core.model_gateway import ModelGateway, ModelTier, ModelProvider
from core.digital_twin import DigitalTwinSimulator, SimulationState
from core.connectors import HospitalityPMSConnector, AccountingConnector, ConnectorPermission
from core.agent_bus import AgentCommunicationBus, GovernedAgentMessage, MessagePriority
from core.evolution import SelfEvolutionPipeline, UpgradeStage
from core.night_shift import OvernightOperationsEngine

class TestRoboAssistantCompanyOS(unittest.TestCase):

    def setUp(self):
        self.tenant = TenantManager.create_tenant(f"Apex Enterprise Corp {uuid.uuid4().hex[:6]}")
        self.tenant_id = self.tenant["tenant_id"]
        self.owner = UserManager.create_user(self.tenant_id, f"owner_{uuid.uuid4().hex[:6]}@apex.corp", "Chief Executive", UserRole.OWNER)
        self.manager = UserManager.create_user(self.tenant_id, f"ops_{uuid.uuid4().hex[:6]}@apex.corp", "Ops Lead", UserRole.MANAGER)
        self.observer = UserManager.create_user(self.tenant_id, f"auditor_{uuid.uuid4().hex[:6]}@apex.corp", "Auditor", UserRole.AUDITOR)

        # Register a unique valid company in the relational schema
        self.comp_id = f"comp_{uuid.uuid4().hex[:12]}"
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO companies (
                    company_id, tenant_id, name, industry, company_type, status,
                    revenue, cost, contribution, understanding_pct, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (self.comp_id, self.tenant_id, "Apex Precision Corp", "Manufacturing", "NEW", "OPERATIONAL", 0.0, 0.0, 0.0, 100.0, time.time())
            )
            conn.commit()

    def test_01_multi_tenant_isolation_and_tokens(self):
        """Test token signing, verification, and tenant boundary enforcement."""
        token = UserManager.generate_token(self.owner)
        self.assertIsNotNone(token)

        payload = UserManager.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], self.owner["user_id"])
        self.assertEqual(payload["tenant_id"], self.tenant_id)

        # Cross-tenant boundary check
        foreign_tenant_id = "tnt_foreign_xyz"
        self.assertFalse(AuthorizationEnforcer.require_tenant(payload, foreign_tenant_id))
        self.assertTrue(AuthorizationEnforcer.require_tenant(payload, self.tenant_id))

    def test_02_epistemic_truth_and_knowledge_graph(self):
        """Verify knowledge facts, truth states, and company baseline generation."""
        f1 = CompanyKnowledgeGraph.assert_fact(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            category="IDENTITY",
            subject="company",
            predicate="legal_name",
            object_val="Apex Precision Ltd",
            truth_state=TruthState.MEASURED
        )
        self.assertIsNotNone(f1)

        f2 = CompanyKnowledgeGraph.assert_fact(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            category="FINANCIAL",
            subject="financials",
            predicate="revenue",
            object_val="₹ 1,500,000.00",
            truth_state=TruthState.MEASURED
        )
        self.assertIsNotNone(f2)

        baseline = CompanyKnowledgeGraph.get_company_baseline(self.tenant_id, self.comp_id)
        self.assertEqual(baseline["total_facts"], 2)
        self.assertEqual(baseline["measured_facts_count"], 2)
        self.assertEqual(baseline["revenue_truth_state"], TruthState.MEASURED)
        self.assertEqual(baseline["status"], "HEALTHY")

    def test_03_department_control_units(self):
        """Verify Department Control Units creation and hierarchical attributes."""
        dept = DepartmentControlUnit.create_department(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            name="Precision Engineering",
            manager_agent_id="agt_director_eng",
            budget_limit=250000.0,
            spending_limit=50000.0
        )
        self.assertIsNotNone(dept["department_id"])
        self.assertEqual(dept["name"], "Precision Engineering")

        depts = DepartmentControlUnit.list_departments(self.tenant_id, self.comp_id)
        self.assertEqual(len(depts), 1)
        self.assertEqual(depts[0]["budget_limit"], 250000.0)

    def test_04_first_class_approvals_pipeline(self):
        """Verify end-to-end approval lifecycle and authority verification."""
        req = ApprovalPipeline.create_request(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            agent_id="agt_machinist_01",
            action_desc="Re-tool spindle CNC machine 3",
            reason="Tolerance drift detected in turbine blade batch",
            risk_level="HIGH",
            consequence="Temporary line stop for 30 minutes"
        )
        self.assertEqual(req["status"], "PENDING")

        # Manager cannot approve high-risk governance mutations
        res_fail = ApprovalPipeline.decide_request(
            tenant_id=self.tenant_id,
            request_id=req["request_id"],
            approver_user=self.manager,
            approved=True
        )
        self.assertFalse(res_fail["success"])
        self.assertIn("INSUFFICIENT_PERMISSIONS", res_fail["error"])

        # Owner can approve and generate signed cryptographic grant hash
        res_ok = ApprovalPipeline.decide_request(
            tenant_id=self.tenant_id,
            request_id=req["request_id"],
            approver_user=self.owner,
            approved=True
        )
        self.assertTrue(res_ok["success"])
        self.assertEqual(res_ok["status"], "APPROVED")
        self.assertTrue(res_ok["signed_grant_hash"].startswith("GRANT_"))

    def test_05_budget_hierarchy_and_alert_thresholds(self):
        """Verify hierarchical budget limits and automated threshold alerts."""
        # Valid hierarchy: Company (100k) > Dept (50k) > Emp (10k) > Mission (2k)
        val = BudgetHierarchyEngine.validate_allocation(100000.0, 50000.0, 10000.0, 2000.0)
        self.assertTrue(val["valid"])

        # Invalid hierarchy: Dept (60k) exceeds Company (50k)
        invalid = BudgetHierarchyEngine.validate_allocation(50000.0, 60000.0, 10000.0, 2000.0)
        self.assertFalse(invalid["valid"])
        self.assertIn("BUDGET_CEILING_VIOLATION", invalid["error"])

        # Alert thresholds: 75% -> NOTICE, 95% -> HIGH_WARNING, 105% -> CRITICAL_HALT
        t1 = BudgetHierarchyEngine.check_spend_threshold(7500.0, 10000.0)
        self.assertEqual(t1["alert_level"], "NOTICE")
        self.assertTrue(t1["can_proceed"])

        t2 = BudgetHierarchyEngine.check_spend_threshold(9500.0, 10000.0)
        self.assertEqual(t2["alert_level"], "HIGH_WARNING")
        self.assertTrue(t2["can_proceed"])

        t3 = BudgetHierarchyEngine.check_spend_threshold(10500.0, 10000.0)
        self.assertEqual(t3["alert_level"], "CRITICAL_HALT")
        self.assertFalse(t3["can_proceed"])

    def test_06_business_outcomes_vs_task_success(self):
        """Verify strict distinction: TASK_SUCCESS != BUSINESS_OUTCOME."""
        eval_res = BusinessOutcomeEngine.evaluate_mission_outcome(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            mission_id="msn_rev_01",
            task_success=True,
            expected_metric={"metric": "recovered_revenue", "value": 50000.0},
            actual_measured_metric={"metric": "recovered_revenue", "value": 48000.0},
            verified_evidence_metric={"metric": "recovered_revenue", "value": 46500.0}
        )
        self.assertTrue(eval_res["task_success"])
        self.assertEqual(eval_res["outcome_status"], "VERIFIED_PARTIAL")
        self.assertEqual(eval_res["variance_pct"], -7.0)

    def test_07_opportunity_risk_and_layered_memory(self):
        """Verify intelligence discovery and organizational memory isolation."""
        opp = OpportunityEngine.register_opportunity(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            title="Consolidate duplicate cloud database replicas",
            evidence="Audit log indicates 2 unused standby PostgreSQL clusters",
            potential_impact="₹ 35,000 monthly cost reduction",
            confidence=0.92
        )
        self.assertEqual(opp["status"], "DISCOVERED")

        rsk = RiskEngine.register_risk(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            title="Single point of failure on supplier API",
            evidence="Vendor latency spiked past 12,000ms three times today",
            potential_impact="Order processing blackout",
            severity=0.85
        )
        self.assertEqual(rsk["status"], "DISCOVERED")

        # Layered Memory Storage
        mem_id = OrganizationalMemory.store_memory(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            memory_tier=MemoryTier.COMPANY,
            memory_type=MemoryType.LESSON,
            content="Never issue mass invoice updates without preliminary dry-run reconciliation."
        )
        self.assertIsNotNone(mem_id)

        mems = OrganizationalMemory.query_memory(self.tenant_id, company_id=self.comp_id)
        self.assertGreater(len(mems), 0)

    def test_08_metered_billing_usage(self):
        """Verify input/output token recording and provider cost calculations."""
        UsageMeteringEngine.record_usage(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            agent_id="agt_analyst",
            mission_id="msn_001",
            model="claude-3-7-sonnet",
            input_tokens=1500,
            output_tokens=600,
            cost=0.0135
        )
        summary = UsageMeteringEngine.get_tenant_usage_summary(self.tenant_id)
        self.assertEqual(summary["total_input_tokens"], 1500)
        self.assertEqual(summary["total_output_tokens"], 600)
        self.assertEqual(summary["total_cost"], 0.0135)
        self.assertEqual(summary["total_calls"], 1)

    def test_09_model_gateway_orchestration(self):
        """Verify Model Gateway dynamic model routing and token cost tracking."""
        res = ModelGateway.dispatch_inference(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            agent_id="agt_strategist",
            mission_id="msn_strat_01",
            prompt="Analyze quarterly variance in night audit reconciliation.",
            model_id="claude-3-7-sonnet"
        )
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["model"], "claude-3-7-sonnet")
        self.assertEqual(res["provider"], ModelProvider.ANTHROPIC)
        self.assertGreater(res["input_tokens"], 0)
        self.assertGreater(res["cost"], 0.0)

    def test_10_company_digital_twin_simulation(self):
        """Verify Digital Twin simulation produces SIMULATED label and impact forecasts."""
        context = {
            "name": "Apex Precision Corp",
            "revenue": 500000.0,
            "cost": 200000.0,
            "departments": ["Precision Engineering", "Operations"]
        }
        sim = DigitalTwinSimulator.simulate_mission_execution(
            company_context=context,
            proposed_action="Execute automated inventory restock",
            target_department="Operations",
            estimated_budget=15000.0,
            authority_required="AUTOMATIC_IDEMPOTENT"
        )
        self.assertEqual(sim["state_label"], SimulationState.SIMULATED)
        self.assertEqual(sim["estimated_cost"], 15000.0)
        self.assertEqual(sim["forecast_total_cost"], 215000.0)
        self.assertTrue(sim["rollback_availability"])
        self.assertIn("SIMULATION ONLY", sim["warning"])

    def test_11_enterprise_connector_fabric(self):
        """Verify enterprise connector handshake and READ_ONLY_VISIBILITY enforcement."""
        pms = HospitalityPMSConnector()
        self.assertFalse(pms.connected)
        self.assertEqual(pms.permission_level, ConnectorPermission.READ_ONLY_VISIBILITY)

        # Connect with credentials hash
        success = pms.connect({"token_hash": "sha256_mock_opera_token"})
        self.assertTrue(success)
        self.assertTrue(pms.connected)

        records = pms.fetch_night_audit_records()
        self.assertFalse(records["ledger_verified"])
        self.assertFalse(records.get("is_mock"))
        self.assertEqual(records.get("code"), "NOT_CONFIGURED")
        self.assertEqual(records.get("execution_mode"), "DISCONNECTED")
        self.assertEqual(records["permission"], ConnectorPermission.READ_ONLY_VISIBILITY)
        self.assertEqual(records.get("folios"), [])

        acc = AccountingConnector()
        acc.connect({"token_hash": "sha256_mock_tally_token"})
        gl = acc.fetch_general_ledger()
        # No simulated ledger values: unconfigured connector reports honestly.
        self.assertEqual(gl.get("code"), "NOT_CONFIGURED")
        self.assertEqual(gl.get("accounts_reconciled"), 0)
        self.assertEqual(gl.get("entries"), [])

    def test_12_inter_agent_communication_bus(self):
        """Verify governed agent messaging and blocking of privilege escalation attempts."""
        bus = AgentCommunicationBus()
        legit_msg = GovernedAgentMessage(
            sender_id="ceo_core",
            receiver_id="agt_director_eng",
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            purpose="Request CNC telemetry report",
            payload={"action": "query_metrics"},
            priority=MessagePriority.NORMAL
        )
        dispatch_ok = bus.dispatch_message(legit_msg)
        self.assertTrue(dispatch_ok["success"])
        self.assertEqual(dispatch_ok["message"]["status"], "DELIVERED")

        # Security invariant: Agent attempting privilege escalation through chat payload
        malicious_msg = GovernedAgentMessage(
            sender_id="agt_machinist_01",
            receiver_id="ceo_core",
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            purpose="Request elevation",
            payload={"command": "escalate_privilege to ADMIN"},
            priority=MessagePriority.EMERGENCY
        )
        dispatch_fail = bus.dispatch_message(malicious_msg)
        self.assertFalse(dispatch_fail["success"])
        self.assertIn("SECURITY_VIOLATION", dispatch_fail["error"])

    def test_13_governed_self_evolution_pipeline(self):
        """Verify self-evolution pipeline requires dual human control for governance code."""
        # Proposal targeting a protected governance kernel file
        prop = SelfEvolutionPipeline.submit_proposal(
            tenant_id=self.tenant_id,
            proposer_agent_id="agt_kernel_optimizer",
            target_component="control_kernel.py",
            patch_description="Optimize mutual exclusion lock release",
            diff_payload="--- a/control_kernel.py\n+++ b/control_kernel.py"
        )
        self.assertTrue(prop["governance_protected_target"])
        self.assertTrue(prop["requires_dual_human_control"])

        audited = SelfEvolutionPipeline.execute_audit_stages(prop)
        self.assertEqual(audited["stage"], UpgradeStage.DUAL_CONTROL)

        # Single approver must fail on protected governance target
        single_res = SelfEvolutionPipeline.authorize_and_activate(audited, approver_one=self.owner, approver_two=None)
        self.assertFalse(single_res["success"])
        self.assertIn("DUAL_CONTROL_VIOLATION", single_res["error"])

        # Dual distinct executive approvers succeed and yield rollback package
        co_founder = {"user_id": "usr_cofounder_02", "role": UserRole.EXECUTIVE}
        dual_res = SelfEvolutionPipeline.authorize_and_activate(audited, approver_one=self.owner, approver_two=co_founder)
        self.assertTrue(dual_res["success"])
        self.assertEqual(dual_res["stage"], UpgradeStage.ACTIVATED)
        self.assertTrue(dual_res["rollback_package"]["can_restore"])

    def test_14_night_shift_and_executive_morning_meeting(self):
        """Verify Overnight shift execution and 10-point Executive Morning Meeting generation."""
        missions = [
            {"mission_id": "m1", "status": "SUCCESS"},
            {"mission_id": "m2", "status": "SUCCESS"},
            {"mission_id": "m3", "status": "BLOCKED"}
        ]
        overnight = OvernightOperationsEngine.execute_night_shift(
            tenant_id=self.tenant_id,
            company_id=self.comp_id,
            active_missions=missions,
            employees_count=4
        )
        self.assertEqual(overnight["completed_missions_count"], 2)
        self.assertEqual(overnight["blocked_missions_count"], 1)
        self.assertEqual(overnight["governance_violations"], 0)

        agenda = OvernightOperationsEngine.generate_executive_morning_meeting(
            company_name="Apex Precision Corp",
            overnight_summary=overnight,
            unresolved_approvals_count=1,
            discovered_opportunities=["Consolidate cloud storage volume replicas"]
        )
        self.assertEqual(len(agenda["questions"]), 10)
        self.assertEqual(agenda["questions"][0]["question"], "What happened?")
        self.assertEqual(agenda["questions"][9]["question"], "What does the CEO recommend next?")
        self.assertIn("NOT automatically executed", agenda["rule"])

if __name__ == "__main__":
    unittest.main()
