"""Unit & Integration Tests for Stage 5: Agent Factory Integration.

Verifies:
- Declarative zonata.agent/v1 spec compilation into governed execution graphs.
- 100% GovernedCall invariant across external nodes (model, tool, mcp, delegate).
- Separation of duties (Law L5): Requester != Builder != Tester != Approver.
- ProcessStep execution powered by compiled Agent Factory agents.
- Quarantined OSS Import lane: fails closed with AF-SANDBOX-UNAVAILABLE under T0 host.
"""

import pytest
from core.factory_integration import (
    FactoryIntegrationBridge,
    SeparationOfDutiesViolationError,
    SandboxUnavailableError,
)
from core.process_packs.schema import ProcessStep
from agent_factory.adapters.zonata import ZonataEvidenceAdapter


@pytest.fixture
def bridge():
    adapter = ZonataEvidenceAdapter()
    return FactoryIntegrationBridge(evidence_port=adapter)


def test_stage5_separation_of_duties_enforcement(bridge):
    """Verify Law L5: Requester != Builder != Tester != Approver."""
    # Test 1: Valid 4-party separation of duties
    bridge.check_separation_of_duties(
        requester_id="usr_requester",
        builder_id="usr_builder",
        tester_id="usr_tester",
        approver_id="usr_approver"
    )

    # Test 2: Approver tries to self-approve own requested or built agent
    with pytest.raises(SeparationOfDutiesViolationError) as exc_info:
        bridge.check_separation_of_duties(
            requester_id="usr_alice",
            builder_id="usr_bob",
            tester_id="usr_charlie",
            approver_id="usr_alice"  # Self-approval by requester!
        )
    assert "approver 'usr_alice' cannot also be requester" in str(exc_info.value)

    # Test 3: Builder tries to test own build
    with pytest.raises(SeparationOfDutiesViolationError) as exc_info:
        bridge.check_separation_of_duties(
            requester_id="usr_alice",
            builder_id="usr_bob",
            tester_id="usr_bob",  # Builder testing own work!
            approver_id="usr_charlie"
        )
    assert "builder 'usr_bob' cannot test their own work" in str(exc_info.value)


def test_stage5_spec_compilation_and_governed_invariants(bridge):
    """Verify compilation of zonata.agent/v1 spec with 100% GovernedCall wrapping."""
    spec = bridge.resolve_or_create_agent_spec(
        tenant_id="tnt_stage5",
        company_id="comp_stage5",
        role="CFO",
        capabilities=["pricing.calculate_tier", "billing.create_invoice"]
    )
    assert spec["apiVersion"] == "zonata.agent/v1"
    assert spec["kind"] == "Agent"

    compiled = bridge.compile_agent(spec)
    # Asserts that 100% of external nodes carry GovernedCall wrapper
    assert compiled.verify_no_unwrapped_external_nodes()
    assert compiled.agent_name == "cfo-agent"
    assert len(compiled.nodes) >= 3


def test_stage5_process_pack_step_execution_with_agent(bridge):
    """Verify ProcessStep execution powered by an Agent Factory compiled agent."""
    step = ProcessStep(
        id="quote_generation",
        name="Pricing and Proposal Formulation",
        actor="agent",
        role="CFO",
        tool_capabilities=["pricing.calculate_tier"],
        gate_checks=["BudgetGate", "CharterGate"],
        reversible=True
    )

    context = {
        "company_name": "MegaCorp International",
        "requested_tier": "enterprise_gold",
        "estimated_seats": 100
    }

    out = bridge.execute_agent_step(
        step=step,
        context=context,
        tenant_id="tnt_stage5",
        company_id="comp_stage5"
    )

    assert out["quote_generation_output"] == "processed"
    assert out["quote_generation_agent_executed"] is True
    assert "quote_generation_tokens_used" in out


def test_stage5_quarantined_oss_import_t0_fail_closed(bridge):
    """Verify open-source quarantined import fails closed with AF-SANDBOX-UNAVAILABLE on untrusted tiers."""
    # Test 1: Requesting T1/T2 sandbox on T0 sovereign host must fail-closed
    with pytest.raises(SandboxUnavailableError) as exc_info:
        bridge.import_quarantined_agent(
            source_url="https://github.com/external-community/untrusted-agent.git",
            manifest_data={"name": "community-market-scraper"},
            tier_requested="T1"
        )
    assert "AF-SANDBOX-UNAVAILABLE" in str(exc_info.value)

    # Test 2: Safe T0 declarative import produces zonata.agent/v1 specification
    t0_imported = bridge.import_quarantined_agent(
        source_url="https://github.com/trusted-spec/lead-evaluator.git",
        manifest_data={"name": "lead-evaluator", "version": "1.2.0"},
        tier_requested="T0"
    )
    assert t0_imported["apiVersion"] == "zonata.agent/v1"
    assert t0_imported["metadata"]["name"] == "lead-evaluator"
