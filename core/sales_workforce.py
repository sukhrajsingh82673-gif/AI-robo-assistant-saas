"""
RoboAssistant Company OS 2.0 — AI Sales Workforce
Governs commercial lead qualification, intent classification, customer negotiation,
and quotation strictly bounded by pricing truth and discount ceilings.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
from .db import db

class SalesLeadStatus:
    NEW = "NEW"
    QUALIFIED = "QUALIFIED"
    NEGOTIATING = "NEGOTIATING"
    CONVERTED = "CONVERTED"
    LOST = "LOST"
    ESCALATED = "ESCALATED"

class AISalesWorkforce:
    DISCOUNT_CEILING_PERCENT = 10.0  # Max autonomous discount without CEO/Owner approval

    def __init__(self, tenant_id: str = "tnt_primary", company_id: Optional[str] = None):
        self.tenant_id = tenant_id
        self.company_id = company_id or "comp_primary"

    def ingest_lead(self, contact_name: str, channel: str, initial_inquiry: str) -> Dict[str, Any]:
        """
        Ingests and qualifies an incoming commercial lead.
        """
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        now = time.time()

        # Score intent and qualification
        inquiry_lower = initial_inquiry.lower()
        score = 0.5
        if any(w in inquiry_lower for w in ["quote", "price", "book", "buy", "purchase", "reserve"]):
            score = 0.85
        if any(w in inquiry_lower for w in ["urgent", "ready", "immediately"]):
            score = min(1.0, score + 0.1)

        status = SalesLeadStatus.QUALIFIED if score >= 0.7 else SalesLeadStatus.NEW

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sales_leads (
                    lead_id, tenant_id, company_id, contact_name, channel, intent,
                    qualification_score, status, assigned_agent_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'agt_sales_rep_01', ?)
                """,
                (lead_id, self.tenant_id, self.company_id, contact_name, channel, initial_inquiry, score, status, now)
            )
            conn.commit()

        return {
            "lead_id": lead_id,
            "contact_name": contact_name,
            "qualification_score": score,
            "status": status,
            "channel": channel
        }

    def process_customer_message(self, lead_id: str, message: str, agent_id: str = "agt_sales_rep_01") -> Dict[str, Any]:
        """
        Evaluates customer messages, handles objections, and strictly enforces commercial discount ceilings.
        Invariant: The sales agent cannot invent prices or exceed the discount ceiling.
        """
        with db.get_connection() as conn:
            lead = conn.execute("SELECT * FROM sales_leads WHERE lead_id = ?", (lead_id,)).fetchone()

        if not lead:
            return {"success": False, "error": f"Lead '{lead_id}' not found"}

        msg_lower = message.lower()
        requested_discount = 0.0

        # Check for discount inquiries
        if "discount" in msg_lower or "%" in msg_lower:
            for word in msg_lower.split():
                if word.endswith("%"):
                    try:
                        requested_discount = float(word.rstrip("%"))
                    except ValueError:
                        pass

        converted = False
        discount_offered = 0.0
        policy_checked = True

        if requested_discount > self.DISCOUNT_CEILING_PERCENT:
            # Exceeds agent discount authority! Must escalate to Owner / CEO
            response = (
                f"Thank you for your interest! While our standard approved incentive is up to {self.DISCOUNT_CEILING_PERCENT:.0f}%, "
                f"your request for {requested_discount:.0f}% requires executive approval. I have escalated this directly to our management."
            )
            status_update = SalesLeadStatus.ESCALATED
        elif requested_discount > 0:
            # Within autonomous authority (e.g. 5% or 10%)
            discount_offered = min(requested_discount, self.DISCOUNT_CEILING_PERCENT)
            response = (
                f"We are delighted to offer you a preferred direct booking discount of {discount_offered:.0f}%. "
                "I have prepared your verified booking reservation link."
            )
            status_update = SalesLeadStatus.NEGOTIATING
        elif any(w in msg_lower for w in ["confirm", "proceed", "pay", "book now"]):
            response = "Excellent! Your booking is confirmed. Handoff to secure payment gateway is initiated."
            status_update = SalesLeadStatus.CONVERTED
            converted = True
        else:
            response = "Thank you for reaching out. We have prime availability suited for your dates. Would you like a formal quotation?"
            status_update = SalesLeadStatus.QUALIFIED

        # Record interaction into SQLite
        interaction_id = f"sint_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sales_interactions (
                    interaction_id, lead_id, agent_id, channel, customer_message,
                    agent_response, discount_offered, policy_checked, converted, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    interaction_id, lead_id, agent_id, lead["channel"], message,
                    response, discount_offered, 1 if policy_checked else 0,
                    1 if converted else 0, time.time()
                )
            )
            conn.execute(
                "UPDATE sales_leads SET status = ? WHERE lead_id = ?",
                (status_update, lead_id)
            )
            conn.commit()

        return {
            "success": True,
            "interaction_id": interaction_id,
            "agent_response": response,
            "discount_offered": discount_offered,
            "policy_checked": policy_checked,
            "escalated": (status_update == SalesLeadStatus.ESCALATED),
            "lead_status": status_update,
            "converted": converted
        }

    def list_leads(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            if status:
                rows = conn.execute("SELECT * FROM sales_leads WHERE company_id = ? AND status = ?", (self.company_id, status)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM sales_leads WHERE company_id = ?", (self.company_id,)).fetchall()
            return [dict(r) for r in rows]
