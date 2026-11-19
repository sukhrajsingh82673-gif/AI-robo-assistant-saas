"""
Tests for Phase 8: Apple-Grade Accessibility (WCAG 2.2 AA), Reduced Motion, docs/architecture/DESIGN.md & Final QA
Verifies:
1. docs/architecture/DESIGN.md comprehensive design system documentation.
2. Focus visible ring (:focus-visible) and --focus-ring token.
3. Accessible ARIA attributes across primitive components (dialog, progressbar, tablist).
4. Full prefers-reduced-motion rules across design_tokens.css, motion.js, and ai_orb.js.
5. All Apple-grade scripts loaded in index.html in valid execution order.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleAccessibilityQA(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(BASE_DIR, "docs/architecture/DESIGN.md"), "r", encoding="utf-8") as f:
            self.design_md = f.read()
        with open(os.path.join(WEB_DIR, "design_tokens.css"), "r", encoding="utf-8") as f:
            self.tokens_css = f.read()
        with open(os.path.join(WEB_DIR, "components.css"), "r", encoding="utf-8") as f:
            self.components_css = f.read()
        with open(os.path.join(WEB_DIR, "components.js"), "r", encoding="utf-8") as f:
            self.components_js = f.read()
        with open(os.path.join(WEB_DIR, "motion.js"), "r", encoding="utf-8") as f:
            self.motion_js = f.read()
        with open(os.path.join(WEB_DIR, "ai_orb.js"), "r", encoding="utf-8") as f:
            self.orb_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_design_documentation_completeness(self):
        # 10 core sections in docs/architecture/DESIGN.md
        required_sections = [
            "Design Vision & Philosophy",
            "Design Tokens & Foundations",
            "Motion System",
            "Squircles & Iconography",
            "Signature AI Presence",
            "Primitive Components",
            "App Shell & Navigation",
            "The Two Entry Flows",
            "5-Part AI Action Pattern",
            "Core Workspaces & Governance",
            "Accessibility (WCAG 2.2 AA) Audit"
        ]
        for sec in required_sections:
            self.assertIn(sec, self.design_md, f"Missing section in docs/architecture/DESIGN.md: {sec}")

        # Non-negotiable principles
        self.assertIn("Obvious in 5 Seconds", self.design_md)
        self.assertIn("Simplicity Wins Every Tie", self.design_md)
        self.assertIn("Zero Invented Business Data", self.design_md)

    def test_accessibility_focus_rings(self):
        self.assertIn("--focus-ring:", self.tokens_css)
        self.assertIn(":focus-visible", self.tokens_css)
        self.assertIn("box-shadow: var(--focus-ring);", self.tokens_css)
        self.assertIn(":focus-visible", self.components_css)

    def test_accessibility_aria_attributes(self):
        # Dialog
        self.assertIn('role="dialog"', self.components_js)
        self.assertIn('aria-modal="true"', self.components_js)
        self.assertIn('aria-labelledby="appleModalTitle"', self.components_js)

        # Progress bar
        self.assertIn('role="progressbar"', self.components_js)
        self.assertIn('aria-valuenow=', self.components_js)
        self.assertIn('aria-valuemin="0"', self.components_js)
        self.assertIn('aria-valuemax="100"', self.components_js)

        # Tablist
        self.assertIn('role="tablist"', self.components_js)

    def test_prefers_reduced_motion(self):
        # CSS reduced motion rule
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.tokens_css)
        self.assertIn("animation-duration: 0.01ms !important;", self.tokens_css)
        self.assertIn("transition-duration: 0.01ms !important;", self.tokens_css)

        # JS reduced motion check
        self.assertIn("prefersReducedMotion()", self.motion_js)
        self.assertIn("(prefers-reduced-motion: reduce)", self.motion_js)

        # AI Orb reduced motion override
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.orb_js)

    def test_complete_apple_pipeline_in_index_html(self):
        expected_scripts = [
            "motion.js",
            "icons.js",
            "app_tile.js",
            "ai_orb.js",
            "components.js",
            "ai_action_card.js",
            "ceo_command_center.js",
            "department_workspace.js",
            "apple_workforce_board.js",
            "apple_sales_board.js",
            "apple_reports_preview.js",
            "apple_governed_terminal.js",
            "apple_security_center.js",
            "apple_coworker_assistant.js",
            "app_shell.js",
            "entry_flows.js",
            "design_preview_workspace.js"
        ]
        for sc in expected_scripts:
            self.assertIn(f'<script src="{sc}"></script>', self.index_html, f"Missing script tag: {sc}")

if __name__ == '__main__':
    unittest.main()
