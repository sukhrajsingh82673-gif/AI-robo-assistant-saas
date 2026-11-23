"""Acceptance Test AT-10: Release Approval Flow and Anti-Self-Approval Enforcement."""

import json
import sqlite3
from pathlib import Path
import pytest
from agent_factory.api.routes import AgentFactoryRouter


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_at10.db")
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


@pytest.fixture
def router(test_db, tmp_path):
    get_conn = test_db
    ledger_file = str(tmp_path / "test_at10_ledger.jsonl")
    return AgentFactoryRouter(db_conn_factory=get_conn, ledger_file=ledger_file)


def test_at10_approval_engine_flow_and_self_approval_block(router, test_db):
    submitter_headers = {
        "X-Tenant-ID": "tnt_at10",
        "X-User-ID": "emp.builder_lead",
        "X-Company-ID": "comp_at10",
        "Idempotency-Key": "idem_at10_001"
    }
    approver_headers = {
        "X-Tenant-ID": "tnt_at10",
        "X-User-ID": "emp.ai_ceo",
        "X-Company-ID": "comp_at10",
        "Idempotency-Key": "idem_at10_002"
    }

    # 1. Seed agent, version, and certification
    ver_id = "agv_at10_test"
    cert_id = "crt_at10_test"
    with test_db() as conn:
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, lifecycle, created_at, updated_at
            ) VALUES ('agt_at10', 'tnt_at10', 'comp_at10', 'at10-agent', 'AT10 Agent', 'Specialist',
                      'finance', 'emp.builder_lead', 'agt.at10-agent', 'BUILT', 1000.0, 1000.0)
        """)
        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, 'tnt_at10', 'agt_at10', '1.0.0', '{}', 'sha',
                      '{}', '{}', 'R1', 'CERTIFIED', 'emp.builder_lead', 1000.0)
        """, (ver_id,))
        conn.execute("""
            INSERT INTO af_artifact (
                id, tenant_id, kind, sha256, size_bytes, storage_uri, created_by, created_at
            ) VALUES ('art_c10', 'tnt_at10', 'certification_bundle', 'sha_c10', 100, 'uri', 'emp.builder_lead', 1000.0)
        """)
        conn.execute("""
            INSERT INTO af_certification (
                id, tenant_id, subject_kind, agent_version_id, gate_policy_version,
                gate_results, all_mandatory_passed, bundle_artifact_id, evidence_ledger_ref,
                issued_by, issued_at
            ) VALUES (?, 'tnt_at10', 'agent_version', ?, '1.0.0', '{"ok": true}', 1, 'art_c10', 'ev_c10', 'emp.qa', 1000.0)
        """, (cert_id, ver_id))
        conn.commit()

    # 2. Submitter submits release
    sub_body = {
        "subject_kind": "agent_version",
        "subject_id": ver_id,
        "certification_id": cert_id
    }
    status, res, _ = router.dispatch("POST", "/api/v8/agent-factory/releases", submitter_headers, json.dumps(sub_body).encode())
    assert status == 201
    release_id = res["release_id"]
    assert res["status"] == "PENDING"

    # 3. AT-10 Self-Approval Attempt: Submitter attempts to approve their own release -> MUST BE FORBIDDEN
    dec_body = {"decision": "APPROVED"}
    status, dec_err, _ = router.dispatch(
        "POST", f"/api/v8/agent-factory/releases/{release_id}/decision",
        submitter_headers, json.dumps(dec_body).encode()
    )
    assert status == 403
    assert dec_err["code"] == "AF-SELF-APPROVAL"

    # 4. Legitimate Approval: Distinct approver (AI CEO) approves release -> SUCCESS
    status, dec_ok, _ = router.dispatch(
        "POST", f"/api/v8/agent-factory/releases/{release_id}/decision",
        approver_headers, json.dumps(dec_body).encode()
    )
    assert status == 200
    assert dec_ok["decision"] == "APPROVED"
