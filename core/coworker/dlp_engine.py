"""
ZONATA Autonomous Executive Coworker — Milestone 3: Core DLP Engine
Detects secrets, PII, financial data, and high-entropy anomalies across 12 categories and 10 channels.
"""

from __future__ import annotations
import re
import math
import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


class DLPCategory(str, Enum):
    API_KEYS_AND_SECRETS = "API_KEYS_AND_SECRETS"
    PRIVATE_KEYS_CERTIFICATES = "PRIVATE_KEYS_CERTIFICATES"
    DATABASE_CREDENTIALS = "DATABASE_CREDENTIALS"
    PII_PERSONAL_DATA = "PII_PERSONAL_DATA"
    FINANCIAL_PAYMENT_DATA = "FINANCIAL_PAYMENT_DATA"
    HEALTH_MEDICAL_DATA = "HEALTH_MEDICAL_DATA"
    PROPRIETARY_SOURCE_CODE = "PROPRIETARY_SOURCE_CODE"
    INTERNAL_INFRASTRUCTURE = "INTERNAL_INFRASTRUCTURE"
    AUTH_TOKENS_JWT = "AUTH_TOKENS_JWT"
    CUSTOMER_CRM_RECORDS = "CUSTOMER_CRM_RECORDS"
    COMPLIANCE_RESTRICTED = "COMPLIANCE_RESTRICTED"
    HIGH_ENTROPY_SUSPICIOUS = "HIGH_ENTROPY_SUSPICIOUS"


class DLPChannel(str, Enum):
    TERMINAL_COMMAND = "TERMINAL_COMMAND"
    TERMINAL_OUTPUT = "TERMINAL_OUTPUT"
    API_REQUEST_PAYLOAD = "API_REQUEST_PAYLOAD"
    API_RESPONSE_PAYLOAD = "API_RESPONSE_PAYLOAD"
    FILE_WRITE = "FILE_WRITE"
    FILE_READ = "FILE_READ"
    SCREENSHOT_IMAGE = "SCREENSHOT_IMAGE"
    BROWSER_INPUT = "BROWSER_INPUT"
    LLM_PROMPT = "LLM_PROMPT"
    COMMUNICATION_BUS = "COMMUNICATION_BUS"


class DLPRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DLPFinding:
    finding_id: str
    category: DLPCategory
    channel: DLPChannel
    risk_level: DLPRiskLevel
    snippet_masked: str
    match_start: int
    match_end: int
    detection_rule: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class DLPScanResult:
    clean: bool
    findings: List[DLPFinding]
    sanitized_text: str
    highest_risk: DLPRiskLevel = DLPRiskLevel.LOW
    action_taken: str = "ALLOW"


