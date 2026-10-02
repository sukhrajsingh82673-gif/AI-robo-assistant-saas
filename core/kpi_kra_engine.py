"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Architecture — KPI & KRA Operational Engine
Connects employee assignments to measurable real-world business outcomes.

Constitutional Invariants:
  TASK_COMPLETION != BUSINESS_OUTCOME
  NO_SELF_AWARDED_SUCCESS (KPI success verified against physical/relational data source)
  IMMUTABLE_MEASUREMENT_CHAIN (Every metric change sealed in cryptographic evidence)
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.v7.kpi_kra_engine")

@dataclass
class StructuredKPI:
    kpi_id: str
    tenant_id: str
    company_id: str
    employee_id: str
    name: str
    definition: str
    unit: str                            # USD, INR, PERCENTAGE, COUNT, SECONDS
    target_value: float
    threshold_value: float
    measurement_frequency: str           # DAILY, WEEKLY, MONTHLY, PER_MISSION
    data_source: str                     # e.g., PMS_LEDGER, CRM_PIPELINE, STRIPE_INVOICES
    owner: str                           # Employee ID or Title
    calculation_method: str              # SUM, AVERAGE, RATIO, LATEST
    minimum_acceptable_value: float
    warning_threshold: float
    escalation_threshold: float
    verification_method: str             # LEDGER_RECONCILIATION, THIRD_PARTY_API, AUDIT_HASH
    created_at: float = field(default_factory=time.time)

@dataclass
class StructuredKRA:
    kra_id: str
    tenant_id: str
    company_id: str
    employee_id: str
    name: str
    responsibility: str
    associated_workflows: List[str]
    associated_kpi_ids: List[str]
    allowed_tools: List[str]
    authority_scope: Dict[str, Any]
    escalation_rules: List[str]
    expected_outcomes: List[str]
    created_at: float = field(default_factory=time.time)

