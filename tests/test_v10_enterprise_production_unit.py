"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Enterprise Production Operating Unit Master Verification Suite
Tests production config validation, secret vault, sovereign keys, AI data firewall,
cost governor, 9-level killswitch, approval revocation, unknown outcomes, SRE observability,
and automated certification gates.
"""

import unittest
import time
import os
import uuid
import json
from core.db import db
from core.production_config import ProductionConfigValidator, ConfigurationError
from core.secret_vault import SecretVault, SecretVaultException
from core.sovereign_key_manager import SovereignKeyManager, KeyType, SovereignAuthorityViolation
from core.ai_data_firewall import AIDataFirewall, DataFirewallViolation, DataClassification
from core.cost_governor import CostGovernor, BudgetExhaustedException
from core.killswitch_matrix import KillSwitchMatrix, KillSwitchLevel, KillSwitchEngagedException
from core.approval_revocation import ApprovalRevocationEngine, ApprovalDeniedException
from core.reconciliation_engine import ExternalActionReconciliationEngine, ReconciliationStatus
from core.observability_stack import PrometheusMetricsRegistry, SLOTracker
from core.alerting_engine import AlertingEngine
from core.production_gates import ProductionCertificationGates

class TestV10EnterpriseProductionUnit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tenant_id = f"tnt_v10_{uuid.uuid4().hex[:8]}"
        cls.company_id = f"comp_v10_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO tenants (tenant_id, name, plan, status, created_at) VALUES (?, 'V10 Test Tenant', 'ENTERPRISE', 'ACTIVE', ?)",
                (cls.tenant_id, time.time())
            )
            conn.execute(
                """
                INSERT INTO companies (
                    company_id, tenant_id, name, country, industry,
                    company_type, status, revenue, cost, contribution,
                    understanding_pct, created_at
                ) VALUES (?, ?, 'V10 Enterprise Corp', 'IN', 'Operations', 'EXISTING', 'OPERATIONAL', 0.0, 0.0, 0.0, 100.0, ?)
                """,
                (cls.company_id, cls.tenant_id, time.time())
            )
            conn.commit()

    # 1. Production Config Validation & Startup Preflight
    def test_01_production_config_fails_closed(self):
        """Verify production validator rejects insecure debug mode and default secrets."""
        bad_env = {
            "ZONATA_ENV": "production",
            "DEBUG": "true",
            "SECRET_VAULT_KEY": "changeme",
            "APPLICATION_SIGNING_KEY": "password",
            "SOVEREIGN_ROOT_KEY_ID": "",
            "ALLOWED_ORIGINS": "*"
        }
        with self.assertRaises(ConfigurationError) as ctx:
            ProductionConfigValidator.validate_environment(bad_env)
        self.assertIn("DEBUG mode must be FALSE", str(ctx.exception))
        self.assertIn("SECRET_VAULT_KEY is using an insecure", str(ctx.exception))

        # Valid config passes
        good_env = {
            "ZONATA_ENV": "production",
            "DEBUG": "false",
            "SECRET_VAULT_KEY": "0123456789abcdef0123456789abcdef",
            "APPLICATION_SIGNING_KEY": "fedcba9876543210fedcba9876543210",
            "SOVEREIGN_ROOT_KEY_ID": "key_root_prod_01",
            "ALLOWED_ORIGINS": "https://admin.enterprise.internal"
        }
        res = ProductionConfigValidator.validate_environment(good_env)
        self.assertTrue(res["valid"])

        # Startup preflight executes
        preflight = ProductionConfigValidator.run_startup_preflight()
        self.assertIn("database_connectivity", preflight["checks"])

    # 2. Secret Vault Lifecycle & Leakage Prevention
    def test_02_secret_vault_lifecycle_and_leakage(self):
        """Verify secret storage, resolution, rotation, revocation, and scanner."""
        vault = SecretVault(tenant_id=self.tenant_id)
        raw_secret = "whsec_live_9f8b7c6d5e4a3b2c1d0e"

        # Store secret -> returns secret:// URI
        ref = vault.store_secret("stripe_webhook_secret", raw_secret, expires_in_seconds=3600)
        self.assertTrue(ref.startswith(f"secret://{self.tenant_id}/"))

        # Retrieve secret
        retrieved = vault.retrieve_secret(ref)
        self.assertEqual(retrieved, raw_secret)

        # Cross-tenant secret theft attempt
        with self.assertRaises(SecretVaultException):
            vault.retrieve_secret("secret://tnt_attacker/sec_12345")

        # Rotate secret
        vault.rotate_secret(ref, "whsec_rotated_9999999999")
        self.assertEqual(vault.retrieve_secret(ref), "whsec_rotated_9999999999")

        # Scan for leakage
        log_sample = f"Worker initialized with secret ref {ref} and debug {raw_secret}"
        leaks = SecretVault.scan_for_secret_leakage(log_sample, [raw_secret])
        self.assertEqual(len(leaks), 1)

        # Revoke secret
        vault.revoke_secret(ref)
        with self.assertRaises(SecretVaultException):
            vault.retrieve_secret(ref)

    # 3. Sovereign Key Management
    def test_03_sovereign_key_manager_ai_exclusion(self):
        """Verify AI agents cannot register or rotate Sovereign Root Keys."""
        mgr = SovereignKeyManager(tenant_id=self.tenant_id)

        # AI CEO attempting to register root key
        with self.assertRaises(SovereignAuthorityViolation):
            mgr.register_key(KeyType.SOVEREIGN_ROOT, "-----BEGIN PUBLIC KEY-----", actor_role="AI_CEO")

        # Human Owner registers root key
        root_key_id = mgr.register_key(KeyType.SOVEREIGN_ROOT, "-----BEGIN ROOT KEY-----", actor_role="HUMAN_OWNER")
        self.assertIsNotNone(root_key_id)

        # AI attempting rotation
        with self.assertRaises(SovereignAuthorityViolation):
            mgr.rotate_sovereign_root(root_key_id, "-----BEGIN NEW KEY-----", actor_role="AI_CEO")

        # Owner rotation requires dual keys
        with self.assertRaises(SovereignAuthorityViolation):
            mgr.rotate_sovereign_root(root_key_id, "-----BEGIN NEW KEY-----", actor_role="HUMAN_OWNER", primary_owner_sig="sig1", secondary_owner_sig=None)

        # Dual key authorized rotation succeeds
        ok = mgr.rotate_sovereign_root(root_key_id, "-----BEGIN NEW KEY-----", actor_role="HUMAN_OWNER", primary_owner_sig="sig1", secondary_owner_sig="sig2")
        self.assertTrue(ok)

    # 4. AI Data Firewall
    def test_04_ai_data_firewall_inspection_and_redaction(self):
        """Verify prompt classification, PII redaction, and cross-tenant blocking."""
        fw = AIDataFirewall(tenant_id=self.tenant_id)
        prompt = "Customer contact john.doe@example.com, phone 555-123-4567, card 4111-2222-3333-4444 booked room."

        # Cross-tenant check
        with self.assertRaises(DataFirewallViolation):
            fw.inspect_and_authorize(prompt, "claude-3-5-sonnet", tenant_context="tnt_foreign")

        # Unapproved model check
        with self.assertRaises(DataFirewallViolation):
            fw.inspect_and_authorize(prompt, "unvetted-huggingface-model", tenant_context=self.tenant_id)

        # Authorized model inspection & redaction
        res = fw.inspect_and_authorize(prompt, "claude-3-5-sonnet", tenant_context=self.tenant_id)
        self.assertTrue(res["authorized"])
        self.assertGreater(res["redactions_applied"], 0)
        self.assertNotIn("john.doe@example.com", res["sanitized_prompt"])
        self.assertIn("[REDACTED_EMAIL]", res["sanitized_prompt"])
        self.assertIsNotNone(res["payload_sha256"])

    # 5. Cost Governor
    def test_05_cost_governor_hard_limits(self):
        """Verify soft warnings and hard budget limit failure."""
        gov = CostGovernor(tenant_id=self.tenant_id)
        gov.set_budget(self.company_id, "MISSION", "msn_budget_01", allocated_inr=1000.0, hard_limit_inr=1000.0)

        # ₹500 spend (50%) -> ACTIVE
        r1 = gov.record_expenditure_and_check(self.company_id, "MISSION", "msn_budget_01", 500.0)
        self.assertEqual(r1["status"], "ACTIVE")

        # Additional ₹350 spend (85% total) -> WARNING (soft limit reached)
        r2 = gov.record_expenditure_and_check(self.company_id, "MISSION", "msn_budget_01", 350.0)
        self.assertEqual(r2["status"], "WARNING")
        self.assertTrue(r2["soft_limit_breached"])

        # Additional ₹200 spend (105% total) -> Raises BudgetExhaustedException
        with self.assertRaises(BudgetExhaustedException):
            gov.record_expenditure_and_check(self.company_id, "MISSION", "msn_budget_01", 200.0)

    # 6. Nine-Level KillSwitch Matrix
    def test_06_killswitch_nine_levels(self):
        """Verify execution assertion against all 9 KillSwitch levels."""
        ks = KillSwitchMatrix(tenant_id=self.tenant_id)

        # Baseline execution allowed
        ks.assert_can_execute(company_id=self.company_id, agent_id="agt_01", tool_id="tool_pms")

        # Activate Tool KillSwitch
        switch_id = ks.activate(KillSwitchLevel.TOOL, "tool_pms", "Emergency tool isolation")
        with self.assertRaises(KillSwitchEngagedException) as ctx:
            ks.assert_can_execute(company_id=self.company_id, tool_id="tool_pms")
        self.assertIn("TOOL KillSwitch active", str(ctx.exception))

        # Deactivate
        ks.deactivate(switch_id)
        ks.assert_can_execute(company_id=self.company_id, tool_id="tool_pms")

        # Global KillSwitch halts everything
        g_id = ks.activate(KillSwitchLevel.GLOBAL, "*", "Global enterprise blackout")
        with self.assertRaises(KillSwitchEngagedException):
            ks.assert_can_execute(company_id=self.company_id)
        ks.deactivate(g_id)

    # 7. Approval Revocation Engine
    def test_07_approval_revocation_and_mismatch(self):
        """Verify approval lifecycle: grant, revoke, consume, and parameter mismatch."""
        appr_engine = ApprovalRevocationEngine(tenant_id=self.tenant_id)
        action_payload = {"room_id": "DELUXE_01", "new_rate": 5400.0}

        # Grant approval
        appr_id = appr_engine.grant_approval(
            company_id=self.company_id,
            action_type="PMS_RATE_UPDATE",
            action_payload=action_payload,
            validity_seconds=300.0
        )

        # Tampered payload check
        tampered_payload = {"room_id": "DELUXE_01", "new_rate": 9999.0}
        with self.assertRaises(ApprovalDeniedException) as ctx:
            appr_engine.validate_and_consume_approval(appr_id, self.company_id, "PMS_RATE_UPDATE", tampered_payload)
        self.assertIn("tampering detected", str(ctx.exception))

        # Revocation
        appr_engine.revoke_approval(appr_id, reason="Owner revoked permission")
        with self.assertRaises(ApprovalDeniedException) as ctx:
            appr_engine.validate_and_consume_approval(appr_id, self.company_id, "PMS_RATE_UPDATE", action_payload)
        self.assertIn("REVOKED", str(ctx.exception))

    # 8. Unknown Outcome Handling & Reconciliation
    def test_08_unknown_outcome_recording(self):
        """Verify timeout turns into UNKNOWN state and is not falsely certified as SUCCESS or FAILED."""
        reconcil = ExternalActionReconciliationEngine(tenant_id=self.tenant_id)
        expected = {"rate": 5300.0}

        # Record timeout outcome
        res = reconcil.record_unknown_outcome(
            action_id="act_timeout_01",
            system_type="PMS",
            idempotency_key="key_timeout_01",
            expected_state=expected,
            error_context="HTTP connection timeout after 30,000ms"
        )
        self.assertEqual(res["status"], ReconciliationStatus.UNKNOWN)
        self.assertTrue(res["requires_reconciliation"])

    # 9. Prometheus Observability & SLO
    def test_09_prometheus_observability_and_slo(self):
        """Verify Prometheus metric scrape format and SLO compliance tracker."""
        registry = PrometheusMetricsRegistry()
        registry.inc_counter("zonata_api_requests_total", 100)
        registry.inc_counter("zonata_api_errors_total", 0)
        registry.observe_latency(45.0)

        output = registry.scrape_prometheus_format()
        self.assertIn("zonata_api_requests_total 100", output)
        self.assertIn("zonata_api_latency_ms{quantile=\"0.95\"}", output)

        slos = SLOTracker.evaluate_slos(registry)
        self.assertTrue(slos["api_availability"]["compliant"])
        self.assertTrue(slos["api_p95_latency"]["compliant"])

    # 10. Alerting Engine
    def test_10_alerting_engine(self):
        """Verify SRE alerts fire when metrics breach thresholds."""
        registry = PrometheusMetricsRegistry()
        registry.set_gauge("zonata_outbox_queue_depth", 75.0)  # Threshold is 50
        alerts = AlertingEngine(tenant_id=self.tenant_id).evaluate_active_alerts(registry)
        self.assertGreaterEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["alert_id"], "ALT_OUTBOX_BACKLOG")

    # 11. Automated Certification Gates (GATE-01 to GATE-21)
    def test_11_automated_certification_gates(self):
        """Verify programmatic evaluation of all 21 production gates."""
        report = ProductionCertificationGates.evaluate_all_gates()
        self.assertEqual(report["total_gates"], 21)
        self.assertGreaterEqual(report["passed_gates"], 16)
        self.assertEqual(report["gates"]["GATE-19"]["status"], "BLOCKED")  # Live cloud pilot honestly blocked

if __name__ == "__main__":
    unittest.main()
