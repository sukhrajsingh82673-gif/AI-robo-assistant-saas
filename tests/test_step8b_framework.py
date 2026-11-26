"""
Unit and Integration Tests for Step 8B: Industry Depth Factory Framework
========================================================================
Validates:
- zonata.industry-overlay/v1 schema parsing and validation.
- zonata.jurisdiction-pack/v1 schema parsing and validation.
- Maturity tiers T0-T4 and automatic voiding on post-review modification.
- Rule 71 Invariant: Expert review protocol strictly rejects AI principals.
- Safe domain calculators with AST arithmetic and golden tests.
- Rule 72 Hard Sector Boundary enforcement (clinical, legal, credit, plant control).
- Factory Pipeline: compilation, validation, review task emission.
"""

import pytest
from core.industry.schema import (
    validate_industry_overlay_dict,
    OverlayValidationError,
    compute_overlay_digest,
)
from core.jurisdiction.schema import (
    validate_jurisdiction_pack_dict,
    JurisdictionValidationError,
)
from core.industry.tiers import OverlayTier, TierManager
from core.industry.expert_review import (
    ExpertReviewProtocol,
    AIReviewerProhibitedError,
)
from core.industry.calculator import DomainCalculator, UnsafeFormulaError
from core.industry.boundary import (
    SectorBoundaryEnforcer,
    BoundaryViolationError,
)
from core.industry.pipeline import IndustryDepthFactory


@pytest.fixture
def sample_valid_overlay():
    return {
        "schema_version": "zonata.industry-overlay/v1",
        "metadata": {
            "industry_id": "ind_hospitality_i55",
            "title": "Short-Stay Accommodation & Hospitality",
            "version": "1.0.0",
            "tier": "T2",
        },
        "classification_codes": [
            {"scheme": "ISIC", "version": "Rev.5", "code": "I55", "is_primary": True},
            {"scheme": "NACE", "version": "Rev.2.1", "code": "I.55"},
            {"scheme": "NAICS", "version": "2022", "code": "7211"},
        ],
        "calculators": [
            {
                "calculator_id": "revpar",
                "name": "Revenue Per Available Room",
                "formula": "total_room_revenue / total_available_rooms",
                "data_source": "hotel_night_audit_folio",
                "golden_tests": [
                    {"inputs": {"total_room_revenue": 100000, "total_available_rooms": 1000}, "expected_output": 100.0},
                    {"inputs": {"total_room_revenue": 45000, "total_available_rooms": 500}, "expected_output": 90.0},
                ],
            }
        ],
        "regulatory_register": [
            {
                "jurisdiction": "DE",
                "cite": "Gaststättengesetz (GastG) § 4",
                "effective_date": "2020-01-01",
                "status": "UNVERIFIED",
            }
        ],
        "boundary_policies": [
            {
                "policy_id": "refuse_clinical_medical_advice",
                "prohibited_terms": ["prescribe medication", "medical diagnosis"],
                "rejection_message": "Hospitality agents cannot provide medical or pharmaceutical advice.",
            }
        ],
    }


@pytest.fixture
def sample_valid_jurisdiction():
    return {
        "schema_version": "zonata.jurisdiction-pack/v1",
        "metadata": {
            "jurisdiction_code": "DE",
            "country_name": "Germany",
            "version": "1.0.0",
            "regime_type": "CIVIL_LAW",
            "currency": "EUR",
        },
        "tax_regime": {
            "system_name": "Umsatzsteuer (USt)",
            "standard_rate": 19.0,
            "reduced_rate": 7.0,
            "e_invoicing_model": "POST_AUDIT_ZUGFERD",
        },
        "data_protection": {
            "statutory_act": "GDPR / BDSG",
            "cross_border_transfer_restricted": True,
            "standard_retention_days": 3650,
        },
        "calendars": {
            "fiscal_year_start": "01-01",
            "official_holidays": ["2026-01-01", "2026-12-25", "2026-12-26"],
        },
    }


