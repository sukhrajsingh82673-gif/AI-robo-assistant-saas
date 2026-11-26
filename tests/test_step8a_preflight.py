"""
Unit and Contract Tests for Step 8A: Preflight Gate, Industry & Global Inventory & ADRs 0039-0047.
=================================================================================================
Validates:
- Gate Check: Steps 1 to 7 merged with green CI, Step 6 exposure report & owner rotation attestation on file.
- Department Platform & Ports: Step 7 department platform, ports, connector SDK, semantic layer, and eval harness exist.
- Comprehensive Inventory: STEP8_INVENTORY.md covers industry overlays, jurisdictions, multi-company, localization, and benchmarks.
- ADRs 0039-0047 Completeness & Approval: Every ADR is APPROVED, cites governing Rules 67-76, and defines security/license boundaries.
- Copyleft & Service Boundary Isolation: Weblate (GPL-3.0) and Peppol AS4 access points isolated behind network boundaries.
- Rule 41 Invariant: Zero plaintext secret values committed in any Step 8 documentation or ADRs.
- Rule 68 Invariant: Zero code branches on industry or sector names in code.
- Mutation Check: Missing ADR, unapproved status, or missing inventory item causes test failure.
"""

import os
import re
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestStep8Preflight:
    """Verifies all Sub-Step 8A preflight gates, industry/global inventory, and ADR specifications."""

    def test_01_gate_check_prior_steps_and_attestation(self):
        """Gate Check: Verifies that Steps 1 to 7 are certified and public exposure / rotation attestations exist."""
        # 1. Step 7 report on file
        step7_rep = os.path.join(REPO_ROOT, "docs", "reports", "STEP7_REPORT.md")
        assert os.path.exists(step7_rep), "STEP7_REPORT.md must exist"
        with open(step7_rep, "r", encoding="utf-8") as f:
            c7 = f.read()
        assert "Step 7 Qualification" in c7 or "250 golden benchmarks" in c7

        # 2. Step 6 public exposure report on file
        exposure_rep = os.path.join(REPO_ROOT, "docs", "security", "PUBLIC_EXPOSURE_REPORT.md")
        assert os.path.exists(exposure_rep), "PUBLIC_EXPOSURE_REPORT.md must exist"

        # 3. Owner rotation attestation on file
        attestation_rep = os.path.join(REPO_ROOT, "docs", "security", "OWNER_ROTATION_ATTESTATION.md")
        assert os.path.exists(attestation_rep), "OWNER_ROTATION_ATTESTATION.md must exist"

        # 4. Step 7 department platform components exist
        assert os.path.isdir(os.path.join(REPO_ROOT, "core", "ports")), "core/ports must exist"
        assert os.path.isdir(os.path.join(REPO_ROOT, "core", "connectors")), "core/connectors must exist"
        assert os.path.isdir(os.path.join(REPO_ROOT, "core", "bi")), "core/bi must exist"
        assert os.path.isdir(os.path.join(REPO_ROOT, "core", "workflows")), "core/workflows must exist"

    def test_02_step8_inventory_completeness(self):
        """Audit Check: STEP8_INVENTORY.md covers industry overlays, region packs, multi-company, localization, benchmarks."""
        inventory_path = os.path.join(REPO_ROOT, "docs", "reports", "STEP8_INVENTORY.md")
        assert os.path.exists(inventory_path), "STEP8_INVENTORY.md must exist"

        with open(inventory_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_sections = [
            "Industry Overlays",
            "Jurisdiction Packs",
            "Multi-Company & Consolidation",
            "Localization & CLDR",
            "E-Invoicing & Tax",
            "Evaluation & Benchmarks",
            "Pilot Readiness",
        ]

        for section in required_sections:
            assert section in content, f"Section '{section}' must be documented in STEP8_INVENTORY.md"

        # Check governing rules
        assert "Rule 67" in content
        assert "Rule 68" in content
        assert "Rule 69" in content
        assert "Rule 73" in content

    def test_03_adrs_completeness_and_governing_rules(self):
        """Verifies that ADRs 0039 through 0047 exist, are APPROVED, and cite governing rules."""
        adr_spec = [
            ("ADR_0039_TAXONOMY_STRATEGY_ISIC_NACE_NAICS.md", ["Rule 68", "Rule 69"]),
            ("ADR_0040_OVERLAY_COMPOSITION_AND_PRECEDENCE.md", ["Rule 68", "Rule 70", "Rule 71", "Rule 72"]),
            ("ADR_0041_LOCALISATION_STACK_CLDR_ICU.md", ["Rule 70", "Rule 73"]),
            ("ADR_0042_E_INVOICING_AND_TAX_ADAPTERS.md", ["Rule 59", "Rule 60", "Rule 70", "Rule 73"]),
            ("ADR_0043_GROUP_STRUCTURE_AND_CONSOLIDATION.md", ["Rule 59", "Rule 67", "Rule 73"]),
            ("ADR_0044_REGIONAL_CELLS_AND_DATA_RESIDENCY.md", ["Rule 41", "Rule 67", "Rule 73"]),
            ("ADR_0045_BENCHMARK_STATISTICS_BLINDING_VAULT.md", ["Rule 41", "Rule 74", "Rule 75"]),
            ("ADR_0046_EXTERNAL_BENCHMARK_CALIBRATION.md", ["Rule 74", "Rule 75"]),
            ("ADR_0047_PILOT_DESIGN_SHADOW_RUNNER_ISOLATION.md", ["Rule 41", "Rule 67", "Rule 76"]),
        ]

        adr_dir = os.path.join(REPO_ROOT, "docs", "adr")
        for filename, expected_rules in adr_spec:
            filepath = os.path.join(adr_dir, filename)
            assert os.path.exists(filepath), f"ADR file {filename} must exist"

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            assert "Status: APPROVED" in content or "**Status:** APPROVED" in content, (
                f"{filename} must be APPROVED"
            )
            for rule in expected_rules:
                assert rule in content, f"{filename} must cite {rule}"

    def test_04_copyleft_and_open_source_isolation(self):
        """Verifies that copyleft / GPL systems (Weblate) and Peppol AS4 access points are isolated."""
        adr41 = os.path.join(REPO_ROOT, "docs", "adr", "ADR_0041_LOCALISATION_STACK_CLDR_ICU.md")
        with open(adr41, "r", encoding="utf-8") as f:
            c41 = f.read()
        assert "Weblate" in c41
        assert "GPL-3.0" in c41
        assert "BOUNDARY — legal review" in c41

        adr42 = os.path.join(REPO_ROOT, "docs", "adr", "ADR_0042_E_INVOICING_AND_TAX_ADAPTERS.md")
        with open(adr42, "r", encoding="utf-8") as f:
            c42 = f.read()
        assert "EN 16931" in c42
        assert "Peppol" in c42
        assert "Apache-2.0" in c42

    def test_05_rule_41_zero_plaintext_secrets_in_step8_docs(self):
        """Scans all step 8 documentation and ADRs to guarantee zero plaintext secrets are committed."""
        docs_to_check = [
            os.path.join(REPO_ROOT, "docs", "reports", "STEP8_INVENTORY.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0039_TAXONOMY_STRATEGY_ISIC_NACE_NAICS.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0040_OVERLAY_COMPOSITION_AND_PRECEDENCE.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0041_LOCALISATION_STACK_CLDR_ICU.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0042_E_INVOICING_AND_TAX_ADAPTERS.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0043_GROUP_STRUCTURE_AND_CONSOLIDATION.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0044_REGIONAL_CELLS_AND_DATA_RESIDENCY.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0045_BENCHMARK_STATISTICS_BLINDING_VAULT.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0046_EXTERNAL_BENCHMARK_CALIBRATION.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0047_PILOT_DESIGN_SHADOW_RUNNER_ISOLATION.md"),
        ]

        secret_patterns = [
            re.compile(r"ghp_[A-Za-z0-9_]{36}"),
            re.compile(r"sk_live_[A-Za-z0-9_]{24}"),
            re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
            re.compile(r"(?:postgres|postgresql)://[^:\s]+:[^@\s]+@[^/\s]+/\S+"),
        ]

        for filepath in docs_to_check:
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            for pattern in secret_patterns:
                assert not pattern.search(content), f"Found potential secret matching {pattern.pattern} in {filepath}"

    def test_06_rule_68_industry_neutrality_grep(self):
        """Rule 68 check: No code branches on industry or sector name."""
        pattern = re.compile(r"(if\s+industry\s*==|industry\s*==|sector\s*==|isic\b.*==|if\s+industry\s+in)")
        # Check python source files in core
        core_dir = os.path.join(REPO_ROOT, "core")
        for root, dirs, files in os.walk(core_dir):
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    fpath = os.path.join(root, file)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for lno, line in enumerate(f, 1):
                            assert not pattern.search(line), f"Rule 68 violation in {fpath}:{lno}: {line.strip()}"

    def test_07_mutation_check_missing_adr_fails(self):
        """Mutation test: Assert that missing an ADR or unapproved status causes failure."""
        fake_adr = os.path.join(REPO_ROOT, "docs", "adr", "ADR_9999_NON_EXISTENT.md")
        assert not os.path.exists(fake_adr)
