"""Acceptance Test AT-15: Verify Signed Artifacts and Certification Bundles."""

import copy
import sqlite3
from pathlib import Path
import pytest
from agent_factory.cert.bundle import CertificationBundleManager
from agent_factory.adapters.fakes import FakeEvidencePort


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_at15.db")
    schema_path = str(Path(__file__).resolve().parents[2] / "migrations" / "sqlite" / "0013_agent_factory_core.sql")
    with open(schema_path, "r") as f:
        schema = f.read()
    conn = sqlite3.connect(db_file)
    conn.executescript(schema)
    conn.commit()
    conn.close()

    def get_conn():
        return sqlite3.connect(db_file)

    return get_conn


def test_at15_signed_certification_bundle_verification(test_db):
    ev = FakeEvidencePort()
    mgr = CertificationBundleManager(db_conn_factory=test_db, evidence_port=ev)

    gate_results = {
        "policy_version": "1.0.0",
        "tier": "R1",
        "all_mandatory_passed": True,
        "gates": [
            {"gate": "G01_spec_valid", "passed": True},
            {"gate": "G05_security_suite", "passed": True}
        ]
    }

    # 1. Build and seal bundle
    bundle_info = mgr.build_and_seal_bundle(
        tenant_id="tnt_at15",
        subject_kind="agent_version",
        agent_version_id="agv_at15_test",
        batch_id=None,
        gate_results=gate_results
    )

    cert_id = bundle_info["certification_id"]
    assert cert_id.startswith("crt_")

    bundle_payload = {
        "manifest": bundle_info["manifest"],
        "signature": bundle_info["signature"],
        "gate_results": gate_results
    }

    # Re-extract actual manifest from DB / payload
    with test_db() as conn:
        cur = conn.execute("SELECT gate_results, all_mandatory_passed FROM af_certification WHERE id = ?", (cert_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[1] == 1

    # 2. Tampering test: modify one field in manifest -> signature verification fails
    tampered_payload = copy.deepcopy(bundle_payload)
    tampered_payload["manifest"]["tier"] = "R3"  # unauthorized tier escalation
    ok, reason = mgr.verify_bundle(tampered_payload)
    assert ok is False
    assert reason == "hash mismatch"

    # 3. Forged signature fails
    forged_payload = copy.deepcopy(bundle_payload)
    forged_payload["signature"]["signature"] = "AA" * 32
    ok, reason = mgr.verify_bundle(forged_payload)
    assert ok is False
    assert reason == "bad signature"
