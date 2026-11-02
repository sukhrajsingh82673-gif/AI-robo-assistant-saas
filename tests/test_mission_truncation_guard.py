"""
Mission truncation / non-fabrication guard.

A mission whose deliverable was cut off at the model token limit must not be
sealed as verified. The runtime refuses verification and reports UNCERTAIN.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest

from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.db import db, configure_isolated_test_db
from core.coworker.background_dispatcher import (
    BackgroundMissionDispatcher, MissionState
)
from core.coworker.subworkers import SubWorkerCoordinator
from core.coworker.runtimes.runtime_router import WorkerRuntimeRouter
from core.llm_runtime import LLMResult


TRUNCATED_CONTENT = "## Partial deliverable\n\nThis response stops mid-sentence: onboarding"


def _truncated_chat(self, tenant_id, company_id, messages, system=None,
                    max_tokens=None, temperature=None, intent="general"):
    return LLMResult(
        content=TRUNCATED_CONTENT,
        provider="test_stub",
        model="truncated-test",
        degraded=False,
        latency_ms=0.2,
        finish_reason="length",
    )


class TestMissionTruncationGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_db_path = db.db_path
        cls.cls_temp_dir = tempfile.mkdtemp(prefix="zonata_truncation_cls_")
        cls.isolated_db = os.path.join(cls.cls_temp_dir, "truncation.db")
        configure_isolated_test_db(cls.isolated_db)
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) "
                "VALUES ('tnt_test', 'Test Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (time.time(),),
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, "
                "company_type, status, revenue, cost, contribution, understanding_pct, created_at) "
                "VALUES ('comp_test', 'tnt_test', 'Test Corp', 'Tech', 'NEW', 'OPERATIONAL', "
                "0.0, 0.0, 0.0, 100.0, ?)",
                (time.time(),),
            )
            conn.commit()
        cls._llm_patcher = patch("core.llm_runtime.LLMRuntime.chat", _truncated_chat)
        cls._llm_patcher.start()

    @classmethod
    def tearDownClass(cls):
        try:
            cls._llm_patcher.stop()
        except Exception:
            pass
        if cls.orig_db_path:
            db.set_db_path(cls.orig_db_path)
            os.environ["ZONATA_DB_PATH"] = cls.orig_db_path
        shutil.rmtree(cls.cls_temp_dir, ignore_errors=True)

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="zonata_truncation_")
        self.db_path = os.path.join(self.test_dir, "truncation_run.db")
        self.dispatcher = BackgroundMissionDispatcher(
            subworker_coord=SubWorkerCoordinator(tenant_id="tnt_test"),
            runtime_router=WorkerRuntimeRouter(tenant_id="tnt_test"),
            tenant_id="tnt_test",
            company_id="comp_test",
            db_path=self.db_path,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_truncated_deliverable_is_not_sealed_as_verified(self):
        mission = self.dispatcher.submit_background_prompt(
            prompt="Produce a long onboarding analysis for the truncation guard test",
            initiator="Test",
        )
        # Plan, deliverable, verification stages.
        for _ in range(4):
            mission = self.dispatcher.execute_compound_mission_step(mission.mission_id)
            if mission.status in (
                MissionState.COMPLETED.value,
                MissionState.UNCERTAIN.value,
                MissionState.BLOCKED.value,
                MissionState.FAILED.value,
            ):
                break

        self.assertEqual(mission.status, MissionState.UNCERTAIN.value)
        self.assertIsNone(mission.evidence_id)
        stages = [e["stage"] for e in mission.timeline]
        self.assertIn("DELIVERABLE_TRUNCATED", stages)
        self.assertIn("VERIFICATION_REFUSED", stages)

        self.assertTrue(mission.deliverables)
        with open(mission.deliverables[-1], "rb") as f:
            blob = f.read()
        self.assertIn(b"DELIVERABLE_TRUNCATED", blob)
        # The truncated body must be retained for audit, not silently dropped.
        self.assertIn(TRUNCATED_CONTENT.encode()[:40], blob)


if __name__ == "__main__":
    unittest.main()
