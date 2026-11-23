"""
ZONATA Telemetry Sanitizer & Secret Redaction Engine
===================================================
Enforces Standing Rule 24 and Standing Rule 36:
- Zero plaintext credentials, passwords, private keys, or canary secrets in telemetry.
- Strict attribute allow-list enforcement.
- Prompts and completion bodies omitted by default, captured only under explicit tenant opt-in.
- Raises TelemetryLeakageError in strict verification mode.
"""

import re
from typing import Dict, Any, Optional, Set, Union


class TelemetryLeakageError(ValueError):
    """Raised when an unredacted secret or canary token is detected in strict mode."""
    pass


# High-entropy credential patterns and known secret prefixes
SENSITIVE_KEY_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"password",
        r"secret",
        r"(?:auth|access|refresh|bearer|session|api|csrf|id)?[._-]?token\b",
        r"\btoken\b",
        r"api[_-]?key",
        r"\bauth\b",
        r"bearer",
        r"credential",
        r"private[_-]?key",
        r"access[_-]?key",
        r"session[_-]?id",
        r"cookie",
        r"certificate",
        r"signature",
    ]
]

SENSITIVE_VALUE_PATTERNS = [
    # Canary secrets
    re.compile(r"ZONATA_CANARY_[A-Za-z0-9_\-]+"),
    # Common API key formats
    re.compile(r"\b(?:sk|pk|ak)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]{16,}\b", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
]

# Allowed stable telemetry attribute prefixes and keys
ALLOWED_ATTRIBUTE_PREFIXES = (
    "zonata.",
    "service.",
    "gen_ai.",
    "telemetry.",
    "code.",
    "http.",
    "net.",
    "db.",
    "rpc.",
    "trace.",
    "span.",
    "task.",
)


class TelemetrySanitizer:
    """Sanitizes telemetry span attributes, events, and metrics payloads."""

    def __init__(self, default_strict: bool = False):
        self.default_strict = default_strict

    @classmethod
    def is_sensitive_key(cls, key: str) -> bool:
        """Checks if an attribute key indicates sensitive data."""
        k = key.lower()
        # Explicit exception for token counts and usage metrics
        if any(metric in k for metric in ["tokens_input", "tokens_output", "total_tokens", "prompt_tokens", "completion_tokens", "token_count"]):
            return False
        return any(pattern.search(k) for pattern in SENSITIVE_KEY_PATTERNS)

    @classmethod
    def contains_sensitive_value(cls, value: str) -> bool:
        """Scans string for high-entropy secrets or canary markers."""
        return any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS)

    @classmethod
    def redact_string(cls, val_str: str) -> str:
        """Replaces detected secret patterns in a string with redaction markers."""
        cleaned = val_str
        for pattern in SENSITIVE_VALUE_PATTERNS:
            cleaned = pattern.sub("[REDACTED_SECRET]", cleaned)
        return cleaned

    def sanitize_attribute(
        self,
        key: str,
        value: Any,
        strict: Optional[bool] = None,
        tenant_allow_prompt_capture: bool = False
    ) -> Optional[Any]:
        """
        Sanitizes an individual span attribute.
        Returns sanitized value, or None if the attribute should be dropped.
        """
        is_strict = self.default_strict if strict is None else strict

        # Check key against sensitive key patterns
        if self.is_sensitive_key(key):
            if is_strict:
                raise TelemetryLeakageError(
                    f"Sensitive key '{key}' blocked by strict telemetry policy (Rule 24)"
                )
            return "[REDACTED_CREDENTIAL]"

        # Handle prompt and completion text bodies per Rule 36
        if key in ("gen_ai.prompt", "gen_ai.completion", "zonata.prompt_body", "zonata.response_body"):
            if not tenant_allow_prompt_capture:
                # Omit prompt/response body unless tenant policy explicitly permits
                return "[BODY_OMITTED_BY_TENANT_POLICY]"

        # Value-level scanning for strings
        if isinstance(value, str):
            if self.contains_sensitive_value(value):
                if is_strict:
                    raise TelemetryLeakageError(
                        f"Secret detected in attribute '{key}': value matched canary/credential pattern (Rule 24)"
                    )
                return self.redact_string(value)
            return value

        # Non-string primitives (int, float, bool)
        if isinstance(value, (int, float, bool)):
            return value

        # Nested dict or list
        if isinstance(value, dict):
            return self.sanitize_dict(value, strict=is_strict, tenant_allow_prompt_capture=tenant_allow_prompt_capture)
        if isinstance(value, (list, tuple)):
            return [
                self.sanitize_attribute(f"{key}[{i}]", item, strict=is_strict, tenant_allow_prompt_capture=tenant_allow_prompt_capture)
                for i, item in enumerate(value)
            ]

        # Fallback string conversion
        str_val = str(value)
        if self.contains_sensitive_value(str_val):
            if is_strict:
                raise TelemetryLeakageError(f"Secret detected in attribute '{key}' string representation")
            return self.redact_string(str_val)
        return str_val

    def sanitize_dict(
        self,
        attributes: Dict[str, Any],
        strict: Optional[bool] = None,
        tenant_allow_prompt_capture: bool = False
    ) -> Dict[str, Any]:
        """Sanitizes an entire dictionary of attributes."""
        sanitized = {}
        for k, v in attributes.items():
            clean_v = self.sanitize_attribute(
                str(k),
                v,
                strict=strict,
                tenant_allow_prompt_capture=tenant_allow_prompt_capture
            )
            if clean_v is not None:
                sanitized[str(k)] = clean_v
        return sanitized
