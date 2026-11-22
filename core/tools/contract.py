"""ZONATA Sovereign Core — Tool Contract and Untrusted Content Delimiters.

Implements OpenCode Step 2E (Requirement 1):
1. Typed input schema (Pydantic), typed output schema (Pydantic).
2. Side-effect class (READ, WRITE_REVERSIBLE, WRITE_IRREVERSIBLE, EXTERNAL_COMMS, MONEY).
3. Required capability key checked against capability truth table.
4. Required action class for ActionGateway governance evaluation.
5. Cost model in minor units / cents, timeout seconds, idempotency key support.
6. Defensive delimiter wrapping of untrusted tool outputs.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
import hashlib
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field

from core.authority.types import ActionClass


class SideEffectClass(str, Enum):
    READ = "READ"
    WRITE_REVERSIBLE = "WRITE_REVERSIBLE"
    WRITE_IRREVERSIBLE = "WRITE_IRREVERSIBLE"
    EXTERNAL_COMMS = "EXTERNAL_COMMS"
    MONEY = "MONEY"


def wrap_untrusted_tool_output(
    source: str,
    id: str,
    content: str,
    sha256: Optional[str] = None
) -> str:
    """Labels untrusted output and defensively delimits before it reaches a model.

    Neutralizes rogue closing delimiter attempts embedded inside the text.
    Format:
    <<<UNTRUSTED_CONTENT source="..." id="..." sha256="..." >>>
    ...
    <<<END_UNTRUSTED_CONTENT>>>
    """
    if sha256 is None:
        sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Neutralize closing delimiter attempts in text
    safe_content = content.replace("<<<END_UNTRUSTED_CONTENT>>>", "<<<NEUTRALIZED_UNTRUSTED_CONTENT>>>")

    return (
        f'<<<UNTRUSTED_CONTENT source="{source}" id="{id}" sha256="{sha256}">>>\n'
        f'{safe_content}\n'
        f'<<<END_UNTRUSTED_CONTENT>>>'
    )


class ToolContract(ABC):
    """Abstract base contract for all sovereign tools."""
    name: str = "base_tool"
    description: str = "Base tool description"
    version: str = "1.0.0"
    side_effect_class: SideEffectClass = SideEffectClass.READ
    required_capability: str = "database"
    required_action_class: ActionClass = ActionClass.READ_INTERNAL
    cost_cents: int = 0
    timeout_seconds: float = 30.0
    supports_idempotency: bool = True

    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]

    @abstractmethod
    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: BaseModel,
        idempotency_key: Optional[str] = None,
    ) -> BaseModel:
        """Executes the tool with validated arguments."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "side_effect_class": self.side_effect_class.value,
            "required_capability": self.required_capability,
            "required_action_class": self.required_action_class.value,
            "cost_cents": self.cost_cents,
            "timeout_seconds": self.timeout_seconds,
            "supports_idempotency": self.supports_idempotency,
            "input_schema": self.input_schema.schema() if hasattr(self.input_schema, "schema") else {},
            "output_schema": self.output_schema.schema() if hasattr(self.output_schema, "schema") else {},
        }
