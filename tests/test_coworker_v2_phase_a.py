"""
ZONATA Autonomous Coworker 2.0 — Phase A Comprehensive Verification Suite
Tests Milestones 1 to 4:
  - Milestone 1: 12-State Task Lifecycle, DB Store, Leases, Cleanups, Patrols, Orchestrator.
  - Milestone 2: 5-Level Execution Decision Ladder, AST Screening, License Audit, Sandbox, Rollback.
  - Milestone 3: 14 GUI Automation Primitives, Perception Engine, Hermes, OpenCloud, OpenDots.
  - Milestone 4: 10 Subworker Archetypes, Ephemeral Agent Factory, Subordination Invariants.
"""

import os
import sys
import time
import uuid
import pytest
import tempfile
import shutil

# Ensure workspace root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.contracts_v2 import (
    TaskLifecycleState, VALID_TRANSITIONS, CoworkerV2Task,
    TaskStateTransition, CoworkerExecutionLease, LeaseStatus,
    CleanupManifestRecord, CleanupResourceType, CleanupStatus,
    SecurityPatrolFinding, PatrolType, PatrolSeverity
)
from core.coworker.db_store_v2 import CoworkerDbStoreV2
from core.coworker.orchestrator_v2 import CoworkerLifecycleOrchestrator, InvalidStateTransitionError
from core.coworker.decision_engine import (
    ExecutionDecisionEngine, ExecutionLadderLevel, DecisionEvaluationResult
)
from core.coworker.computer_use_engine import (
    ComputerUseEngine, PerceptionEngine, BoundingBox, UIElement
)
from core.coworker.adapters.hermes_adapter import HermesComputerUseAdapter
from core.coworker.adapters.opencloud_adapter import OpenCloudAdapter
from core.coworker.adapters.opendots_adapter import OpenDotsAdapter
from core.coworker.subworkers_v2 import SubWorkerArchetype, ARCHETYPE_REGISTRY
from core.coworker.agent_factory_v2 import EphemeralAgentFactoryV2


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = CoworkerDbStoreV2(db_path=path)
    yield store
    if os.path.exists(path):
        os.remove(path)


# =============================================================================
# Milestone 1 Tests: 12-State Task Lifecycle & Orchestrator
# =============================================================================

def test_milestone_1_twelve_states_defined():
    expected_states = {
        "IDLE", "TASK_RECEIVED", "TASK_ANALYSIS", "TOOL_DISCOVERY",
        "EXECUTION", "VERIFICATION", "WAITING_FOR_APPROVAL",
        "REPORTING_TO_CEO", "SECURITY_MONITORING", "ERROR_RECOVERY",
        "PAUSED", "TERMINATED"
    }
    actual_states = {s.value for s in TaskLifecycleState}
    assert expected_states == actual_states
    assert len(TaskLifecycleState) == 12


def test_milestone_1_db_store_task_and_transitions(temp_db):
    task = CoworkerV2Task(
        task_id="task_test_01",
        mission_id="msn_01",
        tenant_id="tnt_test",
        company_id="cmp_test",
        title="Analyze Q4 Metrics",
        description="Run analysis",
        state=TaskLifecycleState.TASK_RECEIVED
    )
    temp_db.save_task(task)

    loaded = temp_db.get_task("task_test_01")
    assert loaded is not None
    assert loaded.title == "Analyze Q4 Metrics"
    assert loaded.state == TaskLifecycleState.TASK_RECEIVED

    # Record transition
    trans = TaskStateTransition(
        transition_id="tr_01",
        task_id="task_test_01",
        from_state=TaskLifecycleState.TASK_RECEIVED,
        to_state=TaskLifecycleState.TASK_ANALYSIS,
        reason="Initial analysis started"
    )
    temp_db.record_transition(trans)
    transitions = temp_db.get_transitions("task_test_01")
    assert len(transitions) == 1
    assert transitions[0].to_state == TaskLifecycleState.TASK_ANALYSIS


def test_milestone_1_orchestrator_valid_and_invalid_transitions(temp_db):
    orch = CoworkerLifecycleOrchestrator(db_store=temp_db)
    task = CoworkerV2Task(
        task_id="task_orch_01",
        mission_id="msn_orch",
        tenant_id="tnt_primary",
        company_id="cmp_primary",
        title="Build Report",
        description="Compile quarterly report",
        state=TaskLifecycleState.TASK_RECEIVED
    )
    temp_db.save_task(task)

    # Valid: TASK_RECEIVED -> TASK_ANALYSIS
    updated = orch.transition_to("task_orch_01", TaskLifecycleState.TASK_ANALYSIS, reason="Begin analysis")
    assert updated.state == TaskLifecycleState.TASK_ANALYSIS

    # Invalid: TASK_ANALYSIS -> REPORTING_TO_CEO (Must go through TOOL_DISCOVERY / EXECUTION / VERIFICATION)
    with pytest.raises(InvalidStateTransitionError):
        orch.transition_to("task_orch_01", TaskLifecycleState.REPORTING_TO_CEO, reason="Skip pipeline")


