"""
ZONATA Agent Factory — Phase 2 Transition Helper Tests
Validates the evidence-before-effect guarantees of transition().
"""

import unittest
import sqlite3
import uuid
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agent_factory.ports import Principal, Resource
from agent_factory.adapters.fakes import (
    FakeAuthorityAdapter, FakeEvidenceAdapter, FakeKillSwitchAdapter
)
from agent_factory.domain.transition import (
    transition, TransitionContext, InvalidTransitionError, TransitionForbiddenError
)
from migrations.migration_manager import split_sql_statements


class TestTransitionHelper(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        sql_path = os.path.join(os.path.dirname(__file__), "../../migrations/sqlite/0013_agent_factory_core.sql")
        with open(sql_path, "r") as f:
            sql = f.read()
        stmts = split_sql_statements(sql, dialect="sqlite")
        for stmt in stmts:
            self.conn.execute(stmt)
        self.conn.commit()

        self.tenant_id = "tnt_trans_test"
        self.principal = Principal(
            principal_id="emp_test_user",
            tenant_id=self.tenant_id,
            company_id="cmp_001",
            kind="ai_employee",
            roles=["employee"]
        )

        self.authority = FakeAuthorityAdapter(default_allow=True)
        self.evidence = FakeEvidenceAdapter(fail_append=False)
        self.killswitch = FakeKillSwitchAdapter()

        self.ctx = TransitionContext(
            tenant_id=self.tenant_id,
            principal=self.principal,
            conn=self.conn,
            authority_port=self.authority,
            evidence_port=self.evidence,
            killswitch_port=self.killswitch,
            meta={"correlation_id": "corr_test_01"}
        )

        # Seed an af_request
        self.request_id = f"req_{uuid.uuid4().hex[:8]}"
        now = time.time()
        self.conn.execute("""
            INSERT INTO af_request (
                id, tenant_id, company_id, requester_principal_id, requester_kind,
                mode, natural_language, status, budget_cap_usd, spent_usd,
                idempotency_key, correlation_id, created_at, updated_at
            ) VALUES (?, ?, 'cmp_001', 'emp_test_user', 'ai_employee', 'single', 'Test request', 'REQUESTED', 10.0, 0.0, 'idem_1', 'corr_1', ?, ?)
        """, (self.request_id, self.tenant_id, now, now))
        self.conn.commit()

    def test_01_valid_transition_records_evidence_and_lifecycle_event(self):
        ev_id = transition(
            self.ctx, "request", self.request_id, "ANALYSING",
            reason="Starting analysis",
            expect_from="REQUESTED"
        )
        self.assertIsNotNone(ev_id)
        self.assertTrue(ev_id.startswith("EV-FAKE-"))

        # Check DB state updated
        cur = self.conn.execute("SELECT status FROM af_request WHERE id = ?", (self.request_id,))
        self.assertEqual(cur.fetchone()[0], "ANALYSING")

        # Check af_lifecycle_event inserted with evidence_ledger_id
        cur = self.conn.execute(
            "SELECT from_state, to_state, evidence_ledger_id, actor FROM af_lifecycle_event WHERE subject_id = ?",
            (self.request_id,)
        )
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "REQUESTED")
        self.assertEqual(row[1], "ANALYSING")
        self.assertEqual(row[2], ev_id)
        self.assertEqual(row[3], "emp_test_user")

    def test_02_invalid_transition_rejected(self):
        # Cannot jump from REQUESTED directly to PUBLISHING
        with self.assertRaises(InvalidTransitionError):
            transition(
                self.ctx, "request", self.request_id, "PUBLISHING",
                reason="Direct jump attempt"
            )

        # Status must remain REQUESTED
        cur = self.conn.execute("SELECT status FROM af_request WHERE id = ?", (self.request_id,))
        self.assertEqual(cur.fetchone()[0], "REQUESTED")

    def test_03_fail_closed_guarantee_on_evidence_error(self):
        """If evidence append raises an exception, the state mutation must fail and roll back."""
        failing_evidence = FakeEvidenceAdapter(fail_append=True)
        fail_ctx = TransitionContext(
            tenant_id=self.tenant_id,
            principal=self.principal,
            conn=self.conn,
            authority_port=self.authority,
            evidence_port=failing_evidence,
            killswitch_port=self.killswitch
        )

        with self.assertRaises(RuntimeError):
            transition(
                fail_ctx, "request", self.request_id, "ANALYSING",
                reason="Attempt with failing ledger"
            )

        # State must NOT be ANALYSING
        cur = self.conn.execute("SELECT status FROM af_request WHERE id = ?", (self.request_id,))
        self.assertEqual(cur.fetchone()[0], "REQUESTED")

    def test_04_killswitch_blocks_transition(self):
        self.killswitch.activate("REQUEST", self.request_id)
        with self.assertRaises(PermissionError):
            transition(
                self.ctx, "request", self.request_id, "ANALYSING",
                reason="Attempt while killed"
            )

    def test_05_authority_denial_blocks_transition(self):
        self.authority.deny_actions.add("factory.request.analysing")
        with self.assertRaises(TransitionForbiddenError):
            transition(
                self.ctx, "request", self.request_id, "ANALYSING",
                reason="Attempt with denied authority"
            )


if __name__ == "__main__":
    unittest.main()
