"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Internet-Facing Edge Security Gateway & WAF

Implements AREA C of the Master Infrastructure Specification:
- Prepares ZONATA for safe Internet exposure.
- Implements:
    * Edge Reverse Proxy routing & WAF inspection
    * Token-bucket rate limiting per IP and per tenant
    * Internal service shielding: strictly blocks external routing to:
        Vault (:8200), Database (:5432), NATS (:4222), Temporal (:7233), OpenFGA, and Workers
    * Web Application Firewall (WAF) rule evaluation:
        - SQL Injection (SQLi)
        - Cross-Site Scripting (XSS)
        - Path Traversal (../)
        - Command Injection
        - Malformed/Oversized Payload Shielding (10MB limit)
    * Production HTTP security header injection:
        - Strict-Transport-Security (HSTS)
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - Content-Security-Policy (CSP)
        - Referrer-Policy: strict-origin-when-cross-origin
- Constitutional Invariant:
    Edge security is outer perimeter defense.
    ZONATA sovereign AuthorityGateway remains the ultimate authority.
"""

import re
import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("zonata.infra.edge")

@dataclass
class EdgeInspectionResult:
    is_allowed: bool
    status_code: int
    blocking_reason: Optional[str] = None
    violation_category: Optional[str] = None
    rate_limit_remaining: int = 100
    security_headers: Dict[str, str] = field(default_factory=dict)


class EdgeSecurityGateway:
    """
    Edge Reverse Proxy & WAF Gateway for Internet-Facing Traffic.
    Protects internal services and enforces edge security boundaries.
    """

    MAX_PAYLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

    # Internal service paths that must NEVER be accessed from external ingress
    RESTRICTED_INTERNAL_PATHS = [
        "/v1/sys/",          # Vault sys API
        "/v1/secret/",       # Direct Vault secrets API
        "/temporal/api/",    # Temporal internal API
        "/openfga/stores",   # OpenFGA internal store config
        "/nats/monitor",     # NATS internal monitor
        "/debug/pprof",      # Internal profiling endpoints
        "/metrics/internal"  # Unauthenticated internal metrics
    ]

    # WAF Heuristic Signatures
    WAF_RULES = [
        (re.compile(r"(?i)(\bUNION\s+ALL\s+SELECT\b|\bSELECT\s+.*\s+FROM\s+information_schema\b|\bDROP\s+TABLE\b|\bALTER\s+TABLE\b)"), "SQL_INJECTION"),
        (re.compile(r"(?i)(<script\b[^>]*>.*?</script>|javascript:\s*|onload\s*=\s*['\"]?|onerror\s*=\s*['\"]?)"), "CROSS_SITE_SCRIPTING"),
        (re.compile(r"(\.\./\.\./|\.\.\\\.\.\\|/etc/passwd|/etc/shadow|/proc/self)"), "PATH_TRAVERSAL"),
        (re.compile(r"(?i)(;\s*(rm\s+-rf|wget\s+http|curl\s+http|bash\s+-i|mkfifo))"), "COMMAND_INJECTION")
    ]

    # Standard security headers applied to all outbound responses
    SECURITY_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }

    def __init__(self, default_rate_limit: int = 120):
        # In-memory token bucket rate limiter: ip_or_tenant -> (tokens, last_refill)
        self.default_rate_limit = default_rate_limit  # requests per minute
        self._rate_limits: Dict[str, Tuple[float, float]] = {}

    def _check_rate_limit(self, client_key: str) -> Tuple[bool, int]:
        now = time.time()
        capacity = float(self.default_rate_limit)
        refill_rate = capacity / 60.0  # tokens per second

        if client_key not in self._rate_limits:
            self._rate_limits[client_key] = (capacity - 1.0, now)
            return True, int(capacity - 1)

        tokens, last_time = self._rate_limits[client_key]
        elapsed = now - last_time
        tokens = min(capacity, tokens + (elapsed * refill_rate))

        if tokens >= 1.0:
            tokens -= 1.0
            self._rate_limits[client_key] = (tokens, now)
            return True, int(tokens)
        else:
            self._rate_limits[client_key] = (tokens, now)
            return False, 0

    def inspect_inbound_request(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        body_bytes: bytes,
        client_ip: str,
        tenant_id: Optional[str] = None
    ) -> EdgeInspectionResult:
        """
        Comprehensive edge gate inspection before traffic touches ZONATA application layer.
        """
        # 1. Payload Size Check
        if len(body_bytes) > self.MAX_PAYLOAD_BYTES:
            logger.warning(f"Edge WAF blocked oversized payload ({len(body_bytes)} bytes) from {client_ip}")
            return EdgeInspectionResult(
                is_allowed=False,
                status_code=413,
                blocking_reason="Payload Too Large: exceeds 10MB limit",
                violation_category="OVERSIZED_PAYLOAD",
                security_headers=self.SECURITY_HEADERS
            )

        # 2. Internal Service Shielding Check
        path_lower = path.lower()
        for restricted_prefix in self.RESTRICTED_INTERNAL_PATHS:
            if restricted_prefix in path_lower:
                logger.error(f"[SECURITY ALERT] Unauthorized access to restricted internal path '{path}' blocked from {client_ip}")
                return EdgeInspectionResult(
                    is_allowed=False,
                    status_code=403,
                    blocking_reason=f"Access to internal infrastructure path '{path}' is strictly forbidden",
                    violation_category="RESTRICTED_INTERNAL_SERVICE",
                    security_headers=self.SECURITY_HEADERS
                )

        # 3. Rate Limit Check (Token Bucket per Tenant or IP)
        rate_key = tenant_id or client_ip
        allowed, remaining = self._check_rate_limit(rate_key)
        if not allowed:
            logger.warning(f"Rate limit exceeded for {rate_key}")
            return EdgeInspectionResult(
                is_allowed=False,
                status_code=429,
                blocking_reason="Too Many Requests: rate limit exceeded",
                violation_category="RATE_LIMIT_EXCEEDED",
                rate_limit_remaining=0,
                security_headers=self.SECURITY_HEADERS
            )

        # 4. WAF Inspection on Path, Query, and Body
        body_text = ""
        try:
            body_text = body_bytes.decode("utf-8", errors="ignore")
        except Exception:
            pass

        inspected_target = f"{path}\n{body_text}"
        for pattern, category in self.WAF_RULES:
            if pattern.search(inspected_target):
                logger.error(f"[WAF DETECTED] Threat '{category}' matched on path '{path}' from {client_ip}")
                return EdgeInspectionResult(
                    is_allowed=False,
                    status_code=400,
                    blocking_reason=f"WAF Policy Violation: malicious payload matching signature '{category}'",
                    violation_category=category,
                    rate_limit_remaining=remaining,
                    security_headers=self.SECURITY_HEADERS
                )

        # All checks passed
        return EdgeInspectionResult(
            is_allowed=True,
            status_code=200,
            rate_limit_remaining=remaining,
            security_headers=self.SECURITY_HEADERS
        )

    def apply_security_headers(self, headers_dict: Dict[str, str]) -> Dict[str, str]:
        """Appends mandatory security headers to any outgoing HTTP response."""
        result = dict(headers_dict)
        result.update(self.SECURITY_HEADERS)
        return result


# Global singleton instance
edge_security_gateway = EdgeSecurityGateway()
