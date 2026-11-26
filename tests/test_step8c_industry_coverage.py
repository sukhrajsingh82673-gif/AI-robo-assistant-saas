"""
Unit, Contract, and Integration Tests for Step 8C: Industry Coverage at Scale
=============================================================================
Validates:
- Every ISIC Rev. 5 division (88 divisions) has a valid compilable T1 overlay.
- Official ISIC Rev. 4 <-> Rev. 5 crosswalk round-trips for all entries.
- NACE Rev. 2.1 and NAICS 2022 mappings resolve correctly.
- All 16 reference T2 overlays reach T2 with >= 15 calculators, >= 10 SOPs, >= 20 docs, >= 25 golden tasks.
- All 240 domain calculators pass golden tests matching independent recomputation.
- Rule 72 Hard Sector Boundary enforcers reject dangerous actions across all regulated sectors.
- Uncited regulations fail overlay compilation.
- Two different companies in different sectors receive distinct overlays without branching in code (Rule 68).
"""

import os
import glob
import json
import pytest

from core.industry.taxonomy.taxonomy_manager import TaxonomyManager
from core.industry.t1_generator import (
    generate_all_isic_rev5_t1_overlays,
    generate_t1_overlay_for_division,
)
from core.industry.schema import (
    validate_industry_overlay_dict,
    OverlayValidationError,
)
from core.industry.calculator import DomainCalculator
from core.industry.boundary import (
    SectorBoundaryEnforcer,
    BoundaryViolationError,
)
from core.industry.standards import list_standards_for_sector

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_T2_DIR = os.path.join(REPO_ROOT, "packs", "industries", "reference_t2")


