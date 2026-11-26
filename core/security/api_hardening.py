"""
ZONATA Sovereign Core — Sub-Step 5E: API Hardening, OWASP ASVS & Edge Perimeter Defense.
=======================================================================================
Governed by:
- OWASP Top 10 / ASVS L2 API controls.
- Host header injection defense & strict CORS origin controls.
- Auth brute-force protection with progressive exponential lockout.
- WAF attack payload inspection (SQLi, XSS, Path Traversal, Command Injection).
"""

from __future__ import annotations

import collections
import logging
import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("zonata.security.api")


class SecurityAttackDetected(Exception):
    """Raised when an active attack pattern (SQLi, XSS, Path Traversal, etc.) is detected."""
    pass


class HostHeaderPoisoningError(SecurityAttackDetected):
    """Raised when an unapproved or spoofed Host header is presented."""
    pass


class CORSSecurityViolation(SecurityAttackDetected):
    """Raised when CORS configuration or request violates cross-origin security rules."""
    pass


class BruteForceLockoutActive(Exception):
    """Raised when an entity is temporarily locked out due to excessive failed attempts."""
    pass


@dataclass
class APIHardeningConfig:
    allowed_hosts: List[str] = field(
        default_factory=lambda: [
            "localhost",
            "127.0.0.1",
            "zonata.internal",
            "api.zonata.internal",
            "app.zonata.internal",
        ]
    )
    cors_allowed_origins: List[str] = field(
        default_factory=lambda: [
            "https://app.zonata.internal",
            "https://console.zonata.internal",
        ]
    )
    max_payload_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_auth_attempts: int = 5
    base_lockout_seconds: float = 2.0
    max_lockout_seconds: float = 300.0


class HostHeaderValidator:
    """Protects against HTTP Host header poisoning and password-reset hijacking."""

    def __init__(self, allowed_hosts: Optional[List[str]] = None):
        self.allowed_hosts = set(
            allowed_hosts or APIHardeningConfig().allowed_hosts
        )

    def validate_host(self, host: str) -> bool:
        if not host:
            raise HostHeaderPoisoningError("Empty Host header presented")

        # Strip port if present (e.g., localhost:8000)
        clean_host = host.split(":")[0].strip().lower()

        if clean_host not in self.allowed_hosts and "*" not in self.allowed_hosts:
            raise HostHeaderPoisoningError(
                f"Host '{clean_host}' is not in the authorized hosts allow-list: {self.allowed_hosts}"
            )
        return True


