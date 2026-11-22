"""
OpenCode Step 2K — Step 2 Qualification Scenario Test Suite.

Verifies end-to-end execution of scripts/step2_scenario.py across all
subsystems: CEO brain, ActionGateway, 5-layer verification, hierarchical KPIs,
workforce trust, SOP execution, adversarial defenses, and capability truth.
"""

import unittest
import pytest

from scripts.step2_scenario import run_scenario


class TestStep2Scenario(unittest.TestCase):
    """Verifies that the entire Step 2 intelligence & verified execution kernel scenario passes cleanly."""

    def test_step2_scenario_runs_cleanly_and_passes_all_stages(self):
        """Exercises the 8-stage qualification pipeline and asserts every stage passes."""
        report = run_scenario()
        self.assertTrue(report.get("passed"), "Scenario did not complete with passed=True")
        self.assertIn("stages", report)

        stages = report["stages"]
        self.assertEqual(stages["stage1_empty_goal"]["status"], "PASSED")
        self.assertEqual(stages["stage1_empty_goal"]["kpi_status"], "INSUFFICIENT_MEASUREMENTS")

        self.assertEqual(stages["stage2_baseline_and_kpi"]["status"], "PASSED")
        self.assertEqual(stages["stage2_baseline_and_kpi"]["expected_baseline"], 38.0)
        self.assertEqual(stages["stage2_baseline_and_kpi"]["baseline_days"], 38.0)
        self.assertTrue(stages["stage2_baseline_and_kpi"]["approved"])

        self.assertEqual(stages["stage3_ceo_planning"]["status"], "PASSED")
        self.assertGreater(stages["stage3_ceo_planning"]["tasks_planned"], 0)

        self.assertEqual(stages["stage4_shadow_promotion"]["status"], "PASSED")
        self.assertTrue(stages["stage4_shadow_promotion"]["refusal_verified"])
        self.assertEqual(stages["stage4_shadow_promotion"]["final_trust_level"], "SUPERVISED")

        self.assertEqual(stages["stage5_verified_execution"]["status"], "PASSED")
        self.assertEqual(stages["stage5_verified_execution"]["verification_status"], "PASSED")
        self.assertGreaterEqual(stages["stage5_verified_execution"]["layers_evaluated"], 1)

        self.assertEqual(stages["stage6_kpi_reporting"]["status"], "PASSED")
        self.assertTrue(stages["stage6_kpi_reporting"]["number_lock_valid"])

        self.assertEqual(stages["stage7_adversarial"]["status"], "PASSED")
        adv = stages["stage7_adversarial"]["sub_checks"]
        self.assertTrue(adv["injection_blocked"])
        self.assertTrue(adv["agent_governance_write_blocked"])
        self.assertTrue(adv["budget_exhaustion_handled"])
        self.assertTrue(adv["provider_fallback_verified"])
        self.assertTrue(adv["malformed_reply_fails_closed"])
        self.assertTrue(adv["idempotent_resume_verified"])
        self.assertTrue(adv["killswitch_halt_verified"])

        self.assertEqual(stages["stage8_evidence_and_capabilities"]["status"], "PASSED")
        caps = stages["stage8_evidence_and_capabilities"]["capabilities"]
        self.assertEqual(caps["browser"], "NOT_IMPLEMENTED")
        self.assertEqual(caps["desktop"], "NOT_IMPLEMENTED")
