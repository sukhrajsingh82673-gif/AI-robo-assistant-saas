"""
Step 4I Acceptance & Contract Test Suite: 24/7 Autonomous Daemon & Self-Healing
=============================================================================
Validates:
1. Distributed leader election and dead-node failover via scheduler_leader_leases.
2. Monotonic leased scheduler execution with catchup policies (RUN_ONCE, SKIP_MISSED).
3. Outbox Dead-Letter Queue (DLQ) processor with exponential backoff and isolation.
4. Autonomous self-healing supervisor reclaiming orphaned job leases and stalled locks.
5. Circuit breaker state machine (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
6. 24/7 Canary health probe verifying DB connectivity and KMS roundtrip.
7. Graceful daemon termination and leadership release on shutdown signals.
8. Mutation check: unhandled job exceptions do not crash daemon supervisor loop.
"""

import os
import time
import json
import uuid
from unittest import TestCase

from core.db import db
from core.daemon.leader_elector import LeaderElector
from core.daemon.dlq_processor import OutboxDLQProcessor
from core.daemon.self_healing import SelfHealingSupervisor, CircuitBreaker, CircuitState
from core.daemon.canary_probe import DaemonCanaryProbe
from core.daemon.autonomous_daemon import AutonomousDaemon


class TestStep4AutonomousDaemon(TestCase):
    """Sub-Step 4I Test Suite."""

    def setUp(self):
        os.environ["ZONATA_TEST_MODE"] = "1"
        self.tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_id = f"comp_{uuid.uuid4().hex[:8]}"
        self._clean_tables()

    def tearDown(self):
        self._clean_tables()

    def _clean_tables(self):
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM scheduler_leader_leases")
            cur.execute("DELETE FROM scheduled_jobs WHERE tenant_id = ?", (self.tenant_id,))
            cur.execute("DELETE FROM outbox_events WHERE tenant_id = ?", (self.tenant_id,))
            conn.commit()

    def test_01_distributed_leader_election_and_failover(self):
        """Leader election lease acquisition, renewal, and expired lease takeover."""
        lease_key = f"test_lease_{uuid.uuid4().hex[:8]}"
        node_a = LeaderElector(lease_key=lease_key, node_id="node_alpha")
        node_b = LeaderElector(lease_key=lease_key, node_id="node_bravo")

        # 1. Node A acquires lease
        self.assertTrue(node_a.try_acquire_or_renew(ttl_seconds=2.0))
        leader_info = node_a.get_current_leader()
        self.assertIsNotNone(leader_info)
        self.assertEqual(leader_info["leader_node_id"], "node_alpha")
        self.assertTrue(leader_info["is_self"])

        # 2. Node B tries to acquire active lease -> must fail
        self.assertFalse(node_b.try_acquire_or_renew(ttl_seconds=2.0))

        # 3. Simulate Node A expiration (set expires_at in the past)
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE scheduler_leader_leases SET expires_at = ? WHERE lease_key = ?",
                (time.time() - 10.0, lease_key)
            )
            conn.commit()

        # 4. Node B detects expired lease and takes over leadership
        self.assertTrue(node_b.try_acquire_or_renew(ttl_seconds=5.0))
        new_leader_info = node_b.get_current_leader()
        self.assertEqual(new_leader_info["leader_node_id"], "node_bravo")
        self.assertTrue(new_leader_info["is_self"])

    def test_02_scheduled_job_execution_and_catchup_policies(self):
        """Monotonic scheduled job execution with RUN_ONCE and SKIP_MISSED policies."""
        now = time.time()
        executed_jobs = []

        daemon = AutonomousDaemon(
            node_id="daemon_runner",
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        daemon.register_job_handler("hourly_sync", lambda: executed_jobs.append("hourly_sync"))
        daemon.register_job_handler("metrics_sweep", lambda: executed_jobs.append("metrics_sweep"))

        # Insert 2 ready jobs
        with db.get_connection() as conn:
            cur = conn.cursor()
            # Job 1: RUN_ONCE
            cur.execute(
                """
                INSERT INTO scheduled_jobs (
                    job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                    next_run_at, catchup_policy, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"job_{uuid.uuid4().hex[:8]}", self.tenant_id, self.company_id,
                    "hourly_sync", 3600, now - 10.0, "RUN_ONCE", "IDLE", now - 100.0
                )
            )
            # Job 2: SKIP_MISSED
            cur.execute(
                """
                INSERT INTO scheduled_jobs (
                    job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                    next_run_at, catchup_policy, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"job_{uuid.uuid4().hex[:8]}", self.tenant_id, self.company_id,
                    "metrics_sweep", 60, now - 50.0, "SKIP_MISSED", "IDLE", now - 100.0
                )
            )
            conn.commit()

        # Execute single daemon tick
        report = daemon.tick(now=now)
        self.assertTrue(report["is_leader"])
        self.assertEqual(report["jobs_executed"], 2)
        self.assertIn("hourly_sync", executed_jobs)
        self.assertIn("metrics_sweep", executed_jobs)

        # Verify next_run_at updated
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name, next_run_at, status FROM scheduled_jobs WHERE tenant_id = ?", (self.tenant_id,))
            rows = cur.fetchall()
            for name, next_run, status in rows:
                self.assertEqual(status, "IDLE")
                self.assertGreater(next_run, now)

    def test_03_outbox_dlq_processor_and_exponential_backoff(self):
        """Outbox DLQ processor retries with exponential backoff and moves to DEAD_LETTER after max_attempts."""
        processor = OutboxDLQProcessor(base_backoff_sec=0.1, max_backoff_sec=1.0)
        successful_events = []
        fail_counter = {"count": 0}

        def _success_handler(payload):
            successful_events.append(payload["msg"])

        def _fail_handler(payload):
            fail_counter["count"] += 1
            raise RuntimeError("Temporary downstream failure")

        processor.register_handler("notification.sent", _success_handler)
        processor.register_handler("payment.process", _fail_handler)

        now = time.time()
        event_succ_id = f"evt_{uuid.uuid4().hex[:8]}"
        event_fail_id = f"evt_{uuid.uuid4().hex[:8]}"

        with db.get_connection() as conn:
            cur = conn.cursor()
            # Successful event
            cur.execute(
                """
                INSERT INTO outbox_events (
                    id, tenant_id, company_id, topic, idempotency_key, payload,
                    status, attempts, max_attempts, next_retry_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_succ_id, self.tenant_id, self.company_id, "notification.sent",
                    f"idem_{uuid.uuid4().hex[:8]}", json.dumps({"msg": "Welcome!"}),
                    "PENDING", 0, 3, now, now
                )
            )
            # Failing event with max_attempts = 2
            cur.execute(
                """
                INSERT INTO outbox_events (
                    id, tenant_id, company_id, topic, idempotency_key, payload,
                    status, attempts, max_attempts, next_retry_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_fail_id, self.tenant_id, self.company_id, "payment.process",
                    f"idem_{uuid.uuid4().hex[:8]}", json.dumps({"amount": 100}),
                    "PENDING", 0, 2, now, now
                )
            )
            conn.commit()

        # Batch 1: Processes both
        counts1 = processor.process_batch(batch_size=10)
        self.assertEqual(counts1["processed"], 2)
        self.assertEqual(counts1["succeeded"], 1)
        self.assertEqual(counts1["retried"], 1)
        self.assertEqual(successful_events, ["Welcome!"])

        # Check failing event is in FAILED with attempts=1
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, attempts, next_retry_at FROM outbox_events WHERE id = ?", (event_fail_id,))
            row = cur.fetchone()
            self.assertEqual(row[0], "FAILED")
            self.assertEqual(row[1], 1)

            # Fast forward next_retry_at to now for next attempt
            cur.execute("UPDATE outbox_events SET next_retry_at = ? WHERE id = ?", (time.time() - 1.0, event_fail_id))
            conn.commit()

        # Batch 2: Failing event fails again (attempts = 2 >= max_attempts 2) -> DEAD_LETTER
        counts2 = processor.process_batch(batch_size=10)
        self.assertEqual(counts2["dead_lettered"], 1)

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, attempts, last_error FROM outbox_events WHERE id = ?", (event_fail_id,))
            row = cur.fetchone()
            self.assertEqual(row[0], "DEAD_LETTER")
            self.assertEqual(row[1], 2)
            self.assertIn("Temporary downstream failure", row[2])

        # Test reprocessing dead-letter
        self.assertTrue(processor.reprocess_dead_letter(event_fail_id))
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, attempts FROM outbox_events WHERE id = ?", (event_fail_id,))
            row = cur.fetchone()
            self.assertEqual(row[0], "PENDING")
            self.assertEqual(row[1], 0)

    def test_04_self_healing_reclaims_orphaned_jobs_and_locks(self):
        """Self-healing supervisor reclaims orphaned jobs and stalled outbox locks."""
        supervisor = SelfHealingSupervisor()
        now = time.time()

        job_id = f"job_orphaned_{uuid.uuid4().hex[:8]}"
        evt_id = f"evt_stalled_{uuid.uuid4().hex[:8]}"

        with db.get_connection() as conn:
            cur = conn.cursor()
            # Stalled running job with expired lease
            cur.execute(
                """
                INSERT INTO scheduled_jobs (
                    job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                    next_run_at, lease_owner, lease_expires_at, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id, self.tenant_id, self.company_id, "orphan_task", 300,
                    now, "crashed_worker_node", now - 60.0, "RUNNING", now - 300.0
                )
            )
            # Stalled outbox event with expired lock
            cur.execute(
                """
                INSERT INTO outbox_events (
                    id, tenant_id, company_id, topic, idempotency_key, payload,
                    status, next_retry_at, locked_by, locked_until, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evt_id, self.tenant_id, self.company_id, "test.topic",
                    f"idem_{uuid.uuid4().hex[:8]}", json.dumps({"test": 1}),
                    "PROCESSING", now, "crashed_worker_node", now - 30.0, now
                )
            )
            conn.commit()

        # Run healing sweep
        healing_report = supervisor.run_healing_cycle()
        self.assertGreaterEqual(healing_report["reclaimed_jobs"], 1)
        self.assertGreaterEqual(healing_report["reclaimed_outbox_events"], 1)

        # Verify job reset to IDLE and event reset to PENDING
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, lease_owner, lease_expires_at FROM scheduled_jobs WHERE job_id = ?", (job_id,))
            j_row = cur.fetchone()
            self.assertEqual(j_row[0], "IDLE")
            self.assertIsNone(j_row[1])

            cur.execute("SELECT status, locked_by, locked_until FROM outbox_events WHERE id = ?", (evt_id,))
            e_row = cur.fetchone()
            self.assertEqual(e_row[0], "PENDING")
            self.assertIsNone(e_row[1])

    def test_05_circuit_breaker_transitions(self):
        """Circuit breaker state transitions: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
        cb = CircuitBreaker("email_service", failure_threshold=2, cooldown_sec=0.2)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        # Failure 1
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

        # Failure 2 -> trips to OPEN
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

        # Cooldown period
        time.sleep(0.25)
        # First execution after cooldown enters HALF_OPEN
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Successful trials heal the circuit
        cb.record_success()
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

    def test_06_canary_health_probe(self):
        """24/7 Canary health probe evaluates system health."""
        probe = DaemonCanaryProbe(tenant_id=self.tenant_id, company_id=self.company_id)
        status = probe.check_health()

        self.assertTrue(status.is_healthy)
        self.assertTrue(status.database_connected)
        self.assertTrue(status.kms_roundtrip_ok)
        self.assertIn("db_dialect", status.details)

    def test_07_graceful_shutdown_releases_lease(self):
        """Graceful daemon shutdown stops thread and voluntarily releases leader lease."""
        daemon = AutonomousDaemon(
            node_id="daemon_graceful",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            tick_interval_sec=0.1
        )
        daemon.start()
        time.sleep(0.3)
        self.assertTrue(daemon.running)

        # Check lease held
        leader_info = daemon.leader_elector.get_current_leader()
        self.assertIsNotNone(leader_info)
        self.assertTrue(leader_info["is_active"])

        # Stop daemon
        daemon.stop()
        self.assertFalse(daemon.running)

        # Verify lease was released (expires_at set to 0)
        leader_info_after = daemon.leader_elector.get_current_leader()
        self.assertFalse(leader_info_after["is_active"])

    def test_08_mutation_check_unhandled_crash_fails_closed(self):
        """Unhandled job exceptions do not crash daemon supervisor loop."""
        daemon = AutonomousDaemon(
            node_id="daemon_resilient",
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )

        def _crashing_handler():
            raise ZeroDivisionError("Simulated catastrophic arithmetic explosion in user task")

        daemon.register_job_handler("crashing_task", _crashing_handler)

        now = time.time()
        job_id = f"job_crash_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO scheduled_jobs (
                    job_id, tenant_id, company_id, name, cron_or_interval_seconds,
                    next_run_at, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, self.tenant_id, self.company_id, "crashing_task", 60, now, "IDLE", now)
            )
            conn.commit()

        # Tick should NOT raise exception
        report = daemon.tick(now=now)
        self.assertEqual(report["jobs_executed"], 1)

        # Job must be recorded as FAILED rather than locked
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status, lease_owner FROM scheduled_jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            self.assertEqual(row[0], "FAILED")
            self.assertIsNone(row[1])
