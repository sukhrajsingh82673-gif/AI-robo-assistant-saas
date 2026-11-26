"""Tests for Agent-to-Agent (A2A) Gateway: Narrowing Delegation and Loop Protection."""

import pytest
from agent_factory.capabilities.a2a_gateway import (
    A2AGateway, compute_narrowed_permissions,
    A2ALoopDetectedError, A2ADepthExceededError
)


def test_a2a_narrowing_delegation_intersection():
    """Effective permissions = min(delegator, delegatee)."""
    p_delegator = {
        "granted_tools": [
            {"name": "web.fetch_page", "scopes": ["read", "write"], "max_calls": 50},
            {"name": "db.query_readonly", "scopes": ["read"], "max_calls": 20}
        ],
        "network": {"external": True, "allowed_hosts": ["a.com", "b.com"]},
        "writes": True,
        "data_classification_max": "confidential"
    }

    p_delegatee = {
        "granted_tools": [
            {"name": "web.fetch_page", "scopes": ["read"], "max_calls": 10},
            {"name": "chart.render", "scopes": ["write"], "max_calls": 5}
        ],
        "network": {"external": False, "allowed_hosts": ["a.com"]},
        "writes": False,
        "data_classification_max": "internal"
    }

    narrowed = compute_narrowed_permissions(p_delegator, p_delegatee)

    # 1. Tools: only web.fetch_page is common; scopes = [read]; max_calls = min(50, 10) = 10
    assert len(narrowed["granted_tools"]) == 1
    t = narrowed["granted_tools"][0]
    assert t["name"] == "web.fetch_page"
    assert t["scopes"] == ["read"]
    assert t["max_calls"] == 10

    # 2. Network: external False (delegatee has False); allowed_hosts = ["a.com"]
    assert narrowed["network"]["external"] is False
    assert narrowed["network"]["allowed_hosts"] == ["a.com"]

    # 3. Writes: False (delegatee has False)
    assert narrowed["writes"] is False

    # 4. Classification: narrowed to internal
    assert narrowed["data_classification_max"] == "internal"


def test_a2a_loop_detection():
    gw = A2AGateway()
    delegation_chain = ["agent_alpha", "agent_beta"]

    # Attempting to delegate back to agent_alpha in the chain raises A2ALoopDetectedError
    with pytest.raises(A2ALoopDetectedError):
        gw.validate_and_delegate(
            delegator_id="agent_beta",
            delegatee_id="agent_alpha",
            delegation_chain=delegation_chain,
            delegator_profile={},
            delegatee_profile={},
            payload={}
        )


def test_a2a_depth_limit():
    gw = A2AGateway(max_depth=3)
    chain = ["a1", "a2", "a3"]

    with pytest.raises(A2ADepthExceededError):
        gw.validate_and_delegate(
            delegator_id="a3",
            delegatee_id="a4",
            delegation_chain=chain,
            delegator_profile={},
            delegatee_profile={},
            payload={}
        )
