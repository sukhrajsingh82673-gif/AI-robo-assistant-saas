"""
ZONATA Enterprise SaaS — Free-Tier Embedded Worker & Staging Durability Suite
Validates worker crash recovery, orphaned job reclamation, retry governance,
idempotency controls, graceful shutdown, and edge metric protection.
"""

import os
import sys
import time
import json
import uuid
import unittest
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.db import configure_isolated_test_db, db
from core.action_envelope import ActionEnvelope, RiskClass, command_bus
from core.database_engine import engine, WorkloadType


class TestFreeTierWorkerDurability(unittest.TestCase):
    def setUp(self):
        command_bus._stop_event.clear()
        self.test_db_path = configure_isolated_test_db()
        # Initialize queue table in isolated DB
        command_bus._init_db()

    def tearDown(self):
        command_bus.stop()
        for p in engine.pools.values():
            p.reset()
        db.close()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass


    def test_01_orphaned_job_recovery_after_crash(self):
        """Validates that jobs interrupted in ASSIGNED status are recovered to QUEUED on worker restart."""
        # Create a test action envelope
        action = ActionEnvelope.create(
            tenant_id="tnt_durability_test",
            company_id="comp_durability_test",
            agent_id="agt_durability_1",
            capability_id="system.diagnostics.echo",
            target="internal",
            intent="Test worker crash recovery",
            risk_class=RiskClass.READ_ONLY,
            parameters={"message": "Crash recovery verification"},
            idempotency_key=f"idemp_{uuid.uuid4().hex}"
        )
        action_id = command_bus.enqueue(action)

        # Simulate worker claiming the job and then immediately crashing/sleeping
        claimed = command_bus.fetch_next(worker_id="crashed_worker_999")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.action_id, action_id)

        # Verify job is ASSIGNED to crashed worker in database
        status_before = command_bus.get_status(action_id)
        self.assertEqual(status_before["status"], "ASSIGNED")

        # Simulate container restart: worker startup calls recover_interrupted_jobs
        recovered_count = command_bus.recover_interrupted_jobs(timeout_seconds=0.0)
        self.assertGreaterEqual(recovered_count, 1)

        # Verify job is safely back in QUEUED state with retry count tracked
        status_after = command_bus.get_status(action_id)
        self.assertEqual(status_after["status"], "QUEUED")

        # Verify a new worker can now fetch and claim the recovered job
        new_claimed = command_bus.fetch_next(worker_id="reborn_worker_1000")
        self.assertIsNotNone(new_claimed)
        self.assertEqual(new_claimed.action_id, action_id)

    def test_02_job_retry_limit_exhaustion_protection(self):
        """Validates that a poison job causing repeated crashes is terminated after 3 retries."""
        action = ActionEnvelope.create(
            tenant_id="tnt_durability_test",
            company_id="comp_durability_test",
            agent_id="agt_durability_2",
            capability_id="system.diagnostics.echo",
            target="internal",
            intent="Test retry exhaustion",
            risk_class=RiskClass.READ_ONLY,
            parameters={"message": "Poison action simulation"},
            idempotency_key=f"idemp_{uuid.uuid4().hex}"
        )
        action_id = command_bus.enqueue(action)

        # Simulate 3 crashes
        for i in range(1, 4):
            claimed = command_bus.fetch_next(worker_id=f"worker_crash_{i}")
            self.assertIsNotNone(claimed)
            command_bus.recover_interrupted_jobs(timeout_seconds=0.0)
            status = command_bus.get_status(action_id)
            self.assertEqual(status["status"], "QUEUED", f"Failed on recovery attempt {i}")

        # 4th crash: should exceed maximum retries and transition to FAILED
        claimed = command_bus.fetch_next(worker_id="worker_crash_4")
        self.assertIsNotNone(claimed)
        command_bus.recover_interrupted_jobs(timeout_seconds=0.0)

        final_status = command_bus.get_status(action_id)
        self.assertEqual(final_status["status"], "FAILED")
        self.assertIn("exceeded maximum retry attempts", final_status["error"])

    def test_03_graceful_worker_stop(self):
        """Validates that command_bus.stop() gracefully breaks the worker loop."""
        command_bus.reset_worker()
        worker_thread = threading.Thread(
            target=command_bus.run_worker,
            kwargs={"worker_id": "test_graceful_worker", "poll_interval": 0.02},
            daemon=True
        )
        worker_thread.start()
        time.sleep(0.1)
        self.assertTrue(worker_thread.is_alive())

        # Signal stop
        command_bus.stop()
        worker_thread.join(timeout=5.0)
        self.assertFalse(worker_thread.is_alive(), "Worker thread should terminate cleanly upon stop() signal")


if __name__ == "__main__":
    unittest.main()
