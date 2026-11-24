"""
Multi-Tenant Noisy-Neighbor Isolation and Concurrency Governor (Rule 68 & ADR 0044)
Enforces token-bucket rate limiting per tenant. Guarantees that aggressive tenant traffic
cannot exhaust cluster capacity or starve adjacent tenants sharing the cluster.
"""

from typing import Dict, Any, Optional
import time


class RateLimitExceededError(Exception):
    """Raised when a tenant exhausts their allocated concurrency or rate limits."""
    pass


class TokenBucket:
    """Individual tenant rate limiter using token-bucket algorithm."""

    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.tokens = capacity
        self.last_refill = time.monotonic()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + (elapsed * self.refill_rate))
        self.last_refill = now

    def acquire(self, tokens: float = 1.0) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class ConcurrencyGovernor:
    """Multi-tenant concurrency and throughput governor ensuring noisy-neighbor isolation."""

    def __init__(self, default_capacity: float = 50.0, default_refill_rate: float = 20.0):
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: Dict[str, TokenBucket] = {}
        self._throttled_counts: Dict[str, int] = {}
        self._admitted_counts: Dict[str, int] = {}

    def _get_bucket(self, tenant_id: str) -> TokenBucket:
        if tenant_id not in self._buckets:
            self._buckets[tenant_id] = TokenBucket(self.default_capacity, self.default_refill_rate)
            self._throttled_counts[tenant_id] = 0
            self._admitted_counts[tenant_id] = 0
        return self._buckets[tenant_id]

    def try_admit_request(self, tenant_id: str, cost: float = 1.0) -> bool:
        """Attempts to admit request for tenant. Returns True if admitted, False if throttled."""
        bucket = self._get_bucket(tenant_id)
        if bucket.acquire(cost):
            self._admitted_counts[tenant_id] += 1
            return True
        else:
            self._throttled_counts[tenant_id] += 1
            return False

    def admit_or_raise(self, tenant_id: str, cost: float = 1.0):
        """Admits request or raises RateLimitExceededError."""
        if not self.try_admit_request(tenant_id, cost):
            raise RateLimitExceededError(
                f"RATE_LIMIT_EXCEEDED: Tenant '{tenant_id}' exceeded concurrency burst limit. "
                f"Request throttled to protect shared cluster stability (Rule 68)."
            )

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, int]:
        return {
            "admitted": self._admitted_counts.get(tenant_id, 0),
            "throttled": self._throttled_counts.get(tenant_id, 0),
        }
