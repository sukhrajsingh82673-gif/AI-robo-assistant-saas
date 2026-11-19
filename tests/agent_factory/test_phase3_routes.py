"""Tests for Agent Factory Phase 3 Routes (Routes 3, 4, 5, 13, 14, 15, 16)."""

import json
import os
import sqlite3
import pytest
from agent_factory.api.routes import AgentFactoryRouter


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_p3.db")
    schema_path = "/data/data/com.termux/files/home/AI-robo-assistant-saas/migrations/sqlite/0013_agent_factory_core.sql"
    with open(schema_path, "r") as f:
        schema = f.read()
    conn = sqlite3.connect(db_file)
    conn.executescript(schema)
    conn.commit()
    conn.close()

    def get_conn():
        return sqlite3.connect(db_file)

    return get_conn, db_file


@pytest.fixture
def router(test_db, tmp_path):
    get_conn, _ = test_db
    ledger_file = str(tmp_path / "test_p3_ledger.jsonl")
    return AgentFactoryRouter(db_conn_factory=get_conn, ledger_file=ledger_file)


def test_phase3_routes_lifecycle(router):
    headers = {
        "X-Tenant-ID": "tnt_p3_test",
        "X-User-ID": "emp.finance_director",
        "X-Company-ID": "comp_p3_test",
        "Idempotency-Key": "idem_p3_req_001"
    }

    # 1. Create a request
    create_body = {
        "mode": "single",
        "natural_language": "Build an automated financial reconciliation agent to audit ledger variances daily."
    }
    status, res, r_headers = router.dispatch(
        "POST", "/api/v8/agent-factory/requests",
        headers, json.dumps(create_body).encode()
    )
    assert status == 202
    req_id = res["request_id"]

    # 2. Route 4: POST /requests/{id}/analyze
    status, res, r_headers = router.dispatch(
        "POST", f"/api/v8/agent-factory/requests/{req_id}/analyze",
        headers, b""
    )
    assert status == 200
    assert "ars" in res
    ars = res["ars"]
    assert ars["category"] == "finance"
    assert "finance-reconciliation" in ars["suggested_template_ref"]

    # 3. Route 3: POST /requests/{id}/clarifications
    clarif_body = {
        "answers": {
            "target_systems": ["accounting_gl"],
            "variance_threshold": 50.0
        }
    }
    status, res, r_headers = router.dispatch(
        "POST", f"/api/v8/agent-factory/requests/{req_id}/clarifications",
        headers, json.dumps(clarif_body).encode()
    )
    assert status == 200
    assert res["clarifications_recorded"] is True
    assert "X-Evidence-Id" in r_headers

    # 4. Route 5: GET /requests/{id}/estimate
    status, res, r_headers = router.dispatch(
        "GET", f"/api/v8/agent-factory/requests/{req_id}/estimate",
        headers, b""
    )
    assert status == 200
    assert "estimated_tokens" in res
    assert "estimated_cost_usd" in res
    assert res["sandbox_tier_required"] == "T0"

    # 5. Route 13: GET /templates
    status, res, r_headers = router.dispatch(
        "GET", "/api/v8/agent-factory/templates",
        headers, b""
    )
    assert status == 200
    items = res["items"]
    assert len(items) >= 6
    names = [i["name"] for i in items]
    assert "finance-reconciliation" in names

    # 6. Route 14: GET /templates/{name}
    status, res, r_headers = router.dispatch(
        "GET", "/api/v8/agent-factory/templates/finance-reconciliation",
        headers, b""
    )
    assert status == 200
    assert res["metadata"]["name"] == "finance-reconciliation"

    # 7. Route 15: POST /templates/{name}/versions/{semver}/submit
    status, res, r_headers = router.dispatch(
        "POST", "/api/v8/agent-factory/templates/finance-reconciliation/versions/1.0.0/submit",
        headers, b""
    )
    assert status == 200
    assert res["status"] == "IN_REVIEW"

    # 8. Route 16: POST /templates/{name}/versions/{semver}/publish (requires approval_id)
    pub_body_no_app = {}
    status, res, r_headers = router.dispatch(
        "POST", "/api/v8/agent-factory/templates/finance-reconciliation/versions/1.0.0/publish",
        headers, json.dumps(pub_body_no_app).encode()
    )
    assert status == 400  # approval_id required

    pub_body = {"approval_id": "app_eng_9921"}
    status, res, r_headers = router.dispatch(
        "POST", "/api/v8/agent-factory/templates/finance-reconciliation/versions/1.0.0/publish",
        headers, json.dumps(pub_body).encode()
    )
    assert status == 200
    assert res["status"] == "PUBLISHED"
    assert "X-Evidence-Id" in r_headers
