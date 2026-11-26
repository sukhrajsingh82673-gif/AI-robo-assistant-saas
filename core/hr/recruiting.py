"""
Structured Recruiting Engine & Inclusive Language Linter
========================================================
Features:
- Job Description validation with inclusive language linting
- Salary transparency range enforcement
- Structured interview rubric scoring
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    job_id: str
    tenant_id: str
    company_id: str
    title: str
    department: str
    description: str
    min_salary: float
    max_salary: float
    currency: str = "INR"
    requirements: List[str] = Field(default_factory=list)
    inclusive_lint_passed: bool = False
    lint_warnings: List[str] = Field(default_factory=list)


class CandidateResume(BaseModel):
    candidate_id: str
    tenant_id: str
    company_id: str
    raw_name: str
    years_experience: float
    skills: List[str]
    education_level: str  # 'bachelors', 'masters', 'phd'
    gender_marker: Optional[str] = None
    age_indicator: Optional[int] = None


class InclusiveLanguageLinter:
    """Detects biased, exclusionary, or hyper-aggressive phrasing in job descriptions."""

    MASCULINE_BIASED_WORDS = [
        "rockstar", "ninja", "hacker", "guru", "dominate", "aggressive",
        "killer instinct", "work hard play hard", "young and hungry"
    ]

    @classmethod
    def lint_job_description(cls, text: str) -> Tuple[bool, List[str]]:
        warnings: List[str] = []
        lower = text.lower()

        for term in cls.MASCULINE_BIASED_WORDS:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, lower):
                warnings.append(f"Inclusive Language Warning: '{term}' is exclusionary or gender-biased")

        passed = len(warnings) == 0
        return passed, warnings


class RecruitingManager:
    """Enforces salary transparency and inclusive job postings."""

    @staticmethod
    def create_job_posting(
        job_id: str,
        tenant_id: str,
        company_id: str,
        title: str,
        department: str,
        description: str,
        min_salary: float,
        max_salary: float,
        currency: str = "INR"
    ) -> JobPosting:
        # Salary transparency enforcement
        if min_salary <= 0 or max_salary <= 0 or max_salary < min_salary:
            raise ValueError("Salary transparency violation: valid min_salary and max_salary range required")

        passed, warnings = InclusiveLanguageLinter.lint_job_description(description)
        return JobPosting(
            job_id=job_id,
            tenant_id=tenant_id,
            company_id=company_id,
            title=title,
            department=department,
            description=description,
            min_salary=min_salary,
            max_salary=max_salary,
            currency=currency,
            inclusive_lint_passed=passed,
            lint_warnings=warnings
        )

    @staticmethod
    def score_interview_rubric(scores: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
        """Calculates weighted objective rubric score out of 100."""
        w = weights or {k: 1.0 / len(scores) for k in scores}
        total = sum(scores[k] * w.get(k, 0.0) for k in scores)
        return round(total, 2)
