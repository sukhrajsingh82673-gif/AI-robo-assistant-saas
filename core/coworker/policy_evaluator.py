"""
ZONATA Universal AI Co-worker Fabric — Policy Evaluator & Risk Classifier
Evaluates capability requests against tenant policy, worker authority scope,
and risk thresholds.
Mandates explicit human approval for high-risk financial, purchasing, or destructive tasks.
"""

from typing import Dict, List, Optional, Any, Tuple
from .contracts import RiskLevel, CapabilityDefinition, CoworkerProfile

class RiskClassifier:
    """Classifies risk tiers of capability operations."""

    @staticmethod
    def classify(capability_id: str, params: Dict[str, Any]) -> RiskLevel:
        cap_lower = capability_id.lower()

        # Critical: Financial transactions, payments, legal commitments, credential changes
        if any(k in cap_lower for k in ["purchase", "payment", "credential", "revoke_root", "transfer_money", "financial"]):
            return RiskLevel.CRITICAL

        # High: Destructive filesystem deletion, user termination, visual CUA without bounds
        if any(k in cap_lower for k in ["delete", "drop", "terminate", "format", "visual"]):
            return RiskLevel.HIGH

        # Medium: Business mutations (CRM updates, emails, database writes, workflow replay)
        if any(k in cap_lower for k in ["update", "send", "write", "workflow", "set_text"]):
            return RiskLevel.MEDIUM

        # Low: Read-only, inspection, navigation, screenshots, reports
        return RiskLevel.LOW


class CoworkerPolicyEvaluator:
    """Evaluates whether a worker is authorized to execute a capability."""

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def evaluate_request(
        self,
        worker: CoworkerProfile,
        capability: CapabilityDefinition,
        params: Dict[str, Any]
    ) -> Tuple[bool, bool, RiskLevel, Optional[str]]:
        """
        Returns:
        (is_allowed, requires_human_approval, assessed_risk, denial_reason)
        """
        # 1. Tenant boundary check
        if worker.tenant_id != self.tenant_id:
            return False, False, RiskLevel.CRITICAL, f"Tenant isolation violation: worker {worker.worker_id} belongs to {worker.tenant_id}"

        # 2. Worker status check
        if worker.status != "ACTIVE":
            return False, False, RiskLevel.HIGH, f"Worker {worker.worker_id} is currently {worker.status}"

        # 3. Classify dynamic risk
        assessed_risk = RiskClassifier.classify(capability.capability_id, params)

        # 4. Check worker risk limit
        risk_hierarchy = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
        if risk_hierarchy[assessed_risk] > risk_hierarchy[worker.risk_limit]:
            # Over worker's autonomous risk ceiling -> requires human approval or denial
            if assessed_risk == RiskLevel.CRITICAL:
                return True, True, assessed_risk, "Risk exceeds worker autonomous limit; requires mandatory human approval"

        # 5. Check forbidden actions in worker authority scope
        forbidden = worker.authority_scope.get("forbidden_actions", [])
        if capability.capability_id in forbidden:
            return False, False, assessed_risk, f"Capability '{capability.capability_id}' is explicitly forbidden for worker {worker.worker_id}"

        # 6. Check specific financial authority
        if assessed_risk == RiskLevel.CRITICAL:
            if not worker.authority_scope.get("financial_transactions", False):
                # Must be escalated for human approval
                return True, True, assessed_risk, "Financial execution requires explicit Human Owner approval"

        # 7. Check if capability definition statically mandates approval
        requires_human = capability.requires_human_approval or (assessed_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL])

        return True, requires_human, assessed_risk, None
