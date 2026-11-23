"""ZONATA Sovereign Core — Tool Registry and Capability Gate.

Implements OpenCode Step 2E (Requirement 1):
- Manages registered tools and their contracts.
- Queries capability truth table: tools whose capability is not OK/SANDBOX appear as unavailable with machine-readable reasons.
- Never invokes a tool whose underlying capability is NOT_CONFIGURED or NOT_IMPLEMENTED.
"""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from core.ports.base import capability_truth_table, PortStatus
from core.tools.contract import ToolContract

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry maintaining active tool contracts and capability reality gates."""

    def __init__(self):
        self._tools: Dict[str, ToolContract] = {}

    def register(self, tool: ToolContract) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} (version {tool.version})")

    def get(self, name: str) -> Optional[ToolContract]:
        return self._tools.get(name)

    def list_tools(
        self,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List registered tools with genuine availability from the capability truth table."""
        results: List[Dict[str, Any]] = []
        for name, tool in sorted(self._tools.items()):
            cap = tool.required_capability
            status = capability_truth_table.get_status(cap)
            is_live = status in (PortStatus.OK.value, PortStatus.SANDBOX.value)

            unavailable_reason = None
            if not is_live:
                unavailable_reason = f"Capability '{cap}' status is '{status}' (unavailable)"

            info = tool.to_dict()
            info["available"] = is_live
            info["capability_status"] = status
            info["unavailable_reason"] = unavailable_reason
            results.append(info)
        return results

    def is_tool_available(self, name: str) -> tuple[bool, Optional[str]]:
        """Checks if a tool exists and its required capability is live."""
        tool = self.get(name)
        if not tool:
            return False, f"Tool '{name}' is not registered"

        status = capability_truth_table.get_status(tool.required_capability)
        if status in (PortStatus.OK.value, PortStatus.SANDBOX.value):
            return True, None
        return False, f"Capability '{tool.required_capability}' status is '{status}'"

    def execute(
        self,
        name: str,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        arguments: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validates arguments, enforces capability truth gate, and executes tool."""
        tool = self.get(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' not found in registry",
                "status": "NOT_FOUND",
            }

        # Capability Truth Gate: Do not invoke unconfigured or unimplemented capabilities
        cap_status = capability_truth_table.get_status(tool.required_capability)
        if cap_status not in (PortStatus.OK.value, PortStatus.SANDBOX.value):
            return {
                "success": False,
                "error": f"Tool '{name}' capability '{tool.required_capability}' is {cap_status}",
                "capability": tool.required_capability,
                "capability_status": cap_status,
                "status": "CAPABILITY_UNAVAILABLE",
            }

        # Input schema validation
        try:
            parsed_args = tool.input_schema(**arguments)
        except ValidationError as e:
            return {
                "success": False,
                "error": f"Invalid arguments for tool '{name}': {e}",
                "status": "VALIDATION_ERROR",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Argument parsing failed: {e}",
                "status": "VALIDATION_ERROR",
            }

        t0 = time.perf_counter()
        try:
            output_model = tool.execute(
                tenant_id=tenant_id,
                company_id=company_id,
                principal_id=principal_id,
                args=parsed_args,
                idempotency_key=idempotency_key,
            )
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "success": True,
                "data": output_model.dict(),
                "duration_ms": duration_ms,
                "status": "SUCCESS",
            }
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
                "status": "EXECUTION_ERROR",
            }


tool_registry = ToolRegistry()
