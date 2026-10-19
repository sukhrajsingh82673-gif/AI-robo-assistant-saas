"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Tenant Fairness, Rate Limiting & Abuse Prevention Engine (Phase 16)

Provides multi-tiered, tenant-aware, and distributed rate limiting and concurrency management:
1. Global & IP Perimeter Shielding (DDoS / flood protection)
2. Tenant Quotas & Fairness (Tier-based: Free, Starter, Pro, Enterprise)
3. Identity / Actor Quotas (Per-user within tenant protection)
4. Endpoint-Specific Throttle (Expensive AI, reports, mutating operations, auth brute-force)
5. Distributed Concurrency Leases (Active workflow & agent execution limits per tenant)
6. Dual Database-Backed (Neon PostgreSQL) & Thread-Safe In-Memory Fallback
7. Strict RFC-Compliant HTTP 429 Responses with Retry-After & X-RateLimit-* headers
8. Sovereign Tenant Isolation: Zero cross-tenant data or quota leakage
"""

import os
import time
import uuid
import random
import threading
import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager

from core.db import db

logger = logging.getLogger("zonata.tenant_fairness")


class RateLimitAxis(str, Enum):
    GLOBAL = "GLOBAL_RATE_LIMIT_EXCEEDED"
    TENANT = "TENANT_QUOTA_EXCEEDED"
    IDENTITY = "IDENTITY_QUOTA_EXCEEDED"
    IP = "IP_RATE_LIMIT_EXCEEDED"
    ENDPOINT = "ENDPOINT_RATE_LIMIT_EXCEEDED"
    CONCURRENCY = "CONCURRENCY_LIMIT_EXCEEDED"
    AUTH_ABUSE = "AUTH_ABUSE_PREVENTED"


@dataclass
class RateLimitDecision:
    is_allowed: bool
    status_code: int = 200
    limit: int = 0
    remaining: int = 0
    retry_after: int = 0
    violation_axis: Optional[str] = None
    detail: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class TenantQuotaConfig:
    tier: str
    requests_per_minute: int
    max_concurrency: int
    expensive_rpm: int
    mutating_rpm: int
    identity_rpm: int


# Default Tier Entitlements & Rate-Limiting Quotas
DEFAULT_TIER_QUOTAS: Dict[str, TenantQuotaConfig] = {
    "FREE": TenantQuotaConfig(
        tier="FREE",
        requests_per_minute=60,
        max_concurrency=1,
        expensive_rpm=10,
        mutating_rpm=30,
        identity_rpm=60,
    ),
    "STARTER": TenantQuotaConfig(
        tier="STARTER",
        requests_per_minute=300,
        max_concurrency=3,
        expensive_rpm=30,
        mutating_rpm=120,
        identity_rpm=120,
    ),
    "PRO": TenantQuotaConfig(
        tier="PRO",
        requests_per_minute=1200,
        max_concurrency=10,
        expensive_rpm=60,
        mutating_rpm=300,
        identity_rpm=300,
    ),
    "ENTERPRISE": TenantQuotaConfig(
        tier="ENTERPRISE",
        requests_per_minute=3600,
        max_concurrency=50,
        expensive_rpm=180,
        mutating_rpm=600,
        identity_rpm=600,
    ),
}

# Expensive operations requiring specialized sub-limits
EXPENSIVE_ENDPOINTS = {
    "/api/overview/explain-variance",
    "/api/v1/neon/ai/chat",
    "/api/ai/chat",
    "/api/reports/generate",
    "/api/automation/agent/generate",
    "/api/v1/zonata/org-design/generate",
    "/api/briefing",
}

# Endpoints exempt from tenant and identity rate limits
EXEMPT_ENDPOINTS = {
    "/readyz",
    "/healthz",
    "/livez",
    "/health",
    "/metrics",
    "/api/v1/health",
}


class ConcurrencyLeaseManager:
    """
    Tracks and enforces concurrent execution quotas (workflows, agent missions, AI jobs)
    per tenant across multi-process and multi-instance deployments.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._memory_leases: Dict[str, Tuple[str, str, float]] = {}  # lease_id -> (tenant_id, type, expires_at)

    def acquire_lease(
        self,
        tenant_id: str,
        max_concurrency: int,
        lease_type: str = "WORKFLOW",
        ttl_seconds: float = 300.0,
    ) -> Tuple[bool, Optional[str], int]:
        """
        Attempts to acquire a concurrency lease for a tenant.
        Returns: (acquired: bool, lease_id: Optional[str], retry_after: int)
        """
        now = time.time()
        lease_id = f"lease_{uuid.uuid4().hex[:12]}"
        expires_at = now + ttl_seconds

        # 1. Database-backed acquisition (Shared across Render / Neon instances)
        try:
            with db.get_connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                except Exception:
                    pass

                # Purge expired leases for this tenant
                conn.execute(
                    "DELETE FROM tenant_concurrency_leases WHERE tenant_id = ? AND expires_at < ?",
                    (tenant_id, now),
                )

                # Query active leases for this tenant
                rows = conn.execute(
                    "SELECT expires_at FROM tenant_concurrency_leases WHERE tenant_id = ? AND expires_at >= ? ORDER BY expires_at ASC",
                    (tenant_id, now),
                ).fetchall()

                active_count = len(rows)
                if active_count >= max_concurrency:
                    earliest_expiry = rows[0][0] if isinstance(rows[0], (tuple, list)) else rows[0]["expires_at"]
                    retry_after = max(1, int(earliest_expiry - now) + 1)
                    conn.commit()
                    return False, None, retry_after

                # Insert lease
                conn.execute(
                    """
                    INSERT INTO tenant_concurrency_leases (lease_id, tenant_id, lease_type, acquired_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (lease_id, tenant_id, lease_type, now, expires_at),
                )
                conn.commit()
                return True, lease_id, 0
        except Exception as e:
            logger.warning(f"Database lease acquisition fallback to in-memory: {e}")

        # 2. In-memory fallback
        with self._lock:
            # Clean expired
            active_leases = [
                (lid, tid, ltype, exp)
                for lid, (tid, ltype, exp) in self._memory_leases.items()
                if exp >= now and tid == tenant_id
            ]
            if len(active_leases) >= max_concurrency:
                earliest_expiry = min(item[3] for item in active_leases)
                retry_after = max(1, int(earliest_expiry - now) + 1)
                return False, None, retry_after

            self._memory_leases[lease_id] = (tenant_id, lease_type, expires_at)
            return True, lease_id, 0

    def release_lease(self, lease_id: Optional[str]) -> bool:
        """Releases an active concurrency lease."""
        if not lease_id:
            return False

        released = False
        try:
            with db.get_connection() as conn:
                cur = conn.execute("DELETE FROM tenant_concurrency_leases WHERE lease_id = ?", (lease_id,))
                conn.commit()
                if cur.rowcount > 0:
                    released = True
        except Exception:
            pass

        with self._lock:
            if lease_id in self._memory_leases:
                del self._memory_leases[lease_id]
                released = True

        return released

    @contextmanager
    def lease(self, tenant_id: str, max_concurrency: int, lease_type: str = "WORKFLOW", ttl_seconds: float = 300.0):
        """Context manager for acquiring and safely releasing a concurrency lease."""
        ok, lease_id, retry_after = self.acquire_lease(tenant_id, max_concurrency, lease_type, ttl_seconds)
        if not ok:
            from core.auth import AuthExceptions
            raise RuntimeError(f"Tenant concurrency limit exceeded. Retry after {retry_after}s.")
        try:
            yield lease_id
        finally:
            self.release_lease(lease_id)


class TenantFairnessEngine:
    """
    Centralized rate limiting and tenant fairness engine enforcing multi-tier quotas,
    sliding-window tracking, and abuse prevention across the ZONATA SaaS platform.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._memory_records: Dict[str, List[float]] = {}
        self.concurrency_manager = ConcurrencyLeaseManager()
        self._tier_cache: Dict[str, Tuple[TenantQuotaConfig, float]] = {}  # tenant_id -> (config, cached_at)

    def _check_sliding_window(
        self,
        rate_key: str,
        max_requests: int,
        window_seconds: float = 60.0,
    ) -> Tuple[bool, int, int]:
        """
        Atomic sliding window implementation backed by PostgreSQL / SQLite table `tenant_rate_limits`.
        Returns: (allowed: bool, remaining: int, retry_after: int)
        """
        now = time.time()
        window_start = now - window_seconds

        # 1. Database-backed distributed sliding window
        try:
            with db.get_connection() as conn:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                except Exception:
                    pass

                # Scoped pruning for THIS rate_key
                conn.execute(
                    "DELETE FROM tenant_rate_limits WHERE rate_key = ? AND attempt_timestamp < ?",
                    (rate_key, window_start),
                )

                # Count active events in current window
                rows = conn.execute(
                    "SELECT attempt_timestamp FROM tenant_rate_limits WHERE rate_key = ? AND attempt_timestamp >= ? ORDER BY attempt_timestamp ASC",
                    (rate_key, window_start),
                ).fetchall()

                count = len(rows)
                if count >= max_requests:
                    oldest = rows[0][0] if isinstance(rows[0], (tuple, list)) else rows[0]["attempt_timestamp"]
                    retry_after = max(1, int(window_seconds - (now - oldest)) + 1)
                    conn.commit()
                    return False, 0, retry_after

                # Record current request attempt
                conn.execute(
                    "INSERT INTO tenant_rate_limits (rate_key, attempt_timestamp) VALUES (?, ?)",
                    (rate_key, now),
                )

                # Probabilistic table cleanup (1 in 50 calls) to prevent table accumulation
                if random.random() < 0.02:
                    conn.execute(
                        "DELETE FROM tenant_rate_limits WHERE attempt_timestamp < ?",
                        (now - 3600.0,),
                    )

                conn.commit()
                remaining = max(0, max_requests - (count + 1))
                return True, remaining, 0
        except Exception as e:
            logger.debug(f"Database sliding window fallback to in-memory: {e}")

        # 2. Thread-safe in-memory sliding window fallback
        with self._lock:
            timestamps = self._memory_records.get(rate_key, [])
            valid_timestamps = [t for t in timestamps if t >= window_start]
            if len(valid_timestamps) >= max_requests:
                self._memory_records[rate_key] = valid_timestamps
                retry_after = max(1, int(window_seconds - (now - valid_timestamps[0])) + 1)
                return False, 0, retry_after

            valid_timestamps.append(now)
            self._memory_records[rate_key] = valid_timestamps

            # Memory bound: periodically prune keys
            if len(self._memory_records) > 5000:
                self._prune_memory_records(now)

            remaining = max(0, max_requests - len(valid_timestamps))
            return True, remaining, 0

    def _prune_memory_records(self, now: float):
        """Purges stale keys from in-memory fallback dictionary."""
        cutoff = now - 3600.0
        keys_to_delete = [
            k for k, v in self._memory_records.items()
            if not v or v[-1] < cutoff
        ]
        for k in keys_to_delete:
            del self._memory_records[k]

    def get_tenant_quota(self, tenant_id: str) -> TenantQuotaConfig:
        """
        Retrieves the quota configuration for a given tenant, resolving their commercial plan tier.
        """
        now = time.time()
        # Check cache (15s TTL)
        cached = self._tier_cache.get(tenant_id)
        if cached and (now - cached[1] < 15.0):
            return cached[0]

        plan_tier = "ENTERPRISE"
        try:
            with db.get_connection() as conn:
                row = conn.execute("SELECT plan FROM tenants WHERE tenant_id = ?", (tenant_id,)).fetchone()
                if row:
                    raw_plan = row[0] if isinstance(row, (tuple, list)) else row["plan"]
                    plan_tier = str(raw_plan).strip().upper()
        except Exception:
            pass

        # Environment-level override for testing or emergency maintenance
        env_override = os.environ.get("ZONATA_TENANT_RATE_LIMIT_OVERRIDE")
        if env_override and env_override.upper() in DEFAULT_TIER_QUOTAS:
            plan_tier = env_override.upper()

        config = DEFAULT_TIER_QUOTAS.get(plan_tier, DEFAULT_TIER_QUOTAS["FREE"])
        self._tier_cache[tenant_id] = (config, now)
        return config

    def evaluate_request(
        self,
        path: str,
        method: str,
        client_ip: str,
        auth_context: Optional[Dict[str, Any]] = None,
    ) -> RateLimitDecision:
        """
        Hierarchical rate limit evaluation across IP, Tenant, Identity, and Endpoint dimensions.
        """
        # Safety escape hatch for emergency admin disable or unit testing
        if os.environ.get("ZONATA_DISABLE_RATE_LIMITING", "0") == "1":
            return RateLimitDecision(is_allowed=True, status_code=200, limit=99999, remaining=99999)

        # 0. Check exemption
        if path in EXEMPT_ENDPOINTS or path.startswith("/assets/") or path.endswith((".css", ".js", ".png", ".ico")):
            return RateLimitDecision(is_allowed=True, status_code=200, limit=99999, remaining=99999)

        now = time.time()
        reset_time = int(now + 60.0)

        # 1. Layer 1: Anonymous & IP Perimeter Rate Limiting
        # Sensitive public authentication endpoints have tight per-IP bounds
        is_auth_login = path in ("/api/auth/token", "/api/auth/login")
        is_auth_register = (path == "/api/auth/register")

        if is_auth_login:
            ip_limit = int(os.environ.get("ZONATA_RATE_LIMIT_LOGIN_IP", "25"))
            ip_key = f"rl:auth_login:ip:{client_ip}"
        elif is_auth_register:
            ip_limit = int(os.environ.get("ZONATA_RATE_LIMIT_REGISTER_IP", "10"))
            ip_key = f"rl:auth_register:ip:{client_ip}"
        else:
            ip_limit = int(os.environ.get("ZONATA_RATE_LIMIT_GLOBAL_IP", "1200"))
            ip_key = f"rl:global:ip:{client_ip}"

        allowed, remaining, retry_after = self._check_sliding_window(ip_key, max_requests=ip_limit, window_seconds=60.0)
        if not allowed:
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(ip_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "X-RateLimit-Axis": RateLimitAxis.IP.value,
            }
            return RateLimitDecision(
                is_allowed=False,
                status_code=429,
                limit=ip_limit,
                remaining=0,
                retry_after=retry_after,
                violation_axis=RateLimitAxis.IP.value,
                detail=f"Too Many Requests: IP rate limit exceeded ({ip_limit} requests/min). Try again in {retry_after}s.",
                headers=headers,
            )

        # If unauthenticated, IP evaluation is the terminal gate
        if not auth_context:
            headers = {
                "X-RateLimit-Limit": str(ip_limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            }
            return RateLimitDecision(is_allowed=True, status_code=200, limit=ip_limit, remaining=remaining, headers=headers)

        # 2. Layer 2: Tenant-Level Fairness Quota
        tenant_id = auth_context.get("tenant_id")
        if not tenant_id:
            # Fall back to IP limit if no tenant_id present
            return RateLimitDecision(is_allowed=True, status_code=200, limit=ip_limit, remaining=remaining)

        quota_cfg = self.get_tenant_quota(tenant_id)
        tenant_key = f"rl:tenant:{tenant_id}"
        t_allowed, t_remaining, t_retry = self._check_sliding_window(
            tenant_key,
            max_requests=quota_cfg.requests_per_minute,
            window_seconds=60.0,
        )

        if not t_allowed:
            headers = {
                "Retry-After": str(t_retry),
                "X-RateLimit-Limit": str(quota_cfg.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "X-RateLimit-Axis": RateLimitAxis.TENANT.value,
            }
            return RateLimitDecision(
                is_allowed=False,
                status_code=429,
                limit=quota_cfg.requests_per_minute,
                remaining=0,
                retry_after=t_retry,
                violation_axis=RateLimitAxis.TENANT.value,
                detail=f"Rate limit exceeded for tenant quota ({quota_cfg.requests_per_minute} requests/min). Try again in {t_retry}s.",
                headers=headers,
            )

        # 3. Layer 3: Identity-Level Fairness (Per User Within Tenant)
        user_id = auth_context.get("user_id", "usr_default")
        user_key = f"rl:user:{tenant_id}:{user_id}"
        u_allowed, u_remaining, u_retry = self._check_sliding_window(
            user_key,
            max_requests=quota_cfg.identity_rpm,
            window_seconds=60.0,
        )

        if not u_allowed:
            headers = {
                "Retry-After": str(u_retry),
                "X-RateLimit-Limit": str(quota_cfg.identity_rpm),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time),
                "X-RateLimit-Axis": RateLimitAxis.IDENTITY.value,
            }
            return RateLimitDecision(
                is_allowed=False,
                status_code=429,
                limit=quota_cfg.identity_rpm,
                remaining=0,
                retry_after=u_retry,
                violation_axis=RateLimitAxis.IDENTITY.value,
                detail=f"Rate limit exceeded for user quota ({quota_cfg.identity_rpm} requests/min). Try again in {u_retry}s.",
                headers=headers,
            )

        # 4. Layer 4: Endpoint-Specific Protection
        # Expensive operations (AI, report generation, analytics)
        if path in EXPENSIVE_ENDPOINTS or path.startswith("/api/v1/neon/ai/"):
            exp_key = f"rl:expensive:{tenant_id}"
            e_allowed, e_remaining, e_retry = self._check_sliding_window(
                exp_key,
                max_requests=quota_cfg.expensive_rpm,
                window_seconds=60.0,
            )
            if not e_allowed:
                headers = {
                    "Retry-After": str(e_retry),
                    "X-RateLimit-Limit": str(quota_cfg.expensive_rpm),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "X-RateLimit-Axis": RateLimitAxis.ENDPOINT.value,
                }
                return RateLimitDecision(
                    is_allowed=False,
                    status_code=429,
                    limit=quota_cfg.expensive_rpm,
                    remaining=0,
                    retry_after=e_retry,
                    violation_axis=RateLimitAxis.ENDPOINT.value,
                    detail=f"Rate limit exceeded for resource-intensive operations ({quota_cfg.expensive_rpm} requests/min). Try again in {e_retry}s.",
                    headers=headers,
                )

        # Mutating operations
        if method.upper() in ("POST", "PUT", "DELETE", "PATCH") and not (is_auth_login or is_auth_register):
            mut_key = f"rl:mutating:{tenant_id}"
            m_allowed, m_remaining, m_retry = self._check_sliding_window(
                mut_key,
                max_requests=quota_cfg.mutating_rpm,
                window_seconds=60.0,
            )
            if not m_allowed:
                headers = {
                    "Retry-After": str(m_retry),
                    "X-RateLimit-Limit": str(quota_cfg.mutating_rpm),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "X-RateLimit-Axis": RateLimitAxis.ENDPOINT.value,
                }
                return RateLimitDecision(
                    is_allowed=False,
                    status_code=429,
                    limit=quota_cfg.mutating_rpm,
                    remaining=0,
                    retry_after=m_retry,
                    violation_axis=RateLimitAxis.ENDPOINT.value,
                    detail=f"Rate limit exceeded for mutating operations ({quota_cfg.mutating_rpm} requests/min). Try again in {m_retry}s.",
                    headers=headers,
                )

        # All layers passed
        min_remaining = min(remaining, t_remaining, u_remaining)
        headers = {
            "X-RateLimit-Limit": str(quota_cfg.requests_per_minute),
            "X-RateLimit-Remaining": str(min_remaining),
            "X-RateLimit-Reset": str(reset_time),
        }
        return RateLimitDecision(
            is_allowed=True,
            status_code=200,
            limit=quota_cfg.requests_per_minute,
            remaining=min_remaining,
            headers=headers,
        )


# Global singleton engine
tenant_fairness_engine = TenantFairnessEngine()
