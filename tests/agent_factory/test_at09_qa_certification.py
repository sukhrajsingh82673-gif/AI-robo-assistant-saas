"""Acceptance Test AT-09: Reject Agents Failing Mandatory QA Gates."""

import json
import sqlite3
import pytest
from agent_factory.api.routes import AgentFactoryRouter


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_at09.db")
    schema_path = "/data/data/com.termux/files/home/AI-robo-assistant-saas/migrations/sqlite/0013_agent_factory_core.sql"
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
    ledger_file = str(tmp_path / "test_at09_ledger.jsonl")
    return AgentFactoryRouter(db_conn_factory=get_conn, ledger_file=ledger_file)


def test_at09_reject_agent_failing_mandatory_qa(router, test_db):
    headers = {
        "X-Tenant-ID": "tnt_at09",
        "X-User-ID": "emp.qa_lead",
        "X-Company-ID": "comp_at09",
        "Idempotency-Key": "idem_at09_001"
    }

    # 1. Seed agent and agent_version
    agent_id = "agt_at09_test"
    version_id = "agv_at09_test"
    spec = {
        "apiVersion": "zonata.agent/v1",
        "kind": "Agent",
        "metadata": {"name": "qa-test-agent", "version": "1.0.0", "category": "finance", "risk_tier": "R1"},
        "identity": {"principal_kind": "agent", "tenant_bound": True, "may_use_employees": False},
        "role": {"title": "QA Test Agent", "mission": "Testing QA gates", "responsibilities": ["run"], "out_of_scope": [], "success_criteria": ["ok"]}
    }

    with test_db() as conn:
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, lifecycle, created_at, updated_at
            ) VALUES (?, 'tnt_at09', 'comp_at09', 'qa-test-agent', 'QA Test Agent', 'QA Specialist',
                      'finance', 'emp.qa_lead', 'agt.qa-test-agent', 'BUILT', 1000.0, 1000.0)
        """, (agent_id,))

        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, 'tnt_at09', ?, '1.0.0', ?, 'sha_spec_mock',
                      '{}', '{}', 'R1', 'BUILT', 'emp.qa_lead', 1000.0)
        """, (version_id, agent_id, json.dumps(spec)))
        conn.commit()

    # 2. Case A: Inject QA security failure -> Certification MUST BE REJECTED with 422 AF-GATE-FAILED
    orig_eval = router.qa_runner.run_evaluations
    router.qa_runner.run_evaluations = lambda s, v, **kw: orig_eval(s, v, inject_security_failure=True, **kw)

    status, res, _ = router.dispatch(
        "POST", f"/api/v8/agent-factory/agent-versions/{version_id}/certify",
        headers, b""
    )
    assert status == 422
    assert res["code"] == "AF-GATE-FAILED"
    assert "Failed gates" in res["detail"]

    # 3. Case B: Clean QA pass -> Certification SUCCEEDS and status becomes CERTIFIED
    router.qa_runner.run_evaluations = orig_eval
    status, res, r_headers = router.dispatch(
        "POST", f"/api/v8/agent-factory/agent-versions/{version_id}/certify",
        headers, b""
    )
    assert status == 200
    assert res["status"] == "CERTIFIED"
    assert "certification_id" in res
    assert "bundle_sha256" in res
    assert "X-Evidence-Id" in r_headers
