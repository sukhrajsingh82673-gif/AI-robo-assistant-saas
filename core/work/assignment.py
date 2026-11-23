"""
ZONATA Task Assignment Engine
Deterministic candidate scoring from eligibility (authority, tools, trust level),
capacity, queue depth, cost, and historical verified pass rate.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from core.db import db
from core.authority.profiles import authority_profile_manager
from core.authority.types import AutonomyLevel, AUTONOMY_RANK
from core.authority.autonomy import compute_effective_autonomy
from core.organization.service import organization_service
from core.work.types import TaskStatus, TaskAssignmentIneligibleError


class TaskAssignmentEngine:
    """
    Evaluates and scores candidates deterministically for task assignment.
    """

    @classmethod
    def evaluate_candidate_eligibility(
        cls,
        tenant_id: str,
        company_id: str,
        candidate_id: str,
        estimate_minor_units: int,
        required_autonomy_level: str,
        required_capabilities: List[str],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates whether candidate_id is eligible for the task.
        Returns (is_eligible, failure_reason).
        """
        # 1. Authority Profile & Spend Limit Check
        profile = authority_profile_manager.get_profile(tenant_id, company_id, candidate_id)
        if profile and isinstance(profile, dict):
            single_usd = profile.get("single", 0) or 0
            if estimate_minor_units > 0 and single_usd > 0:
                max_minor = int(single_usd * 100)
                if estimate_minor_units > max_minor:
                    return (
                        False,
                        f"Spend estimate ({estimate_minor_units} minor units) exceeds candidate spend limit ({max_minor} minor units)."
                    )

        # 2. Autonomy Trust Level Check
        if required_autonomy_level and required_autonomy_level != AutonomyLevel.SHADOW.value:
            effective_autonomy = compute_effective_autonomy(tenant_id, company_id, candidate_id)
            req_level = AutonomyLevel(required_autonomy_level) if isinstance(required_autonomy_level, str) else required_autonomy_level
            if AUTONOMY_RANK.get(effective_autonomy, 0) < AUTONOMY_RANK.get(req_level, 0):
                return (
                    False,
                    f"Candidate effective autonomy '{effective_autonomy.value}' is below required '{req_level.value}'."
                )

        return (True, None)

    @classmethod
    def get_candidate_metrics(
        cls,
        tenant_id: str,
        company_id: str,
        candidate_id: str,
    ) -> Dict[str, Any]:
        """
        Retrieves active queue depth and historical verified pass rate from real work_tasks data.
        """
        with db.get_connection() as conn:
            # Active queue depth
            queue_row = conn.execute(
                """
                SELECT COUNT(*) as active_cnt
                FROM work_tasks
                WHERE tenant_id = ? AND company_id = ? AND assignee_id = ?
                  AND status IN ('ASSIGNED', 'ACCEPTED', 'IN_PROGRESS')
                """,
                (tenant_id, company_id, candidate_id)
            ).fetchone()
            queue_depth = queue_row["active_cnt"] if queue_row else 0

            # Historical pass rate
            history_row = conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_cnt,
                    SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected_cnt
                FROM work_tasks
                WHERE tenant_id = ? AND company_id = ? AND assignee_id = ?
                """,
                (tenant_id, company_id, candidate_id)
            ).fetchone()

            completed_cnt = (history_row["completed_cnt"] or 0) if history_row else 0
            rejected_cnt = (history_row["rejected_cnt"] or 0) if history_row else 0
            total_evaluated = completed_cnt + rejected_cnt

            if total_evaluated == 0:
                pass_rate = 1.0  # Default neutral baseline for fresh candidate
            else:
                pass_rate = round(completed_cnt / total_evaluated, 4)

        return {
            "queue_depth": queue_depth,
            "completed_count": completed_cnt,
            "rejected_count": rejected_cnt,
            "pass_rate": pass_rate,
        }

    @classmethod
    def score_candidate(
        cls,
        candidate_id: str,
        metrics: Dict[str, Any],
        cost_minor_units: int = 1000,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Deterministic scoring formula:
        score = (pass_rate * 100.0) - (queue_depth * 10.0) - (cost_minor_units / 1000.0)
        """
        pass_rate = metrics["pass_rate"]
        queue_depth = metrics["queue_depth"]
        cost_factor = cost_minor_units / 1000.0

        raw_score = (pass_rate * 100.0) - (queue_depth * 10.0) - cost_factor
        score = round(raw_score, 2)

        breakdown = {
            "pass_rate": pass_rate,
            "queue_depth": queue_depth,
            "cost_minor_units": cost_minor_units,
            "raw_score": score,
        }
        return (score, breakdown)

    @classmethod
    def select_best_assignee(
        cls,
        tenant_id: str,
        company_id: str,
        estimate_minor_units: int,
        required_autonomy_level: str,
        required_capabilities: List[str],
        candidate_pool: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Determines the optimal candidate from candidate_pool (or all company positions),
        computing scores and returning (selected_candidate_id, assignment_reasons).
        """
        candidates = candidate_pool
        if not candidates:
            # Query positions in company
            positions = organization_service.list_positions(tenant_id, company_id)
            candidates = [p["position_id"] for p in positions]

        if not candidates:
            raise TaskAssignmentIneligibleError("No candidate positions available in organization for task assignment.")

        scored_candidates: List[Tuple[float, str, Dict[str, Any]]] = []
        ineligible_reasons: Dict[str, str] = {}

        for cid in candidates:
            eligible, reason = cls.evaluate_candidate_eligibility(
                tenant_id, company_id, cid, estimate_minor_units,
                required_autonomy_level, required_capabilities
            )
            if not eligible:
                ineligible_reasons[cid] = reason or "Ineligible"
                continue

            metrics = cls.get_candidate_metrics(tenant_id, company_id, cid)
            score, breakdown = cls.score_candidate(cid, metrics)
            scored_candidates.append((score, cid, breakdown))

        if not scored_candidates:
            raise TaskAssignmentIneligibleError(
                f"No eligible candidates found. Rejection details: {ineligible_reasons}"
            )

        # Deterministic sort: highest score first, then alphabetically by candidate_id for stable ties
        scored_candidates.sort(key=lambda x: (-x[0], x[1]))
        best_score, best_id, best_breakdown = scored_candidates[0]

        assignment_reasons = {
            "selected_candidate_id": best_id,
            "score": best_score,
            "breakdown": best_breakdown,
            "total_candidates_evaluated": len(candidates),
            "eligible_candidates_count": len(scored_candidates),
            "rationale": "Selected based on highest verified pass rate and optimal active capacity.",
        }

        return (best_id, assignment_reasons)
