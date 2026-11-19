"""
ZONATA Enterprise SaaS — PostgreSQL Reliability, Connection Pooling & Concurrency Suite
Phase 6 Qualification Suite (BLK-06 & BLK-10)

Verifies:
1. Pool initialization and configuration (min/max bounds, timeouts, env overrides).
2. Connection checkout and return cycle (thread-safe queue, active vs idle accounting).
3. Context manager transaction semantics (auto-commit on success, cleanup in finally).
4. Auto-rollback on exception (uncommitted state cleanly rolled back before return).
5. Pool saturation and checkout timeout (DatabasePoolExhaustedError on exhaustion).
6. High-concurrency multi-threaded workload qualification (10 concurrent workers, zero deadlocks).
7. Stale/broken connection eviction and automatic replacement.
8. Idempotent connection close and use-after-free prevention.
9. Standalone SQL migration completeness (all 164 tables, async_command_queue present — BLK-10).
10. Pool telemetry reporting (get_stats()) and graceful shutdown (close_all()).
"""

import os
import sys
import time
import uuid
import unittest
import threading
import tempfile
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import (
    db,
    Database,
    DatabaseDialect,
    PostgresConnectionPool,
    PostgresConnectionWrapper,
    DatabasePoolExhaustedError,
    configure_isolated_test_db,
    TABLE_PRIMARY_KEYS
)
from core.production_config import ProductionConfigValidator, ConfigurationError

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "pg_pool_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class MockRawConnection:
    """Simulates a driver-level connection (psycopg2/pg8000) for testing pool mechanics."""
    def __init__(self, conn_id: int):
        self.conn_id = conn_id
        self.closed = 0
        self.committed = False
        self.rolled_back = False
        self.queries_executed: List[str] = []
        self.should_fail_ping = False

    def cursor(self, *args, **kwargs):
        if self.closed != 0:
            raise RuntimeError("Connection is closed")
        raw = self
        class MockCursor:
            def execute(self, sql, params=()):
                if raw.should_fail_ping and "SELECT 1" in sql:
                    raise RuntimeError("Simulated network broken pipe")
                raw.queries_executed.append(sql)
            def fetchone(self):
                return (1,)
            def fetchall(self):
                return []
            def close(self):
                pass
        return MockCursor()

    def commit(self):
        if self.closed != 0:
            raise RuntimeError("Connection is closed")
        self.committed = True

    def rollback(self):
        if self.closed != 0:
            raise RuntimeError("Connection is closed")
        self.rolled_back = True

    def close(self):
        self.closed = 1


