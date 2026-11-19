"""
Tests for Phase 4: Apple-Grade Entry Flows
Verifies Welcome screen, Flow A (New Company Brief, Preview, Hand-off, Build Timeline)
and Flow B (Existing Company 5-step Intake Stepper, Analysis, and Loophole Findings).
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleEntryFlows(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "entry_flows.js"), "r", encoding="utf-8") as f:
            self.entry_flows_js = f.read()
        with open(os.path.join(WEB_DIR, "company_workspace.js"), "r", encoding="utf-8") as f:
            self.company_ws_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_entry_flows_controller_methods(self):
        self.assertIn("window.EntryFlows =", self.entry_flows_js)

        # Flow A methods
        self.assertIn("renderWelcome", self.entry_flows_js)
        self.assertIn("renderNewCompanyBrief", self.entry_flows_js)
        self.assertIn("openBriefPreview", self.entry_flows_js)
        self.assertIn("triggerHandOffAnimation", self.entry_flows_js)
        self.assertIn("renderBuildTimeline", self.entry_flows_js)

        # Flow B methods
        self.assertIn("renderExistingIntake", self.entry_flows_js)
        self.assertIn("nextIntakeStep", self.entry_flows_js)
        self.assertIn("prevIntakeStep", self.entry_flows_js)
        self.assertIn("testConnection", self.entry_flows_js)
        self.assertIn("renderAnalysisFindings", self.entry_flows_js)
        self.assertIn("renderFindingsResults", self.entry_flows_js)

    def test_timeline_stages_and_loopholes(self):
        # 8 Timeline stages
        stages = [
            'Brief understood', 'Plan approved', 'Website and engines',
            'Sales and marketing setup', 'Finance setup', 'AI team hired',
            'CEO final check', 'Go live'
        ]
        for st in stages:
            self.assertIn(st, self.entry_flows_js, f"Missing timeline stage: {st}")

        # Loopholes
        self.assertIn("Abandoned Checkout Dropout", self.entry_flows_js)
        self.assertIn("Competitor Pricing Undercutting", self.entry_flows_js)
        self.assertIn("Inbound Response Latency", self.entry_flows_js)

    def test_company_workspace_routes_welcome(self):
        self.assertIn("EntryFlows.renderWelcome", self.company_ws_js)

    def test_index_html_loads_entry_flows(self):
        self.assertIn('<script src="entry_flows.js"></script>', self.index_html)

if __name__ == "__main__":
    unittest.main()
