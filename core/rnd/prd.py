"""
Product Requirements Document (PRD) Schema and Validation Engine
=================================================================
Schema: zonata.prd/v1
Enforces completeness: Problem statement, Target personas, Non-goals,
Requirements with testable acceptance criteria, Metrics, and Risks.
"""

from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field


class PRDRequirement(BaseModel):
    req_id: str
    title: str
    description: str
    acceptance_criteria: List[str] = Field(default_factory=list)


class ProductRequirementsDocument(BaseModel):
    prd_id: str
    title: str
    author_principal_id: str
    problem_statement: str
    target_users: List[str]
    non_goals: List[str]
    requirements: List[PRDRequirement]
    success_metrics: List[str]
    risks_and_mitigations: List[Dict[str, str]]
    schema_version: str = Field("zonata.prd/v1", description="PRD standard version")


class PRDValidationResult(BaseModel):
    is_valid: bool
    missing_elements: List[str] = Field(default_factory=list)
    word_count: int


class PRDValidator:
    """Validates structural and semantic completeness of Product Requirements Documents."""

    @staticmethod
    def validate_prd(prd: ProductRequirementsDocument) -> PRDValidationResult:
        missing = []

        # 1. Problem Statement Completeness
        if len(prd.problem_statement.strip()) < 30:
            missing.append("Problem statement must be substantive (minimum 30 characters)")

        # 2. Target Users
        if not prd.target_users:
            missing.append("Target users list cannot be empty")

        # 3. Explicit Non-Goals
        if not prd.non_goals:
            missing.append("Explicit non-goals must be declared to prevent scope creep")

        # 4. Requirements & Testable Acceptance Criteria
        if not prd.requirements:
            missing.append("At least one functional requirement must be specified")
        else:
            for req in prd.requirements:
                if not req.acceptance_criteria:
                    missing.append(f"Requirement '{req.req_id} - {req.title}' lacks testable acceptance criteria")

        # 5. Success Metrics
        if not prd.success_metrics:
            missing.append("Success metrics must be specified")

        # 6. Risks & Mitigations
        if not prd.risks_and_mitigations:
            missing.append("Known risks and mitigations must be documented")

        # Word count rollup
        all_text = f"{prd.title} {prd.problem_statement} {' '.join(prd.non_goals)} {' '.join(r.description for r in prd.requirements)}"
        word_count = len(all_text.split())

        return PRDValidationResult(
            is_valid=len(missing) == 0,
            missing_elements=missing,
            word_count=word_count
        )
