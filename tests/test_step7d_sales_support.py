"""
Unit & Contract Tests for Step 7D: Sales, CRM & Customer Support Depth.
=======================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta
from core.sales.lead_engine import LeadEngine, Lead
from core.sales.consent import OutreachConsentManager, ConsentRecord
from core.sales.quotes import QuoteGenerator, QuoteLine
from core.sales.negotiation import BoundedNegotiationEngine
from core.sales.crm_port import (
    NativeCrmAdapter, TwentyCrmAdapter, HubSpotCrmAdapter, CrmContact, CrmDeal
)
from core.support.helpdesk_port import (
    NativeHelpdeskAdapter, ChatwootAdapter, ZammadAdapter, SupportTicket
)
from core.support.ticket_lifecycle import (
    TicketClassifier, TicketRouter, GovernedAutoResponder
)
from core.support.sla_clock import SLAEscalationClock, SLAConfig


# --- 1. LEAD CAPTURE & DEDUPLICATION TESTS ---

def test_01_lead_capture_and_deduplication():
    engine = LeadEngine()
    lead1 = Lead(
        lead_id="lead_101",
        tenant_id="t1",
        company_id="c1",
        first_name="Alice",
        last_name="Smith",
        email="alice@acmecorp.com",
        phone="+919876543210",
        company_name="Acme Corp"
    )
    captured, is_dup, reason = engine.capture_lead(lead1)
    assert is_dup is False
    assert captured.domain == "acmecorp.com"

    # Duplicate by email
    lead2 = Lead(
        lead_id="lead_102",
        tenant_id="t1",
        company_id="c1",
        first_name="A.",
        last_name="Smith",
        email="ALICE@acmecorp.com",  # Case difference
        phone="+919000000000"
    )
    dup, is_dup2, reason2 = engine.capture_lead(lead2)
    assert is_dup2 is True
    assert dup.lead_id == "lead_101"
    assert "Duplicate email" in reason2

    # Duplicate by phone
    lead3 = Lead(
        lead_id="lead_103",
        tenant_id="t1",
        company_id="c1",
        first_name="Alice",
        last_name="S",
        email="other@acmecorp.com",
        phone="(+91) 98765-43210"
    )
    dup3, is_dup3, reason3 = engine.capture_lead(lead3)
    assert is_dup3 is True
    assert dup3.lead_id == "lead_101"


# --- 2. OUTREACH CONSENT VERIFICATION (RULE 64) ---

def test_02_outreach_consent_enforcement():
    mgr = OutreachConsentManager()
    mgr.suppress_contact("unsub@example.com")

    # Suppression list block
    permitted, reason = mgr.verify_outreach_permission("t1", "c1", "contact_99", "unsub@example.com", "email")
    assert permitted is False
    assert "suppression/unsubscribe list" in reason

    # Record legitimate interest for email
    rec_email = ConsentRecord(
        contact_id="c_101",
        tenant_id="t1",
        company_id="c1",
        channel="email",
        lawful_basis="legitimate_interest",
        source_citation="B2B Directory Enquiry"
    )
    mgr.record_consent(rec_email)

    p_email, _ = mgr.verify_outreach_permission("t1", "c1", "c_101", "valid@corp.com", "email")
    assert p_email is True

    # WhatsApp requires express consent: legitimate interest is insufficient
    rec_wa = ConsentRecord(
        contact_id="c_101",
        tenant_id="t1",
        company_id="c1",
        channel="whatsapp",
        lawful_basis="legitimate_interest",
        source_citation="Web Form"
    )
    mgr.record_consent(rec_wa)
    p_wa, reason_wa = mgr.verify_outreach_permission("t1", "c1", "c_101", "+919876543210", "whatsapp")
    assert p_wa is False
    assert "express_consent" in reason_wa


# --- 3. QUOTES WITH MARGIN & DISCOUNT GUARDRAILS ---

def test_03_quote_guardrails_and_gateway():
    gen = QuoteGenerator(max_autonomous_discount_pct=0.20, min_gross_margin_pct=0.25)
    lines = [
        QuoteLine(item_id="PROD-1", description="SaaS License", quantity=10.0, list_price=1000.0, cost_price=400.0, discount_pct=0.10)
    ]
    # 10% discount: auto-approved
    quote1 = gen.generate_quote("Q-001", "t1", "c1", "cust_1", lines)
    assert quote1.gateway_approval_required is False
    assert quote1.is_approved is True

    # 30% discount: exceeds 20% limit, requires gateway approval (Rule 62)
    lines2 = [
        QuoteLine(item_id="PROD-1", description="SaaS License", quantity=10.0, list_price=1000.0, cost_price=400.0, discount_pct=0.30)
    ]
    quote2 = gen.generate_quote("Q-002", "t1", "c1", "cust_1", lines2)
    assert quote2.gateway_approval_required is True
    assert quote2.is_approved is False

    # Human gateway approval
    approved = gen.approve_quote_via_gateway(quote2, "GATEWAY-SIG-8877", "vp_sales")
    assert approved.is_approved is True
    assert approved.approval_token == "GATEWAY-SIG-8877"


# --- 4. BOUNDED NEGOTIATION ENGINE ---

def test_04_bounded_negotiation():
    neg = BoundedNegotiationEngine()
    # List: $10,000, Floor: $8,000, Max concession 15% ($8,500), Step 5% ($500)
    state = neg.initialize_negotiation(
        deal_id="DEAL-77",
        list_price=10000.0,
        floor_price=8000.0,
        max_concession_pct=0.15,
        step_pct=0.05
    )
    assert state.current_offered_price == 10000.0

    # Round 1: Buyer offers $9,200 (we counter at 5% off list = $9,500)
    s1, msg1 = neg.evaluate_counter_offer(state, 9200.0)
    assert s1.current_round == 1
    assert s1.current_offered_price == 9500.0
    assert "Counter-offering" in msg1

    # Round 2: Buyer offers $9,500 (matches our counter proposal)
    s2, msg2 = neg.evaluate_counter_offer(s1, 9500.0)
    assert s2.is_concluded is True
    assert s2.outcome == "ACCEPTED"

    # Walk away scenario: buyer offers ridiculous low ball below floor
    state_low = neg.initialize_negotiation("DEAL-99", 10000.0, 8000.0, 0.15, 0.05)
    s_low, msg_low = neg.evaluate_counter_offer(state_low, 5000.0)
    assert s_low.is_concluded is True
    assert s_low.outcome == "WALK_AWAY"


# --- 5. CRM PORT & ADAPTERS ---

def test_05_crm_adapters():
    native_crm = NativeCrmAdapter()
    twenty_crm = TwentyCrmAdapter()
    hubspot_crm = HubSpotCrmAdapter(token_provider=lambda: "mock_openbao_token")

    for adapter in [native_crm, twenty_crm, hubspot_crm]:
        c = CrmContact(contact_id="c_1", tenant_id="t1", company_id="c1", email="lead@corp.com", first_name="John", last_name="Doe")
        adapter.upsert_contact(c)
        assert adapter.get_contact("t1", "c1", "c_1").email == "lead@corp.com"

        d = CrmDeal(deal_id="d_1", tenant_id="t1", company_id="c1", contact_id="c_1", deal_name="Annual Sub", amount=50000.0)
        adapter.create_deal(d)
        updated = adapter.update_deal_stage("t1", "c1", "d_1", "closed_won")
        assert updated.stage == "closed_won"


# --- 6. CUSTOMER SUPPORT, TICKETS & SLA ESCALATION ---

def test_06_ticket_classification_and_routing():
    ticket = SupportTicket(
        ticket_id="TICK-101",
        tenant_id="t1",
        company_id="c1",
        customer_id="cust_8",
        customer_email="c@acme.com",
        subject="CRITICAL: Outage on Production Server",
        body="Our system is down and we are facing data loss! Please fix asap."
    )
    classified = TicketClassifier.classify(ticket)
    assert classified.urgency == "critical"
    assert classified.sentiment == "negative"
    assert classified.topic == "technical"

    # Router
    router = TicketRouter(
        agent_skills={"agent_billing": ["billing"], "agent_tech": ["technical", "general"]},
        agent_capacity={"agent_tech": 3}
    )
    assigned = router.route_ticket(classified, current_agent_workload={"agent_tech": 1})
    assert assigned == "agent_tech"

    # Governed auto-responder: critical ticket requires human approval
    proposal = GovernedAutoResponder.generate_response(classified)
    assert proposal.human_approval_required is True


def test_07_sla_escalation_clock_triggers():
    clock = SLAEscalationClock()
    state = clock.initialize_clock("TICK-202", priority="critical")
    # Critical resolution SLA is 120 minutes
    assert state.resolution_sla_minutes == 120

    created_dt = datetime.fromisoformat(state.created_at)

    # 1. 60 minutes later (50% window) -> Warning
    t_50 = created_dt + timedelta(minutes=61)
    s_50, pct_50, act_50 = clock.evaluate_clock(state, current_time=t_50)
    assert s_50.escalation_level == "warning_50"
    assert act_50 == "WARNING_INTERNAL_NOTIFICATION"

    # 2. 95 minutes later (79% window) -> Alert 75
    t_75 = created_dt + timedelta(minutes=95)
    s_75, pct_75, act_75 = clock.evaluate_clock(state, current_time=t_75)
    assert s_75.escalation_level == "alert_75"
    assert act_75 == "SUPERVISOR_ALERT"

    # 3. 110 minutes later (91% window) -> Executive Escalation 90
    t_90 = created_dt + timedelta(minutes=110)
    s_90, pct_90, act_90 = clock.evaluate_clock(state, current_time=t_90)
    assert s_90.escalation_level == "escalation_90"
    assert act_90 == "EXECUTIVE_ESCALATION"

    # 4. 125 minutes later (104% window) -> Breach
    t_100 = created_dt + timedelta(minutes=125)
    s_100, pct_100, act_100 = clock.evaluate_clock(state, current_time=t_100)
    assert s_100.escalation_level == "breached_100"
    assert act_100 == "BREACH_CRITICAL_DISPATCH"
