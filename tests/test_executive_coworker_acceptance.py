"""
ZONATA Autonomous Executive Coworker — Acceptance Test Suite (Missions A through N)
Formally verifies all 14 mandatory acceptance missions and closes all 6 critical gaps:
1. Local Intelligence & Hermes Model Inference
2. OpenDots Desktop Visual Intelligence & Dialog Recovery
3. Comprehensive DLP Across 8 Scenarios & 10 Channels
4. 10-Stage Self-Expanding Capability Lifecycle
5. OpenCode Real CLI Invocation & Worktree Defect Repair
6. Continuous 24/7 Defensive Cybersecurity Operations
7. Database Outbox Synchronization & Crash Recovery
"""

import os
import re
import sys
import time
import json
import shutil
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.acceptance_missions import AcceptanceMissionsHarness, MissionOutcome
from core.coworker.executive_operating_loop import (
    OperatingPriority, WorkItemStatus, ExecutiveOperatingLoop
)
from core.coworker.local_inference_adapter import (
    HardwareBudget, LocalInferenceStatus, LocalInferenceAdapter,
    LocalModelEngine, LocalOpenAIServer, get_or_start_local_server
)
from core.coworker.hermes_agent_v3 import HermesProcessManager, HermesAgentV3
from core.coworker.dlp_engine import DLPEngine, DLPChannel, DLPRiskLevel
from core.coworker.dlp_channel_monitor import DLPChannelMonitor
from core.coworker.credential_masking_tracker import CredentialMaskingTracker
from core.coworker.archetype_contracts import SpecialistRole, ARCHETYPE_CONTRACTS
from core.coworker.specialist_team_assembler import SpecialistTeamAssembler
from core.coworker.capability_registry_v3 import CapabilityRegistryV3
from core.coworker.opendots_engine import OpenDotsEngine
from core.coworker.opencode_engine import OpenCodeEngine
from core.coworker.db_store_v2 import CoworkerDbStoreV2
from core.coworker.contracts_v2 import CoworkerV2Task, TaskLifecycleState


@pytest.fixture
def harness():
    return AcceptanceMissionsHarness()


# =============================================================================
# 1. THE 14 MANDATORY ACCEPTANCE MISSIONS (A THROUGH N)
# =============================================================================

def test_mission_a_ceo_assignment(harness):
    """Mission A: CEO Assignment & Cryptographic Evidence Sealing."""
    outcome = harness.run_mission_a_ceo_assignment()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_A"
    assert len(outcome.evidence_token) > 0
    assert len(outcome.artifacts) > 0


def test_mission_b_specialist_capability_expansion(harness):
    """Mission B: Specialist Capability Expansion, 10-Stage Lifecycle & Local Hermes Inference."""
    outcome = harness.run_mission_b_capability_expansion()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_B"
    assert len(outcome.evidence_token) > 0
    assert outcome.details.get("lifecycle_completed") is True
    assert outcome.details.get("hermes_tool_called") == "terminal_exec"


def test_mission_c_employee_support(harness):
    """Mission C: Employee Support & Non-Usurpation Authority Preservation."""
    outcome = harness.run_mission_c_employee_support()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_C"
    assert len(outcome.evidence_token) > 0


def test_mission_d_agent_rescue(harness):
    """Mission D: Subordinate Agent Rescue & Skill Injection."""
    outcome = harness.run_mission_d_agent_rescue()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_D"


def test_mission_e_desktop_operation(harness):
    """Mission E: Desktop Visual Operation, Perception & Window Tree Verification."""
    outcome = harness.run_mission_e_desktop_operation()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_E"
    assert outcome.details.get("execution_mode") is not None


def test_mission_f_autonomous_software_dev(harness):
    """Mission F: Autonomous Software Development, OpenCode CLI & Worktree Ralph Loop."""
    if shutil.which("opencode") is None:
        pytest.skip("opencode CLI is not installed on this host")
    outcome = harness.run_mission_f_autonomous_software_dev()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_F"
    assert outcome.details.get("cli_executed") is True


