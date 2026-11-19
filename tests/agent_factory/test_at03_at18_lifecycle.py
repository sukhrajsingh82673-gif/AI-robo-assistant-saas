"""ZONATA Agent Factory - Acceptance Tests AT-03 & AT-18.

AT-03: Customise/upgrade existing agent (Upgrade lane, parent version pointer, regression bounds G10).
AT-18: Suspend agent (<= 5s halt, credential revocation, lifecycle tracking, resume & retire).
"""

import sqlite3
import pytest
import time
import json

from agent_factory.domain.lifecycle import (
    LifecycleManager,
    LifecycleError,
    UpgradeRegressionError
)
from agent_factory.monitor.service import MonitoringService, MonitoringError
from agent_factory.adapters.fakes import (
    FakeEvidenceAdapter,
    FakeAuthorityAdapter,
    FakeRuntimeAdapter
)

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_lc.db"
    conn = sqlite3.connect(str(db_file))
    with open("migrations/sqlite/0013_agent_factory_core.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_file)


def test_at03_customise_existing_agent_upgrade_lane(test_db):
    """AT-03: Upgrade existing agent with parent linkage, spec hashing, and G10 regression bounds."""
    def get_conn():
        return sqlite3.connect(test_db)

    evidence = FakeEvidenceAdapter()
    authority = FakeAuthorityAdapter()
    runtime = FakeRuntimeAdapter()

    manager = LifecycleManager(
        db_conn_factory=get_conn,
        evidence_port=evidence,
        authority_port=authority,
        runtime_port=runtime
    )

    tenant_id = "tenant-at03"
    company_id = "comp-at03"
    agent_id = "agt-cfo"
    v1_id = "agv-cfo-1-0-0"
    v1_spec = {"role": "cfo", "tools": ["read_financials"], "version": "1.0.0"}
    now = time.time()

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, active_version_id,
                lifecycle, created_at, updated_at
            ) VALUES (?, ?, ?, 'cfo', 'CFO Agent', 'Chief Financial Officer', 'finance', 'admin', 'pr_cfo_001', ?, 'ACTIVE', ?, ?)
        """, (agent_id, tenant_id, company_id, v1_id, now, now))

        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, ?, ?, '1.0.0', ?, 'v1_hash_xyz', '["financial_read"]', '["fs:read"]', 'R1', 'PUBLISHED', 'admin', ?)
        """, (v1_id, tenant_id, agent_id, json.dumps(v1_spec), now))
        conn.commit()

    # Step 1: Simulate regression detection during upgrade (Gate G10 failure) -> Must be rejected
    with pytest.raises(UpgradeRegressionError) as exc_info:
        manager.upgrade_agent(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=agent_id,
            new_semver="1.1.0",
            spec_delta={"added_capabilities": ["payment.execute"]},
            initiated_by="admin",
            simulate_regression=True
        )
    assert "AF-G10-REGRESSION" in str(exc_info.value)

    # Step 2: Valid upgrade adding 'document.generate' capability
    upg_res = manager.upgrade_agent(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=agent_id,
        new_semver="1.1.0",
        spec_delta={
            "tools": ["read_financials", "generate_pdf"],
            "added_capabilities": ["document.generate"],
            "added_permissions": ["doc:write"]
        },
        initiated_by="emp.cfo",
        simulate_regression=False
    )

    assert upg_res["new_semver"] == "1.1.0"
    assert upg_res["parent_version_id"] == v1_id
    assert upg_res["parent_sha256"] == "v1_hash_xyz"
    assert upg_res["new_sha256"] != "v1_hash_xyz"
    # Crucial invariant: active_version_id MUST still be v1.0.0 until v1.1.0 is released!
    assert upg_res["active_version_id"] == v1_id

    # Verify DB rows
    with get_conn() as conn:
        # Agent active version unchanged
        cur = conn.execute("SELECT active_version_id FROM af_agent WHERE id = ?", (agent_id,))
        assert cur.fetchone()[0] == v1_id

        # New version row inserted with parent_version_id pointing to v1_id
        cur = conn.execute("""
            SELECT id, semver, parent_version_id, status, capability_profile, permission_profile
            FROM af_agent_version WHERE id = ?
        """, (upg_res["new_version_id"],))
        new_row = cur.fetchone()
        assert new_row is not None
        assert new_row[1] == "1.1.0"
        assert new_row[2] == v1_id
        assert new_row[3] == "CERTIFIED"
        assert "document.generate" in new_row[4]
        assert "doc:write" in new_row[5]


