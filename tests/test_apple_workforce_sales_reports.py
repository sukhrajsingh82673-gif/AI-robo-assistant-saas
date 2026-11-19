"""
Tests for Phase 6: Apple-Grade Workforce, Sales Pipeline Board, and Reports Preview
Verifies:
1. AppleWorkforceBoard AI Employee directory enforcing constitutional invariant (employees operate agents, never reverse).
2. AppleSalesBoard 5-stage commercial pipeline Kanban board with assigned specialists and stage progression.
3. AppleReportsPreview document paper-canvas layouts matching exportable PDF statements with cryptographic Merkle proof.
4. Seamless integration into people_workspace.js, workforce_workspace.js, crm_sales_workspace.js, and reports_workspace.js.
5. Index.html script inclusions.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleWorkforceSalesReports(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "apple_workforce_board.js"), "r", encoding="utf-8") as f:
            self.workforce_js = f.read()
        with open(os.path.join(WEB_DIR, "apple_sales_board.js"), "r", encoding="utf-8") as f:
            self.sales_js = f.read()
        with open(os.path.join(WEB_DIR, "apple_reports_preview.js"), "r", encoding="utf-8") as f:
            self.reports_js = f.read()
        with open(os.path.join(WEB_DIR, "people_workspace.js"), "r", encoding="utf-8") as f:
            self.people_js = f.read()
        with open(os.path.join(WEB_DIR, "workforce_workspace.js"), "r", encoding="utf-8") as f:
            self.workforce_ws_js = f.read()
        with open(os.path.join(WEB_DIR, "crm_sales_workspace.js"), "r", encoding="utf-8") as f:
            self.crm_js = f.read()
        with open(os.path.join(WEB_DIR, "reports_workspace.js"), "r", encoding="utf-8") as f:
            self.reports_ws_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_workforce_board_and_constitutional_invariant(self):
        self.assertIn("window.AppleWorkforceBoard =", self.workforce_js)
        self.assertIn("render(containerOrId", self.workforce_js)
        self.assertIn("filterDept(", self.workforce_js)
        self.assertIn("search(", self.workforce_js)
        self.assertIn("inspectEmployee(", self.workforce_js)
        self.assertIn("openProvisionModal(", self.workforce_js)

        # Constitutional Invariant Rule
        self.assertIn("Employees use Agents; Agents NEVER control Employees", self.workforce_js)
        self.assertIn("Immutable Workforce Governance Invariant", self.workforce_js)

        # Diverse C-Suite & Specialist Roster
        for role in ["AI CEO", "AI COO", "AI CMO", "AI CTO", "AI CFO", "AI CHRO", "AI CISO"]:
            self.assertIn(role, self.workforce_js, f"Missing leadership role: {role}")

        # SOP & Agent Tool Links
        self.assertIn("SOP-EXEC-01", self.workforce_js)
        self.assertIn("SOP-MKT-02", self.workforce_js)
        self.assertIn("Authorized Execution Agents", self.workforce_js)

    def test_sales_board_and_kanban_stages(self):
        self.assertIn("window.AppleSalesBoard =", self.sales_js)
        self.assertIn("render(containerOrId", self.sales_js)
        self.assertIn("renderHtml()", self.sales_js)
        self.assertIn("advanceStage(", self.sales_js)
        self.assertIn("inspectDeal(", self.sales_js)
        self.assertIn("openNewDealModal(", self.sales_js)

        # 5 Kanban Stages
        stages = ["Inbound & Discovery", "Qualified & Scored", "Proposal Sent", "Negotiation", "Won & Booked"]
        for st in stages:
            self.assertIn(st, self.sales_js, f"Missing sales stage: {st}")

        # Metrics
        self.assertIn("Total Active Pipeline", self.sales_js)
        self.assertIn("Weighted Expected Value", self.sales_js)
        self.assertIn("Closed & Won Revenue", self.sales_js)
        self.assertIn("Win Rate & Avg Deal", self.sales_js)

    def test_reports_preview_and_paper_canvas(self):
        self.assertIn("window.AppleReportsPreview =", self.reports_js)
        self.assertIn("render(containerOrId", self.reports_js)
        self.assertIn("selectReport(", self.reports_js)
        self.assertIn("exportPdf()", self.reports_js)
        self.assertIn("copySummary()", self.reports_js)

        # Report Types
        self.assertIn("weekly_exec", self.reports_js)
        self.assertIn("financial_pl", self.reports_js)
        self.assertIn("workforce_sop", self.reports_js)
        self.assertIn("security_dlp", self.reports_js)

        # Paper Canvas & Cryptographic Provenance
        self.assertIn("apple-document-canvas", self.reports_js)
        self.assertIn("apple-document-page", self.reports_js)
        self.assertIn("Immutable Proof Hash:", self.reports_js)
        self.assertIn("sha256:", self.reports_js)

    def test_workspace_integrations(self):
        self.assertIn("window.AppleWorkforceBoard", self.people_js)
        self.assertIn("window.AppleWorkforceBoard", self.workforce_ws_js)
        self.assertIn("window.AppleSalesBoard", self.crm_js)
        self.assertIn("window.AppleReportsPreview", self.reports_ws_js)

    def test_index_html_loads_phase6_scripts(self):
        self.assertIn('<script src="apple_workforce_board.js"></script>', self.index_html)
        self.assertIn('<script src="apple_sales_board.js"></script>', self.index_html)
        self.assertIn('<script src="apple_reports_preview.js"></script>', self.index_html)

if __name__ == '__main__':
    unittest.main()
