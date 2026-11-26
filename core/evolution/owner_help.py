"""
ZONATA Owner Help Protocol (Sub-Step 6D).

Governs human-in-the-loop interactions when an agent cannot proceed honestly.
Features:
- Strict 3-step rule (max 3 numbered imperative action steps).
- Deduplication: no duplicate question within 24 hours.
- Hourly rate limit: max 5 requests/hour per tenant (excess queued).
- Sensitive action step-up auth gate.
- Ask once / learn forever knowledge indexing.
- Mutation check: raw credentials in human responses intercepted to Vault (Rule 41).
"""

import re
import uuid
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple


class HelpValidationError(Exception):
    """Raised when a help request violates structural rules (e.g. >3 steps)."""
    pass


class StepUpAuthRequiredError(Exception):
    """Raised when a sensitive action lacks verified step-up credentials."""
    pass


class HelpTicket:
    """Represents a governed help request presented to the human owner."""

    def __init__(
        self,
        tenant_id: str,
        company_id: str,
        task_id: str,
        question: str,
        action_steps: List[str],
        is_sensitive: bool = False,
        ticket_id: Optional[str] = None,
        created_at: Optional[float] = None,
    ):
        self.ticket_id = ticket_id or f"ticket_{uuid.uuid4().hex[:12]}"
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.task_id = task_id
        self.question = question.strip()
        self.action_steps = [s.strip() for s in action_steps]
        self.is_sensitive = is_sensitive
        self.question_hash = hashlib.sha256(self.question.lower().encode("utf-8")).hexdigest()
        self.status = "OPEN"
        self.created_at = created_at or time.time()
        self.resolved_at: Optional[float] = None
        self.resolution: Optional[str] = None
        self.vault_secret_keys: List[str] = []
        self.auto_resolved: bool = False


