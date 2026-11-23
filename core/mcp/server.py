"""ZONATA Sovereign Core — Sandboxed MCP Server.

Implements OpenCode Step 4G (Defensive Wrapping & Protocol Compliance):
Exposes safe internal capabilities over standard MCP JSON-RPC protocol.
Guarantees that all output returned to callers is defensively delimited
using wrap_untrusted_tool_output(...) to neutralize injection payload attempts.
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Optional

from core.tools.contract import wrap_untrusted_tool_output
from core.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class SandboxedMCPServer:
    """Sovereign in-process sandboxed MCP server responding to JSON-RPC requests."""

    def __init__(self, server_id: str = "zonata_core_server"):
        self.server_id = server_id

    def handle_request(self, json_rpc_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming MCP JSON-RPC 2.0 requests."""
        req_id = json_rpc_request.get("id")
        method = json_rpc_request.get("method", "")
        params = json_rpc_request.get("params", {})

        if method == "tools/list":
            return self._handle_tools_list(req_id)
        elif method == "tools/call":
            return self._handle_tools_call(req_id, params)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }

    def _handle_tools_list(self, req_id: Any) -> Dict[str, Any]:
        """Lists available sandboxed tools with strictly delimited descriptions."""
        tools = tool_registry.list_tools()
        formatted_tools: List[Dict[str, Any]] = []
        for t in tools:
            formatted_tools.append({
                "name": t.get("name"),
                "description": t.get("description"),
                "inputSchema": t.get("input_schema", {}),
            })
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": formatted_tools},
        }

    def _handle_tools_call(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool and defensively wraps output against rogue closing delimiters."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        tenant_id = params.get("tenant_id", "t_sandbox")
        company_id = params.get("company_id", "c_sandbox")
        actor_id = params.get("actor_id", "actor_sandbox")

        tool = tool_registry.get(name)
        if not tool:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Tool '{name}' not found"},
            }

        res = tool_registry.execute(
            name=name,
            tenant_id=tenant_id,
            company_id=company_id,
            principal_id=actor_id,
            arguments=arguments,
        )

        raw_str = json.dumps(res)
        safe_output = wrap_untrusted_tool_output(
            source=f"mcp:{self.server_id}:{name}",
            id=f"call_{name}",
            content=raw_str,
        )

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": safe_output}],
                "isError": not res.get("success", False),
            },
        }


sandboxed_mcp_server = SandboxedMCPServer()
