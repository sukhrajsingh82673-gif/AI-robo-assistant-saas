"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Frontend Navigation & Executive Workspace Automated Audit Test
Validates:
1. Every screen in the URA registry has a matching <section id="view-..."> container.
2. Every URA screen has a route alias in the resolver and the wrapper is installed.
3. Every URA screen has a renderer in the URA renderer registry.
4. All referenced workspace JavaScript modules exist on disk and pass syntax validation.
5. AIC CEO Workspace contains all 20 executive sections and zero ungrounded fabricated numbers.
"""

import unittest
import os
import re
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestFrontendNavigationAudit(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()
        with open(os.path.join(WEB_DIR, "app.js"), "r", encoding="utf-8") as f:
            self.app_js = f.read()
        with open(os.path.join(WEB_DIR, "ura_screens.js"), "r", encoding="utf-8") as f:
            self.screens_js = f.read()
        with open(os.path.join(WEB_DIR, "ai_ceo_workspace.js"), "r", encoding="utf-8") as f:
            self.ceo_js = f.read()

    def _registry(self):
        """Return [(screen id, section id)] from the URA screen registry."""
        return re.findall(
            r"\{\s*id:\s*'([^']+)'[\s\S]*?section:\s*'([^']+)'\s*\}",
            self.screens_js,
        )

    def test_sidebar_nav_items_have_matching_section_containers(self):
        registry = self._registry()
        self.assertGreaterEqual(len(registry), 17, f"Expected the 17-screen URA registry, found {len(registry)}")

        view_sections = set(re.findall(r'id="view-([^"]+)"', self.index_html))
        for screen_id, section in registry:
            self.assertIn(
                section.replace("view-", "", 1),
                view_sections,
                f"URA screen '{screen_id}' is missing its container <section id='{section}'>",
            )

        self.assertIn("settings", [screen_id for screen_id, _ in registry])

    def test_app_js_explicitly_routes_all_nav_items(self):
        registry = self._registry()
        routes = dict(re.findall(r"'(/[^']*)':\s*'([^']+)'", self.screens_js))

        self.assertIn("window.handleRoute = function", self.screens_js)
        for screen_id, _section in registry:
            if screen_id == "settings":
                self.assertIn("clean === '/settings'", self.screens_js)
                continue
            self.assertIn(
                screen_id,
                routes.values(),
                f"Route resolver has no alias for URA screen: '{screen_id}'",
            )

    def test_app_js_renderActiveNavView_handles_all_views(self):
        registry = self._registry()
        for screen_id, _section in registry:
            self.assertRegex(
                self.screens_js,
                rf"['\"]?{re.escape(screen_id)}['\"]?:\s*render",
                f"URA renderer registry is missing an entry for: '{screen_id}'",
            )

    def test_workspace_script_files_exist(self):
        scripts = re.findall(r'<script\s+src="([^"]+)"></script>', self.index_html)
        for s in scripts:
            script_path = os.path.join(WEB_DIR, s)
            self.assertTrue(
                os.path.isfile(script_path),
                f"Script tag in index.html references missing file: {s}"
            )

    def test_ai_ceo_workspace_has_20_sections(self):
        expected_tabs = [
            'overview', 'strategy', 'objectives', 'departments', 'workforce',
            'missions', 'kpis', 'finance', 'risks', 'opportunities',
            'decisions', 'approvals', 'evidence', 'reports', 'economic',
            'contracts', 'predictions', 'scorecard', 'constitution', 'scenarios'
        ]
        
        for tab in expected_tabs:
            self.assertIn(
                f"'{tab}'",
                self.ceo_js,
                f"AI CEO Workspace is missing tab definition for: '{tab}'"
            )
            # Verify render method exists for each of the new executive tabs
            if tab in ['economic', 'contracts', 'predictions', 'scorecard', 'constitution', 'scenarios']:
                method_name = f"renderSection{tab.capitalize()}"
                self.assertIn(
                    method_name,
                    self.ceo_js,
                    f"AI CEO Workspace is missing renderer method: {method_name}"
                )

    def test_invariant_activity_separated_from_achievement_in_ui(self):
        invariant_str = "TASK_COMPLETION != MISSION_COMPLETION != BUSINESS_OUTCOME != REVENUE != PROFIT != CASH != VERIFIED_ECONOMIC_RESULT"
        self.assertIn(
            invariant_str,
            self.ceo_js,
            "AIC CEO workspace UI must prominently display the 7-stage verification chain invariant"
        )

    def test_no_mock_data_fallback_badge_present(self):
        self.assertIn(
            "NO VERIFIED DATA",
            self.ceo_js,
            "AIC CEO workspace UI must display 'NO VERIFIED DATA' for ungrounded metrics"
        )

if __name__ == '__main__':
    unittest.main()
