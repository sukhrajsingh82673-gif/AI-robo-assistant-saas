"""
ZONATA Owner Reporting Service & Number-Lock Validator
OpenCode Step 2J: Deterministic owner reporting.
Rule 18: Code checks every number in narrative text against real database facts (Number-Lock).
Honest attribution: States measured changes and actions taken without claiming causality.
"""

from __future__ import annotations

import re
import time
import json
import uuid
from typing import Dict, Any, List, Set, Optional

from core.db import db
from core.executive.types import NumberLockViolationError


class NumberLockValidator:
    """
    Enforces Rule 18 Determinism on owner-facing narrative texts.
    Every number appearing in a generated report must match a real stored database fact.
    """

    @classmethod
    def extract_numbers_from_text(cls, text: str) -> List[float]:
        """Extracts all numeric tokens from text."""
        # Find all integer and decimal numbers (ignoring standalone punctuation)
        raw_tokens = re.findall(r"(?<![A-Za-z_])(\d+(?:\.\d+)?)(?![A-Za-z_])", text)
        numbers = []
        for tok in raw_tokens:
            try:
                numbers.append(float(tok))
            except ValueError:
                pass
        return numbers

    @classmethod
    def verify_numbers(cls, narrative_text: str, facts: Dict[str, Any]) -> List[float]:
        """
        Verifies that every number in narrative_text matches at least one value in facts.
        Returns a list of unverified numbers (empty if number-lock passes).
        """
        # Collect all valid numbers from facts
        valid_numbers: Set[float] = set()
        for v in facts.values():
            if isinstance(v, (int, float)):
                fval = float(v)
                valid_numbers.add(round(fval, 2))
                # Also allow percentage representation (e.g. 0.95 -> 95.0)
                if 0.0 <= fval <= 1.0:
                    valid_numbers.add(round(fval * 100.0, 2))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, (int, float)):
                        valid_numbers.add(round(float(item), 2))
            elif isinstance(v, dict):
                for sub_v in v.values():
                    if isinstance(sub_v, (int, float)):
                        valid_numbers.add(round(float(sub_v), 2))

        narrative_numbers = cls.extract_numbers_from_text(narrative_text)
        unverified: List[float] = []

        for num in narrative_numbers:
            rounded = round(num, 2)
            # Check if this number exists in valid facts
            matched = False
            for v_num in valid_numbers:
                if abs(rounded - v_num) < 1e-2:
                    matched = True
                    break
            if not matched:
                unverified.append(num)

        return unverified


class CEOReportingService:
    """
    Builds verified daily, weekly, and on-demand owner reports.
    Applies Number-Lock verification and honest attribution.
    """

    FORBIDDEN_CAUSAL_PHRASES = [
        "better than human",
        "more accurate than human",
        "our ai caused",
        "we drove",
        "we magically delivered",
    ]

    @classmethod
    def collect_company_facts(cls, tenant_id: str, company_id: str) -> Dict[str, Any]:
        """Collects verified factual metrics from stored database tables."""
        facts: Dict[str, Any] = {}

        with db.get_connection() as conn:
            # 1. Work tasks stats
            t_rows = conn.execute(
                """
                SELECT count(*) as total_tasks,
                       sum(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_tasks,
                       sum(estimate_minor_units) as total_spend
                FROM work_tasks WHERE tenant_id = ? AND company_id = ?
                """,
                (tenant_id, company_id)
            ).fetchone()
            if t_rows:
                facts["total_tasks"] = t_rows["total_tasks"] or 0
                facts["completed_tasks"] = t_rows["completed_tasks"] or 0
                facts["total_spend_minor_units"] = t_rows["total_spend"] or 0

            # 2. Latest KPI snapshots
            kpi_rows = conn.execute(
                """
                SELECT kpi_id, current_value, target_value, status
                FROM kpi_snapshots WHERE tenant_id = ? AND company_id = ?
                ORDER BY computed_at DESC LIMIT 10
                """,
                (tenant_id, company_id)
            ).fetchall()
            for r in kpi_rows:
                facts[f"kpi_{r['kpi_id']}"] = r["current_value"]

        return facts

    @classmethod
    def generate_owner_report(
        cls,
        tenant_id: str,
        company_id: str,
        narrative_draft: Optional[str] = None,
        facts_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates an owner report. Enforces Number-Lock on narrative text.
        If any number is unverified, rejects narrative and falls back to plain verified template.
        """
        facts = facts_override if facts_override is not None else cls.collect_company_facts(tenant_id, company_id)

        # Honest attribution check
        if narrative_draft:
            lower_narrative = narrative_draft.lower()
            for phrase in cls.FORBIDDEN_CAUSAL_PHRASES:
                if phrase in lower_narrative:
                    narrative_draft = None
                    break

        # Number-Lock Verification
        final_narrative = ""
        is_fallback = False

        if narrative_draft:
            unverified = NumberLockValidator.verify_numbers(narrative_draft, facts)
            if unverified:
                # Number-Lock failed: fall back to structured factual template
                is_fallback = True
                final_narrative = cls._build_plain_template(facts)
            else:
                final_narrative = narrative_draft
        else:
            final_narrative = cls._build_plain_template(facts)

        return {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "facts": facts,
            "narrative": final_narrative,
            "is_fallback": is_fallback,
            "generated_at": time.time(),
        }

    @classmethod
    def _build_plain_template(cls, facts: Dict[str, Any]) -> str:
        """Constructs a deterministic factual template without unverified narrative."""
        completed = facts.get("completed_tasks", 0)
        total = facts.get("total_tasks", 0)
        spend = facts.get("total_spend_minor_units", 0)
        return (
            f"Company Operations Summary: {completed} tasks completed out of {total} total tasks. "
            f"Recorded spend: {spend} minor units. All figures verified from system records."
        )