class CORSValidator:
    """Validates CORS requests according to ASVS V14.4."""

    def __init__(self, allowed_origins: Optional[List[str]] = None):
        self.allowed_origins = set(
            allowed_origins or APIHardeningConfig().cors_allowed_origins
        )

    def validate_origin(
        self, origin: Optional[str], allows_credentials: bool = True
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Validates origin and returns appropriate CORS headers.
        Rule: Reject wildcard '*' when allows_credentials is True.
        """
        headers: Dict[str, str] = {
            "Vary": "Origin",
        }

        if not origin:
            # Same-origin request
            return True, headers

        origin_clean = origin.rstrip("/")

        # Check for illegal wildcard with credentials
        if allows_credentials and origin_clean == "*":
            raise CORSSecurityViolation(
                "ASVS V14.4 Violation: Access-Control-Allow-Origin cannot be '*' when credentials are required"
            )

        if origin_clean not in self.allowed_origins and "*" not in self.allowed_origins:
            raise CORSSecurityViolation(
                f"Origin '{origin}' is not in the allowed CORS origins list: {self.allowed_origins}"
            )

        headers["Access-Control-Allow-Origin"] = origin
        if allows_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Tenant-ID, X-Company-ID, X-Request-ID, X-Idempotency-Key"
        )
        return True, headers


class BruteForceProtector:
    """Protects sensitive endpoints (auth, token generation) against brute-force attacks."""

    def __init__(
        self,
        max_attempts: int = 5,
        base_lockout_seconds: float = 2.0,
        max_lockout_seconds: float = 300.0,
    ):
        self.max_attempts = max_attempts
        self.base_lockout = base_lockout_seconds
        self.max_lockout = max_lockout_seconds
        # key -> {"failures": count, "locked_until": timestamp}
        self._tracking: Dict[str, Dict[str, Any]] = collections.defaultdict(
            lambda: {"failures": 0, "locked_until": 0.0}
        )

    def check_attempt(self, key: str, now: Optional[float] = None) -> None:
        """Checks if key is currently locked out."""
        current_time = now if now is not None else time.time()
        record = self._tracking[key]
        if record["locked_until"] > current_time:
            remaining = record["locked_until"] - current_time
            raise BruteForceLockoutActive(
                f"Too many failed attempts. Locked out for {remaining:.1f} more seconds."
            )

    def record_failure(self, key: str, now: Optional[float] = None) -> float:
        """Records a failure and computes progressive exponential lockout duration."""
        current_time = now if now is not None else time.time()
        record = self._tracking[key]
        record["failures"] += 1

        if record["failures"] >= self.max_attempts:
            # Progressive exponential backoff: base * 2^(failures - max)
            excess = record["failures"] - self.max_attempts
            lockout_duration = min(self.base_lockout * (2 ** excess), self.max_lockout)
            record["locked_until"] = current_time + lockout_duration
            return lockout_duration
        return 0.0

    def record_success(self, key: str) -> None:
        """Clears failure counter on successful operation."""
        if key in self._tracking:
            del self._tracking[key]


class SecurityHeaderInjector:
    """Generates standard OWASP defense headers."""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        return {
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; object-src 'none'; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
            ),
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
            "X-XSS-Protection": "1; mode=block",
        }


class WAFPayloadInspector:
    """Inspects HTTP payloads and query strings for standard injection attacks."""

    SQLI_PATTERNS = [
        re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
        re.compile(r"(\bOR\b\s+['\"]?1['\"]?\s*=\s*['\"]?1)", re.IGNORECASE),
        re.compile(r"(\bDROP\b\s+\bTABLE\b)", re.IGNORECASE),
        re.compile(r"(--|#|/\*).*\bSELECT\b", re.IGNORECASE),
    ]

    XSS_PATTERNS = [
        re.compile(r"<script\b[^>]*>", re.IGNORECASE),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"onerror\s*=", re.IGNORECASE),
        re.compile(r"onload\s*=", re.IGNORECASE),
    ]

    TRAVERSAL_PATTERNS = [
        re.compile(r"\.\./"),
        re.compile(r"\.\.\\"),
        re.compile(r"%2e%2e", re.IGNORECASE),
    ]

    COMMAND_INJECTION_PATTERNS = [
        re.compile(r"[;&|`]\s*(sh|bash|curl|wget|nc|cat\s+/etc/passwd)", re.IGNORECASE),
    ]

    @classmethod
    def inspect(cls, data: str, max_bytes: int = 10 * 1024 * 1024) -> None:
        """Inspects data and raises SecurityAttackDetected on any match."""
        if not data:
            return

        if len(data.encode("utf-8")) > max_bytes:
            raise SecurityAttackDetected(
                f"Payload size {len(data.encode('utf-8'))} bytes exceeds maximum allowed limit {max_bytes} bytes."
            )

        for pat in cls.SQLI_PATTERNS:
            if pat.search(data):
                raise SecurityAttackDetected(f"SQL Injection attack detected: pattern matched '{pat.pattern}'")

        for pat in cls.XSS_PATTERNS:
            if pat.search(data):
                raise SecurityAttackDetected(f"Cross-Site Scripting (XSS) attack detected: pattern matched '{pat.pattern}'")

        for pat in cls.TRAVERSAL_PATTERNS:
            if pat.search(data):
                raise SecurityAttackDetected(f"Path Traversal attack detected: pattern matched '{pat.pattern}'")

        for pat in cls.COMMAND_INJECTION_PATTERNS:
            if pat.search(data):
                raise SecurityAttackDetected(f"Command Injection attack detected: pattern matched '{pat.pattern}'")
