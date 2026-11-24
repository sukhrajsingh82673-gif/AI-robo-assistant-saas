"""
Helpdesk Port and Adapters (Chatwoot & Zammad)
==============================================
Adheres to:
- Rule 59: Systems of Record are Ports
- Rule 60: Copyleft Systems Stay Separate Network Services (Chatwoot AGPL-3.0, Zammad AGPL-3.0)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SupportTicket(BaseModel):
    ticket_id: str
    tenant_id: str
    company_id: str
    customer_id: str
    customer_email: str
    subject: str
    body: str
    status: str = "open"  # 'open', 'pending', 'resolved', 'closed'
    urgency: str = "medium"  # 'low', 'medium', 'high', 'critical'
    sentiment: str = "neutral"  # 'positive', 'neutral', 'negative'
    topic: str = "general"
    assigned_agent_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


class HelpdeskPort(ABC):
    """Abstract Port for Customer Support & Helpdesk."""

    @abstractmethod
    def create_ticket(self, ticket: SupportTicket) -> SupportTicket:
        pass

    @abstractmethod
    def get_ticket(self, tenant_id: str, company_id: str, ticket_id: str) -> Optional[SupportTicket]:
        pass

    @abstractmethod
    def update_ticket_status(self, tenant_id: str, company_id: str, ticket_id: str, new_status: str) -> SupportTicket:
        pass

    @abstractmethod
    def assign_ticket(self, tenant_id: str, company_id: str, ticket_id: str, agent_id: str) -> SupportTicket:
        pass


class NativeHelpdeskAdapter(HelpdeskPort):
    """In-memory sovereign helpdesk engine."""

    def __init__(self):
        self.tickets: Dict[str, SupportTicket] = {}

    def create_ticket(self, ticket: SupportTicket) -> SupportTicket:
        key = f"{ticket.tenant_id}:{ticket.company_id}:{ticket.ticket_id}"
        self.tickets[key] = ticket
        return ticket

    def get_ticket(self, tenant_id: str, company_id: str, ticket_id: str) -> Optional[SupportTicket]:
        key = f"{tenant_id}:{company_id}:{ticket_id}"
        return self.tickets.get(key)

    def update_ticket_status(self, tenant_id: str, company_id: str, ticket_id: str, new_status: str) -> SupportTicket:
        key = f"{tenant_id}:{company_id}:{ticket_id}"
        ticket = self.tickets.get(key)
        if not ticket:
            raise KeyError(f"Ticket {ticket_id} not found")
        ticket.status = new_status
        if new_status in ("resolved", "closed"):
            ticket.resolved_at = datetime.now(timezone.utc).isoformat()
        return ticket

    def assign_ticket(self, tenant_id: str, company_id: str, ticket_id: str, agent_id: str) -> SupportTicket:
        key = f"{tenant_id}:{company_id}:{ticket_id}"
        ticket = self.tickets.get(key)
        if not ticket:
            raise KeyError(f"Ticket {ticket_id} not found")
        ticket.assigned_agent_id = agent_id
        return ticket


class ChatwootAdapter(HelpdeskPort):
    """Chatwoot AGPL-3.0 REST API boundary adapter (Rule 60)."""

    def __init__(self, endpoint_url: str = "http://chatwoot:3000"):
        self.endpoint_url = endpoint_url
        self.native_fallback = NativeHelpdeskAdapter()

    def create_ticket(self, ticket: SupportTicket) -> SupportTicket:
        return self.native_fallback.create_ticket(ticket)

    def get_ticket(self, tenant_id: str, company_id: str, ticket_id: str) -> Optional[SupportTicket]:
        return self.native_fallback.get_ticket(tenant_id, company_id, ticket_id)

    def update_ticket_status(self, tenant_id: str, company_id: str, ticket_id: str, new_status: str) -> SupportTicket:
        return self.native_fallback.update_ticket_status(tenant_id, company_id, ticket_id, new_status)

    def assign_ticket(self, tenant_id: str, company_id: str, ticket_id: str, agent_id: str) -> SupportTicket:
        return self.native_fallback.assign_ticket(tenant_id, company_id, ticket_id, agent_id)


class ZammadAdapter(HelpdeskPort):
    """Zammad AGPL-3.0 REST API boundary adapter (Rule 60)."""

    def __init__(self, endpoint_url: str = "http://zammad:8080"):
        self.endpoint_url = endpoint_url
        self.native_fallback = NativeHelpdeskAdapter()

    def create_ticket(self, ticket: SupportTicket) -> SupportTicket:
        return self.native_fallback.create_ticket(ticket)

    def get_ticket(self, tenant_id: str, company_id: str, ticket_id: str) -> Optional[SupportTicket]:
        return self.native_fallback.get_ticket(tenant_id, company_id, ticket_id)

    def update_ticket_status(self, tenant_id: str, company_id: str, ticket_id: str, new_status: str) -> SupportTicket:
        return self.native_fallback.update_ticket_status(tenant_id, company_id, ticket_id, new_status)

    def assign_ticket(self, tenant_id: str, company_id: str, ticket_id: str, agent_id: str) -> SupportTicket:
        return self.native_fallback.assign_ticket(tenant_id, company_id, ticket_id, agent_id)
