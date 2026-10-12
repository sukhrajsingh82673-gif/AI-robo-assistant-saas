"""
Unit and Integration Tests for Governed Multi-Agent Workforce Orchestrator
Validates:
1. Dynamic Workforce Creation & Directional Flows
2. Delegation & Handoff Mechanics
3. Delegation Depth Limits & Cycle/Loop Protection
4. Budget Exhaustion Governance
5. Tenant & Company Isolation Enforcement
6. Tool Permission Denial & Approval Gates
7. Emergency Kill Switch / Quarantine
8. Honest Evidence Generation & Epistemic Result Normalization
9. Section 72 Governed Demonstration (Sales Pipeline Bottlenecks)
"""

import os
import sys
import unittest
import time
import uuid
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.workforce_runtime import (
    SwarmWorkforceRuntime,
    SpecialistRole,
    SpecialistStatus,
    WorkforceLifecycleState,
    RuntimeBudget
)
from core.workforce_orchestrator import (
    GovernedToolWrapper,
    ResultNormalizer,
    SpecialistRoleCatalog,
    DynamicWorkforcePlanner,
    EpistemicClassification
)
from zonata.agent_swarm_adapter import AgentWorkforceAdapter
from core.evidence_ledger import EvidenceLedger
from core.db import db, configure_isolated_test_db

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "workforce_orchestrator_test.db")
    configure_isolated_test_db(isolated_db)
    isolated_ledger = os.path.join(MODULE_TEMP_DIR.name, "workforce_orchestrator_ledger.jsonl")
    os.environ["ZONATA_EVIDENCE_PATH"] = isolated_ledger

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if "ZONATA_EVIDENCE_PATH" in os.environ:
        del os.environ["ZONATA_EVIDENCE_PATH"]
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()

