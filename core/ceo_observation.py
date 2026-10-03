"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — CEO Observation Engine & KPI Deviation Detector
Synthesizes multi-source telemetry into first-class structured observations and deviation signals.

Constitutional Invariants:
  UNKNOWN_IS_FIRST_CLASS (Missing, unreachable, or unverifiable evidence yields UNKNOWN, never assumed success)
  DETERMINISTIC_KPI_VARIANCE (Mathematical metric deviation: actual vs target vs baseline)
  PROVENANCE_AND_CONFIDENCE (Every observation records source, timestamp, confidence, and evidence ref)
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.db import db
from core.executive_events import create_executive_event

class ObservationType:
    NORMAL = "NORMAL"
    DEVIATION = "DEVIATION"
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    STALE_DATA = "STALE_DATA"

class ObservationConfidence:
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"

@dataclass
class ExecutiveObservation:
    observation_id: str
    tenant_id: str
    company_id: str
    observation_type: str
    category: str
    metric_name: Optional[str]
    baseline_value: Optional[float]
    target_value: Optional[float]
    actual_value: Optional[float]
    variance: Optional[float]
    trend: Optional[str]
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: str = ObservationConfidence.VERIFIED
    evidence_ref: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CEOObservationEngine:
    """
    Scans corporate subsystems and computes structured operational telemetry and KPI deviations.
    """
    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id

    def record_observation(
        self,
        observation_type: str,
        category: str,
        summary: str,
        metric_name: Optional[str] = None,
        baseline_value: Optional[float] = None,
        target_value: Optional[float] = None,
        actual_value: Optional[float] = None,
        trend: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        confidence: str = ObservationConfidence.VERIFIED,
        evidence_ref: Optional[str] = None
    ) -> ExecutiveObservation:
        """Records an authoritative structured observation."""
        now = time.time()
        variance = None
        if target_value is not None and actual_value is not None:
            variance = actual_value - target_value

        obs_id = f"obs_{uuid.uuid4().hex[:10]}"
        obs = ExecutiveObservation(
            observation_id=obs_id,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            observation_type=observation_type,
            category=category,
            metric_name=metric_name,
            baseline_value=baseline_value,
            target_value=target_value,
            actual_value=actual_value,
            variance=variance,
            trend=trend,
            summary=summary,
            details=details or {},
            confidence=confidence,
            evidence_ref=evidence_ref,
            created_at=now
        )

        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO executive_observations (
                    observation_id, tenant_id, company_id, observation_type,
                    category, metric_name, baseline_value, target_value,
                    actual_value, variance, trend, summary, details,
                    confidence, evidence_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs.observation_id, obs.tenant_id, obs.company_id, obs.observation_type,
                obs.category, obs.metric_name, obs.baseline_value, obs.target_value,
                obs.actual_value, obs.variance, obs.trend, obs.summary,
                json.dumps(obs.details), obs.confidence, obs.evidence_ref, obs.created_at
            ))
            conn.commit()

        if observation_type == ObservationType.DEVIATION:
            create_executive_event(
                event_type="KPIDeviationDetected",
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                payload={
                    "observation_id": obs.observation_id,
                    "metric": metric_name,
                    "variance": variance,
                    "trend": trend,
                    "confidence": confidence
                }
            )

        return obs

    def scan_kpi_deviations(
        self,
        current_metrics: Dict[str, Dict[str, Any]]
    ) -> List[ExecutiveObservation]:
        """
        Evaluates a dictionary of metric data against targets.
        Format of current_metrics:
        {
           "revpar": {"baseline": 3800.0, "target": 4500.0, "actual": 4720.0, "evidence": "ev_pms_982"},
           "csat": {"baseline": 4.5, "target": 4.6, "actual": 4.65, "evidence": "ev_csat_102"}
        }
        """
        observations = []
        for metric, data in current_metrics.items():
            baseline = data.get("baseline")
            target = data.get("target")
            actual = data.get("actual")
            evidence = data.get("evidence")
            confidence = data.get("confidence", ObservationConfidence.VERIFIED)

            if actual is None:
                # First-class UNKNOWN state! Never assume success when data is missing.
                obs = self.record_observation(
                    observation_type=ObservationType.UNKNOWN,
                    category="KPI_DATA_GAP",
                    summary=f"Missing metric data for '{metric}'. First-class UNKNOWN state triggered.",
                    metric_name=metric,
                    baseline_value=baseline,
                    target_value=target,
                    actual_value=None,
                    confidence=ObservationConfidence.UNKNOWN,
                    evidence_ref=None
                )
                observations.append(obs)
                continue

            variance = actual - target if target is not None else 0.0

            if target is not None and actual < target:
                trend = "NEGATIVE"
                obs_type = ObservationType.DEVIATION
                summary = f"KPI '{metric}' underperforming target: Actual {actual} < Target {target} (Variance: {variance:.2f})"
            elif target is not None and actual >= target:
                trend = "POSITIVE"
                obs_type = ObservationType.NORMAL
                summary = f"KPI '{metric}' achieved or exceeded target: Actual {actual} >= Target {target} (Variance: +{variance:.2f})"
            else:
                trend = "STABLE"
                obs_type = ObservationType.NORMAL
                summary = f"KPI '{metric}' recorded at {actual}"

            obs = self.record_observation(
                observation_type=obs_type,
                category="KPI_METRICS",
                summary=summary,
                metric_name=metric,
                baseline_value=baseline,
                target_value=target,
                actual_value=actual,
                trend=trend,
                details=data,
                confidence=confidence,
                evidence_ref=evidence
            )
            observations.append(obs)

        return observations

    def list_observations(
        self,
        observation_type: Optional[str] = None,
        limit: int = 50
    ) -> List[ExecutiveObservation]:
        with db.get_connection() as conn:
            query = "SELECT * FROM executive_observations WHERE tenant_id = ? AND company_id = ?"
            params = [self.tenant_id, self.company_id]
            if observation_type:
                query += " AND observation_type = ?"
                params.append(observation_type)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                ExecutiveObservation(
                    observation_id=r["observation_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    observation_type=r["observation_type"],
                    category=r["category"],
                    metric_name=r["metric_name"],
                    baseline_value=r["baseline_value"],
                    target_value=r["target_value"],
                    actual_value=r["actual_value"],
                    variance=r["variance"],
                    trend=r["trend"],
                    summary=r["summary"],
                    details=json.loads(r["details"] or "{}"),
                    confidence=r["confidence"],
                    evidence_ref=r["evidence_ref"],
                    created_at=r["created_at"]
                ) for r in rows
            ]
