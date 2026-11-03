"""
ZONATA Real-Time Data Loss Prevention (DLP) Engine & Redaction Filter
"""
import re
import hashlib
from typing import Dict, Any, List, Tuple
from core.security_classification import InformationClassification, CLASSIFICATION_LEVELS

class DLPViolationBlockedError(PermissionError):
    """Raised when content of CONFIDENTIAL or higher sensitivity is targeted for external disclosure."""
    pass

class DataLossPreventionEngine:
    REDACTION_PATTERNS = [
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "[REDACTED_SSN]"),
        (re.compile(r'\b(?:\d{4}-){3}\d{4}\b|\b(?:\d{4}\s){3}\d{4}\b'), "[REDACTED_CARD]"),
        (re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b'), "[REDACTED_IBAN]"),
        (re.compile(r'(?i)(?:api[_-]?key|secret[_-]?token|bearer\s+[a-z0-9_\-\.]{20,})'), "[REDACTED_SECRET]"),
        (re.compile(r'(?i)\bZONATA_CANARY_[A-Za-z0-9_]{6,}\b'), "[REDACTED_CANARY]"),
        (re.compile(r'(?i)(?:salary\s*[:=]\s*\$?\d{4,9}|compensation\s*[:=]\s*\$?\d{4,9})'), "[REDACTED_SALARY]"),
        (re.compile(r'(?i)(?:revenue\s*[:=]\s*\$?\d{4,12}|ebitda\s*[:=]\s*\$?\d{4,12})'), "[REDACTED_FINANCIAL]")
    ]

    @classmethod
    def inspect_and_filter(
        cls,
        text: str,
        destination_classification: str = InformationClassification.CUSTOMER_SHAREABLE.value,
        source_classification: str = InformationClassification.INTERNAL.value
    ) -> Dict[str, Any]:
        """
        Real-time DLP interceptor.
        1. Redacts PII, financial credentials, and canary tokens.
        2. Blocks customer disclosure if source or detected content is CONFIDENTIAL or higher.
        """
        dest_score = CLASSIFICATION_LEVELS.get(destination_classification, 2)
        source_score = CLASSIFICATION_LEVELS.get(source_classification, 3)

        # Gate Check: Prevent CONFIDENTIAL+ from flowing to CUSTOMER_SHAREABLE / PUBLIC
        if dest_score <= 2 and source_score >= 4:
            raise DLPViolationBlockedError(
                f"DLP_VIOLATION_BLOCKED: Content classified as '{source_classification}' cannot be disclosed to '{destination_classification}'."
            )

        sanitized = text
        redacted_count = 0
        matches_found = []

        for pattern, replacement in cls.REDACTION_PATTERNS:
            found = pattern.findall(sanitized)
            if found:
                matches_found.extend(found)
                sanitized = pattern.sub(replacement, sanitized)
                redacted_count += len(found)

        content_hash = hashlib.sha256(sanitized.encode()).hexdigest()
        is_clean = (redacted_count == 0)

        return {
            "status": "CLEAN" if is_clean else "REDACTED",
            "sanitized_content": sanitized,
            "redacted_item_count": redacted_count,
            "content_hash": content_hash,
            "is_customer_safe": dest_score <= 2 and source_score < 4
        }

dlp_engine = DataLossPreventionEngine()
