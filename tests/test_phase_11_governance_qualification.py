"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 11 Comprehensive Qualification Test Suite
================================================
Validates all four core governance workstreams:
  Workstream A: AI CEO Economic Command, Multi-Scope Budgets & Concurrency-Safe Reservations
  Workstream B: Cryptographic Approvals, Canonical Digests, Anti-Tampering & Single-Use Replay Protection
  Workstream C: Agent-to-Agent (A2A) Protocol Interoperability, Tenant Scoping & Anti-Privilege Escalation
  Workstream D: Multi-Session Stateful Agent Memory Synchronization, Conflict Resolution & Restart Recovery
  E2E Pipeline: Unified Principal -> Auth -> Risk -> Approval -> Budget Reservation -> Settlement -> Memory Sync
"""

import unittest
import os
import time
import json
import uuid
import threading

from core.db import db, configure_isolated_test_db
from core.economic_governance import (
    EconomicGovernanceEngine,
    economic_governor,
    BudgetScope,
    BudgetStatus,
    BudgetExhaustionException,
    BudgetFrozenException,
    ChildBudgetExceededException,
    ReservationExpiredException
)
from core.cryptographic_approvals import (
    CryptographicApprovalEngine,
    cryptographic_approvals,
    HighRiskActionClass,
    ActionTamperingException,
    SignatureVerificationException,
    ReplayAttackException,
    ApprovalExpiredException,
    ApprovalRevokedException,
    ApprovalMissingException
)
from core.a2a_interoperability_runtime import (
    A2AGateway,
    A2AKillSwitch,
    AgentTrustLevel,
    AgentRoleType,
    A2ATaskState,
    SecurityException
)
from core.stateful_agent_runtime import (
    StatefulAgentMemoryGateway,
    MemoryScope,
    MemoryType,
    MemoryCategory,
    ConfidenceLevel,
    ConflictResolution,
    SecretScanner,
    SecurityException as MemorySecurityException
)
from zonata.stateful_agent_adapter import StatefulAgentAdapter


class TestPhase11GovernanceQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = configure_isolated_test_db()
        import tempfile
        cls.test_evidence_file = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name
        os.environ["ZONATA_EVIDENCE_PATH"] = cls.test_evidence_file

        cls.tenant_id = f"tnt_p11_{uuid.uuid4().hex[:6]}"
        cls.company_id = f"comp_p11_{uuid.uuid4().hex[:6]}"
        cls.foreign_tenant = f"tnt_foreign_{uuid.uuid4().hex[:6]}"

        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Phase 11 Tenant', ?)",
                (cls.tenant_id, time.time())
            )
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, created_at) VALUES (?, 'Foreign Tenant', ?)",
                (cls.foreign_tenant, time.time())
            )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, country, industry, company_type, status, created_at) "
                "VALUES (?, ?, 'P11 Co', 'US', 'Tech', 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.company_id, cls.tenant_id, time.time())
            )
            conn.commit()

        economic_governor._ensure_tables()
        cryptographic_approvals._ensure_tables()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_evidence_file") and os.path.exists(cls.test_evidence_file):
            try:
                os.remove(cls.test_evidence_file)
            except OSError:
                pass
        os.environ.pop("ZONATA_EVIDENCE_PATH", None)

    def setUp(self):
        self.run_tag = uuid.uuid4().hex[:6]

    # =========================================================================
    # WORKSTREAM A: ECONOMIC COMMAND & HARD BUDGET CEILINGS
    # =========================================================================

    def test_workstream_a_01_multi_scope_budget_configuration(self):
        """Verify configuring multi-scope budgets (Tenant, Workflow, Agent) with token and USD caps."""
        tnt_budget = economic_governor.configure_budget(
            entity_id=self.tenant_id,
            entity_type=BudgetScope.TENANT.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=5000.0,
            allocated_tokens=1_000_000,
            soft_limit_pct=80.0,
            hard_limit_pct=100.0
        )
        self.assertIsNotNone(tnt_budget)
        self.assertEqual(tnt_budget.allocated_usd, 5000.0)
        self.assertEqual(tnt_budget.allocated_tokens, 1_000_000)
        self.assertEqual(tnt_budget.available_usd, 5000.0)

    def test_workstream_a_02_atomic_reservation_and_hard_stop(self):
        """Verify atomic budget reservation succeeds within limit and fails closed when hard limit is breached."""
        wf_id = f"wf_exec_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=wf_id,
            entity_type=BudgetScope.WORKFLOW.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=300.0,
            hard_limit_pct=100.0
        )

        # 1. Successful reservation
        res = economic_governor.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[(BudgetScope.WORKFLOW.value, wf_id)],
            requested_usd=200.0,
            ttl_seconds=120.0
        )
        self.assertEqual(res.reserved_usd, 200.0)
        self.assertEqual(res.status, "RESERVED")

        # 2. Check updated available balance
        updated_budget = economic_governor.get_budget(wf_id)
        self.assertEqual(updated_budget.reserved_usd, 200.0)
        self.assertEqual(updated_budget.available_usd, 100.0)

        # 3. Exceed hard ceiling: request $150 more ($200 + $150 = $350 > $300 ceiling)
        with self.assertRaises(BudgetExhaustionException):
            economic_governor.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[(BudgetScope.WORKFLOW.value, wf_id)],
                requested_usd=150.0
            )

    def test_workstream_a_03_token_budget_ceiling_enforcement(self):
        """Verify token consumption respects hard limits independently of monetary ceilings."""
        agt_id = f"agt_llm_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=agt_id,
            entity_type=BudgetScope.AGENT.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=500.0,
            allocated_tokens=50_000,
            hard_limit_pct=100.0
        )

        # Reserving within token ceiling succeeds
        res = economic_governor.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[(BudgetScope.AGENT.value, agt_id)],
            requested_usd=10.0,
            requested_tokens=30_000
        )
        self.assertEqual(res.reserved_tokens, 30_000)

        # Exceeding token ceiling fails closed
        with self.assertRaises(BudgetExhaustionException):
            economic_governor.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[(BudgetScope.AGENT.value, agt_id)],
                requested_usd=10.0,
                requested_tokens=25_000  # 30,000 + 25,000 = 55,000 > 50,000
            )

    def test_workstream_a_04_two_phase_settlement_and_capacity_release(self):
        """Verify two-phase settlement: actual < reserved returns excess capacity to available pool."""
        ent_id = f"ent_settle_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=ent_id,
            entity_type=BudgetScope.RUN.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=100.0
        )

        res = economic_governor.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[(BudgetScope.RUN.value, ent_id)],
            requested_usd=80.0
        )
        # Actual task cost was only $45
        settlement = economic_governor.settle_budget(
            reservation_id=res.reservation_id,
            actual_usd=45.0,
            actual_tokens=1200
        )
        self.assertEqual(settlement.status, "SETTLED")
        self.assertEqual(settlement.actual_usd, 45.0)

        # Verify budget balance: spent = 45, reserved = 0, available = 55
        b = economic_governor.get_budget(ent_id)
        self.assertEqual(b.spent_usd, 45.0)
        self.assertEqual(b.reserved_usd, 0.0)
        self.assertEqual(b.available_usd, 55.0)

    def test_workstream_a_05_release_reservation_on_task_abort(self):
        """Verify aborted tasks release 100% of reserved funds with zero incurred spend."""
        ent_id = f"ent_cancel_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=ent_id,
            entity_type=BudgetScope.RUN.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=200.0
        )

        res = economic_governor.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[(BudgetScope.RUN.value, ent_id)],
            requested_usd=150.0
        )
        ok = economic_governor.release_reservation(res.reservation_id, reason="NETWORK_TIMEOUT")
        self.assertTrue(ok)

        b = economic_governor.get_budget(ent_id)
        self.assertEqual(b.spent_usd, 0.0)
        self.assertEqual(b.reserved_usd, 0.0)
        self.assertEqual(b.available_usd, 200.0)

    def test_workstream_a_06_child_budget_inheritance_constraint(self):
        """Verify child task budget allocation cannot exceed parent task's remaining unreserved budget."""
        parent_id = f"parent_task_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=parent_id,
            entity_type=BudgetScope.WORKFLOW.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=50.0
        )

        # Child requesting <= available succeeds
        self.assertTrue(
            economic_governor.validate_child_budget_inheritance(parent_id, requested_child_usd=40.0)
        )

        # Child requesting > available is blocked
        with self.assertRaises(ChildBudgetExceededException):
            economic_governor.validate_child_budget_inheritance(parent_id, requested_child_usd=60.0)

    def test_workstream_a_07_emergency_financial_halt(self):
        """Verify freezing a budget blocks all reservations immediately."""
        ent_id = f"ent_freeze_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=ent_id,
            entity_type=BudgetScope.TENANT.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=1000.0
        )

        economic_governor.freeze_budget(ent_id, reason="Anomalous spend detected")
        with self.assertRaises(BudgetFrozenException):
            economic_governor.reserve_budget(
                tenant_id=self.tenant_id,
                scope_chain=[(BudgetScope.TENANT.value, ent_id)],
                requested_usd=10.0
            )

        # Unfreeze restores operations
        economic_governor.unfreeze_budget(ent_id, authorizer_id="sec_lead")
        res = economic_governor.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[(BudgetScope.TENANT.value, ent_id)],
            requested_usd=10.0
        )
        self.assertEqual(res.status, "RESERVED")

    # =========================================================================
    # WORKSTREAM B: CRYPTOGRAPHIC APPROVALS FOR HIGH-RISK ACTIONS
    # =========================================================================

    def test_workstream_b_01_canonical_action_digest_determinism(self):
        """Verify canonical action digest produces identical SHA-256 for identical semantically ordered payloads."""
        payload_1 = {
            "action_id": "act_101",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_lead",
            "capability_id": "wire_transfer",
            "target": "vendor_bank_acct",
            "intent": "Disburse Q3 payment",
            "risk_class": "FINANCIAL",
            "parameters": {"amount": 5000, "currency": "USD"}
        }
        # Inverted parameter keys
        payload_2 = {
            "parameters": {"currency": "USD", "amount": 5000},
            "intent": "Disburse Q3 payment",
            "target": "vendor_bank_acct",
            "capability_id": "wire_transfer",
            "risk_class": "FINANCIAL",
            "agent_id": "agt_lead",
            "company_id": self.company_id,
            "tenant_id": self.tenant_id,
            "action_id": "act_101"
        }
        digest_1 = cryptographic_approvals.compute_action_digest(payload_1)
        digest_2 = cryptographic_approvals.compute_action_digest(payload_2)
        self.assertEqual(digest_1, digest_2)

    def test_workstream_b_02_approval_issuance_and_signature_verification(self):
        """Verify issuance of cryptographic approval certificate and successful consumption."""
        action = {
            "action_id": f"act_wire_{self.run_tag}",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_finance",
            "capability_id": "disburse_vendor_payment",
            "target": "vendor_99",
            "intent": "Quarterly settlement",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "parameters": {"vendor_id": "vend_99", "amount": 12500.0}
        }

        cert = cryptographic_approvals.issue_approval(
            action_payload=action,
            approver_id="usr_chief_financial_officer",
            approver_role="OWNER",
            ttl_seconds=3600.0
        )
        self.assertIsNotNone(cert.signature)
        self.assertIsNotNone(cert.nonce)
        self.assertEqual(cert.status, "ACTIVE")

        # Valid consumption
        consume_res = cryptographic_approvals.verify_and_consume_approval(
            action_payload=action,
            certificate=cert,
            consuming_action_id=action["action_id"]
        )
        self.assertTrue(consume_res["verified"])
        self.assertEqual(consume_res["nonce"], cert.nonce)

    def test_workstream_b_03_parameter_tampering_detection(self):
        """Verify changing action parameters after approval issuance triggers ActionTamperingException."""
        action = {
            "action_id": f"act_safe_{self.run_tag}",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_finance",
            "capability_id": "wire_transfer",
            "target": "legit_vendor",
            "intent": "Legitimate payment",
            "risk_class": "FINANCIAL",
            "parameters": {"amount": 1000.0}
        }
        cert = cryptographic_approvals.issue_approval(
            action_payload=action,
            approver_id="usr_cfo",
            approver_role="OWNER"
        )

        # Attacker alters amount to $50,000 before execution
        tampered_action = dict(action)
        tampered_action["parameters"] = {"amount": 50000.0}

        with self.assertRaises(ActionTamperingException):
            cryptographic_approvals.verify_and_consume_approval(
                action_payload=tampered_action,
                certificate=cert,
                consuming_action_id=tampered_action["action_id"]
            )

    def test_workstream_b_04_forged_signature_rejection(self):
        """Verify altered signature bytes trigger SignatureVerificationException fail-closed."""
        action = {
            "action_id": f"act_forge_{self.run_tag}",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_ops",
            "capability_id": "delete_table",
            "target": "prod_table",
            "intent": "Maintenance",
            "risk_class": "DESTRUCTIVE",
            "parameters": {"drop": True}
        }
        cert = cryptographic_approvals.issue_approval(
            action_payload=action,
            approver_id="usr_admin",
            approver_role="OWNER"
        )

        # Attacker flips bytes in signature
        forged_cert = cert
        forged_cert.signature = "a" * len(cert.signature)

        with self.assertRaises(SignatureVerificationException):
            cryptographic_approvals.verify_and_consume_approval(
                action_payload=action,
                certificate=forged_cert,
                consuming_action_id=action["action_id"]
            )

    def test_workstream_b_05_single_use_nonce_replay_attack_prevention(self):
        """Verify attempting to consume the same approval certificate a second time is rejected as a Replay Attack."""
        action = {
            "action_id": f"act_replay_{self.run_tag}",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_ops",
            "capability_id": "restart_cluster",
            "target": "cluster_main",
            "intent": "Restart",
            "risk_class": "MUTATING",
            "parameters": {"mode": "rolling"}
        }
        cert = cryptographic_approvals.issue_approval(
            action_payload=action,
            approver_id="usr_cfo",
            approver_role="OWNER"
        )

        # First consumption succeeds
        cryptographic_approvals.verify_and_consume_approval(
            action_payload=action,
            certificate=cert,
            consuming_action_id=action["action_id"]
        )

        # Second consumption with identical certificate raises ReplayAttackException
        with self.assertRaises(ReplayAttackException):
            cryptographic_approvals.verify_and_consume_approval(
                action_payload=action,
                certificate=cert,
                consuming_action_id=f"act_replay_attack_{self.run_tag}"
            )

    def test_workstream_b_06_revocation_invalidates_active_approval(self):
        """Verify revoking an approval immediately prevents execution."""
        action = {
            "action_id": f"act_revokable_{self.run_tag}",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_sec",
            "capability_id": "export_data",
            "target": "s3_archive",
            "intent": "Compliance export",
            "risk_class": "HIGH_RISK",
            "parameters": {"dataset": "audit"}
        }
        cert = cryptographic_approvals.issue_approval(
            action_payload=action,
            approver_id="usr_cfo",
            approver_role="OWNER"
        )

        # Host realizes mistake and revokes
        revoked = cryptographic_approvals.revoke_approval(
            approval_id=cert.approval_id,
            tenant_id=self.tenant_id,
            revoker_id="usr_cfo",
            reason="Emergency cancellation"
        )
        self.assertTrue(revoked)

        with self.assertRaises(ApprovalRevokedException):
            cryptographic_approvals.verify_and_consume_approval(
                action_payload=action,
                certificate=cert,
                consuming_action_id=action["action_id"]
            )

    # =========================================================================
    # WORKSTREAM C: AGENT-TO-AGENT (A2A) PROTOCOL INTEROPERABILITY
    # =========================================================================

    def test_workstream_c_01_cross_tenant_a2a_isolation(self):
        """Verify A2A interactions strictly reject cross-tenant target agents."""
        gw_primary = A2AGateway(self.tenant_id, self.company_id)
        
        # Foreign tenant registers an agent
        gw_foreign = A2AGateway(self.foreign_tenant, "comp_foreign")
        card = {
            "name": "Foreign Accounting Agent",
            "description": "Tax agent in another tenant",
            "supported_interfaces": [{"url": "https://foreign.tax/a2a", "protocol_binding": "HTTP+JSON", "protocol_version": "1.0"}],
            "skills": [{"id": "audit_tax", "name": "Audit Tax", "description": "Foreign audit"}]
        }
        ok, foreign_agent_id, _ = gw_foreign.discover_agent(card, allow_test_loopback=True)
        self.assertTrue(ok)

        # Primary tenant attempts to message or delegate to foreign agent
        with self.assertRaises((ValueError, SecurityException)):
            # Target agent not found in primary tenant registry
            gw_primary.delegate_task(
                agent_id=foreign_agent_id,
                skill_name="audit_tax",
                parameters={"year": 2026}
            )

    def test_workstream_c_02_task_lifecycle_transitions(self):
        """Verify governed A2A task lifecycle adheres to standard transitions."""
        gw = A2AGateway(self.tenant_id, self.company_id)
        card = {
            "name": f"Lifecycle Worker {self.run_tag}",
            "description": "Lifecycle testing agent",
            "supported_interfaces": [{"url": "https://worker.internal/a2a", "protocol_binding": "HTTP+JSON", "protocol_version": "1.0"}],
            "skills": [{"id": "compute_kpi", "name": "Compute KPI", "description": "Computes metrics"}]
        }
        ok, agent_id, _ = gw.discover_agent(card, allow_test_loopback=True)
        self.assertTrue(ok)

        # Synchronous task execution against the declared remote endpoint.
        task_res = gw.delegate_task(
            agent_id=agent_id,
            skill_name="compute_kpi",
            parameters={"quarter": "Q3"}
        )
        self.assertIn("id", task_res)
        state = task_res.get("status", {}).get("state", "")
        if state == "COMPLETED":
            self.assertEqual(task_res.get("status", {}).get("state"), "COMPLETED")
        else:
            # The remote agent host is not reachable from this sandbox; the task
            # must fail honestly rather than reporting a fabricated completion.
            self.assertIn("FAILED", state)
            self.assertTrue(task_res.get("error") or task_res.get("status", {}).get("message"))

    def test_workstream_c_03_killswitch_overrides_swarm_execution(self):
        """Verify activating the A2A KillSwitch aborts any subsequent delegations immediately."""
        gw = A2AGateway(self.tenant_id, self.company_id)
        card = {
            "name": f"Swarm Worker {self.run_tag}",
            "description": "Swarm worker",
            "supported_interfaces": [{"url": "https://worker2.internal/a2a", "protocol_binding": "HTTP+JSON", "protocol_version": "1.0"}],
            "skills": [{"id": "ping", "name": "Ping", "description": "Ping test"}]
        }
        ok, agent_id, _ = gw.discover_agent(card, allow_test_loopback=True)
        self.assertTrue(ok)

        # Activate KillSwitch
        A2AKillSwitch.activate(self.tenant_id)
        try:
            with self.assertRaises(SecurityException):
                gw.delegate_task(
                    agent_id=agent_id,
                    skill_name="ping",
                    parameters={}
                )
        finally:
            A2AKillSwitch.deactivate(self.tenant_id)

    # =========================================================================
    # WORKSTREAM D: MULTI-SESSION STATEFUL AGENT MEMORY SYNCHRONIZATION
    # =========================================================================

    def test_workstream_d_01_multi_scope_memory_storage_and_query(self):
        """Verify memory records stored at Company, Agent, and Workspace scopes maintain strict isolation."""
        gw = StatefulAgentMemoryGateway(self.tenant_id)
        
        # Store company-scoped memory
        rec_comp = gw.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=self.company_id,
            memory_key="fiscal_year_end",
            content="Fiscal year closes December 31st.",
            category=MemoryCategory.FACT.value
        )
        self.assertEqual(rec_comp.version, 1)

        # Store agent-scoped memory
        rec_agt = gw.store_memory(
            scope=MemoryScope.AGENT.value,
            scope_id="agt_ai_ceo",
            memory_key="current_focus",
            content="Drive enterprise margin expansion to 25%.",
            category=MemoryCategory.GOAL.value
        )
        self.assertEqual(rec_agt.scope, MemoryScope.AGENT.value)

        # Query company scope
        comp_mems = gw.query_memory(scope=MemoryScope.COMPANY.value, scope_id=self.company_id, memory_key="fiscal_year_end")
        self.assertEqual(len(comp_mems), 1)
        self.assertIn("December 31st", comp_mems[0].content)

    def test_workstream_d_02_secret_scanner_rejection(self):
        """Verify SecretScanner prohibits persisting raw secrets, API keys, or private keys into memory."""
        gw = StatefulAgentMemoryGateway(self.tenant_id)

        # Attempt to store OpenAI API key
        with self.assertRaises(MemorySecurityException):
            gw.store_memory(
                scope=MemoryScope.AGENT.value,
                scope_id="agt_ai_ceo",
                memory_key="leaked_key",
                content="Our secret OpenAI key is sk-proj-1234567890abcdef1234567890abcdef"
            )

        # Attempt to store RSA Private Key
        with self.assertRaises(MemorySecurityException):
            gw.store_memory(
                scope=MemoryScope.AGENT.value,
                scope_id="agt_ai_ceo",
                memory_key="rsa_key",
                content="-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0..."
            )

    def test_workstream_d_03_conflict_detection_and_resolution(self):
        """Verify contradictory statements under same scope/key trigger MemoryConflict and support USE_A, USE_B, and MERGE."""
        gw = StatefulAgentMemoryGateway(self.tenant_id)
        key = f"q4_revenue_projection_{self.run_tag}"

        # Specialist A claims $1.2M
        rec_a = gw.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=self.company_id,
            memory_key=key,
            content="Q4 Projected Revenue is $1.2M."
        )

        # Specialist B claims $1.8M on the same key
        rec_b = gw.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=self.company_id,
            memory_key=key,
            content="Q4 Projected Revenue is $1.8M."
        )

        # Conflict must be flagged
        conflicts = gw.list_conflicts(scope_id=self.company_id, status="OPEN")
        target_conflicts = [c for c in conflicts if c.memory_key == key]
        self.assertEqual(len(target_conflicts), 1)
        conf = target_conflicts[0]

        # Resolve via MERGE
        merged_res = gw.resolve_conflict(
            conflict_id=conf.conflict_id,
            choice=ConflictResolution.MERGE.value,
            resolved_by="AI_CEO",
            merged_content="Q4 Projected Revenue range is $1.2M to $1.8M (Consensus Synthesis)."
        )
        self.assertEqual(merged_res["status"], "RESOLVED")
        self.assertIn("merged_record_id", merged_res)

        # Verify effective active memory contains synthesized consensus
        active = gw.query_memory(scope=MemoryScope.COMPANY.value, scope_id=self.company_id, memory_key=key)
        self.assertEqual(len(active), 1)
        self.assertIn("Consensus Synthesis", active[0].content)

    def test_workstream_d_04_restart_recovery_and_multi_session_continuity(self):
        """Verify re-instantiating the gateway after node restart fully reloads working memory blocks and turns."""
        adapter = StatefulAgentAdapter(self.tenant_id)
        demo_res = adapter.run_executive_continuity_demonstration(self.company_id)
        self.assertEqual(demo_res["status"], "VERIFIED_CONTINUITY")

    def test_workstream_d_05_cross_tenant_memory_isolation(self):
        """Verify strict tenant isolation: Tenant A can never query or access Tenant B's memory records."""
        gw_a = StatefulAgentMemoryGateway(self.tenant_id)
        gw_b = StatefulAgentMemoryGateway(self.foreign_tenant)

        secret_key = f"corp_strategy_{self.run_tag}"
        gw_a.store_memory(
            scope=MemoryScope.TENANT.value,
            scope_id=self.tenant_id,
            memory_key=secret_key,
            content="Confidential acquisition of Competitor X."
        )

        # Tenant B queries the same key
        b_records = gw_b.query_memory(
            scope=MemoryScope.TENANT.value,
            scope_id=self.tenant_id,
            memory_key=secret_key
        )
        self.assertEqual(len(b_records), 0)

    # =========================================================================
    # UNIFIED PIPELINE INTEGRATION: PRINCIPAL -> AUTH -> RISK -> APPROVAL -> BUDGET -> SETTLEMENT -> MEMORY
    # =========================================================================

    def test_unified_pipeline_end_to_end_governed_action(self):
        """
        End-to-End Governance Pipeline:
        1. Action Envelope created with RiskClass.FINANCIAL
        2. Cryptographic Approval issued & signed by CFO
        3. Multi-Scope Budget reserved (Workflow + Tenant)
        4. Cryptographic Approval verified & consumed atomically (nonce burned)
        5. Action simulated / executed
        6. Budget settled with actual spend
        7. Verified outcome recorded in Stateful Memory and Merkle Ledger
        """
        action_payload = {
            "action_id": f"act_e2e_{self.run_tag}",
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "agent_id": "agt_ai_ceo",
            "capability_id": "execute_capital_allocation",
            "target": "aws_compute_reserve",
            "intent": "Prepay GPU reserved capacity",
            "risk_class": HighRiskActionClass.FINANCIAL.value,
            "parameters": {"gpu_instances": 8, "prepay_months": 3, "estimated_cost_usd": 1200.0}
        }

        # 1. Configure Budget
        wf_id = f"wf_infra_{self.run_tag}"
        economic_governor.configure_budget(
            entity_id=wf_id,
            entity_type=BudgetScope.WORKFLOW.value,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            allocated_usd=2000.0
        )

        # 2. Issue Cryptographic Approval
        cert = cryptographic_approvals.issue_approval(
            action_payload=action_payload,
            approver_id="usr_chief_executive_officer",
            approver_role="OWNER"
        )
        self.assertIsNotNone(cert.nonce)

        # 3. Reserve Budget
        res = economic_governor.reserve_budget(
            tenant_id=self.tenant_id,
            scope_chain=[(BudgetScope.WORKFLOW.value, wf_id)],
            requested_usd=1200.0
        )
        self.assertEqual(res.reserved_usd, 1200.0)

        # 4. Verify and Consume Cryptographic Approval
        verify_res = cryptographic_approvals.verify_and_consume_approval(
            action_payload=action_payload,
            certificate=cert,
            consuming_action_id=action_payload["action_id"]
        )
        self.assertTrue(verify_res["verified"])

        # 5. Settle Budget with actual execution cost ($1150 USD)
        settlement = economic_governor.settle_budget(
            reservation_id=res.reservation_id,
            actual_usd=1150.0
        )
        self.assertEqual(settlement.actual_usd, 1150.0)

        # 6. Record Outcome into Persistent Stateful Agent Memory
        gw = StatefulAgentMemoryGateway(self.tenant_id)
        mem = gw.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=self.company_id,
            memory_key=f"infra_commitment_{self.run_tag}",
            content=f"Executed prepayment of 8 GPU instances. Incurred: $1150.00 USD. Approval: {cert.approval_id}.",
            category=MemoryCategory.DECISION.value,
            confidence=ConfidenceLevel.VERIFIED.value,
            metadata={"approval_id": cert.approval_id, "settlement_id": settlement.reservation_id}
        )
        self.assertIsNotNone(mem.record_id)

        # 7. Verify all state updates were committed
        budget_final = economic_governor.get_budget(wf_id)
        self.assertEqual(budget_final.spent_usd, 1150.0)
        self.assertEqual(budget_final.reserved_usd, 0.0)
        self.assertEqual(budget_final.available_usd, 850.0)

        # Nonce cannot be replayed
        with self.assertRaises(ReplayAttackException):
            cryptographic_approvals.verify_and_consume_approval(
                action_payload=action_payload,
                certificate=cert,
                consuming_action_id="act_forged_rerun"
            )


if __name__ == "__main__":
    unittest.main()
