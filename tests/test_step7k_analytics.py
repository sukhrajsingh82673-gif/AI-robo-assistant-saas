"""
Tests for Step 7K: Analytics & Business Intelligence Depth
=========================================================
Adheres to:
- Rule 65: Semantic layer as single source of truth for business metrics.
- Rule 62: Human governance on modifications.
- Multi-tenant RLS isolation in Superset guest tokens.
- Fixed asset multi-method depreciation and double-entry balanced journals.
- Meeting intelligence parsing and task extraction.
"""

import pytest
from core.bi.semantic_layer import (
    SemanticLayerEngine,
    SemanticQueryRequest,
    RawSqlExecutionBlocked
)
from core.bi.bi_port import CubeSemanticAdapter
from core.bi.dashboards import SupersetDashboardManager
from core.bi.meeting_intelligence import MeetingIntelligenceEngine
from core.bi.depreciation import AssetDepreciationEngine


def test_01_semantic_layer_standard_metrics():
    engine = SemanticLayerEngine()
    req = SemanticQueryRequest(
        tenant_id="ten_demo",
        company_id="comp_alpha",
        metric_id="arr"
    )
    res = engine.query_metric(req, underlying_data={"mrr": 25000.0})
    assert res.metric_id == "arr"
    assert res.value == 300000.0
    assert res.unit == "currency"
    assert res.dimensions["tenant_id"] == "ten_demo"


def test_02_semantic_layer_cash_conversion_cycle():
    engine = SemanticLayerEngine()
    req = SemanticQueryRequest(
        tenant_id="ten_demo",
        company_id="comp_alpha",
        metric_id="ccc"
    )
    res = engine.query_metric(req, underlying_data={"dio": 60.0, "dso": 45.0, "dpo": 50.0})
    assert res.metric_id == "ccc"
    assert res.value == 55.0
    assert res.unit == "days"


def test_03_rule_65_raw_sql_execution_blocked():
    engine = SemanticLayerEngine()
    with pytest.raises(RawSqlExecutionBlocked) as exc_info:
        engine.execute_raw_sql("SELECT * FROM financial_transactions WHERE amount > 1000", principal_role="agent")
    assert "Rule 65 Violation" in str(exc_info.value)

    # Admin / system execution allowed
    admin_res = engine.execute_raw_sql("SELECT count(*) FROM companies", principal_role="system_admin")
    assert admin_res["executed"] is True


def test_04_bi_port_and_mcp_tool_adapter():
    adapter = CubeSemanticAdapter()
    mcp_out = adapter.mcp_cube_analytics(
        tenant_id="ten_test",
        company_id="comp_test",
        metric="dso",
        underlying_data={"ar_balance": 150000.0, "credit_sales": 1000000.0}
    )
    assert mcp_out["metric"] == "Days Sales Outstanding"
    assert mcp_out["value"] == 54.75
    assert mcp_out["unit"] == "days"
    assert mcp_out["provenance"] == "Cube_Semantic_Engine"


def test_05_superset_dashboard_specs_and_guest_tokens():
    mgr = SupersetDashboardManager()
    fin_dash = mgr.get_dashboard_spec("FIN")
    assert fin_dash is not None
    assert fin_dash.dashboard_id == "dash_fin_exec"
    assert len(fin_dash.charts) >= 2

    # Guest token RLS generation
    token = mgr.generate_guest_token("ten_tenant99", "comp_co12", "usr_agent1", validity_seconds=1800)
    assert token.guest_token.startswith("superset_gt_")
    assert token.tenant_id == "ten_tenant99"
    assert token.company_id == "comp_co12"
    assert token.rls_clause == "tenant_id = 'ten_tenant99' AND company_id = 'comp_co12'"
    assert token.expires_at > 0


def test_06_meeting_intelligence_parser():
    transcript = """
    Alice: We need to finalize the quarterly filing. Bob will submit the SEC draft by Friday.
    Charlie: Agreed on adopting Cube for the semantic layer.
    David to review the procurement contracts by 2026-12-01.
    Alice: Decided to approve the new marketing budget.
    """
    agenda = ["Quarterly Filing", "BI Architecture", "Marketing Budget"]
    res = MeetingIntelligenceEngine.parse_transcript("Executive Alignment", agenda, transcript)

    assert res.meeting_title == "Executive Alignment"
    assert len(res.agenda_topics) == 3
    assert len(res.action_items) >= 2
    # Verify action items
    owners = [a.owner for a in res.action_items]
    assert "Bob" in owners or "David" in owners
    # Verify decisions
    assert any("adopting Cube" in d or "marketing budget" in d for d in res.key_decisions)


def test_07_fixed_asset_depreciation_schedules():
    engine = AssetDepreciationEngine()
    cost = 120000.0
    salvage = 20000.0
    life = 5

    # Straight-line: (120,000 - 20,000) / 5 = 20,000/yr
    sl = engine.calculate_straight_line("asset_mach_1", cost, salvage, life)
    assert sl.method == "STRAIGHT_LINE"
    assert len(sl.annual_entries) == 5
    assert sl.annual_entries[0].depreciation_expense == 20000.0
    assert sl.annual_entries[-1].ending_book_value == 20000.0

    # Declining balance (double declining: rate = 2/5 = 40%)
    db = engine.calculate_declining_balance("asset_mach_1", cost, salvage, life)
    assert db.method == "DECLINING_BALANCE"
    assert len(db.annual_entries) == 5
    assert db.annual_entries[0].depreciation_expense == 48000.0
    assert db.annual_entries[-1].ending_book_value >= salvage

    # Sum-of-Years'-Digits (SYD): 1+2+3+4+5 = 15. Year 1: 5/15 * 100k = 33,333.33
    syd = engine.calculate_sum_of_years_digits("asset_mach_1", cost, salvage, life)
    assert syd.method == "SUM_OF_YEARS_DIGITS"
    assert syd.annual_entries[0].depreciation_expense == 33333.33

    # Balanced monthly journal entry
    jrn = engine.generate_monthly_journal_entry("asset_mach_1", 24000.0, "2026-11-30")
    assert jrn.debit_account == "6000_Depreciation_Expense"
    assert jrn.credit_account == "1500_Accumulated_Depreciation"
    assert jrn.debit_amount == 2000.0
    assert jrn.credit_amount == 2000.0
    assert jrn.is_balanced is True
