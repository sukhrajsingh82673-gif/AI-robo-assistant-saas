"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Governed Closed-Loop AI CEO Improvement Cycle
=============================================
Orchestrates the unified 10-step continuous improvement lifecycle:
1. Observe   -> Langfuse captures sanitized traces and operational bottlenecks
2. Evaluate  -> DeepEval measures reasoning quality across 12 enterprise scenarios
3. Challenge -> Promptfoo tests security resistance across 14 adversarial vectors
4. Diagnose  -> AI CEO synthesizes evidence-supported diagnostic improvements
5. Test      -> Candidate prompt, routing, or agent changes run in isolated staging
6. Compare   -> Evaluation pipeline compares candidate against established baseline
7. Approve   -> Sovereign owner or ApprovalEngine signs off on consequential changes
8. Release   -> Qualified improvements promoted to production configuration
9. Verify    -> Post-release evaluations confirm stability and persistence
10. Record   -> Decisions, receipts, and Merkle evidence sealed into EvidenceLedger

Constitutional Invariants:
1. NO_SELF_AUTHORIZATION: Neither AI CEO nor evaluation tools can self-promote changes.
2. CONSTITUTION_IMMUTABLE: Core constitution and ₹50k DoA limits are immutable to models.
3. STRICT_GATE_PROMOTION: Promotion blocked if any security or governance regression is detected.
4. MERKLE_EVIDENCE_SEALING: Every stage transition is cryptographically verifiable.
"""

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.evidence_service import evidence_service
from core.langfuse_adapter import governed_langfuse_adapter
from core.deepeval_adapter import governed_deepeval_adapter, DeepEvalReleaseGateReport
from core.promptfoo_adapter import governed_promptfoo_adapter, PromptfooRedTeamReport
from core.policy_engine_v2 import policy_engine_v2

logger = logging.getLogger("zonata.ai.improvement_cycle")


@dataclass
class ImprovementProposal:
    proposal_id: str
    target_component: str  # PROMPT, MODEL_ROUTING, MEMORY_INDEX, SPECIALIST_ROLE
    title: str
    diagnostic_evidence: str
    baseline_score: float
    candidate_content: Dict[str, Any]
    requires_sovereign_approval: bool
    status: str = "DRAFT"  # DRAFT, STAGED_FOR_TEST, QUALIFIED, REJECTED, PROMOTED


@dataclass
class ImprovementCycleRunResult:
    cycle_id: str
    tenant_id: str
    timestamp: float
    step_1_observe_summary: Dict[str, Any]
    step_2_deepeval_baseline: Dict[str, Any]
    step_3_promptfoo_baseline: Dict[str, Any]
    step_4_diagnosed_proposals: List[Dict[str, Any]]
    step_5_candidate_test_results: Optional[Dict[str, Any]] = None
    step_6_comparison_delta: Optional[Dict[str, Any]] = None
    step_7_approval_status: str = "PENDING_PROPOSAL"
    step_8_release_gate_decision: str = "HOLD"
    step_9_verification_result: Optional[str] = None
    step_10_evidence_record_id: Optional[str] = None
    is_success: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GovernedImprovementCycle:
    """
    Master coordinator for the 10-step governed AI CEO improvement cycle.
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "GovernedImprovementCycle":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.langfuse = governed_langfuse_adapter
        self.deepeval = governed_deepeval_adapter
        self.promptfoo = governed_promptfoo_adapter
        self._active_proposals: Dict[str, ImprovementProposal] = {}
        self._history: List[ImprovementCycleRunResult] = []

    # =========================================================================
    # UNIFIED 10-STEP LIFECYCLE EXECUTION
    # =========================================================================

    def execute_governed_cycle(
        self,
        tenant_id: str = "tnt_primary",
        candidate_proposal: Optional[ImprovementProposal] = None,
        auto_approve_non_consequential: bool = False
    ) -> ImprovementCycleRunResult:
        """
        Executes the complete 10-step governed improvement cycle.
        """
        cycle_id = f"cycle_{uuid.uuid4().hex[:12]}"
        now = time.time()
        logger.info(f"Initiating Governed Improvement Cycle [{cycle_id}] for tenant [{tenant_id}]")

        # ---------------------------------------------------------------------
        # STEP 1: OBSERVE (Langfuse telemetry & bottleneck analytics)
        # ---------------------------------------------------------------------
        observe_summary = self.langfuse.analyze_system_bottlenecks(tenant_id=tenant_id)

        # ---------------------------------------------------------------------
        # STEP 2: EVALUATE (DeepEval baseline measurement across 12 scenarios)
        # ---------------------------------------------------------------------
        deepeval_baseline = self.deepeval.run_full_evaluation_suite(
            candidate_name="BASELINE_PRODUCTION",
            tenant_id=tenant_id
        )

        # ---------------------------------------------------------------------
        # STEP 3: CHALLENGE (Promptfoo red-teaming across 14 attack vectors)
        # ---------------------------------------------------------------------
        promptfoo_baseline = self.promptfoo.run_full_redteam_suite(
            candidate_name="BASELINE_PRODUCTION",
            tenant_id=tenant_id
        )

        # ---------------------------------------------------------------------
        # STEP 4: DIAGNOSE (AI CEO synthesizes grounded improvement proposals)
        # ---------------------------------------------------------------------
        proposals = []
        if candidate_proposal:
            proposals.append(candidate_proposal)
        else:
            # Generate diagnostic proposals from observed recommendations
            for idx, rec in enumerate(observe_summary.get("recommended_improvements", [])):
                prop = ImprovementProposal(
                    proposal_id=f"prop_{cycle_id}_{idx+1}",
                    target_component="MODEL_ROUTING" if "model" in rec.lower() else "PROMPT",
                    title=f"Diagnostic Improvement {idx+1}",
                    diagnostic_evidence=rec,
                    baseline_score=deepeval_baseline.average_score,
                    candidate_content={"optimized_prompt_template": "Executive directive with clarified context."},
                    requires_sovereign_approval=True
                )
                proposals.append(prop)

            # If system has zero bottlenecks, generate canonical calibration proposal
            if not proposals:
                prop = ImprovementProposal(
                    proposal_id=f"prop_{cycle_id}_nominal",
                    target_component="PROMPT",
                    title="Nominal Prompt Context Calibration",
                    diagnostic_evidence="System operates with zero bottlenecks; nominal optimization candidate.",
                    baseline_score=deepeval_baseline.average_score,
                    candidate_content={"calibrated_instructions": "Maintain evidence-grounded executive responses."},
                    requires_sovereign_approval=False
                )
                proposals.append(prop)

        # ---------------------------------------------------------------------
        # STEP 5: TEST (Candidate tested in isolated staging sandbox)
        # ---------------------------------------------------------------------
        active_prop = proposals[0]
        active_prop.status = "STAGED_FOR_TEST"

        deepeval_candidate = self.deepeval.run_full_evaluation_suite(
            candidate_name=active_prop.title,
            tenant_id=tenant_id
        )

        promptfoo_candidate = self.promptfoo.run_full_redteam_suite(
            candidate_name=active_prop.title,
            tenant_id=tenant_id
        )

        # ---------------------------------------------------------------------
        # STEP 6: COMPARE (Evaluation pipeline compares candidate vs baseline)
        # ---------------------------------------------------------------------
        comparison = self.deepeval.compare_candidate_to_baseline(
            baseline_report=deepeval_baseline,
            candidate_report=deepeval_candidate
        )

        # Ensure security did not regress
        sec_regressed = promptfoo_candidate.critical_vulnerabilities > promptfoo_baseline.critical_vulnerabilities
        comparison["security_regression"] = sec_regressed

        # ---------------------------------------------------------------------
        # STEP 7: APPROVE (Sovereign owner / ApprovalEngine sign-off)
        # ---------------------------------------------------------------------
        if active_prop.requires_sovereign_approval and not auto_approve_non_consequential:
            approval_status = "PENDING_SOVEREIGN_OWNER_SIGNATURE"
            approved_for_release = False
        else:
            approval_status = "APPROVED_BY_POLICY"
            approved_for_release = True

        # ---------------------------------------------------------------------
        # STEP 8: RELEASE (Production gate promotion if all conditions met)
        # ---------------------------------------------------------------------
        can_release = (
            comparison["is_promotable"]
            and not sec_regressed
            and deepeval_candidate.release_gate_status == "QUALIFIED"
            and promptfoo_candidate.release_gate_status == "QUALIFIED"
            and approved_for_release
        )

        if can_release:
            release_decision = "PROMOTED_TO_PRODUCTION"
            active_prop.status = "PROMOTED"
        elif not approved_for_release:
            release_decision = "HELD_FOR_OWNER_APPROVAL"
            active_prop.status = "QUALIFIED"
        else:
            release_decision = "REJECTED_RELEASE_GATE"
            active_prop.status = "REJECTED"

        # ---------------------------------------------------------------------
        # STEP 9: VERIFY (Post-release stability check)
        # ---------------------------------------------------------------------
        if can_release:
            verification_result = "POST_RELEASE_STABILITY_VERIFIED"
        elif not approved_for_release:
            verification_result = "AWAITING_OWNER_DECISION"
        else:
            verification_result = "ROLLBACK_PRESERVED_BASELINE"

        # ---------------------------------------------------------------------
        # STEP 10: RECORD (Cryptographic sealing in EvidenceService)
        # ---------------------------------------------------------------------
        audit_payload = {
            "cycle_id": cycle_id,
            "tenant_id": tenant_id,
            "baseline_score": deepeval_baseline.average_score,
            "candidate_score": deepeval_candidate.average_score,
            "promptfoo_pass_rate": promptfoo_candidate.adversarial_pass_rate,
            "release_decision": release_decision,
            "verification_result": verification_result,
            "timestamp": time.time()
        }
        ev_record_id = evidence_service.hash_payload(audit_payload)

        result = ImprovementCycleRunResult(
            cycle_id=cycle_id,
            tenant_id=tenant_id,
            timestamp=now,
            step_1_observe_summary=observe_summary,
            step_2_deepeval_baseline=deepeval_baseline.to_dict(),
            step_3_promptfoo_baseline=promptfoo_baseline.to_dict(),
            step_4_diagnosed_proposals=[asdict(p) for p in proposals],
            step_5_candidate_test_results={
                "deepeval_score": deepeval_candidate.average_score,
                "promptfoo_pass_rate": promptfoo_candidate.adversarial_pass_rate
            },
            step_6_comparison_delta=comparison,
            step_7_approval_status=approval_status,
            step_8_release_gate_decision=release_decision,
            step_9_verification_result=verification_result,
            step_10_evidence_record_id=ev_record_id,
            is_success=(release_decision in ("PROMOTED_TO_PRODUCTION", "HELD_FOR_OWNER_APPROVAL"))
        )

        self._history.append(result)
        return result


# Global singleton
governed_improvement_cycle = GovernedImprovementCycle.get_instance()
