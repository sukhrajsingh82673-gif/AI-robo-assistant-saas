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
4. Andon expression safety and canonical waste-tag validation.
"""

import os

import pytest
import yaml

from core.process_packs.loader import ProcessPackLoader
from core.process_packs.schema import WasteTag, compile_andon_expression
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
        "compliance_and_risk",
    ]
    valid_waste_tags = {tag.value for tag in WasteTag}

    for pack_id in all_packs:
        path = os.path.join("packs", pack_id, "v1", "pack.yaml")
        assert os.path.exists(path), f"Pack file missing: {path}"

        pack = pack_loader.load_file(path)
        assert pack.pack_id == pack_id
        assert pack.version == "1.0.0"
        assert len(pack.steps) >= 3
        assert len(pack.andon) >= 1
        assert len(pack.simulation_scenarios) >= 2
        for tag in pack.waste_tags:
            assert tag in valid_waste_tags, f"{pack_id} uses non-canonical waste tag {tag}"
        for andon in pack.andon:
            compile_andon_expression(andon.trigger_expression)


def test_simulation_and_andon_across_all_extended_packs(pack_loader, simulator):
    """Verifies simulation harness runs clean and Andon scenarios across newly added packs."""
    new_packs = [
        "record_to_report",
        "hire_to_retire",
        "plan_to_deliver",
        "compliance_and_risk",
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


def test_european_union_vat(compliance_engine):
    """Verifies EU VAT: reverse charge only for valid cross-border B2B, otherwise destination VAT."""
    pack = compliance_engine.get_pack("eu")
    assert pack is not None
    assert pack["currency"] == "EUR"

    # 1. Cross-border B2B with a valid customer VAT ID -> 0% reverse charge.
    res_b2b = compliance_engine.calculate_tax(
        "eu",
        10000.0,
        {
            "is_b2b": True,
            "vies_vat_id": "FR12345678901",
            "member_state": "FR",
            "supplier_member_state": "DE",
        },
    )
    assert res_b2b.currency == "EUR"
    assert res_b2b.tax_amount == 0.0
    assert res_b2b.total_amount == 10000.0
    assert "EU_VAT_REVERSE_CHARGE" in res_b2b.tax_breakdown

    # 2. Domestic B2B is still taxable, even with a VAT ID.
    res_domestic = compliance_engine.calculate_tax(
        "eu",
        1000.0,
        {
            "is_b2b": True,
            "vies_vat_id": "DE123456789",
            "member_state": "DE",
            "supplier_member_state": "DE",
        },
    )
    assert res_domestic.tax_amount == 190.0

    # 3. Malformed VAT ID must not qualify for reverse charge.
    res_bad_vat = compliance_engine.calculate_tax(
        "eu",
        1000.0,
        {
            "is_b2b": True,
            "vies_vat_id": "NOT-A-VAT",
            "member_state": "FR",
            "supplier_member_state": "DE",
        },
    )
    assert res_bad_vat.tax_amount == 200.0

    # 4. VAT ID from the wrong member state must not qualify.
    res_wrong_state = compliance_engine.calculate_tax(
        "eu",
        1000.0,
        {
            "is_b2b": True,
            "vies_vat_id": "DE123456789",
            "member_state": "FR",
            "supplier_member_state": "DE",
        },
    )
    assert res_wrong_state.tax_amount == 200.0

    # 5. A supplier outside the EU is not a cross-border EU reverse-charge supply.
    res_non_eu_supplier = compliance_engine.calculate_tax(
        "eu",
        1000.0,
        {
            "is_b2b": True,
            "vies_vat_id": "FR12345678901",
            "member_state": "FR",
            "supplier_member_state": "US",
        },
    )
    assert res_non_eu_supplier.tax_amount == 200.0

    # 6. B2C destination rates, including non-default states.
    res_de = compliance_engine.calculate_tax("eu", 1000.0, {"member_state": "DE"})
    assert (res_de.tax_amount, res_de.total_amount) == (190.0, 1190.0)
    res_es = compliance_engine.calculate_tax("eu", 1000.0, {"member_state": "ES"})
    assert (res_es.tax_amount, res_es.total_amount) == (210.0, 1210.0)
    res_hu = compliance_engine.calculate_tax("eu", 1000.0, {"member_state": "HU"})
    assert res_hu.tax_amount == 270.0

    # 7. Unknown or missing destination state fails closed.
    with pytest.raises(ValueError):
        compliance_engine.calculate_tax("eu", 100.0, {"member_state": "XX"})
    with pytest.raises(ValueError):
        compliance_engine.calculate_tax("eu", 100.0, {})


def test_gdpr_ropa(compliance_engine):
    """Verifies Article 30 ROPA fields and conditional Article 37 DPO handling."""
    valid_ropa = {
        "legal_basis": "public_task",
        "controller_identity": "Zonata GmbH, privacy@zonata.eu",
        "purposes": ["payroll", "statutory reporting"],
        "data_categories": ["employee_id", "email", "tax_number"],
        "retention_days": 365,
    }
    result = compliance_engine.validate_gdpr_ropa(valid_ropa)
    assert result["compliant"] is True
    assert result["errors"] == []

    legacy_alias = {
        "legal_basis": "contractual_necessity",
        "controller_identity": "Zonata GmbH, privacy@zonata.eu",
        "purposes": ["contract fulfilment"],
        "data_categories": ["customer_contact"],
        "retention_days": 30,
        "requires_dpo": True,
        "dpo_contact": "dpo@zonata.eu",
    }
    assert compliance_engine.validate_gdpr_ropa(legacy_alias)["compliant"] is True

    invalid_ropa = {
        "legal_basis": "unsupported_basis",
        "controller_identity": "",
        "purposes": [],
        "data_categories": [],
        "retention_days": "365",
        "requires_dpo": True,
        "third_country_transfers": True,
    }
    result = compliance_engine.validate_gdpr_ropa(invalid_ropa)
    assert result["compliant"] is False
    assert len(result["errors"]) == 7

    zero_retention = dict(valid_ropa, retention_days=0)
    result = compliance_engine.validate_gdpr_ropa(zero_retention)
    assert any("retention" in e.lower() for e in result["errors"])


def test_andon_expression_is_sandboxed():
    """Andon expressions may not call functions, touch attributes, or import modules."""
    for malicious in (
        "__import__('os').system('id')",
        "open('secret').read()",
        "value.__class__.__mro__",
        "items[0]",
    ):
        with pytest.raises(ValueError):
            compile_andon_expression(malicious)

    code = compile_andon_expression("severity == 'P0' and score > 5")
    assert eval(code, {"__builtins__": {}}, {"severity": "P0", "score": 9}) is True


def test_loader_rejects_non_canonical_waste_tag_and_unsafe_andon(pack_loader):
    with open(os.path.join("packs", "lead_to_cash", "v1", "pack.yaml"), encoding="utf-8") as f:
        base = yaml.safe_load(f)

    legacy_waste = dict(base, waste_tags=["over-processing"])
    normalized = pack_loader.parse_dict(legacy_waste)
    assert normalized.waste_tags == ["over_processing"]

    unknown_waste = dict(base, waste_tags=["bogus_waste"])
    with pytest.raises(ValueError):
        pack_loader.parse_dict(unknown_waste)

    unsafe = yaml.safe_load(yaml.safe_dump(base))
    unsafe["andon"][0]["trigger_expression"] = "__import__('os').system('id')"
    with pytest.raises(ValueError):
        pack_loader.parse_dict(unsafe)
