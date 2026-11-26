"""Acceptance Tests AT-19 & AT-20: Resource and Cost Quota Limits Enforcement."""

import json
import sqlite3
from pathlib import Path
import pytest
from agent_factory.api.routes import AgentFactoryRouter
from agent_factory.control.quotas import ensure_quotas_seeded, reserve_quota


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_at19_at20.db")
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
    ledger_file = str(tmp_path / "test_at19_ledger.jsonl")
    return AgentFactoryRouter(db_conn_factory=get_conn, ledger_file=ledger_file)


def test_at19_at20_quota_rejection_on_depleted_budget(router, test_db):
    headers = {
        "X-Tenant-ID": "tnt_at19",
        "X-User-ID": "emp.director",
        "X-Company-ID": "comp_at19",
        "Idempotency-Key": "idem_at19_001"
    }

    # 1. Seed request
    req_body = {
        "mode": "team",
        "natural_language": "Build automated intelligence team with 3 agents.",
        "budget_cap_usd": 15.0
    }
    status, res, _ = router.dispatch("POST", "/api/v8/agent-factory/requests", headers, json.dumps(req_body).encode())
    assert status == 202
    req_id = res["request_id"]

    # 2. Create batch (Route 7)
    batch_body = {
        "request_id": req_id,
        "release_policy": "atomic_team",
        "items": [
            {"agent_key": "specialist_a", "role_title": "Specialist A"},
            {"agent_key": "specialist_b", "role_title": "Specialist B"}
        ],
        "edges": []
    }
    status, b_res, _ = router.dispatch("POST", "/api/v8/agent-factory/batches", headers, json.dumps(batch_body).encode())
    assert status == 202
    batch_id = b_res["batch_id"]

    # 3. Simulate depleted quota by reserving all 10 builds
    with test_db() as conn:
        ensure_quotas_seeded(conn, "tnt_at19")
        reserve_quota(conn, "tnt_at19", "builds", amount=10.0)
        conn.commit()

    # 4. Starting the batch must be rejected with 429 AF-QUOTA-EXCEEDED
    status, start_res, _ = router.dispatch("POST", f"/api/v8/agent-factory/batches/{batch_id}/start", headers, b"")
    assert status == 429
    assert start_res["code"] == "AF-QUOTA-EXCEEDED"
