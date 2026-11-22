"""
ZONATA CEO Planner & Deterministic Plan Validator
OpenCode Step 2J: Plans missions, projects, and tasks delegated to positions.
Enforces deterministic validation: capability availability, budget arithmetic, authority coverage, acyclicity, and deadlines.
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, deque

from core.db import db
from core.ports.base import capability_truth_table
from core.work import workforce_work_service
from core.executive.types import (
    DirectiveModel,
    DirectiveStatus,
    PlanGraphModel,
    PlanMissionSpec,
    PlanProjectSpec,
    PlanTaskSpec,
    PlanValidationFailedError,
    ClarificationRequiredError,
)


class PlanValidator:
    """
    Strict deterministic validator for CEO execution plans.
    Validates:
      1. Capability Availability: Steps needing non-live capabilities become BLOCKED.
      2. Budget Arithmetic: Total estimated cost cannot exceed directive/company budget.
      3. Authority Coverage: Positions must hold sufficient authority profile for required action classes.
      4. Dependency Acyclicity: Prerequisite task DAG must be strictly acyclic.
      5. Deadline Chronology: Task <= Project <= Mission <= Directive deadline.
    """

    @classmethod
    def validate_plan(
        cls,
        tenant_id: str,
        company_id: str,
        directive: DirectiveModel,
        plan: PlanGraphModel,
    ) -> List[str]:
        """
        Validates a proposed plan graph. Returns a list of failure reasons.
        Empty list indicates plan passes all deterministic checks.
        """
        reasons: List[str] = []

        # 1. Budget Arithmetic Validation
        total_cost = 0
        all_tasks: List[PlanTaskSpec] = []
        for m in plan.missions:
            for p in m.projects:
                for t in p.tasks:
                    total_cost += t.estimate_minor_units
                    all_tasks.append(t)

        plan.total_estimated_cost_minor_units = total_cost

        if directive.budget_minor_units > 0 and total_cost > directive.budget_minor_units:
            reasons.append(
                f"BUDGET_EXCEEDED: Plan total estimated cost ({total_cost} minor units) "
                f"exceeds directive budget ({directive.budget_minor_units} minor units)."
            )

        # 2. Capability Availability Checks
        for t in all_tasks:
            for cap in t.required_capabilities:
                # Browser and desktop control are unbuilt/not live in Step 2
                if cap in ("BROWSER_CONTROL", "MARKET_RESEARCH_LIVE", "DESKTOP_CONTROL"):
                    t.required_capabilities = [f"BLOCKED: CAPABILITY_NOT_LIVE ({cap})"]
                else:
                    cap_status = capability_truth_table.get_status(cap)
                    if cap_status != "LIVE":
                        t.required_capabilities = [f"BLOCKED: CAPABILITY_NOT_LIVE ({cap})"]

        # 3. Position Authority Coverage Checks
        with db.get_connection() as conn:
            pos_rows = conn.execute(
                "SELECT position_id, authority_profile_id, spend_limit_minor_units FROM positions "
                "WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id)
            ).fetchall()
            pos_map = {r["position_id"]: dict(r) for r in pos_rows}

        for t in all_tasks:
            if t.position_code in pos_map:
                p_info = pos_map[t.position_code]
                spend_limit = p_info.get("spend_limit_minor_units", 0)
                if t.estimate_minor_units > spend_limit:
                    reasons.append(
                        f"AUTHORITY_INSUFFICIENT: Task '{t.task_id}' cost {t.estimate_minor_units} "
                        f"exceeds position '{t.position_code}' spend limit {spend_limit}."
                    )
                # Authority profile check (e.g. G1 cannot perform FINANCIAL_DISBURSEMENT)
                profile = p_info.get("authority_profile_id", "G1")
                if t.action_class in ("FINANCIAL_DISBURSEMENT", "CONTRACT_SIGNING") and profile in ("G1", "G2"):
                    reasons.append(
                        f"AUTHORITY_INSUFFICIENT: Position '{t.position_code}' holds profile '{profile}' "
                        f"which cannot execute action class '{t.action_class}'."
                    )

        # 4. Dependency Acyclicity Check
        task_ids = {t.task_id for t in all_tasks}
        graph = defaultdict(list)
        in_degree = {t.task_id: 0 for t in all_tasks}

        for t in all_tasks:
            for prereq in t.prerequisites:
                if prereq in task_ids:
                    graph[prereq].append(t.task_id)
                    in_degree[t.task_id] += 1

        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        visited_count = 0
        while queue:
            node = queue.popleft()
            visited_count += 1
            for nxt in graph[node]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if visited_count < len(all_tasks):
            reasons.append("DEPENDENCY_CYCLE: Task prerequisites contain a circular dependency.")

        # 5. Deadline Chronology Check
        for m in plan.missions:
            if directive.deadline_ts and m.deadline_ts and m.deadline_ts > directive.deadline_ts:
                reasons.append(f"DEADLINE_VIOLATION: Mission '{m.mission_id}' deadline exceeds directive deadline.")
            for p in m.projects:
                if m.deadline_ts and p.deadline_ts and p.deadline_ts > m.deadline_ts:
                    reasons.append(f"DEADLINE_VIOLATION: Project '{p.project_id}' deadline exceeds mission deadline.")
                for t in p.tasks:
                    if p.deadline_ts and t.deadline_ts and t.deadline_ts > p.deadline_ts:
                        reasons.append(f"DEADLINE_VIOLATION: Task '{t.task_id}' deadline exceeds project deadline.")

        return reasons


class CEOPlanner:
    """
    Translates validated Directives into execution graphs of missions, projects, and tasks.
    Delegates exclusively through positions (never directly executed by the CEO).
    """

    @classmethod
    def plan_directive(
        cls,
        tenant_id: str,
        company_id: str,
        directive: DirectiveModel,
        proposed_plan: PlanGraphModel,
    ) -> PlanGraphModel:
        """
        Validates and materializes a plan graph into the Work Kernel.
        """
        if directive.is_ambiguous:
            raise ClarificationRequiredError(
                question=directive.clarifying_question or "Command requires clarification.",
                ambiguity_domain="AMBIGUOUS_COMMAND",
            )

        # 1. Deterministic Validation
        errors = PlanValidator.validate_plan(tenant_id, company_id, directive, proposed_plan)
        if errors:
            raise PlanValidationFailedError(reasons=errors)

        # 2. Materialize Plan in Work Kernel
        now = time.time()
        for m in proposed_plan.missions:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO work_missions (
                        id, tenant_id, company_id, title, objective, lead_position_id,
                        status, budget_micro_units, target_deadline_ts, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'PLANNING', ?, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    """,
                    (
                        m.mission_id, tenant_id, company_id, m.title, m.objective,
                        m.lead_position_code, m.budget_minor_units * 10000, m.deadline_ts,
                        now, now
                    )
                )
                conn.commit()

            for p in m.projects:
                with db.get_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO work_projects (
                            id, mission_id, tenant_id, company_id, title,
                            status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 'PLANNING', ?, ?)
                        ON CONFLICT(id) DO NOTHING
                        """,
                        (p.project_id, m.mission_id, tenant_id, company_id, p.title, now, now)
                    )
                    conn.commit()

                for t in p.tasks:
                    is_blocked = any("BLOCKED:" in c for c in t.required_capabilities)
                    task_status = "BLOCKED" if is_blocked else "PROPOSED"
                    blocked_reason = t.required_capabilities[0] if is_blocked else None

                    with db.get_connection() as conn:
                        conn.execute(
                            """
                            INSERT INTO work_tasks (
                                id, tenant_id, company_id, mission_id, project_id, title,
                                owner_id, assignee_type, assignee_id, status, blocked_reason_code,
                                estimate_minor_units, estimate_seconds, deadline_ts,
                                required_capabilities, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, 'principal_owner', 'POSITION', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO NOTHING
                            """,
                            (
                                t.task_id, tenant_id, company_id, m.mission_id, p.project_id,
                                t.title, t.position_code, task_status, blocked_reason,
                                t.estimate_minor_units, t.estimate_seconds, t.deadline_ts,
                                json.dumps(t.required_capabilities), now, now
                            )
                        )
                        conn.commit()

        # Update directive status to PLANNED
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE ceo_directives SET status = 'PLANNED', updated_at = ? WHERE id = ?",
                (now, directive.id)
            )
            conn.commit()

        directive.status = DirectiveStatus.PLANNED
        return proposed_plan
