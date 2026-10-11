"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Presidio-Compatible Sensitive Data Detection & Anonymization Engine
=====================================================================
Sovereign, pure-Python implementation of the Microsoft Presidio inspection &
anonymization architecture. Provides high-throughput, local, privacy-safe PII,
secrets, credentials, and company-specific entity detection without transmitting
raw data to external services.

Constitutional Invariants:
  1. ZERO_NETWORK_TRANSMISSION: All inspection is strictly local.
  2. DETECTION != POLICY: Inspection informs policy; policy makes authority decisions.
  3. NO_RAW_SECRETS_LOGGED: Diagnostics and audit logs contain hashes/counts, never secrets.
  4. ADAPTABLE_OPERATORS: Supports Redaction, Tokenization, Masking, and Hashing.
"""

import re
import time
import uuid
import hashlib
import hmac
import secrets
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field


# =============================================================================
# 1. CORE PRESIDIO DATA STRUCTURES
# =============================================================================

@dataclass
class RecognizerResult:
    """Represents a single detected sensitive entity span with confidence score."""
    entity_type: str
    start: int
    end: int
    score: float
    analysis_explanation: Optional[Dict[str, Any]] = None
    text_snippet: Optional[str] = None  # Safe description, never raw credentials

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "score": round(self.score, 3),
            "explanation": self.analysis_explanation or {}
        }


@dataclass
class AnonymizerResult:
    """Output of the anonymization engine."""
    text: str
    items_count: int
    entities_detected: List[str]
    token_map: Dict[str, str] = field(default_factory=dict)
    execution_time_ms: float = 0.0


# =============================================================================
# 2. PATTERNS & RECOGNIZERS
# =============================================================================

@dataclass
class Pattern:
    name: str
    regex: str
    score: float
    compiled: re.Pattern = field(init=False)

    def __post_init__(self):
        self.compiled = re.compile(self.regex, re.IGNORECASE)


class BaseRecognizer:
    """Base class for all Presidio entity recognizers."""
    def __init__(self, name: str, supported_entities: List[str], context_words: Optional[List[str]] = None):
        self.name = name
        self.supported_entities = supported_entities
        self.context_words = [w.lower() for w in (context_words or [])]

    def analyze(self, text: str, entities: Optional[List[str]] = None) -> List[RecognizerResult]:
        raise NotImplementedError


class PatternRecognizer(BaseRecognizer):
    """Regex pattern-based recognizer with context enhancement."""
    def __init__(
        self,
        name: str,
        supported_entities: List[str],
        patterns: List[Pattern],
        context_words: Optional[List[str]] = None,
        context_boost: float = 0.15
    ):
        super().__init__(name, supported_entities, context_words)
        self.patterns = patterns
        self.context_boost = context_boost

    def _has_context(self, text: str, start: int, end: int, window: int = 50) -> bool:
        if not self.context_words:
            return False
        left = max(0, start - window)
        right = min(len(text), end + window)
        surrounding = (text[left:start] + " " + text[end:right]).lower()
        return any(cw in surrounding for cw in self.context_words)

    def analyze(self, text: str, entities: Optional[List[str]] = None) -> List[RecognizerResult]:
        results = []
        for pat in self.patterns:
            entity_type = self.supported_entities[0]
            if entities and entity_type not in entities:
                continue

            for match in pat.compiled.finditer(text):
                start, end = match.start(), match.end()
                val = match.group()
                if not val.strip():
                    continue

                score = pat.score
                has_ctx = self._has_context(text, start, end)
                if has_ctx:
                    score = min(1.0, score + self.context_boost)

                results.append(RecognizerResult(
                    entity_type=entity_type,
                    start=start,
                    end=end,
                    score=score,
                    analysis_explanation={
                        "recognizer": self.name,
                        "pattern": pat.name,
                        "context_boost": has_ctx
                    },
                    text_snippet=f"{entity_type} span [{start}:{end}]"
                ))
        return results


# =============================================================================
# 3. STANDARD BUILT-IN RECOGNIZERS
# =============================================================================

class SsnRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="SsnRecognizer",
            supported_entities=["US_SSN"],
            patterns=[
                Pattern("ssn_standard", r"\b\d{3}-\d{2}-\d{4}\b", 0.85),
                Pattern("ssn_spaced", r"\b\d{3}\s\d{2}\s\d{4}\b", 0.75),
                Pattern("ssn_contiguous", r"\b(?<!\d)\d{9}(?!\d)\b", 0.60),
            ],
            context_words=["ssn", "social security", "social-security", "taxpayer", "itin", "ss#"]
        )


class CreditCardRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__(
            name="CreditCardRecognizer",
            supported_entities=["CREDIT_CARD"],
            context_words=["card", "credit", "debit", "visa", "mastercard", "amex", "cvv", "exp"]
        )
        self.pattern = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b3[47]\d{13}\b")

    def _luhn_check(self, num_str: str) -> bool:
        digits = [int(c) for c in num_str if c.isdigit()]
        if len(digits) not in (15, 16):
            return False
        checksum = 0
        reverse = digits[::-1]
        for i, d in enumerate(reverse):
            if i % 2 == 1:
                doubled = d * 2
                checksum += doubled - 9 if doubled > 9 else doubled
            else:
                checksum += d
        return checksum % 10 == 0

    def analyze(self, text: str, entities: Optional[List[str]] = None) -> List[RecognizerResult]:
        if entities and "CREDIT_CARD" not in entities:
            return []
        results = []
        for match in self.pattern.finditer(text):
            val = match.group()
            clean_digits = re.sub(r"[-\s]", "", val)
            is_luhn = self._luhn_check(clean_digits)
            score = 0.95 if is_luhn else 0.70
            results.append(RecognizerResult(
                entity_type="CREDIT_CARD",
                start=match.start(),
                end=match.end(),
                score=score,
                analysis_explanation={"luhn_valid": is_luhn, "recognizer": self.name}
            ))
        return results


class EmailRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="EmailRecognizer",
            supported_entities=["EMAIL_ADDRESS"],
            patterns=[
                Pattern("email_rfc", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", 0.90)
            ],
            context_words=["email", "mail", "contact", "recipient", "sender", "inbox"]
        )


class PhoneRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="PhoneRecognizer",
            supported_entities=["PHONE_NUMBER"],
            patterns=[
                Pattern("phone_intl", r"\b(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b", 0.75),
            ],
            context_words=["phone", "telephone", "mobile", "cell", "call", "sms", "tel"]
        )


class IpAddressRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="IpAddressRecognizer",
            supported_entities=["IP_ADDRESS"],
            patterns=[
                Pattern("ipv4", r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", 0.85),
                Pattern("ipv6", r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b", 0.90)
            ],
            context_words=["ip", "host", "address", "dns", "gateway", "subnet"]
        )


class CryptoKeyRecognizer(BaseRecognizer):
    """Detects private cryptographic keys in PEM/OpenSSH format."""
    def __init__(self):
        super().__init__(
            name="CryptoKeyRecognizer",
            supported_entities=["CRYPTO_PRIVATE_KEY"],
            context_words=["key", "pem", "private", "rsa", "ed25519"]
        )
        self.pattern = re.compile(
            r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----.*?-----END\s+(?:RSA|DSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----",
            re.DOTALL | re.IGNORECASE
        )

    def analyze(self, text: str, entities: Optional[List[str]] = None) -> List[RecognizerResult]:
        if entities and "CRYPTO_PRIVATE_KEY" not in entities:
            return []
        results = []
        for match in self.pattern.finditer(text):
            results.append(RecognizerResult(
                entity_type="CRYPTO_PRIVATE_KEY",
                start=match.start(),
                end=match.end(),
                score=1.0,
                analysis_explanation={"recognizer": self.name, "format": "PEM_CERTIFICATE_BLOCK"}
            ))
        return results


class ApiKeyAndSecretRecognizer(PatternRecognizer):
    """Detects cloud API keys, JWT tokens, and OAuth credentials."""
    def __init__(self):
        super().__init__(
            name="ApiKeyAndSecretRecognizer",
            supported_entities=["API_KEY_OR_SECRET"],
            patterns=[
                Pattern("bearer_jwt", r"\bBearer\s+eyJ[a-zA-Z0-9_\-\.]{20,}\b", 0.95),
                Pattern("jwt_raw", r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b", 0.95),
                Pattern("github_pat", r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b", 0.99),
                Pattern("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b", 0.98),
                Pattern("slack_token", r"\bxox[baprs]-[0-9a-zA-Z]{10,48}\b", 0.98),
                Pattern("generic_api_key", r"(?i)(?:api[_-]?key|secret[_-]?token|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?", 0.90),
                Pattern("openai_anthropic_key", r"\bsk-[a-zA-Z0-9_\-]{20,}\b", 0.95),
                Pattern("password_assignment", r"(?i)password\s*[:=]\s*['\"]([^'\"]{6,})['\"]", 0.85)
            ],
            context_words=["auth", "authorization", "secret", "token", "password", "credential"]
        )


class FinancialAccountRecognizer(PatternRecognizer):
    """Detects IBANs, bank routing numbers, and corporate financial identifiers."""
    def __init__(self):
        super().__init__(
            name="FinancialAccountRecognizer",
            supported_entities=["FINANCIAL_ACCOUNT"],
            patterns=[
                Pattern("iban", r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", 0.85),
                Pattern("routing_number", r"\b\d{9}\b", 0.65),
                Pattern("financial_keywords", r"(?i)(?:ebitda|gross\s+margin|revenue\s+forecast|bank\s+account|routing\s+number)\s*[:=]?\s*[\$₹€£]?\s*[\d,]+(?:\.\d+)?", 0.80)
            ],
            context_words=["bank", "account", "routing", "iban", "swift", "bic", "wire", "ledger"]
        )


class SyntheticCanaryRecognizer(PatternRecognizer):
    """Detects synthetic security canaries used in testing and active defense."""
    def __init__(self):
        super().__init__(
            name="SyntheticCanaryRecognizer",
            supported_entities=["SECURITY_CANARY"],
            patterns=[
                Pattern("canary_standard", r"(?i)\bcanary_sec_[a-zA-Z0-9_]{8,}\b", 1.0),
                Pattern("canary_zonata", r"(?i)\bZONATA_CANARY_[A-Za-z0-9_]{6,}\b", 1.0),
                Pattern("canary_token", r"(?i)\bcanary_tok_[a-zA-Z0-9]{12,}\b", 1.0),
            ],
            context_words=["canary", "honeytoken", "tripwire", "test"]
        )


# =============================================================================
# 4. COMPANY-SPECIFIC CUSTOM RECOGNIZERS (ZONATA CORPORATE)
# =============================================================================

class ZonataEmployeeIdRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="ZonataEmployeeIdRecognizer",
            supported_entities=["ZONATA_EMPLOYEE_ID"],
            patterns=[
                Pattern("zonata_emp_standard", r"\bZN-EMP-\d{4,6}\b", 0.95),
                Pattern("zonata_emp_alt", r"\bEMP-[A-Z0-9]{5,8}\b", 0.90)
            ],
            context_words=["employee", "staff", "badge", "payroll", "personnel", "worker"]
        )


class ZonataInternalTokenRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="ZonataInternalTokenRecognizer",
            supported_entities=["ZONATA_INTERNAL_TOKEN"],
            patterns=[
                Pattern("zonata_token_live", r"\bzn_(?:live|test|sec)_[a-zA-Z0-9]{24,}\b", 0.99),
                Pattern("zonata_auth_secret", r"\bZONATA_[A-Z0-9_]+_KEY_[0-9]{4}\b", 0.95)
            ],
            context_words=["zonata", "token", "internal", "key", "tenant"]
        )


class ZonataCustomerAccountRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="ZonataCustomerAccountRecognizer",
            supported_entities=["ZONATA_CUSTOMER_ID"],
            patterns=[
                Pattern("zonata_cust_id", r"\bCUST-[A-Z0-9]{6,10}\b", 0.92),
                Pattern("zonata_acc_id", r"\bACC-IN-\d{8,12}\b", 0.90)
            ],
            context_words=["customer", "client", "account", "subscriber", "billing"]
        )


class ZonataConfidentialProjectRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            name="ZonataConfidentialProjectRecognizer",
            supported_entities=["CONFIDENTIAL_PROJECT_NAME"],
            patterns=[
                Pattern("proj_falcon", r"\bProject\s+Falcon\b", 0.90),
                Pattern("proj_titan", r"\bProject\s+Titan\b", 0.90),
                Pattern("proj_sovereign", r"\bProject\s+Sovereign\b", 0.90),
                Pattern("proj_deepsky", r"\bProject\s+DeepSky\b", 0.90)
            ],
            context_words=["merger", "acquisition", "confidential", "secret", "strategy", "nda", "classified"]
        )


class IndiaIdentityRecognizer(PatternRecognizer):
    """Detects Indian PII and financial tax identifiers (PAN, Aadhaar, GSTIN, IFSC)."""
    def __init__(self):
        super().__init__(
            name="IndiaIdentityRecognizer",
            supported_entities=["INDIA_IDENTITY_OR_TAX_ID"],
            patterns=[
                Pattern("in_pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0.95),
                Pattern("in_aadhaar", r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b", 0.90),
                Pattern("in_gstin", r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b", 0.95),
                Pattern("in_ifsc", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 0.90)
            ],
            context_words=["pan", "aadhaar", "uidai", "gstin", "gst", "ifsc", "tax", "income tax", "bank"]
        )


# =============================================================================
# 5. PRESIDIO ANALYZER ENGINE
# =============================================================================

class PresidioAnalyzerEngine:
    """
    Central analyzer orchestrating all entity recognizers.
    Thread-safe, sub-millisecond execution, pure Python.
    """
    def __init__(self):
        self.recognizers: List[BaseRecognizer] = []
        self._register_default_recognizers()

    def _register_default_recognizers(self):
        # Built-in Standard Recognizers
        self.register_recognizer(SsnRecognizer())
        self.register_recognizer(CreditCardRecognizer())
        self.register_recognizer(EmailRecognizer())
        self.register_recognizer(PhoneRecognizer())
        self.register_recognizer(IpAddressRecognizer())
        self.register_recognizer(CryptoKeyRecognizer())
        self.register_recognizer(ApiKeyAndSecretRecognizer())
        self.register_recognizer(FinancialAccountRecognizer())
        self.register_recognizer(SyntheticCanaryRecognizer())
        # Custom ZONATA Corporate Recognizers
        self.register_recognizer(ZonataEmployeeIdRecognizer())
        self.register_recognizer(ZonataInternalTokenRecognizer())
        self.register_recognizer(ZonataCustomerAccountRecognizer())
        self.register_recognizer(ZonataConfidentialProjectRecognizer())
        self.register_recognizer(IndiaIdentityRecognizer())

    def register_recognizer(self, recognizer: BaseRecognizer):
        self.recognizers.append(recognizer)

    def analyze(
        self,
        text: str,
        entities: Optional[List[str]] = None,
        language: str = "en",
        score_threshold: float = 0.50,
        correlation_id: Optional[str] = None
    ) -> List[RecognizerResult]:
        """
        Scans text and returns filtered, non-overlapping RecognizerResults.
        """
        if not text:
            return []

        raw_results: List[RecognizerResult] = []
        for r in self.recognizers:
            try:
                res = r.analyze(text, entities=entities)
                raw_results.extend(res)
            except Exception:
                continue

        # Filter by threshold
        filtered = [r for r in raw_results if r.score >= score_threshold]

        # Resolve overlaps (sort by start ascending, then score descending, then length descending)
        filtered.sort(key=lambda x: (x.start, -x.score, -(x.end - x.start)))

        resolved: List[RecognizerResult] = []
        last_end = -1
        for item in filtered:
            if item.start >= last_end:
                resolved.append(item)
                last_end = item.end
            else:
                # Overlap: keep the one already present since it sorted higher by score
                continue

        return resolved


# =============================================================================
# 6. PRESIDIO ANONYMIZER ENGINE
# =============================================================================

class PresidioAnonymizerEngine:
    """
    Applies anonymization operators to detected sensitive spans.
    Operators:
      - replace: Replace with safe entity placeholder, e.g. <REDACTED_US_SSN>
      - mask: Mask with asterisks preserving suffix, e.g. ****-****-****-1234
      - tokenize: Replace with reversible surrogate token (tok_dlp_<hash>)
      - hash: Replace with SHA-256 digest
      - redact: Strip content completely
    """
    def __init__(self, token_salt: Optional[str] = None):
        self._token_vault: Dict[str, str] = {}
        self._token_salt: str = token_salt or secrets.token_hex(32)

    def rotate_session_salt(self) -> str:
        """Rotates the session salt for new missions, enforcing cross-mission token isolation."""
        self._token_salt = secrets.token_hex(32)
        return self._token_salt

    def anonymize(
        self,
        text: str,
        analyzer_results: List[RecognizerResult],
        operators: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> AnonymizerResult:
        start_time = time.time()
        if not text or not analyzer_results:
            return AnonymizerResult(
                text=text,
                items_count=0,
                entities_detected=[],
                token_map={},
                execution_time_ms=0.0
            )

        # Sort reverse by start position to safely replace in-place
        sorted_results = sorted(analyzer_results, key=lambda r: r.start, reverse=True)
        mod_text = text
        token_map: Dict[str, str] = {}
        entities_found: Set[str] = set()

        ops = operators or {}

        for item in sorted_results:
            orig_span = mod_text[item.start:item.end]
            entity = item.entity_type
            entities_found.add(entity)

            op_config = ops.get(entity, ops.get("DEFAULT", {"type": "replace"}))
            op_type = op_config.get("type", "replace")

            if op_type == "replace":
                new_val = op_config.get("new_value", f"<REDACTED_{entity}>")
            elif op_type == "mask":
                masking_char = op_config.get("masking_char", "*")
                chars_to_mask = max(0, len(orig_span) - op_config.get("chars_to_preserve", 4))
                preserved = orig_span[chars_to_mask:]
                new_val = (masking_char * chars_to_mask) + preserved
            elif op_type == "tokenize":
                token_hash = hmac.new(self._token_salt.encode("utf-8"), orig_span.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
                surrogate = f"tok_dlp_{entity.lower()}_{token_hash}"
                self._token_vault[surrogate] = orig_span
                token_map[surrogate] = orig_span
                new_val = surrogate
            elif op_type == "hash":
                keyed_hash = hmac.new(self._token_salt.encode("utf-8"), orig_span.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
                new_val = f"<HMAC_{keyed_hash}>"
            elif op_type == "redact":
                new_val = ""
            else:
                new_val = f"<REDACTED_{entity}>"

            mod_text = mod_text[:item.start] + new_val + mod_text[item.end:]

        duration = (time.time() - start_time) * 1000.0
        return AnonymizerResult(
            text=mod_text,
            items_count=len(sorted_results),
            entities_detected=list(entities_found),
            token_map=token_map,
            execution_time_ms=round(duration, 3)
        )

    def detokenize(self, token: str) -> Optional[str]:
        """Safely detokenizes a surrogate token in authorized server context."""
        return self._token_vault.get(token)


# Global instances
presidio_analyzer = PresidioAnalyzerEngine()
presidio_anonymizer = PresidioAnonymizerEngine()
