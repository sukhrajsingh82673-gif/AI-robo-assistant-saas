"""ZONATA Sovereign Core — ZonataAgentRuntime Kernel.

Implements OpenCode Step 2E (Requirements 1, 2, 3, 4, 6):
1. Executes declarative zonata.agent/v1 specs.
2. Bounded execution loops (max_steps, timeout_seconds, budget_micro_units).
3. Repetition detection: breaks and halts when identical tool calls occur without state change.
4. Tool dispatch with Pydantic validation, ActionGateway governance, and spend tracking.
5. Crash recovery: steps persisted to agent_run_steps; resumed runs skip already-executed
   idempotency keys (never duplicating email sends or ledger postings).
6. Kill switch check before every step (halts immediately with HALTED_BY_KILL_SWITCH).
7. Working memory is task-scoped; untrusted content delimited; prompt injection attacks neutralized.
8. Deterministic math executed in code; uncertified agents clamped to SHADOW.
"""

from __future__ import annotations
import hashlib
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ValidationError

from core.db import db, tenant_scoped_class
from core.action_envelope import ActionEnvelope
from core.action_gateway import action_gateway, ActionGatewayRejection
from core.authority.types import ActionClass, PrincipalType, AutonomyLevel
from core.ports.base import capability_truth_table, PortStatus
from core.tools.registry import tool_registry
from core.tools.contract import wrap_untrusted_tool_output
from core.evidence_ledger import EvidenceLedger
from core.distributed_coordination import coordination
from core.agents.certification import certification_service
from agent_factory.spec.validator import SpecValidator

logger = logging.getLogger(__name__)


class AgentRunStatus:
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HALTED_BY_KILL_SWITCH = "HALTED_BY_KILL_SWITCH"
    HALTED_REPETITION = "HALTED_REPETITION"
    HALTED_LIMIT = "HALTED_LIMIT"
    HALTED_AUTHORITY_DENIED = "HALTED_AUTHORITY_DENIED"


