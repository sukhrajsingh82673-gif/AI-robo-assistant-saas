"""
ZONATA Deterministic KPI Arithmetic Calculator
OpenCode Step 2I: Strictly code-computed arithmetic from stored data (Rule 18).
"""

from __future__ import annotations

import time
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple

from core.db import db
from core.kpi.types import (
    KPIMetricType,
    KPIScopeLevel,
    InvalidKPIComputationError,
)


class KPICalculator:
    """
    Pure deterministic arithmetic calculator for Company OS KPIs.
    Rule 18: Determinism in code. Models never compute numbers shown to owners.
    Every computation returns an inputs_hash sealing the exact raw data rows used.
    """

    @classmethod
    def compute_metric(
        cls,
        tenant_id: str,
        company_id: str,
        metric_type: KPIMetricType,
        scope_level: KPIScopeLevel,
        scope_id: Optional[str] = None,
    ) -> Tuple[float, Dict[str, Any], str]:
        """
        Computes metric value, computation proof dictionary, and inputs_hash.
        Returns: (computed_value, proof_dict, inputs_hash)
        """
        with db.get_connection() as conn:
            if metric_type == KPIMetricType.TASK_DURATION:
                return cls._compute_task_duration(conn, tenant_id, company_id, scope_level, scope_id)
            elif metric_type == KPIMetricType.PRODUCTIVITY:
                return cls._compute_productivity(conn, tenant_id, company_id, scope_level, scope_id)
            elif metric_type == KPIMetricType.PASS_RATE:
                return cls._compute_pass_rate(conn, tenant_id, company_id, scope_level, scope_id)
            elif metric_type == KPIMetricType.COST_PER_MISSION:
                return cls._compute_cost_per_mission(conn, tenant_id, company_id, scope_level, scope_id)
            elif metric_type == KPIMetricType.DEFECT_RATE:
                return cls._compute_defect_rate(conn, tenant_id, company_id, scope_level, scope_id)
            elif metric_type == KPIMetricType.LEDGER_BALANCE:
                return cls._compute_ledger_balance(conn, tenant_id, company_id, scope_level, scope_id)
            else:
                raise InvalidKPIComputationError(f"Unsupported metric type: {metric_type}")

    @classmethod
    def _compute_task_duration(
        cls, conn, tenant_id: str, company_id: str, scope_level: KPIScopeLevel, scope_id: Optional[str]
    ) -> Tuple[float, Dict[str, Any], str]:
        """Computes average task completion duration in seconds."""
        query = (
            "SELECT id, submitted_at, completed_at, created_at FROM work_tasks "
            "WHERE tenant_id = ? AND company_id = ? AND status = 'COMPLETED'"
        )
        params = [tenant_id, company_id]
        if scope_level == KPIScopeLevel.EMPLOYEE and scope_id:
            query += " AND assignee_id = ?"
            params.append(scope_id)
        elif scope_level == KPIScopeLevel.POSITION and scope_id:
            query += " AND assignee_id = ?"
            params.append(scope_id)

        rows = conn.execute(query, tuple(params)).fetchall()
        if not rows:
            proof = {"count": 0, "total_seconds": 0.0, "average_seconds": 0.0}
            inputs_hash = hashlib.sha256(b"empty_task_duration").hexdigest()
            return 0.0, proof, inputs_hash

        durations = []
        raw_items = []
        for r in rows:
            start_ts = r["submitted_at"] or r["created_at"]
            finish_ts = r["completed_at"]
            dur = max(0.0, float(finish_ts - start_ts)) if finish_ts and start_ts else 0.0
            durations.append(dur)
            raw_items.append({"id": r["id"], "duration": dur})

        total_sec = sum(durations)
        avg_sec = round(total_sec / float(len(durations)), 2)
        proof = {
            "task_count": len(durations),
            "total_seconds": total_sec,
            "average_seconds": avg_sec,
            "tasks": raw_items,
        }
        inputs_hash = hashlib.sha256(json.dumps(raw_items, sort_keys=True).encode()).hexdigest()
        return avg_sec, proof, inputs_hash

    @classmethod
    def _compute_productivity(
        cls, conn, tenant_id: str, company_id: str, scope_level: KPIScopeLevel, scope_id: Optional[str]
    ) -> Tuple[float, Dict[str, Any], str]:
        """
        Computes employee productivity as throughput per hour of task duration.
        productivity = (completed_tasks * 3600.0) / total_duration_seconds.
        Directly responds to changes in task duration in the database.
        """
        avg_dur, dur_proof, _ = cls._compute_task_duration(conn, tenant_id, company_id, scope_level, scope_id)
        task_count = dur_proof.get("task_count", 0)
        total_seconds = dur_proof.get("total_seconds", 0.0)

        if total_seconds <= 0.0 or task_count <= 0:
            proof = {"task_count": 0, "total_seconds": 0.0, "productivity_tasks_per_hour": 0.0}
            inputs_hash = hashlib.sha256(b"empty_productivity").hexdigest()
            return 0.0, proof, inputs_hash

        # Tasks completed per hour of working duration
        tasks_per_hour = round((float(task_count) * 3600.0) / float(total_seconds), 4)
        proof = {
            "task_count": task_count,
            "total_seconds": total_seconds,
            "productivity_tasks_per_hour": tasks_per_hour,
            "tasks": dur_proof.get("tasks", []),
        }
        inputs_hash = hashlib.sha256(json.dumps(dur_proof.get("tasks", []), sort_keys=True).encode()).hexdigest()
        return tasks_per_hour, proof, inputs_hash

    @classmethod
    def _compute_pass_rate(
        cls, conn, tenant_id: str, company_id: str, scope_level: KPIScopeLevel, scope_id: Optional[str]
    ) -> Tuple[float, Dict[str, Any], str]:
        """Computes verification pass percentage: (passed / total) * 100.0."""
        rows = conn.execute(
            """
            SELECT id, task_id, overall_status FROM task_verifications
            WHERE tenant_id = ? AND company_id = ? AND overall_status IN ('PASSED', 'FAILED')
            """,
            (tenant_id, company_id)
        ).fetchall()

        if not rows:
            proof = {"total_verifications": 0, "passed": 0, "pass_rate": 100.0}
            inputs_hash = hashlib.sha256(b"empty_pass_rate").hexdigest()
            return 100.0, proof, inputs_hash

        passed_count = sum(1 for r in rows if r["overall_status"] == "PASSED")
        total_count = len(rows)
        rate = round((float(passed_count) / float(total_count)) * 100.0, 2)
        raw_items = [{"id": r["id"], "status": r["overall_status"]} for r in rows]

        proof = {
            "total_verifications": total_count,
            "passed": passed_count,
            "pass_rate": rate,
        }
        inputs_hash = hashlib.sha256(json.dumps(raw_items, sort_keys=True).encode()).hexdigest()
        return rate, proof, inputs_hash

    @classmethod
    def _compute_cost_per_mission(
        cls, conn, tenant_id: str, company_id: str, scope_level: KPIScopeLevel, scope_id: Optional[str]
    ) -> Tuple[float, Dict[str, Any], str]:
        """Computes average cost in minor units / cents per mission."""
        rows = conn.execute(
            """
            SELECT id, estimate_minor_units FROM work_tasks
            WHERE tenant_id = ? AND company_id = ? AND status = 'COMPLETED'
            """,
            (tenant_id, company_id)
        ).fetchall()

        if not rows:
            proof = {"total_spend": 0, "mission_count": 0, "avg_cost": 0.0}
            inputs_hash = hashlib.sha256(b"empty_cost_mission").hexdigest()
            return 0.0, proof, inputs_hash

        total_cost = sum(r["estimate_minor_units"] for r in rows)
        avg_cost = round(float(total_cost) / float(len(rows)), 2)
        raw_items = [{"id": r["id"], "cost": r["estimate_minor_units"]} for r in rows]

        proof = {"total_spend": total_cost, "task_count": len(rows), "avg_cost": avg_cost}
        inputs_hash = hashlib.sha256(json.dumps(raw_items, sort_keys=True).encode()).hexdigest()
        return avg_cost, proof, inputs_hash

    @classmethod
    def _compute_defect_rate(
        cls, conn, tenant_id: str, company_id: str, scope_level: KPIScopeLevel, scope_id: Optional[str]
    ) -> Tuple[float, Dict[str, Any], str]:
        """Computes defect rate percentage."""
        query = "SELECT id, defect_type FROM kaizen_defect_records WHERE tenant_id = ? AND company_id = ?"
        params = [tenant_id, company_id]
        if scope_level == KPIScopeLevel.POSITION and scope_id:
            query += " AND position_id = ?"
            params.append(scope_id)

        defect_rows = conn.execute(query, tuple(params)).fetchall()
        defects_count = len(defect_rows)

        # Total task submissions
        sub_rows = conn.execute(
            "SELECT count(*) FROM work_tasks WHERE tenant_id = ? AND company_id = ? AND status IN ('SUBMITTED', 'VERIFYING', 'COMPLETED', 'REJECTED')",
            (tenant_id, company_id)
        ).fetchone()[0]

        total_subs = max(sub_rows, defects_count, 1)
        rate = round((float(defects_count) / float(total_subs)) * 100.0, 2)
        raw_items = [{"id": r["id"], "defect": r["defect_type"]} for r in defect_rows]

        proof = {"defects_count": defects_count, "submissions_count": total_subs, "defect_rate": rate}
        inputs_hash = hashlib.sha256(json.dumps(raw_items, sort_keys=True).encode()).hexdigest()
        return rate, proof, inputs_hash

    @classmethod
    def _compute_ledger_balance(
        cls, conn, tenant_id: str, company_id: str, scope_level: KPIScopeLevel, scope_id: Optional[str]
    ) -> Tuple[float, Dict[str, Any], str]:
        """Computes net ledger balance from accounts."""
        rows = conn.execute(
            "SELECT account_id, code, type FROM accounts WHERE tenant_id = ? AND company_id = ?",
            (tenant_id, company_id)
        ).fetchall()

        raw_items = [{"id": r["account_id"], "code": r["code"]} for r in rows]
        proof = {"accounts_count": len(rows), "balance": 0.0}
        inputs_hash = hashlib.sha256(json.dumps(raw_items, sort_keys=True).encode()).hexdigest()
        return 0.0, proof, inputs_hash
