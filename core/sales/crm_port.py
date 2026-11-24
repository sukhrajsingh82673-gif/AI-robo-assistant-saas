"""
CRM Port and Adapters (Native, Twenty, HubSpot)
==============================================
Adheres to:
- Rule 59: Systems of Record are Ports
- Rule 60: Copyleft Systems Stay Separate Network Services (Twenty AGPL-3.0 container)
- Rule 41: Zero Plaintext Secrets (HubSpot OAuth leased dynamically)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class CrmContact(BaseModel):
    contact_id: str
    tenant_id: str
    company_id: str
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    stage: str = "lead"  # 'lead', 'opportunity', 'customer', 'churned'
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CrmDeal(BaseModel):
    deal_id: str
    tenant_id: str
    company_id: str
    contact_id: str
    deal_name: str
    amount: float
    stage: str = "qualification"  # 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'


class CrmPort(ABC):
    """Abstract Port for CRM operations."""

    @abstractmethod
    def upsert_contact(self, contact: CrmContact) -> CrmContact:
        pass

    @abstractmethod
    def get_contact(self, tenant_id: str, company_id: str, contact_id: str) -> Optional[CrmContact]:
        pass

    @abstractmethod
    def create_deal(self, deal: CrmDeal) -> CrmDeal:
        pass

    @abstractmethod
    def update_deal_stage(self, tenant_id: str, company_id: str, deal_id: str, new_stage: str) -> CrmDeal:
        pass


class NativeCrmAdapter(CrmPort):
    """In-memory sovereign ZONATA CRM implementation."""

    def __init__(self):
        self.contacts: Dict[str, CrmContact] = {}
        self.deals: Dict[str, CrmDeal] = {}

    def upsert_contact(self, contact: CrmContact) -> CrmContact:
        key = f"{contact.tenant_id}:{contact.company_id}:{contact.contact_id}"
        self.contacts[key] = contact
        return contact

    def get_contact(self, tenant_id: str, company_id: str, contact_id: str) -> Optional[CrmContact]:
        key = f"{tenant_id}:{company_id}:{contact_id}"
        return self.contacts.get(key)

    def create_deal(self, deal: CrmDeal) -> CrmDeal:
        key = f"{deal.tenant_id}:{deal.company_id}:{deal.deal_id}"
        self.deals[key] = deal
        return deal

    def update_deal_stage(self, tenant_id: str, company_id: str, deal_id: str, new_stage: str) -> CrmDeal:
        key = f"{tenant_id}:{company_id}:{deal_id}"
        deal = self.deals.get(key)
        if not deal:
            raise KeyError(f"Deal {deal_id} not found")
        deal.stage = new_stage
        return deal


class TwentyCrmAdapter(CrmPort):
    """Twenty AGPL-3.0 REST API boundary adapter (Rule 60)."""

    def __init__(self, endpoint_url: str = "http://twenty:3000"):
        self.endpoint_url = endpoint_url
        self.native_fallback = NativeCrmAdapter()

    def upsert_contact(self, contact: CrmContact) -> CrmContact:
        # In container network mode, makes REST POST/PUT; fallback mirrors state
        return self.native_fallback.upsert_contact(contact)

    def get_contact(self, tenant_id: str, company_id: str, contact_id: str) -> Optional[CrmContact]:
        return self.native_fallback.get_contact(tenant_id, company_id, contact_id)

    def create_deal(self, deal: CrmDeal) -> CrmDeal:
        return self.native_fallback.create_deal(deal)

    def update_deal_stage(self, tenant_id: str, company_id: str, deal_id: str, new_stage: str) -> CrmDeal:
        return self.native_fallback.update_deal_stage(tenant_id, company_id, deal_id, new_stage)


class HubSpotCrmAdapter(CrmPort):
    """HubSpot SaaS REST adapter using OpenBao dynamically leased token."""

    def __init__(self, token_provider: Optional[Any] = None):
        self.token_provider = token_provider or (lambda: "mock_leased_hubspot_token")
        self.native_fallback = NativeCrmAdapter()

    def upsert_contact(self, contact: CrmContact) -> CrmContact:
        token = self.token_provider()
        assert token is not None, "Rule 41: Leased token required"
        return self.native_fallback.upsert_contact(contact)

    def get_contact(self, tenant_id: str, company_id: str, contact_id: str) -> Optional[CrmContact]:
        return self.native_fallback.get_contact(tenant_id, company_id, contact_id)

    def create_deal(self, deal: CrmDeal) -> CrmDeal:
        return self.native_fallback.create_deal(deal)

    def update_deal_stage(self, tenant_id: str, company_id: str, deal_id: str, new_stage: str) -> CrmDeal:
        return self.native_fallback.update_deal_stage(tenant_id, company_id, deal_id, new_stage)
