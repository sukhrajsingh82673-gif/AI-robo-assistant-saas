"""
ZONATA Universal AI Co-worker Fabric — Capability Registry
Implements the machine-readable capability registry mapping capabilities to
categories, risk levels, authorization requirements, and supported providers.
"""

from typing import Dict, List, Optional, Any
from .contracts import (
    CapabilityDefinition, CapabilityCategory, RiskLevel, CostClass, LatencyClass
)

class CapabilityRegistry:
    """
    Central authoritative catalog of all capabilities supported in ZONATA Co-worker Fabric.
    The AI CEO requests a capability; ZONATA determines the provider.
    """

    def __init__(self):
        self._registry: Dict[str, CapabilityDefinition] = {}
        self._load_standard_capabilities()

    def _load_standard_capabilities(self):
        # 1. Desktop Capabilities
        self.register(CapabilityDefinition(
            capability_id="desktop.workflow",
            name="Execute Repeatable Desktop Workflow",
            description="Compiles and executes demonstrated desktop workflows across business applications",
            category=CapabilityCategory.DESKTOP,
            providers=["provider_openadapt", "provider_robocorp", "provider_ui_tars"],
            preferred_provider="provider_openadapt",
            fallback_providers=["provider_linux_desktop", "provider_windows_desktop", "provider_ui_tars"],
            risk_level=RiskLevel.MEDIUM,
            requires_authorization=True,
            requires_human_approval=False,
            requires_verification=True,
            supports_rollback=True,
            supports_dry_run=True,
            cost_class=CostClass.LOW,
            latency_class=LatencyClass.FAST
        ))

        self.register(CapabilityDefinition(
            capability_id="desktop.accessibility_tree",
            name="Inspect Native Accessibility Tree",
            description="Traverses OS accessibility/UI automation tree without computer vision",
            category=CapabilityCategory.DESKTOP,
            providers=["provider_linux_desktop", "provider_windows_desktop", "provider_macos_desktop", "provider_computer_use_mcp"],
            preferred_provider="provider_linux_desktop",
            fallback_providers=["provider_computer_use_mcp", "provider_ui_tars"],
            risk_level=RiskLevel.LOW,
            requires_authorization=False,
            requires_human_approval=False,
            requires_verification=False,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.SUB_SECOND
        ))

        self.register(CapabilityDefinition(
            capability_id="desktop.click_element",
            name="Native UI Element Click",
            description="Invokes native UI automation pattern or accessibility click",
            category=CapabilityCategory.DESKTOP,
            providers=["provider_linux_desktop", "provider_windows_desktop", "provider_macos_desktop", "provider_computer_use_mcp", "provider_ui_tars"],
            preferred_provider="provider_linux_desktop",
            fallback_providers=["provider_computer_use_mcp", "provider_ui_tars"],
            risk_level=RiskLevel.LOW,
            requires_authorization=True,
            requires_verification=True,
            supports_rollback=False,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.FAST
        ))

        # 2. Browser Capabilities
        self.register(CapabilityDefinition(
            capability_id="browser.navigate",
            name="Navigate Browser URL",
            description="Navigates browser to target web page and inspects DOM readiness",
            category=CapabilityCategory.BROWSER,
            providers=["provider_playwright", "provider_computer_use_mcp", "provider_ui_tars"],
            preferred_provider="provider_playwright",
            fallback_providers=["provider_computer_use_mcp", "provider_ui_tars"],
            risk_level=RiskLevel.LOW,
            requires_authorization=True,
            requires_verification=True,
            supports_rollback=False,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.FAST
        ))

        self.register(CapabilityDefinition(
            capability_id="browser.extract",
            name="Extract Structured Web Data",
            description="Extracts tabular or text data from web pages using DOM selectors",
            category=CapabilityCategory.BROWSER,
            providers=["provider_playwright", "provider_ui_tars"],
            preferred_provider="provider_playwright",
            fallback_providers=["provider_ui_tars"],
            risk_level=RiskLevel.LOW,
            requires_authorization=False,
            requires_verification=True,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.FAST
        ))

        # 3. API Capabilities (API-First execution)
        self.register(CapabilityDefinition(
            capability_id="api.crm_update",
            name="Update CRM Record",
            description="Direct structured REST/GraphQL update of customer and booking data",
            category=CapabilityCategory.API,
            providers=["provider_api_mcp", "provider_playwright", "provider_ui_tars"],
            preferred_provider="provider_api_mcp",
            fallback_providers=["provider_playwright", "provider_openadapt", "provider_ui_tars"],
            risk_level=RiskLevel.MEDIUM,
            requires_authorization=True,
            requires_human_approval=False,
            requires_verification=True,
            supports_rollback=True,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.SUB_SECOND
        ))

        self.register(CapabilityDefinition(
            capability_id="api.crm_read",
            name="Read CRM Record",
            description="Fetches customer or reservation profile via direct structured API",
            category=CapabilityCategory.API,
            providers=["provider_api_mcp", "provider_playwright"],
            preferred_provider="provider_api_mcp",
            fallback_providers=["provider_playwright"],
            risk_level=RiskLevel.LOW,
            requires_authorization=False,
            requires_verification=False,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.SUB_SECOND
        ))

        self.register(CapabilityDefinition(
            capability_id="api.email_send",
            name="Send Business Email",
            description="Dispatches email through mail gateway; subject to policy approval",
            category=CapabilityCategory.API,
            providers=["provider_api_mcp", "provider_playwright"],
            preferred_provider="provider_api_mcp",
            fallback_providers=["provider_playwright"],
            risk_level=RiskLevel.MEDIUM,
            requires_authorization=True,
            requires_human_approval=True,  # Policy-gated
            requires_verification=True,
            supports_rollback=False,
            cost_class=CostClass.LOW,
            latency_class=LatencyClass.FAST
        ))

        # 4. RPA Capabilities
        self.register(CapabilityDefinition(
            capability_id="rpa.excel_update",
            name="Update Spreadsheet / Workbook",
            description="Modifies cells, sheets, and formulas in local Excel or CSV spreadsheets",
            category=CapabilityCategory.RPA,
            providers=["provider_robocorp", "provider_openrpa", "provider_openadapt"],
            preferred_provider="provider_robocorp",
            fallback_providers=["provider_openrpa", "provider_openadapt"],
            risk_level=RiskLevel.LOW,
            requires_authorization=True,
            requires_verification=True,
            supports_rollback=True,
            cost_class=CostClass.FREE,
            latency_class=LatencyClass.FAST
        ))

        # 5. Visual Computer-Use Capabilities
        self.register(CapabilityDefinition(
            capability_id="visual.screen_understanding",
            name="Visual Screen Understanding",
            description="Analyzes screen coordinates and visual UI widgets via vision models",
            category=CapabilityCategory.VISUAL_CUA,
            providers=["provider_ui_tars", "provider_agent_s"],
            preferred_provider="provider_ui_tars",
            fallback_providers=["provider_agent_s"],
            risk_level=RiskLevel.HIGH,
            requires_authorization=True,
            requires_verification=True,
            cost_class=CostClass.HIGH,
            latency_class=LatencyClass.SLOW
        ))

        # 6. High-Risk Financial & Purchasing
        self.register(CapabilityDefinition(
            capability_id="financial.purchase_software",
            name="Execute Financial Software Purchase",
            description="Authorizes payment card or banking debit for business procurement",
            category=CapabilityCategory.API,
            providers=["provider_api_mcp"],
            preferred_provider="provider_api_mcp",
            fallback_providers=[],
            risk_level=RiskLevel.CRITICAL,
            requires_authorization=True,
            requires_human_approval=True,  # Mandatory human sign-off
            requires_verification=True,
            supports_rollback=False,
            cost_class=CostClass.HIGH,
            latency_class=LatencyClass.MEDIUM
        ))

    def register(self, definition: CapabilityDefinition):
        self._registry[definition.capability_id] = definition

    def get_capability(self, capability_id: str) -> Optional[CapabilityDefinition]:
        return self._registry.get(capability_id)

    def list_capabilities(self, category: Optional[CapabilityCategory] = None) -> List[CapabilityDefinition]:
        if category:
            return [cap for cap in self._registry.values() if cap.category == category]
        return list(self._registry.values())

    def get_providers_for_capability(self, capability_id: str) -> List[str]:
        cap = self.get_capability(capability_id)
        if not cap:
            return []
        return cap.providers
