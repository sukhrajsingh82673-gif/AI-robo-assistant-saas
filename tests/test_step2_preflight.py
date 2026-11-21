"""
OpenCode Step 2A — Preflight and Inventory Acceptance Tests.
Verifies Step 1 foundation gate criteria, subsystem imports, and documentation completeness.
"""

import os
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestStep2Preflight:
    """Acceptance tests for OpenCode Sub-Step 2A."""

    def test_step1_subsystems_import_and_instantiate(self):
        """Confirm all Step 1 foundation subsystems are importable and available."""
        # 1. Capability truth probe & Port framework
        from core.ports.base import Port, PortStatus, ProviderResult
        from core.capability_probe import probe_all_capabilities
        caps = probe_all_capabilities()
        assert len(caps) >= 15
        assert PortStatus.OK.value == "OK"

        # 2. Governed Document store
        from core.documents.pipeline import DocumentPipeline
        doc_pipeline = DocumentPipeline()
        assert hasattr(doc_pipeline, "ingest")

        # 3. Folio evidence backbone
        from core.folios.manager import FolioManager
        folio_mgr = FolioManager()
        assert hasattr(folio_mgr, "create_folio")

        # 4. Double-entry ledger kernel
        from core.ledger.kernel import LedgerKernel
        ledger = LedgerKernel()
        assert hasattr(ledger, "post_journal_entry")

        # 5. Industry pack framework
        from core.industry_packs.loader import IndustryPackLoader
        loader = IndustryPackLoader()
        assert hasattr(loader, "install_pack")

        # 6. Always-on baseline (outbox & scheduler)
        from core.baseline.outbox import DurableOutbox
        from core.baseline.scheduler import DurableScheduler
        outbox = DurableOutbox()
        scheduler = DurableScheduler()
        assert hasattr(outbox, "enqueue")
        assert hasattr(scheduler, "register_job")

    def test_step2_inventory_document_exists_and_complete(self):
        """Verify docs/reports/STEP2_INVENTORY.md exists and covers all mandatory domains."""
        inv_path = REPO_ROOT / "docs" / "reports" / "STEP2_INVENTORY.md"
        assert inv_path.exists(), "STEP2_INVENTORY.md must be written"

        content = inv_path.read_text(encoding="utf-8")

        # Must copy G1-G9 definitions exactly
        for grade in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]:
            assert f'"{grade}":' in content or f"`{grade}`" in content or f"{grade}:" in content

        # Must cover domains
        required_domains = [
            "LLM Providers & Routing",
            "ActionGateway",
            "Authority Profiles (G1–G9)",
            "Approvals",
            "Budgets",
            "Kill Switch",
            "Missions",
            "Tasks",
            "SOP Versioning",
            "KRA/KPI Scoring",
            "CEO Brain",
            "Kaizen",
            "Agent Instances",
            "AI Employees",
            "Org & Roles",
            "Tool Registry & MCP",
            "Agent Specs",
            "Workforce Tables",
        ]
        for domain in required_domains:
            assert domain in content, f"Missing domain: {domain}"

        # Must record default model provider and throughput limits
        assert "embedded_free" in content
        assert "Throughput Limits" in content

        # Must record untyped action triggers
        assert "Untyped Action Triggers" in content or "untyped check" in content.lower()

    def test_step2_report_section_2a_exists(self):
        """Verify docs/reports/STEP2_REPORT.md contains Sub-Step 2A with Step 1 CI Run URL."""
        report_path = REPO_ROOT / "docs" / "reports" / "STEP2_REPORT.md"
        assert report_path.exists(), "STEP2_REPORT.md must be written"

        content = report_path.read_text(encoding="utf-8")
        assert "Sub-Step 2A — Preflight and Inventory" in content
        assert "44925486054" in content, "Must record authoritative Step 1 CI run ID"
        assert "step2-intelligence-execution" in content
