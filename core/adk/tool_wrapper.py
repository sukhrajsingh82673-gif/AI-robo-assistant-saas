"""ZONATA Sovereign Core — Google ADK Tool Wrapper.

Implements OpenCode Step 4F (Rule 34 & Rule 35):
Wraps sovereign tools for Google ADK agents, guaranteeing that all tool calls:
1. Package inputs into immutable ActionEnvelopes.
2. Undergo full 9-step governance evaluation via ActionGateway.
3. Execute through ToolRegistry with capability truth checks.
4. Enforce deterministic idempotency keys (Rule 35) to prevent duplicate side-effects.
"""

from __future__ import annotations
import logging
import time
from typing import Any, Dict, Optional

from core.action_envelope import ActionEnvelope
from core.action_gateway import action_gateway
from core.authority.types import ActionClass
from core.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class ADKToolExecutionError(RuntimeError):
    """Raised when an ADK tool execution is rejected by policy or fails execution."""
    pass


class ZonataADKToolWrapper:
    """Wraps sovereign tools for ADK multi-agent squads."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._tool = tool_registry.get(tool_name)
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}

    @property
    def is_available(self) -> bool:
        if not self._tool:
            return False
        avail, _ = tool_registry.is_tool_available(self.tool_name)
        return avail

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        actor_id: str,
        arguments: Dict[str, Any],
        idempotency_key: str,
        action_class_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes tool through ActionGateway evaluation and ToolRegistry execution."""
        # Rule 35 Idempotency check
        if idempotency_key in self._idempotency_cache:
            cached = dict(self._idempotency_cache[idempotency_key])
            cached["cached_replay"] = True
            return cached

        if not self._tool:
            raise ADKToolExecutionError(f"Tool '{self.tool_name}' is not registered in ToolRegistry")

        resolved_act_class = action_class_name or (
            self._tool.required_action_class.value
            if hasattr(self._tool.required_action_class, "value")
            else str(self._tool.required_action_class)
        )

        envelope = ActionEnvelope.create(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=actor_id,
            capability_id=getattr(self._tool, "required_capability", "database"),
            target=self.tool_name,
            intent=f"ADK squad execute {self.tool_name}",
            parameters=arguments,
            action_class=resolved_act_class,
            idempotency_key=idempotency_key,
        )

        decision = action_gateway.evaluate_decision_gate(envelope)
        if not decision.allowed:
            raise ADKToolExecutionError(
                f"ActionGateway rejected tool '{self.tool_name}': {decision.rule_id} - {decision.reason}"
            )

        result = tool_registry.execute(
            name=self.tool_name,
            tenant_id=tenant_id,
            company_id=company_id,
            principal_id=actor_id,
            arguments=arguments,
            idempotency_key=idempotency_key,
        )

        outcome = {
            "tool": self.tool_name,
            "result": result,
            "idempotency_key": idempotency_key,
            "timestamp": time.time(),
            "cached_replay": False,
        }
        self._idempotency_cache[idempotency_key] = outcome
        return outcome
