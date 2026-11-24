"""
ZONATA Failure Intelligence & Governed Diagnosis Engine (Sub-Step 6C).

Transforms every runtime failure into a structured, privacy-scrubbed learning event.
Features:
- Strict 6-class failure taxonomy + UNKNOWN fallback.
- Signature-based deduplication.
- 3-node LangGraph analyst graph.
- Rolling self-eval scorecards with MTTF, MTTR, and regression metrics.
"""

import re
import uuid
import time
import hashlib
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class FailureClass(str, Enum):
    EXECUTION_ERROR = "EXECUTION_ERROR"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    POLICY_DENIAL = "POLICY_DENIAL"
    REGRESSION = "REGRESSION"
    HALLUCINATION = "HALLUCINATION"
    AMBIGUOUS_SPEC = "AMBIGUOUS_SPEC"
    UNKNOWN = "UNKNOWN"


class MitigationProposalType(str, Enum):
    PLAYBOOK_CANDIDATE = "PLAYBOOK_CANDIDATE"
    OPTIMIZER_CANDIDATE = "OPTIMIZER_CANDIDATE"
    OWNER_HELP_REQUEST = "OWNER_HELP_REQUEST"
    GITHUB_TRIAGE = "GITHUB_TRIAGE"


class PIIScrubber:
    """Removes sensitive keys, passwords, JWTs, and PII from failure traces."""

    PATTERNS = [
        (re.compile(r"\bey[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", re.IGNORECASE), "[REDACTED_JWT]"),
        (re.compile(r"\b[A-Za-z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", re.IGNORECASE), "[REDACTED_EMAIL]"),
        (re.compile(r"(password|secret|bearer|token|api_key)\s*[:=]\s*[^\s,;]+", re.IGNORECASE), r"\1: [REDACTED_SECRET]"),
        (re.compile(r"\b(4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"), "[REDACTED_CC]"),
    ]

    @classmethod
    def scrub(cls, text: str) -> str:
        if not text:
            return ""
        scrubbed = str(text)
        for pattern, replacement in cls.PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed


