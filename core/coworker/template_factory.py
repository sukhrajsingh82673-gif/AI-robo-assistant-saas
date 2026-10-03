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
            allowed_providers=["provider_playwright", "provider_api_mcp", "provider_ui_tars", "provider_agent_s"],
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
            allowed_providers=["provider_openadapt", "provider_linux_desktop", "provider_windows_desktop", "provider_computer_use_mcp", "provider_ui_tars", "provider_agent_s"],
            risk_limit=RiskLevel.MEDIUM,
            working_hours="24x7",
            mission_limit=15,
            budget_limit=50.0,
            status="ACTIVE"
        )

    @staticmethod
    def create_supplier_research_coworker(tenant_id: str = "tnt_primary", worker_id: Optional[str] = None) -> CoworkerProfile:
        """
        Creates an autonomous Supplier Research & Market Comparison Specialist.
        Lifecycle Stages:
        1. OBJECTIVE: Continuously discover, evaluate, and benchmark enterprise suppliers.
        2. ROLE: Senior Autonomous Procurement & Supplier Intelligence Worker.
        3. CAPABILITIES: OpenClaw crawl, table extraction, CSV comparison, terminal reporting, approval gating.
        4. TOOLS: OpenClaw, Playwright, Terminal, API MCP.
        5. KNOWLEDGE: Procurement policies, vendor rating matrices, budget constraints.
        6. RULES: Never commit funds autonomously, always verify supplier tax IDs, log SHA-256 evidence.
        7. CREDENTIALS: Scoped supplier portal read tokens.
        8. PERMISSIONS: Read-only external web, write-only reports directory, gated financial.
        9. SCHEDULE: 24x7 continuous market observation.
        10. SUCCESS CRITERIA: Formatted supplier comparison report with verifiable SHA-256 hash.
        11. VERIFICATION: Out-of-band file existence, table integrity, hash matching.
        12. ESCALATION: Human supervisor approval required before issuing vendor purchase order.
        """
        wid = worker_id or f"cw_supp_res_{uuid.uuid4().hex[:6]}"
        return CoworkerProfile(
            worker_id=wid,
            tenant_id=tenant_id,
            role="Autonomous Supplier Research Specialist",
            department="Strategic Sourcing & Procurement",
            skills=[
                "Web Market Crawling",
                "Vendor Rating Benchmarking",
                "Automated Table Extraction",
                "Price Discrepancy Detection",
                "Cryptographic Report Synthesis"
            ],
            capabilities=[
                "browser.openclaw_crawl",
                "browser.openclaw_extract_table",
                "browser.openclaw_search",
                "browser.openclaw_scrape",
                "browser.navigate",
                "rpa.csv_filter",
                "terminal.file_operation",
                "terminal.verify_hash",
                "api.email_send",
                "financial.purchase_software"
            ],
            authority_scope={
                "financial_transactions": False, # Human approval mandatory
                "destructive_operations": False,
                "max_single_budget_usd": 0.0,
                "forbidden_actions": ["system.format_disk", "auth.grant_root"]
            },
            credential_scope=["supplier_read_token"],
            platform_scope=["linux", "windows", "darwin"],
            allowed_providers=[
                "provider_openclaw",
                "provider_playwright",
                "provider_terminal",
                "provider_robocorp",
                "provider_api_mcp"
            ],
            risk_limit=RiskLevel.MEDIUM,
            working_hours="24x7",
            mission_limit=30,
            budget_limit=500.0,
            status="ACTIVE",
            metadata={
                "lifecycle_stages": [
                    "OBJECTIVE", "ROLE", "CAPABILITIES", "TOOLS", "KNOWLEDGE",
                    "RULES", "CREDENTIALS", "PERMISSIONS", "SCHEDULE",
                    "SUCCESS_CRITERIA", "VERIFICATION", "ESCALATION"
                ],
                "escalation_policy": "ESCALATE_ON_PURCHASE_OVER_ZERO_USD",
                "verification_method": "INDEPENDENT_FILE_HASH"
            }
        )

    @classmethod
    def compile_from_natural_language(cls, natural_prompt: str, tenant_id: str = "tnt_primary") -> CoworkerProfile:
        prompt_lower = natural_prompt.lower()
        if "supplier" in prompt_lower or "research worker" in prompt_lower or "sourcing" in prompt_lower:
            return cls.create_supplier_research_coworker(tenant_id)
        elif "hotel" in prompt_lower or "revenue" in prompt_lower or "occupancy" in prompt_lower:
            return cls.create_hotel_revenue_coworker(tenant_id)
        elif "procurement" in prompt_lower or "purchase" in prompt_lower:
            return cls.create_procurement_coworker(tenant_id)
        elif "desktop" in prompt_lower or "legacy" in prompt_lower or "erp" in prompt_lower:
            return cls.create_desktop_operator_coworker(tenant_id)
        else:
            return cls.create_supplier_research_coworker(tenant_id)
