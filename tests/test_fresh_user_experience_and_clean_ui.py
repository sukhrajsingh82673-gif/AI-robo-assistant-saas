"""
ZONATA Enterprise SaaS — Fresh User Experience, Clean UI & Mock-Data Elimination Qualification Suite
Step 1 Verification:
1. Fresh tenant workspace begins with zero fabricated records, zero mock transactions,
   zero fake balances, and zero synthetic employees or work orders.
2. Strict tenant scoping across Finance, Reports, Employees, Processes, and Overview APIs.
3. Zero cross-tenant data leakage (no 'tnt_sales_%' legacy pollution).
4. Frontend workspace integrity: zero hardcoded demo accounts, names, or mock figures.
"""

import os
import sys
import time
import tempfile
import unittest
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.db import db, configure_isolated_test_db
from core.enterprise_finance import EnterpriseFinanceEngine
from core.enterprise_reports import EnterpriseReportsEngine
from core.portfolio import CompanyPortfolioManager
from core.overview_service import OverviewDataService

MODULE_TEMP_DIR = None
MODULE_ORIG_DB_PATH = None
MODULE_ORIG_ENV_DB_PATH = None

def setUpModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_ORIG_ENV_DB_PATH = os.environ.get("ZONATA_DB_PATH")
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "fresh_user_experience_test.db")
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


