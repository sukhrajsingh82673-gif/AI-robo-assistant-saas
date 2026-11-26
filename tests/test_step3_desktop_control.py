"""
Acceptance Test Suite for OpenCode Step 3C — Desktop Perception and Control
Tests:
(a) Layer 1 parses an accessibility snapshot into interactable nodes with relative coordinates.
(b) Password fields masked in Layer 1 and Layer 2 before leaving the host (Rule 24).
(c) Layer 2 invoked ONLY when Layer 1 is insufficient or pre-action visual check is required, and evidence records the layer used.
(d) Out-of-grant coordinates rejected on the host (Rule 23 / Rule 28).
(e) Human override: any physical mouse or keyboard event or hotkey halts execution instantly.
(f) Physical-speed throttling enforces human typing and click limits.
(g) Minimum necessary capture (Rule 28) bounds capture strictly to granted window.
"""

import unittest
import time
import uuid
from typing import Dict, Any

from core.db import db
from core.host.perception import (
    BoundingRect,
    AccessibilityNode,
    AccessibilityTree,
    PerceptionLayer,
    PerceptionSnapshot,
    DesktopPerceptionEngine,
)
from core.host.interaction import (
    InteractionPrimitive,
    InteractionResult,
    OutOfGrantCoordinatesError,
    HumanPhysicalOverrideError,
    PhysicalSpeedThrottler,
    HumanOverrideDetector,
    DesktopInteractionDispatcher,
)
from core.host.agent import ZonataHostAgent
from core.host.types import HostSecurityViolation
from core.evidence_service import evidence_service