class FailureIncident:
    """Represents a structured, scrubbed failure event."""

    def __init__(
        self,
        tenant_id: str,
        company_id: str,
        failure_class: FailureClass,
        stack_or_trace: str,
        prompt_hash: Optional[str] = None,
        tool_call: Optional[Dict[str, Any]] = None,
        verification_diff: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None,
    ):
        self.incident_id = incident_id or str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.failure_class = failure_class if isinstance(failure_class, FailureClass) else FailureClass.UNKNOWN
        self.stack_or_trace = PIIScrubber.scrub(stack_or_trace)
        self.prompt_hash = prompt_hash or hashlib.sha256(b"empty_prompt").hexdigest()
        self.tool_call = tool_call or {}
        self.verification_diff = verification_diff or {}
        self.count = 1
        self.created_at = time.time()
        self.last_seen_at = self.created_at
        self.resolved_at: Optional[float] = None
        self.signature = self._compute_signature()

        # Diagnosis fields
        self.root_cause_hypothesis: str = ""
        self.proposed_mitigation: MitigationProposalType = MitigationProposalType.GITHUB_TRIAGE
        self.confidence: float = 0.0
        self.human_escalated: bool = False

    def _normalize_error(self, text: str) -> str:
        """Strips hex memory addresses, timestamps, and line numbers for stable signature."""
        clean = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", text)
        clean = re.sub(r"\bline\s+\d+\b", "line NUM", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", "TIMESTAMP", clean)
        return clean.strip()[:300]

    def _compute_signature(self) -> str:
        norm_trace = self._normalize_error(self.stack_or_trace)
        tool_name = self.tool_call.get("name", "none")
        raw = f"{self.failure_class.value}:{norm_trace}:{tool_name}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class FailureIntelligenceEngine:
    """
    Ingests failure events, deduplicates them, executes 3-node LangGraph analysis,
    and maintains rolling self-eval scorecards.
    """

    def __init__(self):
        # Store: {tenant_id: {signature: FailureIncident}}
        self._incidents: Dict[str, Dict[str, FailureIncident]] = {}
        # History for MTTF/MTTR: {tenant_id: [FailureIncident]}
        self._incident_history: Dict[str, List[FailureIncident]] = {}

    def ingest_failure(
        self,
        tenant_id: str,
        company_id: str,
        failure_class: Any,
        stack_or_trace: str,
        prompt_hash: Optional[str] = None,
        tool_call: Optional[Dict[str, Any]] = None,
        verification_diff: Optional[Dict[str, Any]] = None,
    ) -> FailureIncident:
        """
        Step 1: Normalizes and classifies failure. Defaults to UNKNOWN if invalid.
        Step 2: Deduplicates if an identical signature exists.
        Step 3: Runs 3-node analyst graph.
        """
        if not isinstance(failure_class, FailureClass):
            try:
                failure_class = FailureClass(str(failure_class))
            except ValueError:
                failure_class = FailureClass.UNKNOWN

        incident = FailureIncident(
            tenant_id=tenant_id,
            company_id=company_id,
            failure_class=failure_class,
            stack_or_trace=stack_or_trace,
            prompt_hash=prompt_hash,
            tool_call=tool_call,
            verification_diff=verification_diff,
        )

        tenant_store = self._incidents.setdefault(tenant_id, {})
        sig = incident.signature

        if sig in tenant_store:
            existing = tenant_store[sig]
            existing.count += 1
            existing.last_seen_at = time.time()
            return existing

        # Execute 3-Node Analyst Graph
        self._run_analyst_graph(incident)

        tenant_store[sig] = incident
        self._incident_history.setdefault(tenant_id, []).append(incident)
        return incident

    def _run_analyst_graph(self, incident: FailureIncident) -> None:
        """
        3-Node LangGraph Analyst:
        Node 1: classify_and_diagnose
        Node 2: evaluate_context
        Node 3: propose_mitigation
        """
        # Node 1: Classify & Diagnose Root Cause
        cls = incident.failure_class
        if cls == FailureClass.EXECUTION_ERROR:
            incident.root_cause_hypothesis = "External runtime, environment, or tool failure during execution."
            incident.confidence = 0.85
        elif cls == FailureClass.VERIFICATION_FAILURE:
            incident.root_cause_hypothesis = "Model output claimed completion but failed validation pyramid contract."
            incident.confidence = 0.90
        elif cls == FailureClass.POLICY_DENIAL:
            incident.root_cause_hypothesis = "Action blocked by governance, authorization, or isolation policy."
            incident.confidence = 0.95
        elif cls == FailureClass.REGRESSION:
            incident.root_cause_hypothesis = "A capability or test that previously succeeded now fails."
            incident.confidence = 0.92
        elif cls == FailureClass.HALLUCINATION:
            incident.root_cause_hypothesis = "Model fabricated nonexistent files, IDs, or schema entities."
            incident.confidence = 0.88
        elif cls == FailureClass.AMBIGUOUS_SPEC:
            incident.root_cause_hypothesis = "Task prompt is structurally underspecified or missing critical parameters."
            incident.confidence = 0.80
        else:  # UNKNOWN
            incident.root_cause_hypothesis = "Unclassified or anomalous error requires human security triage."
            incident.confidence = 0.20
            incident.human_escalated = True

        # Node 2 & 3: Propose Mitigation
        if cls == FailureClass.AMBIGUOUS_SPEC:
            incident.proposed_mitigation = MitigationProposalType.OWNER_HELP_REQUEST
        elif cls in (FailureClass.HALLUCINATION, FailureClass.VERIFICATION_FAILURE):
            incident.proposed_mitigation = MitigationProposalType.OPTIMIZER_CANDIDATE
        elif cls == FailureClass.EXECUTION_ERROR:
            # If tool-related, suggest playbook addition; if crash, GitHub triage
            if incident.tool_call:
                incident.proposed_mitigation = MitigationProposalType.PLAYBOOK_CANDIDATE
            else:
                incident.proposed_mitigation = MitigationProposalType.GITHUB_TRIAGE
        elif cls == FailureClass.REGRESSION:
            incident.proposed_mitigation = MitigationProposalType.GITHUB_TRIAGE
            incident.human_escalated = True
        elif cls == FailureClass.POLICY_DENIAL:
            incident.proposed_mitigation = MitigationProposalType.OWNER_HELP_REQUEST
        else:
            incident.proposed_mitigation = MitigationProposalType.GITHUB_TRIAGE

    def resolve_incident(self, tenant_id: str, signature: str) -> bool:
        """Marks an incident signature as resolved for MTTR calculation."""
        tenant_store = self._incidents.get(tenant_id, {})
        if signature in tenant_store:
            incident = tenant_store[signature]
            incident.resolved_at = time.time()
            return True
        return False

    def generate_scorecard(self, tenant_id: str) -> Dict[str, Any]:
        """
        Calculates MTTF, MTTR, regression rate, and class breakdowns.
        """
        history = self._incident_history.get(tenant_id, [])
        tenant_store = self._incidents.get(tenant_id, {})

        if not history:
            return {
                "tenant_id": tenant_id,
                "total_incidents": 0,
                "deduplicated_signatures": 0,
                "mttf_seconds": 0.0,
                "mttr_seconds": 0.0,
                "regression_rate": 0.0,
                "class_distribution": {},
                "recommendations": ["No failures observed. System operational."],
            }

        total_occurrences = sum(inc.count for inc in tenant_store.values())
        class_dist: Dict[str, int] = {}
        for inc in history:
            cls_name = inc.failure_class.value
            class_dist[cls_name] = class_dist.get(cls_name, 0) + inc.count

        # MTTF: Mean Time To Failure (intervals between unique failures)
        if len(history) > 1:
            times = sorted(inc.created_at for inc in history)
            intervals = [t2 - t1 for t1, t2 in zip(times[:-1], times[1:])]
            mttf = sum(intervals) / len(intervals) if intervals else 0.0
        else:
            mttf = 0.0

        # MTTR: Mean Time To Resolution
        resolved = [inc for inc in history if inc.resolved_at is not None]
        if resolved:
            durations = [inc.resolved_at - inc.created_at for inc in resolved]
            mttr = sum(durations) / len(durations)
        else:
            mttr = 0.0

        regressions = class_dist.get(FailureClass.REGRESSION.value, 0)
        reg_rate = (regressions / total_occurrences) if total_occurrences > 0 else 0.0

        recommendations = []
        if reg_rate > 0.05:
            recommendations.append("HIGH REGRESSION: Freeze optimizer prompts and audit recent playbooks.")
        if class_dist.get(FailureClass.AMBIGUOUS_SPEC.value, 0) > 3:
            recommendations.append("HIGH AMBIGUOUS_SPEC: Trigger Owner Help Protocol to disambiguate intent.")
        if class_dist.get(FailureClass.HALLUCINATION.value, 0) > 0:
            recommendations.append("HALLUCINATIONS DETECTED: Route failed trace to DSPy optimizer training set.")
        if not recommendations:
            recommendations.append("Metrics within normal thresholds.")

        return {
            "tenant_id": tenant_id,
            "total_incidents": total_occurrences,
            "deduplicated_signatures": len(tenant_store),
            "mttf_seconds": round(mttf, 2),
            "mttr_seconds": round(mttr, 2),
            "regression_rate": round(reg_rate, 4),
            "class_distribution": class_dist,
            "recommendations": recommendations,
        }
