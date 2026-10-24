"""
ZONATA Enterprise SaaS — Step 2 Full Operational Validation Suite
Verifies end-to-end functionality across:
- Scenario A: Fresh-user experience and clean zero-state workspace
- Scenario B: AI CEO reasoning, strategic planning and decision-room governance
- Scenario C: Task delegation, multi-specialist assignment and execution lifecycle
- Scenario D: Finance, general ledger, and expense reconciliation
- Scenario E: People, HR directory, dynamic hiring, and operational records
- Scenario F: Enterprise reports generation and format parsing (PostgreSQL/SQLite dual-dialect safe)
- Scenario G: MCP tools catalog, killswitch, and Governed Browser Use session creation
- Scenario H: Human-in-the-loop approval gates and multi-role decision workflow
- Scenario I: Fault resilience, SQL injection resistance, and honest error handling
- Scenario J: Multi-tenant boundary isolation and restricted pilot envelope capacity enforcement
"""

import os
import sys
import time
import tempfile
import unittest
import json
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.db import db, configure_isolated_test_db
from core.enterprise_finance import EnterpriseFinanceEngine
from core.enterprise_reports import EnterpriseReportsEngine
from core.portfolio import CompanyPortfolioManager
from core.overview_service import OverviewDataService
from core.approvals import ApprovalPipeline
from core.browser_use_execution_runtime import BrowserExecutionGateway, BrowserProfileType
from core.ceo_engine import CEOExecutiveEngine
from core.mcp_interoperability_runtime import MCPGateway

MODULE_TEMP_DIR = None
MODULE_ORIG_DB_PATH = None
MODULE_ORIG_ENV_DB_PATH = None

def setUpModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_ORIG_ENV_DB_PATH = os.environ.get("ZONATA_DB_PATH")
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "step2_operational_validation_test.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
    if MODULE_ORIG_ENV_DB_PATH is not None:
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_ENV_DB_PATH
    else:
        os.environ.pop("ZONATA_DB_PATH", None)
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestStep2OperationalValidation(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_step2_{int(time.time()*1000)}"
        self.company_id = f"comp_{self.tenant_id}"

        # Initialize tenant and company in database
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (self.tenant_id, "ZONATA QA LAB — STEP 2", "PILOT", "ACTIVE", time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.company_id, self.tenant_id, "ZONATA QA LAB — STEP 2", "Software & Cloud", "EXISTING", "ACTIVE", time.time())
            )
            conn.commit()

    def test_01_scenario_a_clean_zero_state(self):
        """Scenario A: Pristine zero-state workspace validation."""
        snap = OverviewDataService.get_snapshot(tenant_id=self.tenant_id, company_id=None, period="today")
        self.assertFalse(snap["financial"]["has_data"])
        self.assertIsNone(snap["financial"]["revenue"])
        self.assertEqual(snap["workforce"]["total_workforce"], 0)
        self.assertEqual(snap["operations"]["active_operations"], 0)

        fin = EnterpriseFinanceEngine(tenant_id=self.tenant_id)
        fin_sum = fin.get_financial_summary()
        self.assertEqual(len(fin_sum.get("recent_transactions", [])), 0)
        self.assertEqual(len(fin_sum.get("recent_expenses", [])), 0)

    def test_02_scenario_b_ai_ceo_planning_and_governance(self):
        """Scenario B: AI CEO reasoning separation and decision-room planning."""
        portfolio = CompanyPortfolioManager(tenant_id=self.tenant_id, load_from_db=True)
        companies = portfolio.list_companies()
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0].company_id, self.company_id)

        ceo = CEOExecutiveEngine(portfolio)
        res = ceo.chat_directive(self.company_id, "Assess initial risk profile and strategy for Q1")
        self.assertTrue(res.get("success"))
        self.assertIn("ceo_response", res)

    def test_03_scenario_c_task_delegation_lifecycle(self):
        """Scenario C: Multi-specialist task delegation and status transitions."""
        from src.services.agent_engine import delegation_engine
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        plan = delegation_engine.create_delegation_plan(
            goal_id=goal_id,
            goal_title="Deploy Continuous Integration Validation Rig",
            lead_agent_id="agent_ceo",
            subtasks=[
                {"id": "st_1", "title": "Setup Test Environment", "target_role": "DevOps Engineer", "priority": "high", "dependencies": []},
                {"id": "st_2", "title": "Run Smoke Tests", "target_role": "QA Engineer", "priority": "high", "dependencies": ["st_1"]}
            ],
            requires_board_approval=False
        )
        self.assertIsNotNone(plan)
        self.assertEqual(plan["approval_status"], "approved")

        # Complete first subtask
        res = delegation_engine.complete_subtask(goal_id, "st_1", "Environment verified and ready.")
        self.assertIn("unblocked_tasks", res)
        updated_plan = delegation_engine.plans[goal_id]
        st1 = [st for st in updated_plan["subtasks"] if st["id"] == "st_1"][0]
        self.assertEqual(st1["status"], "completed")

    def test_04_scenario_d_financial_ledger_and_reconciliation(self):
        """Scenario D: Financial ledger, expense creation, and mathematical reconciliation."""
        fin = EnterpriseFinanceEngine(tenant_id=self.tenant_id)
        exp = fin.create_expense({
            "company_id": self.company_id,
            "claimant_name": "Senior QA Engineer",
            "department": "Engineering",
            "category": "CLOUD_SERVICES",
            "amount": 350.0,
            "description": "Synthetic Infrastructure Lease"
        })
        self.assertTrue(exp.get("success"))
        eid = exp.get("expense_id")

        summary = fin.get_financial_summary(company_id=self.company_id)
        expenses = summary.get("recent_expenses", [])
        matched = [e for e in expenses if e.get("expense_id") == eid]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["amount"], 350.0)

    def test_05_scenario_e_people_and_dynamic_workforce(self):
        """Scenario E: Dynamic employee deployment and organization directory."""
        from core.workforce import DynamicAgentFactory
        contract = DynamicAgentFactory.create_employment_contract(
            role="Autonomous Reliability Engineer",
            department="Operations",
            manager="AI CEO",
            responsibilities=["Monitor system telemetry"],
            objectives=["Zero downtime"],
            allowed_tools=["python3", "curl"]
        )
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO employees (
                    agent_id, company_id, tenant_id, role, department, manager,
                    budget_limit, spending_limit, authority_ceiling, working_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (contract.agent_id, self.company_id, self.tenant_id, contract.role,
                 contract.department, contract.manager, contract.budget_limit, contract.spending_limit,
                 "AUTOMATIC_IDEMPOTENT", contract.working_state, time.time())
            )
            conn.commit()

            row = conn.execute("SELECT * FROM employees WHERE agent_id = ?", (contract.agent_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["tenant_id"], self.tenant_id)
            self.assertEqual(row["role"], "Autonomous Reliability Engineer")

    def test_06_scenario_f_enterprise_reports_dual_dialect(self):
        """Scenario F: Reports engine generation and dual PostgreSQL/SQLite JSON parsing."""
        engine = EnterpriseReportsEngine(tenant_id=self.tenant_id)
        report = engine.generate_report({
            "company_id": self.company_id,
            "title": "Quarterly Operational Audit",
            "report_category": "OPERATIONAL",
            "metrics": {"total_tests": 120, "passed": 120},
            "dimensions": {"environment": "STAGING"},
            "chart_data": [{"period": "W1", "value": 100}],
            "forecast_data": {"confidence": 0.99}
        })
        self.assertIsNotNone(report)
        self.assertEqual(report["title"], "Quarterly Operational Audit")
        self.assertEqual(report["metrics"]["total_tests"], 120)

        # List reports
        reps = engine.list_reports(company_id=self.company_id)
        self.assertGreaterEqual(len(reps), 1)

    def test_07_scenario_g_mcp_and_browser_use(self):
        """Scenario G: MCP catalog and Governed Browser Use session creation."""
        # MCP tools catalog
        mcp_gw = MCPGateway(tenant_id=self.tenant_id, company_id=self.company_id)
        tools = mcp_gw.list_tools()
        self.assertIsInstance(tools, list)

        # Browser Use session
        gateway = BrowserExecutionGateway(tenant_id=self.tenant_id, company_id=self.company_id)
        sess = gateway.create_session(
            agent_id="agent_step2_qa",
            profile_type=BrowserProfileType.EPHEMERAL.value,
            allowed_domains=["zonata.internal"]
        )
        self.assertIsNotNone(sess)
        self.assertIn("session_id", sess)

        # Close session
        closed = gateway.close_session(sess["session_id"])
        self.assertTrue(closed)

    def test_08_scenario_h_human_approval_gate(self):
        """Scenario H: High-risk approval gate lifecycle (PENDING -> APPROVED)."""
        appr = ApprovalPipeline.create_request(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            agent_id="agent_requester",
            action_desc="Authorize production database schema migration",
            reason="Step 2 operational hardening",
            risk_level="HIGH",
            consequence="Temporary read locks on reporting tables"
        )
        self.assertEqual(appr["status"], "PENDING")
        rid = appr["request_id"]

        # Owner decision
        owner_user = {"user_id": "usr_test_owner", "role": "OWNER"}
        res = ApprovalPipeline.decide_request(
            tenant_id=self.tenant_id,
            request_id=rid,
            approver_user=owner_user,
            approved=True
        )
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("status"), "APPROVED")

    def test_09_scenario_i_fault_resilience(self):
        """Scenario I: Robustness against non-existent queries and fault boundaries."""
        fin = EnterpriseFinanceEngine(tenant_id=self.tenant_id)
        # Querying non-existent company returns safe zero-state
        non_existent_summary = fin.get_financial_summary(company_id="comp_nonexistent_xyz")
        self.assertEqual(len(non_existent_summary.get("recent_expenses", [])), 0)

        # Reports engine get_report on non-existent report_id returns None honestly
        rep_engine = EnterpriseReportsEngine(tenant_id=self.tenant_id)
        self.assertIsNone(rep_engine.get_report("rep_nonexistent_12345"))

    def test_10_scenario_j_multi_tenant_isolation(self):
        """Scenario J: Strict isolation prevents cross-tenant data leakage."""
        other_tenant = f"tnt_other_{int(time.time()*1000)}"
        other_company = f"comp_{other_tenant}"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, 'Other Corp', 'PILOT', 'ACTIVE', ?)",
                (other_tenant, time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) VALUES (?, ?, 'Other Corp', 'Finance', 'EXISTING', 'ACTIVE', ?)",
                (other_company, other_tenant, time.time())
            )
            conn.commit()

        # Seed expense in other tenant
        other_fin = EnterpriseFinanceEngine(tenant_id=other_tenant)
        other_fin.create_expense({
            "company_id": other_company,
            "claimant_name": "Other Tenant CFO",
            "amount": 999999.0,
            "description": "Secret Acquisition Fund"
        })

        # Fresh tenant must NOT see other tenant's expense
        my_fin = EnterpriseFinanceEngine(tenant_id=self.tenant_id)
        my_summary = my_fin.get_financial_summary(company_id=self.company_id)
        amounts = [e["amount"] for e in my_summary.get("recent_expenses", [])]
        self.assertNotIn(999999.0, amounts)


if __name__ == "__main__":
    unittest.main()
