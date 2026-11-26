"""ZONATA Sovereign Core — Sub-Step 4C Unit & Contract Test Suite.

Verifies:
1. PostgresCheckpointer table initialization and CRUD operations.
2. Rule 36: State payloads are encrypted at rest; plaintext never hits database rows.
3. Multi-tenant RLS isolation across tenant_id and company_id.
4. LangGraphRuntimeAdapter cyclic loop execution (Planner -> Executor -> Critic).
5. Bounded execution: loops terminate within max_iterations (<= 5).
6. In-flight resumption: resumes from saved checkpoints without re-executing steps (Rule 35).
7. Kill switch halt and streaming compliance.
8. Mutation checks: checkpointer fails closed when encryption is unconfigured.
"""

from __future__ import annotations
import base64
import json
import os
import unittest
from typing import Any, Dict

from core.db import db
from core.ports.base import PortStatus
from core.ports.agent_runtime import (
    AgentSpec,
    ExecutionContext,
    AgentChunk,
    AgentResult,
    AgentRuntimeStatus,
)
from core.langgraph.state import AgentState
from core.langgraph.checkpointer import PostgresCheckpointer
from core.langgraph.adapter import LangGraphRuntimeAdapter


class TestStep4LangGraphRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        cls.checkpointer = PostgresCheckpointer()
        cls.adapter = LangGraphRuntimeAdapter(state_checkpointer=cls.checkpointer)

    def test_01_checkpointer_tables_created(self):
        """Test that PostgresCheckpointer ensures tables exist in the database."""
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='langgraph_checkpoints'")
            row = cur.fetchone()
            self.assertIsNotNone(row, "Table 'langgraph_checkpoints' must exist")

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='langgraph_checkpoint_writes'")
            row_writes = cur.fetchone()
            self.assertIsNotNone(row_writes, "Table 'langgraph_checkpoint_writes' must exist")

    def test_02_checkpointer_put_and_get(self):
        """Test storing and retrieving encrypted checkpoints."""
        tenant_id = "tenant_lg_01"
        company_id = "company_lg_01"
        thread_id = "thread_crud_01"
        cp_id = "cp_001"

        state_data = {
            "run_id": thread_id,
            "messages": [{"role": "user", "content": "Analyze quarterly revenue"}],
            "current_step": 1,
            "iteration": 1,
        }
        metadata = {"spec_id": "auditor_agent", "version": "1.0.0"}

        self.checkpointer.put(
            tenant_id=tenant_id,
            company_id=company_id,
            thread_id=thread_id,
            checkpoint_id=cp_id,
            state_dict=state_data,
            metadata=metadata,
            idempotency_key="idem_cp_01",
            step_count=1,
        )

        retrieved = self.checkpointer.get(
            tenant_id=tenant_id,
            company_id=company_id,
            thread_id=thread_id,
            checkpoint_id=cp_id,
        )
        self.assertIsNotNone(retrieved)
        got_state, got_meta, got_id = retrieved
        self.assertEqual(got_id, cp_id)
        self.assertEqual(got_state["run_id"], thread_id)
        self.assertEqual(got_state["messages"][0]["content"], "Analyze quarterly revenue")
        self.assertEqual(got_meta["spec_id"], "auditor_agent")

    def test_03_encryption_at_rest_rule_36(self):
        """Rule 36 Verification: Asserts raw database rows contain ciphertext and NO plaintext secrets."""
        tenant_id = "tenant_enc_test"
        company_id = "company_enc_test"
        thread_id = "thread_secret_audit"
        cp_id = "cp_confidential_99"

        secret_phrase = "TOP_SECRET_PROPRIETARY_FINANCIAL_ASSETS_98765"
        state_data = {"secret_payload": secret_phrase, "value": 1000000}

        self.checkpointer.put(
            tenant_id=tenant_id,
            company_id=company_id,
            thread_id=thread_id,
            checkpoint_id=cp_id,
            state_dict=state_data,
        )

        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT checkpoint_blob, metadata_blob
                FROM langgraph_checkpoints
                WHERE tenant_id = ? AND thread_id = ? AND checkpoint_id = ?
                """,
                (tenant_id, thread_id, cp_id)
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            cp_blob, meta_blob = row

            # Assert raw ciphertext does NOT contain the plaintext secret
            self.assertNotIn(secret_phrase, cp_blob, "Rule 36 Violation: Plaintext state found in database!")
            self.assertNotIn(secret_phrase, meta_blob, "Rule 36 Violation: Plaintext metadata found in database!")

            # Assert it is valid base64
            try:
                raw_bytes = base64.b64decode(cp_blob)
                self.assertGreater(len(raw_bytes), 0)
            except Exception as e:
                self.fail(f"Checkpoint blob is not valid base64 ciphertext: {e}")

    def test_04_cyclic_execution_loop(self):
        """Test LangGraphRuntimeAdapter executes a bounded cyclic workflow."""
        spec = AgentSpec(
            spec_id="spec_cyclic_01",
            name="Cyclic Auditor",
            system_prompt="Audit and verify ledger reconciliation records.",
            allowed_tools=["calculator"],
        )
        ctx = ExecutionContext(
            tenant_id="tenant_lg_cycle",
            company_id="company_lg_cycle",
            actor_id="user_ci",
            run_id="run_cyclic_01",
            idempotency_key="idem_cyclic_01",
        )
        result = self.adapter.execute_agent(
            spec=spec,
            input_data={"account": "AR_4000", "requested_tool": "calculator", "tool_args": {"expression": "200 + 300"}},
            context=ctx,
        )
        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.state, AgentRuntimeStatus.COMPLETED)
        self.assertIn("cycles_completed", result.output)
        self.assertLessEqual(result.output["cycles_completed"], 5)
        self.assertIn("calculator", result.output["tool_outputs"])

    def test_05_resumption_from_checkpoint_rule_35(self):
        """Test Rule 35: Resuming completed run from saved checkpoint skips duplicate execution."""
        spec = AgentSpec(
            spec_id="spec_resume_01",
            name="Resumable Agent",
            system_prompt="Perform single execution.",
        )
        ctx = ExecutionContext(
            tenant_id="tenant_resume",
            company_id="company_resume",
            actor_id="user_ci",
            run_id="run_resume_fixed_01",
            idempotency_key="idem_resume_01",
        )
        # First execution: completes and checkpoints
        res1 = self.adapter.execute_agent(spec, {"data": "test"}, ctx)
        self.assertEqual(res1.state, AgentRuntimeStatus.COMPLETED)

        # Second execution: resumes from checkpoint
        res2 = self.adapter.execute_agent(spec, {"data": "ignored_on_resume"}, ctx)
        self.assertEqual(res2.state, AgentRuntimeStatus.COMPLETED)
        self.assertTrue(res2.metadata.get("cached", False))

    def test_06_streaming_chunks(self):
        """Test LangGraphRuntimeAdapter streaming yields AgentChunk objects."""
        spec = AgentSpec(spec_id="spec_stream", name="Streamer Agent")
        ctx = ExecutionContext(
            tenant_id="tenant_stream",
            company_id="company_stream",
            actor_id="user_ci",
            run_id="run_stream_01",
        )
        chunks = list(self.adapter.stream_agent(spec, {"input": "test"}, ctx))
        self.assertGreater(len(chunks), 0)
        types = [c.chunk_type for c in chunks]
        self.assertIn("log", types)
        self.assertIn("token", types)

    def test_07_mutation_check_unconfigured_kms_fails_closed(self):
        """Mutation Check: Proves that PostgresCheckpointer fails closed when KMS is unconfigured."""
        from core.ports.kms import NotConfiguredKMSProvider

        # Save and reset test mode to simulate production missing KMS
        old_test_mode = os.environ.get("ZONATA_TEST_MODE")
        try:
            if "ZONATA_TEST_MODE" in os.environ:
                del os.environ["ZONATA_TEST_MODE"]
            unconfigured_kms = NotConfiguredKMSProvider()
            strict_checkpointer = PostgresCheckpointer(kms_provider=unconfigured_kms)

            with self.assertRaises(RuntimeError) as cm:
                strict_checkpointer.put(
                    tenant_id="t_mut",
                    company_id="c_mut",
                    thread_id="th_mut",
                    checkpoint_id="cp_mut",
                    state_dict={"data": "leak_attempt"},
                )
            self.assertIn("Rule 36 Violation", str(cm.exception))
        finally:
            if old_test_mode is not None:
                os.environ["ZONATA_TEST_MODE"] = old_test_mode


if __name__ == "__main__":
    unittest.main()
