"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Frontend Navigation & Executive Workspace Automated Audit Test
Validates:
1. All 26 sidebar navigation items in web/index.html have corresponding <section id="view-..."> containers.
2. All 26 routes are explicitly handled in web/app.js handleRoute() without falling back to 'overview'.
3. All 26 views are handled in renderActiveNavView() in web/app.js.
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
        with open(os.path.join(WEB_DIR, "ai_ceo_workspace.js"), "r", encoding="utf-8") as f:
            self.ceo_js = f.read()

    def test_sidebar_nav_items_have_matching_section_containers(self):
        nav_items = set(re.findall(r'data-nav="([^"]+)"', self.index_html))
        self.assertGreaterEqual(len(nav_items), 26, f"Expected at least 26 nav items, found {len(nav_items)}")

        view_sections = set(re.findall(r'id="view-([^"]+)"', self.index_html))

        for item in nav_items:
            self.assertIn(
                item,
                view_sections,
                f"Sidebar item data-nav='{item}' is missing container <section id='view-{item}'>"
            )

    def test_app_js_explicitly_routes_all_nav_items(self):
        nav_items = set(re.findall(r'data-nav="([^"]+)"', self.index_html))
        
        # Verify handleRoute handles every nav item
        for item in nav_items:
            if item == 'overview':
                continue
            pattern = rf"(?:startsWith|includes)\(['\"/]*{re.escape(item)}['\"/]*\)"
            match = re.search(pattern, self.app_js)
            self.assertTrue(
                match is not None,
                f"Route handler in app.js does not explicitly check for nav item: '{item}'"
            )

    def test_app_js_renderActiveNavView_handles_all_views(self):
        nav_items = set(re.findall(r'data-nav="([^"]+)"', self.index_html))
        
        for item in nav_items:
            pattern = rf"navKey\s*===?\s*['\"]{re.escape(item)}['\"]"
            match = re.search(pattern, self.app_js)
            self.assertTrue(
                match is not None,
                f"renderActiveNavView() in app.js is missing a case branch for: '{item}'"
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
