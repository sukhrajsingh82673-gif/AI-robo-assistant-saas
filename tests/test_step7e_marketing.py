"""
Unit & Contract Tests for Step 7E: Marketing & Brand Depth.
===========================================================
"""

import pytest
from core.marketing.brand import BrandGuidelinesValidator
from core.marketing.claim_verifier import ContentClaimVerifier
from core.marketing.campaign import Campaign, CampaignLifecycleManager
from core.marketing.attribution import MultiTouchAttributionEngine, Touchpoint
from core.marketing.marketing_port import (
    GoogleAdsAdapter, MetaAdsAdapter, LinkedInAdsAdapter
)
from core.departments.models import DepartmentBudget


# --- 1. BRAND GUIDELINES & RULE 44 TESTS ---

def test_01_brand_guidelines_compliant_copy():
    validator = BrandGuidelinesValidator()
    clean_copy = (
        "ZONATA provides sovereign autonomous orchestration for modern enterprise operations. "
        "Engineered for mathematical precision and auditability."
    )
    res = validator.validate_copy(clean_copy)
    assert res.is_compliant is True
    assert len(res.violations) == 0


def test_02_brand_guidelines_violations_and_rule_44():
    validator = BrandGuidelinesValidator()

    # Superlative check
    sup_copy = "ZONATA is the fastest and cheapest solution on the market."
    res_sup = validator.validate_copy(sup_copy)
    assert res_sup.is_compliant is False
    cats = {v.category for v in res_sup.violations}
    assert "forbidden_superlative" in cats

    # Disallowed term check
    dis_copy = "Experience the magic of autonomous agents."
    res_dis = validator.validate_copy(dis_copy)
    assert res_dis.is_compliant is False
    assert any(v.category == "disallowed_term" for v in res_dis.violations)

    # Rule 44: 'better than human' assertion strictly banned
    rule44_copy = "Our AI system is better than human accountants and eliminates all humans."
    res_44 = validator.validate_copy(rule44_copy)
    assert res_44.is_compliant is False
    assert any(v.category == "rule_44_claim" for v in res_44.violations)


# --- 2. CONTENT CLAIM VERIFICATION TESTS ---

def test_03_content_claim_verification():
    verifier = ContentClaimVerifier()

    # Copy with verified statistics (99.99% uptime, 10,000 tps)
    verified_text = "Delivering 99.99% uptime and handling up to 10,000 tps in benchmark trials."
    res = verifier.verify_claims(verified_text)
    assert res.is_verified is True
    assert len(res.verified_claims) >= 2
    assert len(res.unverified_claims) == 0

    # Copy with unverified statistical assertion
    unverified_text = "Offering 99.5% accuracy on autonomous tax filings."
    res_unv = verifier.verify_claims(unverified_text)
    assert res_unv.is_verified is False
    assert len(res_unv.unverified_claims) > 0


# --- 3. CAMPAIGN LIFECYCLE & BUDGET COMMIT TESTS ---

def test_04_campaign_lifecycle_and_budget_commit():
    mgr = CampaignLifecycleManager()
    budget = DepartmentBudget(
        id="bgt_mktg",
        tenant_id="t1",
        company_id="c1",
        department_id="dept_mktg",
        currency="INR",
        total_budget=50000.0,
        valid_from="2026-10-01",
        valid_to="2026-12-31"
    )

    camp = Campaign(
        campaign_id="CAMP-01",
        tenant_id="t1",
        company_id="c1",
        name="Q4 SaaS Enterprise Launch",
        channel="linkedin",
        target_audience="CTOs, CFOs",
        creative_copy="Initial Draft",
        budget_allocated=20000.0
    )

    # 1. Advance to creative
    camp = mgr.advance_to_creative(camp, "Approved Enterprise Copy")
    assert camp.stage == "creative"

    # 2. Brand review
    camp = mgr.complete_brand_review(camp, is_brand_compliant=True)
    assert camp.stage == "brand_approved"

    # 3. Legal review
    camp = mgr.complete_legal_review(camp, "LEGAL-APPROVAL-SIG-1234", "legal_counsel_principal")
    assert camp.stage == "legal_approved"

    # 4. Commit budget
    camp = mgr.commit_campaign_budget(camp, budget)
    assert camp.stage == "budget_committed"
    assert budget.spend_committed == 20000.0
    assert budget.available_budget() == 30000.0

    # 5. Schedule campaign
    camp = mgr.schedule_campaign(camp)
    assert camp.stage == "scheduled"


# --- 4. FIRST-PARTY ATTRIBUTION TESTS ---

def test_05_multi_touch_attribution_models():
    engine = MultiTouchAttributionEngine()
    touchpoints = [
        Touchpoint(touchpoint_id="tp_1", user_id="u_10", campaign_id="CAMP_SEARCH", channel="google_ads", timestamp="2026-10-01T10:00:00"),
        Touchpoint(touchpoint_id="tp_2", user_id="u_10", campaign_id="CAMP_SOCIAL", channel="linkedin", timestamp="2026-10-05T14:00:00"),
        Touchpoint(touchpoint_id="tp_3", user_id="u_10", campaign_id="CAMP_EMAIL", channel="email", timestamp="2026-10-10T09:00:00"),
    ]
    conversion_val = 1000.0

    # First Touch (100% to CAMP_SEARCH)
    res_first = engine.calculate_attribution(touchpoints, conversion_val, model="FIRST_TOUCH")
    assert res_first.campaign_credits["CAMP_SEARCH"] == 1000.0
    assert "CAMP_SOCIAL" not in res_first.campaign_credits

    # Last Touch (100% to CAMP_EMAIL)
    res_last = engine.calculate_attribution(touchpoints, conversion_val, model="LAST_TOUCH")
    assert res_last.campaign_credits["CAMP_EMAIL"] == 1000.0

    # Linear (1/3 each = 333.33)
    res_linear = engine.calculate_attribution(touchpoints, conversion_val, model="LINEAR")
    assert round(sum(res_linear.campaign_credits.values()), 0) == 1000.0
    assert res_linear.campaign_credits["CAMP_SEARCH"] == 333.33

    # U-Shaped (40% first, 40% last, 20% middle)
    res_u = engine.calculate_attribution(touchpoints, conversion_val, model="U_SHAPED")
    assert res_u.campaign_credits["CAMP_SEARCH"] == 400.0
    assert res_u.campaign_credits["CAMP_SOCIAL"] == 200.0
    assert res_u.campaign_credits["CAMP_EMAIL"] == 400.0


# --- 5. MARKETING PORT & AD ADAPTERS ---

def test_06_marketing_platform_adapters():
    g_ads = GoogleAdsAdapter(token_provider=lambda: "mock_openbao_token")
    m_ads = MetaAdsAdapter(token_provider=lambda: "mock_openbao_token")
    li_ads = LinkedInAdsAdapter(token_provider=lambda: "mock_openbao_token")

    camp = Campaign(
        campaign_id="CAMP-99",
        tenant_id="t1",
        company_id="c1",
        name="Omnichannel Sprint",
        channel="omni",
        target_audience="B2B Founders",
        creative_copy="Enterprise copy",
        budget_allocated=15000.0
    )

    for adapter in [g_ads, m_ads, li_ads]:
        res = adapter.publish_ad(camp)
        assert res["status"] == "published"
        assert res["campaign_id"] == "CAMP-99"

        perf = adapter.get_performance("CAMP-99")
        assert perf["impressions"] > 0
        assert perf["clicks"] > 0

        pause_res = adapter.pause_ad("CAMP-99")
        assert pause_res["status"] == "paused"
