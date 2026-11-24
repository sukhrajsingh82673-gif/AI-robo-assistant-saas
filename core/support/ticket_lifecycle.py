"""
Ticket Lifecycle Engine: Classification, Routing, and Governed Auto-Response
===========================================================================
Adheres to:
- Rule 62: Reserved Human Decisions (high-risk ticket responses require human gateway approval)
"""

from typing import Dict, List, Optional, Tuple, Any
from core.support.helpdesk_port import SupportTicket


class ResponseProposal:
    def __init__(self, ticket_id: str, proposed_body: str, confidence: float, human_approval_required: bool):
        self.ticket_id = ticket_id
        self.proposed_body = proposed_body
        self.confidence = confidence
        self.human_approval_required = human_approval_required
        self.is_dispatched = False


class TicketClassifier:
    """Classifies incoming tickets for Urgency, Sentiment, and Topic."""

    @staticmethod
    def classify(ticket: SupportTicket) -> SupportTicket:
        content = (ticket.subject + " " + ticket.body).lower()

        # Urgency
        if any(w in content for w in ["outage", "system down", "critical", "emergency", "data loss", "breach"]):
            ticket.urgency = "critical"
        elif any(w in content for w in ["urgent", "asap", "error 500", "blocked"]):
            ticket.urgency = "high"
        elif any(w in content for w in ["slow", "minor", "typo", "question"]):
            ticket.urgency = "low"
        else:
            ticket.urgency = "medium"

        # Sentiment
        if any(w in content for w in ["furious", "terrible", "horrible", "unacceptable", "lawsuit", "cancel", "data loss", "broken", "frustrated", "angry"]):
            ticket.sentiment = "negative"
        elif any(w in content for w in ["thank you", "great", "excellent", "appreciate"]):
            ticket.sentiment = "positive"
        else:
            ticket.sentiment = "neutral"

        # Topic
        if any(w in content for w in ["invoice", "charge", "refund", "billing", "payment", "card"]):
            ticket.topic = "billing"
        elif any(w in content for w in ["vulnerability", "security", "password", "2fa", "exploit"]):
            ticket.topic = "security"
        elif any(w in content for w in ["bug", "api", "crash", "stack trace", "exception", "server", "outage", "down"]):
            ticket.topic = "technical"
        else:
            ticket.topic = "general"

        return ticket


class TicketRouter:
    """Routes tickets to agents based on skills and capacity."""

    def __init__(self, agent_skills: Dict[str, List[str]], agent_capacity: Dict[str, int]):
        self.agent_skills = agent_skills  # e.g. {"agent_1": ["billing", "general"], "agent_2": ["security", "technical"]}
        self.agent_capacity = agent_capacity  # max concurrent tickets

    def route_ticket(self, ticket: SupportTicket, current_agent_workload: Dict[str, int]) -> Optional[str]:
        best_agent = None
        min_load = 999999

        for agent, skills in self.agent_skills.items():
            if ticket.topic in skills or "general" in skills:
                max_cap = self.agent_capacity.get(agent, 5)
                load = current_agent_workload.get(agent, 0)
                if load < max_cap and load < min_load:
                    min_load = load
                    best_agent = agent

        if best_agent:
            ticket.assigned_agent_id = best_agent
        return best_agent


class GovernedAutoResponder:
    """Generates draft responses with human-approval gates for high-risk topics."""

    @staticmethod
    def generate_response(ticket: SupportTicket) -> ResponseProposal:
        # High risk topics (security, refund/billing, or critical urgency) mandate human review
        requires_approval = (
            ticket.urgency in ("critical", "high") or
            ticket.topic in ("security", "billing") or
            ticket.sentiment == "negative"
        )

        draft = f"Hello, thank you for contacting ZONATA support regarding '{ticket.subject}'. Our team is reviewing this issue."
        return ResponseProposal(
            ticket_id=ticket.ticket_id,
            proposed_body=draft,
            confidence=0.92,
            human_approval_required=requires_approval
        )
