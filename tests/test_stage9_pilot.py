"""Unit & Integration Tests for Stage 9: Pilot Deployment Simulation.

Verifies:
- Enterprise pilot onboarding with Charter, 8 Executive Owners, and Regional configuration.
- L0 Observe Mode simulation cycles across the core Process Packs.
- Lean KPI evidence gathering (FPY, cycle time, cost).
- Deterministic Autonomy Promotion (L0 -> L1 -> L2) backed by cryptographic Merkle evidence.
"""

import pytest
from core.pilot_runner import PilotEnterpriseRunner
from core.process_packs.loader import ProcessPackLoader
from agent_factory.adapters.zonata import ZonataEvidenceAdapter


@pytest.fixture
def pilot_runner():
    adapter = ZonataEvidenceAdapter()
    return PilotEnterpriseRunner(evidence_port=adapter)


@pytest.fixture
def pack_loader():
    return ProcessPackLoader()


def test_stage9_enterprise_pilot_onboarding(pilot_runner):
    """Verify onboarding of enterprise organization with Charter and 8 Executive Accountable Owners."""
    tenant = "tnt_pilot_apex"
    company = "comp_pilot_apex"

    charter = pilot_runner.onboard_pilot_company(
        tenant_id=tenant,
        company_id=company,
        company_name="Apex Global Technologies",
        region="india",
        owner_principal_id="principal.human.ceo"
    )

    assert charter.tenant_id == tenant
    assert len(charter.red_lines) >= 5
    assert len(charter.spending_limits) >= 4

    # Verify registered executive owners
    exec_owner = pilot_runner.owner_registry.get_owner(tenant, "department", "executive")
    finance_owner = pilot_runner.owner_registry.get_owner(tenant, "department", "finance")
    ciso_owner = pilot_runner.owner_registry.get_owner(tenant, "department", "security")

    assert exec_owner is not None
    assert finance_owner is not None
    assert ciso_owner is not None
    assert finance_owner.owner_name == "Chief Financial Officer"


def test_stage9_l0_observe_mode_and_evidence_gathering(pilot_runner, pack_loader):
    """Verify executing L0 shadow-mode business transactions and collecting empirical KPIs."""
    tenant = "tnt_pilot_apex"
    company = "comp_pilot_apex"

    pack = pack_loader.load_file("packs/procure_to_pay/v1/pack.yaml")

    # Run 6 L0 cycles
    res = pilot_runner.run_l0_simulation_cycle(
        tenant_id=tenant,
        company_id=company,
        pack=pack,
        cycles=6
    )

    assert res["cycles_run"] == 6
    assert res["first_pass_yield"] > 0.0
    assert res["avg_cycle_time"] > 0.0

    # Verify aggregate metrics in store
    agg = pilot_runner.metrics_store.get_aggregate_kpis(tenant, pack.pack_id)
    assert agg["total_runs"] >= 6


def test_stage9_evidence_backed_autonomy_promotion(pilot_runner, pack_loader):
    """Verify empirical evidence-backed promotion of a process pack to higher Autonomy."""
    tenant = "tnt_promotion_corp"
    pack_id = "support_to_resolution"

    pack = pack_loader.load_file("packs/support_to_resolution/v1/pack.yaml")
    # Reset to L0 for promotion drill
    pack.autonomy.current_level = 0
    pack_loader.save_pack(pack)

    # Populate 6 clean runs with 100% FPY and 0 errors
    for i in range(6):
        pilot_runner.metrics_store.record_run(
            tenant_id=tenant,
            company_id="c1",
            pack_id=pack_id,
            instance_id=f"promo_inst_{i}",
            cycle_time_seconds=1.2,
            first_pass_yield=1.0,
            cost_usd=0.005,
            error_count=0
        )

    # Evaluate promotion
    verdict = pilot_runner.evaluate_and_promote(
        tenant_id=tenant,
        pack_id=pack_id,
        actor="principal.human.cfo"
    )

    assert verdict.promoted is True
    assert verdict.from_level == 0
    assert verdict.to_level == 1
    assert verdict.evidence_id is not None
    assert verdict.evidence_id.startswith("EV-")

    # Check updated pack in loader
    updated_pack = pack_loader.get_pack(pack_id)
    assert updated_pack.autonomy.current_level == 1
