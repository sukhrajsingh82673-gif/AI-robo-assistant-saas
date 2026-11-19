"""
Tests for Phase 2: Apple-Grade Primitive Components
Verifies components.css, window.UI component factory, and all interaction states.
"""

import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

class TestApplePrimitiveComponents(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB_DIR, "components.css"), "r", encoding="utf-8") as f:
            self.components_css = f.read()
        with open(os.path.join(WEB_DIR, "components.js"), "r", encoding="utf-8") as f:
            self.components_js = f.read()
        with open(os.path.join(WEB_DIR, "design_preview_workspace.js"), "r", encoding="utf-8") as f:
            self.preview_js = f.read()
        with open(os.path.join(WEB_DIR, "index.html"), "r", encoding="utf-8") as f:
            self.index_html = f.read()

    def test_components_css_has_all_primitives(self):
        classes = [
            # Buttons
            ".btn-apple", ".btn-apple-primary", ".btn-apple-secondary",
            ".btn-apple-plain", ".btn-apple-destructive", ".btn-apple-icon",
            ".btn-apple-loading",
            # Inputs
            ".field-group-apple", ".input-apple", ".input-apple-error",
            # Cards
            ".card-apple", ".card-apple-interactive", ".card-apple-hero",
            # Chips
            ".chip-apple", ".chip-green", ".chip-orange", ".chip-red",
            ".chip-accent", ".chip-filter",
            # Toggles & Segmented
            ".toggle-apple", ".toggle-track-apple", ".segmented-apple",
            ".segmented-item-apple",
            # List rows
            ".grouped-list-apple", ".list-row-apple",
            # Skeletons
            ".skeleton-apple", ".skeleton-text", ".skeleton-avatar",
            # Progress & Empty State
            ".progress-bar-apple", ".empty-state-apple",
            # Toasts & Modals
            ".toast-apple", ".modal-overlay-apple", ".modal-dialog-apple"
        ]
        for cls in classes:
            self.assertIn(cls, self.components_css, f"Missing component class: {cls}")

    def test_components_js_exports_window_ui(self):
        self.assertIn("window.UI = UI;", self.components_js)
        primitives = [
            "UI.Button", "UI.Input", "UI.Card", "UI.Chip",
            "UI.Toggle", "UI.SegmentedControl", "UI.ListRow",
            "UI.Skeleton", "UI.ProgressBar", "UI.EmptyState",
            "UI.showToast", "UI.openModal", "UI.closeModal"
        ]
        for prim in primitives:
            self.assertIn(prim, self.components_js, f"Missing UI method: {prim}")

    def test_accessibility_and_keyboard_focus(self):
        # Focus ring present
        self.assertIn(":focus-visible", self.components_css)
        self.assertIn("--focus-ring", self.components_css)
        # Modal has role="dialog" and aria-modal="true"
        self.assertIn('role="dialog"', self.components_js)
        self.assertIn('aria-modal="true"', self.components_js)
        # Escape key handling for modals
        self.assertIn("e.key === 'Escape'", self.components_js)

    def test_index_html_links_components_assets(self):
        self.assertIn('<link rel="stylesheet" href="components.css" />', self.index_html)
        self.assertIn('<script src="components.js"></script>', self.index_html)

    def test_design_preview_showcases_all_primitives(self):
        self.assertIn("UI.Button", self.preview_js)
        self.assertIn("UI.Input", self.preview_js)
        self.assertIn("UI.Chip", self.preview_js)
        self.assertIn("UI.Toggle", self.preview_js)
        self.assertIn("UI.SegmentedControl", self.preview_js)
        self.assertIn("UI.ListRow", self.preview_js)
        self.assertIn("UI.Skeleton", self.preview_js)
        self.assertIn("UI.ProgressBar", self.preview_js)
        self.assertIn("UI.EmptyState", self.preview_js)

if __name__ == "__main__":
    unittest.main()
