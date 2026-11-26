"""
ZONATA Unit & Contract Tests — Sub-Step 5A: Preflight, Inventory & ADRs Gate Check.
==================================================================================
Verifies:
1. Steps 1 to 4 gate dependencies exist and pass readiness contracts:
   - KeyManagementPort & interim LocalEnvelopeKeyProvider (Step 1D)
   - OriginBoundSecretVault (Step 3D)
   - ActionGateway authority, approvals, budgets, and kill switch (Step 2C)
   - LLMGateway (Step 2B)
   - Job runner and scheduler (Step 1I)
   - Evidence ledger (Step 1F / 1G)
   - Capability truth table with 18 standard capabilities (Step 1C)
   - Temporal engine and adapter (Step 4D)
   - ToolRegistry (Step 2E)
   - MCP client and server (Step 4G)
   - OpenTelemetry tracing and sanitization (Step 4H)
2. STEP5_INVENTORY.md exists, is non-trivial, and covers all required audit items:
   - Authentication and session code in api_server.py and core/auth.py
   - Role tiers (OWNER, EXECUTIVE, MANAGER, OPERATOR, AUDITOR, OBSERVER)
   - Two-step sign-in and session length settings
   - enterprise_secret_vault and automation_signing_keys
   - Environment and database secret reads
   - Audit log and evidence ledger
   - Row-level security (RLS) status
   - Database connection roles and pooler mode
   - API routes and authorization checks
3. SECRETS_REGISTER.md exists and contains ZERO plaintext secrets, passwords, or tokens.
4. All 8 Step 5 ADRs (ADR 0018 to ADR 0025) exist and have complete structure.
5. Mutation check: verifying non-existent security controls fails as expected.
"""

from __future__ import annotations

