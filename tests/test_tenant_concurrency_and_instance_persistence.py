"""
ZONATA Enterprise SaaS — Rate Limiting & Concurrency Lease Persistence Suite
Verifies:
1. Distributed concurrency lease coordination across independent manager instances
2. Lease persistence and enforcement across simulated application restarts
3. Automatic eviction of expired leases across process restarts
4. Simultaneous multi-threaded race conditions enforcing exact tenant concurrency ceilings
5. Sliding-window rate limit state persistence across application instances
"""

import os
import sys
import time
import uuid
import unittest
import concurrent.futures
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tenant_fairness import (
    ConcurrencyLeaseManager,
    TenantFairnessEngine,
    TenantQuotaConfig,
    RateLimitAxis
)
from core.db import db


class TestTenantConcurrencyAndInstancePersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure schema tables exist
        with db.get_connection() as conn:
            try:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_concurrency_leases (
                    lease_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    lease_type TEXT NOT NULL,
                    acquired_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS tenant_rate_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rate_key TEXT NOT NULL,
                    attempt_timestamp REAL NOT NULL
                );
                """)
                conn.commit()
            except Exception:
                pass

    def setUp(self):
        self.tenant_id = f"tnt_test_{uuid.uuid4().hex[:8]}"

    def tearDown(self):
        with db.get_connection() as conn:
            try:
                conn.execute("DELETE FROM tenant_concurrency_leases WHERE tenant_id = ?", (self.tenant_id,))
                conn.execute("DELETE FROM tenant_rate_limits WHERE rate_key LIKE ?", (f"%{self.tenant_id}%",))
                conn.commit()
            except Exception:
                pass

    def test_01_multi_instance_concurrency_lease_synchronization(self):
        """Two distinct manager instances must coordinate and enforce quotas via shared DB."""
        instance_a = ConcurrencyLeaseManager()
        instance_b = ConcurrencyLeaseManager()

        max_concurrency = 2
        # Instance A acquires 2 leases (filling capacity)
        ok1, lease1, _ = instance_a.acquire_lease(self.tenant_id, max_concurrency=max_concurrency)
        self.assertTrue(ok1)
        self.assertIsNotNone(lease1)

        ok2, lease2, _ = instance_a.acquire_lease(self.tenant_id, max_concurrency=max_concurrency)
        self.assertTrue(ok2)
        self.assertIsNotNone(lease2)

        # Instance B (separate instance) attempts 3rd lease -> must be denied
        ok3, lease3, retry_after = instance_b.acquire_lease(self.tenant_id, max_concurrency=max_concurrency)
        self.assertFalse(ok3)
        self.assertIsNone(lease3)
        self.assertGreater(retry_after, 0)

        # Instance A releases 1 lease
        rel_ok = instance_a.release_lease(lease1)
        self.assertTrue(rel_ok)

        # Instance B can now acquire the freed lease slot
        ok4, lease4, _ = instance_b.acquire_lease(self.tenant_id, max_concurrency=max_concurrency)
        self.assertTrue(ok4)
        self.assertIsNotNone(lease4)

        # Clean up
        instance_a.release_lease(lease2)
        instance_b.release_lease(lease4)

    def test_02_lease_persistence_across_process_restart(self):
        """Active leases must survive an application process crash/restart."""
        # Simulated Process 1
        proc_1 = ConcurrencyLeaseManager()
        ok, lease_id, _ = proc_1.acquire_lease(self.tenant_id, max_concurrency=1, ttl_seconds=60.0)
        self.assertTrue(ok)

        # Process 1 terminates (simulated by deleting instance)
        del proc_1

        # Simulated Process 2 starts up
        proc_2 = ConcurrencyLeaseManager()
        # Tenant should still be blocked because active lease exists in DB
        ok_blocked, _, retry_after = proc_2.acquire_lease(self.tenant_id, max_concurrency=1)
        self.assertFalse(ok_blocked)
        self.assertGreater(retry_after, 0)

        # Process 2 releases the lease
        released = proc_2.release_lease(lease_id)
        self.assertTrue(released)

        # Tenant can now acquire
        ok_new, new_lease, _ = proc_2.acquire_lease(self.tenant_id, max_concurrency=1)
        self.assertTrue(ok_new)
        proc_2.release_lease(new_lease)

    def test_03_expired_lease_automatic_eviction_on_restart(self):
        """Expired leases must be evicted on the next acquisition attempt after restart."""
        proc_1 = ConcurrencyLeaseManager()
        # Acquire short-lived lease (1.0 second TTL)
        ok, lease_id, _ = proc_1.acquire_lease(self.tenant_id, max_concurrency=1, ttl_seconds=1.0)
        self.assertTrue(ok)
        del proc_1

        # Wait for lease to expire
        time.sleep(1.2)

        # Process 2 starts up and tries to acquire
        proc_2 = ConcurrencyLeaseManager()
        ok_after_expire, new_lease_id, _ = proc_2.acquire_lease(self.tenant_id, max_concurrency=1)
        self.assertTrue(ok_after_expire, "Expired lease was not automatically evicted!")
        self.assertNotEqual(lease_id, new_lease_id)

        proc_2.release_lease(new_lease_id)

    def test_04_simultaneous_race_condition_concurrency_ceiling(self):
        """Simultaneous competing threads must strictly adhere to tenant ceiling."""
        manager = ConcurrencyLeaseManager()
        max_concurrency = 3
        num_threads = 10

        results: List[Tuple[bool, str]] = []

        def worker():
            ok, lid, _ = manager.acquire_lease(self.tenant_id, max_concurrency=max_concurrency, ttl_seconds=30.0)
            return (ok, lid)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        successful = [r for r in results if r[0] is True]
        rejected = [r for r in results if r[0] is False]

        # In SQLite/single-DB, max_concurrency must be respected
        self.assertEqual(len(successful), max_concurrency, f"Expected {max_concurrency} leases, got {len(successful)}")
        self.assertEqual(len(rejected), num_threads - max_concurrency)

        # Clean up
        for _, lid in successful:
            manager.release_lease(lid)

    def test_05_rate_limit_sliding_window_persistence_across_instances(self):
        """Rate limit sliding window events must be shared across engine instances."""
        engine_1 = TenantFairnessEngine()
        engine_2 = TenantFairnessEngine()

        rate_key = f"tenant:{self.tenant_id}:rpm"
        limit = 5

        # Engine 1 consumes 3 tokens
        for _ in range(3):
            allowed, remaining, _ = engine_1._check_sliding_window(rate_key, max_requests=limit, window_seconds=60.0)
            self.assertTrue(allowed)

        # Engine 2 (separate instance) consumes remaining 2 tokens
        allowed4, rem4, _ = engine_2._check_sliding_window(rate_key, max_requests=limit, window_seconds=60.0)
        self.assertTrue(allowed4)

        allowed5, rem5, _ = engine_2._check_sliding_window(rate_key, max_requests=limit, window_seconds=60.0)
        self.assertTrue(allowed5)
        self.assertEqual(rem5, 0)

        # 6th attempt on Engine 1 must be rate-limited
        allowed6, rem6, retry_after = engine_1._check_sliding_window(rate_key, max_requests=limit, window_seconds=60.0)
        self.assertFalse(allowed6)
        self.assertEqual(rem6, 0)
        self.assertGreater(retry_after, 0)


if __name__ == "__main__":
    unittest.main()
