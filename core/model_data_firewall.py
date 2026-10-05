"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 10 — Model Data Loss Prevention (DLP) Firewall
Inspects, sanitizes, and evaluates outbound prompts before transmission to external AI providers.
Prevents credential exfiltration, secret leakage, and unredacted PII exposure.

Constitutional Invariants:
  MODEL != AUTHORITY
  MODEL != POLICY
  NEVER_SEND_ENTERPRISE_DATA_UNLESS_POLICY_EXPLICITLY_PERMITS
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.data_classification_engine import classification_engine, DataClassificationLevel, SensitivityCategory

logger = logging.getLogger("zonata.model.firewall")

# Comprehensive redaction patterns
REDACTION_RULES = [
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "[REDACTED_SSN]"),
    (re.compile(r'\b(?:\d{4}-){3}\d{4}\b'), "[REDACTED_CREDIT_CARD]"),
    (re.compile(r'(?i)(?:api[_-]?key|secret[_-]?token|bearer\s+)[a-z0-9_\-\.]{16,}'), "[REDACTED_CREDENTIAL]"),
    (re.compile(r'(?i)-----BEGIN[A-Z\s]+PRIVATE KEY-----.*?-----END[A-Z\s]+PRIVATE KEY-----', re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'), "[REDACTED_EMAIL]")
]

@dataclass
class FirewallInspectionResult:
    is_allowed: bool
    sanitized_prompt: str
    detected_classification: str
    detected_sensitivities: List[str]
    redaction_count: int
    blocking_reason: Optional[str] = None

class ModelDataFirewall:
    """
    Data Loss Prevention barrier sitting strictly between ZONATA AI Employees and LLM Providers.
    """
    # Strict cloud transmission policy: HIGHLY_RESTRICTED data is NEVER transmitted to external models
    PROHIBITED_CLOUD_LEVELS = {DataClassificationLevel.HIGHLY_RESTRICTED}

    def inspect_and_filter(
        self,
        raw_prompt: str,
        tenant_id: str,
        provider_name: str,
        is_sovereign_local_model: bool = False,
        allow_pii_redaction: bool = True
    ) -> FirewallInspectionResult:
        """
        Inspect prompt text, classify sensitivity, apply redaction, and enforce transmission boundaries.
        """
        # 1. Classify content
        eff_level, categories, reasons = classification_engine.classify_content(raw_prompt)

        # 2. Enforce Sovereign Policy: If data is HIGHLY_RESTRICTED and model is 3rd-party cloud -> BLOCK
        if eff_level in self.PROHIBITED_CLOUD_LEVELS and not is_sovereign_local_model:
            logger.error(f"[DLP BLOCKED] Prompt contains {eff_level} data; transmission to external provider '{provider_name}' forbidden.")
            return FirewallInspectionResult(
                is_allowed=False,
                sanitized_prompt="",
                detected_classification=eff_level,
                detected_sensitivities=categories,
                redaction_count=0,
                blocking_reason=f"Classification '{eff_level}' strictly prohibited from external cloud provider '{provider_name}'."
            )

        # 3. Apply DLP redaction if permitted
        sanitized = raw_prompt
        redactions = 0
        if allow_pii_redaction:
            for pattern, replacement in REDACTION_RULES:
                matches = pattern.findall(sanitized)
                if matches:
                    redactions += len(matches)
                    sanitized = pattern.sub(replacement, sanitized)

        return FirewallInspectionResult(
            is_allowed=True,
            sanitized_prompt=sanitized,
            detected_classification=eff_level,
            detected_sensitivities=categories,
            redaction_count=redactions,
            blocking_reason=None
        )

    def inspect_and_sanitize(
        self,
        raw_prompt: str,
        tenant_id: str = "tnt_primary",
        is_local: bool = False
    ) -> FirewallInspectionResult:
        """Convenience wrapper for inspecting and sanitizing prompt text."""
        return self.inspect_and_filter(
            raw_prompt=raw_prompt,
            tenant_id=tenant_id,
            provider_name="MODEL_FIREWALL",
            is_sovereign_local_model=is_local,
            allow_pii_redaction=True
        )

# Global singleton
model_data_firewall = ModelDataFirewall()
