"""ZONATA Sovereign Core — Extended Coverage & Global Readiness Test Suite.

Verifies:
1. All 7 Core Enterprise Process Packs from Section 5 Coverage Map:
   - Lead-to-Cash
   - Procure-to-Pay
   - Support-to-Resolution
   - Record-to-Report
   - Hire-to-Retire
   - Plan-to-Deliver
   - Compliance & Risk
2. End-to-End Simulation Execution & Andon Stop-the-Line Halts across all 7 packs.
3. European Union Regional Compliance (EUR, B2B Reverse Charge, Member State VAT, GDPR Article 30 ROPA).
"""

import pytest
import os
from core.process_packs.loader import ProcessPackLoader
from core.process_packs.engine import ProcessExecutionEngine
from core.process_packs.simulator import ProcessPackSimulator
from core.region_packs.engine import RegionalComplianceEngine


@pytest.fixture
def pack_loader():
    return ProcessPackLoader()


@pytest.fixture
def simulator():
    return ProcessPackSimulator()


@pytest.fixture
def compliance_engine():
    return RegionalComplianceEngine()


def test_all_seven_enterprise_process_packs_load_and_validate(pack_loader):
    """Verifies that all 7 enterprise process packs load and pass schema validation."""
    all_packs = [
        "lead_to_cash",
        "procure_to_pay",
        "support_to_resolution",
        "record_to_report",
        "hire_to_retire",
        "plan_to_deliver",
        "compliance_and_risk"
    ]

    for pack_id in all_packs:
        path = os.path.join("packs", pack_id, "v1", "pack.yaml")
        assert os.path.exists(path), f"Pack file missing: {path}"

        pack = pack_loader.load_file(path)
        assert pack.pack_id == pack_id
        assert pack.version == "1.0.0"
        assert len(pack.steps) >= 3
        assert len(pack.andon) >= 1
        assert len(pack.simulation_scenarios) >= 2


def test_simulation_and_andon_across_all_extended_packs(pack_loader, simulator):
    """Verifies simulation harness runs clean and Andon scenarios across newly added packs."""
    new_packs = [
        "record_to_report",
        "hire_to_retire",
        "plan_to_deliver",
        "compliance_and_risk"
    ]

    for pack_id in new_packs:
        path = os.path.join("packs", pack_id, "v1", "pack.yaml")
        pack = pack_loader.load_file(path)

        sc_clean = pack.simulation_scenarios[0]
        res_clean = simulator.run_scenario(pack, sc_clean)
        assert res_clean.passed, f"Clean scenario failed for {pack_id}: {res_clean.errors}"
        assert res_clean.status == "COMPLETED"
        assert res_clean.first_pass_yield == 1.0

        sc_andon = pack.simulation_scenarios[1]
        res_andon = simulator.run_scenario(pack, sc_andon)
        assert res_andon.passed, f"Andon scenario failed for {pack_id}: {res_andon.errors}"
        assert res_andon.status == "HALTED_ANDON"


def test_european_union_vat_and_gdpr(compliance_engine):
    """Verifies EU regional pack taxation (reverse charge & member VAT) and GDPR ROPA mandates."""
    pack = compliance_engine.get_pack("eu")
    assert pack is not None
    assert pack["currency"] == "EUR"

    # 1. B2B Cross-Border Reverse Charge (0% VAT with valid VIES VAT ID)
    res_b2b = compliance_engine.calculate_tax(
        "eu",
        10000.0,
        {"is_b2b": True, "vies_vat_id": "DE123456789"}
    )
    assert res_b2b.currency == "EUR"
    assert res_b2b.tax_amount == 0.0
    assert res_b2b.total_amount == 10000.0
    assert "EU_VAT_REVERSE_CHARGE" in res_b2b.tax_breakdown

    # 2. B2C Germany Domestic VAT (19%)
    res_de = compliance_engine.calculate_tax(
        "eu",
        1000.0,
        {"is_b2b": False, "member_state": "DE"}
    )
    assert res_de.tax_amount == 190.0
    assert res_de.total_amount == 1190.0

    # 3. B2C Spain Domestic VAT (21%)
    res_es = compliance_engine.calculate_tax(
        "eu",
        1000.0,
        {"is_b2b": False, "member_state": "ES"}
    )
    assert res_es.tax_amount == 210.0
    assert res_es.total_amount == 1210.0

    # 4. GDPR Article 30 ROPA Compliance Check
    valid_ropa = {
        "legal_basis": "contractual_necessity",
        "data_categories": ["employee_id", "email", "tax_number"],
        "retention_days": 365,
        "dpo_contact": "dpo@enterprise-org.eu"
    }
    eval_valid = compliance_engine.validate_gdpr_ropa(valid_ropa)
    assert eval_valid["compliant"] is True
    assert len(eval_valid["errors"]) == 0

    invalid_ropa = {
        "legal_basis": "unsupported_basis",
        "data_categories": [],
        "retention_days": -1,
        "dpo_contact": None
    }
    eval_invalid = compliance_engine.validate_gdpr_ropa(invalid_ropa)
    assert eval_invalid["compliant"] is False
    assert len(eval_invalid["errors"]) == 4
