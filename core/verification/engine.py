"""
ZONATA Verification Pyramid Engine
OpenCode Step 2H: Five-layer verification engine, recipe registry, and spot check router.
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, Any, List, Optional

from core.db import db, tenant_scoped_class
from core.evidence_service import evidence_service
from core.work.service import workforce_work_service
from core.work.types import TaskStatus, AssigneeSelfCompletionForbiddenError
from core.verification.types import (
    VerificationLayer,
    VerificationStatus,
    LayerResultStatus,
    VerificationLayerResult,
    VerificationReport,
    VerificationRecipe,
    VerificationError,
    IncompleteVerificationError,
    UnauthorizedLayerInvokerError,
)
from core.verification.layers import (
    SchemaVerificationLayer,
    DeterministicCodeVerificationLayer,
    CrossRecordVerificationLayer,
    PeerModelVerificationLayer,
    HumanVerificationLayer,
)
from core.verification.sampling import SpotCheckSampler


@tenant_scoped_class
class VerificationEngine:
    """
    Five-layer progressive verification engine enforcing Rule 17.
    A task claiming 'done' is merely a claim; completion requires passing the verification recipe.
    """

    _recipes: Dict[str, VerificationRecipe] = {}

    @classmethod
    def register_recipe(
        cls,
        task_type: str,
        required_layers: List[VerificationLayer],
        layer_configs: Optional[Dict[str, Any]] = None,
    ) -> VerificationRecipe:
        """Registers a verification recipe for a specific task type."""
        recipe = VerificationRecipe(
            task_type=task_type,
            required_layers=required_layers,
            layer_configs=layer_configs or {},
        )
        cls._recipes[task_type] = recipe
        return recipe

    @classmethod
    def get_recipe(cls, task_type: str) -> VerificationRecipe:
        """Retrieves recipe for a task type, falling back to standard 2-layer recipe."""
        if task_type in cls._recipes:
            return cls._recipes[task_type]
        # Default baseline: Schema and Deterministic Code verification
        return VerificationRecipe(
            task_type=task_type,
            required_layers=[VerificationLayer.SCHEMA, VerificationLayer.DETERMINISTIC_CODE],
            layer_configs={},
        )

    @classmethod
    def verify_task(
        cls,
        tenant_id: str,
        company_id: str,
        task_id: str,
        invoker_id: str,
        submission_data: Dict[str, Any],
        task_type: Optional[str] = None,
        spot_check_rates: Optional[Dict[str, float]] = None,
        recipe_override: Optional[List[VerificationLayer]] = None,
    ) -> VerificationReport:
        """
        Executes progressive verification across required layers.
        Enforces Rule 17: Assignee can NEVER self-complete.
        """
        task = workforce_work_service.get_task(tenant_id, company_id, task_id)
        assignee_id = task.get("assignee_id")
        current_status = TaskStatus(task["status"])

        # Rule 17 Guard: Assignee cannot complete its own task
        if invoker_id == assignee_id:
            raise AssigneeSelfCompletionForbiddenError(
                f"Rule 17: Assignee '{assignee_id}' cannot invoke verification to self-complete task '{task_id}'."
            )

        # Transition task to VERIFYING if currently SUBMITTED
        if current_status == TaskStatus.SUBMITTED:
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE work_tasks SET status = 'VERIFYING', updated_at = ? WHERE id = ?",
                    (time.time(), task_id)
                )
                conn.commit()
            task["status"] = "VERIFYING"

        acc_criteria = task.get("acceptance_criteria") or {}
        if isinstance(acc_criteria, str):
            try:
                acc_criteria = json.loads(acc_criteria)
            except Exception:
                acc_criteria = {}

        resolved_task_type = task_type or task.get("task_type") or acc_criteria.get("task_type", "DEFAULT")
        base_recipe = cls.get_recipe(resolved_task_type)
        required_layers = recipe_override if recipe_override is not None else base_recipe.required_layers
        layer_configs = base_recipe.layer_configs

        verification_id = f"ver_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Persist verification session
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO task_verifications (
                    id, tenant_id, company_id, task_id, overall_status,
                    required_layers, current_layer, is_spot_check, created_at
                ) VALUES (?, ?, ?, ?, 'IN_PROGRESS', ?, ?, 0, ?)
                """,
                (
                    verification_id, tenant_id, company_id, task_id,
                    json.dumps([l.value for l in required_layers]),
                    required_layers[0].value if required_layers else None,
                    now
                )
            )
            conn.commit()

        passed_layers: List[VerificationLayer] = []
        layer_results: List[VerificationLayerResult] = []
        failing_layer: Optional[VerificationLayer] = None
        rejection_reason: Optional[str] = None
        is_spot_check = False

        layer_evaluators = {
            VerificationLayer.SCHEMA: SchemaVerificationLayer,
            VerificationLayer.DETERMINISTIC_CODE: DeterministicCodeVerificationLayer,
            VerificationLayer.CROSS_RECORD: CrossRecordVerificationLayer,
            VerificationLayer.PEER_MODEL: PeerModelVerificationLayer,
            VerificationLayer.HUMAN: HumanVerificationLayer,
        }

        # 1. Evaluate Required Layers in Progressive Order
        for layer in required_layers:
            evaluator = layer_evaluators[layer]
            config = layer_configs.get(layer.value, {})

            # Update current layer in DB
            with db.get_connection() as conn:
                conn.execute(
                    "UPDATE task_verifications SET current_layer = ? WHERE id = ?",
                    (layer.value, verification_id)
                )
                conn.commit()

            result = evaluator.evaluate(
                tenant_id=tenant_id,
                company_id=company_id,
                task=task,
                invoker_id=invoker_id,
                submission_data=submission_data,
                config=config,
            )
            layer_results.append(result)
            cls._record_layer_result(tenant_id, company_id, verification_id, task_id, invoker_id, result)

            if result.status == LayerResultStatus.FAILED:
                failing_layer = layer
                rejection_reason = f"[{result.rule_name}] {result.error_message}" if result.rule_name else (result.error_message or "Failed")
                break
            elif result.status == LayerResultStatus.SKIPPED:
                # E.g. Awaiting Human Inbox Review
                with db.get_connection() as conn:
                    conn.execute(
                        "UPDATE task_verifications SET overall_status = 'PENDING' WHERE id = ?",
                        (verification_id,)
                    )
                    conn.commit()
                return VerificationReport(
                    verification_id=verification_id,
                    task_id=task_id,
                    overall_status=VerificationStatus.PENDING,
                    required_layers=required_layers,
                    passed_layers=passed_layers,
                    failing_layer=None,
                    rejection_reason="Awaiting asynchronous review (e.g. Human Inbox)",
                    layer_results=layer_results,
                    is_spot_check=False,
                )
            else:
                passed_layers.append(layer)

        # 2. Handle Layer Failure
        if failing_layer:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    UPDATE task_verifications
                    SET overall_status = 'FAILED', failing_layer = ?, rejection_reason = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (failing_layer.value, rejection_reason, time.time(), verification_id)
                )
                # Re-route task back to ASSIGNED with rejection logged
                conn.execute(
                    "UPDATE work_tasks SET status = 'ASSIGNED', updated_at = ? WHERE id = ?",
                    (time.time(), task_id)
                )
                conn.commit()

            evidence_service.record_event(
                tenant_id=tenant_id,
                company_id=company_id,
                event_type="TASK_VERIFICATION_REJECTED",
                payload={
                    "task_id": task_id,
                    "verification_id": verification_id,
                    "failing_layer": failing_layer.value,
                    "rejection_reason": rejection_reason,
                    "re_routed_to": "ASSIGNED",
                },
                action_id=f"rej_{verification_id}"
            )

            return VerificationReport(
                verification_id=verification_id,
                task_id=task_id,
                overall_status=VerificationStatus.FAILED,
                required_layers=required_layers,
                passed_layers=passed_layers,
                failing_layer=failing_layer,
                rejection_reason=rejection_reason,
                layer_results=layer_results,
                is_spot_check=False,
            )

        # 3. Spot Check Sampling for Higher Layers
        spot_rates = spot_check_rates or {}
        rate_l4 = spot_rates.get("PEER_MODEL", 0.0)
        rate_l5 = spot_rates.get("HUMAN", 0.0)

        # Spot check for Layer 4 (Peer Model) if not already required
        if VerificationLayer.PEER_MODEL not in required_layers and rate_l4 > 0.0:
            if SpotCheckSampler.is_sampled(task_id, VerificationLayer.PEER_MODEL, rate_l4):
                is_spot_check = True
                l4_result = PeerModelVerificationLayer.evaluate(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    task=task,
                    invoker_id="system_verifier",
                    submission_data=submission_data,
                    config=layer_configs.get(VerificationLayer.PEER_MODEL.value, {}),
                )
                layer_results.append(l4_result)
                cls._record_layer_result(tenant_id, company_id, verification_id, task_id, "system_verifier", l4_result)
                if l4_result.status == LayerResultStatus.FAILED:
                    failing_layer = VerificationLayer.PEER_MODEL
                    rejection_reason = l4_result.error_message
                    cls._fail_verification(tenant_id, company_id, verification_id, task_id, failing_layer, rejection_reason)
                    return VerificationReport(
                        verification_id=verification_id,
                        task_id=task_id,
                        overall_status=VerificationStatus.FAILED,
                        required_layers=required_layers,
                        passed_layers=passed_layers,
                        failing_layer=failing_layer,
                        rejection_reason=rejection_reason,
                        layer_results=layer_results,
                        is_spot_check=True,
                    )
                passed_layers.append(VerificationLayer.PEER_MODEL)

        # Spot check for Layer 5 (Human Review) if not already required
        if VerificationLayer.HUMAN not in required_layers and rate_l5 > 0.0:
            if SpotCheckSampler.is_sampled(task_id, VerificationLayer.HUMAN, rate_l5):
                is_spot_check = True
                l5_result = HumanVerificationLayer.evaluate(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    task=task,
                    invoker_id="system_verifier",
                    submission_data=submission_data,
                    config=layer_configs.get(VerificationLayer.HUMAN.value, {}),
                )
                layer_results.append(l5_result)
                cls._record_layer_result(tenant_id, company_id, verification_id, task_id, "system_verifier", l5_result)
                if l5_result.status != LayerResultStatus.PASSED:
                    # Awaiting human
                    with db.get_connection() as conn:
                        conn.execute(
                            "UPDATE task_verifications SET overall_status = 'PENDING', is_spot_check = 1 WHERE id = ?",
                            (verification_id,)
                        )
                        conn.commit()
                    return VerificationReport(
                        verification_id=verification_id,
                        task_id=task_id,
                        overall_status=VerificationStatus.PENDING,
                        required_layers=required_layers,
                        passed_layers=passed_layers,
                        failing_layer=None,
                        rejection_reason="Sampled for Human Review via Spot Check",
                        layer_results=layer_results,
                        is_spot_check=True,
                    )
                passed_layers.append(VerificationLayer.HUMAN)

        # 4. All Layers Passed: Formally Mark Task COMPLETED
        now_done = time.time()
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE task_verifications
                SET overall_status = 'PASSED', is_spot_check = ?, completed_at = ?
                WHERE id = ?
                """,
                (1 if is_spot_check else 0, now_done, verification_id)
            )
            conn.commit()

        # Complete task in workforce work service
        workforce_work_service.verify_task(
            tenant_id=tenant_id,
            company_id=company_id,
            task_id=task_id,
            decision="APPROVED",
            verifier_id=invoker_id,
            verification_report_id=verification_id,
            reason="All progressive verification pyramid layers passed successfully."
        )

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="TASK_VERIFICATION_PASSED",
            payload={
                "task_id": task_id,
                "verification_id": verification_id,
                "passed_layers": [l.value for l in passed_layers],
                "is_spot_check": is_spot_check,
            },
            action_id=f"pass_{verification_id}"
        )

        return VerificationReport(
            verification_id=verification_id,
            task_id=task_id,
            overall_status=VerificationStatus.PASSED,
            required_layers=required_layers,
            passed_layers=passed_layers,
            failing_layer=None,
            rejection_reason=None,
            layer_results=layer_results,
            is_spot_check=is_spot_check,
        )

    @classmethod
    def _record_layer_result(
        cls,
        tenant_id: str,
        company_id: str,
        verification_id: str,
        task_id: str,
        invoker_id: str,
        result: VerificationLayerResult,
    ) -> str:
        """Persists layer evaluation result."""
        res_id = f"vlr_{uuid.uuid4().hex[:12]}"
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO verification_layer_results (
                    id, verification_id, tenant_id, company_id, task_id, layer,
                    invoker_id, status, rule_name, observed_value, expected_value,
                    scorecard, evidence_pointers, error_message, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res_id, verification_id, tenant_id, company_id, task_id,
                    result.layer.value, invoker_id, result.status.value,
                    result.rule_name, result.observed_value, result.expected_value,
                    json.dumps(result.scorecard), json.dumps(result.evidence_pointers),
                    result.error_message, result.evaluated_at
                )
            )
            conn.commit()
        return res_id

    @classmethod
    def _fail_verification(
        cls,
        tenant_id: str,
        company_id: str,
        verification_id: str,
        task_id: str,
        failing_layer: VerificationLayer,
        reason: Optional[str],
    ) -> None:
        """Helper to mark verification and task as failed/routed back."""
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE task_verifications
                SET overall_status = 'FAILED', failing_layer = ?, rejection_reason = ?, completed_at = ?
                WHERE id = ?
                """,
                (failing_layer.value, reason, time.time(), verification_id)
            )
            conn.execute(
                "UPDATE work_tasks SET status = 'ASSIGNED', updated_at = ? WHERE id = ?",
                (time.time(), task_id)
            )
            conn.commit()


verification_engine = VerificationEngine()