def test_milestone_1_crash_recovery_and_cleanup(temp_db):
    orch = CoworkerLifecycleOrchestrator(db_store=temp_db)
    now = time.time()
    task = CoworkerV2Task(
        task_id="task_crashed_01",
        mission_id="msn_crash",
        tenant_id="tnt_primary",
        company_id="cmp_primary",
        title="Hanging Execution",
        description="Worker node crashed",
        state=TaskLifecycleState.EXECUTION
    )
    temp_db.save_task(task)

    # Expired lease
    lease = CoworkerExecutionLease(
        lease_id="lease_expired_01",
        task_id="task_crashed_01",
        worker_id="worker_crashed",
        acquired_at=now - 500,
        expires_at=now - 100,
        heartbeat_at=now - 400,
        status=LeaseStatus.ACTIVE
    )
    temp_db.save_lease(lease)
    task.lease_id = lease.lease_id
    temp_db.save_task(task)

    # Recover crashes
    recovered = orch.recover_crashes(max_stale_seconds=60)
    assert len(recovered) == 1
    assert recovered[0].task_id == "task_crashed_01"
    assert recovered[0].state == TaskLifecycleState.ERROR_RECOVERY


# =============================================================================
# Milestone 2 Tests: 5-Level Intelligent Execution Decision Engine
# =============================================================================

def test_milestone_2_level_1_posix_detection(temp_db):
    engine = ExecutionDecisionEngine(db_store=temp_db)
    res = engine.evaluate_level_1_posix("git status")
    assert res is not None
    assert res.level == ExecutionLadderLevel.LEVEL_1_POSIX
    assert res.resolved is True
    assert "posix_git" in res.capability_name


def test_milestone_2_level_3_ast_and_license_screening(temp_db):
    engine = ExecutionDecisionEngine(db_store=temp_db)

    # Clean MIT package
    clean_code = "import json\ndef process(data):\n    return json.loads(data)\n"
    res_clean = engine.evaluate_level_3_discovery("json_helper", "MIT", clean_code)
    assert res_clean.resolved is True
    assert res_clean.license_status == "APPROVED"
    assert res_clean.security_score >= 0.70

    # Rejected GPL license
    res_gpl = engine.evaluate_level_3_discovery("gpl_lib", "GPL-3.0", clean_code)
    assert res_gpl.resolved is False
    assert res_gpl.license_status == "REJECTED_OR_QUARANTINED"

    # Insecure AST code (contains eval and credential path)
    bad_code = "import os\ndef exploit():\n    eval('2+2')\n    with open('/etc/shadow') as f: return f.read()\n"
    res_bad = engine.evaluate_level_3_discovery("sketchy_tool", "MIT", bad_code)
    assert res_bad.resolved is False
    assert res_bad.security_score < 0.70


def test_milestone_2_level_5_execution_and_rollback(temp_db):
    engine = ExecutionDecisionEngine(db_store=temp_db)
    cmd = [sys.executable, "-c", "import sys; print('HELLO_ZONATA')"]
    out = engine.execute_with_verification_and_rollback(
        cmd,
        verify_fn=lambda stdout, stderr: "HELLO_ZONATA" in stdout
    )
    assert out.success is True
    assert out.verification_passed is True
    assert len(out.output_hash) == 64

    # Test rollback trigger on failure
    rollback_called = [False]
    def on_rollback():
        rollback_called[0] = True
        return True

    failing_cmd = [sys.executable, "-c", "import sys; sys.exit(1)"]
    out_fail = engine.execute_with_verification_and_rollback(failing_cmd, rollback_fn=on_rollback)
    assert out_fail.success is False
    assert rollback_called[0] is True
    assert out_fail.rollback_applied is True


# =============================================================================
# Milestone 3 Tests: Desktop Computer-Use Engine & Adapters
# =============================================================================

