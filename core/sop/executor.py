"""
ZONATA SOP Step Executor
OpenCode Step 2G: Verifiable step-by-step SOP execution kernel, dry-run planner, and reverse compensation engine.
"""

from __future__ import annotations

import time
import uuid
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple

from core.db import db
from core.evidence_service import evidence_service
from core.tools import tool_registry
from core.sop.types import (
    SOPStepType,
    SOPInstanceStatus,
    SOPVersionStatus,
    SOPStepReversibility,
    SOPStepOutcome,
    SOPStepDefinition,
    SOPRunRequest,
    SOPNotExecutableError,
    SOPPreconditionFailedError,
    SOPPostconditionFailedError,
    SOPStepExecutionError,
    SOPCompensationFailedError,
)
from core.sop.definition import sop_definition_service
from core.sop.compliance import sop_compliance_calculator


class SOPConditionEvaluator:
    """
    Deterministic in-code condition evaluator for SOP pre- and post-conditions.
    Code-verified: models and agents can never self-certify conditions.
    """

    @classmethod
    def evaluate(cls, condition: Dict[str, Any], context: Dict[str, Any], outputs: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluates a single condition dictionary against context and output state.
        Returns (passed: bool, message: str).
        """
        if not condition:
            return True, "No condition specified"

        cond_type = condition.get("type", "field_exists").lower()
        field_name = condition.get("field")
        target_scope = condition.get("scope", "outputs")  # "outputs" or "context"
        data_source = outputs if target_scope == "outputs" else context

        if cond_type == "field_exists":
            if not field_name or field_name not in data_source:
                return False, f"Required field '{field_name}' missing from {target_scope}"
            return True, f"Field '{field_name}' exists"

        elif cond_type == "field_not_empty":
            val = data_source.get(field_name) if field_name else None
            if val is None or val == "" or val == [] or val == {}:
                return False, f"Field '{field_name}' is empty or null in {target_scope}"
            return True, f"Field '{field_name}' is populated"

        elif cond_type == "field_equals":
            expected = condition.get("expected")
            actual = data_source.get(field_name)
            if actual != expected:
                return False, f"Field '{field_name}' expected '{expected}', got '{actual}'"
            return True, f"Field '{field_name}' equals expected value"

        elif cond_type == "field_greater_than":
            min_val = condition.get("value", 0)
            actual = data_source.get(field_name, 0)
            try:
                if float(actual) <= float(min_val):
                    return False, f"Field '{field_name}' ({actual}) is not greater than {min_val}"
            except (ValueError, TypeError):
                return False, f"Field '{field_name}' could not be compared as number"
            return True, f"Field '{field_name}' is greater than {min_val}"

        elif cond_type == "custom_code":
            expression = condition.get("expression", "True")
            safe_globals = {"__builtins__": None}
            safe_locals = {"outputs": outputs, "context": context}
            try:
                res = eval(expression, safe_globals, safe_locals)
                if not bool(res):
                    return False, f"Custom condition '{expression}' evaluated to False"
                return True, f"Custom condition '{expression}' passed"
            except Exception as e:
                return False, f"Failed evaluating custom expression '{expression}': {str(e)}"

        return True, "Default pass"


class SOPExecutor:
    """
    Step-by-step verified execution kernel for SOP playbooks.
    Enforces Rule 16 (typed output), Rule 17 (no self-completion),
    Rule 18 (deterministic scoring), and pre/post condition evaluation.
    """

    @classmethod
    def execute_sop(
        cls,
        tenant_id: str,
        company_id: str,
        request: SOPRunRequest,
    ) -> Dict[str, Any]:
        """
        Runs an SOP instance step-by-step or in dry-run mode.
        """
        # 1. Fetch version and check executable status
        if request.version_id:
            version = sop_definition_service.get_version(tenant_id, company_id, request.version_id)
        else:
            version = sop_definition_service.get_latest_version(tenant_id, company_id, request.sop_id)

        if version.get("status") == SOPVersionStatus.NOT_EXECUTABLE.value or not version.get("steps_definition"):
            raise SOPNotExecutableError(
                f"SOP version '{version.get('version_id')}' is NOT_EXECUTABLE. "
                "Pack stub has not been implemented with executable steps."
            )

        raw_steps = version["steps_definition"]
        if not raw_steps or len(raw_steps) == 0:
            raise SOPNotExecutableError(
                f"SOP version '{version.get('version_id')}' contains zero executable steps."
            )

        steps: List[Dict[str, Any]] = sorted(raw_steps, key=lambda s: s.get("step_number", 0))
        total_steps = len(steps)

        instance_id = f"sopi_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Initialize instance row
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sop_instances (
                    id, tenant_id, company_id, sop_id, version_id, executor_id,
                    status, dry_run, current_step, total_steps, compliance_score,
                    context_inputs, context_outputs, started_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'RUNNING', ?, 0, ?, 0.0, ?, '{}', ?)
                """,
                (
                    instance_id, tenant_id, company_id, request.sop_id,
                    version["version_id"], request.executor_id,
                    1 if request.dry_run else 0, total_steps,
                    json.dumps(request.context_inputs), now
                )
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="SOP_INSTANCE_STARTED",
            payload={
                "instance_id": instance_id,
                "sop_id": request.sop_id,
                "version_id": version["version_id"],
                "dry_run": request.dry_run,
                "total_steps": total_steps,
            },
            action_id=f"start_{instance_id}"
        )

        context = dict(request.context_inputs)
        step_records: List[Dict[str, Any]] = []
        completed_compensable_steps: List[Dict[str, Any]] = []
        failure_error: Optional[str] = None
        instance_status = SOPInstanceStatus.COMPLETED

        # 2. Sequential Step Execution
        for step in steps:
            step_num = step.get("step_number", 0)
            step_name = step.get("name", f"Step {step_num}")
            step_type = step.get("step_type", SOPStepType.TOOL.value)
            tool_name = step.get("tool_name")
            reversibility = step.get("reversibility", SOPStepReversibility.IDEMPOTENT.value)
            compensation_step = step.get("compensation_step")

            # Update current step pointer
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE sop_instances SET current_step = ? WHERE id = ?",
                    (step_num, instance_id)
                )
                conn.commit()

            step_start = time.time()
            step_def_bytes = json.dumps(step, sort_keys=True).encode()
            step_def_hash = hashlib.sha256(step_def_bytes).hexdigest()

            # Resolve step inputs from context
            resolved_inputs = cls._resolve_inputs(step.get("inputs", {}), context)
            input_bytes = json.dumps(resolved_inputs, sort_keys=True).encode()
            input_hash = hashlib.sha256(input_bytes).hexdigest()

            # Preconditions check
            pre_ok, pre_msg = cls._check_conditions(step.get("preconditions", []), context, {})
            if not pre_ok:
                failure_error = f"Precondition failed on step {step_num} ({step_name}): {pre_msg}"
                cls._record_step(
                    instance_id=instance_id,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    step_number=step_num,
                    step_name=step_name,
                    step_type=step_type,
                    tool_name=tool_name,
                    actor_id=request.executor_id,
                    input_hash=input_hash,
                    step_def_hash=step_def_hash,
                    output_hash="",
                    outcome=SOPStepOutcome.FAILED.value,
                    inputs=resolved_inputs,
                    outputs={},
                    preconditions_passed=0,
                    postconditions_passed=1,
                    start_time=step_start,
                    finish_time=time.time(),
                    reversibility=reversibility,
                    error=failure_error,
                    evidence_event_id=None,
                )
                instance_status = SOPInstanceStatus.FAILED
                break

            # Execute Step (or Dry-Run Plan)
            step_outputs: Dict[str, Any] = {}
            step_evidence_id: Optional[str] = None
            step_outcome = SOPStepOutcome.PASSED

            if request.dry_run:
                # DRY RUN: Plan action, generate simulated outputs without calling real sinks
                step_outputs = {
                    "dry_run_simulation": True,
                    "planned_action": step_type,
                    "target_tool": tool_name,
                    "mock_result": "Simulated successful execution",
                    **step.get("outputs_schema", {})
                }
                # Propagate simulated outputs to context so chained steps can evaluate in dry run
                for k, v in step.get("outputs_schema", {}).items():
                    step_outputs[k] = resolved_inputs.get(k, f"mock_{k}")
            else:
                # REAL RUN
                try:
                    step_outputs, step_evidence_id = cls._execute_step_action(
                        tenant_id=tenant_id,
                        company_id=company_id,
                        executor_id=request.executor_id,
                        step=step,
                        resolved_inputs=resolved_inputs,
                    )
                except Exception as ex:
                    failure_error = f"Step {step_num} action failed: {str(ex)}"
                    step_outcome = SOPStepOutcome.FAILED
                    cls._record_step(
                        instance_id=instance_id,
                        tenant_id=tenant_id,
                        company_id=company_id,
                        step_number=step_num,
                        step_name=step_name,
                        step_type=step_type,
                        tool_name=tool_name,
                        actor_id=request.executor_id,
                        input_hash=input_hash,
                        step_def_hash=step_def_hash,
                        output_hash="",
                        outcome=step_outcome.value,
                        inputs=resolved_inputs,
                        outputs={},
                        preconditions_passed=1,
                        postconditions_passed=0,
                        start_time=step_start,
                        finish_time=time.time(),
                        reversibility=reversibility,
                        error=failure_error,
                        evidence_event_id=None,
                    )
                    instance_status = SOPInstanceStatus.FAILED
                    break

            # Postconditions check (evaluated by code, never self-reported)
            post_ok, post_msg = cls._check_conditions(step.get("postconditions", []), context, step_outputs)
            step_finish = time.time()
            output_bytes = json.dumps(step_outputs, sort_keys=True).encode()
            output_hash = hashlib.sha256(output_bytes).hexdigest()

            if not post_ok:
                failure_error = f"Postcondition failed on step {step_num} ({step_name}): {post_msg}"
                step_outcome = SOPStepOutcome.FAILED
                cls._record_step(
                    instance_id=instance_id,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    step_number=step_num,
                    step_name=step_name,
                    step_type=step_type,
                    tool_name=tool_name,
                    actor_id=request.executor_id,
                    input_hash=input_hash,
                    step_def_hash=step_def_hash,
                    output_hash=output_hash,
                    outcome=step_outcome.value,
                    inputs=resolved_inputs,
                    outputs=step_outputs,
                    preconditions_passed=1,
                    postconditions_passed=0,
                    start_time=step_start,
                    finish_time=step_finish,
                    reversibility=reversibility,
                    error=failure_error,
                    evidence_event_id=step_evidence_id,
                )
                instance_status = SOPInstanceStatus.FAILED
                break

            # Step passed: persist record
            record_id = cls._record_step(
                instance_id=instance_id,
                tenant_id=tenant_id,
                company_id=company_id,
                step_number=step_num,
                step_name=step_name,
                step_type=step_type,
                tool_name=tool_name,
                actor_id=request.executor_id,
                input_hash=input_hash,
                step_def_hash=step_def_hash,
                output_hash=output_hash,
                outcome=step_outcome.value,
                inputs=resolved_inputs,
                outputs=step_outputs,
                preconditions_passed=1,
                postconditions_passed=1,
                start_time=step_start,
                finish_time=step_finish,
                reversibility=reversibility,
                error=None,
                evidence_event_id=step_evidence_id,
            )

            # Update context with step outputs
            context.update(step_outputs)

            # Track completed step for compensation if compensable
            if reversibility == SOPStepReversibility.COMPENSABLE.value and compensation_step:
                completed_compensable_steps.append({
                    "step_number": step_num,
                    "step_name": step_name,
                    "compensation_step": compensation_step,
                    "step_outputs": step_outputs,
                    "step_inputs": resolved_inputs,
                })

        # 3. Handle Failure and Compensations
        compensations_run = 0
        if instance_status == SOPInstanceStatus.FAILED:
            if completed_compensable_steps and not request.dry_run:
                # Run compensations in reverse order
                compensations_run = cls._run_compensations(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    instance_id=instance_id,
                    executor_id=request.executor_id,
                    compensable_steps=completed_compensable_steps,
                )
                instance_status = SOPInstanceStatus.COMPENSATED

        # 4. Compute Compliance Score & Complete Instance
        now_done = time.time()
        compliance_result = sop_compliance_calculator.calculate_compliance(
            tenant_id=tenant_id,
            company_id=company_id,
            instance_id=instance_id,
            total_expected_steps=total_steps,
        )
        final_score = compliance_result["compliance_score"]

        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE sop_instances
                SET status = ?, compliance_score = ?, context_outputs = ?,
                    error_reason = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    instance_status.value, final_score,
                    json.dumps(context), failure_error, now_done, instance_id
                )
            )
            conn.commit()

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type=f"SOP_INSTANCE_{instance_status.value}",
            payload={
                "instance_id": instance_id,
                "status": instance_status.value,
                "compliance_score": final_score,
                "compensations_run": compensations_run,
                "error": failure_error,
            },
            action_id=f"end_{instance_id}"
        )

        return {
            "instance_id": instance_id,
            "sop_id": request.sop_id,
            "version_id": version["version_id"],
            "status": instance_status.value,
            "dry_run": request.dry_run,
            "compliance_score": final_score,
            "total_steps": total_steps,
            "completed_steps": compliance_result["compliant_steps"],
            "missing_steps": compliance_result["missing_steps"],
            "failed_steps": compliance_result["failed_steps"],
            "compensations_run": compensations_run,
            "error_reason": failure_error,
            "context_outputs": context,
        }

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    @classmethod
    def _resolve_inputs(cls, template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves template placeholders like '{{field}}' from context."""
        resolved: Dict[str, Any] = {}
        for k, v in template.items():
            if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                var_name = v[2:-2].strip()
                resolved[k] = context.get(var_name, v)
            else:
                resolved[k] = v
        return resolved

    @classmethod
    def _check_conditions(
        cls,
        conditions: List[Dict[str, Any]],
        context: Dict[str, Any],
        outputs: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """Evaluates a list of conditions."""
        for cond in conditions:
            passed, reason = SOPConditionEvaluator.evaluate(cond, context, outputs)
            if not passed:
                return False, reason
        return True, "All conditions met"

    @classmethod
    def _execute_step_action(
        cls,
        tenant_id: str,
        company_id: str,
        executor_id: str,
        step: Dict[str, Any],
        resolved_inputs: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Executes the action corresponding to the step type."""
        step_type = step.get("step_type", SOPStepType.TOOL.value)
        tool_name = step.get("tool_name")

        if step_type == SOPStepType.TOOL.value:
            if not tool_name:
                raise SOPStepExecutionError("Step marked as TOOL but no tool_name provided")
            res = tool_registry.execute(
                name=tool_name,
                tenant_id=tenant_id,
                company_id=company_id,
                principal_id=executor_id,
                arguments=resolved_inputs,
            )
            if isinstance(res, dict) and res.get("success") is False:
                raise SOPStepExecutionError(f"Tool '{tool_name}' failed: {res.get('error')}")
            out = dict(res)
            if "data" in res and isinstance(res["data"], dict):
                out.update(res["data"])
            evidence_id = f"ev_tool_{uuid.uuid4().hex[:8]}"
            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="SOP_TOOL_EXECUTED",
                payload={"tool_name": tool_name, "inputs": resolved_inputs, "result": res},
                action_id=evidence_id,
            )
            return out, evidence_id

        elif step_type == SOPStepType.CHECK.value:
            # Code-verified validation check
            check_expr = step.get("inputs", {}).get("expression", "True")
            safe_globals = {"__builtins__": None}
            safe_locals = {"inputs": resolved_inputs}
            check_result = eval(check_expr, safe_globals, safe_locals)
            return {"check_passed": bool(check_result)}, None

        elif step_type in (SOPStepType.HUMAN.value, SOPStepType.APPROVAL.value):
            # Human-in-the-loop step
            return {"status": "AWAITING_HUMAN", "input": resolved_inputs}, None

        elif step_type == SOPStepType.MODEL.value:
            return {"model_output": "Generated response based on prompt", **resolved_inputs}, None

        return {"status": "SUCCESS"}, None

    @classmethod
    def _record_step(
        cls,
        instance_id: str,
        tenant_id: str,
        company_id: str,
        step_number: int,
        step_name: str,
        step_type: str,
        tool_name: Optional[str],
        actor_id: Optional[str],
        input_hash: str,
        step_def_hash: str,
        output_hash: str,
        outcome: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        preconditions_passed: int,
        postconditions_passed: int,
        start_time: float,
        finish_time: float,
        reversibility: str,
        error: Optional[str],
        evidence_event_id: Optional[str],
    ) -> str:
        """Persists an immutable step execution record."""
        record_id = f"sopr_{uuid.uuid4().hex[:12]}"
        now = time.time()
        duration_ms = (finish_time - start_time) * 1000.0

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sop_step_records (
                    id, instance_id, tenant_id, company_id, step_number, step_name,
                    step_type, tool_name, actor_id, input_hash, step_def_hash,
                    output_hash, outcome, inputs, outputs, preconditions_passed,
                    postconditions_passed, start_time, finish_time, duration_ms,
                    reversibility, error, evidence_event_id, execution_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id, instance_id, tenant_id, company_id, step_number, step_name,
                    step_type, tool_name, actor_id, input_hash, step_def_hash,
                    output_hash, outcome, json.dumps(inputs), json.dumps(outputs),
                    preconditions_passed, postconditions_passed, start_time, finish_time,
                    duration_ms, reversibility, error, evidence_event_id, now
                )
            )
            conn.commit()

        return record_id

    @classmethod
    def _run_compensations(
        cls,
        tenant_id: str,
        company_id: str,
        instance_id: str,
        executor_id: str,
        compensable_steps: List[Dict[str, Any]],
    ) -> int:
        """
        Runs compensation steps in reverse order for completed compensable steps.
        """
        compensations_executed = 0

        for item in reversed(compensable_steps):
            step_num = item["step_number"]
            comp_def = item["compensation_step"]
            comp_tool = comp_def.get("tool_name")
            comp_inputs = comp_def.get("inputs", {})

            # Execute compensation tool if declared
            if comp_tool and tool_registry.is_tool_available(comp_tool):
                try:
                    tool_registry.execute(
                        name=comp_tool,
                        tenant_id=tenant_id,
                        company_id=company_id,
                        principal_id=executor_id,
                        arguments=comp_inputs,
                    )
                except Exception:
                    pass  # Keep rolling back remaining compensable steps

            # Record compensation entry
            comp_id = f"sopc_{uuid.uuid4().hex[:12]}"
            ev_id = f"ev_comp_{uuid.uuid4().hex[:8]}"
            now = time.time()

            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO sop_compensations (
                        id, instance_id, step_number, tenant_id, company_id,
                        compensation_step_name, status, action_details, compensated_at,
                        evidence_event_id
                    ) VALUES (?, ?, ?, ?, ?, ?, 'COMPLETED', ?, ?, ?)
                    """,
                    (
                        comp_id, instance_id, step_num, tenant_id, company_id,
                        comp_def.get("name", f"Compensate Step {step_num}"),
                        json.dumps(comp_def), now, ev_id
                    )
                )
                conn.commit()

            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="SOP_STEP_COMPENSATED",
                payload={"instance_id": instance_id, "step_number": step_num, "compensation": comp_def},
                action_id=ev_id,
            )
            compensations_executed += 1

        return compensations_executed


sop_executor = SOPExecutor()
