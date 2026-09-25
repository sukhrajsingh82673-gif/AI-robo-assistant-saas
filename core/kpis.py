"""
RoboAssistant Company OS 1.0 — Dynamic KPI Engine
Implements Section 89:
Dynamic multi-level KPI evaluation across Company, Department, and Mission.
Invariant: Never compare incompatible metrics; distinguish VERIFIED from ESTIMATED.
"""

from typing import Dict, Any, List, Optional
import time
import uuid

class KpiVerificationState:
    VERIFIED = "VERIFIED"
    CALCULATED = "CALCULATED"
    PENDING_EVIDENCE = "PENDING_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"

class DynamicKpiEngine:
    """
    Evaluates and records operational and financial KPIs against baselines and targets.
    """

    @staticmethod
    def register_kpi(
        tenant_id: str,
        company_id: str,
        name: str,
        definition: str,
        unit: str,
        target: float,
        baseline: Optional[float] = None,
        source: str = "SYSTEM_TELEMETRY",
        department_id: Optional[str] = None
    ) -> Dict[str, Any]:
        kpi_id = f"kpi_{uuid.uuid4().hex[:8]}"
        return {
            "kpi_id": kpi_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "department_id": department_id,
            "name": name,
            "definition": definition,
            "unit": unit,
            "target": target,
            "baseline": baseline,
            "actual": None,
            "verification_status": KpiVerificationState.UNAVAILABLE,
            "source": source,
            "last_updated": time.time()
        }

    @staticmethod
    def record_kpi_actual(
        kpi_record: Dict[str, Any],
        actual_value: float,
        evidence_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Updates actual KPI measurement. Stamped VERIFIED only if cryptographic evidence exists.
        """
        status = KpiVerificationState.VERIFIED if evidence_hash else KpiVerificationState.CALCULATED
        kpi_record["actual"] = actual_value
        kpi_record["verification_status"] = status
        kpi_record["evidence_hash"] = evidence_hash
        kpi_record["last_updated"] = time.time()

        # Target achievement
        target = kpi_record.get("target", 0.0)
        kpi_record["target_achieved"] = (actual_value >= target) if target > 0 else False
        return kpi_record