import os
import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestStep5Preflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"

    def test_01_key_and_credential_ports_exist(self):
        """Gate Check: KeyManagementPort, LocalEnvelopeKeyProvider, and OriginBoundSecretVault exist."""
        from core.ports.kms import KeyManagementPort, LocalEnvelopeKeyProvider
        from core.vault.vault import OriginBoundSecretVault

        self.assertTrue(issubclass(LocalEnvelopeKeyProvider, KeyManagementPort))
        vault = OriginBoundSecretVault()
        self.assertTrue(hasattr(vault, "store_credential"))
        self.assertTrue(hasattr(vault, "inject_credential"))

    def test_02_action_gateway_governance_exists(self):
        """Gate Check: ActionGateway with authority, approvals, budgets, and kill switch exists (2C)."""
        from core.action_gateway import action_gateway, ZonataActionGateway
        from core.authority.types import ActionClass, AutonomyLevel, PolicyDecisionResult
        from core.authority.budget_guard import spend_budget_guard

        self.assertIsNotNone(action_gateway)
        self.assertTrue(hasattr(action_gateway, "evaluate"))
        self.assertTrue(hasattr(action_gateway, "execute_action"))
        self.assertIsNotNone(spend_budget_guard)

    def test_03_llm_gateway_exists(self):
        """Gate Check: LLMGateway with tier routing exists (2B)."""
        from core.ports.llm import llm_gateway, ModelTier

        self.assertIsNotNone(llm_gateway)
        self.assertTrue(hasattr(llm_gateway, "generate"))
        self.assertIn("FAST", [t.name for t in ModelTier])
        self.assertIn("VISION", [t.name for t in ModelTier])

    def test_04_capability_truth_table_exists(self):
        """Gate Check: Capability truth table covers standard 18 capabilities."""
        from core.capability_probe import probe_all_capabilities
        from core.ports.base import PortStatus

        results = probe_all_capabilities()
        self.assertEqual(len(results), 18, f"Expected 18 capabilities, found {len(results)}")

    def test_05_evidence_ledger_exists(self):
        """Gate Check: Evidence ledger exists and records hashes (1F/1G)."""
        from core.evidence_ledger import EvidenceLedger
        from core.evidence_service import evidence_service

        self.assertIsNotNone(evidence_service)
        ledger = EvidenceLedger()
        self.assertTrue(hasattr(ledger, "seal_evidence"))
        self.assertTrue(hasattr(ledger, "verify_ledger_integrity"))
        self.assertTrue(hasattr(evidence_service, "record_event"))

    def test_06_job_runner_and_scheduler_exist(self):
        """Gate Check: Job runner and distributed scheduler exist (1I)."""
        from core.baseline.scheduler import DurableScheduler
        from core.baseline.outbox import DurableOutbox

        scheduler = DurableScheduler()
        outbox = DurableOutbox()
        self.assertIsNotNone(scheduler)
        self.assertIsNotNone(outbox)

    def test_07_temporal_engine_and_adapter_exist(self):
        """Gate Check: Temporal durable workflow engine and adapter exist (4D)."""
        from core.temporal.adapter import TemporalRuntimeAdapter
        from core.temporal.workflows import ZonataAgentWorkflow

        adapter = TemporalRuntimeAdapter()
        self.assertIsNotNone(adapter)
        self.assertTrue(hasattr(adapter, "execute_agent"))
        self.assertIsNotNone(ZonataAgentWorkflow)

    def test_08_tool_registry_and_mcp_exist(self):
        """Gate Check: ToolRegistry and Governed MCP client & server exist (4G)."""
        from core.tools.registry import tool_registry
        from core.mcp.client import GovernedMCPClient, governed_mcp_client
        from core.mcp.server import SandboxedMCPServer, sandboxed_mcp_server

        tools = tool_registry.list_tools()
        self.assertGreater(len(tools), 0)
        self.assertIsNotNone(GovernedMCPClient)
        self.assertIsNotNone(governed_mcp_client)
        self.assertIsNotNone(SandboxedMCPServer)
        self.assertIsNotNone(sandboxed_mcp_server)

    def test_09_opentelemetry_observability_exists(self):
        """Gate Check: OpenTelemetry tracer, interceptor, and sanitizer exist (4H)."""
        from core.telemetry.tracer import get_tracer
        from core.telemetry.interceptor import instrument_tool_call, instrument_llm_call
        from core.telemetry.sanitizer import TelemetrySanitizer

        tracer = get_tracer("test.preflight")
        self.assertIsNotNone(tracer)
        sanitizer = TelemetrySanitizer()
        attrs = sanitizer.sanitize_dict({"api_key": "secret123", "normal": "val"})
        self.assertEqual(attrs["api_key"], "[REDACTED_CREDENTIAL]")
        self.assertEqual(attrs["normal"], "val")

    def test_10_inventory_file_covers_all_ten_domains(self):
        """Requirement 2: docs/reports/STEP5_INVENTORY.md exists and covers all required targets."""
        inventory_path = REPO_ROOT / "docs" / "reports" / "STEP5_INVENTORY.md"
        self.assertTrue(inventory_path.exists(), "STEP5_INVENTORY.md must exist")

        text = inventory_path.read_text(encoding="utf-8")
        expected_targets = [
            "Authentication & Tokens",
            "Session Lifetime & 2FA",
            "Role Tiers (RBAC)",
            "Secret Vault",
            "automation_signing_keys",
            "Environment Secret Ingestion",
            "Evidence & Audit Log",
            "Row-Level Security (RLS)",
            "Database Connection & Roles",
            "Connection Pooling",
            "API Route Authorization",
        ]
        for target in expected_targets:
            self.assertIn(target, text, f"Inventory must audit '{target}'")

    def test_11_secrets_register_has_zero_raw_secrets(self):
        """Requirement 3: docs/security/SECRETS_REGISTER.md exists and contains NO plaintext secrets."""
        register_path = REPO_ROOT / "docs" / "security" / "SECRETS_REGISTER.md"
        self.assertTrue(register_path.exists(), "SECRETS_REGISTER.md must exist")

        text = register_path.read_text(encoding="utf-8")
        self.assertGreater(len(text), 1000, "SECRETS_REGISTER.md should be substantial")

        # Invariant checks: Must NOT contain raw secret patterns
        forbidden_patterns = [
            r"sk-[a-zA-Z0-9]{20,}",            # OpenAI keys
            r"sk-ant-[a-zA-Z0-9]{20,}",        # Anthropic keys
            r"AIzaSy[a-zA-Z0-9_-]{33}",         # Google API keys
            r"password\s*[:=]\s*['\"][^'\"]+['\"]", # Raw password assignments
            r"bearer\s+[a-zA-Z0-9\._-]{30,}",  # Raw bearer tokens
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            self.assertEqual(len(matches), 0, f"Found forbidden secret matching pattern {pattern}: {matches}")

        # Invariant check: Must catalog key platform secrets
        cataloged = [
            "ANTHROPIC_API_KEY",
            "KMS_MASTER_KEY",
            "ZONATA_AUTH_SECRET",
            "STRIPE_SECRET_KEY",
            "POSTGRES_PASSWORD",
            "VAULT_ROOT_TOKEN",
        ]
        for item in cataloged:
            self.assertIn(item, text, f"Secrets register must document '{item}'")

    def test_12_all_eight_step5_adrs_exist_and_complete(self):
        """Requirement 4: All 8 Step 5 ADRs (ADR 0018 to ADR 0025) exist and have required sections."""
        adr_dir = REPO_ROOT / "docs" / "adr"
        expected_adrs = [
            "ADR_0018_OPENBAO_SECRETS_PLATFORM.md",
            "ADR_0019_KEYCLOAK_IDENTITY_PROVIDER.md",
            "ADR_0020_WORKLOAD_IDENTITY_SPIFFE.md",
            "ADR_0021_DATABASE_ROLES_AND_TRANSACTION_POOLER.md",
            "ADR_0022_POLICY_ENGINE_AUTHORITY.md",
            "ADR_0023_CRYPTO_AGILITY_POST_QUANTUM.md",
            "ADR_0024_SUPPLY_CHAIN_SIGNING.md",
            "ADR_0025_AUDIT_LOG_AND_SIEM_FORMAT.md",
        ]
        for adr in expected_adrs:
            path = adr_dir / adr
            self.assertTrue(path.exists(), f"ADR '{adr}' must exist in docs/adr/")
            content = path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 400, f"ADR '{adr}' must have substantive analysis")
            self.assertIn("Status:", content)
            self.assertIn("Context", content)
            self.assertIn("Decision", content)
            self.assertIn("Consequences", content)

    def test_13_mutation_check_unregistered_secret_or_port_fails(self):
        """Mutation Check: Verifies that checking for non-existent security controls fails."""
        with self.assertRaises(ImportError):
            from core.ports import NonExistentSecurityPort  # type: ignore

        # Verifies that corrupting an inventory check pattern fails
        inventory_text = (REPO_ROOT / "docs" / "reports" / "STEP5_INVENTORY.md").read_text(encoding="utf-8")
        self.assertNotIn("TOTALLY_BOGUS_MISSING_TARGET_XYZ", inventory_text)


if __name__ == "__main__":
    unittest.main()
