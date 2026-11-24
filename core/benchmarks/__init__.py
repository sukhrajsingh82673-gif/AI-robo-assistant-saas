"""
Human-Baseline Benchmark and Governed Claims Stack (Rule 69, ADR 0045, ADR 0046)
"""

from core.benchmarks.vault import (
    BenchmarkVault,
    BenchmarkVaultAccessDeniedError,
    BenchmarkTamperError,
)
from core.benchmarks.recorder import (
    HumanBaselineRecorder,
    ParticipantConsentMissingError,
)
from core.benchmarks.calibration import (
    SpendCapEnforcer,
    EvaluationBudgetExceededError,
    TheAgentCompanyAdapter,
    GDPvalAdapter,
    RemoteLaborIndexAdapter,
)
from core.benchmarks.claims import (
    BenchmarkClaim,
    BenchmarkClaimsRegistry,
    UnverifiedClaimBlockedError,
)

__all__ = [
    "BenchmarkVault",
    "BenchmarkVaultAccessDeniedError",
    "BenchmarkTamperError",
    "HumanBaselineRecorder",
    "ParticipantConsentMissingError",
    "SpendCapEnforcer",
    "EvaluationBudgetExceededError",
    "TheAgentCompanyAdapter",
    "GDPvalAdapter",
    "RemoteLaborIndexAdapter",
    "BenchmarkClaim",
    "BenchmarkClaimsRegistry",
    "UnverifiedClaimBlockedError",
]
