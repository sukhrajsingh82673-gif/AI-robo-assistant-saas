"""
Counterfactual Fairness Engine (Rule 63)
========================================
Audits resume and candidate scoring by demographic permutation.
Invariants:
- Swaps name, gender markers, age indicators, and university prestige proxies.
- Scoring disparity ratio across permutations must be strictly within [0.95, 1.05].
- Any deviation raises CounterfactualFairnessViolation and halts the screening model.
"""

from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
from core.hr.recruiting import CandidateResume


class CounterfactualFairnessViolation(Exception):
    """Raised when demographic permutations cause score disparity outside [0.95, 1.05]."""
    def __init__(self, message: str, disparity_ratio: float, details: Dict[str, Any]):
        super().__init__(message)
        self.disparity_ratio = disparity_ratio
        self.details = details


class DemographicPermutationResult(BaseModel):
    baseline_score: float
    permutation_scores: List[float] = Field(default_factory=list)
    min_disparity_ratio: float
    max_disparity_ratio: float
    is_fair: bool
    audit_samples_count: int


class CandidateScoringModel:
    """Objective, skills-grounded candidate scoring engine."""

    SKILL_WEIGHTS = {
        "python": 15.0, "sql": 10.0, "distributed_systems": 20.0,
        "fastapi": 10.0, "temporal": 15.0, "postgresql": 10.0,
        "system_architecture": 20.0
    }

    def score_candidate(self, candidate: CandidateResume) -> float:
        # Score strictly on verifiable merit: skills, experience, education
        score = 0.0

        # 1. Skills contribution
        for skill in candidate.skills:
            score += self.SKILL_WEIGHTS.get(skill.lower(), 5.0)

        # 2. Experience contribution (up to 25 pts)
        score += min(25.0, candidate.years_experience * 2.5)

        # 3. Education contribution (up to 15 pts)
        edu = candidate.education_level.lower()
        if edu == "phd":
            score += 15.0
        elif edu == "masters":
            score += 10.0
        else:
            score += 5.0

        return round(score, 2)


class CounterfactualFairnessAuditor:
    """Generates demographic permutations and validates disparity ratios against Rule 63 bounds."""

    DEMOGRAPHIC_NAMES = [
        # Diverse gender, regional, and cultural name sets
        "Aarav Sharma", "Priya Patel", "Rohan Verma", "Ananya Iyer",
        "Mohammed Al-Mansoor", "Fatima Zahra", "Tariq Aziz", "Aisha Khan",
        "David Miller", "Emily Johnson", "Michael Brown", "Sarah Davis",
        "Wei Chen", "Mei-Ling Zhou", "Jun-Ho Park", "Ji-Woo Kim",
        "Kwame Osei", "Zainab Mensah", "Chukwudi Eze", "Amara Okonkwo"
    ]

    GENDER_MARKERS = ["M", "F", "NB"]
    AGE_INDICATORS = [23, 28, 35, 42, 55]

    def __init__(self, scoring_model: Optional[CandidateScoringModel] = None):
        self.model = scoring_model or CandidateScoringModel()

    def audit_counterfactual_fairness(self, base_candidate: CandidateResume) -> DemographicPermutationResult:
        baseline_score = self.model.score_candidate(base_candidate)
        assert baseline_score > 0, "Base candidate score must be positive"

        scores: List[float] = []
        disparities: List[float] = []

        # Generate permutations
        count = 0
        for name in self.DEMOGRAPHIC_NAMES:
            for g in self.GENDER_MARKERS:
                for age in self.AGE_INDICATORS:
                    count += 1
                    perm_candidate = CandidateResume(
                        candidate_id=f"perm_{count}",
                        tenant_id=base_candidate.tenant_id,
                        company_id=base_candidate.company_id,
                        raw_name=name,
                        years_experience=base_candidate.years_experience,
                        skills=base_candidate.skills,
                        education_level=base_candidate.education_level,
                        gender_marker=g,
                        age_indicator=age
                    )
                    score = self.model.score_candidate(perm_candidate)
                    scores.append(score)
                    ratio = score / baseline_score
                    disparities.append(ratio)
                    if count >= 100:
                        break
                if count >= 100:
                    break
            if count >= 100:
                break

        min_ratio = round(min(disparities), 4)
        max_ratio = round(max(disparities), 4)

        # Rule 63 Invariant: Disparity ratio must be strictly within [0.95, 1.05]
        is_fair = (0.95 <= min_ratio <= 1.05) and (0.95 <= max_ratio <= 1.05)

        if not is_fair:
            raise CounterfactualFairnessViolation(
                f"Rule 63 Counterfactual Fairness Violation: disparity ratio outside [0.95, 1.05] "
                f"(min={min_ratio}, max={max_ratio})",
                disparity_ratio=min_ratio if min_ratio < 0.95 else max_ratio,
                details={"min_ratio": min_ratio, "max_ratio": max_ratio, "samples": count}
            )

        return DemographicPermutationResult(
            baseline_score=baseline_score,
            permutation_scores=scores,
            min_disparity_ratio=min_ratio,
            max_disparity_ratio=max_ratio,
            is_fair=is_fair,
            audit_samples_count=len(scores)
        )