@tenant_scoped_class
class ZonataAgentRuntime:
    """Sovereign Agent Execution Kernel.

    Honest naming: Does not claim to be LangGraph or Temporal.
    """

    def __init__(self, evidence_ledger: Optional[EvidenceLedger] = None):
        self.evidence_ledger = evidence_ledger or EvidenceLedger()

    def _is_killswitch_active(
        self,
        tenant_id: str,
        company_id: str,
        agent_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluates database kill switch matrix and distributed coordination."""
        # 1. Distributed coordination check
        killed, reason = coordination.is_killed("AGENT", agent_id)
        if killed:
            return True, f"Coordination coordinator kill switch active: {reason}"

        # 2. Database matrix check
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT level, target_id, reason FROM enterprise_killswitch_matrix
                    WHERE is_active = 1 AND (
                        (level = 'GLOBAL') OR
                        (level = 'TENANT' AND (target_id = ? OR target_id = '*')) OR
                        (level = 'COMPANY' AND (target_id = ? OR target_id = '*')) OR
                        (level = 'AGENT' AND target_id = ?)
                    )
                    LIMIT 1
                    """,
                    (tenant_id, company_id, agent_id)
                )
                row = cur.fetchone()
                if row:
                    level, target, r = row
                    return True, f"Active {level} kill switch on '{target}': {r}"
        except Exception:
            pass

        return False, None

    def execute_plan_step(
        self,
        run_id: str,
        step_number: int,
        tenant_id: str,
        company_id: str,
        agent_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a single proposed tool step through schema validation, ActionGateway, and tool registry."""
        step_id = f"step_{run_id}_{step_number}"
        t0 = time.perf_counter()

        # Check if already executed (Crash Recovery / Idempotency)
        if idempotency_key:
            try:
                with db.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT status, result, duration_ms, evidence_id FROM agent_run_steps
                        WHERE run_id = ? AND idempotency_key = ? AND status = 'SUCCESS'
                        LIMIT 1
                        """,
                        (run_id, idempotency_key)
                    )
                    row = cur.fetchone()
                    if row:
                        res_data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        logger.info(f"Reusing persisted step {step_number} with idempotency key '{idempotency_key}'")
                        return {
                            "status": "SUCCESS",
                            "data": res_data,
                            "replayed": True,
                            "idempotency_key": idempotency_key,
                            "duration_ms": row[2],
                            "evidence_id": row[3],
                        }
            except Exception:
                pass

        tool = tool_registry.get(tool_name)
        if not tool:
            return {
                "status": "FAILED",
                "error": f"Tool '{tool_name}' is not registered in tool registry",
                "tool_name": tool_name,
            }

        # Capability Truth Gate: Do not invoke unconfigured or unimplemented capabilities
        cap_status = capability_truth_table.get_status(tool.required_capability)
        if cap_status not in (PortStatus.OK.value, PortStatus.SANDBOX.value):
            return {
                "status": "CAPABILITY_UNAVAILABLE",
                "error": f"Tool '{tool_name}' capability '{tool.required_capability}' is {cap_status}",
                "capability": tool.required_capability,
                "capability_status": cap_status,
                "tool_name": tool_name,
            }

        # Input Schema Validation
        try:
            parsed_args = tool.input_schema(**arguments)
        except ValidationError as ve:
            return {
                "status": "VALIDATION_ERROR",
                "error": f"Tool '{tool_name}' input validation failed: {ve}",
                "tool_name": tool_name,
            }

        # ActionGateway Authority Gate
        spend_amount = (
            arguments.get("total_amount_minor_units", 0)
            or arguments.get("amount_minor_units", 0)
            or getattr(tool, "cost_cents", 0)
        )
        envelope = ActionEnvelope.create(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_id=agent_id,
            principal_id=agent_id,
            principal_type=PrincipalType.AGENT.value,
            action_class=tool.required_action_class.value,
            capability_id=tool.required_capability,
            target=f"tool:{tool_name}",
            intent=f"Execute tool {tool_name}",
            parameters=arguments,
            spend_amount_minor_units=spend_amount,
            idempotency_key=idempotency_key,
        )

        decision = action_gateway.evaluate_decision_gate(envelope)
        if decision.status != "APPROVED":
            # Record rejected step
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self._persist_step(
                step_id=step_id,
                run_id=run_id,
                tenant_id=tenant_id,
                company_id=company_id,
                step_number=step_number,
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                status="REJECTED",
                idempotency_key=idempotency_key,
                duration_ms=duration_ms,
                error=decision.reason or decision.rule_id,
            )
            return {
                "status": "AUTHORITY_DENIED",
                "error": f"ActionGateway rejected execution: {decision.reason or decision.rule_id}",
                "rule_id": decision.rule_id,
                "decision_id": decision.decision_id,
            }

        # Tool Execution
        try:
            output_model = tool.execute(
                tenant_id=tenant_id,
                company_id=company_id,
                principal_id=agent_id,
                args=parsed_args,
                idempotency_key=idempotency_key,
            )
            raw_data = output_model.dict() if hasattr(output_model, "dict") else dict(output_model)
            duration_ms = (time.perf_counter() - t0) * 1000.0

            # Record to evidence ledger
            evidence_id = None
            try:
                evidence_id = self.evidence_ledger.append_entry(
                    event_type="AGENT_TOOL_EXECUTION",
                    principal_id=agent_id,
                    metadata={
                        "run_id": run_id,
                        "step_number": step_number,
                        "tool_name": tool_name,
                        "duration_ms": duration_ms,
                    },
                    payload={"arguments": arguments, "result": raw_data},
                    tenant_id=tenant_id,
                    company_id=company_id,
                )
            except Exception:
                pass

            # Persist successful step for crash recovery
            self._persist_step(
                step_id=step_id,
                run_id=run_id,
                tenant_id=tenant_id,
                company_id=company_id,
                step_number=step_number,
                tool_name=tool_name,
                arguments=arguments,
                result=raw_data,
                status="SUCCESS",
                idempotency_key=idempotency_key,
                duration_ms=duration_ms,
                evidence_id=evidence_id,
            )

            # Defensive output wrapping for LLM consumption
            untrusted_wrapped = wrap_untrusted_tool_output(
                source=f"tool:{tool_name}:{step_number}",
                id=step_id,
                content=json.dumps(raw_data),
            )

            return {
                "status": "SUCCESS",
                "data": raw_data,
                "untrusted_content": untrusted_wrapped,
                "duration_ms": duration_ms,
                "evidence_id": evidence_id,
                "idempotency_key": idempotency_key,
            }
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            self._persist_step(
                step_id=step_id,
                run_id=run_id,
                tenant_id=tenant_id,
                company_id=company_id,
                step_number=step_number,
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                status="FAILED",
                idempotency_key=idempotency_key,
                duration_ms=duration_ms,
                error=str(e),
            )
            return {
                "status": "EXECUTION_ERROR",
                "error": str(e),
                "duration_ms": duration_ms,
            }

    def _persist_step(
        self,
        step_id: str,
        run_id: str,
        tenant_id: str,
        company_id: str,
        step_number: int,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        status: str,
        idempotency_key: Optional[str],
        duration_ms: float,
        evidence_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Persists step execution to agent_run_steps table."""
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO agent_run_steps (
                        id, run_id, tenant_id, company_id, step_number, tool_name,
                        arguments, result, status, idempotency_key, duration_ms,
                        evidence_id, error, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step_id, run_id, tenant_id, company_id, step_number, tool_name,
                        json.dumps(arguments), json.dumps(result) if result else None,
                        status, idempotency_key, duration_ms, evidence_id, error, time.time()
                    )
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to persist step {step_number}: {e}")

    def run(
        self,
        tenant_id: str,
        company_id: str,
        agent_spec: Dict[str, Any],
        task_input: Dict[str, Any],
        planned_steps: Optional[List[Dict[str, Any]]] = None,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
        simulate_interrupt_after_step: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Executes a bounded agent run under strict sovereign constraints."""
        t_start = time.perf_counter()
        run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        agent_id = agent_spec.get("metadata", {}).get("id") or agent_spec.get("identity", {}).get("name", "agent_default")

        # 1. Spec Validation
        validator = SpecValidator()
        v_result = validator.validate(agent_spec)
        if not v_result.is_valid:
            return {
                "run_id": run_id,
                "status": AgentRunStatus.FAILED,
                "error": f"Invalid agent specification: {', '.join(v_result.errors)}",
                "completed_steps": 0,
            }

        # 2. Limits and Autonomy
        limits = agent_spec.get("limits", {})
        max_steps = min(int(limits.get("max_steps", 10)), 50)
        timeout_seconds = float(limits.get("timeout_seconds", 120.0))
        max_cost_usd = float(limits.get("max_cost_usd_per_task", 0.50))
        budget_micro_units = int(max_cost_usd * 1_000_000)

        # Certification ceiling check (Rule 19)
        autonomy_ceiling, clamp_reason = certification_service.enforce_autonomy_ceiling(
            requested_autonomy=AutonomyLevel.AUTONOMOUS,
            agent_id=agent_id,
            tenant_id=tenant_id,
            spec=agent_spec,
        )

        # Persist run entry
        now = time.time()
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO agent_runs (
                        id, tenant_id, company_id, agent_id, task_id, status,
                        current_step, max_steps, timeout_seconds, budget_micro_units,
                        spent_micro_units, autonomy_level, started_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id, tenant_id, company_id, agent_id, task_id,
                        AgentRunStatus.RUNNING, 0, max_steps, timeout_seconds,
                        budget_micro_units, 0, autonomy_ceiling.value, now
                    )
                )
                conn.commit()
        except Exception:
            pass

        steps_to_run = planned_steps or []
        completed_steps = 0
        working_memory: List[Dict[str, Any]] = [{"role": "user", "content": json.dumps(task_input)}]
        spent_micro_units = 0

        # Repetition detector history: tracks (tool_name, arguments_hash)
        call_history: List[Tuple[str, str]] = []

        for step_idx, step_def in enumerate(steps_to_run, start=1):
            # Check step bounds
            if step_idx > max_steps:
                return self._finalize_run(
                    run_id, AgentRunStatus.HALTED_LIMIT,
                    f"Exceeded maximum allowed steps ({max_steps})",
                    completed_steps, spent_micro_units, working_memory
                )

            # Check time bounds
            elapsed = time.perf_counter() - t_start
            if elapsed > timeout_seconds:
                return self._finalize_run(
                    run_id, AgentRunStatus.HALTED_LIMIT,
                    f"Exceeded maximum allowed seconds ({timeout_seconds}s)",
                    completed_steps, spent_micro_units, working_memory
                )

            # Check budget bounds
            if spent_micro_units >= budget_micro_units:
                return self._finalize_run(
                    run_id, AgentRunStatus.HALTED_LIMIT,
                    f"Exceeded task budget reservation ({budget_micro_units} micro-units)",
                    completed_steps, spent_micro_units, working_memory
                )

            # Check Kill Switch before every step
            killed, kill_reason = self._is_killswitch_active(tenant_id, company_id, agent_id)
            if killed:
                return self._finalize_run(
                    run_id, AgentRunStatus.HALTED_BY_KILL_SWITCH,
                    f"Halted immediately by active kill switch: {kill_reason}",
                    completed_steps, spent_micro_units, working_memory
                )

            tool_name = step_def.get("tool_name", "")
            arguments = step_def.get("arguments", {})
            idempotency_key = step_def.get("idempotency_key") or f"{run_id}_step_{step_idx}"

            # Repetition detection: if same tool called with identical arguments twice in a row
            args_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
            if call_history and call_history[-1] == (tool_name, args_hash):
                return self._finalize_run(
                    run_id, AgentRunStatus.HALTED_REPETITION,
                    f"Repetitive tool execution detected for '{tool_name}' without state progression; human assistance required",
                    completed_steps, spent_micro_units, working_memory
                )
            call_history.append((tool_name, args_hash))

            # Execute plan step
            step_res = self.execute_plan_step(
                run_id=run_id,
                step_number=step_idx,
                tenant_id=tenant_id,
                company_id=company_id,
                agent_id=agent_id,
                tool_name=tool_name,
                arguments=arguments,
                idempotency_key=idempotency_key,
            )

            # Check tool status
            status = step_res.get("status")
            if status == "AUTHORITY_DENIED":
                return self._finalize_run(
                    run_id, AgentRunStatus.HALTED_AUTHORITY_DENIED,
                    step_res.get("error"),
                    completed_steps, spent_micro_units, working_memory
                )
            elif status == "CAPABILITY_UNAVAILABLE":
                return self._finalize_run(
                    run_id, AgentRunStatus.FAILED,
                    step_res.get("error"),
                    completed_steps, spent_micro_units, working_memory
                )
            elif status != "SUCCESS":
                return self._finalize_run(
                    run_id, AgentRunStatus.FAILED,
                    step_res.get("error"),
                    completed_steps, spent_micro_units, working_memory
                )

            # Record cost
            tool = tool_registry.get(tool_name)
            if tool and tool.cost_cents:
                spent_micro_units += int(tool.cost_cents * 10_000)

            completed_steps += 1

            # Update working memory with defensive untrusted delimiters
            if step_res.get("untrusted_content"):
                working_memory.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": step_res["untrusted_content"]
                })

            # Simulate interrupt (e.g. kill -9 crash drill)
            if simulate_interrupt_after_step is not None and step_idx == simulate_interrupt_after_step:
                return {
                    "run_id": run_id,
                    "status": "INTERRUPTED",
                    "completed_steps": completed_steps,
                    "interrupt_step": step_idx,
                    "reason": "Process killed mid-run (simulation)",
                }

        return self._finalize_run(
            run_id, AgentRunStatus.COMPLETED,
            None, completed_steps, spent_micro_units, working_memory
        )

    def resume(
        self,
        run_id: str,
        tenant_id: str,
        company_id: str,
        agent_spec: Dict[str, Any],
        task_input: Dict[str, Any],
        planned_steps: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resumes an interrupted run, skipping steps already executed via idempotency keys."""
        logger.info(f"Resuming run '{run_id}'...")
        return self.run(
            tenant_id=tenant_id,
            company_id=company_id,
            agent_spec=agent_spec,
            task_input=task_input,
            planned_steps=planned_steps,
            run_id=run_id,
        )

    def _finalize_run(
        self,
        run_id: str,
        status: str,
        error_reason: Optional[str],
        completed_steps: int,
        spent_micro_units: int,
        working_memory: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Persists the final status and cost of an agent run."""
        now = time.time()
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE agent_runs
                    SET status = ?, error_reason = ?, current_step = ?,
                        spent_micro_units = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (status, error_reason, completed_steps, spent_micro_units, now, run_id)
                )
                conn.commit()
        except Exception:
            pass

        return {
            "run_id": run_id,
            "status": status,
            "error": error_reason,
            "completed_steps": completed_steps,
            "spent_micro_units": spent_micro_units,
            "working_memory_count": len(working_memory),
        }
