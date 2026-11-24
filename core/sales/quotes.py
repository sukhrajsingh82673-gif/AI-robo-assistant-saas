"""
Sales Quote Generation Engine with Margin & Discount Guardrails
==============================================================
Adheres to:
- Rule 62: Reserved Human Financial Decisions
- Invariant: Quotes with discounts > 20% require mandatory manager gateway approval.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class QuoteLine(BaseModel):
    item_id: str
    description: str
    quantity: float
    list_price: float
    cost_price: float
    discount_pct: float = Field(0.0, ge=0.0, le=1.0)

    def subtotal_list(self) -> float:
        return self.quantity * self.list_price

    def subtotal_discounted(self) -> float:
        return self.quantity * (self.list_price * (1.0 - self.discount_pct))

    def subtotal_cost(self) -> float:
        return self.quantity * self.cost_price


class Quote(BaseModel):
    quote_id: str
    tenant_id: str
    company_id: str
    customer_id: str
    currency: str = "INR"
    lines: List[QuoteLine]
    total_list_amount: float = 0.0
    total_discounted_amount: float = 0.0
    overall_discount_pct: float = 0.0
    total_cost_amount: float = 0.0
    gross_margin_pct: float = 0.0
    gateway_approval_required: bool = False
    is_approved: bool = False
    approval_token: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class QuoteGenerator:
    """Calculates quotes, margins, and enforces discount threshold guardrails."""

    def __init__(self, max_autonomous_discount_pct: float = 0.20, min_gross_margin_pct: float = 0.25):
        self.max_autonomous_discount_pct = max_autonomous_discount_pct
        self.min_gross_margin_pct = min_gross_margin_pct

    def generate_quote(self, quote_id: str, tenant_id: str, company_id: str, customer_id: str, lines: List[QuoteLine], currency: str = "INR") -> Quote:
        total_list = sum(l.subtotal_list() for l in lines)
        total_discounted = sum(l.subtotal_discounted() for l in lines)
        total_cost = sum(l.subtotal_cost() for l in lines)

        overall_discount = (total_list - total_discounted) / total_list if total_list > 0 else 0.0
        gross_margin = (total_discounted - total_cost) / total_discounted if total_discounted > 0 else 0.0

        # Rule 62: Discounts > 20% require manager gateway approval
        approval_required = overall_discount > self.max_autonomous_discount_pct or gross_margin < self.min_gross_margin_pct

        return Quote(
            quote_id=quote_id,
            tenant_id=tenant_id,
            company_id=company_id,
            customer_id=customer_id,
            currency=currency,
            lines=lines,
            total_list_amount=round(total_list, 2),
            total_discounted_amount=round(total_discounted, 2),
            overall_discount_pct=round(overall_discount, 4),
            total_cost_amount=round(total_cost, 2),
            gross_margin_pct=round(gross_margin, 4),
            gateway_approval_required=approval_required,
            is_approved=not approval_required
        )

    def approve_quote_via_gateway(self, quote: Quote, approval_token: str, approver_principal_id: str) -> Quote:
        if not quote.gateway_approval_required:
            quote.is_approved = True
            return quote

        if not approval_token or not approver_principal_id:
            raise ValueError("Gateway approval requires a verified signature and authorizer principal")

        quote.is_approved = True
        quote.approval_token = approval_token
        return quote
