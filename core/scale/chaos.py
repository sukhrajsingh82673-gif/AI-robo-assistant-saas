"""
Chaos Injection and Idempotency Recovery Runner (Rule 76 & ADR 0044)
Simulates transient network partitions, pool exhaustion, and transport disconnects.
Verifies retry backoff and idempotency key deduplication to prevent duplicate ledger postings.
"""

from typing import Dict, Any, List, Optional, Callable
import time
import hashlib


class TransientNetworkGlitchError(IOError):
    """Simulated transient network dropout."""
    pass


class ChaosInjector:
    """Injects controlled failures into execution pipelines."""

    def __init__(self, failure_probability: float = 0.5, max_failures: int = 2):
        self.failure_probability = failure_probability
        self.max_failures = max_failures
        self.failures_injected = 0

    def maybe_fail(self):
        """Simulates transient outage until max_failures reached."""
        if self.failures_injected < self.max_failures:
            self.failures_injected += 1
            raise TransientNetworkGlitchError(
                f"CHAOS_INJECTED: Transient transport partition (fault #{self.failures_injected})"
            )


class IdempotentRetryRunner:
    """Executes business transactions with exponential backoff and deduplication caching."""

    def __init__(self, max_retries: int = 3, base_backoff_ms: float = 10.0):
        self.max_retries = max_retries
        self.base_backoff_ms = base_backoff_ms
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}

    def execute_idempotent_operation(
        self,
        idempotency_key: str,
        operation: Callable[[], Dict[str, Any]],
        chaos_injector: Optional[ChaosInjector] = None,
    ) -> Dict[str, Any]:
        """
        Executes operation. If idempotency_key has already been committed, returns cached result
        immediately without re-executing. If a transient failure occurs, retries with backoff.
        """
        # Deduplication check
        if idempotency_key in self._idempotency_cache:
            cached = self._idempotency_cache[idempotency_key].copy()
            cached["cached_replay"] = True
            return cached

        attempts = 0
        while attempts <= self.max_retries:
            attempts += 1
            try:
                if chaos_injector:
                    chaos_injector.maybe_fail()

                # Execute operation
                result = operation()
                result["attempts_required"] = attempts
                result["cached_replay"] = False
                self._idempotency_cache[idempotency_key] = result
                return result
            except TransientNetworkGlitchError as e:
                if attempts > self.max_retries:
                    raise
                # Exponential backoff (simulated short sleep)
                sleep_s = (self.base_backoff_ms * (2 ** (attempts - 1))) / 1000.0
                time.sleep(min(0.1, sleep_s))

        raise RuntimeError("Unreachable")
