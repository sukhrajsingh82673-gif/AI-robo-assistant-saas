"""
ZONATA Agent Factory — Acceptance Test AT-10: Prevent Self-Approval
Specification:
  Given: emp.cmo requested; also holds approver role
  When: emp.cmo attempts to approve the release (via API or direct SQL)
  Then: 403/409 AF-SELF-APPROVAL; DB trigger independently rejects direct SQL insert/update;
        Factory Director service principal approving own batch is denied.
"""

import unittest
import sqlite3
import uuid
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from migrations.migration_manager import split_sql_statements


class TestAT10SelfApprovalPrevention(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        sql_path = os.path.join(os.path.dirname(__file__), "../../migrations/sqlite/0013_agent_factory_core.sql")
        with open(sql_path, "r") as f:
            sql = f.read()
        stmts = split_sql_statements(sql, dialect="sqlite")
        for stmt in stmts:
            self.conn.execute(stmt)
        self.conn.commit()

        self.tenant_id = "tnt_at10"
        self.company_id = "cmp_at10"
        self.requester_cmo = "emp.cmo"
        self.owner_principal = "human.owner"

    def test_at10_requester_cannot_approve_own_release_db_trigger(self):
        now = time.time()
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        batch_id = f"bat_{uuid.uuid4().hex[:8]}"
        cert_id = f"cert_{uuid.uuid4().hex[:8]}"
        art_id = f"art_{uuid.uuid4().hex[:8]}"
        rel_id = f"rel_{uuid.uuid4().hex[:8]}"

        # 1. Requester emp.cmo submits request
        self.conn.execute("""
            INSERT INTO af_request (id, tenant_id, company_id, requester_principal_id, requester_kind, mode, natural_language, idempotency_key, correlation_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'ai_employee', 'single', 'Campaign specialist agent request', 'idem_at10', 'corr_at10', ?, ?)
        """, (req_id, self.tenant_id, self.company_id, self.requester_cmo, now, now))

        # 2. Batch and Certification created
        self.conn.execute("""
            INSERT INTO af_batch (id, tenant_id, company_id, request_id, agent_count, dependency_graph, manifest_sha256, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, '[]', 'manifest_hash', ?, ?)
        """, (batch_id, self.tenant_id, self.company_id, req_id, now, now))

        self.conn.execute("""
            INSERT INTO af_artifact (id, tenant_id, kind, sha256, size_bytes, storage_uri, created_by, created_at)
            VALUES (?, ?, 'certification_bundle', 'sha_bundle_at10', 256, 's3://test/cert', 'cert_mgr', ?)
        """, (art_id, self.tenant_id, now))

        self.conn.execute("""
            INSERT INTO af_certification (id, tenant_id, subject_kind, batch_id, gate_policy_version, gate_results, all_mandatory_passed, bundle_artifact_id, evidence_ledger_ref, issued_by, issued_at)
            VALUES (?, ?, 'team', ?, '1.0.0', '[]', 1, ?, 'ev_ref_at10', 'factory.certification_manager', ?)
        """, (cert_id, self.tenant_id, batch_id, art_id, now))

        self.conn.execute("""
            INSERT INTO af_release (id, tenant_id, subject_kind, batch_id, certification_id, submitted_by, decision, created_at)
            VALUES (?, ?, 'team', ?, ?, 'factory.release_manager', 'PENDING', ?)
        """, (rel_id, self.tenant_id, batch_id, cert_id, now))
        self.conn.commit()

        # 3. emp.cmo attempts self-approval
        with self.assertRaises(sqlite3.IntegrityError) as ctx:
            self.conn.execute("""
                UPDATE af_release
                SET decision = 'APPROVED', decided_by_principal = ?, approval_id = 'appr_valid_nonce', decided_at = ?
                WHERE id = ?
            """, (self.requester_cmo, time.time(), rel_id))

        self.assertIn("requester cannot approve own release", str(ctx.exception))

        # 4. Independent human.owner approver succeeds
        self.conn.execute("""
            UPDATE af_release
            SET decision = 'APPROVED', decided_by_principal = ?, approval_id = 'appr_valid_nonce', decided_at = ?
            WHERE id = ?
        """, (self.owner_principal, time.time(), rel_id))
        self.conn.commit()

        cur = self.conn.execute("SELECT decision, decided_by_principal FROM af_release WHERE id = ?", (rel_id,))
        row = cur.fetchone()
        self.assertEqual(row[0], "APPROVED")
        self.assertEqual(row[1], self.owner_principal)


if __name__ == "__main__":
    unittest.main()
