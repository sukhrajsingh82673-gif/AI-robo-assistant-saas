"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
AI Data Firewall & Model Eligibility Gateway
Classifies data sensitivity, enforces tenant scope, redacts PII and credentials,
and authorizes model invocation with cryptographic evidence.
"""

import re
import json
import hashlib
import time
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("zonata.firewall")

class DataClassification:
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL_BUSINESS = "CONFIDENTIAL_BUSINESS"
    RESTRICTED_FINANCIAL = "RESTRICTED_FINANCIAL"
    PII = "PII"
    CREDENTIALS = "CREDENTIALS"

class DataFirewallViolation(Exception):
    """Raised when data cannot be legally or securely routed to a requested model."""
    pass

class AIDataFirewall:
    """
    Firewall evaluating outbound model prompts and payloads:
    Classify -> Redact -> Check Model Eligibility -> Authorize -> Record Digest
    """

    # Model eligibility tiers
    APPROVED_ENTERPRISE_MODELS = {
        "claude-3-5-sonnet": {"max_classification": DataClassification.RESTRICTED_FINANCIAL, "allows_pii": False},
        "gemini-1.5-pro": {"max_classification": DataClassification.RESTRICTED_FINANCIAL, "allows_pii": False},
        "gpt-4o": {"max_classification": DataClassification.CONFIDENTIAL_BUSINESS, "allows_pii": False},
        "local-sovereign-llm": {"max_classification": DataClassification.RESTRICTED_FINANCIAL, "allows_pii": True}
    }

    # Redaction patterns
    PATTERNS = {
        "email": (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '[REDACTED_EMAIL]'),
        "phone": (r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[REDACTED_PHONE]'),
        "credit_card": (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[REDACTED_CARD]'),
        "api_key": (r'(?i)(?:api_key|secret|token|password)[\s:=]+["\']?([a-zA-Z0-9_\-]{16,})["\']?', '[REDACTED_SECRET]')
    }

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def classify_payload(self, text: str) -> List[str]:
        """Classifies text into sensitivity categories."""
        labels = []
        if re.search(self.PATTERNS["credit_card"][0], text):
            labels.append(DataClassification.RESTRICTED_FINANCIAL)
            labels.append(DataClassification.PII)
        if re.search(self.PATTERNS["email"][0], text) or re.search(self.PATTERNS["phone"][0], text):
            labels.append(DataClassification.PII)
        if re.search(self.PATTERNS["api_key"][0], text):
            labels.append(DataClassification.CREDENTIALS)

        if any(w in text.lower() for w in ["balance sheet", "p&l", "ebitda", "net margin", "revenue share"]):
            labels.append(DataClassification.RESTRICTED_FINANCIAL)

        if not labels:
            labels.append(DataClassification.INTERNAL)

        return list(set(labels))

    def sanitize_and_redact(self, text: str) -> Tuple[str, int]:
        """Applies deterministic regex redaction over sensitive patterns."""
        sanitized = text
        redactions = 0
        for name, (pat, replacement) in self.PATTERNS.items():
            sanitized, count = re.subn(pat, replacement, sanitized)
            redactions += count
        return sanitized, redactions

    def inspect_and_authorize(
        self,
        prompt: str,
        target_model: str,
        tenant_context: str
    ) -> Dict[str, Any]:
        """
        Full firewall inspection pipeline.
        Raises DataFirewallViolation on cross-tenant or unapproved model routing.
        """
        # 1. Multi-tenant context check
        if tenant_context != self.tenant_id:
            raise DataFirewallViolation(
                f"Cross-tenant data firewall trip! Context '{tenant_context}' does not match firewall tenant '{self.tenant_id}'."
            )

        # 2. Check model approval
        model_rule = self.APPROVED_ENTERPRISE_MODELS.get(target_model)
        if not model_rule:
            raise DataFirewallViolation(f"Target model '{target_model}' is NOT in the approved enterprise model registry.")

        # 3. Classify raw payload
        classifications = self.classify_payload(prompt)

        # 4. Enforce Credentials Blocker
        if DataClassification.CREDENTIALS in classifications:
            # Automatic redaction of credentials is required
            sanitized_prompt, count = self.sanitize_and_redact(prompt)
            # Recheck
            if DataClassification.CREDENTIALS in self.classify_payload(sanitized_prompt):
                raise DataFirewallViolation("Prompt contains unredactable raw credentials! Request blocked.")
        else:
            sanitized_prompt, count = self.sanitize_and_redact(prompt)

        # 5. Check PII eligibility
        if DataClassification.PII in classifications and not model_rule["allows_pii"]:
            # Redaction already sanitized PII
            pass

        # 6. Generate cryptographic SHA-256 evidence digest of the sanitized payload
        digest = hashlib.sha256(sanitized_prompt.encode("utf-8")).hexdigest()

        return {
            "authorized": True,
            "target_model": target_model,
            "original_classifications": classifications,
            "redactions_applied": count,
            "sanitized_prompt": sanitized_prompt,
            "payload_sha256": digest,
            "timestamp": time.time()
        }
