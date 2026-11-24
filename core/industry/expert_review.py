"""
Expert Review Protocol for Industry Overlays (Rule 71)
======================================================
Depth is earned by human review, not generated.
- Records reviewer's identity, stated credentials document, checklist, and conflict declaration.
- Binds sign-off to the exact SHA-256 content digest of the overlay.
- HARD INVARIANT: An AI principal can NEVER be recorded as a reviewer (Rule 71).
"""

import re
import datetime
from typing import Dict, Any, List, Optional
from core.industry.schema import compute_overlay_digest


class AIReviewerProhibitedError(PermissionError):
    """Raised when an AI principal or synthetic identity attempts to sign an expert review (Rule 71)."""
    pass


# Disallowed AI principal identifiers and patterns
AI_PRINCIPAL_PATTERNS = [
    re.compile(r"^(agent|model|ai|bot|llm|copilot|assistant):", re.IGNORECASE),
    re.compile(r"\b(gpt|claude|gemini|llama|mistral|antigravity|opencode|qwen|deepseek)\b", re.IGNORECASE),
    re.compile(r"\b(synthetic|autonomous|agentic|machine|subagent)\b", re.IGNORECASE),
]


class ExpertReviewProtocol:
    """Manages human expert review registration, checklists, conflict checks, and digest binding."""

    @staticmethod
    def validate_reviewer_identity(reviewer_id: str, reviewer_name: str) -> None:
        """Verifies that the reviewer is a human professional and strictly not an AI principal."""
        combined = f"{reviewer_id} {reviewer_name}"
        for pattern in AI_PRINCIPAL_PATTERNS:
            if pattern.search(combined):
                raise AIReviewerProhibitedError(
                    f"Rule 71 Violation: AI principal or automated identity '{reviewer_name}' "
                    f"cannot be recorded as an overlay reviewer. Only verified human domain experts may sign reviews."
                )

    @classmethod
    def submit_review(
        cls,
        overlay_data: Dict[str, Any],
        reviewer_id: str,
        reviewer_name: str,
        stated_credentials: str,
        checklist_answers: Dict[str, bool],
        conflict_of_interest_declaration: str,
    ) -> Dict[str, Any]:
        """Submits an expert review for an overlay and binds it to the current content digest."""
        cls.validate_reviewer_identity(reviewer_id, reviewer_name)

        if not stated_credentials or len(stated_credentials.strip()) < 10:
            raise ValueError("Stated credentials document/summary must be provided")

        if not conflict_of_interest_declaration:
            raise ValueError("Conflict of interest declaration is mandatory")

        # Mandatory review checklist items
        required_checks = [
            "calculators_mathematically_sound",
            "regulatory_cites_accurate",
            "boundary_policies_adequate",
            "no_dangerous_automation",
        ]
        for check in required_checks:
            if not checklist_answers.get(check):
                raise ValueError(f"Mandatory checklist item '{check}' must be confirmed PASS")

        # Update metadata tier prior to computing digest
        reviews_count = len(overlay_data.get("expert_reviews", [])) + 1
        if reviews_count == 1:
            overlay_data.setdefault("metadata", {})["tier"] = "T3"
        elif reviews_count >= 2 and overlay_data.get("pilot_evidence"):
            overlay_data.setdefault("metadata", {})["tier"] = "T4"

        content_digest = compute_overlay_digest(overlay_data)

        review_record = {
            "review_id": f"rev_{content_digest[:8]}_{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}",
            "reviewer_id": reviewer_id,
            "reviewer_name": reviewer_name,
            "stated_credentials": stated_credentials,
            "checklist": checklist_answers,
            "conflict_declaration": conflict_of_interest_declaration,
            "content_digest": content_digest,
            "signed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # Append to overlay data
        if "expert_reviews" not in overlay_data:
            overlay_data["expert_reviews"] = []
        overlay_data["expert_reviews"].append(review_record)

        return review_record
