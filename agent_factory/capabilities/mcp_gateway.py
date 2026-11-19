"""ZONATA Agent Factory - MCP Tool Gateway with Tool Description Hash Pinning.

Implements Gate AT-13:
- Authorization scope verification before MCP invocation
- Hash pinning of tool descriptions & schemas to defeat prompt injection poisoning
- Complete evidence recording on all executions and denials
"""

from __future__ import annotations
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent_factory.ports import EvidenceEvent


class McpGatewayError(Exception):
    """Base error for MCP gateway."""
    pass


class McpUnauthorizedError(McpGatewayError):
    """Raised when caller lacks required authorization scopes."""
    pass


class McpPoisoningDetectedError(McpGatewayError):
    """Raised when an MCP tool's description/schema does not match its pinned hash."""
    pass


def canonical_schema_hash(schema: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of tool schema/description."""
    canonical_bytes = json.dumps(
        schema,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


class McpToolRegistration:
    def __init__(
        self,
        server_id: str,
        tool_name: str,
        schema: Dict[str, Any],
        required_scopes: List[str],
        handler: Optional[Callable[[Dict[str, Any]], Any]] = None
    ):
        self.server_id = server_id
        self.tool_name = tool_name
        self.schema = schema
        self.pinned_sha256 = canonical_schema_hash(schema)
        self.required_scopes = set(required_scopes)
        self.handler = handler or (lambda args: {"result": "ok", "echo": args})


class McpGateway:
    def __init__(self, evidence_port=None):
        self.evidence = evidence_port
        self._tools: Dict[Tuple[str, str], McpToolRegistration] = {}

    def register_tool(
        self,
        server_id: str,
        tool_name: str,
        schema: Dict[str, Any],
        required_scopes: List[str],
        handler: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> McpToolRegistration:
        reg = McpToolRegistration(server_id, tool_name, schema, required_scopes, handler)
        self._tools[(server_id, tool_name)] = reg
        return reg

    def invoke(
        self,
        server_id: str,
        tool_name: str,
        args: Dict[str, Any],
        caller_scopes: List[str],
        current_schema_presented: Optional[Dict[str, Any]] = None,
        tenant_id: str = "tnt_default",
        agent_id: str = "agt_unknown"
    ) -> Any:
        key = (server_id, tool_name)
        if key not in self._tools:
            raise McpGatewayError(f"MCP tool '{server_id}/{tool_name}' not registered")

        reg = self._tools[key]

        # 1. Scope Authorization Check
        caller_scope_set = set(caller_scopes)
        if not reg.required_scopes.issubset(caller_scope_set):
            missing = reg.required_scopes - caller_scope_set
            if self.evidence:
                self.evidence.append_event(EvidenceEvent(
                    subject_kind="mcp_call",
                    subject_id=f"{server_id}/{tool_name}",
                    event_type="mcp.call.denied",
                    actor=agent_id,
                    payload_hashes={"missing_scopes": sorted(list(missing))},
                    timestamp=time.time(),
                    tenant_id=tenant_id
                ))
            raise McpUnauthorizedError(f"Missing required MCP scopes: {missing}")

        # 2. Hash Pinning Verification (Gate AT-13)
        if current_schema_presented is not None:
            presented_hash = canonical_schema_hash(current_schema_presented)
            if presented_hash != reg.pinned_sha256:
                if self.evidence:
                    self.evidence.append_event(EvidenceEvent(
                        subject_kind="mcp_call",
                        subject_id=f"{server_id}/{tool_name}",
                        event_type="mcp.poisoning_detected",
                        actor=agent_id,
                        payload_hashes={
                            "expected_hash": reg.pinned_sha256,
                            "presented_hash": presented_hash
                        },
                        timestamp=time.time(),
                        tenant_id=tenant_id
                    ))
                raise McpPoisoningDetectedError(
                    f"AF-TOOL-POISONING-DETECTED: Tool description modified dynamically! "
                    f"Expected hash {reg.pinned_sha256[:12]}..., got {presented_hash[:12]}..."
                )

        # 3. Execution
        res = reg.handler(args)

        if self.evidence:
            self.evidence.append_event(EvidenceEvent(
                subject_kind="mcp_call",
                subject_id=f"{server_id}/{tool_name}",
                event_type="mcp.call.ok",
                actor=agent_id,
                payload_hashes={
                    "server": server_id,
                    "tool": tool_name,
                    "pinned_hash": reg.pinned_sha256
                },
                timestamp=time.time(),
                tenant_id=tenant_id
            ))

        return res
