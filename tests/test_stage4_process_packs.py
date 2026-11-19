"""Unit & Integration Tests for Stage 4: Process Pack Framework.

Verifies:
- Declarative parsing & schema validation of the three core Process Packs:
  1. Lead-to-Cash (packs/lead_to_cash/v1/pack.yaml)
  2. Procure-to-Pay (packs/procure_to_pay/v1/pack.yaml)
  3. Support-to-Resolution (packs/support_to_resolution/v1/pack.yaml)
- SIPOC alignment and input/output contracts.
- ProcessExecutionEngine execution, state progression, and Merkle evidence sealing.
- Deterministic Andon cord triggers (stop-the-line behavior, incident tracking).
- Simulation harness execution and Lean KPI collection (FPY, cycle time, cost).
"""

import os
import pytest
from core.process_packs.loader import ProcessPackLoader
from core.process_packs.engine import ProcessExecutionEngine
from core.process_packs.simulator import ProcessPackSimulator
from agent_factory.adapters.zonata import ZonataEvidenceAdapter


@pytest.fixture
def pack_loader():
    return ProcessPackLoader()


@pytest.fixture
def process_engine():
    adapter = ZonataEvidenceAdapter()
    return ProcessExecutionEngine(evidence_port=adapter)


@pytest.fixture
def simulator(process_engine):
    return ProcessPackSimulator(engine=process_engine)


def test_stage4_load_and_validate_all_three_packs(pack_loader):
    """Verify loading and schema validation of the 3 primary Process Packs."""
    packs_to_test = [
        ("packs/lead_to_cash/v1/pack.yaml", "lead_to_cash", "CMO/CFO"),
        ("packs/procure_to_pay/v1/pack.yaml", "procure_to_pay", "CFO/COO"),
        ("packs/support_to_resolution/v1/pack.yaml", "support_to_resolution", "COO/CTO"),
    ]

    for rel_path, expected_id, expected_owner in packs_to_test:
        assert os.path.exists(rel_path), f"Pack file not found: {rel_path}"
        pack = pack_loader.load_file(rel_path)
        assert pack.pack_id == expected_id
        assert pack.owner_role == expected_owner
        assert len(pack.steps) >= 5
        assert pack.sipoc is not None
        assert len(pack.sipoc.process_steps) == len(pack.steps)
        assert len(pack.andon) >= 2
        assert len(pack.simulation_scenarios) >= 2

        # Verify DB persistence
        retrieved = pack_loader.get_pack(expected_id)
        assert retrieved is not None
        assert retrieved.name == pack.name


def test_stage4_engine_end_to_end_execution(pack_loader, process_engine):
    """Verify ProcessExecutionEngine runs steps sequentially, records outputs, and seals evidence."""
    pack = pack_loader.load_file("packs/lead_to_cash/v1/pack.yaml")

    initial_inputs = {
        "lead_contact": "sarah.connor@cyberdyne.com",
        "company_name": "Cyberdyne Systems Inc",
        "estimated_seats": 25,
        "requested_tier": "enterprise_gold",
        "discount_percent": 12.0,
        "is_sanctioned": False
    }

    instance = process_engine.create_instance(
        tenant_id="tnt_stage4",
        company_id="comp_stage4",
        pack=pack,
        initial_inputs=initial_inputs
    )
    assert instance.status == "RUNNING"
    assert instance.current_step_index == 0

    # Step-by-step handler
    def custom_handler(step, ctx):
        return {
            f"{step.id}_output": "processed",
            f"{step.id}_timestamp": 12345678.0
        }

    # Execute all 7 steps
    for _ in range(len(pack.steps)):
        instance = process_engine.execute_next_step(instance, pack, step_handler=custom_handler)

    assert instance.status == "COMPLETED"
    assert instance.current_step_index == len(pack.steps)
    assert len(instance.records) == len(pack.steps)
    assert instance.total_cost_usd > 0

    # Verify all steps have cryptographic evidence IDs
    for rec in instance.records:
        assert rec.status == "SUCCEEDED"
        assert rec.evidence_id is not None
        assert rec.evidence_id.startswith("EV-")


def test_stage4_andon_stop_the_line_trigger(pack_loader, process_engine):
    """Verify Andon rule halts process execution immediately when boundary condition trips."""
    pack = pack_loader.load_file("packs/lead_to_cash/v1/pack.yaml")

    # Discount exceeds 25% policy -> should trip ANDON-L2C-01
    initial_inputs = {
        "lead_contact": "bad_actor@exploit.com",
        "company_name": "Rogue LLC",
        "estimated_seats": 5,
        "requested_tier": "starter",
        "discount_percent": 30.0,  # TRIPS ANDON
        "is_sanctioned": False
    }

    instance = process_engine.create_instance(
        tenant_id="tnt_stage4",
        company_id="comp_stage4",
        pack=pack,
        initial_inputs=initial_inputs
    )

    # Attempt to execute first step
    instance = process_engine.execute_next_step(instance, pack)

    # Verify line was halted
    assert instance.status == "HALTED_ANDON"
    assert instance.andon_incident is not None
    assert instance.andon_incident["rule_id"] == "ANDON-L2C-01"
    assert instance.andon_incident["escalate_to"] == "CFO"

    # Attempting to execute another step should raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        process_engine.execute_next_step(instance, pack)
    assert "HALTED_ANDON" in str(exc_info.value)


def test_stage4_simulation_harness_scenarios(pack_loader, simulator):
    """Verify ProcessPackSimulator executes both happy-path and Andon scenarios and gathers Lean KPIs."""
    p2p_pack = pack_loader.load_file("packs/procure_to_pay/v1/pack.yaml")

    # Scenario 1: Standard IT purchase (Happy path)
    sc1 = p2p_pack.simulation_scenarios[0]
    res1 = simulator.run_scenario(p2p_pack, sc1)
    assert res1.passed
    assert res1.status == "COMPLETED"
    assert res1.first_pass_yield == 1.0
    assert res1.cycle_time_seconds > 0
    assert len(res1.errors) == 0

    # Scenario 2: Price variance > 2% (Andon stop)
    sc2 = p2p_pack.simulation_scenarios[1]
    res2 = simulator.run_scenario(p2p_pack, sc2)
    assert res2.passed
    assert res2.status == "HALTED_ANDON"

    # Scenario 3: Support-to-resolution P0 security breach escalation
    s2r_pack = pack_loader.load_file("packs/support_to_resolution/v1/pack.yaml")
    sc_sec = s2r_pack.simulation_scenarios[1]
    res_sec = simulator.run_scenario(s2r_pack, sc_sec)
    assert res_sec.passed
    assert res_sec.status == "HALTED_ANDON"