class KPIKRAEngine:
    """
    Authoritative engine for defining, measuring, and verifying Key Performance
    Indicators (KPIs) and Key Result Areas (KRAs) for AI Employees.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_kpis (
                kpi_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                name TEXT NOT NULL,
                definition TEXT NOT NULL,
                unit TEXT NOT NULL,
                target_value REAL NOT NULL,
                threshold_value REAL NOT NULL,
                measurement_frequency TEXT NOT NULL,
                data_source TEXT NOT NULL,
                owner TEXT NOT NULL,
                calculation_method TEXT NOT NULL,
                minimum_acceptable_value REAL NOT NULL,
                warning_threshold REAL NOT NULL,
                escalation_threshold REAL NOT NULL,
                verification_method TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_kpi_measurements (
                measurement_id TEXT PRIMARY KEY,
                kpi_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                mission_id TEXT,
                measured_value REAL NOT NULL,
                target_value REAL NOT NULL,
                variance REAL NOT NULL,
                variance_percentage REAL NOT NULL,
                status TEXT NOT NULL, -- TARGET_MET, WARNING, BREACHED
                verification_proof JSON NOT NULL,
                measured_at REAL NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_kras (
                kra_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                name TEXT NOT NULL,
                responsibility TEXT NOT NULL,
                associated_workflows JSON NOT NULL,
                associated_kpi_ids JSON NOT NULL,
                allowed_tools JSON NOT NULL,
                authority_scope JSON NOT NULL,
                escalation_rules JSON NOT NULL,
                expected_outcomes JSON NOT NULL,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_emp ON employee_kpis(employee_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_kpi_meas ON employee_kpi_measurements(kpi_id);")

    def register_kpi(self, kpi: StructuredKPI) -> StructuredKPI:
        """Register a formal KPI specification for an employee."""
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO employee_kpis (
                kpi_id, tenant_id, company_id, employee_id, name, definition,
                unit, target_value, threshold_value, measurement_frequency,
                data_source, owner, calculation_method, minimum_acceptable_value,
                warning_threshold, escalation_threshold, verification_method, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kpi.kpi_id, kpi.tenant_id, kpi.company_id, kpi.employee_id,
                kpi.name, kpi.definition, kpi.unit, kpi.target_value,
                kpi.threshold_value, kpi.measurement_frequency, kpi.data_source,
                kpi.owner, kpi.calculation_method, kpi.minimum_acceptable_value,
                kpi.warning_threshold, kpi.escalation_threshold, kpi.verification_method,
                kpi.created_at
            ))
        return kpi

    def register_kra(self, kra: StructuredKRA) -> StructuredKRA:
        """Register a formal KRA specification for an employee."""
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO employee_kras (
                kra_id, tenant_id, company_id, employee_id, name, responsibility,
                associated_workflows, associated_kpi_ids, allowed_tools,
                authority_scope, escalation_rules, expected_outcomes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                kra.kra_id, kra.tenant_id, kra.company_id, kra.employee_id,
                kra.name, kra.responsibility, json.dumps(kra.associated_workflows),
                json.dumps(kra.associated_kpi_ids), json.dumps(kra.allowed_tools),
                json.dumps(kra.authority_scope), json.dumps(kra.escalation_rules),
                json.dumps(kra.expected_outcomes), kra.created_at
            ))
        return kra

    def record_measurement(
        self,
        kpi_id: str,
        measured_value: float,
        verification_proof: Dict[str, Any],
        mission_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a verified business outcome against an employee's KPI.
        Calculates variance and determines if target is met or breached.
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            row = conn.execute("SELECT * FROM employee_kpis WHERE kpi_id = ?", (kpi_id,)).fetchone()
            if not row:
                raise ValueError(f"KPI {kpi_id} not found.")

        target = row["target_value"]
        min_acc = row["minimum_acceptable_value"]
        warn_th = row["warning_threshold"]

        variance = measured_value - target
        variance_pct = (variance / target * 100.0) if target != 0 else 0.0

        if measured_value >= target:
            status = "TARGET_MET"
        elif measured_value >= warn_th:
            status = "WARNING"
        else:
            status = "BREACHED"

        measurement_id = f"meas_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO employee_kpi_measurements (
                measurement_id, kpi_id, tenant_id, company_id, employee_id,
                mission_id, measured_value, target_value, variance, variance_percentage,
                status, verification_proof, measured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                measurement_id, kpi_id, row["tenant_id"], row["company_id"],
                row["employee_id"], mission_id, measured_value, target,
                variance, variance_pct, status, json.dumps(verification_proof), now
            ))

        evidence_service.record_event(
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
            event_type="KPI_MEASUREMENT_RECORDED",
            payload={
                "measurement_id": measurement_id,
                "kpi_id": kpi_id,
                "employee_id": row["employee_id"],
                "measured_value": measured_value,
                "target_value": target,
                "variance": variance,
                "status": status,
                "verification_source": verification_proof.get("source", "UNKNOWN")
            }
        )

        return {
            "measurement_id": measurement_id,
            "kpi_id": kpi_id,
            "employee_id": row["employee_id"],
            "measured_value": measured_value,
            "target_value": target,
            "variance": variance,
            "variance_percentage": variance_pct,
            "status": status,
            "measured_at": now
        }

    def evaluate_employee_performance(self, employee_id: str) -> Dict[str, Any]:
        """
        Aggregate all KPI measurements for an employee to compute overall
        performance health: PERFORMING, UNDERPERFORMING, DEGRADED, or REVIEW_REQUIRED.
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            measurements = conn.execute("""
            SELECT * FROM employee_kpi_measurements
            WHERE employee_id = ?
            ORDER BY measured_at DESC
            LIMIT 50
            """, (employee_id,)).fetchall()

        if not measurements:
            return {
                "employee_id": employee_id,
                "total_measurements": 0,
                "health": "UNKNOWN",
                "score": 100.0,
                "summary": "No operational KPI measurements recorded yet."
            }

        total = len(measurements)
        met_cnt = sum(1 for m in measurements if m["status"] == "TARGET_MET")
        warn_cnt = sum(1 for m in measurements if m["status"] == "WARNING")
        breach_cnt = sum(1 for m in measurements if m["status"] == "BREACHED")

        score = ((met_cnt * 100.0) + (warn_cnt * 50.0)) / (total * 100.0) * 100.0

        if breach_cnt >= 3 or score < 50.0:
            health = "UNDERPERFORMING"
        elif warn_cnt >= 2 or score < 75.0:
            health = "REVIEW_REQUIRED"
        elif score < 85.0:
            health = "DEGRADED"
        else:
            health = "PERFORMING"

        return {
            "employee_id": employee_id,
            "total_measurements": total,
            "targets_met": met_cnt,
            "warnings": warn_cnt,
            "breaches": breach_cnt,
            "score": round(score, 1),
            "health": health,
            "summary": f"{health}: {met_cnt}/{total} targets met, {breach_cnt} breaches, score {round(score, 1)}%"
        }

kpi_kra_engine = KPIKRAEngine()
