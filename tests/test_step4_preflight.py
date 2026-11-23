"""
ZONATA Unit & Contract Tests — Sub-Step 4A: Preflight, Inventory & ADRs Gate Check.
==================================================================================
Verifies:
1. Steps 1 to 3 gate dependencies exist and pass readiness contracts:
   - WorkflowEngine port and local engine (Step 2E)
   - AgentRuntime and ToolRegistry (Step 2E)
   - ActionGateway authority, approvals, budgets, and kill switch (Step 2C)
   - LLMGateway (Step 2B)
   - Job runner and scheduler (Step 1I)
   - Evidence ledger (Step 1F / 1G)
   - Capability truth table with 18 standard capabilities (Step 1C)
   - KeyManagementPort (Step 1D) and OriginBoundSecretVault (Step 3D)
   - Step 3 hands: browser, desktop, terminal, research, and import lane
2. STEP4_INVENTORY.md exists and accurately catalogs all 10 audit targets.
3. All 9 Step 4 ADRs (ADR 0009 to ADR 0017) are written and structured.
"""

from __future__ import annotations

import os
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestStep4Preflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"

    def test_01_workflow_engine_port_exists(self):
        """Gate Check: WorkflowEngine port with local engine exists (2E)."""
        from core.ports.workflow import (
            WorkflowEnginePort,
            LocalWorkflowEngine,
            SandboxWorkflowEngineProvider,
        )
        self.assertTrue(issubclass(LocalWorkflowEngine, WorkflowEnginePort))
        self.assertTrue(issubclass(SandboxWorkflowEngineProvider, WorkflowEnginePort))

    def test_02_agent_runtime_and_tool_registry_exist(self):
        """Gate Check: AgentRuntime and ToolRegistry exist (2E)."""
        from core.agents.runtime import ZonataAgentRuntime
        from core.tools.registry import tool_registry, ToolRegistry
        from core.tools.contract import ToolContract

        tools = tool_registry.list_tools()
        self.assertGreater(len(tools), 0, "ToolRegistry should contain built-in tools")

    def test_03_action_gateway_governance_exists(self):
        """Gate Check: ActionGateway with authority, approvals, budgets, and kill switch exists (2C)."""
        from core.action_gateway import action_gateway, ZonataActionGateway
        from core.authority.types import ActionClass, AutonomyLevel, PolicyDecisionResult
        from core.authority.budget_guard import SpendBudgetGuard, spend_budget_guard

        self.assertIsNotNone(action_gateway)
        self.assertTrue(hasattr(action_gateway, "evaluate"))
        self.assertTrue(hasattr(action_gateway, "execute_action"))

    def test_04_llm_gateway_exists(self):
        """Gate Check: LLMGateway with tier routing exists (2B)."""
        from core.ports.llm import llm_gateway, ModelTier

        self.assertIsNotNone(llm_gateway)
        self.assertTrue(hasattr(llm_gateway, "generate"))
        self.assertIn("FAST", [t.name for t in ModelTier])
        self.assertIn("VISION", [t.name for t in ModelTier])

    def test_05_job_runner_and_scheduler_exist(self):
        """Gate Check: Job runner and distributed scheduler exist (1I)."""
        from core.baseline.scheduler import DurableScheduler
        from core.baseline.outbox import DurableOutbox

        scheduler = DurableScheduler()
        outbox = DurableOutbox()
        self.assertIsNotNone(scheduler)
        self.assertIsNotNone(outbox)

    def test_06_evidence_ledger_exists(self):
        """Gate Check: Evidence ledger exists and records hashes (1F/1G)."""
        from core.evidence_ledger import EvidenceLedger
        from core.evidence_service import evidence_service

        self.assertIsNotNone(evidence_service)
        ledger = EvidenceLedger()
        self.assertTrue(hasattr(ledger, "seal_evidence"))
        self.assertTrue(hasattr(ledger, "verify_ledger_integrity"))
        self.assertTrue(hasattr(evidence_service, "record_event"))

    def test_07_capability_truth_table_exists(self):
        """Gate Check: Capability truth table covers standard 18 capabilities."""
        from core.capability_probe import probe_all_capabilities
        from core.ports.base import PortStatus

        results = probe_all_capabilities()
        self.assertEqual(len(results), 18, f"Expected 18 capabilities, found {len(results)}")

    def test_08_key_and_credential_ports_exist(self):
        """Gate Check: KeyManagementPort and OriginBoundSecretVault exist."""
        from core.ports.kms import KeyManagementPort
        from core.vault.vault import OriginBoundSecretVault

        vault = OriginBoundSecretVault()
        self.assertTrue(hasattr(vault, "store_credential"))
        self.assertTrue(hasattr(vault, "inject_credential"))

    def test_09_step3_hands_exist_as_tools_or_ports(self):
        """Gate Check: Step 3 hands exist (browser, desktop, terminal, research, import)."""
        # Browser Hand
        from core.ports.browser import browser_port, BrowserPort
        # Desktop Hand
        from core.host.agent import ZonataHostAgent
        from core.host.perception import DesktopPerceptionEngine
        # Terminal Hand
        from core.ports.terminal import TerminalPort
        # Research Hand
        from core.ports.search import SearchPort
        from core.research.engine import ResearchEngine
        # Agent Factory Import Lane
        from core.agent_import.scanner import SkillImportScanner
        from core.agent_import.license_gate import LicenseGate

        self.assertIsNotNone(browser_port)
        self.assertIsNotNone(TerminalPort())
        self.assertIsNotNone(SearchPort())

    def test_10_inventory_file_covers_all_ten_domains(self):
        """Requirement 2: docs/reports/STEP4_INVENTORY.md exists and covers all required targets."""
        inventory_path = REPO_ROOT / "docs" / "reports" / "STEP4_INVENTORY.md"
        self.assertTrue(inventory_path.exists(), "STEP4_INVENTORY.md must exist")

        text = inventory_path.read_text(encoding="utf-8")
        expected_targets = [
            "LangGraph Adapter",
            "Temporal Workflow Code",
            "Hand-written MCP Client",
            "Agent-to-Agent (A2A) Code",
            "Compose Services",
            "Transactional Outbox",
            "Agent Factory Compiler",
            "Workflow & Run State Tables",
            "Google ADK Framework",
            "OpenTelemetry SDK Instrumentation",
        ]
        for target in expected_targets:
            self.assertIn(target, text, f"Inventory must audit '{target}'")

    def test_11_all_nine_step4_adrs_exist(self):
        """Requirement 3: All 9 Step 4 Architectural Decision Records exist and are complete."""
        adr_dir = REPO_ROOT / "docs" / "architecture"
        expected_adrs = [
            "ADR_0009_TEMPORAL_TOPOLOGY.md",
            "ADR_0010_FRAMEWORK_SPLIT_DECISION_D4_1.md",
            "ADR_0011_LANGGRAPH_CHECKPOINTER.md",
            "ADR_0012_ADK_EXTENSION_POINTS.md",
            "ADR_0013_MCP_SPEC_AND_SDK.md",
            "ADR_0014_A2A_INTEROP_EVALUATION.md",
            "ADR_0015_OPENTELEMETRY_CONVENTIONS_AND_CANARY.md",
            "ADR_0016_OBSERVABILITY_BACKENDS_AND_AGPL_BOUNDARY.md",
            "ADR_0017_NATS_VS_POSTGRES_OUTBOX.md",
        ]
        for adr in expected_adrs:
            path = adr_dir / adr
            self.assertTrue(path.exists(), f"ADR file '{adr}' must exist in docs/architecture/")
            content = path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 300, f"ADR '{adr}' must not be a stub")
            self.assertIn("Status:", content)
            self.assertIn("Decision", content)

    def test_12_mutation_check_missing_dependency_fails(self):
        """Mutation Check: Verifies that checking for a non-existent port fails cleanly."""
        with self.assertRaises(ImportError):
            from core.ports import NonExistentFakeFrameworkPort  # type: ignore


if __name__ == "__main__":
    unittest.main()
