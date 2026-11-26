"""
Lead Capture and Deduplication Engine
=====================================
Deduplicates incoming leads by normalized email, phone number, and company domain.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import re
from pydantic import BaseModel, Field


class Lead(BaseModel):
    lead_id: str
    tenant_id: str
    company_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    source: str = "web_form"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    enrichment_data: Dict[str, Any] = Field(default_factory=dict)


class LeadEngine:
    """Manages lead storage, normalization, and deduplication across multiple keys."""

    def __init__(self):
        self.leads: Dict[str, Lead] = {}
        self.email_index: Dict[str, str] = {}
        self.phone_index: Dict[str, str] = {}
        self.domain_index: Dict[str, List[str]] = {}

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.lower().strip()

    @staticmethod
    def normalize_phone(phone: Optional[str]) -> Optional[str]:
        if not phone:
            return None
        # Keep digits and leading plus
        cleaned = re.sub(r"[^\d+]", "", phone.strip())
        return cleaned

    @staticmethod
    def extract_domain(email: str) -> Optional[str]:
        parts = email.split("@")
        if len(parts) == 2:
            domain = parts[1].lower().strip()
            # Ignore generic consumer domains for B2B domain matching
            if domain not in ("gmail.com", "yahoo.com", "hotmail.com", "outlook.com"):
                return domain
        return None

    def capture_lead(self, lead: Lead) -> Tuple[Lead, bool, Optional[str]]:
        """Captures lead or detects duplicate. Returns (lead, is_duplicate, original_lead_id)."""
        norm_email = self.normalize_email(lead.email)
        norm_phone = self.normalize_phone(lead.phone)
        domain = lead.domain or self.extract_domain(lead.email)
        lead.domain = domain

        # 1. Email check
        if norm_email in self.email_index:
            orig_id = self.email_index[norm_email]
            return self.leads[orig_id], True, f"Duplicate email: {norm_email}"

        # 2. Phone check
        if norm_phone and norm_phone in self.phone_index:
            orig_id = self.phone_index[norm_phone]
            return self.leads[orig_id], True, f"Duplicate phone: {norm_phone}"

        # Store new lead
        self.leads[lead.lead_id] = lead
        self.email_index[norm_email] = lead.lead_id
        if norm_phone:
            self.phone_index[norm_phone] = lead.lead_id
        if domain:
            self.domain_index.setdefault(domain, []).append(lead.lead_id)

        return lead, False, None
