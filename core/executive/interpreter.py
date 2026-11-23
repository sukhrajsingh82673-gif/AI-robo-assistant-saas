"""
ZONATA CEO Command Interpreter & Ambiguity Guard
OpenCode Step 2J: Interprets owner commands into typed Directives.
When ambiguity affects money, legal exposure, or irreversibility, asks clarifying questions instead of guessing.
"""

from __future__ import annotations

import re
import time
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple

from core.db import db
from core.executive.types import (
    DirectiveModel,
    DirectiveStatus,
    ClarificationRequiredError,
)


class CommandInterpreter:
    """
    Parses natural language owner commands into typed Directives.
    Guards against high-stakes ambiguity regarding money, legal exposure, and irreversibility.
    """

    FINANCIAL_KEYWORDS = ["spend", "budget", "cost", "invest", "purchase", "payout", "price", "disburse"]
    LEGAL_KEYWORDS = ["sue", "litigate", "nda", "contract", "settle", "liability", "patent", "copyright"]
    IRREVERSIBLE_KEYWORDS = ["delete", "terminate", "destroy", "wipe", "liquidate", "shut down", "fire"]

    @classmethod
    def interpret_command(
        cls,
        tenant_id: str,
        company_id: str,
        command: str,
        explicit_budget_minor_units: Optional[int] = None,
        explicit_deadline_ts: Optional[float] = None,
        explicit_constraints: Optional[List[str]] = None,
        explicit_kpis: Optional[List[str]] = None,
    ) -> DirectiveModel:
        """
        Interprets owner command. Flags high-stakes ambiguity if critical constraints are missing.
        Stores directive record in database.
        """
        now = time.time()
        directive_id = f"dir_{uuid.uuid4().hex[:12]}"
        constraints = explicit_constraints or []
        target_kpis = explicit_kpis or []

        # 1. Ambiguity Detection across High-Stakes Domains
        is_ambiguous, ambiguity_domain, clarifying_question = cls._scan_high_stakes_ambiguity(
            command=command,
            budget=explicit_budget_minor_units,
            deadline=explicit_deadline_ts,
        )

        status = DirectiveStatus.CLARIFICATION_REQUIRED if is_ambiguous else DirectiveStatus.PROPOSED
        budget = explicit_budget_minor_units or 0

        # Extract objective summary
        clean_cmd = command.strip()
        objective = clean_cmd[:200]

        # 2. Persist in Database
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO ceo_directives (
                    id, tenant_id, company_id, owner_command, objective,
                    constraints, deadline_ts, budget_minor_units, target_kpis,
                    scope, is_ambiguous, clarifying_question, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    directive_id, tenant_id, company_id, command, objective,
                    json.dumps(constraints), explicit_deadline_ts, budget,
                    json.dumps(target_kpis), json.dumps({}),
                    1 if is_ambiguous else 0, clarifying_question, status.value,
                    now, now
                )
            )
            conn.commit()

        return DirectiveModel(
            id=directive_id,
            tenant_id=tenant_id,
            company_id=company_id,
            owner_command=command,
            objective=objective,
            constraints=constraints,
            deadline_ts=explicit_deadline_ts,
            budget_minor_units=budget,
            target_kpis=target_kpis,
            scope={},
            is_ambiguous=is_ambiguous,
            clarifying_question=clarifying_question,
            status=status,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def get_directive(cls, tenant_id: str, company_id: str, directive_id: str) -> Optional[DirectiveModel]:
        """Retrieves a directive by ID."""
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM ceo_directives WHERE id = ? AND tenant_id = ? AND company_id = ?",
                (directive_id, tenant_id, company_id)
            ).fetchone()
        if not row:
            return None
        return DirectiveModel(
            id=row["id"],
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
            owner_command=row["owner_command"],
            objective=row["objective"],
            constraints=json.loads(row["constraints"]) if row["constraints"] else [],
            deadline_ts=row["deadline_ts"],
            budget_minor_units=row["budget_minor_units"],
            target_kpis=json.loads(row["target_kpis"]) if row["target_kpis"] else [],
            scope=json.loads(row["scope"]) if row["scope"] else {},
            is_ambiguous=bool(row["is_ambiguous"]),
            clarifying_question=row["clarifying_question"],
            status=DirectiveStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @classmethod
    def _scan_high_stakes_ambiguity(
        cls, command: str, budget: Optional[int], deadline: Optional[float]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Scans for high-stakes keywords without explicit numerical constraints or scope.
        Returns: (is_ambiguous, domain, clarifying_question)
        """
        cmd_lower = command.lower()

        # Check financial ambiguity (open-ended spending without budget)
        has_fin = any(kw in cmd_lower for kw in cls.FINANCIAL_KEYWORDS)
        if has_fin and (budget is None or budget <= 0):
            # Check if command has phrases like "whatever it takes", "at any cost", "scale aggressively"
            open_ended = any(p in cmd_lower for p in ["whatever", "any cost", "unlimited", "aggressively", "as needed", "scale"])
            if open_ended or "spend" in cmd_lower or "budget" in cmd_lower:
                return (
                    True,
                    "FINANCIAL_EXPOSURE",
                    "Command involves financial expenditure without an explicit budget ceiling. What is the maximum authorized budget for this directive?"
                )

        # Check legal ambiguity
        has_legal = any(kw in cmd_lower for kw in cls.LEGAL_KEYWORDS)
        if has_legal:
            # Check if specific party or jurisdiction is absent
            if not re.search(r"\b(against|with|entity|corp|inc|ltd)\s+[A-Za-z0-9_]+", cmd_lower):
                return (
                    True,
                    "LEGAL_EXPOSURE",
                    "Command involves legal actions without specific counter-party or legal scope. Please specify the target entity and legal counsel parameters."
                )

        # Check irreversible destruction
        has_irrev = any(kw in cmd_lower for kw in cls.IRREVERSIBLE_KEYWORDS)
        if has_irrev:
            if not re.search(r"\b(id|account|task|version|file)\s+[A-Za-z0-9_-]+", cmd_lower):
                return (
                    True,
                    "IRREVERSIBLE_ACTION",
                    "Command involves irreversible resource deletion without targeted IDs. Please specify exact target IDs and confirm manual approval intent."
                )

        return False, None, None
