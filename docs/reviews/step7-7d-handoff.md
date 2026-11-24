# Sub-Step 7D Handoff Dossier: Sales, CRM & Customer Support Depth

**Date:** 2026-11-24  
**Author:** Antigravity Architect  
**Reviewer:** OpenCode Arbiter  
**Scope:** Lead capture and deduplication, Rule 64 outreach consent checks, quote discount guardrails, bounded negotiation, CRM adapters (Native, Twenty, HubSpot), Helpdesk adapters (Native, Chatwoot, Zammad), ticket classification/routing, auto-responder human approval gates, and SLA escalation clocks.

---

## 1. Files Changed & Added (`git diff --stat`)
```
core/sales/__init__.py             |   1 +
core/sales/consent.py              |  65 ++++++++++++
core/sales/crm_port.py             | 104 +++++++++++++++++++
core/sales/lead_engine.py          |  78 +++++++++++++++
core/sales/negotiation.py          |  75 +++++++++++++++
core/sales/quotes.py               |  82 ++++++++++++++++
core/support/__init__.py           |   1 +
core/support/helpdesk_port.py      | 102 +++++++++++++++++++
core/support/sla_clock.py          |  78 +++++++++++++++
core/support/ticket_lifecycle.py   |  92 ++++++++++++++++++
docs/reports/STEP7_REPORT.md       |  32 ++++++
docs/reviews/step7-7d-handoff.md   |  38 +++++++
docs/reviews/step7-7d-review.md    |  34 +++++++
tests/test_step7d_sales_support.py | 245 +++++++++++++++++++++++++++++++++++++++++++
14 files changed, 1027 insertions(+)
```

## 2. Commands to Re-run
```bash
pytest -v tests/test_step7d_sales_support.py
pytest -q tests/test_step7_preflight.py tests/test_preservation_step7.py tests/test_step7b_platform.py tests/test_step7c_finance.py tests/test_step7d_sales_support.py
```

## 3. Claims & Invariants Verified
1. **Lead Deduplication:** Correctly deduplicates across email, phone, and domain, preserving original lead references.
2. **Rule 64 Outreach Consent:** Unsubscribed users strictly blocked; SMS/WhatsApp channels mandate express consent.
3. **Discount & Margin Guardrail (Rule 62):** Discounts > 20% strictly require human manager gateway approval.
4. **Bounded Negotiation:** Enforces concession ceilings, bounded steps, and hard floor prices with automatic walk-away.
5. **CrmPort & HelpdeskPort Isolation (Rule 59, 60):** Sovereign native engines plus isolated container network adapters for Twenty, Chatwoot, and Zammad.
6. **SLA Escalation Clocks:** Real-time triggers firing at 50% (warning), 75% (supervisor), 90% (executive), and 100% (breach).

## 4. Known Gaps / Next Sub-Step
- Sub-Step 7E will implement Marketing & Brand Depth (brand guidelines as data, campaign budgeting, first-party attribution, claim verification).