class DLPEngine:
    """Enterprise Data Loss Prevention (DLP) Regex & Shannon Entropy Engine."""

    PATTERNS: List[Tuple[re.Pattern, DLPCategory, DLPRiskLevel, str]] = [
        # 1. API Keys & Secrets
        (re.compile(r'(?i)\b(sk-[a-zA-Z0-9_\-]{20,})\b'), DLPCategory.API_KEYS_AND_SECRETS, DLPRiskLevel.CRITICAL, "OpenAI / Claude Secret Key"),
        (re.compile(r'\b(AKIA[0-9A-Z]{16})\b'), DLPCategory.API_KEYS_AND_SECRETS, DLPRiskLevel.HIGH, "AWS Access Key ID"),
        (re.compile(r'\b(ghp_[a-zA-Z0-9]{36})\b'), DLPCategory.API_KEYS_AND_SECRETS, DLPRiskLevel.CRITICAL, "GitHub Token"),
        (re.compile(r'\b(stripe_[a-zA-Z0-9_]{20,})\b'), DLPCategory.API_KEYS_AND_SECRETS, DLPRiskLevel.CRITICAL, "Stripe Secret"),

        # 2. Private Keys
        (re.compile(r'-----BEGIN (?:RSA|OPENSSH|EC|PGP) PRIVATE KEY-----(?:[\s\S]+?-----END (?:RSA|OPENSSH|EC|PGP) PRIVATE KEY-----)?'),
         DLPCategory.PRIVATE_KEYS_CERTIFICATES, DLPRiskLevel.CRITICAL, "Private Cryptographic Key"),

        # 3. Database Credentials
        (re.compile(r'(?i)\b(postgres|postgresql|mysql|mongodb|redis)://[^:]+:([^@]+)@'),
         DLPCategory.DATABASE_CREDENTIALS, DLPRiskLevel.CRITICAL, "Database Connection String with Password"),

        # 4. PII Data (SSN)
        (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), DLPCategory.PII_PERSONAL_DATA, DLPRiskLevel.HIGH, "US Social Security Number"),

        # 5. Financial Data (Credit Card)
        (re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'),
         DLPCategory.FINANCIAL_PAYMENT_DATA, DLPRiskLevel.CRITICAL, "Credit Card Number"),

        # 6. Auth Tokens / JWT
        (re.compile(r'\beyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\b'),
         DLPCategory.AUTH_TOKENS_JWT, DLPRiskLevel.HIGH, "JSON Web Token (JWT)"),

        # 7. Internal Infrastructure
        (re.compile(r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'),
         DLPCategory.INTERNAL_INFRASTRUCTURE, DLPRiskLevel.LOW, "Internal RFC1918 IP Address"),
    ]

    def __init__(self, entropy_threshold: float = 4.2):
        self.entropy_threshold = entropy_threshold

    @staticmethod
    def calculate_entropy(text: str) -> float:
        if not text:
            return 0.0
        prob = [float(text.count(c)) / len(text) for c in dict.fromkeys(list(text))]
        return - sum([p * math.log(p) / math.log(2.0) for p in prob])

    def scan(self, text: str, channel: DLPChannel) -> DLPScanResult:
        if not text:
            return DLPScanResult(clean=True, findings=[], sanitized_text="")

        findings: List[DLPFinding] = []
        sanitized = text

        # 1. Regex Pattern Matching
        for pattern, category, risk, rule_name in self.PATTERNS:
            for match in pattern.finditer(text):
                raw_match = match.group(0)
                masked = raw_match[:2] + ("*" * (len(raw_match) - 4)) + raw_match[-2:] if len(raw_match) > 6 else "****"
                finding = DLPFinding(
                    finding_id=f"dlp_{uuid.uuid4().hex[:8]}",
                    category=category,
                    channel=channel,
                    risk_level=risk,
                    snippet_masked=masked,
                    match_start=match.start(),
                    match_end=match.end(),
                    detection_rule=rule_name
                )
                findings.append(finding)
                sanitized = sanitized.replace(raw_match, f"[REDACTED:{category.value}]")

        # 2. High-Entropy String Detection
        tokens = text.split()
        for tok in tokens:
            cleaned = re.sub(r'[^a-zA-Z0-9]', '', tok)
            if len(cleaned) >= 24 and not cleaned.startswith("[REDACTED"):
                ent = self.calculate_entropy(cleaned)
                if ent >= self.entropy_threshold:
                    finding = DLPFinding(
                        finding_id=f"dlp_{uuid.uuid4().hex[:8]}",
                        category=DLPCategory.HIGH_ENTROPY_SUSPICIOUS,
                        channel=channel,
                        risk_level=DLPRiskLevel.MEDIUM,
                        snippet_masked=cleaned[:4] + "****" + cleaned[-2:],
                        match_start=0,
                        match_end=len(cleaned),
                        detection_rule=f"High Shannon Entropy ({ent:.2f} >= {self.entropy_threshold})"
                    )
                    findings.append(finding)
                    sanitized = sanitized.replace(tok, "[REDACTED:HIGH_ENTROPY_SECRET]")

        highest_risk = DLPRiskLevel.LOW
        if any(f.risk_level == DLPRiskLevel.CRITICAL for f in findings):
            highest_risk = DLPRiskLevel.CRITICAL
        elif any(f.risk_level == DLPRiskLevel.HIGH for f in findings):
            highest_risk = DLPRiskLevel.HIGH
        elif any(f.risk_level == DLPRiskLevel.MEDIUM for f in findings):
            highest_risk = DLPRiskLevel.MEDIUM

        return DLPScanResult(
            clean=(len(findings) == 0),
            findings=findings,
            sanitized_text=sanitized,
            highest_risk=highest_risk,
            action_taken="BLOCK" if highest_risk == DLPRiskLevel.CRITICAL else "ALLOW"
        )