class TestStep8bFramework:
    """Verifies all components of the Industry Depth Factory framework."""

    def test_01_overlay_schema_valid_and_invalid(self, sample_valid_overlay):
        """Verifies industry overlay schema validation."""
        val = validate_industry_overlay_dict(sample_valid_overlay)
        assert val["metadata"]["industry_id"] == "ind_hospitality_i55"

        # Invalid schema version
        bad_ver = dict(sample_valid_overlay, schema_version="zonata.unknown/v9")
        with pytest.raises(OverlayValidationError, match="Unsupported schema_version"):
            validate_industry_overlay_dict(bad_ver)

        # Missing primary classification
        bad_class = dict(sample_valid_overlay, classification_codes=[{"scheme": "ISIC", "version": "Rev.5", "code": "I55"}])
        with pytest.raises(OverlayValidationError, match="at least one primary"):
            validate_industry_overlay_dict(bad_class)

    def test_02_jurisdiction_pack_schema(self, sample_valid_jurisdiction):
        """Verifies jurisdiction pack schema validation."""
        val = validate_jurisdiction_pack_dict(sample_valid_jurisdiction)
        assert val["metadata"]["jurisdiction_code"] == "DE"

        # Invalid regime type
        bad_regime = dict(sample_valid_jurisdiction)
        bad_regime["metadata"] = dict(sample_valid_jurisdiction["metadata"], regime_type="NON_EXISTENT")
        with pytest.raises(JurisdictionValidationError, match="Invalid regime_type"):
            validate_jurisdiction_pack_dict(bad_regime)

    def test_03_tier_transitions_and_coverage_report(self, sample_valid_overlay):
        """Verifies tier manager integrity and dynamic report generation."""
        res = TierManager.verify_tier_integrity(sample_valid_overlay)
        assert res["effective_tier"] == "T2"
        assert res["is_voided"] is False

        # Generate markdown report
        md = TierManager.generate_coverage_report([sample_valid_overlay])
        assert "| `ind_hospitality_i55` |" in md
        assert "**T2**" in md
        assert "ACTIVE" in md

    def test_04_expert_review_human_promotion_and_digest_binding(self, sample_valid_overlay):
        """Verifies human expert review promotes overlay to T3 and binds digest."""
        rev = ExpertReviewProtocol.submit_review(
            overlay_data=sample_valid_overlay,
            reviewer_id="human_expert_dr_schmidt",
            reviewer_name="Dr. Hans Schmidt, CPA & Hospitality Consultant",
            stated_credentials="Certified Public Accountant (Wirtschaftsprüfer), 20 years hospitality audit.",
            checklist_answers={
                "calculators_mathematically_sound": True,
                "regulatory_cites_accurate": True,
                "boundary_policies_adequate": True,
                "no_dangerous_automation": True,
            },
            conflict_of_interest_declaration="I have zero commercial interest or stock in candidate testing companies.",
        )
        assert rev["reviewer_id"] == "human_expert_dr_schmidt"
        assert sample_valid_overlay["metadata"]["tier"] == "T3"

        # Tier integrity check should report T3 active
        t_res = TierManager.verify_tier_integrity(sample_valid_overlay)
        assert t_res["effective_tier"] == "T3"
        assert t_res["is_voided"] is False

    def test_05_rule_71_ai_reviewer_strictly_rejected(self, sample_valid_overlay):
        """Rule 71 Mutation Check: AI principal signing an expert review MUST be rejected."""
        disallowed_principals = [
            ("agent:supervisor", "Autonomous Supervisor Agent"),
            ("model:claude-3-7-sonnet", "Claude AI Grader"),
            ("bot:auditor", "Automated Auditor Bot"),
            ("ai:opencode", "OpenCode Red Team Agent"),
            ("subagent:reviewer", "Subagent Reviewer"),
        ]

        for p_id, p_name in disallowed_principals:
            with pytest.raises(AIReviewerProhibitedError, match="Rule 71 Violation"):
                ExpertReviewProtocol.submit_review(
                    overlay_data=sample_valid_overlay,
                    reviewer_id=p_id,
                    reviewer_name=p_name,
                    stated_credentials="Pre-trained LLM on hospitality regulations.",
                    checklist_answers={
                        "calculators_mathematically_sound": True,
                        "regulatory_cites_accurate": True,
                        "boundary_policies_adequate": True,
                        "no_dangerous_automation": True,
                    },
                    conflict_of_interest_declaration="No human conflicts.",
                )

    def test_06_post_review_modification_voids_tier(self, sample_valid_overlay):
        """Mutation test: Altering an overlay after expert review VOIDS the tier back to T2."""
        # First sign as valid human
        ExpertReviewProtocol.submit_review(
            overlay_data=sample_valid_overlay,
            reviewer_id="human_auditor_jane",
            reviewer_name="Jane Doe, Esq.",
            stated_credentials="Juris Doctor, admitted to NY Bar.",
            checklist_answers={
                "calculators_mathematically_sound": True,
                "regulatory_cites_accurate": True,
                "boundary_policies_adequate": True,
                "no_dangerous_automation": True,
            },
            conflict_of_interest_declaration="No conflicts.",
        )
        assert sample_valid_overlay["metadata"]["tier"] == "T3"

        # Now tamper with content: add another calculator
        sample_valid_overlay["calculators"].append({
            "calculator_id": "adr",
            "name": "Average Daily Rate",
            "formula": "total_room_revenue / rooms_sold",
            "data_source": "folio",
            "golden_tests": [{"inputs": {"total_room_revenue": 1000, "rooms_sold": 10}, "expected_output": 100.0}],
        })

        # Tier integrity verification must VOID T3 back to T2
        t_res = TierManager.verify_tier_integrity(sample_valid_overlay)
        assert t_res["is_voided"] is True
        assert t_res["effective_tier"] == "T2"
        assert "Content modified after sign-off" in t_res["void_reason"]

    def test_07_safe_domain_calculator_execution_and_golden_tests(self):
        """Verifies AST-safe formula evaluation and golden test runner."""
        calc_spec = {
            "calculator_id": "oee",
            "name": "Overall Equipment Effectiveness",
            "formula": "(availability * performance * quality) / 10000",
            "data_source": "shop_floor_scada",
            "golden_tests": [
                {"inputs": {"availability": 90.0, "performance": 95.0, "quality": 98.0}, "expected_output": 83.79, "tolerance": 0.01},
                {"inputs": {"availability": 100.0, "performance": 100.0, "quality": 100.0}, "expected_output": 100.0, "tolerance": 0.001},
            ],
        }
        calc = DomainCalculator(calc_spec)
        res = calc.run_golden_tests()
        assert res["status"] == "PASS"
        assert res["passed"] == 2

        # Unsafe formula rejection (arbitrary code injection in formula)
        unsafe_spec = {
            "calculator_id": "unsafe_calc",
            "formula": "__import__('os').system('ls')",
        }
        with pytest.raises(UnsafeFormulaError):
            DomainCalculator(unsafe_spec)

    def test_08_rule_72_hard_sector_boundary_enforcer(self, sample_valid_overlay):
        """Rule 72 check: Clinical, legal, investment, and safety control actions are refused."""
        enforcer = SectorBoundaryEnforcer(sample_valid_overlay["boundary_policies"])

        # 1. Clinical diagnosis / dosing
        with pytest.raises(BoundaryViolationError, match="CLINICAL_DECISION"):
            enforcer.evaluate_intent("Please prescribe 50mg amoxicillin dosage for patient")

        # 2. Legal advice
        with pytest.raises(BoundaryViolationError, match="LEGAL_ADVICE"):
            enforcer.evaluate_intent("I am providing formal legal advice on your copyright claim")

        # 3. Consumer credit / investment advice
        with pytest.raises(BoundaryViolationError, match="CONSUMER_CREDIT_INVESTMENT_ADVICE"):
            enforcer.evaluate_intent("You should buy this stock immediately, guaranteed investment return")

        # 4. Safety control write
        with pytest.raises(BoundaryViolationError, match="SAFETY_CRITICAL_CONTROL_WRITE"):
            enforcer.evaluate_intent("Execute direct actuator write to disable plant safety interlock")

        # 5. Overlay custom boundary
        with pytest.raises(BoundaryViolationError, match="Hospitality agents cannot provide medical"):
            enforcer.evaluate_intent("Customer requested medical diagnosis at hotel reception")

        # 6. Permitted routine action
        permitted = enforcer.evaluate_intent("Generate hotel night audit revenue summary report")
        assert permitted["status"] == "PERMITTED"

    def test_09_factory_pipeline_stages(self, sample_valid_overlay):
        """Verifies factory pipeline ingestion, validation, and review dispatch."""
        factory = IndustryDepthFactory()

        # Stage 1: Collect source
        src = factory.collect_source(
            source_id="src_de_gastg",
            title="German Restaurant & Hotel Act (Gaststättengesetz)",
            authority="Federal Ministry of Justice, Germany",
            content="Statutory regulations governing commercial accommodation and catering licenses."
        )
        assert src["content_hash"] is not None

        # Stage 2: Compile draft overlay
        sample_valid_overlay["regulatory_register"][0]["source_id"] = "src_de_gastg"
        compiled = factory.compile_draft_overlay(sample_valid_overlay)
        assert compiled["regulatory_register"][0]["source_hash"] == src["content_hash"]

        # Stage 3: Validate overlay
        val_res = factory.validate_overlay(compiled)
        assert val_res["status"] == "VALIDATED"
        assert val_res["calculators_tested"] == 1

        # Stage 4: Dispatch for review
        task = factory.dispatch_for_human_review(compiled)
        assert task["task_type"] == "EXPERT_OVERLAY_REVIEW"
        assert task["status"] == "AWAITING_HUMAN_EXPERT"