class TestStep3DesktopControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.verify_readiness()

    def setUp(self):
        self.tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_id = f"cmp_{uuid.uuid4().hex[:8]}"
        self.window_bounds = BoundingRect(x=100, y=200, width=1024, height=768)
        self.engine = DesktopPerceptionEngine()
        self.dispatcher = DesktopInteractionDispatcher()
        self.agent = ZonataHostAgent(device_name="Test-Workstation")
        self.agent.tenant_id = self.tenant_id
        self.agent.company_id = self.company_id
        self.agent.device_id = f"dev_{uuid.uuid4().hex[:8]}"

    def _sample_accessibility_data(self) -> Dict[str, Any]:
        return {
            "window_id": "win_acme_crm",
            "window_title": "Acme Enterprise CRM",
            "nodes": [
                {
                    "node_id": "btn_submit",
                    "role": "button",
                    "name": "Submit Remittance",
                    "bounds": {"x": 200, "y": 300, "width": 120, "height": 40},
                    "is_interactive": True,
                    "value": None,
                },
                {
                    "node_id": "input_username",
                    "role": "edit_text",
                    "name": "Username Field",
                    "bounds": {"x": 200, "y": 360, "width": 250, "height": 30},
                    "is_interactive": True,
                    "value": "alice@corp.example",
                },
                {
                    "node_id": "input_password",
                    "role": "password_field",
                    "name": "Master Password",
                    "bounds": {"x": 200, "y": 410, "width": 250, "height": 30},
                    "is_interactive": True,
                    "is_password": True,
                    "value": "SuperSecretP@ssword123!",
                },
                {
                    "node_id": "widget_captcha",
                    "role": "captcha_widget",
                    "name": "Verification Challenge",
                    "bounds": {"x": 200, "y": 460, "width": 300, "height": 80},
                    "is_interactive": False,
                    "value": "ChallengePrompt",
                },
            ],
        }

    def test_01_layer1_parses_accessibility_tree_into_relative_coordinates(self):
        """Acceptance (a): Layer 1 parses an accessibility snapshot into interactable nodes with relative coordinates."""
        raw_data = self._sample_accessibility_data()
        tree = self.engine.parse_accessibility_snapshot(raw_data, self.window_bounds)

        self.assertEqual(tree.window_id, "win_acme_crm")
        self.assertEqual(tree.window_title, "Acme Enterprise CRM")

        btn = tree.find_by_id("btn_submit")
        self.assertIsNotNone(btn)
        self.assertEqual(btn.name, "Submit Remittance")
        self.assertEqual(btn.bounds.x, 200)
        self.assertEqual(btn.bounds.y, 300)

        # Window origin is (100, 200). Relative coords must be (200-100, 300-200) = (100, 100)
        self.assertEqual(btn.relative_bounds.x, 100)
        self.assertEqual(btn.relative_bounds.y, 100)
        self.assertEqual(btn.relative_bounds.width, 120)
        self.assertEqual(btn.relative_bounds.height, 40)
        self.assertEqual(btn.relative_bounds.center, (160, 120))

    def test_02_password_and_secret_fields_masked_on_host(self):
        """Acceptance (b): Password fields masked in Layer 1 and Layer 2 before leaving the host (Rule 24)."""
        raw_data = self._sample_accessibility_data()
        tree = self.engine.parse_accessibility_snapshot(raw_data, self.window_bounds)

        pwd_node = tree.find_by_id("input_password")
        self.assertIsNotNone(pwd_node)
        # Value must be replaced with [MASKED_INPUT]
        self.assertEqual(pwd_node.value, "[MASKED_INPUT]")

        tree_dict = tree.to_dict()
        serialized_nodes = {n["node_id"]: n for n in tree_dict["nodes"]}
        self.assertEqual(serialized_nodes["input_password"]["value"], "[MASKED_INPUT]")
        self.assertTrue(serialized_nodes["input_password"]["masked"])

        # Also verify visual masking frame (Layer 2)
        masked_frame = self.engine.mask_visual_frame({"window_id": tree.window_id}, tree)
        self.assertEqual(masked_frame["masked_status"], "CREDENTIALS_REDACTED")
        masked_node_ids = [r["node_id"] for r in masked_frame["masked_regions"]]
        self.assertIn("input_password", masked_node_ids)
        self.assertIn("widget_captcha", masked_node_ids)

    def test_03_perception_strategy_prefers_layer1(self):
        """Acceptance (c): Layer 1 preferred when accessibility data is complete; evidence recorded."""
        raw_data = self._sample_accessibility_data()
        snapshot = self.agent.perceive_window(
            window_bounds=self.window_bounds,
            accessibility_data=raw_data,
        )

        self.assertEqual(snapshot.perception_layer, PerceptionLayer.L1_ACCESSIBILITY_TREE)
        self.assertIsNotNone(snapshot.tree)
        self.assertIsNotNone(snapshot.evidence_event_id)

    def test_04_layer2_invoked_when_tree_missing_or_high_impact_check(self):
        """Acceptance (c): Layer 2 invoked only when Layer 1 is insufficient or pre-action visual check is required."""
        # 1. Empty tree -> triggers Layer 2 fallback
        snapshot_empty = self.agent.perceive_window(
            window_bounds=self.window_bounds,
            accessibility_data={"nodes": []},
        )
        self.assertEqual(snapshot_empty.perception_layer, PerceptionLayer.L2_VISION)
        self.assertIsNotNone(snapshot_empty.masked_visual_summary)

        # 2. Complete tree, but high-impact action requires visual confirmation (Rule 27)
        raw_data = self._sample_accessibility_data()
        snapshot_high_impact = self.agent.perceive_window(
            window_bounds=self.window_bounds,
            accessibility_data=raw_data,
            is_high_impact=True,
        )
        self.assertEqual(snapshot_high_impact.perception_layer, PerceptionLayer.L2_VISION)

        # 3. Explicit visual inspection task
        snapshot_visual = self.agent.perceive_window(
            window_bounds=self.window_bounds,
            accessibility_data=raw_data,
            visual_inspection_task=True,
        )
        self.assertEqual(snapshot_visual.perception_layer, PerceptionLayer.L2_VISION)

    def test_05_out_of_grant_coordinates_rejected_on_host(self):
        """Acceptance (d): Out-of-grant coordinates rejected on the host (Rule 23 & Rule 28)."""
        # Valid relative coordinate within window [0..1024, 0..768]
        result = self.agent.dispatch_gui_action(
            primitive=InteractionPrimitive.CLICK,
            window_bounds=self.window_bounds,
            relative_coords=(150, 200),
        )
        self.assertTrue(result.executed)
        # Absolute coords translated to (100+150, 200+200) = (250, 400)
        self.assertEqual(result.absolute_coords, (250, 400))

        # Coordinate exceeding width (1200 > 1024)
        with self.assertRaises(OutOfGrantCoordinatesError) as ctx:
            self.agent.dispatch_gui_action(
                primitive=InteractionPrimitive.CLICK,
                window_bounds=self.window_bounds,
                relative_coords=(1200, 200),
            )
        self.assertIn("outside the granted window bounds", str(ctx.exception))

        # Negative relative coordinate (-10, 50)
        with self.assertRaises(OutOfGrantCoordinatesError):
            self.agent.dispatch_gui_action(
                primitive=InteractionPrimitive.CLICK,
                window_bounds=self.window_bounds,
                relative_coords=(-10, 50),
            )

        # Drag end exceeding boundary
        with self.assertRaises(OutOfGrantCoordinatesError):
            self.agent.dispatch_gui_action(
                primitive=InteractionPrimitive.CLICK_AND_DRAG,
                window_bounds=self.window_bounds,
                relative_coords=(100, 100),
                drag_end_relative=(100, 900),  # 900 > 768 height
            )

    def test_06_human_override_halts_execution_instantly(self):
        """Acceptance (e): Any physical mouse or keyboard event or hotkey halts execution instantly."""
        # Trigger human physical override
        self.agent.trigger_physical_override(reason="HUMAN_PHYSICAL_MOUSE_MOVE_DETECTED")

        # Any subsequent dispatch must be rejected
        with self.assertRaises(HostSecurityViolation):
            self.agent.dispatch_gui_action(
                primitive=InteractionPrimitive.CLICK,
                window_bounds=self.window_bounds,
                relative_coords=(100, 100),
            )

        # Perception must also be halted
        with self.assertRaises(HostSecurityViolation):
            self.agent.perceive_window(
                window_bounds=self.window_bounds,
                accessibility_data=self._sample_accessibility_data(),
            )

    def test_07_physical_speed_throttling_enforces_human_cadence(self):
        """Acceptance (f): Physical speed throttling calculates realistic typing duration."""
        throttler = PhysicalSpeedThrottler(simulated=True)
        sample_text = "The quick brown fox jumps over the lazy dog."  # 44 chars
        # At 12 chars per second, 44 chars should take ~3.66 seconds
        duration = throttler.compute_typing_duration(sample_text)
        expected = 44 / 12.0
        self.assertAlmostEqual(duration, expected, places=2)

        # Fast clicks within 50ms interval report positive throttled wait ms
        throttler.throttle_interaction(is_click=True)
        wait_ms = throttler.throttle_interaction(is_click=True)
        self.assertGreater(wait_ms, 0.0)

    def test_08_minimum_necessary_capture_bounds_strictly_to_window(self):
        """Acceptance (g): Capture is strictly bounded to the granted window, avoiding desktop bleed."""
        snapshot = self.agent.perceive_window(
            window_bounds=self.window_bounds,
            accessibility_data=self._sample_accessibility_data(),
        )
        self.assertEqual(snapshot.window_bounds, {"x": 100, "y": 200, "width": 1024, "height": 768})
        # Full-screen bleed would encompass (0, 0, 1920, 1080)
        self.assertNotEqual(snapshot.window_bounds["x"], 0)


if __name__ == "__main__":
    unittest.main()
