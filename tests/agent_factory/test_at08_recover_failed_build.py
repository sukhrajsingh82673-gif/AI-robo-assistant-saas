"""Acceptance Test AT-08: Checkpoint Resumption on Failed Build."""

import sqlite3
from pathlib import Path
import pytest
from agent_factory.build.pipeline import SingleAgentPipeline, BuildStageFailure
from agent_factory.adapters.fakes import (
    FakeAuthorityPort, FakeEvidencePort, FakeKillSwitchPort, FakeRuntimePort
)


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_at08.db")
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


def test_at08_recover_failed_build(test_db):
    conn_factory = test_db
    auth = FakeAuthorityPort()
    ev = FakeEvidencePort()
    ks = FakeKillSwitchPort()
    rt = FakeRuntimePort()

    pipeline = SingleAgentPipeline(
        db_conn_factory=conn_factory,
        authority_port=auth,
        evidence_port=ev,
        killswitch_port=ks,
        runtime_port=rt
    )

    tenant_id = "tnt_at08"
    company_id = "comp_at08"
    req_id = "req_at08_001"

    with conn_factory() as conn:
        conn.execute("""
            INSERT INTO af_request (
                id, tenant_id, company_id, requester_principal_id, requester_kind,
                mode, natural_language, status, risk_tier, budget_cap_usd,
                spent_usd, idempotency_key, correlation_id, created_at, updated_at
            ) VALUES (?, ?, ?, 'emp.marketing_lead', 'ai_employee', 'single',
                      'Build a marketing campaign creator to draft campaign newsletters.',
                      'ANALYSING', 'R1', 5.0, 0.0, 'idem_at08_001', 'corr_at08', 1000.0, 1000.0)
        """, (req_id, tenant_id, company_id))
        conn.commit()

    # Step 1: Simulate failure during build by monkeypatching unit verification
    original_verify = pipeline.integration.verify_author_cases
    pipeline.integration.verify_author_cases = lambda g, s, c, a: (False, [{"case_id": "test_01", "passed": False, "error": "Injected transient test failure"}])

    saved_checkpoint = None
    try:
        pipeline.run(request_id=req_id, tenant_id=tenant_id, company_id=company_id, principal_id="emp.marketing_lead")
    except BuildStageFailure as e:
        saved_checkpoint = e.checkpoint
        assert e.stage == "stage5_unit_test"

    assert saved_checkpoint is not None
    assert "ars" in saved_checkpoint
    assert "design" in saved_checkpoint
    assert "spec" in saved_checkpoint

    # Step 2: Restore normal verification and resume from saved checkpoint
    pipeline.integration.verify_author_cases = original_verify

    res = pipeline.run(
        request_id=req_id,
        tenant_id=tenant_id,
        company_id=company_id,
        principal_id="emp.marketing_lead",
        existing_checkpoint=saved_checkpoint
    )

    assert res["status"] == "BUILT"
    assert res["staging_deployed"] is True
    # Verify stages 1-3 were preserved from checkpoint
    assert res["checkpoint"]["ars"] == saved_checkpoint["ars"]
    assert res["checkpoint"]["spec"] == saved_checkpoint["spec"]
