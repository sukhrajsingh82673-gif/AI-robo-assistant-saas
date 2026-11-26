"""Acceptance Test AT-11: Prevent Self-Granted Permissions."""

import pytest
from agent_factory.spec.calculator import compute_permission_profile
from agent_factory.build.governed_call import governed_call, GovernedCallContext, GovernedCallDeniedError
from agent_factory.adapters.fakes import FakeAuthorityPort, FakeEvidencePort, FakeKillSwitchPort


def test_at11_prevent_self_granted_permissions():
    """Verify that an agent cannot self-grant permissions beyond template/tenant ceilings."""
    # 1. Spec attempts to request forbidden tools and full external network
    adversarial_request = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read", "write"], "max_calls": 100},
            {"name": "db.direct_prod_write", "scopes": ["write"], "max_calls": 50},
            {"name": "internal.employee_command", "scopes": ["execute"], "max_calls": 50}
        ],
        "network": {
            "external": True,
            "allowed_hosts": ["*"]
        },
        "writes": True,
        "data_classification_max": "restricted"
    }

    # Template strictly limits to read-only web fetch and internal data classification
    template_ceiling = {
        "tools": [
            {"name": "web.fetch_page", "scopes": ["read"], "max_calls": 20}
        ],
        "network": {
            "external": False,
            "allowed_hosts": ["safe.domain.org"]
        },
        "writes": False,
        "data_classification_max": "internal"
    }

    constitution = {
        "forbidden_tools": ["db.direct_prod_write"],
        "writes_allowed": False
    }

    registry = {"web.fetch_page", "db.direct_prod_write", "internal.employee_command"}

    profile = compute_permission_profile(
        requested_permissions=adversarial_request,
        template_max_grantable=template_ceiling,
        constitution=constitution,
        registry=registry
    )

    # Assert that all escalated permissions were stripped:
    granted_names = {t["name"] for t in profile.granted_tools}
    assert "db.direct_prod_write" not in granted_names
    assert "internal.employee_command" not in granted_names
    assert "web.fetch_page" in granted_names

    # Scopes clamped to read only
    web_tool = [t for t in profile.granted_tools if t["name"] == "web.fetch_page"][0]
    assert web_tool["scopes"] == ["read"]
    assert web_tool["max_calls"] == 20

    # Writes and external network denied
    assert profile.can_write is False
    assert profile.can_external_network is False
    assert profile.data_classification_max == "internal"

    # 2. Runtime verification: GovernedCall denies any call to a disallowed tool
    auth = FakeAuthorityPort(allow_all=False)
    ev = FakeEvidencePort()
    ks = FakeKillSwitchPort()

    ctx = GovernedCallContext(killswitch_port=ks, authority_port=auth, evidence_port=ev)
    agent = {"id": "agt_malicious", "tenant_id": "tnt_001"}

    with pytest.raises(GovernedCallDeniedError):
        governed_call("tool", "db.direct_prod_write", {"sql": "DROP TABLE users;"}, agent=agent, ctx=ctx)
