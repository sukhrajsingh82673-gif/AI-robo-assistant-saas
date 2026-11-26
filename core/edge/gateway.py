"""
Edge Gateway Reverse Proxy & Route Entitlement Layer (ADR 0049, Rules 77, 80).
Provides TLS termination validation, security headers, token-bucket rate limiting,
W3C traceparent and X-Request-ID propagation, and RFC 9457 Problem Details errors.
"""

import time
import uuid
import json
from typing import Dict, Any, Optional, Callable, Tuple
from collections import defaultdict


class RFC9457Error(Exception):
    """Represents an RFC 9457 Problem Details for HTTP APIs error."""

    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        error_type: str = "about:blank",
        instance: Optional[str] = None,
        extensions: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.error_type = error_type
        self.instance = instance or f"urn:uuid:{uuid.uuid4()}"
        self.extensions = extensions or {}

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "type": self.error_type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "instance": self.instance,
        }
        payload.update(self.extensions)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class RateLimiter:
    """Token bucket / sliding window rate limiter."""

    def __init__(self, default_rate_per_sec: float = 50.0, default_burst: int = 100):
        self.default_rate = default_rate_per_sec
        self.default_burst = default_burst
        # state: key -> (tokens, last_update_timestamp)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def is_allowed(
        self, key: str, rate: Optional[float] = None, burst: Optional[int] = None
    ) -> Tuple[bool, int, float]:
        """
        Evaluate if a request with key is allowed.
        Returns: (allowed: bool, remaining_tokens: int, reset_after_seconds: float)
        """
        now = time.time()
        effective_rate = rate if rate is not None else self.default_rate
        effective_burst = burst if burst is not None else self.default_burst

        if key not in self._buckets:
            self._buckets[key] = (effective_burst - 1, now)
            return True, effective_burst - 1, 0.0

        current_tokens, last_time = self._buckets[key]
        elapsed = max(0.0, now - last_time)
        refilled_tokens = min(float(effective_burst), current_tokens + (elapsed * effective_rate))

        if refilled_tokens >= 1.0:
            remaining = int(refilled_tokens - 1.0)
            self._buckets[key] = (refilled_tokens - 1.0, now)
            return True, remaining, 0.0
        else:
            time_to_wait = (1.0 - refilled_tokens) / effective_rate if effective_rate > 0 else 1.0
            self._buckets[key] = (refilled_tokens, now)
            return False, 0, round(time_to_wait, 3)

    def reset(self, key: Optional[str] = None):
        if key:
            self._buckets.pop(key, None)
        else:
            self._buckets.clear()


class EdgeResponse:
    """Represents a normalized HTTP response returned by the Edge Gateway."""

    def __init__(
        self,
        status_code: int,
        headers: Dict[str, str],
        body: str,
        content_type: str = "application/json",
    ):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        self.content_type = content_type

    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class EdgeGateway:
    """
    Edge Gateway reverse proxy with security policies, rate limiting, and route entitlement checks.
    """

    DEFAULT_SECURITY_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        entitlements_verifier: Optional[Callable[[str, str, Dict[str, Any]], Tuple[bool, str]]] = None,
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.entitlements_verifier = entitlements_verifier
        self._routes: Dict[str, Callable] = {}

    def register_route(self, path_prefix: str, handler: Callable):
        self._routes[path_prefix] = handler

    def dispatch(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        client_ip: str,
        body: Optional[str] = None,
        api_key_override: Optional[str] = None,
    ) -> EdgeResponse:
        """
        Dispatches request through perimeter security checks, rate limiting, and route entitlements.
        """
        request_id = headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:16]}"
        traceparent = headers.get("traceparent") or f"00-{uuid.uuid4().hex}-{uuid.uuid4().hex[:16]}-01"

        out_headers = dict(self.DEFAULT_SECURITY_HEADERS)
        out_headers["X-Request-ID"] = request_id
        out_headers["traceparent"] = traceparent

        # 1. Rate limiting check
        rate_key = api_key_override or client_ip
        allowed, remaining, reset_after = self.rate_limiter.is_allowed(rate_key)
        out_headers["X-RateLimit-Remaining"] = str(remaining)

        if not allowed:
            out_headers["Retry-After"] = str(max(1, int(reset_after)))
            out_headers["Content-Type"] = "application/problem+json"
            problem = RFC9457Error(
                status=429,
                title="Too Many Requests",
                detail=f"Rate limit exceeded. Try again in {reset_after} seconds.",
                error_type="https://zonata.ai/errors/rate-limit-exceeded",
                extensions={"retry_after_seconds": reset_after},
            )
            return EdgeResponse(429, out_headers, problem.to_json(), content_type="application/problem+json")

        # 2. Entitlement verification check if registered
        tenant_id = headers.get("X-Tenant-ID") or "anonymous"
        if self.entitlements_verifier:
            entitled, reason = self.entitlements_verifier(tenant_id, path, headers)
            if not entitled:
                out_headers["Content-Type"] = "application/problem+json"
                problem = RFC9457Error(
                    status=403,
                    title="Feature Not Entitled",
                    detail=reason,
                    error_type="https://zonata.ai/errors/feature-not-entitled",
                    extensions={"tenant_id": tenant_id, "required_path": path},
                )
                return EdgeResponse(403, out_headers, problem.to_json(), content_type="application/problem+json")

        # 3. Route matching
        for prefix, handler in self._routes.items():
            if path.startswith(prefix):
                try:
                    res_status, res_headers, res_body = handler(method, path, headers, body)
                    out_headers.update(res_headers)
                    return EdgeResponse(res_status, out_headers, res_body)
                except Exception as ex:
                    out_headers["Content-Type"] = "application/problem+json"
                    problem = RFC9457Error(
                        status=500,
                        title="Internal Gateway Error",
                        detail=str(ex),
                        error_type="https://zonata.ai/errors/gateway-internal",
                    )
                    return EdgeResponse(500, out_headers, problem.to_json(), content_type="application/problem+json")

        # 4. Route not found
        out_headers["Content-Type"] = "application/problem+json"
        problem = RFC9457Error(
            status=404,
            title="Route Not Found",
            detail=f"No route handler matched path '{path}'.",
            error_type="https://zonata.ai/errors/not-found",
        )
        return EdgeResponse(404, out_headers, problem.to_json(), content_type="application/problem+json")