def test_milestone_3_computer_use_primitives():
    engine = ComputerUseEngine(display_width=1920, display_height=1080)

    # 1. observe
    obs = engine.observe()
    assert obs.screen_width == 1920
    assert len(obs.elements) >= 4
    # The element tree is seeded, so the observation must say so.
    assert obs.synthetic is True
    assert obs.elements[0].metadata["source"] == "seeded_scene"

    # 2. click (cursor tracking is local; execution is reported honestly)
    res_click = engine.click(600, 450)
    assert engine.cursor_x == 600
    assert engine.cursor_y == 450
    if not os.environ.get("DISPLAY"):
        assert res_click["executed"] is False
        assert res_click["status"] == "ACTION_NOT_IMPLEMENTED"
        assert res_click["reason"] == "NO_DISPLAY"

    # 3. double_click
    engine.double_click(200, 100)
    assert engine.cursor_x == 200

    # 4. type & key
    engine.type_text("Hello ZONATA")
    engine.press_key("Return")

    # 5. verify: the seeded scene cannot prove anything about the host screen
    passed = engine.verify("element_present", "Submit")
    assert passed is False
    if not os.environ.get("DISPLAY"):
        assert engine.verify("cursor_at", (200, 100)) is False

    # 6. screenshot (placeholder bytes in headless mode, and flagged as such)
    png = engine.screenshot()
    assert png.startswith(b"\x89PNG")
    assert engine.last_screenshot_synthetic is (not bool(os.environ.get("DISPLAY")))


def test_milestone_3_hermes_adapter():
    engine = ComputerUseEngine()
    adapter = HermesComputerUseAdapter(engine=engine)
    schema = adapter.get_tool_schema()
    assert schema["function"]["name"] == "computer_use"

    # Call observe: headless perception is seeded, so it must not claim success
    call_obs = adapter.execute_hermes_call({"action": "observe"})
    assert "elements_detected" in call_obs
    if not os.environ.get("DISPLAY"):
        assert call_obs["status"] == "PARTIAL"
        assert call_obs["reason"] == "PERCEPTION_NOT_IMPLEMENTED"

    # Call click: the tool status must mirror what the host actually did
    call_click = adapter.execute_hermes_call({"action": "click", "coordinate": [500, 300]})
    assert engine.cursor_x == 500
    if not os.environ.get("DISPLAY"):
        assert call_click["status"] == "ACTION_NOT_IMPLEMENTED"
        assert call_click["executed"] is False


def test_milestone_3_opendots_grounding_adapter():
    engine = ComputerUseEngine(display_width=1920, display_height=1080)
    adapter = OpenDotsAdapter(screen_width=1920, screen_height=1080, engine=engine)
    assert adapter.SPECIFICATION["license"] == "Apache-2.0"

    # Ground exact element
    target = adapter.ground_intent("Submit")
    assert target.source == "PERCEPTION_TREE"
    assert target.predicted_x > 0 and target.predicted_y > 0

    # Ground search intent via anchor heuristic
    search_target = adapter.ground_intent("search input bar")
    assert search_target.confidence >= 0.70


# =============================================================================
# Milestone 4 Tests: Ephemeral Specialized Agent Factory & Subworkers
# =============================================================================

def test_milestone_4_ten_subworker_archetypes():
    assert len(SubWorkerArchetype) == 10
    expected = [
        "Research Specialist", "Software Installation Specialist",
        "Browser Automation Specialist", "Data Processing Specialist",
        "Python Dev Specialist", "Linux Admin Specialist",
        "Document Specialist", "Testing Specialist",
        "Diagnostics Specialist", "Cybersecurity Analyst"
    ]
    for exp in expected:
        assert any(a.value == exp for a in SubWorkerArchetype)


def test_milestone_4_ephemeral_agent_factory_invariants(temp_db):
    factory = EphemeralAgentFactoryV2(db_store=temp_db)
    parent_task = CoworkerV2Task(
        task_id="parent_task_01",
        mission_id="msn_p01",
        tenant_id="tnt_test",
        company_id="cmp_test",
        title="Security Audit & Remediation",
        description="Audit python codebase",
        authority_scope=["python3", "ast_lint"],
        budget_allocated_usd=3.00,
        budget_spent_usd=1.00
    )
    temp_db.save_task(parent_task)

    # Spawn Cybersecurity Analyst
    subworker = factory.spawn_subworker(
        parent_task=parent_task,
        archetype=SubWorkerArchetype.CYBERSECURITY_ANALYST,
        micro_budget_usd=1.50
    )

    # Invariant 1: Budget Invariant (child budget <= parent remaining 2.00)
    assert subworker.budget_limit_usd <= 2.00
    assert subworker.status == "ACTIVE"

    # Invariant 2: Subordinate scope invariant
    assert "read_only" in subworker.authority_scope or any(
        s in parent_task.authority_scope for s in subworker.authority_scope
    )

    # Decommission subworker
    decomm = factory.decommission_subworker(subworker.worker_id, reason="audit_complete")
    assert decomm is True
    reloaded = temp_db.get_subworker(subworker.worker_id)
    assert reloaded.status == "DECOMMISSIONED"
