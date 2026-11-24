"""
Tests for Sub-Step 8I: Step 8 Final Qualification & Scenario (Rule 67, 68, 70, 71, 72, 73, 74, 75, 76)
Executes the end-to-end synthetic scenario across 3 corporate groups, 3 sectors, 3 jurisdictions,
and 3 languages (with Arabic RTL), verifying all 7 adversarial boundary probes are blocked.
"""

import pytest
from scripts.step8_scenario import run_step8_scenario


class TestStep8IFinalScenario:

    def test_01_end_to_end_multi_sector_scenario_qualification(self):
        summary = run_step8_scenario()

        # Status & Corporate Group Coverage
        assert summary["status"] == "SCENARIO_QUALIFIED"
        assert summary["corporate_groups_evaluated"] == 3
        assert set(summary["isic_sectors_covered"]) == {"C28", "G47", "H52"}
        assert set(summary["jurisdictions_evaluated"]) == {"DE", "IN", "US", "SA", "BE"}

        # Multi-Lingual & RTL Layout
        assert "ar" in summary["languages_tested"]
        assert "de" in summary["languages_tested"]
        assert summary["rtl_layout_verified"] is True

        # Operations & Invoicing
        assert summary["simulated_days"] == 30
        assert "ZUGFeRD 2.2" in summary["e_invoicing_standards_verified"]
        assert "India IRP" in summary["e_invoicing_standards_verified"]
        assert "Peppol BIS 3.0" in summary["e_invoicing_standards_verified"]

        # Intercompany Accounting Invariant
        assert summary["intercompany_elimination_net_variance"] == 0

        # Adversarial Security & Sector Boundary Probes
        assert summary["adversarial_probes_tested"] == 7
        assert summary["adversarial_probes_blocked"] == 7

        # Deterministic SHA-256 Digest
        assert len(summary["scenario_digest_sha256"]) == 64
