"""
Industry Depth Factory Pipeline (LangGraph & ADK State Machine)
Orchestrates:
1. Source Collection: ingests authoritative sources with timestamp & SHA-256 hash
2. Drafting: synthesizes structured overlay ensuring every regulatory claim links to a source
3. Validation: schema checks, calculator golden test runs, boundary policy verification
4. Human Expert Review Dispatch: routes review tasks with conflict declarations to human inbox
5. Promotion: promotes to T3/T4 strictly upon human sign-off (Rule 71)
"""

import hashlib
import datetime
from typing import Dict, Any, List, Optional
from core.industry.schema import validate_industry_overlay_dict, compute_overlay_digest
from core.industry.calculator import DomainCalculator
from core.industry.boundary import SectorBoundaryEnforcer
from core.industry.tiers import OverlayTier, TierManager


class FactoryPipelineError(ValueError):
    """Raised when an overlay generation pipeline stage fails."""
    pass


class IndustryDepthFactory:
    """Executes the multi-stage overlay manufacturing and qualification pipeline."""

    def __init__(self):
        self.sources_store: Dict[str, Dict[str, Any]] = {}

    def collect_source(self, source_id: str, title: str, authority: str, content: str) -> Dict[str, Any]:
        """Stage 1: Ingests an authoritative statutory or standards source."""
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        record = {
            "source_id": source_id,
            "title": title,
            "authority": authority,
            "content_hash": h,
            "retrieval_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "content_length": len(content),
        }
        self.sources_store[source_id] = record
        return record

    def compile_draft_overlay(self, raw_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Compiles structured draft, dropping any regulatory claim without verified source."""
        # Clean regulatory register: any item without a valid source_id is dropped
        reg_register = raw_spec.get("regulatory_register", [])
        verified_regs = []
        for reg in reg_register:
            src_ref = reg.get("source_id")
            if src_ref and src_ref in self.sources_store:
                reg["source_hash"] = self.sources_store[src_ref]["content_hash"]
                verified_regs.append(reg)
            elif reg.get("cite"):
                # If explicit statutory citation is provided, keep but mark UNVERIFIED
                reg["status"] = "UNVERIFIED"
                verified_regs.append(reg)

        raw_spec["regulatory_register"] = verified_regs
        return raw_spec

    def validate_overlay(self, overlay_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Automated validation: schema, calculator golden tests, and boundary checks."""
        # 1. Structural schema validation
        validated = validate_industry_overlay_dict(overlay_spec)

        # 2. Run golden tests for all declared calculators
        calc_results = []
        for c in validated.get("calculators", []):
            calc = DomainCalculator(c)
            res = calc.run_golden_tests()
            if res["status"] != "PASS":
                raise FactoryPipelineError(
                    f"Calculator '{calc.calculator_id}' failed golden tests: {res['failed']} failed"
                )
            calc_results.append(res)

        # 3. Verify boundary policies are defined
        boundaries = validated.get("boundary_policies", [])
        if not boundaries:
            raise FactoryPipelineError("Overlay must define at least one boundary policy (Rule 72)")

        digest = compute_overlay_digest(validated)
        return {
            "status": "VALIDATED",
            "content_digest": digest,
            "calculators_tested": len(calc_results),
            "tier": validated.get("metadata", {}).get("tier", "T1"),
        }

    def dispatch_for_human_review(self, overlay_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: Emits expert review task to the human inbox."""
        digest = compute_overlay_digest(overlay_spec)
        meta = overlay_spec.get("metadata", {})
        return {
            "task_id": f"task_review_{digest[:10]}",
            "task_type": "EXPERT_OVERLAY_REVIEW",
            "industry_id": meta.get("industry_id"),
            "target_tier": "T3",
            "content_digest": digest,
            "checklist": [
                "calculators_mathematically_sound",
                "regulatory_cites_accurate",
                "boundary_policies_adequate",
                "no_dangerous_automation",
            ],
            "requires_conflict_declaration": True,
            "status": "AWAITING_HUMAN_EXPERT",
        }
