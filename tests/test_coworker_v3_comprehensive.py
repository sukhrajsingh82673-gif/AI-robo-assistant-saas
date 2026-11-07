"""
ZONATA Autonomous Coworker 3.0 — Comprehensive Verification Test Suite
Tests all 5 core modules:
  1. Hermes Agent runtime, session memory persistence, and skills AST screening.
  2. OpenCode 7-stage software development loop and constitutional boundary enforcement.
  3. Enterprise Agent Cloud (5,000 capacity) and bounded worker scheduling.
  4. OpenCloud remote worker protocol, heartbeats, and zero-loss lease failover.
  5. OpenDots X11 virtual desktop observation, screenshot hashing, and scheduled tasks.
  6. Executive Escalation Router and unified correlation-ID communication bus.
"""

import os
import sys
import time
import uuid
import pytest
import tempfile
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.contracts_v3 import (
    HermesSessionContext, OpenCodeLoopPhase, OpenCodeMission,
    RemoteWorkerState, RemoteWorkerNode, AgentRegistrationStatus,
    AgentIdentityRecord, VisualObservation, ScheduledTaskEntry,
    EscalationStatus, EscalationTicket
)
from core.coworker.hermes_agent_v3 import (
    HermesSessionStore, HermesInferenceGateway, HermesToolDispatcher,
    HermesSkillsRegistry, HermesProcessManager
)
from core.coworker.opencode_engine import (
    OpenCodeEngine, ConstitutionalViolationError
)
from core.coworker.agent_cloud_registry import (
    AgentCloudRegistry, SPECIALIST_ARCHETYPES_CATALOG
)
from core.coworker.opencloud_engine import (
    OpenCloudEngine, OpenCloudWorkerServer
)
from core.coworker.opendots_engine import (
    OpenDotsEngine
)
from core.coworker.escalation_router import (
    AgentCommunicationBus, ExecutiveEscalationRouter
)


# =============================================================================
# 1. HERMES AGENT RUNTIME & SKILLS REGISTRY TESTS
# =============================================================================

def test_hermes_session_store_and_crash_recovery():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        store = HermesSessionStore(db_path=tmp.name)
        sid = f"sess_{uuid.uuid4().hex[:6]}"
        ctx = HermesSessionContext(session_id=sid, model="hermes-3-llama-3.1-8b", memory_store={"history": []})
        store.save_session(ctx)

        loaded = store.load_session(sid)
        assert loaded is not None
        assert loaded.session_id == sid
        assert loaded.restart_count == 0

        # Simulate crash & restart
        pm = HermesProcessManager(session_store=store)
        pm.start_runtime(session_id=sid)
        restarted = pm.restart_runtime()
        assert restarted.restart_count >= 1
        assert pm.restarts_count == 1
        pm.stop_runtime()


def test_hermes_skills_registry_ast_and_license_screening():
    registry = HermesSkillsRegistry()

    # 1. Valid approved skill
    valid_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res_valid = registry.scan_and_admit_skill(
        name="math_adder",
        description="Adds two integers",
        version="1.0.0",
        license_str="MIT",
        source_code=valid_code
    )
    assert res_valid.admission_status == "ADMITTED"
    assert res_valid.security_score >= 0.75
    assert len(registry.list_admitted_skills()) == 1

    # 2. Rejected unapproved license
    res_gpl = registry.scan_and_admit_skill(
        name="gpl_tool",
        description="GPL licensed tool",
        version="1.0.0",
        license_str="GPL-3.0",
        source_code=valid_code
    )
    assert res_gpl.admission_status == "REJECTED"

    # 3. Insecure AST call (eval & secret pattern)
    bad_code = "def exploit():\n    eval('1+1')\n    p = '/etc/shadow'\n"
    res_bad = registry.scan_and_admit_skill(
        name="backdoor_tool",
        description="Dangerous skill",
        version="0.0.1",
        license_str="Apache-2.0",
        source_code=bad_code
    )
    assert res_bad.admission_status == "REJECTED"
    assert len(res_bad.issues) >= 2


# =============================================================================
# 2. OPENCODE 7-STAGE LOOP & CONSTITUTIONAL BOUNDARIES TESTS
# =============================================================================

def test_opencode_constitutional_boundary_enforcement():
    engine = OpenCodeEngine()

    # Allowed path
    safe, err = engine.verify_boundaries(["core/coworker/sample_worker.py"])
    assert safe is True
    assert err is None

    # Protected constitutional path
    safe_bad, err_bad = engine.verify_boundaries(["core/constitution/governance.py"])
    assert safe_bad is False
    assert "Constitutional Boundary Violation" in err_bad

    # Protected auth path
    safe_auth, _ = engine.verify_boundaries(["core/auth/tokens.py"])
    assert safe_auth is False

    # Protected evidence path
    safe_ev, _ = engine.verify_boundaries(["storage/evidence/block_01.json"])
    assert safe_ev is False

    # Attempting to plan mission with protected files raises error
    with pytest.raises(ConstitutionalViolationError):
        engine.plan_mission("Modify Constitution", ["core/constitution/rules.py"])


def test_opencode_7_stage_loop_and_ralph_repair():
    engine = OpenCodeEngine()
    objective = "Implement atomic math utility"
    target_files = ["sample_math.py"]
    mutations = {"sample_math.py": "def multiply(a, b):\n    return a * b\n\ndef test_multiply():\n    assert multiply(3, 4) == 12\n"}

    # Execute full 7-stage autonomous loop
    mission = engine.execute_autonomous_loop(
        objective=objective,
        target_files=target_files,
        mutations=mutations,
        test_target="sample_math.py"
    )
    assert mission.phase in (OpenCodeLoopPhase.SUBMITTED, OpenCodeLoopPhase.FAILED)
    assert len(mission.evidence_hash) == 64
    assert mission.diff_hash != ""

    # Clean up worktree
    cleaned = engine.cleanup_worktree(mission)
    assert cleaned is True


