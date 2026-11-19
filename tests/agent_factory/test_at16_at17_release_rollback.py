"""ZONATA Agent Factory - Acceptance Tests AT-16 & AT-17.

AT-16: Two-phase atomic team publish with failure injection compensation.
AT-17: Rollback to previous certified version via pointer switch.
"""

import sqlite3
import pytest
import time
import uuid

from agent_factory.registry.release_manager import (
    ReleaseManager,
    ReleaseError,
    AtomicPublishFailedError
)
from agent_factory.adapters.fakes import (
    FakeEvidenceAdapter,
    FakeRuntimeAdapter,
    FakeWorkforceAdapter,
    FakeApprovalAdapter
)

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_rf.db"
    conn = sqlite3.connect(str(db_file))
    with open("migrations/sqlite/0013_agent_factory_core.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_file)

def test_at16_atomic_team_publish_with_failure_compensation(test_db):
    """AT-16: Validate two-phase atomic team publish and rollback on partial failure."""
    def get_conn():
        return sqlite3.connect(test_db)

    evidence = FakeEvidenceAdapter()
    approval = FakeApprovalAdapter()
    runtime = FakeRuntimeAdapter()
    workforce = FakeWorkforceAdapter()
    
    manager = ReleaseManager(
        db_conn_factory=get_conn,
        evidence_port=evidence,
        approval_port=approval,
        runtime_port=runtime,
        workforce_port=workforce
    )

    tenant_id = "tenant-at16"
    company_id = "comp-at16"
    request_id = "req-at16-01"
    batch_id = "batch-at16-01"
    now = time.time()

    # Setup database with request, batch and batch items
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO af_request (
                id, tenant_id, company_id, requester_principal_id, requester_kind,
                mode, natural_language, status, idempotency_key, correlation_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, 'requester_1', 'human_owner', 'team', 'Build team', 'BUILDING', 'idem-at16', 'corr-at16', ?, ?)
        """, (request_id, tenant_id, company_id, now, now))

        conn.execute("""
            INSERT INTO af_requirement_spec (id, tenant_id, request_id, version, body, body_sha256, authored_by, created_at)
            VALUES ('spec-at16', ?, ?, 1, '{"goal": "team"}', 'hash', 'admin', ?)
        """, (tenant_id, request_id, now))

        conn.execute("""
            INSERT INTO af_batch (id, tenant_id, company_id, request_id, release_policy, agent_count, waves, dependency_graph, manifest_sha256, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'atomic_team', 3, 1, '{}', 'mhash', 'CERTIFIED', ?, ?)
        """, (batch_id, tenant_id, company_id, request_id, now, now))

        members = ["lead", "worker_1", "worker_2"]
        for m in members:
            agent_id = f"agt_{m}"
            version_id = f"agv_{m}"
            conn.execute("""
                INSERT INTO af_agent (
                    id, tenant_id, company_id, slug, display_name, role_title,
                    category, owner_principal_id, agent_principal_id, lifecycle,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'devops', 'admin', ?, 'CERTIFIED', ?, ?)
            """, (agent_id, tenant_id, company_id, m, f"Agent {m}", m, f"pr_{m}", now, now))

            conn.execute("""
                INSERT INTO af_agent_version (
                    id, tenant_id, agent_id, semver, spec, spec_sha256,
                    capability_profile, permission_profile, risk_tier, status,
                    created_by, created_at
                ) VALUES (?, ?, ?, '1.0.0', '{}', 'hash', '[]', '[]', 'R1', 'CERTIFIED', 'admin', ?)
            """, (version_id, tenant_id, agent_id, now))

            conn.execute("""
                INSERT INTO af_batch_item (
                    id, tenant_id, batch_id, agent_key, role_title, requirement_spec_id,
                    status, agent_id, agent_version_id
                ) VALUES (?, ?, ?, ?, ?, 'spec-at16', 'CERTIFIED', ?, ?)
            """, (f"bit_{m}", tenant_id, batch_id, m, m, agent_id, version_id))

        # Add bundle artifact, certification and release
        conn.execute("""
            INSERT INTO af_artifact (id, tenant_id, kind, sha256, size_bytes, storage_uri, created_by, created_at)
            VALUES ('art-bundle-1', ?, 'certification_bundle', 'bundlehash', 1024, 'file:///tmp/bundle', 'admin', ?)
        """, (tenant_id, now))

        conn.execute("""
            INSERT INTO af_certification (
                id, tenant_id, subject_kind, batch_id, gate_policy_version,
                gate_results, all_mandatory_passed, bundle_artifact_id, evidence_ledger_ref,
                issued_by, issued_at
            ) VALUES ('cert-batch-1', ?, 'team', ?, '1.0.0', '{"G00": true}', 1, 'art-bundle-1', 'ev-1', 'admin', ?)
        """, (tenant_id, batch_id, now))

        conn.execute("""
            INSERT INTO af_release (
                id, tenant_id, subject_kind, batch_id, certification_id,
                approval_id, decision, submitted_by, decided_by_principal, decided_at, created_at
            ) VALUES ('rel-batch-1', ?, 'team', ?, 'cert-batch-1', 'appr-123', 'APPROVED', 'requester_1', 'approver_2', ?, ?)
        """, (tenant_id, batch_id, now, now))
        conn.commit()

    # Step 1: Inject failure during atomic publish on member 'worker_2'
    with pytest.raises(AtomicPublishFailedError) as exc_info:
        manager.publish_atomic_team(
            tenant_id=tenant_id,
            company_id=company_id,
            release_id="rel-batch-1",
            batch_id=batch_id,
            published_by="admin",
            inject_failure_on_member="worker_2"
        )
    assert "Deployment failed for member 'worker_2'" in str(exc_info.value)

    # Verify atomic rollback: no team record created, no members activated
    with get_conn() as conn:
        team_count = conn.execute("SELECT COUNT(*) FROM af_team WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        assert team_count == 0, "No team record should exist after rollback"

        running_inst = conn.execute("SELECT COUNT(*) FROM af_runtime_instance WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
        assert running_inst == 0, "No runtime instances should exist after rollback"

        # Check agent active_version_id is still NULL
        for m in members:
            active_ver = conn.execute("SELECT active_version_id FROM af_agent WHERE id = ?", (f"agt_{m}",)).fetchone()[0]
            assert active_ver is None

    # Step 2: Publish cleanly without failure injection
    res = manager.publish_atomic_team(
        tenant_id=tenant_id,
        company_id=company_id,
        release_id="rel-batch-1",
        batch_id=batch_id,
        published_by="admin"
    )
    assert res["status"] == "PUBLISHED"
    assert res["members_published"] == 3

    # Verify all members are now ACTIVE and team created
    with get_conn() as conn:
        team_row = conn.execute("SELECT id, lifecycle FROM af_team WHERE tenant_id = ?", (tenant_id,)).fetchone()
        assert team_row is not None
        assert team_row[1] == "ACTIVE"

        team_members = conn.execute("SELECT COUNT(*) FROM af_team_member WHERE team_id = ?", (team_row[0],)).fetchone()[0]
        assert team_members == 3

        instances = conn.execute("SELECT COUNT(*) FROM af_runtime_instance WHERE tenant_id = ? AND status = 'RUNNING'", (tenant_id,)).fetchone()[0]
        assert instances == 3

        for m in members:
            active_ver = conn.execute("SELECT active_version_id, lifecycle FROM af_agent WHERE id = ?", (f"agt_{m}",)).fetchone()
            assert active_ver[0] == f"agv_{m}"
            assert active_ver[1] == "ACTIVE"


def test_at17_rollback_to_previous_certified_version(test_db):
    """AT-17: Validate pointer switch rollback to previous certified version and rejection of uncertified version."""
    def get_conn():
        return sqlite3.connect(test_db)

    evidence = FakeEvidenceAdapter()
    approval = FakeApprovalAdapter()
    runtime = FakeRuntimeAdapter()
    workforce = FakeWorkforceAdapter()
    
    manager = ReleaseManager(
        db_conn_factory=get_conn,
        evidence_port=evidence,
        approval_port=approval,
        runtime_port=runtime,
        workforce_port=workforce
    )

    tenant_id = "tenant-at17"
    company_id = "comp-at17"
    agent_id = "agt-support"
    v1_id = "agv-support-v1"
    v2_id = "agv-support-v2"
    v3_uncert_id = "agv-support-v3"
    now = time.time()

    with get_conn() as conn:
        # Agent setup
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, active_version_id,
                lifecycle, created_at, updated_at
            ) VALUES (?, ?, ?, 'support', 'Support Agent', 'Support Specialist', 'customer_support', 'admin', 'pr_sup', ?, 'ACTIVE', ?, ?)
        """, (agent_id, tenant_id, company_id, v2_id, now, now))

        # Version 1 (SUPERSEDED)
        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, ?, ?, '1.0.0', '{}', 'hash1', '[]', '[]', 'R1', 'SUPERSEDED', 'admin', ?)
        """, (v1_id, tenant_id, agent_id, now - 100))

        # Version 2 (PUBLISHED)
        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, ?, ?, '2.0.0', '{}', 'hash2', '[]', '[]', 'R1', 'PUBLISHED', 'admin', ?)
        """, (v2_id, tenant_id, agent_id, now))

        # Version 3 (FAILED_QA)
        conn.execute("""
            INSERT INTO af_agent_version (
                id, tenant_id, agent_id, semver, spec, spec_sha256,
                capability_profile, permission_profile, risk_tier, status,
                created_by, created_at
            ) VALUES (?, ?, ?, '3.0.0', '{}', 'hash3', '[]', '[]', 'R1', 'FAILED_QA', 'admin', ?)
        """, (v3_uncert_id, tenant_id, agent_id, now + 10))
        conn.commit()

    # Step 1: Attempt rollback to uncertified version 3 -> Must fail
    with pytest.raises(ReleaseError) as exc_info:
        manager.rollback_to_version(
            tenant_id=tenant_id,
            agent_id=agent_id,
            target_version_id=v3_uncert_id,
            reason="Trying to rollback to v3",
            initiated_by="ops-admin"
        )
    assert "Cannot rollback to uncertified version in status 'FAILED_QA'" in str(exc_info.value)

    # Step 2: Rollback to certified version 1 -> Must succeed
    res = manager.rollback_to_version(
        tenant_id=tenant_id,
        agent_id=agent_id,
        target_version_id=v1_id,
        reason="Incident in v2.0.0 - reverting to stable v1.0.0",
        initiated_by="ops-admin"
    )
    assert res["status"] == "ROLLED_BACK"
    assert res["active_version_id"] == v1_id

    # Verify pointer switch in DB
    with get_conn() as conn:
        active_ver = conn.execute("SELECT active_version_id FROM af_agent WHERE id = ?", (agent_id,)).fetchone()[0]
        assert active_ver == v1_id, "active_version_id must now point to v1_id"
