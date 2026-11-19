"""Property and Determinism Tests for Permission Profile Calculator (TEMPLATES §5.1)."""

import pytest
from agent_factory.spec.calculator import compute_permission_profile, PermissionProfile


def test_permission_profile_subset_property():
    """Property 1: Granted tools and privileges must be a subset of the request and every ceiling."""
    req_perms = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read", "write"], "max_calls": 50},
            {"name": "db.query_readonly", "scopes": ["read"], "max_calls": 30},
            {"name": "doc.generate", "scopes": ["write"], "max_calls": 10}
        ],
        "network": {"external": True, "allowed_hosts": ["api.example.com", "internal.corp"]},
        "writes": True,
        "data_classification_max": "confidential"
    }

    # Template allows only web.fetch_page (read) and doc.generate (write), no external network
    template_ceil = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read"], "max_calls": 20},
            {"name": "doc.generate", "scopes": ["write"], "max_calls": 5}
        ],
        "network": {"external": False, "allowed_hosts": ["api.example.com"]},
        "writes": True,
        "data_classification_max": "internal"
    }

    registry = {"web.fetch_page", "doc.generate", "db.query_readonly"}

    profile = compute_permission_profile(
        requested_permissions=req_perms,
        template_max_grantable=template_ceil,
        registry=registry
    )

    granted_tool_names = {t["name"] for t in profile.granted_tools}
    # db.query_readonly is not in template ceiling -> dropped
    assert "db.query_readonly" not in granted_tool_names
    assert "web.fetch_page" in granted_tool_names
    assert "doc.generate" in granted_tool_names

    # Scopes and max_calls restricted by template
    web_tool = [t for t in profile.granted_tools if t["name"] == "web.fetch_page"][0]
    assert web_tool["scopes"] == ["read"]  # write dropped
    assert web_tool["max_calls"] == 20     # min(50, 20)

    # External network disabled by template
    assert profile.can_external_network is False
    # Data classification narrowed to internal
    assert profile.data_classification_max == "internal"


def test_permission_profile_idempotent_property():
    """Property 2: Passing granted profile permissions back into the calculator yields the identical profile."""
    req_perms = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read"], "max_calls": 20},
            {"name": "knowledge.search", "scopes": ["read"], "max_calls": 15}
        ],
        "network": {"external": False, "allowed_hosts": ["example.org"]},
        "writes": False,
        "data_classification_max": "internal"
    }
    registry = {"web.fetch_page", "knowledge.search"}

    prof1 = compute_permission_profile(req_perms, registry=registry)

    # Re-run calculator using output of prof1 as requested permissions
    req_perms2 = {
        "tools": prof1.granted_tools,
        "network": {"external": prof1.can_external_network, "allowed_hosts": prof1.network_allowed_hosts},
        "writes": prof1.can_write,
        "data_classification_max": prof1.data_classification_max
    }
    prof2 = compute_permission_profile(req_perms2, registry=registry)

    assert prof1.granted_tools == prof2.granted_tools
    assert prof1.network_allowed_hosts == prof2.network_allowed_hosts
    assert prof1.can_external_network == prof2.can_external_network
    assert prof1.can_write == prof2.can_write
    assert prof1.data_classification_max == prof2.data_classification_max
    assert prof1.risk_tier == prof2.risk_tier


def test_permission_profile_monotone_property():
    """Property 3: Monotone - narrowing any input only narrows or keeps equal the output."""
    req_perms = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read", "write"], "max_calls": 40}
        ],
        "network": {"external": True, "allowed_hosts": ["a.com", "b.com"]},
        "writes": True,
        "data_classification_max": "confidential"
    }
    registry = {"web.fetch_page"}

    # Base profile
    p_base = compute_permission_profile(req_perms, registry=registry)

    # Narrow tenant policy
    strict_tenant = {
        "allowed_tools": ["web.fetch_page"],
        "network_allowed": False,
        "writes_allowed": False,
        "data_classification_max": "internal"
    }
    p_narrow = compute_permission_profile(req_perms, tenant_policy=strict_tenant, registry=registry)

    assert p_narrow.can_external_network is False
    assert p_narrow.can_write is False
    assert p_narrow.data_classification_max == "internal"
    assert len(p_narrow.granted_tools) <= len(p_base.granted_tools)


def test_drops_unregistered_tools():
    req_perms = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read"], "max_calls": 10},
            {"name": "malicious.exploit_tool", "scopes": ["execute"], "max_calls": 5}
        ]
    }
    registry = {"web.fetch_page"}
    profile = compute_permission_profile(req_perms, registry=registry)
    granted_names = [t["name"] for t in profile.granted_tools]
    assert "web.fetch_page" in granted_names
    assert "malicious.exploit_tool" not in granted_names
    assert any("not found in capability registry" in n for n in profile.reduction_notes)


def test_constitution_denies_employee_access_and_direct_prod():
    req_perms = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read"], "max_calls": 10},
            {"name": "internal.employee_command", "scopes": ["execute"], "max_calls": 10},
            {"name": "db.direct_prod_write", "scopes": ["write"], "max_calls": 10}
        ]
    }
    constitution = {"forbidden_tools": ["db.direct_prod_write"]}
    registry = {"web.fetch_page", "internal.employee_command", "db.direct_prod_write"}

    profile = compute_permission_profile(req_perms, constitution=constitution, registry=registry)
    granted_names = [t["name"] for t in profile.granted_tools]
    assert "web.fetch_page" in granted_names
    assert "internal.employee_command" not in granted_names
    assert "db.direct_prod_write" not in granted_names
    assert any("rejected by ZONATA Constitution" in n for n in profile.reduction_notes)