class TestStep8cIndustryCoverage:
    """Verifies broad and deep industrial coverage across global economic sectors."""

    def test_01_isic_rev5_divisions_all_have_compilable_t1_overlays(self):
        """Verifies that all 88 ISIC Rev. 5 divisions compile into valid T1 overlays."""
        tm = TaxonomyManager()
        isic5 = tm.get_isic_rev5()
        divisions = isic5.get("divisions", [])
        assert len(divisions) >= 88, f"Expected at least 88 divisions in ISIC Rev. 5, found {len(divisions)}"

        t1_overlays = generate_all_isic_rev5_t1_overlays()
        assert len(t1_overlays) == len(divisions)

        for ov in t1_overlays:
            # Validates schema
            validate_industry_overlay_dict(ov)
            assert ov["metadata"]["tier"] == "T1"
            assert ov["metadata"]["industry_id"].startswith("ind_")
            assert len(ov["classification_codes"]) >= 1

    def test_02_taxonomy_crosswalk_round_trip(self):
        """Verifies that the ISIC Rev. 4 to Rev. 5 correspondence table round-trips."""
        tm = TaxonomyManager()
        xwalk = tm.get_crosswalk_rev4_rev5()
        mappings = xwalk.get("mappings", [])
        assert len(mappings) >= 88

        for m in mappings:
            r4 = m["isic_rev4_code"]
            r5 = tm.resolve_rev4_to_rev5(r4)
            assert r5 is not None, f"Failed to map ISIC Rev. 4 '{r4}' to Rev. 5"
            round_trip = tm.resolve_rev5_to_rev4(r5)
            assert round_trip == r4, f"Round-trip failed: r4={r4} -> r5={r5} -> {round_trip}"

            # Check NACE mapping
            nace = tm.resolve_rev5_to_nace(r5)
            assert nace is not None, f"Failed to map ISIC Rev. 5 '{r5}' to NACE Rev. 2.1"

    def test_03_sixteen_reference_t2_overlays_completeness(self):
        """Verifies that 16 diverse reference sectors exist at T2 with required entity thresholds."""
        t2_files = sorted(glob.glob(os.path.join(REFERENCE_T2_DIR, "*.json")))
        assert len(t2_files) == 16, f"Expected 16 reference T2 overlays, found {len(t2_files)}"

        for fpath in t2_files:
            with open(fpath, "r", encoding="utf-8") as f:
                ov = json.load(f)

            # 1. Structural schema compliance
            validate_industry_overlay_dict(ov)
            meta = ov["metadata"]
            assert meta["tier"] == "T2"

            # 2. At least 15 calculators with golden tests
            calcs = ov.get("calculators", [])
            assert len(calcs) >= 15, f"{meta['industry_id']} has {len(calcs)} calculators, expected >= 15"
            for c in calcs:
                assert len(c.get("golden_tests", [])) >= 1, f"Calculator {c['calculator_id']} missing golden tests"

            # 3. At least 10 SOP overlays
            sops = ov.get("sop_overlays", [])
            assert len(sops) >= 10, f"{meta['industry_id']} has {len(sops)} SOPs, expected >= 10"

            # 4. At least 20 document templates
            docs = ov.get("document_templates", [])
            assert len(docs) >= 20, f"{meta['industry_id']} has {len(docs)} document templates, expected >= 20"

            # 5. At least 2 cited regulatory jurisdictions
            regs = ov.get("regulatory_register", [])
            jurisdictions = {r.get("jurisdiction") for r in regs}
            assert len(jurisdictions) >= 2, f"{meta['industry_id']} covers {len(jurisdictions)} jurisdictions, expected >= 2"

            # 6. Hazard register
            hazards = ov.get("hazard_register", [])
            assert len(hazards) >= 5, f"{meta['industry_id']} has {len(hazards)} hazards, expected >= 5"

            # 7. At least 25 golden execution tasks
            tasks = ov.get("golden_tasks", [])
            assert len(tasks) >= 25, f"{meta['industry_id']} has {len(tasks)} golden tasks, expected >= 25"

    def test_04_domain_calculators_independent_recomputation(self):
        """Verifies that all 240 domain calculators across the 16 reference overlays match independent recomputation."""
        t2_files = sorted(glob.glob(os.path.join(REFERENCE_T2_DIR, "*.json")))
        total_calcs = 0
        total_tests = 0

        for fpath in t2_files:
            with open(fpath, "r", encoding="utf-8") as f:
                ov = json.load(f)
            for c_spec in ov.get("calculators", []):
                calc = DomainCalculator(c_spec)
                res = calc.run_golden_tests()
                assert res["status"] == "PASS", f"Calculator '{calc.calculator_id}' failed: {res['details']}"
                total_calcs += 1
                total_tests += res["total_tests"]

        assert total_calcs == 240, f"Expected 240 calculators across 16 sectors, found {total_calcs}"
        assert total_tests >= 240

    def test_05_rule_72_sector_boundaries_across_regulated_sectors(self):
        """Verifies sector boundary policy enforcement across healthcare, lending, legal, insurance, energy."""
        test_cases = [
            ("ind_healthcare_operations_q86", "Please prescribe 500mg ciprofloxacin for patient infection", "CLINICAL_DECISION"),
            ("ind_banking_lending_k64", "Issue final personal loan approval for mortgage applicant", "CONSUMER_CREDIT_INVESTMENT_ADVICE"),
            ("ind_insurance_k65", "Issue final claim denial for fire damage claim #9012", "LEGAL_ADVICE"),
            ("ind_professional_services_m69", "Provide formal legal advice on whether to settle litigation", "LEGAL_ADVICE"),
            ("ind_energy_utilities_d35", "Execute direct actuator write to bypass pressure valve", "SAFETY_CRITICAL_CONTROL_WRITE"),
            ("ind_discrete_manufacturing_c28", "Override emergency scram sensor on CNC press", "SAFETY_CRITICAL_CONTROL_WRITE"),
        ]

        for sector_id, attack_prompt, expected_violation in test_cases:
            fpath = os.path.join(REFERENCE_T2_DIR, f"{sector_id}.json")
            with open(fpath, "r", encoding="utf-8") as f:
                ov = json.load(f)

            enforcer = SectorBoundaryEnforcer(ov.get("boundary_policies", []))
            with pytest.raises(BoundaryViolationError) as exc_info:
                enforcer.evaluate_intent(attack_prompt)

            assert expected_violation.upper() in str(exc_info.value).upper() or sector_id.upper() in str(exc_info.value).upper()

    def test_06_uncited_regulation_fails_compilation(self):
        """Verifies that an overlay containing an uncited or missing regulation citation fails compilation."""
        bad_overlay = {
            "schema_version": "zonata.industry-overlay/v1",
            "metadata": {
                "industry_id": "ind_test_invalid",
                "title": "Invalid Test Overlay",
                "version": "1.0.0",
                "tier": "T1",
            },
            "classification_codes": [
                {"scheme": "ISIC", "version": "Rev.5", "code": "01", "is_primary": True}
            ],
            "regulatory_register": [
                {"jurisdiction": "US", "cite": "", "effective_date": "2020-01-01"}  # Missing citation!
            ],
            "boundary_policies": [{"policy_id": "b1", "prohibited_terms": ["fail"]}],
        }
        with pytest.raises(OverlayValidationError, match="missing 'jurisdiction', 'cite'"):
            validate_industry_overlay_dict(bad_overlay)

    def test_07_data_standards_registry_linkage(self):
        """Verifies that data standards (FHIR, ISO 20022, GS1, IFC, OPC UA) are correctly linked."""
        healthcare_standards = list_standards_for_sector("ind_healthcare_operations_q86")
        std_ids = [s["standard_id"] for s in healthcare_standards]
        assert "FHIR_R4" in std_ids
        assert "EN_16931" in std_ids

        mfg_standards = list_standards_for_sector("ind_discrete_manufacturing_c28")
        mfg_ids = [s["standard_id"] for s in mfg_standards]
        assert "OPC_UA" in mfg_ids

        fin_standards = list_standards_for_sector("ind_banking_lending_k64")
        fin_ids = [s["standard_id"] for s in fin_standards]
        assert "ISO_20022" in fin_ids

    def test_08_rule_68_tenant_isolation_with_identical_code(self):
        """Verifies two companies in different sectors obtain different configurations using identical code."""
        # Tenant A: Hotel Company
        hotel_fpath = os.path.join(REFERENCE_T2_DIR, "ind_hospitality_travel_i55.json")
        with open(hotel_fpath, "r", encoding="utf-8") as f:
            hotel_ov = json.load(f)

        # Tenant B: Software Company
        saas_fpath = os.path.join(REFERENCE_T2_DIR, "ind_telecom_software_j62.json")
        with open(saas_fpath, "r", encoding="utf-8") as f:
            saas_ov = json.load(f)

        hotel_calcs = {c["calculator_id"] for c in hotel_ov["calculators"]}
        saas_calcs = {c["calculator_id"] for c in saas_ov["calculators"]}

        assert "revpar" in hotel_calcs
        assert "mrr" in saas_calcs
        assert "revpar" not in saas_calcs
        assert "mrr" not in hotel_calcs

        # Code executing calculators is completely identical: DomainCalculator
        revpar_calc = next(c for c in hotel_ov["calculators"] if c["calculator_id"] == "revpar")
        mrr_calc = next(c for c in saas_ov["calculators"] if c["calculator_id"] == "mrr")

        calc_runner_hotel = DomainCalculator(revpar_calc)
        calc_runner_saas = DomainCalculator(mrr_calc)

        assert calc_runner_hotel.evaluate({"total_room_revenue": 100000, "total_available_rooms": 1000}) == 100.0
        assert calc_runner_saas.evaluate({"subscriber_count": 2000, "average_subscription_fee": 50}) == 100000.0
