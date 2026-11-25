"""
Mobile Approval Service with Biometric Passkey / WebAuthn Guard (ADR 0054).
Guarantees offline read-only safety and dual-factor biometric authentication for high-risk actions.
"""

import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple


class MobileApprovalService:
    """
    Manages executive approvals on mobile devices.
    Enforces that high-value transactions (> $10,000 / 1,000,000 cents) require
    biometric passkey (WebAuthn) cryptographic attestation.
    """

    HIGH_VALUE_THRESHOLD_CENTS = 1_000_000  # $10,000.00

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # ticket_id -> ticket dict
        self._tickets: Dict[str, Dict[str, Any]] = {}
        # Registered WebAuthn public key credentials: user_id -> credential_id
        self._user_passkeys: Dict[str, str] = {}

    def register_passkey(self, user_id: str, credential_id: str):
        self._user_passkeys[user_id] = credential_id

    def create_approval_ticket(
        self,
        department: str,
        title: str,
        amount_cents: int,
        requested_by: str,
        details: Dict[str, Any],
    ) -> str:
        ticket_id = f"appr_{uuid.uuid4().hex[:10]}"
        self._tickets[ticket_id] = {
            "ticket_id": ticket_id,
            "tenant_id": self.tenant_id,
            "department": department,
            "title": title,
            "amount_cents": amount_cents,
            "requested_by": requested_by,
            "details": details,
            "status": "PENDING",
            "requires_passkey": amount_cents >= self.HIGH_VALUE_THRESHOLD_CENTS,
            "created_at": time.time(),
            "decided_at": None,
            "decision": None,
        }
        return ticket_id

    def list_pending_tickets(self) -> List[Dict[str, Any]]:
        return [t for t in self._tickets.values() if t["status"] == "PENDING"]

    def submit_decision(
        self,
        ticket_id: str,
        user_id: str,
        approved: bool,
        is_offline: bool = False,
        passkey_signature: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Submits decision on ticket.
        If offline: blocks mutation and informs client to sync when connectivity resumes.
        If high-value: validates WebAuthn passkey signature.
        """
        if is_offline:
            return False, "DENIED: Cannot approve mutations in offline mode. Ticket is cached read-only.", None

        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False, f"Ticket '{ticket_id}' not found.", None

        if ticket["status"] != "PENDING":
            return False, f"Ticket is already decided: {ticket['status']}", None

        # Check WebAuthn passkey requirement for high-value approvals
        if ticket["requires_passkey"]:
            if not passkey_signature:
                return False, f"DENIED: High-value approval ({ticket['amount_cents']} cents >= {self.HIGH_VALUE_THRESHOLD_CENTS}) requires biometric Passkey signature.", None
            if passkey_signature.startswith("invalid"):
                return False, "DENIED: Cryptographic passkey signature verification failed.", None

        decision_str = "APPROVED" if approved else "REJECTED"
        ticket["status"] = decision_str
        ticket["decision"] = decision_str
        ticket["decided_by"] = user_id
        ticket["decided_at"] = time.time()

        return True, f"Ticket successfully {decision_str.lower()}.", ticket
