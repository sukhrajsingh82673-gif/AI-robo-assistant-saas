"""
ZONATA Autonomous Coworker 2.0 — Phase B Comprehensive Verification Suite
Tests Milestones 5 to 7:
  - Milestone 5: Storage & Resource Guard, Pre-flight Checks, Workspace Isolation, Asset Protection, Safe Cleanup.
  - Milestone 6: Autonomous Defensive Cybersecurity Monitor, AST Scanning, Secrets & Entropy, Dependency & API Audit.
  - Milestone 7: Evidence, Cryptographic Merkle Sealing, Concurrency File Locking, AI CEO Executive Reporting.
"""

import os
import sys
import time
import uuid
import json
import pytest
import tempfile
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.coworker.contracts_v2 import (
    CleanupManifestRecord, CleanupResourceType, CleanupStatus,
    SecurityPatrolFinding, PatrolType, PatrolSeverity
)
from core.coworker.db_store_v2 import CoworkerDbStoreV2
from core.coworker.resource_guard import ResourceGuardEngine, HostResourceMetrics
from core.coworker.defense_monitor import DefensiveCybersecurityMonitor, calculate_shannon_entropy
from core.coworker.evidence_reporting import (
    EvidenceAndReportingEngine, VerificationOutcome, PhysicalVerificationCheck,
    ExecutiveDeliverable, AICeoExecutiveReport
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = CoworkerDbStoreV2(db_path=path)
    yield store
    if os.path.exists(path):
        os.remove(path)


# =============================================================================
# Milestone 5 Tests: Storage & Resource Management Engine
# =============================================================================

def test_milestone_5_host_resource_preflight_checks(temp_db):
    guard = ResourceGuardEngine(db_store=temp_db)
    metrics = guard.check_host_resources()

    assert metrics.free_ram_mb > 0
    assert metrics.free_disk_gb > 0
    assert metrics.cpu_percent >= 0
    # Host should meet basic health thresholds
    assert metrics.ram_healthy is True
    assert metrics.disk_healthy is True


def test_milestone_5_workspace_provisioning_and_cleanup(temp_db):
    temp_dir = tempfile.mkdtemp(prefix="zonata_ws_test_")
    try:
        guard = ResourceGuardEngine(db_store=temp_db, workspaces_root=temp_dir)
        ws_path = guard.provision_mission_workspace("msn_res_01", "task_res_01")
        assert os.path.exists(ws_path)
        assert ws_path.startswith(temp_dir)

        # Check that manifest record was created in DB
        pending = temp_db.list_pending_cleanups(mission_id="msn_res_01")
        assert len(pending) == 1
        assert pending[0].resource_path == ws_path

        # Create temporary file inside workspace
        dummy_file = os.path.join(ws_path, "temp_data.csv")
        with open(dummy_file, "w") as f:
            f.write("a,b,c\n1,2,3\n")
        assert os.path.exists(dummy_file)

        # Safe reclaim of workspace directory
        cleaned, err = guard.safe_reclaim_resource(pending[0])
        assert cleaned is True
        assert not os.path.exists(ws_path)
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_milestone_5_sovereign_asset_protection(temp_db):
    guard = ResourceGuardEngine(db_store=temp_db)

    # Sovereign asset paths must NEVER be allowed for cleanup
    assert guard.is_protected_path("/root/roboassistant/storage/evidence/audit_ledger.jsonl") is True
    assert guard.is_protected_path("/root/roboassistant/core/api_server.py") is True
    assert guard.is_protected_path("/root/roboassistant/storage/roboassistant.db") is True
    assert guard.is_protected_path("/etc/shadow") is True

    # Attempting to clean a protected file must be blocked
    protected_record = CleanupManifestRecord(
        manifest_id="mf_blocked_01",
        task_id="task_01",
        mission_id="msn_01",
        resource_type=CleanupResourceType.TEMP_FILE,
        resource_path="/root/roboassistant/storage/roboassistant.db"
    )
    cleaned, err = guard.safe_reclaim_resource(protected_record)
    assert cleaned is False
    assert "BLOCKED" in str(err)


# =============================================================================
# Milestone 6 Tests: Autonomous Defensive Cybersecurity Monitor
# =============================================================================

def test_milestone_6_shannon_entropy_calculation():
    # Low entropy plain english
    low_ent = calculate_shannon_entropy("aaaaaaaaaaaaaaaa")
    assert low_ent == 0.0

    # High entropy random base64 secret string
    high_ent = calculate_shannon_entropy("dK9#mQ2$zL8@pW4!vX1%nC7&jR3*bF5~")
    assert high_ent > 4.5


def test_milestone_6_ast_static_scan(temp_db):
    monitor = DefensiveCybersecurityMonitor(db_store=temp_db)

    # Create temporary python script with dangerous eval/exec
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("import math\ndef calc():\n    eval('1+1')\n    exec('x=2')\n")
        temp_file = f.name

    try:
        findings = monitor.scan_python_ast(temp_file)
        assert len(findings) >= 2
        types = [f.severity for f in findings]
        assert PatrolSeverity.HIGH in types
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_milestone_6_secrets_detection(temp_db):
    monitor = DefensiveCybersecurityMonitor(db_store=temp_db)
    leak_sample = "export OPENAI_API_KEY='sk-1234567890abcdef1234567890abcdef'\n"
    findings = monitor.scan_for_secrets(leak_sample, source_label="test_config.sh")

    assert len(findings) >= 1
    assert any(f.severity == PatrolSeverity.CRITICAL for f in findings)
    assert any("OpenAI" in f.description for f in findings)


def test_milestone_6_full_defensive_patrol_sweep(temp_db):
    monitor = DefensiveCybersecurityMonitor(db_store=temp_db)
    report = monitor.run_full_defensive_patrol()

    assert report["status"] == "COMPLETED"
    assert "total_findings" in report
    assert "findings" in report
    assert isinstance(report["findings"], list)


# =============================================================================
# Milestone 7 Tests: Evidence, Merkle Sealing & AI CEO Reporting
# =============================================================================

def test_milestone_7_physical_verification():
    temp_dir = tempfile.mkdtemp()
    try:
        engine = EvidenceAndReportingEngine(ledger_dir=temp_dir)
        deliverable_file = os.path.join(temp_dir, "ceo_deliverable.json")
        with open(deliverable_file, "w") as f:
            f.write('{"status": "SUCCESS", "records_processed": 500}\n')

        outcome, checks = engine.verify_file_deliverable(deliverable_file, min_bytes=10)
        assert outcome == VerificationOutcome.VERIFIED
        assert len(checks) >= 2
        assert all(c.passed for c in checks)

        # Non-existent file must FAIL verification
        bad_outcome, bad_checks = engine.verify_file_deliverable(os.path.join(temp_dir, "missing.json"))
        assert bad_outcome == VerificationOutcome.FAILED
        assert not bad_checks[0].passed
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_milestone_7_merkle_sealing_concurrency(temp_db):
    temp_dir = tempfile.mkdtemp()
    try:
        engine = EvidenceAndReportingEngine(ledger_dir=temp_dir)
        payload = {"mission_id": "msn_merkle_01", "result": "verified"}

        token = engine.seal_evidence_record(payload)
        assert token.startswith("merkle_")
        assert len(token) > 10
        assert os.path.exists(engine.ledger_path)

        # Verify ledger line format
        with open(engine.ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert "content_sha256" in entry
            assert entry["payload"]["mission_id"] == "msn_merkle_01"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_milestone_7_executive_report_builder():
    temp_dir = tempfile.mkdtemp()
    try:
        engine = EvidenceAndReportingEngine(ledger_dir=temp_dir)
        file_path = os.path.join(temp_dir, "summary.pdf")
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4 sample executive brief")

        deliverable = ExecutiveDeliverable(
            artifact_id="art_01",
            filename="summary.pdf",
            path=file_path,
            size_bytes=len(b"%PDF-1.4 sample executive brief"),
            sha256="fake_sha256_hash",
            deliverable_type="EXECUTIVE_PDF"
        )

        outcome, checks = engine.verify_file_deliverable(file_path, min_bytes=5)

        report = engine.build_executive_report(
            mission_id="msn_exec_01",
            task_id="task_exec_01",
            objective="Audit corporate spend and produce PDF deliverable",
            execution_status="COMPLETED",
            deliverables=[deliverable],
            verification_status=outcome,
            verification_checks=checks,
            tools_used=["posix_python3", "document_pdf"],
            agents_used=["Document Specialist"],
            duration_seconds=12.45
        )

        assert report.mission_id == "msn_exec_01"
        assert report.execution_status == "COMPLETED"
        assert report.merkle_evidence_token.startswith("merkle_")
        assert len(report.deliverables) == 1
        assert report.verification_results["verified"] is True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