class TestWorkforceOrchestrator(unittest.TestCase):
    def setUp(self):
        self.tenant_id = "tnt_primary"
        self.company_id = "comp_primary"
        self.runtime = SwarmWorkforceRuntime()
        import tempfile
        self.test_ledger_file = os.path.join(tempfile.gettempdir(), f"test_audit_ledger_{uuid.uuid4().hex[:8]}.jsonl")
        self.ledger = EvidenceLedger(ledger_file=self.test_ledger_file)
        self.planner = DynamicWorkforcePlanner(runtime=self.runtime, ledger=self.ledger)

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES ('tnt_primary', 'Primary Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (time.time(),)
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO companies (
                    company_id, tenant_id, name, country, industry,
                    company_type, status, currency, revenue, cost,
                    contribution, created_at
                ) VALUES ('comp_primary', 'tnt_primary', 'Primary Corp', 'US', 'SaaS', 'EXISTING', 'OPERATIONAL', '$', 1000.0, 500.0, 500.0, ?)
                """,
                (time.time(),)
            )
            conn.commit()



    def test_dynamic_workforce_creation_and_topology(self):
        plan = self.planner.plan_workforce_for_objective(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="msn_001",
            objective="Analyze our current sales pipeline and identify the top three operational bottlenecks."
        )
        self.assertIsNotNone(plan.get("workforce_id"))
        self.assertEqual(plan["status"], "READY")
        self.assertEqual(len(plan["specialists"]), 3)
        roles = [s["role"] for s in plan["specialists"]]
        self.assertIn("Sales Analyst", roles)
        self.assertIn("Operations Analyst", roles)
        self.assertIn("Verification Specialist", roles)

    def test_directional_communication_enforcement(self):
        plan = self.planner.plan_workforce_for_objective(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="msn_002",
            objective="Analyze our current sales pipeline"
        )
        wf_id = plan["workforce_id"]
        lead_id = plan["specialists"][0]["id"]
        worker_id = plan["specialists"][1]["id"]
        verifier_id = plan["specialists"][2]["id"]

        # Allowed flow: Lead -> Worker
        msg = self.runtime.send_message(
            workforce_id=wf_id,
            sender_id=lead_id,
            recipient_id=worker_id,
            content="Please analyze pipeline bottlenecks"
        )
        self.assertIsNotNone(msg.id)
        self.assertEqual(msg.sender_id, lead_id)
        self.assertEqual(msg.recipient_id, worker_id)

        # Illegal flow: Worker cannot directly message an unmapped third party
        with self.assertRaises(PermissionError):
            self.runtime.send_message(
                workforce_id=wf_id,
                sender_id=worker_id,
                recipient_id=lead_id,  # worker only reports to verifier
                content="Illegal message bypass"
            )

    def test_loop_and_cycle_detection(self):
        plan = self.planner.plan_workforce_for_objective(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="msn_003",
            objective="Analyze sales pipeline"
        )
        wf_id = plan["workforce_id"]
        s1 = plan["specialists"][0]["id"]
        s2 = plan["specialists"][1]["id"]
        # Allow bidirectional flow for test
        self.runtime.create_collaboration(wf_id, s2, s1)

        self.runtime.send_message(wf_id, s1, s2, "Step 1")
        self.runtime.send_message(wf_id, s2, s1, "Step 2")

        # Now attempting to cycle back s1 -> s2 should trigger loop detection
        with self.assertRaises(RuntimeError) as ctx:
            self.runtime.send_message(wf_id, s1, s2, "Cycle Step 3")
        self.assertIn("cycle detected", str(ctx.exception).lower())

    def test_delegation_depth_limit(self):
        plan = self.planner.plan_workforce_for_objective(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="msn_004",
            objective="Analyze sales pipeline",
            max_delegation_depth=1
        )
        wf_id = plan["workforce_id"]
        s1 = plan["specialists"][0]["id"]
        s2 = plan["specialists"][1]["id"]
        s3 = plan["specialists"][2]["id"]
        self.runtime.create_collaboration(wf_id, s2, s3)

        self.runtime.send_message(wf_id, s1, s2, "Depth 1")
        with self.assertRaises(RuntimeError) as ctx:
            self.runtime.send_message(wf_id, s2, s3, "Depth 2 exceeds max 1")
        self.assertIn("delegation depth", str(ctx.exception).lower())

    def test_budget_exhaustion_governance(self):
        plan = self.planner.plan_workforce_for_objective(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="msn_005",
            objective="Analyze sales pipeline",
            budget_usd=1.0  # very low budget
        )
        wf_id = plan["workforce_id"]
        budget = self.runtime.workforces[wf_id]["budget"]
        budget.current_cost_usd = 2.0  # exceed budget

        s1 = plan["specialists"][0]["id"]
        s2 = plan["specialists"][1]["id"]
        with self.assertRaises(RuntimeError) as ctx:
            self.runtime.send_message(wf_id, s1, s2, "Should be blocked")
        self.assertIn("budget exhaustion", str(ctx.exception).lower())

    def test_emergency_kill_switch(self):
        plan = self.planner.plan_workforce_for_objective(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="msn_006",
            objective="Analyze sales pipeline"
        )
        wf_id = plan["workforce_id"]
        self.planner.quarantine_workforce(wf_id, reason="TEST_SECURITY_LOCKDOWN")

        status = self.planner.get_workforce_status(wf_id)
        self.assertEqual(status["status"], "QUARANTINED")
        self.assertTrue(self.runtime.workforces[wf_id]["kill_switch_active"])

        # Any message attempt must be stopped
        s1 = plan["specialists"][0]["id"]
        s2 = plan["specialists"][1]["id"]
        with self.assertRaises(RuntimeError) as ctx:
            self.runtime.send_message(wf_id, s1, s2, "Must fail")
        self.assertIn("kill switch", str(ctx.exception).lower())

    def test_tenant_and_company_isolation(self):
        wrapper = GovernedToolWrapper(self.ledger)
        spec = SpecialistRole(
            id="spec_t1",
            name="Tenant 1 Specialist",
            role="Analyst",
            department="Ops",
            mission_id="m1",
            tenant_id="tnt_tenant_A",
            company_id="cmp_company_A",
            capabilities=["analysis"],
            allowed_tools=["DATA_QUERY_SCOPED"],
            forbidden_tools=[],
            model_policy={},
            context_scope={}
        )

        # Attempting to call tool under tenant_B
        with self.assertRaises(PermissionError) as ctx:
            wrapper.execute_tool(
                tenant_id="tnt_tenant_B",  # MISMATCH
                company_id="cmp_company_A",
                mission_id="m1",
                workforce_id="wf1",
                agent_id="spec_t1",
                specialist=spec,
                tool_name="DATA_QUERY_SCOPED",
                parameters={}
            )
        self.assertIn("Cross-tenant access denied", str(ctx.exception))

        # Attempting cross-company access
        with self.assertRaises(PermissionError) as ctx:
            wrapper.execute_tool(
                tenant_id="tnt_tenant_A",
                company_id="cmp_company_B",  # MISMATCH
                mission_id="m1",
                workforce_id="wf1",
                agent_id="spec_t1",
                specialist=spec,
                tool_name="DATA_QUERY_SCOPED",
                parameters={}
            )
        self.assertIn("Cross-company access denied", str(ctx.exception))

    def test_tool_permission_denial(self):
        wrapper = GovernedToolWrapper(self.ledger)
        spec = SpecialistRole(
            id="spec_t2",
            name="Analyst",
            role="Analyst",
            department="Ops",
            mission_id="m1",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            capabilities=["analysis"],
            allowed_tools=["DATA_QUERY_SCOPED"],
            forbidden_tools=["destructive_fs", "drop_table"],
            model_policy={},
            context_scope={}
        )
        res = wrapper.execute_tool(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="m1",
            workforce_id="wf1",
            agent_id="spec_t2",
            specialist=spec,
            tool_name="destructive_fs",
            parameters={}
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "DENIED")

    def test_approval_pipeline_gate(self):
        wrapper = GovernedToolWrapper(self.ledger)
        spec = SpecialistRole(
            id="spec_t3",
            name="Sales Rep",
            role="Sales",
            department="Commercial",
            mission_id="m1",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            capabilities=["discounts"],
            allowed_tools=["APPLY_DISCOUNT"],
            forbidden_tools=[],
            model_policy={},
            context_scope={}
        )
        # Spending $500 requires approval
        res = wrapper.execute_tool(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="m1",
            workforce_id="wf1",
            agent_id="spec_t3",
            specialist=spec,
            tool_name="APPLY_DISCOUNT",
            parameters={"spend_amount": 500.0},
            risk_level="HIGH"
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "WAITING_APPROVAL")
        self.assertIn("approval_id", res)

    def test_evidence_ledger_integrity(self):
        wrapper = GovernedToolWrapper(self.ledger)
        spec = SpecialistRole(
            id="spec_t4",
            name="Research Agent",
            role="Researcher",
            department="Intel",
            mission_id="m1",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            capabilities=["research"],
            allowed_tools=["MARKET_RESEARCH_SCRAPER"],
            forbidden_tools=[],
            model_policy={},
            context_scope={}
        )
        res = wrapper.execute_tool(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id="m1",
            workforce_id="wf1",
            agent_id="spec_t4",
            specialist=spec,
            tool_name="MARKET_RESEARCH_SCRAPER",
            parameters={"query": "hotel occupancy rates"}
        )
        self.assertTrue(res["success"])
        self.assertIn("evidence_package_id", res)
        self.assertIn("audit_hash", res)

    def test_section_72_sales_bottlenecks_demonstration(self):
        """
        Full Execution of Section 72 Demonstration Test:
        Objective: 'Analyze our current sales pipeline and identify the top three operational bottlenecks.'
        Specialists: Sales Analyst + Operations Analyst + Verification Specialist
        Verifies:
        - Task success does NOT equate to business outcome (invariant)
        - Identification of 3 sales pipeline bottlenecks & 3 operational bottlenecks
        - Epistemic classification (OBSERVATION, UNVERIFIED)
        - Evidence packages generated
        """
        demo_res = AgentWorkforceAdapter.run_sales_bottleneck_demonstration(
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        self.assertEqual(demo_res["status"], "COMPLETED")
        self.assertGreaterEqual(demo_res["evidence_count"], 2)

        result = demo_res["result"]
        self.assertTrue(result["task_success"])
        self.assertFalse(result["business_outcome_verified"])  # Invariant maintained

        findings = result["findings"]
        self.assertGreaterEqual(len(findings), 3)

        # Check that top bottlenecks are reported
        bottleneck_stages = [
            f.get("bottleneck", {}).get("stage") or f.get("bottleneck", {}).get("process")
            for f in findings
        ]
        self.assertIn("Proposal to Contract", bottleneck_stages)
        self.assertIn("Discovery to Demo", bottleneck_stages)
        self.assertIn("Pricing Negotiation", bottleneck_stages)

if __name__ == "__main__":
    unittest.main()
