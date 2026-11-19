"""
Tests for the app shell after the URA phase-1 rebuild.

The original Apple shell (floating Ask URA bar, Apple mobile tab bar, local
Cmd/Ctrl+K listener) was replaced by the `ura_*` layer. These tests keep the
contract that still matters: a responsive sidebar, one company switcher, one
assistant surface, an inspector, and a single command-palette shortcut.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")


class TestAppleAppShell(unittest.TestCase):
    def setUp(self):
        def read(name):
            with open(os.path.join(WEB_DIR, name), "r", encoding="utf-8") as handle:
                return handle.read()

        self.app_shell_css = read("app_shell.css")
        self.app_shell_js = read("app_shell.js")
        self.ura_ui_css = read("ura_ui.css")
        self.ura_shell_js = read("ura_shell.js")
        self.index_html = read("index.html")

    def test_shell_css_rules(self):
        # The live shell is the ura_* layer.
        self.assertIn(".ura-shell", self.ura_ui_css)
        self.assertIn(".ura-sidebar", self.ura_ui_css)
        self.assertIn(".ura-sidebar.rail", self.ura_ui_css)
        self.assertIn(".ura-company-chip", self.ura_ui_css)

        # Logical properties so Arabic flips the whole layout.
        self.assertIn("inset-inline-start", self.ura_ui_css)

        # Phone navigation and the drawer.
        self.assertIn(".ura-tabbar", self.ura_ui_css)
        self.assertIn("@media", self.ura_ui_css)

        # The older Apple shell still backs the Inspector panel.
        self.assertIn(".apple-inspector-panel", self.app_shell_css)
        self.assertIn("width: 380px;", self.app_shell_css)

    def test_app_shell_js_controllers(self):
        self.assertIn("window.AppShell =", self.app_shell_js)
        self.assertIn("toggleSidebarCollapse", self.app_shell_js)
        self.assertIn("openCompanySwitcher", self.app_shell_js)
        self.assertIn("openInspector", self.app_shell_js)
        self.assertIn("closeInspector", self.app_shell_js)
        self.assertIn("window.Inspector =", self.app_shell_js)

        # One switcher for the whole app.
        self.assertIn("CompanySetupSwitcher", self.app_shell_js)

        # Exactly one command-palette shortcut, owned by the URA shell.
        self.assertIn("e.key.toLowerCase() === 'k'", self.ura_shell_js)
        self.assertNotIn("toLowerCase() === 'k'", self.app_shell_js)
        self.assertIn("window.URAShell =", self.ura_shell_js)

        # The company chip opens that single switcher.
        self.assertIn("CompanySetupSwitcher", self.ura_shell_js)

    def test_index_html_has_app_shell_elements(self):
        self.assertIn('<link rel="stylesheet" href="app_shell.css" />', self.index_html)
        self.assertIn('<script src="app_shell.js"></script>', self.index_html)
        self.assertIn('<link rel="stylesheet" href="ura_ui.css" />', self.index_html)
        self.assertIn('<script src="ura_shell.js"></script>', self.index_html)

        # Company switcher chip.
        self.assertIn('class="ura-company-chip"', self.index_html)
        self.assertIn('id="companyChipBtn"', self.index_html)
        self.assertIn('id="companyChipName"', self.index_html)

        # One assistant surface only: the URA assistant root, no second launcher.
        self.assertEqual(self.index_html.count('id="uraAssistantRoot"'), 1)
        self.assertNotIn('id="askUraBarWrap"', self.index_html)


if __name__ == "__main__":
    unittest.main()
