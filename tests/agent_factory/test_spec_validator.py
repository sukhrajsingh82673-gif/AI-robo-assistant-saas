"""Tests for Agent Factory Spec Schema & Semantic Validator (Gate G01)."""

import pytest
from agent_factory.spec.validator import SpecValidator, scan_for_credentials, shannon_entropy


@pytest.fixture
def valid_spec():
    return {
        "apiVersion": "zonata.agent/v1",
        "kind": "Agent",
        "metadata": {
            "name": "financial-auditor",
            "display_name": "Financial Auditor",
            "version": "1.0.0",
            "category": "finance",
            "risk_tier": "R1"
        },
        "identity": {
            "principal_kind": "agent",
            "tenant_bound": True,
            "may_use_employees": False
        },
        "role": {
            "title": "Ledger Auditor",
            "mission": "Audit daily reconciliation logs for balance discrepancies.",
            "responsibilities": ["Inspect journals", "Verify totals"],
            "out_of_scope": ["Executing payments", "Modifying GL balances"],
            "success_criteria": ["All balance calculations are mathematically sound"],
            "instructions": "Audit records following strict double-entry standards."
        },
        "model": {
            "requirements": {
                "complexity": "high",
                "privacy": "confidential"
            }
        },
        "capabilities": {
            "requested": [
                {"key": "tool.use"}
            ]
        },
        "permissions": {
            "requested": {
                "tools": [
                    {"name": "db.query_readonly", "scopes": ["read"], "max_calls": 20}
                ],
                "network": {
                    "external": False,
                    "allowed_hosts": []
                },
                "writes": False
            }
        },
        "workflow": {
            "type": "sequential"
        },
        "memory": {
            "conversation": {"enabled": True, "max_messages": 20},
            "pii_policy": "redact"
        },
        "limits": {
            "max_steps": 30,
            "timeout_seconds": 600,
            "max_cost_usd_per_task": 1.0
        },
        "io": {
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"}
        },
        "observability": {
            "trace": True,
            "capture_content": "redacted"
        },
        "tests": {
            "author_cases": [
                {"id": "smoke", "input": {}, "expect": {"ok": True}}
            ],
            "dataset_refs": ["finance-eval@1.0"]
        }
    }


def test_valid_spec_passes(valid_spec):
    validator = SpecValidator()
    result = validator.validate(valid_spec)
    assert result.is_valid, f"Expected valid spec, got errors: {result.errors}"


def test_missing_required_section_fails(valid_spec):
    validator = SpecValidator()
    del valid_spec["limits"]
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("limits" in e for e in result.errors)


def test_invalid_api_version(valid_spec):
    validator = SpecValidator()
    valid_spec["apiVersion"] = "zonata.agent/v2"
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("Unsupported apiVersion" in e for e in result.errors)


def test_g01_may_not_use_employees(valid_spec):
    validator = SpecValidator()
    valid_spec["identity"]["may_use_employees"] = True
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("may_use_employees" in e for e in result.errors)


def test_g01_rejects_credential_patterns(valid_spec):
    validator = SpecValidator()
    # Inject OpenAI key
    valid_spec["role"]["instructions"] += " Use api key sk-1234567890abcdefghijklmnopqrstuvwxyz for requests."
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("Credential pattern detected" in e for e in result.errors)


def test_g01_rejects_private_key_pattern(valid_spec):
    validator = SpecValidator()
    valid_spec["role"]["instructions"] += "\n-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("Credential pattern detected" in e for e in result.errors)


def test_g01_rejects_url_with_token(valid_spec):
    validator = SpecValidator()
    valid_spec["role"]["instructions"] += " Call https://api.internal.org/data?api_key=secret_token_12345"
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("URL with embedded credential" in e for e in result.errors)


def test_g01_rejects_high_entropy_token(valid_spec):
    validator = SpecValidator()
    # 40 chars of high entropy random characters
    high_ent_token = "K9zLp2VxN8wR1qTyU7mBcDfGhJkLmPqRsTuVwXyZ0123"
    valid_spec["role"]["instructions"] += f" Connect with token {high_ent_token}"
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("High-entropy token" in e for e in result.errors)


def test_instruction_length_cap(valid_spec):
    validator = SpecValidator()
    valid_spec["role"]["instructions"] = "A" * 20001
    result = validator.validate(valid_spec)
    assert not result.is_valid
    assert any("exceeds maximum length of 20000" in e for e in result.errors)
