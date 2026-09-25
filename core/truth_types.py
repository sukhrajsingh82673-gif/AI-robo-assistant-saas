"""
RoboAssistant Company OS 2.0 — Truth, Cognition, and Execution Types
Constitutional data structures defining truth states, planning horizons,
autonomy levels, operational reasoning, and failure taxonomy.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time

class TruthState(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    OBSERVED = "OBSERVED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    AI_INFERRED = "AI_INFERRED"
    SIMULATED = "SIMULATED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class PlanningHorizon(str, Enum):
    IMMEDIATE = "IMMEDIATE"       # Real-time events, outages, immediate failures
    TODAY = "TODAY"               # Daily missions, night audit, reconciliations
    STRATEGIC = "STRATEGIC"       # Weekly/monthly goals: bookings, churn, margins
    LONG_TERM = "LONG_TERM"       # Quarters/years: expansion, transformation, unit economics

class AutonomyLevel(str, Enum):
    L0_OBSERVE = "L0_OBSERVE"
    L1_RECOMMEND = "L1_RECOMMEND"
    L2_EXECUTE_WITH_APPROVAL = "L2_EXECUTE_WITH_APPROVAL"
    L3_EXECUTE_WITHIN_RULES = "L3_EXECUTE_WITHIN_RULES"
    L4_DELEGATED_AUTONOMY = "L4_DELEGATED_AUTONOMY"

class ExecutionStage(str, Enum):
    OBSERVING = "OBSERVING"
    ANALYZING = "ANALYZING"
    CHECKING_AUTHORITY = "CHECKING_AUTHORITY"
    PLANNING = "PLANNING"
    SIMULATING = "SIMULATING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    PREPARING = "PREPARING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    ESCALATING = "ESCALATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class FailureCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    CONFIGURATION = "CONFIGURATION"
    AUTHORIZATION = "AUTHORIZATION"
    CAPABILITY = "CAPABILITY"
    NETWORK = "NETWORK"
    APPLICATION = "APPLICATION"
    DATA = "DATA"
    MODEL = "MODEL"
    HOST = "HOST"
    SECURITY = "SECURITY"
    UNKNOWN = "UNKNOWN"

@dataclass
class CognitiveFact:
    key: str
    value: Any
    source: str
    truth_state: TruthState
    confidence: float = 1.0
    freshness: float = field(default_factory=time.time)
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source,
            "truth_state": self.truth_state.value,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "verified": self.verified,
            "metadata": self.metadata
        }

@dataclass
class OperationalReasoning:
    objective: str
    why: str
    evidence: str
    options: List[str]
    selected_approach: str
    authority: str
    cost: float
    expected_result: str
    risk: str
    reversibility: str
    verification_method: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "why": self.why,
            "evidence": self.evidence,
            "options": self.options,
            "selected_approach": self.selected_approach,
            "authority": self.authority,
            "cost": self.cost,
            "expected_result": self.expected_result,
            "risk": self.risk,
            "reversibility": self.reversibility,
            "verification_method": self.verification_method,
            "timestamp": self.timestamp
        }

@dataclass
class FailureDiagnostic:
    failure_type: FailureCategory
    stage: ExecutionStage
    cause: str
    evidence: str
    retryable: bool
    rollback_state: str
    affected_resources: List[str]
    recommended_recovery: str
    human_intervention_required: bool
    timestamp: float = field(default_factory=time.time)