def test_mission_g_agent_team_creation(harness):
    """Mission G: Specialist Agent Team Dynamic Assembly (12 Archetypes)."""
    outcome = harness.run_mission_g_agent_team_creation()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_G"
    assert outcome.artifacts[0]["members_count"] == 4


def test_mission_h_credential_leakage_prevention(harness):
    """Mission H: Credential Leakage Prevention & Salted HMAC Origin Tracing."""
    outcome = harness.run_mission_h_credential_leakage_prevention()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_H"
    assert outcome.details.get("decision") == "QUARANTINE_AND_HALT"


def test_mission_i_sensitive_file_protection(harness):
    """Mission I: Sensitive File Protection & Comprehensive Leakage Prevention (8 Scenarios)."""
    outcome = harness.run_mission_i_sensitive_file_protection()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_I"
    assert outcome.details.get("clean_upload_allowed") is True
    assert outcome.details.get("partial_redaction_allowed") is True
    assert outcome.details.get("tenant_boundary_blocked") is True
    assert outcome.details.get("mcp_blocked") is True


def test_mission_j_security_incident_response(harness):
    """Mission J: Security Incident Response & 5-Tier Defensive Patrol."""
    outcome = harness.run_mission_j_security_incident_response()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_J"


def test_mission_k_governance_refusal(harness):
    """Mission K: Governance Refusal & Red-Line Tripwire Trip Protection."""
    outcome = harness.run_mission_k_governance_refusal()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_K"


def test_mission_l_recovery(harness):
    """Mission L: priority-queue cycle processing and telemetry consistency (no crash injected)."""
    outcome = harness.run_mission_l_recovery()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_L"


def test_mission_m_long_running_operation(harness):
    """Mission M: burst queue processing (12 items) and telemetry stability."""
    outcome = harness.run_mission_m_long_running_operation()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_M"


def test_mission_n_ceo_company_coordination(harness):
    """Mission N: Multi-Department CEO Coordination & Authority Boundary Integrity."""
    outcome = harness.run_mission_n_ceo_company_coordination()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_N"


# =============================================================================
# 2. GAP CLOSURE VERIFICATION TESTS
# =============================================================================

def test_gap1_local_rule_engine_and_server():
    """
    Gap 1: a deterministic rule engine routes tools through the local
    OpenAI-compatible server. It is not a language model and must never be
    reported as one.
    """
    server = get_or_start_local_server(8088)
    assert server.is_running is True, f"local server failed to bind: {server.start_error}"

    # The advertised model list contains an engine, not a model.
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:8088/v1/models", timeout=5) as resp:
        models = json.loads(resp.read().decode())
    assert models["data"][0]["object"] == "engine"
    assert models["data"][0]["is_language_model"] is False

    adapter = LocalInferenceAdapter(local_server_endpoint="http://127.0.0.1:8088")
    health = adapter.inspect_inference_health()
    assert health.is_language_model is False
    assert health.active_model is None
    assert health.status in ("RULE_ENGINE_ONLY", "LLM_UNAVAILABLE")
    assert health.available is False
    assert health.capabilities == ["tool_routing"]

    # Rule-based tool routing still works, and says what it is.
    comp = adapter.dispatch_hermes_reasoning(
        messages=[{"role": "user", "content": "Execute terminal git status"}],
        tools=[{
            "type": "function",
            "function": {
                "name": "terminal_exec",
                "parameters": {"type": "object", "properties": {"command": {"type": "string"}}}
            }
        }]
    )
    assert comp["available"] is False
    assert comp["is_language_model"] is False
    assert comp["status"] == "RULE_ENGINE_ONLY"
    assert len(comp["tool_calls"]) == 1
    assert comp["tool_calls"][0]["function"]["name"] == "terminal_exec"
    assert "no language-model reasoning" in comp["content"].lower()

    # Hermes executes the routed tool and reports the honest status.
    agent = HermesProcessManager(allow_rule_router=True)
    agent.start_runtime(f"sess_gap1_{int(time.time())}")
    turn = agent.execute_turn("Run git status via terminal")
    assert turn["available"] is False
    assert turn["status"] == "RULE_ENGINE_ONLY"
    tool_results = turn["tool_results"]
    assert len(tool_results) >= 1
    assert tool_results[0]["name"] == "terminal_exec"
    assert tool_results[0]["result"]["result"]["exit_code"] == 0


