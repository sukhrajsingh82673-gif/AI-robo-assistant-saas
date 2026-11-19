"""
Tests for Phase 5: Apple-Grade Command Center & Departments
Verifies:
1. ActionCard & ApprovalCard 5-part AI action pattern with on-demand explainability ('Why?').
2. CEO Command Center Home cockpit (greeting, headline profit in --t-display, approvals strip, 6 departments, live activity).
3. Department Workspace template (tints, objectives, KPIs, work-in-progress, AI workforce with SOPs and agent tools, department-specific extras).
4. Integration into Overview Workspace with deep analytics collapsible toggle.
5. Index.html script inclusions.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleCommandCenter(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "ai_action_card.js"), "r", encoding="utf-8") as f:
            self.action_card_js = f.read()
        with open(os.path.join(WEB_DIR, "ceo_command_center.js"), "r", encoding="utf-8") as f:
            self.ceo_cc_js = f.read()
        with open(os.path.join(WEB_DIR, "department_workspace.js"), "r", encoding="utf-8") as f:
            self.dept_ws_js = f.read()
        with open(os.path.join(WEB_DIR, "overview_workspace.js"), "r", encoding="utf-8") as f:
            self.overview_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_action_card_and_approval_card(self):
        # Exports
        self.assertIn("window.ActionCard =", self.action_card_js)
        self.assertIn("window.ActionCard.openWhy =", self.action_card_js)
        self.assertIn("window.ActionCard.confirmHighRisk =", self.action_card_js)
        self.assertIn("window.ApprovalCard =", self.action_card_js)

        # 5-Part AI Action Pattern components
        self.assertIn("intent", self.action_card_js)
        self.assertIn("Reason:", self.action_card_js)
        self.assertIn("stateConfig", self.action_card_js)
        self.assertIn("Result:", self.action_card_js)
        self.assertIn("Undo (", self.action_card_js)
        self.assertIn("Why?", self.action_card_js)

        # Approval Card Risk Tiers
        self.assertIn("Low", self.action_card_js)
        self.assertIn("Medium", self.action_card_js)
        self.assertIn("High", self.action_card_js)
        self.assertIn("Worst Case:", self.action_card_js)
        self.assertIn("Cheaper Safe Alternative:", self.action_card_js)

    def test_ceo_command_center(self):
        self.assertIn("window.CeoCommandCenter =", self.ceo_cc_js)
        self.assertIn("render(container, snapshot)", self.ceo_cc_js)

        # Hero Greeting & Big Profit Metric in --t-display
        self.assertIn("Good day, Owner", self.ceo_cc_js)
        self.assertIn("t-display tabular-nums", self.ceo_cc_js)
        self.assertIn("This Month's Profit", self.ceo_cc_js)
        self.assertIn("Mini Sparkline", self.ceo_cc_js)

        # Needs You Approvals Strip
        self.assertIn("Needs You", self.ceo_cc_js)

        # Executive Departments Row
        for dept in ["COO", "CMO", "CTO", "CFO", "CHRO", "Security"]:
            self.assertIn(dept, self.ceo_cc_js, f"Missing department {dept} in CEO cockpit")

        # Key Numbers Performance Cards
        self.assertIn("Monthly Revenue", self.ceo_cc_js)
        self.assertIn("Operating Margin", self.ceo_cc_js)
        self.assertIn("Active Sales Leads", self.ceo_cc_js)
        self.assertIn("Conversion Rate", self.ceo_cc_js)

        # Live Activity Feed
        self.assertIn("Live Activity", self.ceo_cc_js)

    def test_department_workspace(self):
        self.assertIn("window.DepartmentWorkspace =", self.dept_ws_js)
        self.assertIn("render(containerOrId, deptId", self.dept_ws_js)
        self.assertIn("open(deptId", self.dept_ws_js)
        self.assertIn("close()", self.dept_ws_js)
        self.assertIn("inspectEmployee(", self.dept_ws_js)
        self.assertIn("askExecutive(", self.dept_ws_js)

        # Core Departments Supported
        for dept_id in ["coo", "cmo", "cto", "cfo", "chro", "security"]:
            self.assertIn(f"id: '{dept_id}'", self.dept_ws_js, f"Missing department config for {dept_id}")

        # Invariant Rule Check: Employees use agents, agents never use employees
        self.assertIn("Employees operate agents; agents never operate employees", self.dept_ws_js)

        # Department-specific visualizations
        self.assertIn("Lead & Revenue Conversion Funnel", self.dept_ws_js) # CMO
        self.assertIn("Connected MCP Tools & Sandboxes", self.dept_ws_js) # CTO
        self.assertIn("Double-Entry Ledger Integrity", self.dept_ws_js) # CFO
        self.assertIn("Workforce Architecture Invariant", self.dept_ws_js) # CHRO

    def test_overview_workspace_integration(self):
        self.assertIn("ceo-command-center-slot", self.overview_js)
        self.assertIn("window.CeoCommandCenter.render", self.overview_js)
        self.assertIn("toggleDetailedAnalytics", self.overview_js)
        self.assertIn("Show Deep Analytics", self.overview_js)

    def test_index_html_loads_phase5_scripts(self):
        self.assertIn('<script src="ai_action_card.js"></script>', self.index_html)
        self.assertIn('<script src="ceo_command_center.js"></script>', self.index_html)
        self.assertIn('<script src="department_workspace.js"></script>', self.index_html)

if __name__ == '__main__':
    unittest.main()
