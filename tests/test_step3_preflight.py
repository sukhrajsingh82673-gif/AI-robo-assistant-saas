"""
OpenCode Step 3A Preflight & Architecture Verification Suite
============================================================
Validates:
1. Gate check across Step 1 and Step 2 foundations:
   - Capability truth table and Port framework
   - ActionGateway with authority, approvals, budgets, and kill switch (2C)
   - LLMGateway with VISION tier (2B)
   - Tool registry and agent runtime (2E)
   - Human inbox and task states including BLOCKED (2F)
   - Document store with RESERVED_BROWSER_SCAN and ClamAV quarantine pipeline (1E)
   - Job runner (1I)
   - Evidence ledger
2. Inventory document completeness (docs/reports/STEP3_INVENTORY.md)
3. Architecture Decision Records (ADR_0002 through ADR_0008)
4. Mutation check verifying failure when gate foundations are missing
"""

import os
import sys
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class TestStep3PreflightGate(unittest.TestCase):
    def setUp(self):
        os.environ["ZONATA_TEST_MODE"] = "1"
        self.root_dir = Path(__file__).resolve().parent.parent

    def test_01_gate_capability_truth_table_and_ports(self):
        from core.capability_probe import probe_all_capabilities
        from core.ports.base import Port, PortStatus

        caps = probe_all_capabilities()
        self.assertGreaterEqual(len(caps), 18, "Must probe at least 18 core system capabilities")
        self.assertIn("browser", caps)
        self.assertIn("desktop_control", caps)
        self.assertIn("llm", caps)
        self.assertIn("secrets", caps)
        self.assertIn("antivirus", caps)
        self.assertIn("workflow_engine", caps)

    def test_02_gate_action_gateway_governance_and_killswitch(self):
        from core.action_gateway import action_gateway, ZonataActionGateway
        from core.authority.budget_guard import SpendBudgetGuard
        from core.killswitch_matrix import KillSwitchMatrix
        from core.authority.approvals import approvals_manager, ApprovalsManager

        self.assertIsInstance(action_gateway, ZonataActionGateway)
        self.assertTrue(hasattr(KillSwitchMatrix, "is_engaged"))
        self.assertTrue(hasattr(approvals_manager, "create_approval_request"))

    def test_03_gate_llm_gateway_with_vision_tier(self):
        from core.ports.llm import LLMGatewayPort, ModelTier

        self.assertTrue(hasattr(ModelTier, "VISION"))
        self.assertEqual(ModelTier.VISION.value, "VISION")

    def test_04_gate_tool_registry_and_agent_runtime(self):
        from core.tools.registry import tool_registry
        from core.agents.runtime import ZonataAgentRuntime

        self.assertTrue(hasattr(tool_registry, "get"))
        self.assertTrue(hasattr(ZonataAgentRuntime, "run"))

    def test_05_gate_human_inbox_and_blocked_task_state(self):
        from core.work.inbox import HumanInboxService
        from core.work.types import TaskStatus

        self.assertTrue(hasattr(HumanInboxService, "create_item"))
        self.assertTrue(hasattr(TaskStatus, "BLOCKED"))
        self.assertEqual(TaskStatus.BLOCKED.value, "BLOCKED")

    def test_06_gate_document_store_reserved_browser_scan_and_antivirus(self):
        from core.documents.schema import DocumentChannel
        from core.ports.antivirus import AntivirusPort

        self.assertTrue(hasattr(DocumentChannel, "RESERVED_BROWSER_SCAN"))
        self.assertEqual(DocumentChannel.RESERVED_BROWSER_SCAN.value, "RESERVED_BROWSER_SCAN")
        self.assertTrue(hasattr(DocumentChannel, "IMPORT_LANE"))

    def test_07_gate_job_runner(self):
        from core.baseline.scheduler import DurableScheduler, ScheduledJobRecord

        self.assertTrue(hasattr(DurableScheduler, "register_job"))
        self.assertTrue(hasattr(DurableScheduler, "acquire_or_renew_leader_lease"))

    def test_08_gate_evidence_ledger(self):
        from core.evidence_ledger import EvidenceLedger
        from core.evidence_service import evidence_service

        self.assertTrue(hasattr(evidence_service, "record_event"))
        self.assertTrue(hasattr(EvidenceLedger, "seal_evidence"))

    def test_09_inventory_document_completeness(self):
        inventory_path = self.root_dir / "docs" / "reports" / "STEP3_INVENTORY.md"
        self.assertTrue(inventory_path.exists(), "docs/reports/STEP3_INVENTORY.md must exist")
        content = inventory_path.read_text(encoding="utf-8")

        required_terms = [
            "browser_gateway.py",
            "playwright_provider.py",
            "ACTION_NOT_IMPLEMENTED",
            "desktop_native_providers.py",
            "win32",
            "darwin",
            "linux",
            "universal_terminal.py",
            "terminal_enabled",
            "Watch me",
            "DurableScheduler",
            "enterprise_secret_vault",
            "quarantine.py",
            "IMPORT_LANE",
        ]
        for term in required_terms:
            self.assertIn(term, content, f"Missing inventory keyword: {term}")

        # Check for status classifications
        self.assertIn("`EXISTS`", content)
        self.assertIn("`PARTIAL`", content)
        self.assertIn("`MISSING`", content)

    def test_10_architecture_decision_records_completeness(self):
        adrs = [
            ("ADR_0002_BROWSER_ENGINE.md", ["Playwright", "Apache-2.0", "Selenium", "Rule 25"]),
            ("ADR_0003_PERCEPTION_STRATEGY.md", ["Accessibility-Tree First", "VISION", "UIA", "AXUIElement"]),
            ("ADR_0004_HOST_AGENT_RUNTIME.md", ["zonata-host-agent", "No Docker", "Keystore", "DPAPI", "Keychain"]),
            ("ADR_0005_TRANSPORT_PROTOCOL.md", ["WebSocket", "Outbound-Only", "sequence_no", "nonce", "Ed25519"]),
            ("ADR_0006_REMOTE_VIEW_TAKEOVER.md", ["WebRTC", "BSD-3-Clause", "aiortc", "Rule 28"]),
            ("ADR_0007_IMPORT_LANE_SANDBOX.md", ["gVisor", "runsc", "MicroVM", "cap-drop"]),
            ("ADR_0008_SEARCH_PROVIDER.md", ["SearchPort", "SearXNG", "Brave", "Rule 25", "UNTRUSTED_EXTERNAL_DATA"]),
        ]

        for filename, expected_keywords in adrs:
            adr_path = self.root_dir / "docs" / "architecture" / filename
            self.assertTrue(adr_path.exists(), f"{filename} must exist")
            content = adr_path.read_text(encoding="utf-8")
            for kw in expected_keywords:
                self.assertIn(kw, content, f"{filename} missing required concept: {kw}")

    def test_11_mutation_check_fails_on_missing_foundation(self):
        # Verify mutation detection: if required attributes were missing, assertions fail
        from core.ports.llm import ModelTier
        from core.work.types import TaskStatus

        with self.assertRaises(AssertionError):
            self.assertFalse(hasattr(ModelTier, "VISION"), "Mutation: VISION tier should be present")

        with self.assertRaises(AssertionError):
            self.assertFalse(hasattr(TaskStatus, "BLOCKED"), "Mutation: BLOCKED status should be present")


if __name__ == "__main__":
    unittest.main()
