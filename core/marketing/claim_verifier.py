"""
Marketing Content Claim Verification Engine
===========================================
Verifies that statistical and factual claims made in marketing materials
are grounded in verifiable benchmark citations and facts.
Adheres to Truth Rule: Never fabricate citations or claim unproven capabilities.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field


class VerifiedFact(BaseModel):
    fact_id: str
    assertion_pattern: str  # Regex pattern matching the claim
    metric_name: str
    verified_value: str
    citation: str  # e.g. "Q3 Benchmark Report Section 4.2"
    effective_date: str


class ClaimVerificationResult(BaseModel):
    is_verified: bool
    verified_claims: List[Dict[str, str]] = Field(default_factory=list)
    unverified_claims: List[str] = Field(default_factory=list)


class ContentClaimVerifier:
    """Scans text for statistical claims and matches against verified benchmark facts."""

    def __init__(self, fact_database: Optional[List[VerifiedFact]] = None):
        self.facts = fact_database or self._default_facts()

    @staticmethod
    def _default_facts() -> List[VerifiedFact]:
        return [
            VerifiedFact(
                fact_id="fact_uptime",
                assertion_pattern=r"99\.9(?:9)?%\s+uptime",
                metric_name="SLA Uptime",
                verified_value="99.95%",
                citation="Infrastructure Production Metrics 2026",
                effective_date="2026-01-01"
            ),
            VerifiedFact(
                fact_id="fact_tps",
                assertion_pattern=r"10,?000\s+(?:tx/sec|tps|transactions per second)",
                metric_name="Throughput",
                verified_value="10,240 tps",
                citation="Distributed Ledger Benchmark Suite v2",
                effective_date="2026-06-15"
            ),
            VerifiedFact(
                fact_id="fact_soc2",
                assertion_pattern=r"soc\s*2\s+type\s+ii",
                metric_name="Security Certification",
                verified_value="Certified",
                citation="Independent Audit Report 2026 by Ernst & Young",
                effective_date="2026-03-31"
            )
        ]

    def verify_claims(self, text: str) -> ClaimVerificationResult:
        verified: List[Dict[str, str]] = []
        unverified: List[str] = []

        # Find any number/percentage based statistical assertions
        stat_patterns = re.findall(r"(\d+(?:\.\d+)?%\s+[a-zA-Z]+|\d+(?:,\d+)?\s+(?:tps|transactions per second|uptime))", text, flags=re.IGNORECASE)

        for claim in stat_patterns:
            matched_fact = None
            for fact in self.facts:
                if re.search(fact.assertion_pattern, claim, flags=re.IGNORECASE):
                    matched_fact = fact
                    break

            if matched_fact:
                verified.append({
                    "claim": claim,
                    "fact_id": matched_fact.fact_id,
                    "citation": matched_fact.citation
                })
            else:
                unverified.append(claim)

        is_verified = len(unverified) == 0
        return ClaimVerificationResult(
            is_verified=is_verified,
            verified_claims=verified,
            unverified_claims=unverified
        )
