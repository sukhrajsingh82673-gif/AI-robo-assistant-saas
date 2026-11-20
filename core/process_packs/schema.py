"""ZONATA Sovereign Core — Process Pack Schema & Validation.

Implements Section 5 of ZONATA Master Prompt:
- SIPOC model: Suppliers, Inputs, Process Steps, Outputs, Customers.
- Lean waste tags: waiting, rework, over-processing, handoff, defects, unused_talent.
- Andon trigger rules: deterministic stop-the-line conditions.
- Autonomy levels & promotion/demotion criteria.
- Simulation scenarios with expected KPIs.
"""

from __future__ import annotations

import ast
import enum
from dataclasses import asdict, dataclass, field
from types import CodeType
from typing import Any, Dict, List, Optional, Set


_ALLOWED_ANDON_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Tuple,
    ast.List,
)


def compile_andon_expression(expression: str) -> CodeType:
    """Compiles an Andon expression after rejecting calls/attributes/subscripts."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Andon trigger_expression must be a non-empty string.")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid Andon expression: {exc}") from exc
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_ANDON_NODES):
            raise ValueError(
                f"Andon expression uses disallowed syntax: {type(node).__name__}"
            )
    return compile(tree, "<andon>", "eval")


class WasteTag(str, enum.Enum):
    WAITING = "waiting"
    REWORK = "rework"
    OVER_PROCESSING = "over_processing"
    HANDOFF = "handoff"
    DEFECTS = "defects"
    UNUSED_TALENT = "unused_talent"


@dataclass
class SIPOC:
    suppliers: List[str]
    inputs: List[str]
    process_steps: List[str]
    outputs: List[str]
    customers: List[str]


@dataclass
class ProcessStep:
    id: str
    name: str
    actor: str  # "agent" | "human" | "system"
    role: str  # e.g. "CMO", "CFO", "specialist"
    tool_capabilities: List[str] = field(default_factory=list)
    gate_checks: List[str] = field(default_factory=list)
    reversible: bool = True
    timeout_seconds: int = 3600
    retry_max: int = 3


@dataclass
class AndonRule:
    condition_id: str
    rule_name: str
    trigger_expression: str
    action: str  # "HALT_AND_ESCALATE" | "FLAG_FOR_REVIEW"
    escalate_to_role: str
    description: str


@dataclass
class AutonomyCriteria:
    current_level: int
    promotion_criteria: Dict[str, Any]
    demotion_criteria: Dict[str, Any]


@dataclass
class ProcessKPIs:
    target_cycle_time_seconds: float
    target_first_pass_yield: float  # e.g. 0.95 (95%)
    target_cost_per_unit_usd: float
    target_error_rate: float
    target_customer_satisfaction: Optional[float] = None


@dataclass
class SimulationScenario:
    scenario_id: str
    name: str
    description: str
    initial_inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any]
    expected_status: str = "COMPLETED"


@dataclass
class ProcessPack:
    pack_id: str
    version: str
    name: str
    description: str
    owner_role: str
    trigger_events: List[str]
    sipoc: SIPOC
    steps: List[ProcessStep]
    policies: Dict[str, Any]
    kpis: ProcessKPIs
    waste_tags: List[str]
    andon: List[AndonRule]
    autonomy: AutonomyCriteria
    simulation_scenarios: List[SimulationScenario] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validates internal consistency and integrity of the Process Pack."""
        errors: List[str] = []

        if not self.pack_id:
            errors.append("ProcessPack pack_id must not be empty.")
        if not self.steps:
            errors.append("ProcessPack must contain at least one ProcessStep.")

        step_ids: Set[str] = set()
        for idx, step in enumerate(self.steps):
            if not step.id:
                errors.append(f"Step at index {idx} has an empty id.")
            if step.id in step_ids:
                errors.append(f"Duplicate step id detected: '{step.id}'.")
            step_ids.add(step.id)

            if step.actor not in ("agent", "human", "system"):
                errors.append(f"Step '{step.id}' has invalid actor '{step.actor}'. Must be agent, human, or system.")

        # Verify SIPOC references
        for p_step in self.sipoc.process_steps:
            if p_step not in step_ids:
                errors.append(f"SIPOC references unknown process step: '{p_step}'.")

        # Verify waste tags use the canonical token set
        valid_waste_tags = {tag.value for tag in WasteTag}
        for tag in self.waste_tags:
            if tag not in valid_waste_tags:
                errors.append(
                    f"Unknown waste tag '{tag}'. Must be one of {sorted(valid_waste_tags)}."
                )

        # Verify Andon rules
        for andon in self.andon:
            if andon.action not in ("HALT_AND_ESCALATE", "FLAG_FOR_REVIEW"):
                errors.append(f"Andon rule '{andon.condition_id}' has invalid action '{andon.action}'.")
            try:
                compile_andon_expression(andon.trigger_expression)
            except ValueError as exc:
                errors.append(f"Andon rule '{andon.condition_id}': {exc}")

        # Verify Autonomy levels (L0-L4)
        if self.autonomy.current_level not in (0, 1, 2, 3, 4):
            errors.append(f"Invalid autonomy current_level {self.autonomy.current_level}. Must be between 0 and 4.")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
