"""
Tests for Phase 3: Apple-Grade AppShell and Navigation
Verifies app_shell.css, app_shell.js, sidebar rail, company switcher, floating Ask URA bar, and Inspector panel.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleAppShell(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "app_shell.css"), "r", encoding="utf-8") as f:
            self.app_shell_css = f.read()
        with open(os.path.join(WEB_DIR, "app_shell.js"), "r", encoding="utf-8") as f:
            self.app_shell_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_app_shell_css_rules(self):
        # 264px desktop sidebar and 72px rail
        self.assertIn("width: 264px;", self.app_shell_css)
        self.assertIn(".apple-sidebar.collapsed", self.app_shell_css)
        self.assertIn("width: 72px;", self.app_shell_css)

        # Floating Ask URA bar
        self.assertIn(".ask-ura-bar-wrap", self.app_shell_css)
        self.assertIn(".ask-ura-bar", self.app_shell_css)

        # 380px Inspector panel
        self.assertIn(".apple-inspector-panel", self.app_shell_css)
        self.assertIn("width: 380px;", self.app_shell_css)

        # Mobile bottom tab bar
        self.assertIn(".apple-mobile-tab-bar", self.app_shell_css)

    def test_app_shell_js_controllers(self):
        self.assertIn("window.AppShell =", self.app_shell_js)
        self.assertIn("toggleSidebarCollapse", self.app_shell_js)
        self.assertIn("openCompanySwitcher", self.app_shell_js)
        self.assertIn("openAskUra", self.app_shell_js)
        self.assertIn("openInspector", self.app_shell_js)
        self.assertIn("closeInspector", self.app_shell_js)

        # Global keyboard shortcut for Cmd/Ctrl+K
        self.assertIn("e.key.toLowerCase() === 'k'", self.app_shell_js)

        # Global Inspector interface
        self.assertIn("window.Inspector =", self.app_shell_js)

    def test_index_html_has_app_shell_elements(self):
        # Linked stylesheet and script
        self.assertIn('<link rel="stylesheet" href="app_shell.css" />', self.index_html)
        self.assertIn('<script src="app_shell.js"></script>', self.index_html)

        # Company Switcher (URA shell company chip opens the company menu)
        self.assertIn('class="ura-company-chip"', self.index_html)
        self.assertIn('id="companyChipBtn"', self.index_html)

        # Floating Ask URA Bar
        self.assertIn('id="askUraBarWrap"', self.index_html)
        self.assertIn('class="ask-ura-bar', self.index_html)
        self.assertIn('AppShell.openAskUra()', self.index_html)

if __name__ == "__main__":
    unittest.main()
