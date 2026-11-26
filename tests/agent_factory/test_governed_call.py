"""Tests for GovernedCall Wrapper (Phase 4)."""

import pytest
from agent_factory.build.governed_call import (
    governed_call, GovernedCallContext,
    GovernedCallDeniedError, GovernedCallKilledError, GovernedCallLimitExceededError
)
from agent_factory.adapters.fakes import (
    FakeAuthorityPort, FakeEvidencePort, FakeKillSwitchPort
)


def test_governed_call_success():
    auth = FakeAuthorityPort()
    ev = FakeEvidencePort()
    ks = FakeKillSwitchPort()

    ctx = GovernedCallContext(
        killswitch_port=ks,
        authority_port=auth,
        evidence_port=ev,
        executor=lambda kind, target, args, tok: {"output": "hello world"}
    )
    agent = {"id": "agt_001", "tenant_id": "tnt_001", "principal_id": "agt.agt_001"}

    out = governed_call("tool", "web.fetch_page", {"url": "https://example.com"}, agent=agent, ctx=ctx)
    assert out == {"output": "hello world"}
    # Verified evidence appended
    assert len(ev.events) == 1
    assert ev.events[0].event_type == "agent.call.ok"


def test_governed_call_blocks_when_killed():
    auth = FakeAuthorityPort()
    ev = FakeEvidencePort()
    ks = FakeKillSwitchPort()
    ks.killed_scopes.add(("AGENT", "agt_killed"))

    ctx = GovernedCallContext(killswitch_port=ks, authority_port=auth, evidence_port=ev)
    agent = {"id": "agt_killed", "tenant_id": "tnt_001"}

    with pytest.raises(GovernedCallKilledError):
        governed_call("tool", "web.fetch_page", {}, agent=agent, ctx=ctx)


def test_governed_call_enforces_limits():
    auth = FakeAuthorityPort()
    ev = FakeEvidencePort()
    ks = FakeKillSwitchPort()

    limits = {"steps": 5, "max_steps": 5, "tool_calls": 0, "max_tool_calls": 10, "cost_usd": 0.0, "max_cost_usd": 1.0}
    ctx = GovernedCallContext(killswitch_port=ks, authority_port=auth, evidence_port=ev, limits_tracker=limits)
    agent = {"id": "agt_001", "tenant_id": "tnt_001"}

    with pytest.raises(GovernedCallLimitExceededError):
        governed_call("tool", "web.fetch_page", {}, agent=agent, ctx=ctx)


def test_governed_call_denied_by_authority():
    auth = FakeAuthorityPort(allow_all=False)
    ev = FakeEvidencePort()
    ks = FakeKillSwitchPort()

    ctx = GovernedCallContext(killswitch_port=ks, authority_port=auth, evidence_port=ev)
    agent = {"id": "agt_001", "tenant_id": "tnt_001"}

    with pytest.raises(GovernedCallDeniedError):
        governed_call("tool", "forbidden_tool", {}, agent=agent, ctx=ctx)

    # Denial recorded in evidence
    assert len(ev.events) == 1
    assert ev.events[0].event_type == "agent.call.denied"
