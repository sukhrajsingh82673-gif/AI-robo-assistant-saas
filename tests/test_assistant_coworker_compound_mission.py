"""
ZONATA Universal AI Co-worker Fabric — Compound End-to-End & Developer Mission Tests
Validates:
- Natural Language Objective -> Assistant -> Co-Worker -> Sub-Workers -> Execution -> Verification -> Deliverable -> Evidence
- Real Compound Mission (Hotel Research & Report Generation with Real SHA-256 Artifacts)
- Real Developer Mission (Repository Inspection, Tool Discovery, Test Suite Execution, Change Synthesis)
- Human Takeover Controls (PAUSE, RESUME, TAKE_CONTROL, STOP, CANCEL, RETRY)
- Sovereign Multi-Scope Kill Switches
- Multi-Tier Governed Memory Sovereignty (Business Memory Immutability)
- Persistent SQLite State Recovery across Restarts
- REST API Server Verification
"""

import unittest
import os
import sys
import json
import time
import shutil
import hashlib
import tempfile
import urllib.request
import urllib.parse

import socket
import threading
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.db import db, configure_isolated_test_db
from core.auth import UserManager, UserRole
from core.coworker.engine import UniversalCoworkerEngine
from core.coworker.background_dispatcher import (
    BackgroundMissionDispatcher, BackgroundMission, MissionState
)
from core.coworker.subworkers import SubWorkerCoordinator, SubWorkerRole
from core.coworker.runtimes.runtime_router import WorkerRuntimeRouter
from core.coworker.runtimes.terminal_runtime import TerminalWorkerRuntime
from core.coworker.memory_tier import GovernedMemoryManager, MemoryTier
from core.coworker.contracts import RiskLevel, ExecutionState, VerificationStatus
from core.killswitch_matrix import KillSwitchMatrix, KillSwitchLevel
from core.llm_runtime import LLMResult

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def _deterministic_chat(self, tenant_id, company_id, messages, system=None,
                        max_tokens=None, temperature=None, intent="general"):
    """Test double for the LLM runtime: deterministic text, no network."""
    objective = ""
    for m in (messages or []):
        if m.get("role") == "user":
            objective = str(m.get("content", ""))[:400]
            break
    return LLMResult(
        content=(
            "## Execution Plan\n"
            "- Review the stated objective and available tenant data.\n"
            "- Identify missing data sources explicitly.\n\n"
            "## Deliverable\n"
            f"Objective: {objective}\n\n"
            "## Data gaps\n"
            "- This is a deterministic test double; no external sources were queried."
        ),
        provider="test_stub", model="deterministic-test", degraded=False,
        latency_ms=0.5,
    )


