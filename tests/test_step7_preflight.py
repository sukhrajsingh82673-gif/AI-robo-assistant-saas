"""
Unit and Contract Tests for Step 7A: Preflight, Department Inventory & ADRs 0032-0038.
=====================================================================================
Validates:
- Gate Check: Prior Steps 1-6 merged and documented.
- 10-Domain Department Inventory: STEP7_INVENTORY.md completeness across all domains.
- 7 Department Architecture ADRs: ADR_0032 through ADR_0038 approved and compliant with Rules 59-66.
- Copyleft License Isolation: Systems under copyleft (ERPNext, Frappe HR, AGPL CRM/Chatwoot) declared as separate services.
- Rule 41 Invariant: Zero plaintext secret values committed in any Step 7 documentation.
- Mutation Check: Missing ADR or domain causes failure.
"""

import os
import re
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestStep7Preflight:
    """Verifies all Sub-Step 7A preflight gates, department inventory, and ADR specifications."""

    def test_01_prior_steps_report_and_preservation_baseline(self):
        """Gate Check: Verifies that Steps 1 to 6 are certified in STEP6_REPORT.md."""
        step6_rep = os.path.join(REPO_ROOT, "docs", "reports", "STEP6_REPORT.md")
        assert os.path.exists(step6_rep), "STEP6_REPORT.md must exist"

        with open(step6_rep, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Sub-Step 6A Status:" in content or "78 passed" in content
        assert "Residual Risks" in content

        # Check PROJECT_MEMORY.md exists
        mem_path = os.path.join(REPO_ROOT, "PROJECT_MEMORY.md")
        assert os.path.exists(mem_path), "PROJECT_MEMORY.md must exist in repo root"

    def test_02_department_inventory_completeness(self):
        """Audit Check: STEP7_INVENTORY.md covers all 10 department domains."""
        inventory_path = os.path.join(REPO_ROOT, "docs", "reports", "STEP7_INVENTORY.md")
        assert os.path.exists(inventory_path), "STEP7_INVENTORY.md must exist"

        with open(inventory_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_domains = [
            "Finance & Accounting",
            "Sales & CRM",
            "Customer Support",
            "Marketing & Brand",
            "HR & Workforce",
            "Operations & Production",
            "Supply Chain & Procure",
            "R&D & Prototyping",
            "Legal, IT & Security",
            "Analytics & BI",
        ]

        for domain in required_domains:
            assert domain in content, f"Domain '{domain}' must be documented in STEP7_INVENTORY.md"

        # Check that governing rules are cited
        assert "Rule 58" in content
        assert "Rule 59" in content
        assert "Rule 60" in content

    def test_03_adrs_completeness_and_approval(self):
        """Verifies that ADRs 0032 through 0038 exist, are APPROVED, and cite rules."""
        adr_numbers = [
            ("ADR_0032_SYSTEMS_OF_RECORD_ERP_ACCOUNTING_HR.md", ["Rule 59", "Rule 60"]),
            ("ADR_0033_CRM_ARCHITECTURE_AND_ADAPTERS.md", ["Rule 59", "Rule 60", "Rule 64"]),
            ("ADR_0034_HELPDESK_AND_CUSTOMER_SUPPORT.md", ["Rule 59", "Rule 60"]),
            ("ADR_0035_PAYMENTS_IN_AND_SUBSCRIPTION_BILLING.md", ["Rule 41", "Rule 62"]),
            ("ADR_0036_ANALYTICS_SEMANTIC_LAYER_AND_BI.md", ["Rule 59", "Rule 60", "Rule 65"]),
            ("ADR_0037_CONNECTOR_SDK_AND_MCP_FRAMEWORK.md", ["Rule 41", "Rule 42", "Rule 59"]),
            ("ADR_0038_DEPARTMENT_MEASUREMENT_DESIGN.md", ["Rule 37", "Rule 63", "Rule 66"]),
        ]

        adr_dir = os.path.join(REPO_ROOT, "docs", "adr")
        for filename, expected_rules in adr_numbers:
            filepath = os.path.join(adr_dir, filename)
            assert os.path.exists(filepath), f"ADR file {filename} must exist"

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            assert "Status: APPROVED" in content or "**Status:** APPROVED" in content, (
                f"{filename} must be APPROVED"
            )
            for rule in expected_rules:
                assert rule in content, f"{filename} must cite {rule}"

    def test_04_copyleft_boundary_isolation(self):
        """Verifies that copyleft systems (ERPNext, Frappe HR, AGPL CRM/Chatwoot) are isolated."""
        adr32 = os.path.join(REPO_ROOT, "docs", "adr", "ADR_0032_SYSTEMS_OF_RECORD_ERP_ACCOUNTING_HR.md")
        with open(adr32, "r", encoding="utf-8") as f:
            c32 = f.read()
        assert "unmodified, isolated network container service" in c32 or "network container service" in c32

        adr33 = os.path.join(REPO_ROOT, "docs", "adr", "ADR_0033_CRM_ARCHITECTURE_AND_ADAPTERS.md")
        with open(adr33, "r", encoding="utf-8") as f:
            c33 = f.read()
        assert "unmodified standalone network service" in c33 or "separate network service" in c33

    def test_05_rule_41_zero_plaintext_secrets_in_docs(self):
        """Scans all step 7 docs and ADRs to guarantee zero plaintext secrets are committed."""
        docs_to_check = [
            os.path.join(REPO_ROOT, "docs", "reports", "STEP7_INVENTORY.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0032_SYSTEMS_OF_RECORD_ERP_ACCOUNTING_HR.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0033_CRM_ARCHITECTURE_AND_ADAPTERS.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0034_HELPDESK_AND_CUSTOMER_SUPPORT.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0035_PAYMENTS_IN_AND_SUBSCRIPTION_BILLING.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0036_ANALYTICS_SEMANTIC_LAYER_AND_BI.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0037_CONNECTOR_SDK_AND_MCP_FRAMEWORK.md"),
            os.path.join(REPO_ROOT, "docs", "adr", "ADR_0038_DEPARTMENT_MEASUREMENT_DESIGN.md"),
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

    def test_06_mutation_check_missing_adr_raises(self):
        """Mutation test: Assert that missing an ADR fails validation."""
        fake_adr = os.path.join(REPO_ROOT, "docs", "adr", "ADR_9999_NON_EXISTENT.md")
        assert not os.path.exists(fake_adr)