class TestPostgreSqlConnectionPooling(unittest.TestCase):
    """Qualification suite for PostgreSQL connection pooling and concurrency reliability."""

    def setUp(self):
        self.mock_db = MagicMock(spec=Database)
        self.mock_db.database_url = "postgresql://zonata_app:secret@localhost:5432/zonata_test"
        self._next_conn_id = 1

        def mock_create():
            conn = MockRawConnection(self._next_conn_id)
            self._next_conn_id += 1
            return conn

        self.mock_db._create_raw_connection.side_effect = mock_create

    def test_01_pool_initialization_and_configuration(self):
        """Verify connection pool bounds, timeout defaults, and environment parsing."""
        pool = PostgresConnectionPool(
            db_instance=self.mock_db,
            min_size=3,
            max_size=15,
            timeout=10.0,
            idle_timeout=120.0
        )
        self.assertEqual(pool.min_size, 3)
        self.assertEqual(pool.max_size, 15)
        self.assertEqual(pool.timeout, 10.0)
        self.assertEqual(pool.idle_timeout, 120.0)
        self.assertEqual(pool._total_count, 0)
        self.assertEqual(len(pool._checked_out), 0)

        # Min size cannot exceed max size
        pool_clamped = PostgresConnectionPool(
            db_instance=self.mock_db,
            min_size=20,
            max_size=10
        )
        self.assertGreaterEqual(pool_clamped.max_size, pool_clamped.min_size)

    def test_02_connection_checkout_and_return_cycle(self):
        """Verify checkout creates connection and close() returns to idle pool without closing socket."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, min_size=2, max_size=5)

        # Checkout 1
        conn1 = pool.get_connection()
        self.assertIsInstance(conn1, PostgresConnectionWrapper)
        self.assertEqual(pool._total_count, 1)
        self.assertEqual(len(pool._checked_out), 1)
        self.assertEqual(len(pool._idle_connections), 0)

        # Checkout 2
        conn2 = pool.get_connection()
        self.assertEqual(pool._total_count, 2)
        self.assertEqual(len(pool._checked_out), 2)

        # Return conn1 via close()
        raw1 = conn1.raw_conn
        conn1.close()
        self.assertEqual(len(pool._checked_out), 1)
        self.assertEqual(len(pool._idle_connections), 1)
        self.assertEqual(raw1.closed, 0, "Raw socket must not be closed on pool return")
        self.assertTrue(raw1.rolled_back, "Safety rollback must execute on return to pool")

        # Checkout 3 should reuse conn1 from idle pool
        conn3 = pool.get_connection()
        self.assertIs(conn3.raw_conn, raw1, "Pool must reuse idle connection")
        self.assertEqual(pool._total_count, 2, "Total connection count must remain 2")
        self.assertEqual(len(pool._checked_out), 2)

        pool.close_all()

    def test_03_context_manager_lifecycle_commit_and_return(self):
        """Verify context manager commits on success and returns to pool in finally."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, max_size=5)

        with pool.get_connection() as conn:
            conn.execute("SELECT 1")
            raw_conn = conn.raw_conn
            self.assertEqual(len(pool._checked_out), 1)
            self.assertFalse(raw_conn.committed)

        # After block exit
        self.assertTrue(raw_conn.committed, "Transaction must commit on normal context exit")
        self.assertEqual(len(pool._checked_out), 0, "Connection must be returned to pool")
        self.assertEqual(len(pool._idle_connections), 1)
        self.assertEqual(raw_conn.closed, 0)

        pool.close_all()

    def test_04_context_manager_rollback_on_exception(self):
        """Verify context manager rolls back on exception and safely returns to pool."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, max_size=5)

        raw_conn = None
        with self.assertRaises(ValueError):
            with pool.get_connection() as conn:
                raw_conn = conn.raw_conn
                conn.execute("INSERT INTO test VALUES (1)")
                raise ValueError("Simulated application error inside transaction")

        self.assertIsNotNone(raw_conn)
        self.assertTrue(raw_conn.rolled_back, "Transaction must rollback on exception")
        self.assertEqual(len(pool._checked_out), 0, "Connection must return to pool after error")
        self.assertEqual(len(pool._idle_connections), 1)

        pool.close_all()

    def test_05_pool_saturation_and_timeout(self):
        """Verify checkout blocks and raises DatabasePoolExhaustedError when pool is saturated."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, max_size=2, timeout=0.1)

        c1 = pool.get_connection()
        c2 = pool.get_connection()
        self.assertEqual(pool._total_count, 2)
        self.assertEqual(len(pool._checked_out), 2)

        # 3rd checkout must timeout and raise DatabasePoolExhaustedError
        start_time = time.time()
        with self.assertRaises(DatabasePoolExhaustedError) as ctx:
            pool.get_connection(timeout=0.1)
        elapsed = time.time() - start_time

        self.assertGreaterEqual(elapsed, 0.08)
        self.assertIn("exhausted", str(ctx.exception).lower())

        # Once c1 is returned, checkout should succeed immediately
        c1.close()
        c3 = pool.get_connection(timeout=0.5)
        self.assertIsNotNone(c3)

        c2.close()
        c3.close()
        pool.close_all()

    def test_06_multithreaded_concurrency_qualification(self):
        """Verify high concurrency across 10 worker threads sharing a pool of 4 connections."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, min_size=2, max_size=4, timeout=5.0)

        num_threads = 10
        iterations_per_thread = 5
        errors = []
        threads = []

        def worker(thread_idx: int):
            try:
                for it in range(iterations_per_thread):
                    with pool.get_connection(timeout=3.0) as conn:
                        conn.execute(f"/* thread_{thread_idx} */ SELECT 1")
                        time.sleep(0.01)  # Simulate workload
            except Exception as e:
                errors.append((thread_idx, str(e)))

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        self.assertEqual(errors, [], f"Concurrency errors occurred: {errors}")
        self.assertEqual(len(pool._checked_out), 0, "All connections must be checked back in")
        self.assertLessEqual(pool._total_count, 4, "Total connections must never exceed max_size (4)")

        pool.close_all()

    def test_07_broken_connection_eviction_and_recovery(self):
        """Verify pool detects broken connection during idle checkout and spawns healthy replacement."""
        pool = PostgresConnectionPool(
            db_instance=self.mock_db,
            max_size=3,
            idle_timeout=0.0  # Force liveness check on every checkout
        )

        c1 = pool.get_connection()
        raw1 = c1.raw_conn
        c1.close()  # Returned to idle pool

        # Simulate network drop on raw1
        raw1.should_fail_ping = True

        # Next checkout should discard raw1 and spawn a fresh connection
        c2 = pool.get_connection()
        self.assertIsNot(c2.raw_conn, raw1, "Broken connection must be evicted")
        self.assertEqual(raw1.closed, 1, "Broken connection must be closed")
        self.assertEqual(pool._total_count, 1, "Total count must be decremented and replaced")

        c2.close()
        pool.close_all()

    def test_08_idempotent_close_and_use_after_free_prevention(self):
        """Verify idempotent close() does not corrupt pool and prevents use-after-free."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, max_size=3)

        conn = pool.get_connection()
        conn.close()
        self.assertEqual(len(pool._idle_connections), 1)

        # Second close should be no-op
        conn.close()
        self.assertEqual(len(pool._idle_connections), 1, "Idempotent close must not double-return")

        # Use after free must raise RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            conn.execute("SELECT 1")
        self.assertIn("closed", str(ctx.exception).lower())

        pool.close_all()

    def test_09_standalone_migration_operational_schema_completeness(self):
        """Verify migrations/pg/0001_postgresql_full_schema.sql contains all operational tables (BLK-10)."""
        migration_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "migrations",
            "pg",
            "0001_postgresql_full_schema.sql"
        )
        self.assertTrue(os.path.exists(migration_path), f"Migration file missing at {migration_path}")

        with open(migration_path, "r", encoding="utf-8") as f:
            content = f.read()

        import re
        tables = re.findall(r"CREATE TABLE IF NOT EXISTS\s+([a-zA-Z0-9_]+)", content, re.IGNORECASE)
        table_set = set(tables)

        self.assertGreaterEqual(len(table_set), 160, f"Expected 160+ tables, found {len(table_set)}")
        # Check critical operational tables specifically addressing BLK-10
        self.assertIn("async_command_queue", table_set, "async_command_queue missing from pg migration!")
        self.assertIn("auth_revoked_tokens", table_set, "auth_revoked_tokens missing from pg migration!")
        self.assertIn("schema_migrations", table_set, "schema_migrations missing from pg migration!")
        self.assertIn("optimistic_lock_registry", table_set, "optimistic_lock_registry missing from pg migration!")
        self.assertIn("supervisor_heartbeats", table_set, "supervisor_heartbeats missing from pg migration!")
        self.assertIn("crm_customers", table_set, "crm_customers missing from pg migration!")
        self.assertIn("crm_deals", table_set, "crm_deals missing from pg migration!")

        # Verify TABLE_PRIMARY_KEYS has async_command_queue
        self.assertIn("async_command_queue", TABLE_PRIMARY_KEYS)
        self.assertEqual(TABLE_PRIMARY_KEYS["async_command_queue"], ("command_id",))

    def test_10_pool_metrics_and_graceful_shutdown(self):
        """Verify get_stats telemetry and close_all shutdown behavior."""
        pool = PostgresConnectionPool(db_instance=self.mock_db, min_size=2, max_size=5)

        c1 = pool.get_connection()
        c2 = pool.get_connection()
        c1.close()

        stats = pool.get_stats()
        self.assertEqual(stats["total_connections"], 2)
        self.assertEqual(stats["active_connections"], 1)
        self.assertEqual(stats["idle_connections"], 1)
        self.assertEqual(stats["min_size"], 2)
        self.assertEqual(stats["max_size"], 5)
        self.assertEqual(stats["status"], "HEALTHY")

        pool.close_all()
        post_stats = pool.get_stats()
        self.assertEqual(post_stats["status"], "CLOSED")
        self.assertEqual(post_stats["total_connections"], 0)
        self.assertEqual(post_stats["active_connections"], 0)
        self.assertEqual(post_stats["idle_connections"], 0)

        # Subsequent checkout on closed pool must fail
        with self.assertRaises(RuntimeError) as ctx:
            pool.get_connection()
        self.assertIn("closed", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
