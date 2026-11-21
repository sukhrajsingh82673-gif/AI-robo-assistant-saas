"""Acceptance Test AT-01: Single-Agent Manufacturing End-to-End."""

import json
import sqlite3
from pathlib import Path
import pytest
from agent_factory.build.pipeline import SingleAgentPipeline
from agent_factory.adapters.fakes import (
    FakeAuthorityPort, FakeEvidencePort, FakeKillSwitchPort, FakeRuntimePort
)


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_at01.db")
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


def test_at01_single_agent_manufacturing(test_db):
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

    tenant_id = "tnt_at01"
    company_id = "comp_at01"
    req_id = "req_at01_001"

    # Seed initial request
    with conn_factory() as conn:
        conn.execute("""
            INSERT INTO af_request (
                id, tenant_id, company_id, requester_principal_id, requester_kind,
                mode, natural_language, status, risk_tier, budget_cap_usd,
                spent_usd, idempotency_key, correlation_id, created_at, updated_at
            ) VALUES (?, ?, ?, 'emp.csuite_lead', 'ai_employee', 'single',
                      'Build an executive c-suite advisory agent to deliver strategic briefings.',
                      'ANALYSING', 'R1', 5.0, 0.0, 'idem_at01_001', 'corr_at01', 1000.0, 1000.0)
        """, (req_id, tenant_id, company_id))
        conn.commit()

    # Run complete 7-stage manufacturing pipeline
    result = pipeline.run(
        request_id=req_id,
        tenant_id=tenant_id,
        company_id=company_id,
        principal_id="emp.csuite_lead"
    )

    assert result["status"] == "BUILT"
    assert result["staging_deployed"] is True
    assert "evidence_id" in result
    assert "package_sha256" in result

    # Check database persistence across stages
    with conn_factory() as conn:
        # Check af_agent
        cur = conn.execute("SELECT slug, category, lifecycle FROM af_agent WHERE id = ?", (result["agent_id"],))
        agent_row = cur.fetchone()
        assert agent_row is not None
        assert agent_row[0] == "c-suite-advisory"
        assert agent_row[1] == "c_suite"

        # Check af_agent_version
        cur = conn.execute("SELECT semver, status, risk_tier FROM af_agent_version WHERE id = ?", (result["agent_version_id"],))
        ver_row = cur.fetchone()
        assert ver_row is not None
        assert ver_row[0] == "1.0.0"
        assert ver_row[1] == "BUILT"

        # Check af_artifact
        cur = conn.execute("SELECT sha256, signature, signing_key_id FROM af_artifact WHERE id = ?", (f"art_{result['agent_version_id']}",))
        art_row = cur.fetchone()
        assert art_row is not None
        assert len(art_row[0]) == 64
        assert len(art_row[1]) > 30

        # Check af_build
        cur = conn.execute("SELECT status, cost_usd, stages FROM af_build WHERE id = ?", (result["build_id"],))
        bld_row = cur.fetchone()
        assert bld_row is not None
        assert bld_row[0] == "SUCCEEDED"
        assert bld_row[1] > 0
        stages = json.loads(bld_row[2])
        assert "stage7_deploy" in stages