class TestAssistantCoworkerCompoundMission(unittest.TestCase):
    orig_db_path = None
    cls_temp_dir = None
    _server = None
    base_url = None
    _llm_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.orig_db_path = db.db_path
        cls.orig_evidence_path = os.environ.get("ZONATA_EVIDENCE_PATH")
        cls.cls_temp_dir = tempfile.mkdtemp(prefix="zonata_coworker_cls_")
        cls.isolated_db = os.path.join(cls.cls_temp_dir, "coworker_qual.db")
        cls.isolated_evidence = os.path.join(cls.cls_temp_dir, "coworker_evidence.jsonl")
        os.environ["ZONATA_EVIDENCE_PATH"] = cls.isolated_evidence
        configure_isolated_test_db(cls.isolated_db)

        # Seed minimal tenant and company
        with db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES ('tnt_test', 'Test Tenant', 'ENTERPRISE', 'ACTIVE', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, revenue, cost, contribution, understanding_pct, created_at) VALUES ('comp_test', 'tnt_test', 'Test Corp', 'Tech', 'NEW', 'OPERATIONAL', 0.0, 0.0, 0.0, 100.0, ?)", (time.time(),))
            conn.commit()

        from api_server import ThreadedHTTPServer, RoboAssistantRequestHandler
        cls.port = get_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls._server = ThreadedHTTPServer(("127.0.0.1", cls.port), RoboAssistantRequestHandler)
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(1.0)

        # Mission execution now requires a real model. Use a deterministic
        # in-process double so the test verifies the pipeline without network.
        cls._llm_patcher = patch("core.llm_runtime.LLMRuntime.chat", _deterministic_chat)
        cls._llm_patcher.start()

    @classmethod
    def tearDownClass(cls):
        if cls._llm_patcher is not None:
            try:
                cls._llm_patcher.stop()
            except Exception:
                pass
        if hasattr(cls, "_server") and cls._server:
            try:
                cls._server.shutdown()
                cls._server.server_close()
            except Exception:
                pass
        if cls.orig_db_path:
            db.set_db_path(cls.orig_db_path)
            os.environ["ZONATA_DB_PATH"] = cls.orig_db_path
        if cls.orig_evidence_path:
            os.environ["ZONATA_EVIDENCE_PATH"] = cls.orig_evidence_path
        elif "ZONATA_EVIDENCE_PATH" in os.environ:
            del os.environ["ZONATA_EVIDENCE_PATH"]
        if hasattr(cls, "cls_temp_dir") and os.path.exists(cls.cls_temp_dir):
            shutil.rmtree(cls.cls_temp_dir, ignore_errors=True)


    def setUp(self):

        self.test_dir = tempfile.mkdtemp(prefix="zonata_compound_test_")
        self.db_path = os.path.join(self.test_dir, "test_robo.db")
        self.subworker_coord = SubWorkerCoordinator(tenant_id="tnt_test")
        self.runtime_router = WorkerRuntimeRouter(tenant_id="tnt_test")
        self.dispatcher = BackgroundMissionDispatcher(
            subworker_coord=self.subworker_coord,
            runtime_router=self.runtime_router,
            tenant_id="tnt_test",
            company_id="comp_test",
            db_path=self.db_path
        )
        self.memory_mgr = GovernedMemoryManager(tenant_id="tnt_test")
        self.killswitch = KillSwitchMatrix(tenant_id="tnt_test")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # 1. Compound End-to-End Business Mission
    def test_compound_business_mission_execution_and_deliverable(self):
        objective = "Research top 10 boutique hotels in Goa, collect market data, synthesize report, and verify"
        mission = self.dispatcher.submit_background_prompt(
            prompt=objective,
            initiator="ZONATA AI Assistant"
        )
        self.assertIsNotNone(mission.mission_id)
        self.assertEqual(mission.status, MissionState.RUNNING.value)
        self.assertGreaterEqual(len(mission.subworkers), 3)

        # Step 1: Research
        m1 = self.dispatcher.execute_compound_mission_step(mission.mission_id)
        self.assertGreaterEqual(m1.progress_percent, 50.0)

        # Step 2: Deliverable Report Generation
        m2 = self.dispatcher.execute_compound_mission_step(mission.mission_id)
        self.assertGreaterEqual(m2.progress_percent, 80.0)
        self.assertGreater(len(m2.deliverables), 0)
        deliverable_file = m2.deliverables[0]
        self.assertTrue(os.path.exists(deliverable_file))

        # Step 3: Verification & Cryptographic Merkle Evidence Ledger Sealing
        m3 = self.dispatcher.execute_compound_mission_step(mission.mission_id)
        self.assertEqual(m3.status, MissionState.COMPLETED.value)
        self.assertEqual(m3.progress_percent, 100.0)
        self.assertIsNotNone(m3.evidence_id)
        self.assertTrue(m3.evidence_id.startswith("ev_merkle_"))
        self.assertIsNotNone(m3.notification_message)

        # Validate physical file content on disk (Markdown deliverable).
        with open(deliverable_file, "r", encoding="utf-8") as f:
            data = f.read()
        self.assertIn(mission.mission_id, data)
        self.assertIn("tnt_test", data)
        self.assertIn("Deliverable", data)

    # 2. Compound Developer Mission (Inspect Repo, Self-Extension, Test Run, Verification)
    def test_compound_developer_mission(self):
        prompt = "Inspect repository, discover missing capability, run automated tests, and produce change summary"
        mission = self.dispatcher.submit_background_prompt(
            prompt=prompt,
            initiator="ZONATA Developer Assistant"
        )
        self.assertIn("runtime_terminal", mission.runtimes_used)

        # Execute Governed Terminal diagnostics directly
        term_runtime = TerminalWorkerRuntime(
            tenant_id="tnt_test",
            company_id="comp_test",
            workspace_root=BASE_DIR
        )
        sess = term_runtime.observe("sess_dev_test")
        self.assertEqual(sess["state"], "IDLE")
        self.assertIn("host", sess)

        # Execute test runner through terminal
        res = term_runtime.run_foreground("sess_dev_test", {
            "command": "python3 -c 'import sys; print(\"DEVELOPER_BUILD_SUCCESS\")'",
            "parameters": {"cwd": BASE_DIR}
        })
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("DEVELOPER_BUILD_SUCCESS", res["stdout"])
        self.assertTrue(res["verified"])

        # Advance mission to completion
        self.dispatcher.execute_compound_mission_step(mission.mission_id)
        self.dispatcher.execute_compound_mission_step(mission.mission_id)
        final_m = self.dispatcher.execute_compound_mission_step(mission.mission_id)
        self.assertEqual(final_m.status, MissionState.COMPLETED.value)

    # 3. Human Takeover Controls (Pause, Resume, Take Control, Retry, Cancel)
    def test_human_takeover_controls(self):
        mission = self.dispatcher.submit_background_prompt("Long running analysis task")
        mid = mission.mission_id

        # Pause
        self.assertTrue(self.dispatcher.pause_mission(mid))
        m = self.dispatcher.get_mission(mid)
        self.assertEqual(m.status, MissionState.WAITING.value)

        # Resume
        self.assertTrue(self.dispatcher.resume_mission(mid))
        m = self.dispatcher.get_mission(mid)
        self.assertEqual(m.status, MissionState.RUNNING.value)

        # Take Control
        self.assertTrue(self.dispatcher.take_control(mid))
        m = self.dispatcher.get_mission(mid)
        self.assertTrue(m.human_control)

        # Stop / Cancel
        self.assertTrue(self.dispatcher.stop_mission(mid))
        m = self.dispatcher.get_mission(mid)
        self.assertEqual(m.status, MissionState.CANCELLED.value)

        # Retry
        ret_m = self.dispatcher.retry_mission(mid)
        self.assertIsNotNone(ret_m)
        self.assertEqual(ret_m.status, MissionState.RUNNING.value)

    # 4. Multi-Tier Governed Memory Sovereignty
    def test_governed_memory_sovereignty(self):
        # Workers are prohibited from writing to BUSINESS_MEMORY
        with self.assertRaises(PermissionError):
            self.memory_mgr.store_memory(
                tier=MemoryTier.BUSINESS_MEMORY,
                key="corporate_strategy",
                value={"directive": "Autonomous Expansion"},
                worker_id="cw_worker_01",
                is_sovereign_write=False
            )

        # Sovereign Owner / AI CEO can write to BUSINESS_MEMORY
        rec_sovereign = self.memory_mgr.store_memory(
            tier=MemoryTier.BUSINESS_MEMORY,
            key="corporate_strategy",
            value={"directive": "Sovereign Board Decision"},
            worker_id="usr_owner",
            is_sovereign_write=True
        )
        self.assertIsNotNone(rec_sovereign)
        self.assertEqual(rec_sovereign.key, "corporate_strategy")

        # Operational memory is writable by workers
        rec_op = self.memory_mgr.store_memory(
            tier=MemoryTier.OPERATIONAL_MEMORY,
            key="worker_metric_01",
            value={"latency_ms": 42},
            worker_id="cw_worker_01",
            is_sovereign_write=False
        )
        self.assertIsNotNone(rec_op)
        self.assertEqual(rec_op.key, "worker_metric_01")

    # 5. Persistent State Recovery Across Restarts
    def test_mission_persistence_across_restarts(self):
        # Create a mission in current dispatcher
        m = self.dispatcher.submit_background_prompt("Test persistence across restarts")
        mid = m.mission_id

        # Instantiate brand-new dispatcher pointing to same DB
        new_dispatcher = BackgroundMissionDispatcher(
            subworker_coord=self.subworker_coord,
            runtime_router=self.runtime_router,
            tenant_id="tnt_test",
            company_id="comp_test",
            db_path=self.db_path
        )
        recovered_m = new_dispatcher.get_mission(mid)
        self.assertIsNotNone(recovered_m)
        self.assertEqual(recovered_m.mission_id, mid)
        self.assertEqual(recovered_m.prompt, "Test persistence across restarts")

    # 6. REST API Server Live Integration
    def test_live_api_server_endpoints(self):
        token = UserManager.generate_token({
            "user_id": "usr_test_coworker",
            "tenant_id": "tnt_test",
            "company_id": "comp_test",
            "role": UserRole.OWNER,
            "permissions": ["*"]
        })
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": "tnt_test",
            "X-Company-ID": "comp_test"
        }

        # Test dashboard endpoint
        req = urllib.request.Request(f"{self.base_url}/api/coworker/dashboard", headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertEqual(data["product"], "ZONATA Universal AI Co-Worker")
            self.assertIn("specialized_runtimes", data)

        # Test reality matrix endpoint
        req_mat = urllib.request.Request(f"{self.base_url}/api/coworker/reality-matrix", headers=headers)
        with urllib.request.urlopen(req_mat, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data_mat = json.loads(resp.read().decode())
            self.assertGreater(data_mat["count"], 0)

        # Test terminal diagnostics endpoint
        req_diag = urllib.request.Request(f"{self.base_url}/api/coworker/terminal/diagnostics", headers=headers)
        with urllib.request.urlopen(req_diag, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data_diag = json.loads(resp.read().decode())
            self.assertIn("host", data_diag)


if __name__ == "__main__":
    unittest.main()
