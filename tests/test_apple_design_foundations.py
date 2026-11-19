"""
Tests for Phase 1: Apple-Grade Design System Foundations
Verifies tokens.css, typography, motion system, icons, AppTile squircles, AiOrb, and /design preview route.
"""

import unittest
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestAppleDesignFoundations(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "design_tokens.css"), "r", encoding="utf-8") as f:
            self.tokens_css = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()
        with open(os.path.join(WEB_DIR, "app.js"), "r", encoding="utf-8") as f:
            self.app_js = f.read()
        with open(os.path.join(WEB_DIR, "motion.js"), "r", encoding="utf-8") as f:
            self.motion_js = f.read()
        with open(os.path.join(WEB_DIR, "icons.js"), "r", encoding="utf-8") as f:
            self.icons_js = f.read()
        with open(os.path.join(WEB_DIR, "app_tile.js"), "r", encoding="utf-8") as f:
            self.app_tile_js = f.read()
        with open(os.path.join(WEB_DIR, "ai_orb.js"), "r", encoding="utf-8") as f:
            self.ai_orb_js = f.read()
        with open(os.path.join(WEB_DIR, "design_preview_workspace.js"), "r", encoding="utf-8") as f:
            self.design_preview_js = f.read()

    def test_design_tokens_css_has_apple_palettes(self):
        # Light mode surfaces & colors
        self.assertIn("--bg:            #F5F5F7", self.tokens_css)
        self.assertIn("--surface:       #FFFFFF", self.tokens_css)
        self.assertIn("--accent:        #0071E3", self.tokens_css)
        self.assertIn("--green:         #34C759", self.tokens_css)
        self.assertIn("--orange:        #FF9500", self.tokens_css)
        self.assertIn("--red:           #FF3B30", self.tokens_css)
        self.assertIn("--purple:        #AF52DE", self.tokens_css)
        self.assertIn("--teal:          #30B0C7", self.tokens_css)

        # Dark mode surfaces & colors
        self.assertIn(":root[data-theme='dark']", self.tokens_css)
        self.assertIn("--bg:            #000000", self.tokens_css)
        self.assertIn("--surface:       #1C1C1E", self.tokens_css)
        self.assertIn("--accent:        #0A84FF", self.tokens_css)
        self.assertIn("--green:         #30D158", self.tokens_css)
        self.assertIn("--orange:        #FF9F0A", self.tokens_css)

    def test_typography_scale_and_materials(self):
        typography_classes = [
            ".t-display", ".t-large-title", ".t-title-1", ".t-title-2",
            ".t-title-3", ".t-headline", ".t-body", ".t-callout",
            ".t-footnote", ".t-caption", ".tabular-nums"
        ]
        for cls in typography_classes:
            self.assertIn(cls, self.tokens_css, f"Missing typography class: {cls}")

        # Glass material with backdrop blur
        self.assertIn(".glass", self.tokens_css)
        self.assertIn("backdrop-filter: saturate(180%) blur(24px)", self.tokens_css)

    def test_motion_library_primitives(self):
        self.assertIn("window.Motion =", self.motion_js)
        self.assertIn("spring", self.motion_js)
        self.assertIn("snappy", self.motion_js)
        self.assertIn("smooth", self.motion_js)
        self.assertIn("bouncy", self.motion_js)
        self.assertIn("animateCountUp", self.motion_js)
        self.assertIn("animateAppear", self.motion_js)
        self.assertIn("prefersReducedMotion", self.motion_js)

    def test_icon_and_app_tile_components(self):
        self.assertIn("window.Icon =", self.icons_js)
        self.assertIn("window.AppTile =", self.app_tile_js)
        # Check all 9 entities configured in AppTile
        for ent in ['ceo', 'coo', 'cmo', 'cto', 'cfo', 'chro', 'security', 'assistant', 'company']:
            self.assertIn(f"{ent}:", self.app_tile_js, f"AppTile missing entity config for: {ent}")

    def test_ai_orb_component(self):
        self.assertIn("window.AiOrb =", self.ai_orb_js)
        self.assertIn("orb-breathe", self.ai_orb_js)
        self.assertIn("state-idle", self.ai_orb_js)
        self.assertIn("state-thinking", self.ai_orb_js)
        self.assertIn("state-speaking", self.ai_orb_js)
        self.assertIn("state-needs-you", self.ai_orb_js)

    def test_design_preview_route_and_view_container(self):
        self.assertIn('id="view-design"', self.index_html)
        self.assertIn('startsWith(\'/design\')', self.app_js)
        self.assertIn('DesignPreviewWorkspace', self.app_js)
        self.assertIn('window.DesignPreviewWorkspace =', self.design_preview_js)

if __name__ == "__main__":
    unittest.main()
