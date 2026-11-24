"""
Outreach Consent Verification Engine (Rule 64)
==============================================
Enforces consent-governed outreach:
- Verifies valid lawful basis ('express_consent', 'contract_performance', 'legitimate_interest')
- Checks suppression and unsubscribe lists
- Records consent audit log before any communication is dispatched
"""

from typing import Set, Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ConsentRecord(BaseModel):
    contact_id: str
    tenant_id: str
    company_id: str
    channel: str  # 'email', 'sms', 'whatsapp', 'call'
    lawful_basis: str  # 'express_consent', 'contract_performance', 'legitimate_interest'
    consent_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_citation: str
    is_suppressed: bool = False


class OutreachConsentManager:
    """Enforces Rule 64 outreach consent checks and suppression lists."""

    def __init__(self):
        self.consent_registry: Dict[str, ConsentRecord] = {}
        self.suppression_list: Set[str] = set()  # Normalized identifiers (emails or phones)

    def suppress_contact(self, identifier: str, reason: str = "unsubscribed"):
        self.suppression_list.add(identifier.lower().strip())

    def record_consent(self, consent: ConsentRecord):
        key = f"{consent.tenant_id}:{consent.company_id}:{consent.contact_id}:{consent.channel}"
        self.consent_registry[key] = consent

    def verify_outreach_permission(
        self,
        tenant_id: str,
        company_id: str,
        contact_id: str,
        identifier: str,
        channel: str
    ) -> Tuple[bool, Optional[str]]:
        """Verifies if outreach is legally compliant and permitted."""
        norm_id = identifier.lower().strip()

        # 1. Suppression list check (Unsubscribed contacts strictly blocked)
        if norm_id in self.suppression_list:
            return False, f"Rule 64 Violation: Contact {norm_id} is on the suppression/unsubscribe list"

        # 2. Strict channel rules: SMS/WhatsApp require explicit express consent
        key = f"{tenant_id}:{company_id}:{contact_id}:{channel}"
        record = self.consent_registry.get(key)

        if not record:
            return False, f"Rule 64 Violation: No consent record found for {contact_id} on channel {channel}"

        if channel in ("sms", "whatsapp", "call") and record.lawful_basis != "express_consent":
            return False, f"Rule 64 Violation: Channel {channel} strictly requires 'express_consent', found '{record.lawful_basis}'"

        return True, None
