"""
Rule 72 Hard Sector Boundary Enforcer
=====================================
The platform never makes clinical decisions, gives legal advice, gives investment,
credit, or insurance advice to consumers, takes final underwriting/lending decisions,
or writes to safety-critical plant, medical, or vehicle controls.

Boundary violations are refused, logged, and routed to a licensed human.
"""

import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("zonata.industry.boundary")


class BoundaryViolationError(PermissionError):
    """Raised when an operation violates a statutory sector boundary (Rule 72)."""
    def __init__(self, boundary_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"Rule 72 Hard Boundary Violation [{boundary_type}]: {message}")
        self.boundary_type = boundary_type
        self.details = details or {}


# Pre-defined prohibited action patterns per sector boundary
PROHIBITED_INTENT_PATTERNS = {
    "CLINICAL_DECISION": [
        re.compile(r"\b(prescribe|diagnose|dosage|titrate|administer|treatment plan for patient)\b", re.IGNORECASE),
        re.compile(r"\b(clinical diagnosis|contraindication determination|emergency triage decision)\b", re.IGNORECASE),
    ],
    "LEGAL_ADVICE": [
        re.compile(r"\b(legal advice|guarantee legal outcome|file lawsuit on behalf|advising you as counsel)\b", re.IGNORECASE),
        re.compile(r"\b(attorney-client privilege established|formal legal opinion on liability)\b", re.IGNORECASE),
    ],
    "CONSUMER_CREDIT_INVESTMENT_ADVICE": [
        re.compile(r"\b(buy this stock|sell this equity|approved your mortgage|guaranteed investment return)\b", re.IGNORECASE),
        re.compile(r"\b(personal loan approval|consumer credit score decision|fiduciary portfolio recommendation)\b", re.IGNORECASE),
    ],
    "SAFETY_CRITICAL_CONTROL_WRITE": [
        re.compile(r"\b(override emergency scram|disable plant safety interlock|bypass pressure valve)\b", re.IGNORECASE),
        re.compile(r"\b(direct actuator write|actuate centrifuge|autonomous brake control write)\b", re.IGNORECASE),
    ],
}


class SectorBoundaryEnforcer:
    """Evaluates incoming operations against industry-declared and platform-wide boundary policies."""

    def __init__(self, overlay_boundaries: Optional[List[Dict[str, Any]]] = None):
        self.overlay_boundaries = overlay_boundaries or []

    def evaluate_intent(self, intent_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Scans input text and context for hard sector boundary violations.
        
        Returns {"status": "PERMITTED"} or raises BoundaryViolationError.
        """
        context = context or {}

        # 1. Check global platform prohibited intents
        for b_type, patterns in PROHIBITED_INTENT_PATTERNS.items():
            for p in patterns:
                match = p.search(intent_text)
                if match:
                    logger.critical(
                        "Sector boundary violation detected: [%s] matched '%s' in context %s",
                        b_type, match.group(0), context
                    )
                    raise BoundaryViolationError(
                        boundary_type=b_type,
                        message=f"Action '{match.group(0)}' violates hard safety/legal boundary. Routing to licensed human.",
                        details={"matched_token": match.group(0), "context": context}
                    )

        # 2. Check overlay-specific declarative boundary policies
        for b_policy in self.overlay_boundaries:
            b_name = b_policy.get("policy_id", "CUSTOM_BOUNDARY")
            keywords = b_policy.get("prohibited_terms", [])
            for term in keywords:
                if term.lower() in intent_text.lower():
                    logger.warning("Overlay boundary policy triggered: [%s] term '%s'", b_name, term)
                    raise BoundaryViolationError(
                        boundary_type=b_name,
                        message=b_policy.get("rejection_message", f"Operation blocked by overlay policy '{b_name}'"),
                        details={"matched_term": term, "escalation_role": b_policy.get("escalate_to", "human_supervisor")}
                    )

        return {"status": "PERMITTED", "verified": True}
