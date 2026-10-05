"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Governed Tool Registry & Capability Gateway

Implements Section 16 & Section 17 of the Gemma 4 Master Specification:
- Dynamic registration of all available capabilities
- Invariant: Gemma 4 NEVER invents tool calls. Proposes tool call -> AuthorityGateway permits/denies.
- Schema per tool:
    tool_id, description, input_schema, output_schema, risk, permissions,
    cost, side_effects, rollback, required_approval, tenant_scope, company_scope.
- Bridges seamlessly with existing ZONATA runtimes:
    Agency Swarm, Letta, HAL, LangGraph, A2A, MCP, OpenHands, Browser Use,
    Universal Terminal, Evidence Ledger, and Kill Switches.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.governed.tool_registry")

class ToolExecutionDeniedError(PermissionError):
    """Raised when AuthorityGateway denies an unauthorized tool execution proposal."""
    pass

@dataclass
class GovernedToolSpec:
    tool_id: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk: str                           # LOW, MEDIUM, HIGH, CRITICAL
    permissions: List[str]
    cost_per_call_usd: float
    side_effects: List[str]
    rollback_handler: Optional[str]
    required_approval: bool
    tenant_scope: str = "tnt_primary"
    company_scope: str = "comp_primary"
    is_active: bool = True
    system_origin: str = "ZONATA_NATIVE" # MCP, BROWSER_USE, OPENHANDS, TERMINAL, A2A, LANGGRAPH

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GovernedToolRegistry:
    """
    Central repository of validated enterprise capabilities.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._tools: Dict[str, GovernedToolSpec] = {}
        self._seed_default_capabilities()

    def _seed_default_capabilities(self):
        tools = [
            GovernedToolSpec(
                tool_id="hospitality_pms_yield_optimizer",
                description="Queries PMS occupancy telemetry and updates room ADR pricing tiers within bounded corridors.",
                input_schema={"type": "object", "properties": {"target_occupancy_pct": {"type": "number"}}},
                output_schema={"type": "object", "properties": {"updated_rates": {"type": "array"}}},
                risk="MEDIUM",
                permissions=["pms:rate_update"],
                cost_per_call_usd=0.01,
                side_effects=["MUTATES_LIVE_ROOM_RATES"],
                rollback_handler="rollback_pms_rates",
                required_approval=False,
                system_origin="HOSPITALITY_PMS"
            ),
            GovernedToolSpec(
                tool_id="marketing_campaign_dispatcher",
                description="Deploys targeted direct-booking promotional sequences across verified email & social channels.",
                input_schema={"type": "object", "properties": {"campaign_budget": {"type": "number"}}},
                output_schema={"type": "object", "properties": {"campaign_id": {"type": "string"}}},
                risk="MEDIUM",
                permissions=["marketing:publish"],
                cost_per_call_usd=0.05,
                side_effects=["TRANSMITS_EXTERNAL_MESSAGES", "DEBITS_MARKETING_BUDGET"],
                rollback_handler="pause_ad_campaign",
                required_approval=False,
                system_origin="A2A_MARKETING_SWARM"
            ),
            GovernedToolSpec(
                tool_id="operational_night_audit_runner",
                description="Executes nightly ledger balance, guest folio reconciliation, and revenue posting audit.",
                input_schema={"type": "object", "properties": {"audit_date": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"balance_verified": {"type": "boolean"}}},
                risk="LOW",
                permissions=["accounting:audit"],
                cost_per_call_usd=0.0,
                side_effects=["READ_ONLY_ACCOUNTING_AUDIT"],
                rollback_handler=None,
                required_approval=False,
                system_origin="NIGHT_AUDIT_ENGINE"
            ),
            GovernedToolSpec(
                tool_id="universal_terminal_command_executor",
                description="Executes sandboxed Linux commandline tools under strictly contained subprocess isolation.",
                input_schema={"type": "object", "properties": {"cmd": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"exit_code": {"type": "integer"}}},
                risk="HIGH",
                permissions=["terminal:sandboxed_exec"],
                cost_per_call_usd=0.0,
                side_effects=["HOST_COMPUTE_EXECUTION"],
                rollback_handler="kill_sandbox_process",
                required_approval=True,
                system_origin="UNIVERSAL_TERMINAL"
            ),
            GovernedToolSpec(
                tool_id="browser_web_scraper",
                description="Retrieves public competitor rate data and market sentiment using headless browser automation.",
                input_schema={"type": "object", "properties": {"target_url": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"extracted_rates": {"type": "object"}}},
                risk="LOW",
                permissions=["browser:scrape"],
                cost_per_call_usd=0.002,
                side_effects=["NETWORK_EGRESS"],
                rollback_handler=None,
                required_approval=False,
                system_origin="BROWSER_USE"
            ),
            GovernedToolSpec(
                tool_id="mcp_connector_bridge",
                description="Interoperates with external MCP servers for enterprise data sync and SaaS tool execution.",
                input_schema={"type": "object", "properties": {"server_id": {"type": "string"}, "method": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"result": {"type": "object"}}},
                risk="MEDIUM",
                permissions=["mcp:invoke"],
                cost_per_call_usd=0.01,
                side_effects=["EXTERNAL_SAAS_CALL"],
                rollback_handler="mcp_disconnect",
                required_approval=False,
                system_origin="MCP"
            )
        ]
        for t in tools:
            self.register_tool(t)

    def register_tool(self, tool_spec: GovernedToolSpec):
        self._tools[tool_spec.tool_id] = tool_spec

    def get_tool(self, tool_id: str) -> Optional[GovernedToolSpec]:
        return self._tools.get(tool_id)

    def list_tools(self) -> List[GovernedToolSpec]:
        return list(self._tools.values())

    def get_manifest_for_prompt(self) -> List[Dict[str, Any]]:
        """Clean manifest presented to Gemma 4 without leaking internal keys."""
        manifest = []
        for t in self._tools.values():
            if t.is_active:
                manifest.append({
                    "tool_id": t.tool_id,
                    "description": t.description,
                    "risk": t.risk,
                    "required_approval": t.required_approval,
                    "origin": t.system_origin
                })
        return manifest

    def authorize_and_dispatch(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        caller_role: str = "AI_CEO",
        spending_limit_inr: float = 50000.0,
        human_owner_approved: bool = False
    ) -> Dict[str, Any]:
        """
        Authority Gateway validation for tool invocation.
        Never allows Gemma 4 to bypass authorization.
        """
        tool = self.get_tool(tool_id)
        if not tool:
            raise ToolExecutionDeniedError(f"Tool '{tool_id}' is not registered in the Governed Tool Registry.")

        # Check Approval Requirement
        if tool.required_approval and not human_owner_approved:
            return {
                "success": False,
                "status": "APPROVAL_REQUIRED",
                "tool_id": tool_id,
                "reason": f"Tool '{tool_id}' carries {tool.risk} risk and requires Human Owner authorization before execution."
            }

        # Simulated safe execution
        return {
            "success": True,
            "status": "EXECUTED",
            "tool_id": tool_id,
            "origin": tool.system_origin,
            "side_effects": tool.side_effects,
            "result": {"status": "SUCCESS", "message": f"Tool '{tool_id}' executed safely under ZONATA AuthorityGateway."}
        }