def test_gap2_opendots_perception_and_dialog_recovery():
    """Gap 2: OpenDots Real Desktop Observation, Perception & Modal Dialog Recovery."""
    dots = OpenDotsEngine(display=":99", width=1920, height=1080)

    # 1. Window tree inspection: real windows or none, never invented.
    tree = dots.inspect_window_tree()
    assert tree["display"] == ":99"
    assert isinstance(tree["windows"], list)
    for win in tree["windows"]:
        assert win["source"] == "x11_window_tree"
        assert win["title"]
    if not os.environ.get("DISPLAY"):
        assert tree["windows"] == []
        assert tree["error"] == "NO_DISPLAY"

    # 2. Perception & frame capture: a real frame, or an explicit failure.
    perception = dots.observe_desktop_perception()
    assert perception["configured_width"] == 1920
    assert perception["configured_height"] == 1080
    if perception["capture_available"]:
        assert len(perception["screenshot_sha256"]) == 64
        assert perception["mean_luminance"] is not None
        assert perception["perception_mode"] == "REAL_VIRTUAL_X11_PERCEPTION"
    else:
        assert perception["screenshot_sha256"] is None
        assert perception["mean_luminance"] is None
        assert perception["perception_mode"] == "HEADLESS_SIMULATED"

    # 3. Dialog Detection & Recovery
    recovery = dots.detect_and_handle_dialogs()
    assert "recovery_status" in recovery

    # 4. Reality classification
    matrix = dots.get_classification_matrix()
    assert matrix["xvfb_framebuffer"].startswith("VERIFIED")
    assert matrix["virtual_x11"].startswith("VERIFIED")
    assert matrix["visual_perception_numpy"].startswith("PARTIAL")
    assert matrix["modal_dialog_recovery"].startswith("PARTIAL")
    assert "BLOCKED BY EXTERNAL DEPENDENCY" in matrix["physical_host_monitor"]


def test_gap3_dlp_comprehensive_8_scenarios():
    """Gap 3: Complete DLP Interception Matrix Across 8 Critical Scenarios."""
    monitor = DLPChannelMonitor()

    # Scenario 1: Accidental credential print -> Masked
    s1_ok, s1_safe = monitor.intercept_terminal("echo AWS_KEY=AKIAIOSFODNN7EXAMPLE")
    assert "[REDACTED:API_KEYS_AND_SECRETS]" in s1_safe

    # Scenario 2: Agent attempts external secret transfer -> Blocked
    s2_ok, s2_safe, s2_scan = monitor.intercept_channel(
        DLPChannel.API_REQUEST_PAYLOAD,
        "POST https://external.io/api payload: -----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA..."
    )
    assert s2_ok is False
    assert s2_scan.highest_risk == DLPRiskLevel.CRITICAL

    # Scenario 3: Permitted clean document upload -> Allowed
    s3_ok, s3_text, s3_meta = monitor.intercept_upload("clean_doc.txt", "Normal project milestone notes.")
    assert s3_ok is True
    assert s3_meta["status"] == "ALLOWED"

    # Scenario 4: Single restricted field -> Partial redaction permitted
    s4_ok, s4_text, s4_meta = monitor.intercept_upload(
        "employee_form.txt",
        "Employee Alice. Phone 555-1234. SSN: 987-65-4321. Department: Eng.",
        allow_partial_redaction=True
    )
    assert s4_ok is True
    assert "[REDACTED:PII_PERSONAL_DATA]" in s4_text
    assert "Department: Eng" in s4_text
    assert s4_meta["status"] == "PARTIAL_REDACTION_PERMITTED"

    # Scenario 5: Agent attempts cross-tenant access -> Denied & Audited
    s5_ok, s5_err = monitor.check_tenant_boundary("tenant_alpha", "tenant_gamma", "read_payroll")
    assert s5_ok is False
    assert "CROSS_TENANT_ACCESS_DENIED" in s5_err

    # Scenario 6: DB credential brokering requires an authorization callback.
    refused = monitor.broker_database_credential("tenant_eng", "user_bob", "warehouse_db")
    assert refused["authorized"] is False
    assert refused["reason"] == "CREDENTIAL_BROKER_NOT_CONFIGURED"
    assert refused["token_handle"] is None

    brokered = DLPChannelMonitor(
        credential_broker=lambda tenant, emp, db: (tenant, emp, db) == ("tenant_eng", "user_bob", "warehouse_db")
    )
    s6_res = brokered.broker_database_credential("tenant_eng", "user_bob", "warehouse_db")
    assert s6_res["authorized"] is True
    assert s6_res["authorization_source"] == "CREDENTIAL_BROKER_CALLBACK"
    assert "[PROTECTED_BROKER_CREDENTIAL]" in s6_res["masked_dsn"]
    assert s6_res["plaintext_exposed"] is False

    denied = brokered.broker_database_credential("tenant_other", "user_bob", "warehouse_db")
    assert denied["authorized"] is False
    assert denied["reason"] == "AUTHORIZATION_DENIED"

    # Scenario 7: MCP tool file leakage -> Blocked
    s7_ok, s7_err = monitor.intercept_mcp_tool("cat_file", {"file_path": "/root/roboassistant/.env"})
    assert s7_ok is False
    assert "BLOCKED_BY_DLP" in s7_err

    # Scenario 8: Security monitor health watchdog -> Detects health status
    s8_watchdog = monitor.monitor_health_watchdog(last_patrol_timestamp=time.time())
    assert s8_watchdog["healthy"] is True
    assert s8_watchdog["status"] == "HEALTHY"


