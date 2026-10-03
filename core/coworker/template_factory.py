"""
ZONATA Universal AI Co-worker Fabric — Co-worker Template Factory
Compiles high-level owner specifications into fully-configured CoworkerProfile objects
equipped with scoped capabilities, policies, approval gates, and working hours.
"""

from typing import Dict, List, Optional, Any
import time
import uuid
from .contracts import CoworkerProfile, RiskLevel

class CoworkerTemplateFactory:
    """
    Factory for instantiating specialized AI Co-workers.
    The owner can specify natural language roles, and the factory compiles
    the profile with least-privilege scoping.
    """

    @staticmethod
    def create_hotel_revenue_coworker(tenant_id: str = "tnt_primary", worker_id: Optional[str] = None) -> CoworkerProfile:
        wid = worker_id or f"cw_hotel_rev_{uuid.uuid4().hex[:6]}"
        return CoworkerProfile(
            worker_id=wid,
            tenant_id=tenant_id,
            role="Hotel Revenue Operations Specialist",
            department="Revenue & Front Desk",
            skills=["Occupancy Analysis", "Spreadsheet Modelling", "Rate Management", "Competitor Scraping"],
            capabilities=[
                "rpa.excel_update",
                "rpa.excel_read",
                "api.crm_read",
                "api.crm_update",
                "browser.navigate",
                "browser.extract",
                "desktop.workflow",
                "desktop.accessibility_tree"
            ],
            authority_scope={
                "financial_transactions": False,
                "destructive_operations": False,
                "max_single_budget_usd": 10.0,
                "forbidden_actions": ["financial.purchase_software", "system.format_disk"]
            },
            credential_scope=["pms_reader", "crm_editor"],
            platform_scope=["linux", "windows", "darwin"],
            allowed_providers=["provider_robocorp", "provider_api_mcp", "provider_playwright", "provider_openadapt", "provider_linux_desktop"],
            risk_limit=RiskLevel.MEDIUM,
            working_hours="24x7",
            mission_limit=20,
            budget_limit=100.0,
            status="ACTIVE"
        )

    @staticmethod
    def create_procurement_coworker(tenant_id: str = "tnt_primary", worker_id: Optional[str] = None) -> CoworkerProfile:
        wid = worker_id or f"cw_procure_{uuid.uuid4().hex[:6]}"
        return CoworkerProfile(
            worker_id=wid,
            tenant_id=tenant_id,
            role="Enterprise Procurement & Supplier Specialist",
            department="Operations",
            skills=["Supplier Comparison", "Price Extraction", "Purchase Order Preparation"],
            capabilities=[
                "browser.navigate",
                "browser.extract",
                "browser.screenshot",
                "api.email_send",
                "financial.purchase_software"  # Gated by human approval
            ],
            authority_scope={
                "financial_transactions": False,  # Mandatory human approval
                "destructive_operations": False,
                "forbidden_actions": []
            },
            credential_scope=["supplier_portal"],
            platform_scope=["linux", "windows", "darwin"],
            allowed_providers=["provider_playwright", "provider_api_mcp", "provider_visual_cua"],
            risk_limit=RiskLevel.MEDIUM,
            working_hours="08:00-20:00",
            mission_limit=10,
            budget_limit=250.0,
            status="ACTIVE"
        )

    @staticmethod
    def create_desktop_operator_coworker(tenant_id: str = "tnt_primary", worker_id: Optional[str] = None) -> CoworkerProfile:
        wid = worker_id or f"cw_desktop_{uuid.uuid4().hex[:6]}"
        return CoworkerProfile(
            worker_id=wid,
            tenant_id=tenant_id,
            role="Legacy Desktop Automation Operator",
            department="IT Operations",
            skills=["Legacy ERP Operation", "Report Exportation", "GUI Automation"],
            capabilities=[
                "desktop.workflow",
                "desktop.accessibility_tree",
                "desktop.click_element",
                "mcp.screenshot",
                "mcp.mouse_click",
                "visual.screen_understanding"
            ],
            authority_scope={
                "financial_transactions": False,
                "destructive_operations": False,
                "forbidden_actions": []
            },
            credential_scope=["desktop_session"],
            platform_scope=["linux", "windows"],
            allowed_providers=["provider_openadapt", "provider_linux_desktop", "provider_windows_desktop", "provider_computer_use_mcp", "provider_visual_cua"],
            risk_limit=RiskLevel.MEDIUM,
            working_hours="24x7",
            mission_limit=15,
            budget_limit=50.0,
            status="ACTIVE"
        )

    @classmethod
    def compile_from_natural_language(cls, natural_prompt: str, tenant_id: str = "tnt_primary") -> CoworkerProfile:
        prompt_lower = natural_prompt.lower()
        if "hotel" in prompt_lower or "revenue" in prompt_lower or "occupancy" in prompt_lower:
            return cls.create_hotel_revenue_coworker(tenant_id)
        elif "procurement" in prompt_lower or "supplier" in prompt_lower or "purchase" in prompt_lower:
            return cls.create_procurement_coworker(tenant_id)
        elif "desktop" in prompt_lower or "legacy" in prompt_lower or "erp" in prompt_lower:
            return cls.create_desktop_operator_coworker(tenant_id)
        else:
            # Default general-purpose coworker
            return cls.create_hotel_revenue_coworker(tenant_id)
