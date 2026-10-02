"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 6 — Enterprise Data Classification Engine
Automatic and policy-driven data classification, sensitivity tagging,
and compliance policy evaluation.

Constitutional Invariant:
  AI_GENERATED_CLASSIFICATION_CANNOT_DOWNGRADE_ADMIN_POLICY
  DATA_CLASSIFICATION != PERMISSION
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger("zonata.data.classification")

class DataClassificationLevel:
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"

# Numeric severity order for comparison
CLASSIFICATION_ORDER = {
    DataClassificationLevel.PUBLIC: 1,
    DataClassificationLevel.INTERNAL: 2,
    DataClassificationLevel.CONFIDENTIAL: 3,
    DataClassificationLevel.RESTRICTED: 4,
    DataClassificationLevel.HIGHLY_RESTRICTED: 5
}

class SensitivityCategory:
    GENERAL = "GENERAL"
    FINANCIAL = "FINANCIAL"
    CUSTOMER_PII = "CUSTOMER_PII"
    EMPLOYEE_HR = "EMPLOYEE_HR"
    SECURITY_AUTH = "SECURITY_AUTH"
    LEGAL = "LEGAL"
    SOURCE_CODE = "SOURCE_CODE"
    STRATEGIC_IP = "STRATEGIC_IP"
    REGULATED_COMPLIANCE = "REGULATED_COMPLIANCE"

# Regex heuristic patterns for content detection
PII_PATTERNS = [
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), SensitivityCategory.CUSTOMER_PII, DataClassificationLevel.RESTRICTED, "SSN pattern detected"),
    (re.compile(r'\b(?:\d{4}-){3}\d{4}\b'), SensitivityCategory.FINANCIAL, DataClassificationLevel.RESTRICTED, "Credit card pattern detected"),
    (re.compile(r'(?i)(?:ebitda|gross\s+margin|revenue\s+forecast|financial\s+ledger|bank\s+account|routing\s+number)'), SensitivityCategory.FINANCIAL, DataClassificationLevel.CONFIDENTIAL, "Financial indicators detected"),
    (re.compile(r'(?i)(?:api[_-]?key|secret[_-]?token|bearer\s+[a-z0-9_\-\.]{20,})'), SensitivityCategory.SECURITY_AUTH, DataClassificationLevel.HIGHLY_RESTRICTED, "Credential/API key pattern detected"),
    (re.compile(r'(?i)(?:private\s+key|BEGIN\s+RSA\s+PRIVATE)'), SensitivityCategory.SECURITY_AUTH, DataClassificationLevel.HIGHLY_RESTRICTED, "Private key detected"),
    (re.compile(r'(?i)(?:salary|compensation|payroll|ssn|dob|date\s+of\s+birth)'), SensitivityCategory.EMPLOYEE_HR, DataClassificationLevel.CONFIDENTIAL, "HR/Payroll indicators detected"),
    (re.compile(r'(?i)(?:attorney-client|privileged\s+and\s+confidential|nda|settlement\s+agreement)'), SensitivityCategory.LEGAL, DataClassificationLevel.RESTRICTED, "Legal privilege indicators detected")
]

class DataClassificationEngine:
    """
    Evaluates corporate content against sensitivity patterns, admin policies, and DLP rules.
    """
    def classify_content(
        self,
        text_content: str,
        admin_policy_level: Optional[str] = None,
        source_system: Optional[str] = None
    ) -> Tuple[str, List[str], List[str]]:
        """
        Scan content and return (effective_level, sensitivity_categories, detection_reasons).
        Enforces that AI or heuristic scan CANNOT downgrade an explicit admin policy.
        """
        detected_categories = set()
        detected_reasons = []
        max_detected_score = CLASSIFICATION_ORDER[DataClassificationLevel.INTERNAL]

        # Scan heuristics
        for pattern, cat, level, reason in PII_PATTERNS:
            if pattern.search(text_content):
                detected_categories.add(cat)
                detected_reasons.append(reason)
                score = CLASSIFICATION_ORDER.get(level, 1)
                if score > max_detected_score:
                    max_detected_score = score

        # Map score back to level
        detected_level = DataClassificationLevel.INTERNAL
        for lvl, score in CLASSIFICATION_ORDER.items():
            if score == max_detected_score:
                detected_level = lvl
                break

        # System-specific sensitivity defaults
        if source_system in ("stripe", "pms_accounting", "payroll"):
            detected_categories.add(SensitivityCategory.FINANCIAL)
            if CLASSIFICATION_ORDER[detected_level] < CLASSIFICATION_ORDER[DataClassificationLevel.CONFIDENTIAL]:
                detected_level = DataClassificationLevel.CONFIDENTIAL

        # Policy Invariant: Admin policy level is enforced. If sensitive heuristics match higher, they upgrade it.
        effective_level = detected_level
        if admin_policy_level and admin_policy_level in CLASSIFICATION_ORDER:
            admin_score = CLASSIFICATION_ORDER[admin_policy_level]
            # If no sensitive PII/secrets matched, honor explicit admin policy (e.g. PUBLIC)
            if not detected_reasons or admin_score > CLASSIFICATION_ORDER[effective_level]:
                effective_level = admin_policy_level
                detected_reasons.append(f"Enforced admin policy: {admin_policy_level}")

        if not detected_categories:
            detected_categories.add(SensitivityCategory.GENERAL)

        return effective_level, list(detected_categories), detected_reasons

# Global singleton
classification_engine = DataClassificationEngine()
