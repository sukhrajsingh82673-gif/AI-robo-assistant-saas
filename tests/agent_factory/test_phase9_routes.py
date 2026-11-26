"""ZONATA Agent Factory - Phase 9 API Route Tests."""

import sqlite3
import pytest
import time
import json

from agent_factory.api.routes import AgentFactoryRouter


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_p9_routes.db"
    conn = sqlite3.connect(str(db_file))
    with open("migrations/sqlite/0013_agent_factory_core.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_file)


def test_phase9_routes_full_flow(test_db):
    def get_conn():
        return sqlite3.connect(test_db)

    router = AgentFactoryRouter(db_conn_factory=get_conn)
    tenant_id = "tenant-p9-rt"
    company_id = "comp-p9-rt"
    agent_id = "agt-ops"
    v1_id = "agv-ops-1-0-0"
    now = time.time()

    # Seed an agent
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, active_version_id,
                lifecycle, created_at, updated_at
            ) VALUES (?, ?, ?, 'ops', 'Ops Agent', 'DevOps Specialist', 'devops', 'admin', 'pr_agt_ops', ?, 'ACTIVE', ?, ?)
        """, (agent_id, tenant_id, company_id, v1_id, now, now))

        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, ?, ?, '1.0.0', '{"role": "ops"}', 'hash-ops-1', '["devops"]', '["fs:read"]', 'R1', 'PUBLISHED', 'admin', ?)
        """, (v1_id, tenant_id, agent_id, now))
        conn.commit()

    headers = {
        "X-Tenant-ID": tenant_id,
        "X-Company-ID": company_id,
        "X-User-ID": "admin-123"
    }

    # 1. GET /monitoring
    status, body, _ = router.dispatch(
        method="GET",
        path=f"/api/v8/agent-factory/agents/{agent_id}/monitoring",
        headers=headers,
        body_bytes=b""
    )
    assert status == 200
    assert body["agent_id"] == agent_id
    assert body["lifecycle"] == "ACTIVE"
    assert body["feedback"]["total_count"] == 0

    # 2. POST /feedback
    status, body, _ = router.dispatch(
        method="POST",
        path=f"/api/v8/agent-factory/agents/{agent_id}/feedback",
        headers=headers,
        body_bytes=json.dumps({"rating": 5, "category": "quality", "comment": "Great performance!"}).encode()
    )
    assert status == 201
    assert body["rating"] == 5

    # 3. POST /upgrades (AT-03 via API)
    status, body, _ = router.dispatch(
        method="POST",
        path=f"/api/v8/agent-factory/agents/{agent_id}/upgrades",
        headers=headers,
        body_bytes=json.dumps({"new_semver": "1.1.0", "delta": {"added_capabilities": ["k8s_deploy"]}}).encode()
    )
    assert status == 201
    assert body["new_semver"] == "1.1.0"
    assert body["parent_version_id"] == v1_id

    # 4. POST /suspend (AT-18 via API)
    status, body, _ = router.dispatch(
        method="POST",
        path=f"/api/v8/agent-factory/agents/{agent_id}/suspend",
        headers=headers,
        body_bytes=json.dumps({"reason": "Routine maintenance"}).encode()
    )
    assert status == 200
    assert body["lifecycle"] == "SUSPENDED"

    # 5. POST /resume
    status, body, _ = router.dispatch(
        method="POST",
        path=f"/api/v8/agent-factory/agents/{agent_id}/resume",
        headers=headers,
        body_bytes=b""
    )
    assert status == 200
    assert body["lifecycle"] == "ACTIVE"

    # 6. POST /retire
    status, body, _ = router.dispatch(
        method="POST",
        path=f"/api/v8/agent-factory/agents/{agent_id}/retire",
        headers=headers,
        body_bytes=json.dumps({"reason": "Replaced by next-gen cluster"}).encode()
    )
    assert status == 200
    assert body["lifecycle"] == "RETIRED"
