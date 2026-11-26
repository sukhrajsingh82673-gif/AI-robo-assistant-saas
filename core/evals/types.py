"""
ZONATA Eval Harness Types and Models
OpenCode Step 2K: Domain types, data structures, and Rule 21 measurement constraints.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pydantic


# Rule 21 Invariant: No quality claims without measurement.
# Never present synthetic pass rates as evidence of human parity.
RULE_21_DISCLAIMER = (
    "Synthetic pass rates are computed against deterministic golden tests and are "
    "never presented as evidence of human parity."
)


class EvalTask(pydantic.BaseModel):
    """Definition of a golden eval task loaded from YAML."""
    id: str
    department: str
    name: str
    tier: str = "WORKER"
    input: Dict[str, Any] = pydantic.Field(default_factory=dict)
    task: str
    acceptance_criteria: List[str] = pydantic.Field(default_factory=list)
    scoring: Dict[str, Any] = pydantic.Field(default_factory=dict)


class TaskEvalResult(pydantic.BaseModel):
    """Result of evaluating a single golden task."""
    task_id: str
    passed: bool
    score: float
    cost_micro_units: int = 0
    latency_ms: float = 0.0
    output_summary: Dict[str, Any] = pydantic.Field(default_factory=dict)
    errors: List[str] = pydantic.Field(default_factory=list)


class EvalRunSummary(pydantic.BaseModel):
    """Summary of an evaluation run for a department or model tier."""
    id: str
    run_id: str
    tenant_id: Optional[str] = None
    company_id: Optional[str] = None
    department: str
    tier: str
    model: str
    total_tasks: int
    passed_tasks: int
    pass_rate: float
    total_cost_micro_units: int = 0
    avg_latency_ms: float = 0.0
    status: str = "COMPLETED"
    created_at: float
    task_results: List[TaskEvalResult] = pydantic.Field(default_factory=list)
    disclaimer: str = RULE_21_DISCLAIMER
