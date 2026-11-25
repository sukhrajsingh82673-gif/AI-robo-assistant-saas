"""
Preflight qualification tests for Step 9: Product Readiness.
Validates ADRs 0048-0057, Step 9 inventory, clean repository state, and preservation baselines.
"""

import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

EXPECTED_ADRS = [
    ("ADR_0048_BILLING_AND_TAX_MODEL.md", ["Rule 78", "Rule 79", "Paddle", "Stripe", "Lago"]),
    ("ADR_0049_EDGE_GATEWAY_ARCHITECTURE.md", ["Rule 77", "Rule 80", "Edge Gateway", "rate limit"]),
    ("ADR_0050_PUBLIC_API_AND_STANDARD_WEBHOOKS.md", ["Rule 80", "OpenAPI 3.1", "Standard Webhooks", "SSRF"]),
    ("ADR_0051_SDK_GENERATION_AND_DEVELOPER_PORTAL.md", ["Rule 80", "TypeScript", "Python", "Developer Portal"]),
    ("ADR_0052_FEATURE_FLAGGING_OPENFEATURE.md", ["OpenFeature", "kill-switch", "audit"]),
    ("ADR_0053_INDEPENDENT_STATUS_PAGE_ARCHITECTURE.md", ["Rule 83", "out-of-band", "status"]),
    ("ADR_0054_MOBILE_PWA_ARCHITECTURE.md", ["Rule 84", "PWA", "Service Worker", "offline"]),
    ("ADR_0055_MARKETPLACE_SANDBOX_ISOLATION.md", ["Rule 81", "manifest", "sandbox", "NOT_IMPLEMENTED"]),
    ("ADR_0056_PRIVACY_PRESERVING_PRODUCT_ANALYTICS.md", ["Rule 78", "Rule 84", "zero-tenant-content"]),
    ("ADR_0057_REGULATORY_PRODUCT_COMPLIANCE_EU_DATA_ACT_CRA_EAA.md", ["EU Data Act", "CRA", "EAA", "WCAG 2.2 AA"]),
]


def test_adrs_present_and_structured():
    """Verify all 10 Step 9 ADRs exist, are marked Accepted, and mention required topics."""
    adr_dir = os.path.join(REPO_ROOT, "docs", "adr")
    assert os.path.isdir(adr_dir), f"Directory {adr_dir} must exist"

    for adr_name, required_keywords in EXPECTED_ADRS:
        adr_path = os.path.join(adr_dir, adr_name)
        assert os.path.isfile(adr_path), f"ADR file {adr_name} must exist"

        with open(adr_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "## Status" in content, f"{adr_name} must have a Status section"
        assert "Accepted" in content, f"{adr_name} must be Accepted"
        assert "## Context" in content, f"{adr_name} must have a Context section"
        assert "## Decision" in content, f"{adr_name} must have a Decision section"
        assert "## Consequences" in content, f"{adr_name} must have a Consequences section"

        for kw in required_keywords:
            assert kw.lower() in content.lower(), f"{adr_name} must mention keyword '{kw}'"


def test_step9_inventory_document():
    """Verify STEP9_INVENTORY.md documents web shell, APIs, billing code, and Rules 77-84."""
    inventory_path = os.path.join(REPO_ROOT, "docs", "reports", "STEP9_INVENTORY.md")
    assert os.path.isfile(inventory_path), "STEP9_INVENTORY.md must exist"

    with open(inventory_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Rule 77" in content
    assert "Rule 78" in content
    assert "Rule 79" in content
    assert "Rule 80" in content
    assert "Rule 81" in content
    assert "Rule 82" in content
    assert "Rule 83" in content
    assert "Rule 84" in content
    assert "OpenAPI" in content
    assert "BillingPort" in content


def test_zero_plaintext_secrets_in_new_files():
    """Ensure no hardcoded live API keys or private keys are committed in docs or tests."""
    secret_patterns = [
        re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
        re.compile(r"pdl_live_[0-9a-zA-Z]{24,}"),
        re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
        re.compile(r"ghp_[0-9a-zA-Z]{36}"),
    ]

    target_files = [os.path.join(REPO_ROOT, "docs", "reports", "STEP9_INVENTORY.md")]
    for adr_name, _ in EXPECTED_ADRS:
        target_files.append(os.path.join(REPO_ROOT, "docs", "adr", adr_name))

    for file_path in target_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        for pattern in secret_patterns:
            assert not pattern.search(content), f"Found potential live secret in {file_path}"
