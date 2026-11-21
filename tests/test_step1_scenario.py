"""OpenCode Step 1J — Step 1 Qualification Scenario Test Suite.

Verifies end-to-end execution of scripts/step1_scenario.py across all
backbone subsystems: documents, folios, ledger, industry packs, outbox,
and capability probes.
"""

import os
import unittest
import pytest

from scripts.step1_scenario import run_scenario


class TestStep1Scenario(unittest.TestCase):
    """Verifies that the entire Step 1 foundation & backbone scenario runs cleanly."""

    def test_step1_scenario_runs_cleanly_and_passes_all_steps(self):
        """Exercises the 12-step qualification pipeline and verifies every step passes."""
        report = run_scenario()
        self.assertTrue(report.get("passed"), "Scenario did not complete with passed=True")
        self.assertIn("steps", report)

        steps = report["steps"]
        self.assertEqual(steps["step1_install"]["status"], "PASSED")
        self.assertEqual(steps["step2_tenants"]["status"], "PASSED")
        self.assertEqual(steps["step3_documents"]["status"], "PASSED")
        self.assertEqual(steps["step4_ocr"]["status"], "PASSED")
        self.assertEqual(steps["step5_folios"]["status"], "PASSED")
        self.assertEqual(steps["step6_7_exports"]["status"], "PASSED")
        self.assertEqual(steps["step8_ledger"]["status"], "PASSED")
        self.assertEqual(steps["step9_isolation"]["status"], "PASSED")
        self.assertEqual(steps["step10_outbox"]["status"], "PASSED")
        self.assertEqual(steps["step11_reality_probe"]["status"], "PASSED")

        # Invariant assertions
        self.assertEqual(steps["step3_documents"]["tenant_alpha_count"], 5)
        self.assertEqual(steps["step3_documents"]["tenant_beta_count"], 5)
        self.assertTrue(steps["step6_7_exports"]["pack_alpha"]["verified"])
        self.assertTrue(steps["step6_7_exports"]["pack_beta"]["verified"])
        self.assertTrue(steps["step8_ledger"]["tb_alpha_balanced"])
        self.assertTrue(steps["step8_ledger"]["tb_beta_balanced"])
        self.assertTrue(steps["step9_isolation"]["folio_isolated"])
        self.assertTrue(steps["step9_isolation"]["document_isolated"])
        self.assertTrue(steps["step9_isolation"]["ledger_isolated"])
        self.assertEqual(steps["step10_outbox"]["processed_count"], 1)


if __name__ == "__main__":
    unittest.main()
