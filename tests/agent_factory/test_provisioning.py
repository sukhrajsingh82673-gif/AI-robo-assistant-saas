"""ZONATA Agent Factory - Workforce Provisioning Tests."""

import sqlite3
import pytest
import time

from agent_factory.registry.provisioner import WorkforceProvisioner, ProvisioningError
from agent_factory.adapters.fakes import FakeEvidenceAdapter, FakeWorkforceAdapter

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_prov.db"
    conn = sqlite3.connect(str(db_file))
    with open("migrations/sqlite/0013_agent_factory_core.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    return str(db_file)

def test_workforce_assignment_and_revocation(test_db):
    def get_conn():
        return sqlite3.connect(test_db)

    evidence = FakeEvidenceAdapter()
    workforce = FakeWorkforceAdapter()
    provisioner = WorkforceProvisioner(
        db_conn_factory=get_conn,
        evidence_port=evidence,
        workforce_port=workforce
    )

    tenant_id = "tenant-prov-1"
    company_id = "comp-prov-1"
    agent_id = "agt-support"
    version_id = "agv-support-v1"
    now = time.time()

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO af_agent (
                id, tenant_id, company_id, slug, display_name, role_title,
                category, owner_principal_id, agent_principal_id, active_version_id,
                lifecycle, created_at, updated_at
            ) VALUES (?, ?, ?, 'support', 'Support Agent', 'Support Specialist', 'customer_support', 'admin', 'pr_sup', ?, 'ACTIVE', ?, ?)
        """, (agent_id, tenant_id, company_id, version_id, now, now))
        conn.commit()

    # Step 1: Assign agent to department 'CustomerSupport'
    res = provisioner.assign(
        tenant_id=tenant_id,
        company_id=company_id,
        agent_id=agent_id,
        agent_version_id=version_id,
        assignee_kind="department",
        assignee_id="dept-cs",
        assigned_by="hr-admin"
    )
    assert res["status"] == "ACTIVE"
    asgn_id = res["assignment_id"]
    assert asgn_id.startswith("asgn_")

    with get_conn() as conn:
        asgn_row = conn.execute("SELECT status, assignee_kind, assignee_id FROM af_assignment WHERE id = ?", (asgn_id,)).fetchone()
        assert asgn_row[0] == "ACTIVE"
        assert asgn_row[1] == "department"
        assert asgn_row[2] == "dept-cs"

    # Step 2: Revoke assignment
    rev_res = provisioner.revoke(
        tenant_id=tenant_id,
        assignment_id=asgn_id,
        revoked_by="hr-admin"
    )
    assert rev_res["status"] == "REVOKED"

    with get_conn() as conn:
        rev_row = conn.execute("SELECT status, ended_at FROM af_assignment WHERE id = ?", (asgn_id,)).fetchone()
        assert rev_row[0] == "REVOKED"
        assert rev_row[1] is not None