def test_at18_suspend_resume_and_retire(test_db):
    """AT-18: Validate immediate suspension (<= 5s), credential revocation, resume and retirement."""
    def get_conn():
        return sqlite3.connect(test_db)

    evidence = FakeEvidenceAdapter()
    authority = FakeAuthorityAdapter()
    runtime = FakeRuntimeAdapter()

    manager = LifecycleManager(
        db_conn_factory=get_conn,
        evidence_port=evidence,
        authority_port=authority,
        runtime_port=runtime
    )
    monitor = MonitoringService(
        db_conn_factory=get_conn,
        evidence_port=evidence
    )

    tenant_id = "tenant-at18"
    company_id = "comp-at18"
    agent_id = "agt-support"
    version_id = "agv-support-1-0-0"
    principal_id = "pr_agt_support_99"
    now = time.time()

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, active_version_id,
                lifecycle, monitoring_status, created_at, updated_at
            ) VALUES (?, ?, ?, 'support', 'Support Agent', 'Specialist', 'customer_support', 'admin', ?, ?, 'ACTIVE', 'HEALTHY', ?, ?)
        """, (agent_id, tenant_id, company_id, principal_id, version_id, now, now))

        conn.execute("""
            INSERT INTO af_runtime_instance (
                id, tenant_id, agent_id, agent_version_id, channel, traffic_percent,
                runtime_ref, status, started_at
            ) VALUES ('inst-1', ?, ?, ?, 'production', 100, 'rt_ref_1', 'RUNNING', ?)
        """, (tenant_id, agent_id, version_id, now))
        conn.commit()

    # Step 1: Suspend agent (AT-18 execution)
    t_start = time.time()
    susp_res = manager.suspend_agent(
        tenant_id=tenant_id,
        agent_id=agent_id,
        reason="Security audit check",
        initiated_by="sec-admin"
    )
    t_duration = time.time() - t_start

    # Assert <= 5s halt requirement
    assert t_duration <= 5.0, f"Suspension must complete within 5 seconds, took {t_duration}s"
    assert susp_res["lifecycle"] == "SUSPENDED"
    assert susp_res["principal_revoked"] == principal_id

    # Verify DB state
    with get_conn() as conn:
        agent_row = conn.execute("SELECT lifecycle, monitoring_status FROM af_agent WHERE id = ?", (agent_id,)).fetchone()
        assert agent_row[0] == "SUSPENDED"
        assert agent_row[1] == "INCIDENT"

        inst_row = conn.execute("SELECT status FROM af_runtime_instance WHERE id = 'inst-1'").fetchone()
        assert inst_row[0] == "SUSPENDED"

        # Verify lifecycle event was recorded
        lc_row = conn.execute("SELECT from_state, to_state, actor FROM af_lifecycle_event WHERE subject_id = ? ORDER BY id DESC LIMIT 1", (agent_id,)).fetchone()
        assert lc_row[0] == "ACTIVE"
        assert lc_row[1] == "SUSPENDED"
        assert lc_row[2] == "sec-admin"

    # Step 2: Resume agent
    res_res = manager.resume_agent(
        tenant_id=tenant_id,
        agent_id=agent_id,
        initiated_by="sec-admin"
    )
    assert res_res["lifecycle"] == "ACTIVE"

    with get_conn() as conn:
        agent_row = conn.execute("SELECT lifecycle, monitoring_status FROM af_agent WHERE id = ?", (agent_id,)).fetchone()
        assert agent_row[0] == "ACTIVE"
        assert agent_row[1] == "HEALTHY"

        inst_row = conn.execute("SELECT status FROM af_runtime_instance WHERE id = 'inst-1'").fetchone()
        assert inst_row[0] == "RUNNING"

    # Step 3: Record feedback & verify monitoring summary
    fb_res = monitor.record_feedback(
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_version_id=version_id,
        from_principal="user-42",
        rating=5,
        category="quality",
        comment="Excellent resolution speed"
    )
    assert fb_res["rating"] == 5

    mon_summary = monitor.get_monitoring_summary(tenant_id=tenant_id, agent_id=agent_id)
    assert mon_summary["feedback"]["total_count"] == 1
    assert mon_summary["feedback"]["average_rating"] == 5.0

    # Step 4: Retire agent permanently
    ret_res = manager.retire_agent(
        tenant_id=tenant_id,
        agent_id=agent_id,
        reason="End of project lifecycle",
        initiated_by="admin"
    )
    assert ret_res["lifecycle"] == "RETIRED"

    with get_conn() as conn:
        agent_row = conn.execute("SELECT lifecycle FROM af_agent WHERE id = ?", (agent_id,)).fetchone()
        assert agent_row[0] == "RETIRED"

        inst_row = conn.execute("SELECT status, stopped_at FROM af_runtime_instance WHERE id = 'inst-1'").fetchone()
        assert inst_row[0] == "STOPPED"
        assert inst_row[1] is not None