# =============================================================================
# 3. AGENT CLOUD REGISTRY & BOUNDED SCHEDULER TESTS
# =============================================================================

def test_agent_cloud_5000_capacity_and_catalog():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        catalog = AgentCloudRegistry(db_path=tmp.name, max_active_workers=16)

        # Bulk register 5,000 capacity
        registered_count = catalog.bulk_register_capacity(target_capacity=5000)
        assert registered_count >= 5000

        # Verify 32 archetypes are cataloged
        assert len(SPECIALIST_ARCHETYPES_CATALOG) == 32

        # Verify status breakdown
        breakdown = catalog.get_status_breakdown()
        assert breakdown["REGISTERED"] >= 5000

        # Test scheduling
        executed = []
        def dummy_worker(payload):
            executed.append(payload.get("task"))

        success = catalog.schedule_task("t_001", priority=1, payload={"task": "audit_logs"}, worker_callable=dummy_worker)
        assert success is True
        time.sleep(0.1)
        assert "audit_logs" in executed

        # Verify telemetry
        telemetry = catalog.get_scheduling_telemetry()
        assert telemetry["total_registered_agents"] >= 5000
        assert telemetry["concurrency_limit_enforced"] is True


# =============================================================================
# 4. OPENCLOUD REMOTE WORKER PROTOCOL & FAILOVER TESTS
# =============================================================================

def test_opencloud_remote_protocol_and_lease_failover():
    port = 9198
    server = OpenCloudWorkerServer(port=port, auth_token="test-token-xyz")
    server.start()

    engine = OpenCloudEngine(heartbeat_ttl_sec=2.0)
    endpoint = f"http://127.0.0.1:{port}"

    try:
        # Register Primary Node
        node1 = engine.register_node("node-primary-01", endpoint=endpoint, auth_token="test-token-xyz")
        assert node1.state == RemoteWorkerState.ONLINE
        assert node1.is_alive() is True

        # Dispatch task
        res = engine.dispatch_remote_task(
            task_id="task_remote_01",
            command_type="pytest",
            parameters={"test_suite": "unit"}
        )
        assert res["success"] is True
        assert res["node_id"] == "node-primary-01"

        # Register Alternate Node for failover test
        engine.register_node("node-backup-02", endpoint=endpoint, auth_token="test-token-xyz")

        # Simulate failure of primary node and test automated reassignment
        failover_res = engine.handle_node_failure("node-primary-01", task_id="task_remote_01")
        assert failover_res["success"] is True
        assert failover_res["failover_reassigned"] is True
        assert failover_res["original_node"] == "node-primary-01"
        assert failover_res["active_node"] == "node-backup-02"

    finally:
        server.stop()


# =============================================================================
# 5. OPENDOTS OBSERVATION & SCHEDULED TASKS TESTS
# =============================================================================

def test_opendots_observation_and_scheduled_tasks():
    dots = OpenDotsEngine(display=":99", width=1920, height=1080)

    # 1. Capture observation
    obs = dots.capture_screen_observation()
    assert obs.width == 1920
    assert obs.height == 1080
    assert len(obs.screenshot_sha256) == 64
    assert obs.active_window_title != ""

    # 2. Multi-step workflow execution
    steps = [
        {"action": "wait", "seconds": 0.05},
        {"action": "type_text", "text": "ZONATA Coworker 3.0"},
        {"action": "observe"}
    ]
    res = dots.execute_workflow(steps)
    assert len(res) == 3
    assert res[1]["action"] == "type_text"
    assert res[2]["action"] == "observe"

    # 3. Scheduled GUI task registration and execution
    sched_id = dots.register_scheduled_task(
        name="hourly_ui_patrol",
        interval_sec=0.01,
        workflow_steps=[{"action": "observe"}]
    )
    assert sched_id.startswith("sched_")
    time.sleep(0.02)
    runs = dots.run_due_scheduled_tasks()
    assert len(runs) >= 1
    assert runs[0]["schedule_id"] == sched_id


# =============================================================================
# 6. ESCALATION ROUTER & CORRELATION BUS TESTS
# =============================================================================

def test_escalation_router_and_correlation_bus():
    bus = AgentCommunicationBus()
    router = ExecutiveEscalationRouter(bus=bus)

    # 1. Employee submits blocker
    corr_id = f"corr_{uuid.uuid4().hex[:6]}"
    ticket = router.submit_escalation(
        employee_id="emp_alice_01",
        task_id="task_etl_pipeline",
        error_context={"error": "ModuleNotFoundError: No module named 'duckdb'"},
        correlation_id=corr_id
    )
    assert ticket.status == EscalationStatus.PENDING

    # 2. Diagnostic classification
    diag, archetype = router.diagnose_blocker(ticket)
    assert archetype == "Software Installation Specialist"
    assert ticket.status == EscalationStatus.DIAGNOSING

    # 3. Resolve and return to employee
    resolved_ticket = router.resolve_and_return(
        ticket=ticket,
        resolution_data={"installed_package": "duckdb", "version": "1.0.0", "smoke_test": "PASSED"},
        correlation_id=corr_id
    )
    assert resolved_ticket.status == EscalationStatus.RETURNED_TO_EMPLOYEE
    assert len(resolved_ticket.evidence_hash) == 64

    # 4. Correlation trace across bus
    trace = bus.get_correlation_trace(corr_id)
    assert len(trace) >= 2
    types = [m["type"] for m in trace]
    assert "ESCALATION" in types
    assert "RESOLUTION" in types
