"""
ZONATA Governed Browser — HTTP Rate Limiting & Governed Back-off (Rule 25).

Enforces Rule 25:
"Back-off on HTTP 429/503/403 with exponential jittered retry up to budget,
never rotating IPs to evade."
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from core.security.anti_evasion import AntiEvasionViolationError

T = TypeVar("T")


@dataclass
class BackoffBudget:
    max_retries: int = 4
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    total_timeout_seconds: float = 60.0
    current_attempt: int = 0
    elapsed_time_seconds: float = 0.0


class GovernedRateLimiter:
    """
    Enforces exponential jittered backoff on rate limit or server busy responses (429, 503, 403).
    Strictly forbids IP/proxy rotation to bypass rate limits.
    """

    def __init__(self, budget: Optional[BackoffBudget] = None):
        self.budget = budget or BackoffBudget()
        self._proxy_address: Optional[str] = None

    def set_egress_proxy(self, proxy_address: Optional[str]) -> None:
        """Set initial egress proxy if configured."""
        self._proxy_address = proxy_address

    def request_proxy_rotation(self, new_proxy_address: str) -> None:
        """
        Refuse any attempt to rotate egress proxies or IP addresses to evade rate limits (Rule 25).
        """
        raise AntiEvasionViolationError(
            "Proxy/IP rotation to evade rate limits or bot blocks is strictly prohibited by Rule 25."
        )

    def calculate_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """
        Calculate full jitter exponential delay:
        delay = min(max_delay, base_delay * 2^attempt) * random.uniform(0.5, 1.5)
        Respects Retry-After header if provided and within budget.
        """
        if retry_after is not None and retry_after > 0:
            raw_delay = min(retry_after, self.budget.max_delay_seconds)
        else:
            raw_delay = min(
                self.budget.max_delay_seconds,
                self.budget.base_delay_seconds * (2 ** attempt),
            )
        # Apply jitter (50% to 150%)
        jitter = random.uniform(0.5, 1.5)
        return raw_delay * jitter

    def should_retry(self, status_code: int) -> bool:
        """Check if HTTP status code warrants backoff retry."""
        return status_code in (429, 503, 403)

    def execute_with_backoff(
        self,
        operation: Callable[[], T],
        on_retry: Optional[Callable[[int, float], None]] = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> T:
        """
        Execute an operation with governed back-off.
        Fails closed when budget is exhausted.
        """
        attempt = 0
        start_time = time.time()

        while True:
            try:
                return operation()
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code is None and hasattr(exc, "code"):
                    status_code = getattr(exc, "code")

                if not (status_code and self.should_retry(status_code)):
                    raise

                attempt += 1
                if attempt > self.budget.max_retries:
                    raise TimeoutError(
                        f"Rate limit retry budget exhausted ({self.budget.max_retries} attempts) for status {status_code}."
                    ) from exc

                elapsed = time.time() - start_time
                if elapsed >= self.budget.total_timeout_seconds:
                    raise TimeoutError(
                        f"Rate limit timeout budget exhausted ({self.budget.total_timeout_seconds}s) for status {status_code}."
                    ) from exc

                retry_after = getattr(exc, "retry_after", None)
                delay = self.calculate_delay(attempt, retry_after=retry_after)

                # Cap delay to remaining time budget
                remaining_time = self.budget.total_timeout_seconds - elapsed
                delay = min(delay, remaining_time)

                if on_retry:
                    on_retry(attempt, delay)

                sleeper(delay)
