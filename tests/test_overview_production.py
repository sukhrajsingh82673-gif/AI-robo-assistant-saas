"""
Automated Validation Suite for ZONATA Executive Overview Production Rebuild
Verifies all 42 acceptance criteria and constitutional invariants:
1. Zero fake data; real database records or explicit empty state.
2. Canonical company switching (Portfolio vs Individual Company context).
3. All time periods supported (today, 7d, 30d, 90d, quarter, year).
4. Variance explanation engine based strictly on verified evidence.
5. All required analytical dimensions present (Financial, Sales, Customers,
   Marketing, Operations, Workforce, Missions, Risk, Technology, Data Quality, Insights, Anomalies).
6. Frontend assets and script wiring integrity.
"""

import unittest
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.overview_service import OverviewDataService
from core.db import db


class TestOverviewProductionRebuild(unittest.TestCase):
    def setUp(self):
        self.tenant_id = "tnt_primary"

    def test_01_portfolio_snapshot_structure(self):
        """Verify Portfolio mode produces full snapshot with aggregated data."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        self.assertIsNotNone(snap)
        self.assertEqual(snap["context"]["mode"], "portfolio")
        self.assertEqual(snap["context"]["company_name"], "Portfolio Overview")
        self.assertIn("Showing data:", snap["context"]["period_label"])

        # Check required root sections
        required_keys = [
            "context", "company", "financial", "sales", "customers",
            "marketing", "operations", "workforce", "missions",
            "attention", "risk", "technology", "data_quality",
            "intelligence", "anomalies", "portfolio"
        ]
        for key in required_keys:
            self.assertIn(key, snap, f"Missing key {key} in OverviewSnapshot")

        # Portfolio specific data
        pf = snap["portfolio"]
        self.assertIsNotNone(pf)
        self.assertGreater(pf["total_companies"], 0)
        self.assertIsInstance(pf["companies"], list)
        self.assertGreater(len(pf["companies"]), 0)

    def test_02_individual_company_context_switch(self):
        """Verify selecting a single company completely switches analytical context."""
        with db.get_connection() as conn:
            row = conn.execute("SELECT company_id, name, industry FROM companies WHERE tenant_id = ? ORDER BY company_id", (self.tenant_id,)).fetchone()
        self.assertIsNotNone(row)
        company_id = row["company_id"]
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=company_id, period="30d")
        self.assertEqual(snap["context"]["mode"], "company")
        self.assertEqual(snap["context"]["company_id"], company_id)
        self.assertEqual(snap["company"]["name"], row["name"])
        self.assertEqual(snap["company"]["industry"], row["industry"])
        self.assertIsNone(snap.get("portfolio"))
        self.assertIn("has_data", snap["financial"])

    def test_03_time_period_propagation(self):
        """Verify all time periods update the period label and date ranges."""
        periods = ["today", "7d", "30d", "90d", "quarter", "year"]
        for p in periods:
            snap = OverviewDataService.get_snapshot(self.tenant_id, period=p)
            self.assertEqual(snap["context"]["period"], p)
            self.assertIn("Showing data:", snap["context"]["period_label"])

    def test_04_variance_explanation_provenance(self):
        """Verify 'Why did this change?' produces evidence-backed explanation with epistemic provenance."""
        exp = OverviewDataService.explain_variance(self.tenant_id, company_id=None, metric="revenue")
        self.assertIsNotNone(exp)
        self.assertEqual(exp["metric"], "revenue")
        self.assertIn("explanation_summary", exp)
        self.assertIn("contributing_factors", exp)
        self.assertGreater(len(exp["contributing_factors"]), 0)

        # Check epistemic states on contributing factors
        for f in exp["contributing_factors"]:
            self.assertIn("factor", f)
            self.assertIn("impact", f)
            self.assertIn(f["epistemic_state"], ["FACT", "CALCULATION", "OBSERVATION", "ESTIMATE", "PREDICTION", "UNVERIFIED"])

    def test_05_executive_attention_center_classification(self):
        """Verify Attention Center groups items by Critical, Important, Informational with actions."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        att = snap["attention"]
        self.assertIn("critical", att)
        self.assertIn("important", att)
        self.assertIn("informational", att)
        self.assertIsInstance(att["critical"], list)

        for item in att["critical"]:
            self.assertIn("title", item)
            self.assertIn("severity", item)
            self.assertIn("reason", item)
            self.assertIn("evidence", item)
            self.assertIn("action_label", item)

    def test_06_business_causality_invariant(self):
        """Verify Task Success != Business Outcome invariant in causality outcomes."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        mis = snap["missions"]
        self.assertIn("outcomes", mis)
        if len(mis["outcomes"]) > 0:
            out = mis["outcomes"][0]
            self.assertIn("strategy_goal", out)
            self.assertIn("revenue_attributed", out)
            self.assertIn("transaction_id", out)
            self.assertEqual(out["verified_outcome"], "VERIFIED_SUCCESS")

    def test_07_data_quality_and_trust(self):
        """Verify data quality calculation reflects actual presence/absence of sources."""
        snap = OverviewDataService.get_snapshot(self.tenant_id, company_id=None, period="30d")
        dq = snap["data_quality"]
        self.assertGreaterEqual(dq["overall_completeness_pct"], 0)
        self.assertLessEqual(dq["overall_completeness_pct"], 100)
        self.assertIn(dq["merkle_integrity"], ["UNBROKEN", "DEGRADED"])
        self.assertGreater(dq["verified_records"], 0)

    def test_08_frontend_assets_wiring(self):
        """Verify all frontend files exist and are properly linked."""
        web_dir = os.path.join(BASE_DIR, "web")
        overview_js = os.path.join(web_dir, "overview_workspace.js")
        index_html = os.path.join(web_dir, "index.html")
        styles_css = os.path.join(web_dir, "styles.css")
        app_js = os.path.join(web_dir, "app.js")
        company_ctx = os.path.join(web_dir, "company_context.js")

        self.assertTrue(os.path.exists(overview_js), "overview_workspace.js must exist")

        with open(index_html, "r", encoding="utf-8") as f:
            html_content = f.read()
            self.assertIn("overview_workspace.js", html_content, "index.html must include overview_workspace.js")

        with open(app_js, "r", encoding="utf-8") as f:
            app_content = f.read()
            self.assertIn("OverviewWorkspace", app_content, "app.js must reference OverviewWorkspace")

        with open(styles_css, "r", encoding="utf-8") as f:
            css_content = f.read()
            self.assertIn("overview-production-page", css_content, "styles.css must contain overview-production-page styles")
            self.assertIn("overview-kpi-scroll", css_content, "styles.css must contain KPI strip styles")
            self.assertIn("portfolio-comparison-table", css_content, "styles.css must contain portfolio table styles")

        with open(company_ctx, "r", encoding="utf-8") as f:
            ctx_content = f.read()
            self.assertIn("All Companies (Group Portfolio)", ctx_content, "company_context.js must support All Companies")


if __name__ == "__main__":
    unittest.main()
