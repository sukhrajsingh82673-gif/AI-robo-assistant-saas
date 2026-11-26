"""
Base Department Process Workflow Framework (Rule 59, Rule 62)
==============================================================
Provides durable execution abstractions, deterministic idempotency keys,
audit trail recording, and post-write independent re-read verification (Rule 59).
"""

from __future__ import annotations
import uuid
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, Field


class WorkflowStepRecord(BaseModel):
    step_id: str
    step_name: str
    department_code: str
    status: str  # 'COMPLETED', 'HALTED_FOR_APPROVAL', 'FAILED', 'VERIFIED'
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    re_read_verified: bool = False
    timestamp: float = Field(default_factory=time.time)


class DepartmentWorkflowContext(BaseModel):
    tenant_id: str
    company_id: str
    workflow_name: str
    workflow_version: str = "1.0.0"
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    steps: List[WorkflowStepRecord] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
    audit_trail: List[str] = Field(default_factory=list)

    def generate_idempotency_key(self, step_idx: int, action: str) -> str:
        return f"{self.run_id}_step_{step_idx}_{action}"

    def record_step(self, step_record: WorkflowStepRecord) -> None:
        self.steps.append(step_record)
        self.audit_trail.append(f"[{step_record.department_code}] {step_record.step_name}: {step_record.status}")


class ReReadVerificationFailed(Exception):
    """Raised when an independent re-read verification fails under Rule 59."""
    pass


class HumanApprovalRequiredHalt(Exception):
    """Raised when workflow halts awaiting a mandatory human approval gateway under Rule 62."""
    pass


class DepartmentBaseWorkflow(ABC):
    """Base class for all cross-department end-to-end workflows."""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version

    @abstractmethod
    def execute(self, ctx: DepartmentWorkflowContext, initial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the workflow pipeline."""
        pass

    def verify_re_read(
        self,
        step_name: str,
        entity_id: str,
        expected_values: Dict[str, Any],
        re_read_fn: Callable[[str], Optional[Dict[str, Any]]]
    ) -> bool:
        """Rule 59: Re-reads persisted state independently to confirm mutation."""
        fresh_data = re_read_fn(entity_id)
        if not fresh_data:
            raise ReReadVerificationFailed(f"Rule 59 Invariant Failed: entity '{entity_id}' could not be re-read after {step_name}.")

        for k, v in expected_values.items():
            if fresh_data.get(k) != v:
                raise ReReadVerificationFailed(
                    f"Rule 59 Re-Read Mismatch in {step_name} for '{entity_id}': expected {k}={v}, found {fresh_data.get(k)}"
                )
        return True
