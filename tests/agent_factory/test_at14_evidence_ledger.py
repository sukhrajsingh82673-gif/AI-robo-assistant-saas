"""
ZONATA Agent Factory — Acceptance Test AT-14: EvidenceLedger Records Verification
Specification:
  Given: Full lifecycle executed with transitions
  When: Run ledger verification and tamper with one stored row in a copy
  Then: Chain verifies (SHA-256 links + Merkle root); every af_lifecycle_event.evidence_ledger_id resolves;
        tampered copy fails verification at the exact entry.
"""

import unittest
import sqlite3
import json
import tempfile
import uuid
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from agent_factory.ports import Principal, EvidenceEvent
from agent_factory.adapters.zonata import ZonataEvidenceAdapter, ZonataAuthorityAdapter, ZonataKillSwitchAdapter
from agent_factory.domain.transition import transition, TransitionContext
from migrations.migration_manager import split_sql_statements


class TestAT14EvidenceLedgerVerification(unittest.TestCase):
    def setUp(self):
        self.scratch_dir = tempfile.mkdtemp(prefix="zonata_at14_")
        self.ledger_file = os.path.join(self.scratch_dir, "at14_ledger.jsonl")

        self.conn = sqlite3.connect(":memory:")
        sql_path = os.path.join(os.path.dirname(__file__), "../../migrations/sqlite/0013_agent_factory_core.sql")
        with open(sql_path, "r") as f:
            sql = f.read()
        stmts = split_sql_statements(sql, dialect="sqlite")
        for stmt in stmts:
            self.conn.execute(stmt)
        self.conn.commit()

        self.tenant_id = "tnt_at14"
        self.principal = Principal(
            principal_id="emp_cmo_at14",
            tenant_id=self.tenant_id,
            company_id="cmp_at14",
            kind="ai_employee",
            roles=["employee"]
        )

        self.evidence_adapter = ZonataEvidenceAdapter(ledger_file=self.ledger_file)
        self.authority = ZonataAuthorityAdapter()
        self.killswitch = ZonataKillSwitchAdapter()

        self.ctx = TransitionContext(
            tenant_id=self.tenant_id,
            principal=self.principal,
            conn=self.conn,
            authority_port=self.authority,
            evidence_port=self.evidence_adapter,
            killswitch_port=self.killswitch
        )

    def test_at14_lifecycle_events_resolve_and_tamper_detected(self):
        # 1. Create request and perform 3 valid sequential transitions
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        now = time.time()
        self.conn.execute("""
            INSERT INTO af_request (
                id, tenant_id, company_id, requester_principal_id, requester_kind,
                mode, natural_language, status, budget_cap_usd, spent_usd,
                idempotency_key, correlation_id, created_at, updated_at
            ) VALUES (?, ?, 'cmp_at14', 'emp_cmo_at14', 'ai_employee', 'single', 'Test AT-14', 'REQUESTED', 10.0, 0.0, 'idem_at14', 'corr_at14', ?, ?)
        """, (req_id, self.tenant_id, now, now))
        self.conn.commit()

        ev1 = transition(self.ctx, "request", req_id, "ANALYSING", reason="Start analysis")
        ev2 = transition(self.ctx, "request", req_id, "DESIGNING", reason="Analysis complete")
        ev3 = transition(self.ctx, "request", req_id, "BUILDING", reason="Design approved")

        # Verify all lifecycle events in DB have valid non-empty evidence_ledger_id
        cur = self.conn.execute(
            "SELECT to_state, evidence_ledger_id FROM af_lifecycle_event WHERE subject_id = ? ORDER BY id ASC",
            (req_id,)
        )
        events = cur.fetchall()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0][1], ev1)
        self.assertEqual(events[1][1], ev2)
        self.assertEqual(events[2][1], ev3)

        # 2. Verify clean chain integrity
        v_clean = self.evidence_adapter.verify_chain()
        self.assertTrue(v_clean["valid"])
        self.assertEqual(v_clean["records_checked"], 3)
        self.assertIsNotNone(v_clean["merkle_root"])

        # 3. Create a scratch copy and tamper with entry #2
        with open(self.ledger_file, "r") as f:
            lines = [json.loads(l) for l in f if l.strip()]

        self.assertEqual(len(lines), 3)
        lines[1]["sha256_digest"] = "0000000000000000000000000000000000000000000000000000000000000000"

        tampered_ledger_file = os.path.join(self.scratch_dir, "tampered_ledger.jsonl")
        with open(tampered_ledger_file, "w") as f:
            for item in lines:
                f.write(json.dumps(item) + "\n")

        # 4. Verify tampered copy fails verification at the exact entry
        tampered_adapter = ZonataEvidenceAdapter(ledger_file=tampered_ledger_file)
        v_tampered = tampered_adapter.verify_chain()
        self.assertFalse(v_tampered["valid"])
        self.assertGreaterEqual(len(v_tampered["forks_detected"]), 1)
        # Fork detected at index 2 (pointing to tampered index 1)
        self.assertEqual(v_tampered["forks_detected"][0]["index"], 2)


if __name__ == "__main__":
    unittest.main()
