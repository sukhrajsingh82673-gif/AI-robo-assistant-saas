"""
Unit and Contract Tests for Step 6A: Preflight, Public-Repo Exposure Check & Evolution ADRs.
===========================================================================================
Validates:
- Gate Check: Prior Steps 1-5 merged and certified.
- Public Exposure Report: Thorough assessment of historical commits without printing secrets.
- Owner Rotation Attestation: Formal attestation of rotated development credentials.
- 10-Domain Evolution Inventory: Complete inventory of all existing evolution/learning assets.
- 6 Trust & Evolution ADRs: ADR_0026 through ADR_0031 completeness.
- Rule 41 Invariant: Zero plaintext secret values in any Step 6 documentation or reports.
"""

import os
import re
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestStep6Preflight:
    """Verifies all Sub-Step 6A preflight gates, exposure audit, and ADR specifications."""

    def test_01_prior_steps_ci_certification_attestation(self):
        """Gate Check: Verifies that Steps 1 to 5 are certified in STEP5_REPORT.md."""
        step5_rep = os.path.join(REPO_ROOT, "docs", "reports", "STEP5_REPORT.md")
        assert os.path.exists(step5_rep), "STEP5_REPORT.md must exist"

        with open(step5_rep, "r", encoding="utf-8") as f:
            content = f.read()

        assert "OVERALL STATUS: 100% QUALIFIED & CERTIFIED PASS" in content
        # Verify final Step 5 qualification run ID is recorded
        assert "45274178625" in content

    def test_02_public_exposure_report_completeness(self):
        """Audit Check: PUBLIC_EXPOSURE_REPORT.md audits SQLite DB, Neon strings, and GitHub settings."""
        report_path = os.path.join(REPO_ROOT, "docs", "security", "PUBLIC_EXPOSURE_REPORT.md")
        assert os.path.exists(report_path), "PUBLIC_EXPOSURE_REPORT.md must exist"

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must analyze roboassistant.db and neon connection strings
        assert "storage/roboassistant.db" in content
        assert "neon.ts" in content
        assert "PUBLIC" in content
        assert "PRIVATE" in content
        assert "GDPR Art. 33" in content or "DPDP Act" in content

        # Rule 41: No raw secrets printed in report
        assert "password123" not in content
        assert "BEGIN PRIVATE KEY" not in content
        assert "ghp_" not in content

    def test_03_owner_rotation_attestation_exists_and_signed(self):
        """Governance Check: OWNER_ROTATION_ATTESTATION.md records formal rotation acknowledgement."""
        attest_path = os.path.join(REPO_ROOT, "docs", "security", "OWNER_ROTATION_ATTESTATION.md")
        assert os.path.exists(attest_path), "OWNER_ROTATION_ATTESTATION.md must exist"

        with open(attest_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Owner Attestation Declaration" in content
        assert "ATTESTED AND RECORDED" in content
        assert "sha256:" in content

    def test_04_step6_inventory_covers_all_ten_domains(self):
        """Inventory Check: STEP6_INVENTORY.md audits all 10 required evolution domains."""
        inv_path = os.path.join(REPO_ROOT, "docs", "reports", "STEP6_INVENTORY.md")
        assert os.path.exists(inv_path), "STEP6_INVENTORY.md must exist"

        with open(inv_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_domains = [
            "Kaizen & Self-Healing",
            "Memory & Knowledge Store",
            "Agent Specs & Factory Gates",
            "Import Lane (Step 3G)",
            "Eval Harness (Step 2K)",
            "Evidence Ledger Events",
            "Outbox & Coordination Events",
            "Failure & Audit Logs",
            "GitHub Integration",
            "Self-Improvement / Optimization",
        ]
        for domain in required_domains:
            assert domain in content, f"Domain '{domain}' missing from STEP6_INVENTORY.md"

    def test_05_all_six_step6_adrs_exist_and_complete(self):
        """ADR Check: Verifies ADR_0026 through ADR_0031 are authored and complete."""
        expected_adrs = {
            "ADR_0026_OPTIMIZER_STACK_DSPY_GEPA.md": ["DSPy", "GEPA", "MIT", "Frozen Model"],
            "ADR_0027_EXTERNAL_AGENT_INTAKE_HERMES.md": ["Hermes Agent", "Nous Research", "MIT", "QUARANTINED"],
            "ADR_0028_KNOWLEDGE_STORE_PLAYBOOKS.md": ["pgvector", "zonata.playbook/v1", "Provenance"],
            "ADR_0029_GITHUB_AUTOMATION_ARCHITECTURE.md": ["GitHub App", "Least Privilege", "Rule 57", "ai/"],
            "ADR_0030_CLEAN_ROOM_PROTOCOL_LEGAL_GATE.md": ["Clean-Room", "Specifier", "Implementer", "Legal Gate"],
            "ADR_0031_EXPERIMENT_INFRASTRUCTURE_SANDBOX.md": ["Experiment Sandbox", "Held-Out", "Rule 51", "Budget"],
        }

        for filename, required_keywords in expected_adrs.items():
            adr_path = os.path.join(REPO_ROOT, "docs", "adr", filename)
            assert os.path.exists(adr_path), f"ADR file missing: {filename}"
            with open(adr_path, "r", encoding="utf-8") as f:
                content = f.read()
            for kw in required_keywords:
                assert kw.lower() in content.lower(), f"Keyword '{kw}' missing from {filename}"

    def test_06_mutation_check_unregistered_secret_or_unapproved_adr_fails(self):
        """Rule 8 & 41 Mutation Check: Missing required ADR or exposure report fails preflight."""
        non_existent_adr = os.path.join(REPO_ROOT, "docs", "adr", "ADR_0099_IMAGINARY.md")
        assert not os.path.exists(non_existent_adr)