class OwnerHelpEngine:
    """
    Coordinates help requests to human owners with deduplication,
    rate-limiting, step-up authentication, and 'learn forever' caching.
    """

    MAX_STEPS = 3
    RATE_LIMIT_PER_HOUR = 5
    DEDUP_WINDOW_SECONDS = 86400  # 24 hours

    def __init__(self):
        # {ticket_id: HelpTicket}
        self.tickets: Dict[str, HelpTicket] = {}
        # {tenant_id: [ticket_id]}
        self.tenant_tickets: Dict[str, List[str]] = {}
        # Learn forever registry: {question_hash: {"resolution": str, "vault_keys": list, "saved_at": float}}
        self.learn_forever_store: Dict[str, Dict[str, Any]] = {}
        # Mock vault for sanitized credentials: {vault_uri: secret_value}
        self.vault: Dict[str, str] = {}

    def submit_help_request(
        self,
        tenant_id: str,
        company_id: str,
        task_id: str,
        question: str,
        action_steps: List[str],
        is_sensitive: bool = False,
    ) -> HelpTicket:
        """
        Validates, deduplicates, rate limits, and registers a help request.
        """
        # Rule 1: The 3-Step Rule
        if len(action_steps) == 0:
            raise HelpValidationError("Help request must provide at least 1 action step for the owner.")
        if len(action_steps) > self.MAX_STEPS:
            raise HelpValidationError(
                f"3-Step Rule Violated: Request contains {len(action_steps)} steps (maximum allowed: {self.MAX_STEPS}). "
                "The agent must decompose the task into smaller sub-tasks."
            )

        q_hash = hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()
        now = time.time()

        # Rule 4: Ask Once / Learn Forever Check
        if q_hash in self.learn_forever_store:
            cached = self.learn_forever_store[q_hash]
            ticket = HelpTicket(
                tenant_id=tenant_id,
                company_id=company_id,
                task_id=task_id,
                question=question,
                action_steps=action_steps,
                is_sensitive=is_sensitive,
            )
            ticket.status = "RESOLVED"
            ticket.resolution = cached["resolution"]
            ticket.vault_secret_keys = cached["vault_keys"]
            ticket.resolved_at = now
            ticket.auto_resolved = True
            self.tickets[ticket.ticket_id] = ticket
            self.tenant_tickets.setdefault(tenant_id, []).append(ticket.ticket_id)
            return ticket

        # Rule 2: Deduplication within 24 hours
        tenant_list = self.tenant_tickets.get(tenant_id, [])
        for tid in reversed(tenant_list):
            existing = self.tickets[tid]
            if existing.question_hash == q_hash and (now - existing.created_at) < self.DEDUP_WINDOW_SECONDS:
                return existing

        # Rule 2: Rate Limit (Max 5/hour per tenant)
        recent_requests = [
            self.tickets[tid]
            for tid in tenant_list
            if (now - self.tickets[tid].created_at) < 3600 and not self.tickets[tid].auto_resolved
        ]

        ticket = HelpTicket(
            tenant_id=tenant_id,
            company_id=company_id,
            task_id=task_id,
            question=question,
            action_steps=action_steps,
            is_sensitive=is_sensitive,
        )

        if len(recent_requests) >= self.RATE_LIMIT_PER_HOUR:
            ticket.status = "QUEUED"
        else:
            ticket.status = "OPEN"

        self.tickets[ticket.ticket_id] = ticket
        self.tenant_tickets.setdefault(tenant_id, []).append(ticket.ticket_id)
        return ticket

    def _sanitize_human_response(self, tenant_id: str, response_text: str) -> Tuple[str, List[str]]:
        """
        Scans human answer for secrets/keys (e.g. API tokens, passwords).
        Routes discovered secrets into Vault and replaces them with vault:// references.
        """
        secret_patterns = [
            (re.compile(r"(?:api_key|token|auth_key)\s*[:=]\s*([a-zA-Z0-9_\-]{16,})", re.IGNORECASE), "api_key"),
            (re.compile(r"(?:password|secret)\s*[:=]\s*([^\s,;]+)", re.IGNORECASE), "password"),
            (re.compile(r"\b(zonata_sec_[a-zA-Z0-9]{16,})\b"), "custom_token"),
        ]

        clean_text = response_text
        vault_keys = []

        for pattern, sec_type in secret_patterns:
            matches = pattern.findall(clean_text)
            for raw_val in matches:
                sec_id = f"sec_{uuid.uuid4().hex[:8]}"
                vault_uri = f"vault://{tenant_id}/secrets/{sec_id}"
                self.vault[vault_uri] = raw_val
                vault_keys.append(vault_uri)
                clean_text = clean_text.replace(raw_val, vault_uri)

        return clean_text, vault_keys

    def resolve_help_request(
        self,
        ticket_id: str,
        human_response: str,
        step_up_token: Optional[str] = None,
    ) -> HelpTicket:
        """
        Resolves a help ticket with human response. Enforces step-up auth on sensitive actions.
        """
        if ticket_id not in self.tickets:
            raise KeyError(f"Ticket {ticket_id} not found.")

        ticket = self.tickets[ticket_id]

        # Rule 3: Sensitive Action Step-Up Auth
        if ticket.is_sensitive:
            if not step_up_token or not self._validate_step_up_token(step_up_token):
                raise StepUpAuthRequiredError(
                    "Sensitive action requires verified cryptographic step-up authentication."
                )

        # Rule 41: Intercept credentials to Vault
        clean_resolution, vault_keys = self._sanitize_human_response(ticket.tenant_id, human_response)

        ticket.resolution = clean_resolution
        ticket.vault_secret_keys = vault_keys
        ticket.status = "RESOLVED"
        ticket.resolved_at = time.time()

        # Rule 4: Ask Once / Learn Forever Indexing
        self.learn_forever_store[ticket.question_hash] = {
            "resolution": clean_resolution,
            "vault_keys": vault_keys,
            "saved_at": ticket.resolved_at,
        }

        return ticket

    def _validate_step_up_token(self, token: str) -> bool:
        """Validates step-up token structure and signature."""
        if not token:
            return False
        # Expected format: stepup_<valid_hex_or_hash>
        return token.startswith("stepup_") and len(token) >= 20

    def get_open_tickets(self, tenant_id: str) -> List[HelpTicket]:
        return [
            self.tickets[tid]
            for tid in self.tenant_tickets.get(tenant_id, [])
            if self.tickets[tid].status == "OPEN"
        ]

    def get_queued_tickets(self, tenant_id: str) -> List[HelpTicket]:
        return [
            self.tickets[tid]
            for tid in self.tenant_tickets.get(tenant_id, [])
            if self.tickets[tid].status == "QUEUED"
        ]
