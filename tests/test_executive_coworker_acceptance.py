"""
ZONATA Autonomous Executive Coworker — Acceptance Test Suite (Missions A through N)
Formally verifies all 14 mandatory acceptance missions per Section 17 of the Master Engineering Directive.
"""

import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.acceptance_missions import AcceptanceMissionsHarness, MissionOutcome
from core.coworker.executive_operating_loop import (
    OperatingPriority, WorkItemStatus, ExecutiveOperatingLoop
)
from core.coworker.local_inference_adapter import (
    HardwareBudget, LocalInferenceStatus, LocalInferenceAdapter
)
from core.coworker.dlp_engine import DLPEngine, DLPChannel, DLPRiskLevel
from core.coworker.credential_masking_tracker import CredentialMaskingTracker
from core.coworker.archetype_contracts import SpecialistRole, ARCHETYPE_CONTRACTS
from core.coworker.specialist_team_assembler import SpecialistTeamAssembler
from core.coworker.capability_registry_v3 import CapabilityRegistryV3


@pytest.fixture
def harness():
    return AcceptanceMissionsHarness()


def test_mission_a_ceo_assignment(harness):
    """Mission A: CEO Assignment & Cryptographic Evidence Sealing."""
    outcome = harness.run_mission_a_ceo_assignment()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_A"
    assert len(outcome.evidence_token) > 0
    assert len(outcome.artifacts) > 0


def test_mission_b_specialist_capability_expansion(harness):
    """Mission B: Specialist Capability Expansion & AST License Screening."""
    outcome = harness.run_mission_b_capability_expansion()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_B"
    assert len(outcome.evidence_token) > 0


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
    """Mission E: Desktop Visual Operation & Window Tree Verification."""
    outcome = harness.run_mission_e_desktop_operation()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_E"
    assert outcome.details.get("execution_mode") is not None


def test_mission_f_autonomous_software_dev(harness):
    """Mission F: Autonomous Software Development & Worktree Defect Repair."""
    outcome = harness.run_mission_f_autonomous_software_dev()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_F"


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
    """Mission I: Sensitive File Protection & Red-Line Data Loss Prevention."""
    outcome = harness.run_mission_i_sensitive_file_protection()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_I"


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
    """Mission L: Engine Crash Recovery & Task State Persistence."""
    outcome = harness.run_mission_l_recovery()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_L"


def test_mission_m_long_running_operation(harness):
    """Mission M: Sustained Priority Operating Loop & Resource Stability."""
    outcome = harness.run_mission_m_long_running_operation()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_M"


def test_mission_n_ceo_company_coordination(harness):
    """Mission N: Multi-Department CEO Coordination & Authority Boundary Integrity."""
    outcome = harness.run_mission_n_ceo_company_coordination()
    assert outcome.passed is True
    assert outcome.mission_code == "MISSION_N"


def test_local_inference_adapter_and_hardware_budget():
    """Unit test for local inference adapter under ARM64 620MB RAM constraint."""
    adapter = LocalInferenceAdapter()
    budget = adapter.budget
    assert budget.total_system_ram_mb == 620.0
    assert budget.max_process_ram_mb == 180.0
    status = adapter.inspect_inference_health()
    assert status.status in ("ONLINE", "RUNTIME_CASCADE_AVAILABLE", "LLM_UNAVAILABLE")
    # When unconfigured, reports LLM_UNAVAILABLE; when runtime cascade succeeds, reports COMPLETED
    completion = adapter.dispatch_hermes_reasoning([{"role": "user", "content": "hi"}])
    assert completion.get("status") in ("LLM_UNAVAILABLE", "COMPLETED")
    if not status.available and not completion.get("available"):
        assert completion.get("status") == "LLM_UNAVAILABLE"
        assert completion.get("content") == ""


def test_dlp_12_categories_and_masking():
    """Unit test for DLP 12-category scanning and salted HMAC origin tracking."""
    engine = DLPEngine()
    tracker = CredentialMaskingTracker()

    secret = "ghp_123456789012345678901234567890123456"
    masked = tracker.mask_and_register_secret(secret, "LLM", "agent_tester")
    assert "[REDACTED:FP:" in masked

    traces = tracker.trace_origin(masked)
    assert len(traces) == 1
    assert traces[0]["origin_actor"] == "agent_tester"

    res = engine.scan(f"Check my token {secret}", DLPChannel.TERMINAL_COMMAND)
    assert res.clean is False
    assert res.highest_risk == DLPRiskLevel.CRITICAL


def test_12_archetype_contracts_completeness():
    """Unit test verifying all 12 specialist archetypes are formally specified."""
    assert len(ARCHETYPE_CONTRACTS) == 12
    for role, contract in ARCHETYPE_CONTRACTS.items():
        assert contract.role == role
        assert len(contract.allowed_capabilities) > 0
        assert "type" in contract.input_schema
        assert "type" in contract.output_schema
        assert contract.quota_ram_mb <= 512
