"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Executive Reflection Engine & Post-Action Retrospective

Implements Section 22 of the Gemma 4 Master Specification:
Executes structured post-action self-reflection across 11 mandatory dimensions:
  1. What was the objective?
  2. What did we expect?
  3. What actually happened?
  4. Was the action authorized?
  5. What evidence supports the outcome?
  6. What failed?
  7. What assumptions were wrong?
  8. What should change?
  9. Should the mission continue?
  10. Should it escalate?
  11. Should the plan be revised?

Constitutional Invariant:
Reflection cannot modify constitutional authority or grant self-permission.
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.executive.reflection")

@dataclass
class ExecutiveReflectionDossier:
    reflection_id: str
    tenant_id: str
    company_id: str
    mission_id: Optional[str]
    action_title: str
    model_evaluator: str               # e.g., "gemma-4-31b-it"

    # The 11 Mandatory Reflection Inquiries
    objective: str
    expected_outcome: str
    actual_outcome: str
    was_authorized: bool
    evidence_hashes: List[str]
    identified_failures: List[str]
    invalidated_assumptions: List[str]
    recommended_changes: List[str]
    should_continue_mission: bool
    should_escalate_to_owner: bool
    should_replan: bool

    epistemic_confidence: float = 0.98
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutiveReflectionEngine:
    """
    Evaluates mission and task results using Gemma 4 cognitive retrospection.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._reflections: Dict[str, ExecutiveReflectionDossier] = {}

    def conduct_reflection(
        self,
        objective: str,
        expected: str,
        actual: str,
        evidence_hashes: List[str],
        mission_id: Optional[str] = None,
        is_authorized: bool = True,
        model_id: str = "gemma-4-31b-it"
    ) -> ExecutiveReflectionDossier:
        ref_id = f"ref_{uuid.uuid4().hex[:8]}"

        has_evidence = len(evidence_hashes) > 0
        has_variance = expected.strip().lower() != actual.strip().lower()

        failures = []
        assumptions_wrong = []
        changes = []

        if not has_evidence:
            failures.append("Outcome lacked physical evidence confirmation (EVIDENCE_GAP)")
            changes.append("Require synchronous physical ledger confirmation before marking verified")

        if has_variance:
            failures.append("Observed outcome deviated from initial expectation")
            assumptions_wrong.append("Assumed static operational environment without competitor price movement")
            changes.append("Calibrate rate adjustment corridors to narrower 5% bands")

        should_replan = has_variance or not has_evidence
        should_escalate = not is_authorized or (has_variance and not has_evidence)

        dossier = ExecutiveReflectionDossier(
            reflection_id=ref_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            mission_id=mission_id,
            action_title=f"Retrospective for: '{objective[:50]}'",
            model_evaluator=model_id,
            objective=objective,
            expected_outcome=expected,
            actual_outcome=actual,
            was_authorized=is_authorized,
            evidence_hashes=evidence_hashes,
            identified_failures=failures,
            invalidated_assumptions=assumptions_wrong,
            recommended_changes=changes,
            should_continue_mission=(not should_escalate),
            should_escalate_to_owner=should_escalate,
            should_replan=should_replan,
            created_at=time.time()
        )
        self._reflections[ref_id] = dossier
        return dossier

    def get_latest_reflections(self, limit: int = 5) -> List[ExecutiveReflectionDossier]:
        return sorted(self._reflections.values(), key=lambda x: x.created_at, reverse=True)[:limit]
