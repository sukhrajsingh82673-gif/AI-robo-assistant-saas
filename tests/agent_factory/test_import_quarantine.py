"""Tests for Quarantined Import Lane and Flag-Gated Sandboxes."""

import pytest
from agent_factory.importer.quarantine import (
    QuarantinedAgentImporter, SandboxUnavailableError
)


def test_import_lane_honest_sandbox_unavailable_rejection():
    """In a T0-only host environment, attempting to provision an agent requiring T1 raises SandboxUnavailableError."""
    # Simulate T0-only host environment
    importer = QuarantinedAgentImporter(allowed_tiers=["T0"])

    with pytest.raises(SandboxUnavailableError) as exc_info:
        importer.import_agent(
            source_url="https://github.com/oss-agents/untrusted-scraper",
            tier_requested="T1"
        )

    assert "AF-SANDBOX-UNAVAILABLE" in str(exc_info.value)
    assert "Sandbox tier 'T1' is not provisioned on this host" in str(exc_info.value)


def test_import_lane_declarative_spec_extraction():
    """When the tier is permitted, importer parses manifest as pure data into zonata.agent/v1 spec without executing code."""
    importer = QuarantinedAgentImporter(allowed_tiers=["T0", "T1"])

    manifest = {
        "name": "oss-pdf-parser",
        "description": "Extract tabular data from PDF files"
    }
    spec = importer.import_agent(
        source_url="https://github.com/oss-agents/pdf-parser",
        manifest_data=manifest,
        tier_requested="T1"
    )

    assert spec["apiVersion"] == "zonata.agent/v1"
    assert spec["kind"] == "Agent"
    assert spec["metadata"]["name"] == "oss-pdf-parser"
    assert spec["identity"]["may_use_employees"] is False
    assert spec["metadata"]["labels"]["quarantined"] == "true"
