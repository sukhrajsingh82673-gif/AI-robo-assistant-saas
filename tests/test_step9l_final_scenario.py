"""
Final Qualification Test Suite for Step 9 (Sub-Step 9L).
Runs the end-to-end customer journey and all adversarial boundary validations.
"""

import os
import pytest
from scripts.step9_scenario import run_complete_step9_scenario

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep9lFinalScenario:

    def test_complete_step9_lifecycle_scenario_passes(self):
        """Verify the full 11-stage product readiness lifecycle executes without error."""
        result = run_complete_step9_scenario()

        assert result["qualification_status"] == "CERTIFIED_PRODUCT_READY"
        assert result["milestones_passed"] >= 10
        assert len(result["scenario_log"]) >= 10
