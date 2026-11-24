"""
Request for Quote (RFQ) Pipeline & Comparison Matrix Engine
===========================================================
Adheres to:
- Rule 62: Reserved Human Financial Decisions (Awarding contract requires human gateway approval)
- Multi-criteria quote evaluation: Price, Lead Time, Quality Rating, Payment Terms.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RFQQuote(BaseModel):
    quote_id: str
    vendor_id: str
    vendor_name: str
    unit_price: float
    total_price: float
    lead_time_days: int
    quality_score: float  # out of 100
    payment_terms_days: int  # e.g. 30 for Net 30, 60 for Net 60
    currency: str = "INR"


class RFQComparisonScore(BaseModel):
    quote_id: str
    vendor_id: str
    composite_score: float  # 0 to 100
    price_score: float
    lead_time_score: float
    quality_score: float
    payment_terms_score: float
    is_recommended: bool = False


class RFQ(BaseModel):
    rfq_id: str
    tenant_id: str
    company_id: str
    item_id: str
    required_quantity: float
    currency: str = "INR"
    status: str = "open"  # 'open', 'quotes_received', 'evaluated', 'awarded', 'closed'
    quotes: List[RFQQuote] = Field(default_factory=list)
    awarded_quote_id: Optional[str] = None
    gateway_approved: bool = False
    award_approval_token: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RFQManager:
    """Manages RFQ quote collection, comparison scoring, and award authorization."""

    def __init__(self, price_weight: float = 0.40, lead_time_weight: float = 0.25, quality_weight: float = 0.25, terms_weight: float = 0.10):
        self.w_price = price_weight
        self.w_lead = lead_time_weight
        self.w_qual = quality_weight
        self.w_terms = terms_weight

    def evaluate_rfq_quotes(self, rfq: RFQ) -> List[RFQComparisonScore]:
        if not rfq.quotes:
            return []

        min_price = min(q.total_price for q in rfq.quotes)
        min_lead = min(q.lead_time_days for q in rfq.quotes)
        max_terms = max(q.payment_terms_days for q in rfq.quotes) or 1

        scores: List[RFQComparisonScore] = []
        best_quote_id = None
        max_composite = -1.0

        for q in rfq.quotes:
            p_score = (min_price / q.total_price) * 100.0 if q.total_price > 0 else 100.0
            l_score = (min_lead / q.lead_time_days) * 100.0 if q.lead_time_days > 0 else 100.0
            q_score = q.quality_score
            t_score = (q.payment_terms_days / max_terms) * 100.0

            composite = round(
                (self.w_price * p_score) +
                (self.w_lead * l_score) +
                (self.w_qual * q_score) +
                (self.w_terms * t_score),
                2
            )

            if composite > max_composite:
                max_composite = composite
                best_quote_id = q.quote_id

            scores.append(RFQComparisonScore(
                quote_id=q.quote_id,
                vendor_id=q.vendor_id,
                composite_score=composite,
                price_score=round(p_score, 2),
                lead_time_score=round(l_score, 2),
                quality_score=round(q_score, 2),
                payment_terms_score=round(t_score, 2),
                is_recommended=False
            ))

        for s in scores:
            if s.quote_id == best_quote_id:
                s.is_recommended = True

        rfq.status = "evaluated"
        return scores

    def award_contract_via_gateway(
        self,
        rfq: RFQ,
        selected_quote_id: str,
        approval_token: str,
        authorizer_principal_id: str
    ) -> RFQ:
        """Rule 62: Awarding a supplier contract strictly mandates human gateway signoff."""
        if not approval_token or not authorizer_principal_id:
            raise ValueError("Rule 62 Violation: Awarding procurement contract requires human gateway authorization")

        quote_exists = any(q.quote_id == selected_quote_id for q in rfq.quotes)
        if not quote_exists:
            raise KeyError(f"Quote {selected_quote_id} not present in RFQ {rfq.rfq_id}")

        rfq.awarded_quote_id = selected_quote_id
        rfq.gateway_approved = True
        rfq.award_approval_token = approval_token
        rfq.status = "awarded"
        return rfq
