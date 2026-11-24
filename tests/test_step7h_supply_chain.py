"""
Unit & Contract Tests for Step 7H: Supply Chain & Procurement Depth.
====================================================================
"""

import pytest
import math
from core.procurement.sanctions import SanctionsScreeningEngine, SanctionedEntity
from core.procurement.rfq import RFQ, RFQQuote, RFQManager
from core.procurement.inventory_policy import ReorderPolicyEngine
from core.procurement.carrier_tracking import SovereignLogisticsAdapter


# --- 1. SANCTIONS & WATCHLIST SCREENING TESTS ---

def test_01_sanctions_screening_clean_and_hit():
    engine = SanctionsScreeningEngine()

    # Clean vendor passes
    res_clean = engine.screen_vendor("VEND-100", "Tata Steel International Ltd")
    assert res_clean.is_sanctioned is False
    assert res_clean.action_taken == "APPROVED"
    is_frozen, _ = engine.is_vendor_frozen("VEND-100")
    assert is_frozen is False

    # Sanctioned entity hit triggers immediate freeze
    res_hit = engine.screen_vendor("VEND-666", "Al-Barakaat Trading Company")
    assert res_hit.is_sanctioned is True
    assert res_hit.action_taken == "FROZEN"
    assert res_hit.matched_entry["list"] == "UN_CONSOLIDATED"

    # Confirmed frozen in registry
    is_frozen_hit, reason = engine.is_vendor_frozen("VEND-666")
    assert is_frozen_hit is True
    assert "UN_CONSOLIDATED" in reason


# --- 2. RFQ COMPARISON MATRIX & HUMAN AWARD GATE (RULE 62) ---

def test_02_rfq_comparison_matrix_and_award_gate():
    manager = RFQManager(price_weight=0.40, lead_time_weight=0.25, quality_weight=0.25, terms_weight=0.10)
    rfq = RFQ(
        rfq_id="RFQ-9001",
        tenant_id="t1",
        company_id="c1",
        item_id="COMP-CHASSIS",
        required_quantity=50.0,
        quotes=[
            # Vendor A: Cheaper but longer lead time
            RFQQuote(quote_id="Q-A", vendor_id="V-A", vendor_name="Vendor A", unit_price=100.0, total_price=5000.0, lead_time_days=10, quality_score=85.0, payment_terms_days=30),
            # Vendor B: Slightly more expensive, much faster lead time, high quality
            RFQQuote(quote_id="Q-B", vendor_id="V-B", vendor_name="Vendor B", unit_price=105.0, total_price=5250.0, lead_time_days=3, quality_score=95.0, payment_terms_days=60),
            # Vendor C: Expensive, slow
            RFQQuote(quote_id="Q-C", vendor_id="V-C", vendor_name="Vendor C", unit_price=140.0, total_price=7000.0, lead_time_days=15, quality_score=70.0, payment_terms_days=15),
        ]
    )

    scores = manager.evaluate_rfq_quotes(rfq)
    assert len(scores) == 3
    # Check that Vendor B is recommended due to superior lead time (3d), quality (95), and terms (60d)
    best = next(s for s in scores if s.is_recommended)
    assert best.quote_id == "Q-B"

    # Contract award without gateway approval fails (Rule 62)
    with pytest.raises(ValueError):
        manager.award_contract_via_gateway(rfq, "Q-B", approval_token="", authorizer_principal_id="")

    # Award with human gateway authorization succeeds
    awarded_rfq = manager.award_contract_via_gateway(
        rfq, "Q-B",
        approval_token="GATEWAY-PROCURE-SIG-5544",
        authorizer_principal_id="cpo_principal"
    )
    assert awarded_rfq.status == "awarded"
    assert awarded_rfq.awarded_quote_id == "Q-B"
    assert awarded_rfq.gateway_approved is True


# --- 3. INVENTORY POLICY & REORDER POINT (EOQ / ROP) ---

def test_03_inventory_policy_eoq_and_rop():
    # Annual Demand D = 10,000 units
    # Order Cost S = 50 INR
    # Holding Cost H = 2 INR/unit/year
    # EOQ = sqrt((2 * 10000 * 50) / 2) = sqrt(500,000) = 707.11 units
    # Lead time L = 9 days
    # Daily demand d = 10,000 / 365 = 27.397
    # Lead time demand = 27.397 * 9 = 246.57
    # Safety Stock = 1.65 * 5.0 * sqrt(9) = 1.65 * 5 * 3 = 24.75
    # ROP = 246.57 + 24.75 = 271.32
    policy = ReorderPolicyEngine.calculate_policy(
        item_id="COMP-GEAR",
        annual_demand=10000.0,
        order_cost=50.0,
        holding_cost=2.0,
        lead_time_days=9.0,
        demand_std_dev=5.0,
        service_level_z=1.65
    )

    assert policy.eoq == 707.11
    assert policy.safety_stock == 24.75
    assert policy.reorder_point == 271.33

    # Stock above ROP -> No purchase requisition
    needed, req = ReorderPolicyEngine.check_stock_and_reorder(policy, current_available_stock=350.0)
    assert needed is False
    assert req is None

    # Stock at or below ROP -> Triggers Purchase Requisition for EOQ
    needed_low, req_low = ReorderPolicyEngine.check_stock_and_reorder(policy, current_available_stock=250.0)
    assert needed_low is True
    assert req_low.recommended_order_quantity == 707.11
    assert req_low.current_stock == 250.0


# --- 4. CARRIER TRACKING & LOGISTICS PORT ---

def test_04_carrier_tracking_lifecycle():
    adapter = SovereignLogisticsAdapter()
    shipment = adapter.create_shipment("DHL", "Warehouse-Mumbai", "Client-Bengaluru")
    track_num = shipment.tracking_number
    assert shipment.current_status == "label_created"
    assert "DHL" in track_num

    # Advance: label_created -> in_transit
    s_transit = adapter.advance_status(track_num, "in_transit", "Mumbai Hub", "Package scanned into transit")
    assert s_transit.current_status == "in_transit"

    # Advance: in_transit -> out_for_delivery
    s_out = adapter.advance_status(track_num, "out_for_delivery", "Bengaluru Hub", "Out with delivery agent")
    assert s_out.current_status == "out_for_delivery"

    # Advance: out_for_delivery -> delivered
    s_delivered = adapter.advance_status(track_num, "delivered", "Client-Bengaluru", "Delivered and signed by recipient")
    assert s_delivered.current_status == "delivered"
    assert len(s_delivered.events) == 4

    # Invalid state transition: delivered -> in_transit raises ValueError
    with pytest.raises(ValueError):
        adapter.advance_status(track_num, "in_transit", "Nowhere", "Impossible move")
