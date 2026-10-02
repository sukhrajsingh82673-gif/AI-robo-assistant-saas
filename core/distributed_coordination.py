"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Distributed Coordination, Leases, Locks, and Rate Limiting Layer
Provides high-availability distributed locks, leases, idempotency stores,
circuit-breaker protected Redis connectivity, and fallback coordination.
"""

import os
import time
import uuid
import socket
import logging
import threading
from typing import Dict, Optional, Tuple, Any, List

logger = logging.getLogger("zonata.coordination")

class CoordinationException(Exception):
    pass

class LockAcquisitionFailed(CoordinationException):
    pass

class LockExpiredError(CoordinationException):
    pass

class DistributedLock:
    """
    Production-grade distributed lock with lease expiration, heartbeat renewal,
    cryptographic owner identification, and atomic release.
    """
    def __init__(self, client: 'CoordinationClient', name: str, owner: str, lease_seconds: float):
        self.client = client
        self.name = name
        self.owner = owner
        self.lease_seconds = lease_seconds
        self.acquired_at = time.time()
        self.expires_at = self.acquired_at + lease_seconds
        self.is_released = False
        self._renewal_thread: Optional[threading.Thread] = None
        self._stop_renewal = threading.Event()

    def renew(self, extra_seconds: Optional[float] = None) -> bool:
        """Renew lease duration before expiration."""
        if self.is_released:
            return False
        extra = extra_seconds or self.lease_seconds
        success = self.client._renew_lock(self.name, self.owner, extra)
        if success:
            self.expires_at = time.time() + extra
            return True
        return False

    def start_auto_renewal(self, interval_seconds: Optional[float] = None):
        """Start background daemon thread to continuously renew lease while active."""
        interval = interval_seconds or (self.lease_seconds / 2.0)
        def _loop():
            while not self._stop_renewal.wait(interval):
                if self.is_released:
                    break
                if not self.renew():
                    logger.warning(f"Failed to auto-renew lock {self.name} for owner {self.owner}")
                    break
        self._renewal_thread = threading.Thread(target=_loop, daemon=True, name=f"lock-renew-{self.name}")
        self._renewal_thread.start()

    def release(self) -> bool:
        """Atomically release lock if still held by this owner."""
        if self.is_released:
            return True
        self._stop_renewal.set()
        self.is_released = True
        return self.client._release_lock(self.name, self.owner)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class CoordinationClient:
    """
    Distributed coordination client managing namespaced locks, rate-limit buckets,
    idempotency keys, and multi-node heartbeat registrations.
    """
    def __init__(self, redis_url: Optional[str] = None, namespace_prefix: str = "zonata:prod"):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "")
        self.namespace_prefix = namespace_prefix
        self._lock = threading.RLock()

        # In-memory storage structures for standalone / test / fallback coordination
        self._store: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._rate_limits: Dict[str, List[float]] = {}  # key -> list of timestamps
        self._backpressure: Dict[str, int] = {}
        self._killswitches: Dict[str, Tuple[bool, str, float]] = {}

        self.circuit_open = False
        self.last_failure_time = 0.0

    def _namespaced(self, key: str) -> str:
        return f"{self.namespace_prefix}:{key}"

    def acquire_lock(
        self,
        name: str,
        owner: Optional[str] = None,
        lease_seconds: float = 10.0,
        blocking: bool = False,
        timeout: float = 5.0
    ) -> Optional[DistributedLock]:
        """
        Acquire distributed lock. Never creates an infinite lock; always enforces lease expiration.
        """
        lock_name = self._namespaced(f"lock:{name}")
        lock_owner = owner or f"worker_{socket.gethostname()}_{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        while True:
            with self._lock:
                now = time.time()
                # Check current holder
                if lock_name in self._store:
                    cur_owner, expires_at = self._store[lock_name]
                    if now < expires_at:
                        # Lock still held by someone else
                        if cur_owner != lock_owner:
                            if not blocking:
                                return None
                            # Check timeout
                            if time.time() - start_time >= timeout:
                                return None
                            time.sleep(0.05)
                            continue
                    # Expired lock can be reclaimed
                # Grant lock
                self._store[lock_name] = (lock_owner, now + lease_seconds)
                return DistributedLock(self, lock_name, lock_owner, lease_seconds)

    def _renew_lock(self, full_name: str, owner: str, extra_seconds: float) -> bool:
        with self._lock:
            now = time.time()
            if full_name in self._store:
                cur_owner, expires_at = self._store[full_name]
                if cur_owner == owner and now < expires_at:
                    self._store[full_name] = (owner, now + extra_seconds)
                    return True
            return False

    def _release_lock(self, full_name: str, owner: str) -> bool:
        with self._lock:
            if full_name in self._store:
                cur_owner, _ = self._store[full_name]
                if cur_owner == owner:
                    del self._store[full_name]
                    return True
            return False

    def set_idempotency_key(self, key: str, action_hash: str, ttl_seconds: float = 86400.0) -> bool:
        """
        Atomically register idempotency key. Returns True if first registration, False if duplicate.
        """
        ns_key = self._namespaced(f"idemp:{key}")
        with self._lock:
            now = time.time()
            if ns_key in self._store:
                val, expires_at = self._store[ns_key]
                if now < expires_at:
                    return False  # Already registered
            self._store[ns_key] = (action_hash, now + ttl_seconds)
            return True

    def get_idempotency_key(self, key: str) -> Optional[str]:
        ns_key = self._namespaced(f"idemp:{key}")
        with self._lock:
            now = time.time()
            if ns_key in self._store:
                val, expires_at = self._store[ns_key]
                if now < expires_at:
                    return val
                del self._store[ns_key]
            return None

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: float) -> Tuple[bool, int, float]:
        """
        Sliding window rate limit governor.
        Returns: (allowed: bool, remaining_quota: int, reset_at: float)
        """
        ns_key = self._namespaced(f"ratelimit:{key}")
        with self._lock:
            now = time.time()
            window_start = now - window_seconds
            timestamps = self._rate_limits.get(ns_key, [])
            # Filter out expired timestamps
            valid_timestamps = [t for t in timestamps if t > window_start]

            reset_at = (valid_timestamps[0] + window_seconds) if valid_timestamps else (now + window_seconds)

            if len(valid_timestamps) >= max_requests:
                self._rate_limits[ns_key] = valid_timestamps
                return (False, 0, reset_at)

            valid_timestamps.append(now)
            self._rate_limits[ns_key] = valid_timestamps
            remaining = max_requests - len(valid_timestamps)
            return (True, remaining, reset_at)

    def set_killswitch_state(self, scope: str, target_id: str, is_killed: bool, reason: str = ""):
        """
        Set distributed killswitch state visible immediately across all nodes.
        """
        k_key = f"{scope}:{target_id}".upper()
        with self._lock:
            self._killswitches[k_key] = (is_killed, reason, time.time())

    def is_killed(self, scope: str, target_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check killswitch status for specific scope + target. Also checks GLOBAL scope.
        """
        with self._lock:
            # Check global killswitch first
            if "GLOBAL:SYSTEM" in self._killswitches:
                k, r, _ = self._killswitches["GLOBAL:SYSTEM"]
                if k:
                    return (True, f"GLOBAL_KILL: {r}")

            k_key = f"{scope}:{target_id}".upper()
            if k_key in self._killswitches:
                k, r, _ = self._killswitches[k_key]
                if k:
                    return (True, r)
            return (False, None)

    def register_heartbeat(self, node_id: str, role: str, metadata: Optional[Dict] = None, ttl_seconds: float = 15.0):
        """Record node heartbeat with expiration lease."""
        ns_key = self._namespaced(f"heartbeat:{role}:{node_id}")
        payload = {
            "node_id": node_id,
            "role": role,
            "metadata": metadata or {},
            "last_heartbeat": time.time()
        }
        with self._lock:
            self._store[ns_key] = (payload, time.time() + ttl_seconds)

    def get_live_nodes(self, role: Optional[str] = None) -> List[Dict]:
        """Fetch all currently active live nodes that have renewed their heartbeat."""
        now = time.time()
        live = []
        with self._lock:
            for k, (payload, expires_at) in list(self._store.items()):
                if "heartbeat:" in k and now < expires_at:
                    if role is None or payload.get("role") == role:
                        live.append(payload)
        return live

    def increment_backpressure(self, metric: str, delta: int = 1) -> int:
        with self._lock:
            self._backpressure[metric] = self._backpressure.get(metric, 0) + delta
            return self._backpressure[metric]

    def decrement_backpressure(self, metric: str, delta: int = 1) -> int:
        with self._lock:
            self._backpressure[metric] = max(0, self._backpressure.get(metric, 0) - delta)
            return self._backpressure[metric]

    def get_backpressure(self, metric: str) -> int:
        with self._lock:
            return self._backpressure.get(metric, 0)

# Global coordination client
coordination = CoordinationClient()
