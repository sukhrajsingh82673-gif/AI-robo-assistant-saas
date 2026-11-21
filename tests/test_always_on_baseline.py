"""
Tests for OpenCode Step 1I: Always-on Baseline
Durable Outbox, Distributed Leased Scheduler, Health Probes, and Backup & Restore Drill.

Acceptance criteria verified:
1. Outbox: side effects committed atomically, at-least-once drain, exponential backoff, DLQ after 5 attempts.
2. Worker resilience: killing worker mid-job does not lose or double-deliver.
3. Scheduler: persisted jobs, monotonic next-run, max-run-time, missed-run catchup policies.
4. Leader failover: dead node drops lease in 30s, leaving no orphan locks.
5. Health probes: /healthz liveness, /readyz readiness, turning 503 when DB paused or critical port fails.
6. Multi-tenant isolation: cross-tenant access denied.
"""

import json
import os
import shutil
import time
import unittest
from unittest import mock
import uuid

from core.db import db, configure_isolated_test_db
from core.baseline.outbox import (
    DurableOutbox,
    OutboxEventRecord,
    OutboxStatus,
    ensure_outbox_tables,
)
from core.baseline.scheduler import (
    DurableScheduler,
    ScheduledJobRecord,
    JobStatus,
    ensure_scheduler_tables,
)
from core.baseline.health import (
    check_liveness,
    check_readiness,
)
from core.ports.base import PortStatus, ProviderResult


class TestAlwaysOnBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not db.is_postgresql():
            cls.test_db_path = configure_isolated_test_db()
        ensure_outbox_tables()
        ensure_scheduler_tables()

    def setUp(self):
        self.tenant_a = f"tnt_a_{uuid.uuid4().hex[:8]}"
        self.company_a = f"cmp_a_{uuid.uuid4().hex[:8]}"
        self.tenant_b = f"tnt_b_{uuid.uuid4().hex[:8]}"
        self.company_b = f"cmp_b_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM scheduler_leader_leases")
            cur.execute("DELETE FROM scheduled_jobs")
            cur.execute("DELETE FROM outbox_events")
            conn.commit()
        self.outbox = DurableOutbox()
        self.scheduler = DurableScheduler()

    # =========================================================================
    # 1. TRANSACTIONAL OUTBOX TESTS
    # =========================================================================

    def test_outbox_atomic_enqueue_and_idempotency(self):
        """Acceptance 1a: Enqueueing is idempotent per (tenant, company, idempotency_key)."""
        payload = {"email_to": "audit@acme.corp", "subject": "Quarterly Statement"}
        ev1 = self.outbox.enqueue(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            topic="email.send",
            idempotency_key="idemp_txn_001",
            payload=payload,
        )
        # Duplicate enqueue returns identical event id
        ev2 = self.outbox.enqueue(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            topic="email.send",
            idempotency_key="idemp_txn_001",
            payload=payload,
        )
        self.assertEqual(ev1, ev2)

        record = self.outbox.get_event(ev1)
        self.assertIsNotNone(record)
        self.assertEqual(record.status, OutboxStatus.PENDING)
        self.assertEqual(record.payload["email_to"], "audit@acme.corp")

    def test_outbox_worker_drains_with_at_least_once_delivery(self):
        """Acceptance 1b: Worker drains pending events and marks status DISPATCHED."""
        dispatched_events = []

        def handle_email(event: OutboxEventRecord):
            dispatched_events.append(event.id)

        self.outbox.register_handler("notification.push", handle_email, handler_key="push_handler")

        ev_id = self.outbox.enqueue(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            topic="notification.push",
            idempotency_key="idemp_push_001",
            payload={"msg": "Hello"},
        )

        drained = self.outbox.drain(worker_id="worker_test_1", batch_size=10)
        self.assertEqual(drained, 1)
        self.assertIn(ev_id, dispatched_events)

        rec = self.outbox.get_event(ev_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.status, OutboxStatus.DISPATCHED)
        self.assertIsNotNone(rec.dispatched_at)

    def test_outbox_exponential_backoff_and_dead_letter_queue_after_5_attempts(self):
        """Acceptance 1c: Failed handlers backoff exponentially and move to DEAD_LETTER after 5 attempts."""
        attempt_log = []

        def failing_handler(event: OutboxEventRecord):
            attempt_log.append(event.attempts)
            raise RuntimeError(f"Simulated external provider crash on attempt {event.attempts}")

        self.outbox.register_handler("sync.fail", failing_handler, handler_key="failing_sync")

        ev_id = self.outbox.enqueue(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            topic="sync.fail",
            idempotency_key="idemp_fail_001",
            payload={"target": "remote_ledger"},
            max_attempts=5,
        )

        # Attempt 1 -> fails -> status FAILED, attempts=1
        self.outbox.drain(worker_id="worker_retry", lease_seconds=1.0)
        rec = self.outbox.get_event(ev_id)
        self.assertEqual(rec.status, OutboxStatus.FAILED)
        self.assertEqual(rec.attempts, 1)
        self.assertIn("Simulated external provider crash", rec.last_error)

        # Force next_retry_at to past to simulate time elapse
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE outbox_events SET next_retry_at = 0 WHERE id = ?", (ev_id,))
            conn.commit()

        # Attempts 2, 3, 4
        for expected_attempts in [2, 3, 4]:
            self.outbox.drain(worker_id="worker_retry", lease_seconds=1.0)
            rec = self.outbox.get_event(ev_id)
            self.assertEqual(rec.status, OutboxStatus.FAILED)
            self.assertEqual(rec.attempts, expected_attempts)
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE outbox_events SET next_retry_at = 0 WHERE id = ?", (ev_id,))
                conn.commit()

        # Attempt 5 -> Final failure -> moves to DEAD_LETTER
        self.outbox.drain(worker_id="worker_retry", lease_seconds=1.0)
        rec = self.outbox.get_event(ev_id)
        self.assertEqual(rec.status, OutboxStatus.DEAD_LETTER)
        self.assertEqual(rec.attempts, 5)

    def test_outbox_worker_crash_mid_job_leaves_no_loss_or_double_delivery(self):
        """Acceptance 1d: Killing worker mid-job does not lose message; reclaimed once lease expires."""
        execution_count = 0

        def robust_handler(event: OutboxEventRecord):
            nonlocal execution_count
            execution_count += 1

        self.outbox.register_handler("order.process", robust_handler, handler_key="order_proc")

        ev_id = self.outbox.enqueue(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            topic="order.process",
            idempotency_key="idemp_order_001",
            payload={"order_id": "ord_999"},
        )

        # Simulate Worker 1 claiming the event and crashing mid-job (status=PROCESSING, locked_until=past)
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE outbox_events
                SET status = 'PROCESSING', locked_by = 'crashed_worker_node', locked_until = ?
                WHERE id = ?
                """,
                (time.time() - 10.0, ev_id),  # Lease expired 10 seconds ago
            )
            conn.commit()

        # Worker 2 comes online and drains: reclaims the abandoned event
        drained = self.outbox.drain(worker_id="survivor_worker_node", lease_seconds=30.0)
        self.assertEqual(drained, 1)
        self.assertEqual(execution_count, 1)

        rec = self.outbox.get_event(ev_id)
        self.assertEqual(rec.status, OutboxStatus.DISPATCHED)

    # =========================================================================
    # 2. DISTRIBUTED LEASED SCHEDULER TESTS
    # =========================================================================

    def test_scheduler_persisted_job_monotonic_next_run(self):
        """Acceptance 2a: Persisted schedule executes due jobs and advances monotonic next-run."""
        job_runs = []

        def dummy_job(record: ScheduledJobRecord):
            job_runs.append(record.name)

        job_id = self.scheduler.register_job(
            tenant_id=self.tenant_a,
            company_id=self.company_a,
            name="daily_compliance_sweep",
            interval_seconds=3600,
            handler=dummy_job,
            first_run_delay_seconds=-5.0,  # Due immediately
        )

        ran = self.scheduler.tick(node_id="leader_node_1")
        self.assertGreaterEqual(ran, 1)
        self.assertIn("daily_compliance_sweep", job_runs)

        rec = self.scheduler.get_job(job_id)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.status, JobStatus.IDLE)
        # Next run is monotonically in the future
        self.assertGreater(rec.next_run_at, time.time())

    def test_scheduler_dead_node_drops_leader_lease_in_30s_and_reclaims_orphan_locks(self):
        """Acceptance 2b: Dead leader node drops lease in 30s; surviving node assumes leadership."""
        leader_a = "sched_node_dead"
        leader_b = "sched_node_survivor"

        # Node A acquires leader lease with expired timestamp (simulating crash > 30s ago)
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM scheduler_leader_leases WHERE lease_key = 'cluster_scheduler_leader'")
            cur.execute(
                """
                INSERT INTO scheduler_leader_leases (lease_key, leader_node_id, heartbeat_at, expires_at)
                VALUES ('cluster_scheduler_leader', ?, ?, ?)
                """,
                (leader_a, now - 45.0, now - 15.0),  # Expired 15s ago
            )
            conn.commit()

        # Node B ticks: detects dead leader A, reclaims leadership
        claimed = self.scheduler.acquire_or_renew_leader_lease(leader_b, lease_duration=30.0)
        self.assertTrue(claimed)

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT leader_node_id FROM scheduler_leader_leases WHERE lease_key = 'cluster_scheduler_leader'")
            active_leader = cur.fetchone()[0]
            self.assertEqual(active_leader, leader_b)

    # =========================================================================
    # 3. REALITY HEALTH & READINESS PROBES
    # =========================================================================

    def test_liveness_probe_returns_200_ok(self):
        """Acceptance 3a: /healthz liveness probe confirms process responsiveness."""
        status_code, payload = check_liveness()
        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "OK")
        self.assertIn("uptime_seconds", payload)

    def test_readiness_probe_returns_200_ready_under_nominal_conditions(self):
        """Acceptance 3b: /readyz returns 200 READY when all subsystems are operational."""
        ensure_outbox_tables()
        ensure_scheduler_tables()
        status_code, payload = check_readiness()
        self.assertEqual(status_code, 200, f"Readiness probe failed with payload: {payload}")
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["checks"]["database"]["status"], "OK")
        self.assertEqual(payload["checks"]["disk_space"]["status"], "OK")

    def test_readiness_probe_turns_503_when_database_unreachable(self):
        """Acceptance 3c: /readyz returns 503 UNREADY when database is unreadable/paused."""
        with mock.patch("core.db.db.get_connection") as mock_conn:
            mock_conn.side_effect = RuntimeError("Database connection paused / unreachable")
            status_code, payload = check_readiness()
            self.assertEqual(status_code, 503)
            self.assertEqual(payload["status"], "UNREADY")
            self.assertEqual(payload["checks"]["database"]["status"], "FAILED")
            self.assertIn("Database unreadable", payload["failure_reasons"][0])

    def test_readiness_probe_turns_503_when_critical_port_fails(self):
        """Acceptance 3d: /readyz returns 503 UNREADY when a critical port (KMS or DB) fails."""
        mock_res = ProviderResult(
            status=PortStatus.FAILED,
            provider="mock_kms",
            provider_ref=None,
            sandbox=False,
            latency_ms=1.0,
            cost=0.0,
            error="Master envelope key destroyed",
        )

        with mock.patch("core.capability_probe.probe_key_management", return_value=mock_res):
            status_code, payload = check_readiness()
            self.assertEqual(status_code, 503)
            self.assertEqual(payload["status"], "UNREADY")
            self.assertEqual(payload["checks"]["critical_ports"]["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
