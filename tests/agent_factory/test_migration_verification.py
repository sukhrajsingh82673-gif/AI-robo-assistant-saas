"""
ZONATA Agent Factory — Phase 2 Migration Verification Tests
Automated Python test suite implementing all 17 checks from reference/sql/001_verify.sql.
Tests table creation, immutability triggers, freeze triggers, and self-approval blocks.
"""

import unittest
import sqlite3
import uuid
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from migrations.migration_manager import split_sql_statements


class TestMigration0013Verification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(":memory:")
        sql_path = os.path.join(os.path.dirname(__file__), "../../migrations/sqlite/0013_agent_factory_core.sql")
        with open(sql_path, "r") as f:
            sql = f.read()
        stmts = split_sql_statements(sql, dialect="sqlite")
        for stmt in stmts:
            cls.conn.execute(stmt)
        cls.conn.commit()

        cls.tenant_a = "tnt_aaaa_1111"
        cls.tenant_b = "tnt_bbbb_2222"
        cls.company_id = "cmp_test_0001"
        cls.requester_id = "emp_requester_cmo"
        cls.approver_id = "emp_approver_ceo"

    def test_01_all_24_tables_created(self):
        cur = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'af_%'")
        tables = {r[0] for r in cur.fetchall()}
        expected_tables = {
            "af_request", "af_requirement_spec", "af_batch", "af_batch_item",
            "af_template", "af_template_version", "af_capability", "af_agent",
            "af_agent_version", "af_build", "af_artifact", "af_eval_run",
            "af_eval_result", "af_finding", "af_certification", "af_release",
            "af_team", "af_team_member", "af_tool_binding", "af_assignment",
            "af_runtime_instance", "af_lifecycle_event", "af_feedback", "af_quota_usage"
        }
        self.assertTrue(expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}")

    def test_02_all_triggers_created(self):
        cur = self.conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'af_%'")
        triggers = {r[0] for r in cur.fetchall()}
        self.assertIn("af_artifact_immutable_u", triggers)
        self.assertIn("af_certification_immutable_u", triggers)
        self.assertIn("af_lifecycle_immutable_u", triggers)
        self.assertIn("af_release_self_approval_block", triggers)
        self.assertIn("af_eval_independence_block", triggers)

    def test_03_immutability_triggers(self):
        # 1. Artifact immutable
        art_id = f"art_{uuid.uuid4().hex[:8]}"
        self.conn.execute("""
            INSERT INTO af_artifact (id, tenant_id, kind, sha256, size_bytes, storage_uri, created_by, created_at)
            VALUES (?, ?, 'spec', 'hash123', 100, 's3://test/spec', 'builder', ?)
        """, (art_id, self.tenant_a, time.time()))
        self.conn.commit()

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE af_artifact SET sha256 = 'hash_tampered' WHERE id = ?", (art_id,))

        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM af_artifact WHERE id = ?", (art_id,))

    def test_04_agent_version_frozen_after_leaving_building(self):
        agent_id = f"agt_{uuid.uuid4().hex[:8]}"
        ver_id = f"ver_{uuid.uuid4().hex[:8]}"
        now = time.time()
        self.conn.execute("""
            INSERT INTO af_agent (id, tenant_id, company_id, slug, display_name, role_title, category, owner_principal_id, agent_principal_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'Test Agent', 'Tester', 'engineering', ?, ?, ?, ?)
        """, (agent_id, self.tenant_a, self.company_id, f"slug-{agent_id}", self.requester_id, f"prn_{agent_id}", now, now))

        self.conn.execute("""
            INSERT INTO af_agent_version (id, tenant_id, agent_id, semver, spec, spec_sha256, capability_profile, permission_profile, risk_tier, status, created_by, created_at)
            VALUES (?, ?, ?, '1.0.0', '{"a":1}', 'hash_a', '{}', '{}', 'R1', 'BUILDING', 'builder', ?)
        """, (ver_id, self.tenant_a, agent_id, now))
        self.conn.commit()

        # Update while BUILDING is allowed
        self.conn.execute("UPDATE af_agent_version SET spec = '{\"a\":2}', spec_sha256 = 'hash_b' WHERE id = ?", (ver_id,))
        self.conn.commit()

        # Transition to BUILT
        self.conn.execute("UPDATE af_agent_version SET status = 'BUILT' WHERE id = ?", (ver_id,))
        self.conn.commit()

        # Update while BUILT must raise
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE af_agent_version SET spec = '{\"a\":3}' WHERE id = ?", (ver_id,))

        # Delete must raise
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM af_agent_version WHERE id = ?", (ver_id,))

    def test_05_release_self_approval_blocked_at_db_level(self):
        """AT-10: Requester cannot approve their own release."""
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        batch_id = f"bat_{uuid.uuid4().hex[:8]}"
        cert_id = f"cert_{uuid.uuid4().hex[:8]}"
        art_id = f"art_{uuid.uuid4().hex[:8]}"
        rel_id = f"rel_{uuid.uuid4().hex[:8]}"
        now = time.time()

        # Insert Request with requester = self.requester_id
        self.conn.execute("""
            INSERT INTO af_request (id, tenant_id, company_id, requester_principal_id, requester_kind, mode, natural_language, idempotency_key, correlation_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'ai_employee', 'single', 'Build test agent', ?, 'corr_1', ?, ?)
        """, (req_id, self.tenant_a, self.company_id, self.requester_id, f"idem_{req_id}", now, now))

        # Insert Batch
        self.conn.execute("""
            INSERT INTO af_batch (id, tenant_id, company_id, request_id, agent_count, dependency_graph, manifest_sha256, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, '[]', 'manifest_hash', ?, ?)
        """, (batch_id, self.tenant_a, self.company_id, req_id, now, now))

        # Insert Artifact for bundle
        self.conn.execute("""
            INSERT INTO af_artifact (id, tenant_id, kind, sha256, size_bytes, storage_uri, created_by, created_at)
            VALUES (?, ?, 'certification_bundle', 'bundle_hash', 500, 's3://test/cert', 'cert_mgr', ?)
        """, (art_id, self.tenant_a, now))

        # Insert Certification
        self.conn.execute("""
            INSERT INTO af_certification (id, tenant_id, subject_kind, batch_id, gate_policy_version, gate_results, all_mandatory_passed, bundle_artifact_id, evidence_ledger_ref, issued_by, issued_at)
            VALUES (?, ?, 'team', ?, '1.0.0', '[]', 1, ?, 'ev_ref_1', 'cert_mgr', ?)
        """, (cert_id, self.tenant_a, batch_id, art_id, now))

        # Insert Release in PENDING state
        self.conn.execute("""
            INSERT INTO af_release (id, tenant_id, subject_kind, batch_id, certification_id, submitted_by, decision, created_at)
            VALUES (?, ?, 'team', ?, ?, 'release_mgr', 'PENDING', ?)
        """, (rel_id, self.tenant_a, batch_id, cert_id, now))
        self.conn.commit()

        # Attempt self-approval (decided_by_principal == requester_principal_id)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                UPDATE af_release
                SET decision = 'APPROVED', decided_by_principal = ?, approval_id = 'appr_123', decided_at = ?
                WHERE id = ?
            """, (self.requester_id, time.time(), rel_id))

        # Legitimate distinct approver succeeds
        self.conn.execute("""
            UPDATE af_release
            SET decision = 'APPROVED', decided_by_principal = ?, approval_id = 'appr_123', decided_at = ?
            WHERE id = ?
        """, (self.approver_id, time.time(), rel_id))
        self.conn.commit()

        # Decided release is immutable
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE af_release SET decision = 'REJECTED' WHERE id = ?", (rel_id,))

    def test_06_independent_qa_evaluator_must_differ_from_builder(self):
        agent_id = f"agt_{uuid.uuid4().hex[:8]}"
        ver_id = f"ver_{uuid.uuid4().hex[:8]}"
        builder_prn = "factory.agent_builder_01"
        now = time.time()

        self.conn.execute("""
            INSERT INTO af_agent (id, tenant_id, company_id, slug, display_name, role_title, category, owner_principal_id, agent_principal_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'QA Test Agent', 'Tester', 'qa', ?, ?, ?, ?)
        """, (agent_id, self.tenant_a, self.company_id, f"slug-{agent_id}", self.requester_id, f"prn_{agent_id}", now, now))

        self.conn.execute("""
            INSERT INTO af_agent_version (id, tenant_id, agent_id, semver, spec, spec_sha256, capability_profile, permission_profile, risk_tier, status, created_by, created_at)
            VALUES (?, ?, ?, '1.0.0', '{"a":1}', 'hash_qa', '{}', '{}', 'R1', 'BUILT', ?, ?)
        """, (ver_id, self.tenant_a, agent_id, builder_prn, now))
        self.conn.commit()

        # Inserting independent_qa with evaluator == builder must raise
        eval_id_bad = f"eval_{uuid.uuid4().hex[:8]}"
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("""
                INSERT INTO af_eval_run (id, tenant_id, subject_kind, agent_version_id, suite, phase, evaluator_principal, dataset_ref, dataset_sha256, model_profile, started_at)
                VALUES (?, ?, 'agent_version', ?, 'security', 'independent_qa', ?, 'dataset_v1', 'd_hash', 'mock', ?)
            """, (eval_id_bad, self.tenant_a, ver_id, builder_prn, now))

        # Different evaluator succeeds
        eval_id_good = f"eval_{uuid.uuid4().hex[:8]}"
        self.conn.execute("""
            INSERT INTO af_eval_run (id, tenant_id, subject_kind, agent_version_id, suite, phase, evaluator_principal, dataset_ref, dataset_sha256, model_profile, started_at)
            VALUES (?, ?, 'agent_version', ?, 'security', 'independent_qa', 'factory.independent_qa_evaluator', 'dataset_v1', 'd_hash', 'mock', ?)
        """, (eval_id_good, self.tenant_a, ver_id, now))
        self.conn.commit()


if __name__ == "__main__":
    unittest.main()
