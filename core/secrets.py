"""
RoboAssistant Company OS 1.0 — Secret Isolation & PII Sanitization Engine
Implements Sections 74 & 80:
- Mediated secret storage (never exposed raw to LLM prompts)
- High-fidelity PII and credential redaction
- Invariant: Zero raw credentials exposed to LLM context, logs, or audit evidence.
"""

from typing import Dict, Any, Optional
import re
import hashlib
import uuid

class SecretManager:
    """
    In-memory isolated secret repository.
    Returns opaque secret references rather than plaintext tokens to agents.
    """
    _SECRETS: Dict[str, str] = {}

    @classmethod
    def store_secret(cls, tenant_id: str, secret_name: str, secret_value: str) -> str:
        ref_id = f"sec_{hashlib.sha256(f'{tenant_id}:{secret_name}'.encode()).hexdigest()[:12]}"
        cls._SECRETS[ref_id] = secret_value
        return ref_id

    @classmethod
    def get_secret(cls, ref_id: str) -> Optional[str]:
        return cls._SECRETS.get(ref_id)

class ContentSanitizer:
    """
    Sanitizes prompts, logs, and evidence to prevent accidental leakage of PII or credentials.
    """
    REDACTION_PATTERNS = [
        (r"(bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[REDACTED_AUTH_TOKEN]"),
        (r"(api[_\-]?key\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{16,}(['\"]?)", r"\1[REDACTED_API_KEY]\2"),
        (r"(password\s*(?:[:=]|\s)\s*['\"]?)[^'\"\s]{6,}(['\"]?)", r"\1[REDACTED_PASSWORD]\2"),
        (r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CREDIT_CARD]"),
        (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]")
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return ""
        sanitized = text
        for pattern, replacement in cls.REDACTION_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