class TestFreshUserExperienceAndCleanUI(unittest.TestCase):
    def setUp(self):
        self.fresh_tenant_id = f"tnt_fresh_{int(time.time()*1000)}"
        self.primary_tenant_id = "tnt_primary"

        # Ensure tenant exists in DB
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (self.fresh_tenant_id, "New Enterprise Customer", "PRO", "ACTIVE", time.time())
            )
            conn.commit()

    def test_01_fresh_tenant_finance_has_zero_mock_data(self):
        """Newly created tenant must have zero fake balance, zero transactions, and zero expenses."""
        fin = EnterpriseFinanceEngine(tenant_id=self.fresh_tenant_id)
        summary = fin.get_financial_summary()

        # Check Summary figures are strictly 0.0
        s = summary.get("summary", {})
        self.assertEqual(s.get("cash_position", 0.0), 0.0)
        self.assertEqual(s.get("accounts_receivable", 0.0), 0.0)
        self.assertEqual(s.get("accounts_payable", 0.0), 0.0)
        self.assertEqual(s.get("gross_revenue_mtd", 0.0), 0.0)
        self.assertEqual(s.get("expenses_mtd", 0.0), 0.0)
        self.assertEqual(s.get("operating_profit", 0.0), 0.0)

        # Chart of accounts balances must all be 0.0
        coa = summary.get("chart_of_accounts", [])
        self.assertGreater(len(coa), 0, "Standard Chart of Accounts structure should be initialized")
        for acc in coa:
            self.assertEqual(acc["balance"], 0.0, f"Account {acc['code']} {acc['name']} must have 0.0 initial balance")

        # Recent transactions and expenses must be empty
        txs = summary.get("recent_transactions", [])
        self.assertEqual(len(txs), 0, "Fresh tenant must have 0 recent transactions")
        exps = summary.get("recent_expenses", [])
        self.assertEqual(len(exps), 0, "Fresh tenant must have 0 recent expenses")

    def test_02_fresh_tenant_reports_are_empty(self):
        """Newly created tenant must have zero default or mock business reports."""
        rep_engine = EnterpriseReportsEngine(tenant_id=self.fresh_tenant_id)
        reports = rep_engine.list_reports()
        self.assertEqual(len(reports), 0, "Fresh tenant must not have synthetic reports")

    def test_03_fresh_tenant_workforce_is_empty(self):
        """Newly created tenant portfolio must not inherit workforce or companies from primary tenant."""
        portfolio = CompanyPortfolioManager(tenant_id=self.fresh_tenant_id, load_from_db=True)
        companies = portfolio.list_companies()
        self.assertEqual(len(companies), 0, "Fresh tenant must not inherit companies")

        summary = portfolio.get_portfolio_summary()
        self.assertEqual(summary.get("total_companies", 0), 0)
        self.assertEqual(summary.get("total_workforce", 0), 0)
        self.assertEqual(summary.get("total_revenue", 0.0), 0.0)

    def test_04_fresh_tenant_overview_snapshot_honest_empty_states(self):
        """Overview snapshot for fresh tenant must return has_data=False across all unconnected modules."""
        overview = OverviewDataService.get_snapshot(
            tenant_id=self.fresh_tenant_id,
            company_id=None,
            period="today"
        )

        fin = overview.get("financial", {})
        self.assertFalse(fin.get("has_data"), "Fresh tenant with 0 revenue must have financial.has_data=False")
        self.assertIsNone(fin.get("revenue"))
        self.assertIsNone(fin.get("expenses"))

        mkt = overview.get("marketing", {})
        self.assertFalse(mkt.get("has_data"), "Fresh tenant with 0 marketing integrations must have marketing.has_data=False")
        self.assertIsNone(mkt.get("spend"))
        self.assertEqual(mkt.get("channels", []), [])

        ops = overview.get("operations", {})
        self.assertFalse(ops.get("has_data"), "Fresh tenant with 0 processes must have operations.has_data=False")
        self.assertEqual(ops.get("active_operations", 0), 0)
        self.assertEqual(ops.get("completed_operations", 0), 0)

        cust = overview.get("customers", {})
        self.assertFalse(cust.get("has_data"), "Fresh tenant with 0 customers must have customers.has_data=False")
        self.assertIsNone(cust.get("total_customers"))

        wf = overview.get("workforce", {})
        self.assertFalse(wf.get("has_data"), "Fresh tenant with 0 employees must have workforce.has_data=False")
        self.assertEqual(wf.get("total_workforce", 0), 0)
        self.assertEqual(wf.get("human_workforce", 0), 0)

    def test_05_no_cross_tenant_pollution_from_test_tenants(self):
        """Verify that data created with 'tnt_sales_%' prefix does not leak into any other tenant."""
        sales_tenant_id = f"tnt_sales_fixture_{int(time.time())}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, 'Sales Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (sales_tenant_id, time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) VALUES ('comp_test', ?, 'Test Sales Corp', 'Sales', 'EXISTING', 'ACTIVE', ?)",
                (sales_tenant_id, time.time())
            )
            # Seed a record in sales_leads and business_causality_chains under tnt_sales_*
            conn.execute("""
            INSERT OR IGNORE INTO sales_leads (
                lead_id, tenant_id, company_id, contact_name, channel, intent, status, qualification_score, created_at
            ) VALUES ('lead_leak_test', ?, 'comp_test', 'Rogue Prospect', 'DIRECT', 'Enterprise Inquiry', 'QUALIFIED', 0.95, ?)
            """, (sales_tenant_id, time.time()))

            conn.execute("""
            INSERT OR IGNORE INTO business_causality_chains (
                chain_id, tenant_id, company_id, strategy_goal, mission_id, revenue_attributed, cost_attributed, verified_outcome, transaction_id, created_at
            ) VALUES ('chain_leak_test', ?, 'comp_test', 'Rogue Revenue', 'msn_test', 999999.0, 0.0, 'PROVED', 'tx_test', ?)
            """, (sales_tenant_id, time.time()))
            conn.commit()

        # Query overview for fresh tenant - must NOT see rogue revenue or rogue leads
        snap = OverviewDataService.get_snapshot(
            tenant_id=self.fresh_tenant_id,
            company_id=None,
            period="today"
        )
        fin = snap.get("financial", {})
        self.assertFalse(fin.get("has_data"), "Rogue causality record must NOT leak into fresh tenant")
        self.assertIsNone(fin.get("revenue"))

        sales = snap.get("sales", {})
        self.assertFalse(sales.get("has_data"), "Rogue sales lead must NOT leak into fresh tenant")
        self.assertIsNone(sales.get("total_leads"))

    def test_06_frontend_workspaces_contain_zero_mock_demo_fixtures(self):
        """Frontend JS files must not contain hardcoded demo accounts, names, or fake metrics."""
        web_dir = os.path.join(BASE_DIR, "web")

        forbidden_patterns = [
            (r'HDFC Treasury', "web/finance_workspace.js"),
            (r'Stripe Escrow', "web/finance_workspace.js"),
            (r'value="Sukhraj Singh"', "web/finance_workspace.js"),
            (r'Priya Sharma', "web/people_workspace.js"),
            (r'Aman Verma', "web/people_workspace.js"),
            (r'Rajesh Khanna', "web/people_workspace.js"),
            (r'WO-8821', "web/operations_workspace.js"),
            (r'WO-8822', "web/operations_workspace.js"),
            (r'Burn to date: <strong>₹420\.00</strong>', "web/workforce_workspace.js"),
        ]

        for pattern, rel_path in forbidden_patterns:
            full_path = os.path.join(web_dir, os.path.basename(rel_path))
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            matches = re.findall(pattern, content)
            self.assertEqual(len(matches), 0, f"Found forbidden mock pattern '{pattern}' in {rel_path}")

    def test_07_expense_creation_and_reconciliation_isolated_by_tenant(self):
        """Filing an expense in a fresh tenant persists strictly in that tenant's ledger."""
        fin = EnterpriseFinanceEngine(tenant_id=self.fresh_tenant_id)
        exp_res = fin.create_expense({
            "claimant_name": "Dr. Alice Smith",
            "department": "Engineering",
            "category": "SOFTWARE",
            "amount": 2500.0,
            "description": "API Gateway Compute Subscription"
        })
        self.assertTrue(exp_res.get("success"))

        # Verify summary in fresh tenant reflects the expense
        summary = fin.get_financial_summary()
        self.assertEqual(len(summary.get("recent_expenses", [])), 1)
        self.assertEqual(summary["recent_expenses"][0]["claimant_name"], "Dr. Alice Smith")
        self.assertEqual(summary["recent_expenses"][0]["amount"], 2500.0)

        # Verify another tenant (primary) does NOT see this expense
        primary_fin = EnterpriseFinanceEngine(tenant_id="tnt_other_isolated")
        primary_summary = primary_fin.get_financial_summary()
        self.assertEqual(len(primary_summary.get("recent_expenses", [])), 0)


if __name__ == "__main__":
    unittest.main()
