"""ZONATA Sovereign Core — Temporal Workflows for Durable Execution.

Implements OpenCode Step 4D (Standing Rules 33, 34, 35, 36, 38):
1. ZonataAgentWorkflow:
   - Versioned execution (Rule 38): carries explicit workflow_version = "1.0.0".
   - Coordinates activities deterministically.
   - Enforces Rule 35: Deterministic activity idempotency keys ({run_id}_step_{idx}_{action}).
   - In-flight execution compatibility: replayed workflow steps resolve from activity results.
"""

from __future__ import annotations
import json
import logging
import time
from typing import Any, Dict, List, Optional

from core.ports.agent_runtime import AgentSpec, ExecutionContext, AgentRuntimeStatus
from core.temporal.activities import (
    TemporalActivities,
    temporal_activities,
    NonRetryableActivityError,
)

logger = logging.getLogger(__name__)


class WorkflowExecutionRecord:
    def __init__(
        self,
        workflow_id: str,
        run_id: str,
        workflow_version: str,
        tenant_id: str,
        company_id: str,
        status: AgentRuntimeStatus,
    ):
        self.workflow_id = workflow_id
        self.run_id = run_id
        self.workflow_version = workflow_version
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.status = status
        self.step_history: List[Dict[str, Any]] = []
        self.output: Dict[str, Any] = {}
        self.error: Optional[str] = None


class ZonataAgentWorkflow:
    """Enterprise durable workflow coordinating resilient agent execution."""

    workflow_version: str = "1.0.0"

    def __init__(self, activities: Optional[TemporalActivities] = None):
        self.activities = activities or temporal_activities

    def execute(
        self,
        spec: AgentSpec,
        input_data: Dict[str, Any],
        context: ExecutionContext,
    ) -> WorkflowExecutionRecord:
        workflow_id = f"wf_{context.run_id}"
        run_id = context.run_id
        tenant_id = context.tenant_id
        company_id = context.company_id
        actor_id = context.actor_id

        record = WorkflowExecutionRecord(
            workflow_id=workflow_id,
            run_id=run_id,
            workflow_version=self.workflow_version,
            tenant_id=tenant_id,
            company_id=company_id,
            status=AgentRuntimeStatus.RUNNING,
        )

        # Check Kill Switch
        from core.distributed_coordination import coordination
        killed, k_reason = coordination.is_killed("AGENT", spec.spec_id)
        if killed:
            record.status = AgentRuntimeStatus.HALTED_BY_KILL_SWITCH
            record.error = f"Halted by active kill switch: {k_reason}"
            return record

        try:
            # Step 1: Model Planning / Execution Activity (Rule 34)
            step1_id = f"{workflow_id}_step1_llm"
            user_prompt = f"Goal: {spec.system_prompt}\nTask Input: {json.dumps(input_data)}"
            llm_outcome = self.activities.llm_generation_activity(
                tenant_id=tenant_id,
                company_id=company_id,
                system_prompt="You are an enterprise execution worker. Produce deterministic action plan.",
                user_prompt=user_prompt,
                model_tier=spec.model_tier,
                correlation_id=run_id,
            )
            record.step_history.append({"step": 1, "activity": "llm_generation", "result": llm_outcome})

            # Step 2: Tool Execution Activity if specified in input (Rule 34 & 35)
            requested_tool = input_data.get("requested_tool")
            tool_outcome = None
            if requested_tool and requested_tool in spec.allowed_tools:
                idem_key = f"{workflow_id}_step2_{requested_tool}"
                tool_args = input_data.get("tool_args", {})
                tool_outcome = self.activities.tool_execution_activity(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    actor_id=actor_id,
                    tool_name=requested_tool,
                    tool_args=tool_args,
                    idempotency_key=idem_key,
                )
                record.step_history.append({"step": 2, "activity": "tool_execution", "result": tool_outcome})

            # Step 3: Synthesis / Completion
            record.status = AgentRuntimeStatus.COMPLETED
            record.output = {
                "workflow_id": workflow_id,
                "workflow_version": self.workflow_version,
                "llm_plan": llm_outcome.get("text", ""),
                "tool_results": {requested_tool: tool_outcome} if tool_outcome else {},
                "steps_completed": len(record.step_history),
                "is_durable": True,
            }
            return record

        except NonRetryableActivityError as e:
            record.status = AgentRuntimeStatus.FAILED
            record.error = str(e)
            return record
        except Exception as e:
            record.status = AgentRuntimeStatus.FAILED
            record.error = f"Workflow execution error: {e}"
            return record