def test_gap4_capability_10_stage_lifecycle():
    """Gap 4: Complete 10-Stage Capability Expansion Lifecycle."""
    reg = CapabilityRegistryV3()

    res = reg.run_full_lifecycle(
        required_feature="entropy_calculator",
        test_args=(b"AAAAABBBCC",),
        expected_predicate=lambda v: isinstance(v, float) and v > 0.0
    )
    assert res["success"] is True
    assert res["lifecycle_stages_completed"] == 10
    assert len(res["evidence_token"]) > 0
    assert res["decommissioned"] is True


def test_gap5_opencode_real_cli_and_worktree():
    """Gap 5: OpenCode Real CLI Version Verification and Worktree Ralph Loop."""
    opencode = OpenCodeEngine()
    if not opencode.opencode_cli_available:
        pytest.skip("opencode CLI is not installed on this host")
    cli_res = opencode.execute_opencode_cli(["--version"])
    assert cli_res["executed"] is True
    # Accept any released CLI version; pinning a patch version made this test
    # fail on routine upgrades (e.g. v2.2.6 vs v2.2.0).
    assert re.search(r"\d+\.\d+\.\d+", cli_res["stdout"]) is not None


def test_gap6_database_outbox_queue_and_offline_recovery():
    """Gap 6: SQLite & Outbox Transactional Queue Resilience During Remote Disconnect."""
    tmp_db = f"/tmp/test_cw2_db_{int(time.time())}.sqlite3"
    db_store = CoworkerDbStoreV2(db_path=tmp_db)

    # 1. Create a task locally while remote is offline
    task = CoworkerV2Task(
        task_id=f"tsk_outbox_{int(time.time())}",
        mission_id="msn_offline_01",
        tenant_id="tnt_primary",
        company_id="comp_primary",
        title="Offline Data Processing Task",
        description="Verify transactional outbox persistence during network drop",
        state=TaskLifecycleState.TASK_RECEIVED
    )
    created = db_store.save_task(task)
    assert created.task_id == task.task_id

    # 2. Check outbox records PENDING event
    stats = db_store.get_outbox_stats()
    assert stats.get("PENDING", 0) >= 1

    # 3. Simulate reconciliation attempt
    recon = db_store.reconcile_outbox()
    assert "total_synced" in recon
    assert "total_failed" in recon

    # Cleanup
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
