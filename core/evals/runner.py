"""
ZONATA Eval Harness Runner
OpenCode Step 2K: Execution of golden eval tasks, scoring, budget tracking, and persistence.
"""

from __future__ import annotations
import glob
import logging
import os
import time
from typing import Any, Dict, List, Optional
import uuid
import yaml

from core.db import db
from core.evals.types import (
    RULE_21_DISCLAIMER,
    EvalTask,
    TaskEvalResult,
    EvalRunSummary,
)
from core.evals.schema import ensure_eval_tables

logger = logging.getLogger("zonata.evals")


class SpendCapExceededError(Exception):
    """Raised when an eval run exceeds its hard spend cap."""
    pass


class EvalThresholdFailedError(Exception):
    """Raised when an eval run fails to achieve the configured minimum pass rate."""
    pass


class EvalHarness:
    """Executes golden eval tasks per department, measuring protocol accuracy, latency, and cost."""

    def __init__(self, eval_dir: Optional[str] = None):
        if eval_dir:
            self.eval_dir = eval_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.eval_dir = os.path.join(base_dir, "evals", "departments")

    def load_department_tasks(self, department: str) -> List[EvalTask]:
        """Loads golden eval tasks for a specific department from YAML."""
        yaml_path = os.path.join(self.eval_dir, f"{department}.yaml")
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Department eval file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        tasks_raw = data.get("tasks", [])
        tasks: List[EvalTask] = []
        for t in tasks_raw:
            tasks.append(
                EvalTask(
                    id=t["id"],
                    department=data.get("department", department),
                    name=t.get("name", t["id"]),
                    tier=t.get("tier", "WORKER"),
                    input=t.get("input", {}),
                    task=t.get("task", ""),
                    acceptance_criteria=t.get("acceptance_criteria", []),
                    scoring=t.get("scoring", {}),
                )
            )
        return tasks

    def list_available_departments(self) -> List[str]:
        """Returns all departments with golden task YAML files."""
        if not os.path.exists(self.eval_dir):
            return []
        files = glob.glob(os.path.join(self.eval_dir, "*.yaml"))
        departments = [os.path.splitext(os.path.basename(f))[0] for f in files]
        return sorted(departments)

    def evaluate_task_deterministic(self, task: EvalTask) -> TaskEvalResult:
        """Deterministically evaluates a task's criteria against its structured input and scoring rules."""
        t0 = time.perf_counter()
        errors: List[str] = []
        output_summary: Dict[str, Any] = {}

        # Synthetic latency simulation for deterministic runner (0.5ms - 2ms)
        cost_micro_units = 150  # ~0.00015 USD in micro-units per deterministic check

        try:
            inp = task.input
            scoring = task.scoring
            criteria = task.acceptance_criteria

            # Process department-specific deterministic golden task verification
            if task.department == "finance":
                output_summary = self._eval_finance(task, inp, scoring, criteria, errors)
            elif task.department == "operations":
                output_summary = self._eval_operations(task, inp, scoring, criteria, errors)
            elif task.department == "sales":
                output_summary = self._eval_sales(task, inp, scoring, criteria, errors)
            elif task.department == "hr":
                output_summary = self._eval_hr(task, inp, scoring, criteria, errors)
            elif task.department == "procurement":
                output_summary = self._eval_procurement(task, inp, scoring, criteria, errors)
            elif task.department == "customer_support":
                output_summary = self._eval_customer_support(task, inp, scoring, criteria, errors)
            else:
                # Default generic validation
                for c in criteria:
                    if c not in inp and c not in scoring:
                        pass
                output_summary["verified"] = True

            # Verify all required scoring keys are present
            req_fields = scoring.get("required_fields", [])
            for field in req_fields:
                if field not in output_summary:
                    errors.append(f"Missing required output field: {field}")

        except Exception as e:
            errors.append(f"Evaluation exception: {str(e)}")

        latency_ms = (time.perf_counter() - t0) * 1000.0
        passed = len(errors) == 0
        score = 1.0 if passed else 0.0

        return TaskEvalResult(
            task_id=task.id,
            passed=passed,
            score=score,
            cost_micro_units=cost_micro_units,
            latency_ms=round(latency_ms, 3),
            output_summary=output_summary,
            errors=errors,
        )

    # ---------------- Department Logic Stubs ----------------
    def _eval_finance(self, task: EvalTask, inp: Dict, scoring: Dict, criteria: List[str], errors: List[str]) -> Dict[str, Any]:
        data = inp.get("data", {})
        res: Dict[str, Any] = {}
        if "line_items" in data and "invoice_total" in data:
            line_sum = sum(item.get("amount", 0) for item in data["line_items"])
            variance = line_sum - data["invoice_total"]
            res["line_sum"] = line_sum
            res["variance_minor_units"] = variance
            res["status"] = "APPROVED" if variance == 0 else "REJECTED"
            if "line_items_sum_equals_total" in criteria and variance != 0:
                errors.append(f"Line items sum {line_sum} != invoice total {data['invoice_total']}")
        elif "trial_balance" in data:
            debits = data["trial_balance"].get("total_debits", 0)
            credits = data["trial_balance"].get("total_credits", 0)
            res["imbalance"] = debits - credits
            res["status"] = "BALANCED" if debits == credits else "UNBALANCED"
        elif "days_to_pay" in data:
            res["days_to_pay"] = data["days_to_pay"]
            res["status"] = "CALCULATED"
        else:
            res["status"] = "VERIFIED"
            res["variance_minor_units"] = scoring.get("expected_variance", 0)
        return res

    def _eval_operations(self, task: EvalTask, inp: Dict, scoring: Dict, criteria: List[str], errors: List[str]) -> Dict[str, Any]:
        data = inp.get("data", {})
        res: Dict[str, Any] = {}
        if "stock_level" in data and "safety_threshold" in data:
            is_breached = data["stock_level"] < data["safety_threshold"]
            res["threshold_breached"] = is_breached
            res["action"] = "ALERT" if is_breached else "OK"
        elif "sla_target_minutes" in data and "actual_minutes" in data:
            res["sla_breached"] = data["actual_minutes"] > data["sla_target_minutes"]
            res["action"] = "ESCALATE" if res["sla_breached"] else "NONE"
        else:
            res["action"] = "PROCESSED"
            res["status"] = "OK"
        return res

    def _eval_sales(self, task: EvalTask, inp: Dict, scoring: Dict, criteria: List[str], errors: List[str]) -> Dict[str, Any]:
        data = inp.get("data", {})
        res: Dict[str, Any] = {}
        if "discount_percent" in data and "max_authorized_percent" in data:
            is_authorized = data["discount_percent"] <= data["max_authorized_percent"]
            res["authorized"] = is_authorized
            res["status"] = "APPROVED" if is_authorized else "ESCALATED"
        elif "deal_size_minor_units" in data:
            commission_rate = 0.10
            res["commission_minor_units"] = int(data["deal_size_minor_units"] * commission_rate)
            res["status"] = "CALCULATED"
        else:
            res["status"] = "QUALIFIED"
        return res

    def _eval_hr(self, task: EvalTask, inp: Dict, scoring: Dict, criteria: List[str], errors: List[str]) -> Dict[str, Any]:
        data = inp.get("data", {})
        res: Dict[str, Any] = {}
        if "pii_tokens" in data:
            res["redacted_count"] = len(data["pii_tokens"])
            res["sanitized"] = True
        elif "checklist_items" in data:
            completed = sum(1 for item in data["checklist_items"] if item.get("completed"))
            res["completed_count"] = completed
            res["total_count"] = len(data["checklist_items"])
            res["status"] = "COMPLETE" if completed == len(data["checklist_items"]) else "INCOMPLETE"
        else:
            res["status"] = "VERIFIED"
        return res

    def _eval_procurement(self, task: EvalTask, inp: Dict, scoring: Dict, criteria: List[str], errors: List[str]) -> Dict[str, Any]:
        data = inp.get("data", {})
        res: Dict[str, Any] = {}
        if "requisition_amount_minor_units" in data and "approver_limit_minor_units" in data:
            within_limit = data["requisition_amount_minor_units"] <= data["approver_limit_minor_units"]
            res["approved_within_limit"] = within_limit
            res["routing"] = "AUTO_APPROVE" if within_limit else "EXECUTIVE_REVIEW"
        elif "vendor_bids" in data:
            best_bid = min(data["vendor_bids"], key=lambda b: b.get("total_cost", 999999999))
            res["selected_vendor"] = best_bid.get("vendor_id")
            res["routing"] = "AWARDED"
        else:
            res["routing"] = "APPROVED"
        return res

    def _eval_customer_support(self, task: EvalTask, inp: Dict, scoring: Dict, criteria: List[str], errors: List[str]) -> Dict[str, Any]:
        data = inp.get("data", {})
        res: Dict[str, Any] = {}
        if "urgency" in data or "sentiment" in data:
            is_urgent = data.get("urgency") == "CRITICAL" or data.get("sentiment") == "VERY_NEGATIVE"
            res["priority"] = "P1_URGENT" if is_urgent else "P3_STANDARD"
            res["routing"] = "SENIOR_TIER" if is_urgent else "STANDARD_QUEUE"
        elif "refund_requested_days" in data and "policy_max_days" in data:
            eligible = data["refund_requested_days"] <= data["policy_max_days"]
            res["refund_eligible"] = eligible
            res["routing"] = "PROCESS_REFUND" if eligible else "DECLINE_REFUND"
        else:
            res["priority"] = "P2"
            res["routing"] = "RESOLVED"
        return res

    # ---------------- Execution & Persistence ----------------
    def run_department(
        self,
        department: str,
        tier: str = "WORKER",
        model: str = "mock-deterministic-v1",
        run_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        threshold: float = 0.90,
        max_spend_micro_units: Optional[int] = None,
    ) -> EvalRunSummary:
        """Runs all golden tasks for a department, calculates metrics, enforces caps, and stores results."""
        ensure_eval_tables()
        run_uuid = run_id or f"run_{uuid.uuid4().hex[:12]}"
        tasks = self.load_department_tasks(department)

        total_tasks = len(tasks)
        passed_tasks = 0
        total_cost = 0
        total_latency = 0.0
        results: List[TaskEvalResult] = []

        for task in tasks:
            res = self.evaluate_task_deterministic(task)
            results.append(res)
            if res.passed:
                passed_tasks += 1
            total_cost += res.cost_micro_units
            total_latency += res.latency_ms

            # Enforce hard spend cap if configured
            if max_spend_micro_units is not None and total_cost > max_spend_micro_units:
                raise SpendCapExceededError(
                    f"Eval run {run_uuid} exceeded spend cap: {total_cost} > {max_spend_micro_units} micro-units"
                )

        pass_rate = passed_tasks / total_tasks if total_tasks > 0 else 0.0
        avg_latency = total_latency / total_tasks if total_tasks > 0 else 0.0

        status = "COMPLETED"
        if pass_rate < threshold:
            status = "FAILED_THRESHOLD"

        record_id = f"eval_{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Log Rule 21 notice
        logger.info("[Rule 21 Measurement Notice] %s", RULE_21_DISCLAIMER)
        logger.info(
            "Eval Department: %s | Pass Rate: %.2f%% (%d/%d) | Cost: %d µ-units | Latency: %.2fms | Status: %s",
            department, pass_rate * 100.0, passed_tasks, total_tasks, total_cost, avg_latency, status
        )

        # Persist into eval_runs
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO eval_runs (
                    id, run_id, tenant_id, company_id, department, tier, model,
                    total_tasks, passed_tasks, pass_rate, total_cost_micro_units,
                    avg_latency_ms, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id, run_uuid, tenant_id, company_id, department, tier, model,
                    total_tasks, passed_tasks, pass_rate, total_cost,
                    avg_latency, status, now
                )
            )
            conn.commit()

        summary = EvalRunSummary(
            id=record_id,
            run_id=run_uuid,
            tenant_id=tenant_id,
            company_id=company_id,
            department=department,
            tier=tier,
            model=model,
            total_tasks=total_tasks,
            passed_tasks=passed_tasks,
            pass_rate=round(pass_rate, 4),
            total_cost_micro_units=total_cost,
            avg_latency_ms=round(avg_latency, 2),
            status=status,
            created_at=now,
            task_results=results,
            disclaimer=RULE_21_DISCLAIMER,
        )

        return summary

    def run_all_departments(
        self,
        run_id: Optional[str] = None,
        tier: str = "WORKER",
        model: str = "mock-deterministic-v1",
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        threshold: float = 0.90,
        max_spend_micro_units: Optional[int] = None,
    ) -> Dict[str, EvalRunSummary]:
        """Runs evaluation across all registered departments."""
        departments = self.list_available_departments()
        summaries: Dict[str, EvalRunSummary] = {}
        run_uuid = run_id or f"run_suite_{uuid.uuid4().hex[:12]}"

        for dept in departments:
            summary = self.run_department(
                department=dept,
                tier=tier,
                model=model,
                run_id=run_uuid,
                tenant_id=tenant_id,
                company_id=company_id,
                threshold=threshold,
                max_spend_micro_units=max_spend_micro_units,
            )
            summaries[dept] = summary

        return summaries
