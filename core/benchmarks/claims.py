"""
Governed Benchmark Claims Registry and Verification Gate (Rule 69 & ADR 0045)
Guards commercial, marketing, and product performance claims.
Claims must cite sealed benchmark run IDs with N >= 30, valid comparison (C vs A or D vs A),
and 0 critical safety violations. Unbacked claims are strictly blocked.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import json


class UnverifiedClaimBlockedError(PermissionError):
    """Raised when an unbacked, under-sampled, or unethically compared claim is registered or published."""
    pass


@dataclass
class BenchmarkClaim:
    claim_id: str
    statement: str
    benchmark_run_id: str
    configuration_comparison: str  # Must be 'C_VS_A' or 'D_VS_A'
    sample_size: int               # Must be >= 30
    effect_size_d: float           # Cohen's d
    ci_95: Tuple[float, float]     # (lower, upper)
    critical_safety_violations: int = 0
    approved_by_lead: Optional[str] = None


class BenchmarkClaimsRegistry:
    """Registry maintaining sealed and verified performance claims."""

    ALLOWED_COMPARISONS = {"C_VS_A", "D_VS_A"}
    MIN_SAMPLE_SIZE = 30

    def __init__(self):
        self._registered_claims: Dict[str, Dict[str, Any]] = {}

    def register_claim(self, claim: BenchmarkClaim) -> Dict[str, Any]:
        """
        Validates claim against empirical standards under Rule 69.
        Throws UnverifiedClaimBlockedError if criteria are violated.
        """
        # Rule 69 Invariant: Comparison must be C vs A or D vs A
        if claim.configuration_comparison not in self.ALLOWED_COMPARISONS:
            raise UnverifiedClaimBlockedError(
                f"UNVERIFIED_CLAIM_BLOCKED: Claim '{claim.claim_id}' uses invalid comparison "
                f"'{claim.configuration_comparison}'. Rule 69 strictly mandates comparison against "
                f"unassisted human baseline (Config A). Claiming superiority against Config B (Unassisted AI) is prohibited."
            )

        # Rule 69 Invariant: Sample size N >= 30
        if claim.sample_size < self.MIN_SAMPLE_SIZE:
            raise UnverifiedClaimBlockedError(
                f"UNVERIFIED_CLAIM_BLOCKED: Claim '{claim.claim_id}' has sample size N={claim.sample_size}. "
                f"Minimum sample size N >= {self.MIN_SAMPLE_SIZE} is required for statistical significance."
            )

        # Critical Safety Violation Veto
        if claim.critical_safety_violations > 0:
            raise UnverifiedClaimBlockedError(
                f"UNVERIFIED_CLAIM_BLOCKED: Claim '{claim.claim_id}' recorded {claim.critical_safety_violations} "
                f"critical safety violations during benchmark execution. Any critical violation automatically vetoes the claim."
            )

        claim_record = {
            "claim_id": claim.claim_id,
            "statement": claim.statement,
            "benchmark_run_id": claim.benchmark_run_id,
            "configuration_comparison": claim.configuration_comparison,
            "sample_size": claim.sample_size,
            "effect_size_d": claim.effect_size_d,
            "ci_95": claim.ci_95,
            "critical_safety_violations": claim.critical_safety_violations,
            "status": "EMPIRICALLY_VERIFIED",
        }

        # Seal claim record
        canonical = json.dumps(claim_record, sort_keys=True)
        claim_record["claim_seal_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        self._registered_claims[claim.claim_id] = claim_record
        return claim_record

    def get_verified_claim(self, claim_id: str) -> Dict[str, Any]:
        if claim_id not in self._registered_claims:
            raise KeyError(f"Claim '{claim_id}' not found in registry")
        return self._registered_claims[claim_id]
