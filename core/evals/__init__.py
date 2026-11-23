"""
ZONATA Eval Harness & Benchmark Subsystem
OpenCode Step 2K: Department golden tasks, protocol correctness, latency, spend caps, and Rule 21.
"""

from core.evals.schema import ensure_eval_tables
from core.evals.types import (
    RULE_21_DISCLAIMER,
    EvalTask,
    TaskEvalResult,
    EvalRunSummary,
)
from core.evals.runner import (
    EvalHarness,
    SpendCapExceededError,
    EvalThresholdFailedError,
)

__all__ = [
    "ensure_eval_tables",
    "RULE_21_DISCLAIMER",
    "EvalTask",
    "TaskEvalResult",
    "EvalRunSummary",
    "EvalHarness",
    "SpendCapExceededError",
    "EvalThresholdFailedError",
]
