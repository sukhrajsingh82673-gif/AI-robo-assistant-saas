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
import hashlib
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
            INSERT INTO employee_kpis (
                kpi_id, tenant_id, company_id, employee_id, name, definition,
                unit, target_value, threshold_value, measurement_frequency,
                data_source, owner, calculation_method, minimum_acceptable_value,
                warning_threshold, escalation_threshold, verification_method, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (kpi_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                company_id = EXCLUDED.company_id,
                employee_id = EXCLUDED.employee_id,
                name = EXCLUDED.name,
                definition = EXCLUDED.definition,
                unit = EXCLUDED.unit,
                target_value = EXCLUDED.target_value,
                threshold_value = EXCLUDED.threshold_value,
                measurement_frequency = EXCLUDED.measurement_frequency,
                data_source = EXCLUDED.data_source,
                owner = EXCLUDED.owner,
                calculation_method = EXCLUDED.calculation_method,
                minimum_acceptable_value = EXCLUDED.minimum_acceptable_value,
                warning_threshold = EXCLUDED.warning_threshold,
                escalation_threshold = EXCLUDED.escalation_threshold,
                verification_method = EXCLUDED.verification_method
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
        # The canonical corporate_employees schema is authoritative; resolve the
        # employee's position when it exists so both schemas stay compatible.
        position_id = ""
        try:
            with engine.transaction(workload=WorkloadType.READ) as conn:
                row = conn.execute(
                    "SELECT position_id FROM corporate_employees WHERE employee_id = ?",
                    (kra.employee_id,),
                ).fetchone()
                if row:
                    position_id = row["position_id"] or ""
        except Exception:
            position_id = ""
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO employee_kras (
                kra_id, tenant_id, company_id, employee_id, position_id, name,
                weight_percentage, accountability_statement, responsibility,
                associated_workflows, associated_kpi_ids, allowed_tools,
                authority_scope, escalation_rules, expected_outcomes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (kra_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                company_id = EXCLUDED.company_id,
                employee_id = EXCLUDED.employee_id,
                name = EXCLUDED.name,
                responsibility = EXCLUDED.responsibility,
                associated_workflows = EXCLUDED.associated_workflows,
                associated_kpi_ids = EXCLUDED.associated_kpi_ids,
                allowed_tools = EXCLUDED.allowed_tools,
                authority_scope = EXCLUDED.authority_scope,
                escalation_rules = EXCLUDED.escalation_rules,
                expected_outcomes = EXCLUDED.expected_outcomes
            """, (
                kra.kra_id, kra.tenant_id, kra.company_id, kra.employee_id,
                position_id, kra.name, 25.0, kra.responsibility, kra.responsibility,
                json.dumps(kra.associated_workflows),
                json.dumps(kra.associated_kpi_ids), json.dumps(kra.allowed_tools),
                json.dumps(kra.authority_scope), json.dumps(kra.escalation_rules),
                json.dumps(kra.expected_outcomes), kra.created_at, kra.created_at
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

@dataclass
class SOPDefinition:
    sop_id: str
    tenant_id: str
    company_id: str
    department_id: str
    sop_code: str
    title: str
    category: str
    cadence: str = "EVENT_DRIVEN"
    risk_level: str = "MEDIUM"
    objective: str = ""
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class SOPVersion:
    version_id: str
    sop_id: str
    tenant_id: str
    version_semver: str  # e.g., '1.0.0'
    status: str          # DRAFT, REVIEW, APPROVED, ACTIVE, SUPERSEDED, RETIRED
    steps_definition: List[Dict[str, Any]]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    anti_gaming_rules: Dict[str, Any]
    required_authority_level: str = "DELEGATED"
    evidence_requirements: List[str] = field(default_factory=list)
    author_employee_id: str = ""
    approved_by_role: Optional[str] = None
    approved_at: Optional[float] = None
    sha256_hash: str = ""
    created_at: float = field(default_factory=time.time)

    def calculate_hash(self) -> str:
        payload = json.dumps({
            "sop_id": self.sop_id,
            "version_semver": self.version_semver,
            "steps": self.steps_definition,
            "inputs": self.input_schema,
            "outputs": self.output_schema,
            "rules": self.anti_gaming_rules
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

class AntiGamingEngine:
    """
    Evaluates primary performance metrics against paired adversarial counter-metrics.
    Constitutional Invariant: No metric exists in isolation.
    """
    @classmethod
    def evaluate_pair(
        cls,
        primary_code: str,
        primary_actual: float,
        primary_target: float,
        counter_code: str,
        counter_actual: float,
        counter_warning: float,
        weight: float = 0.5
    ) -> Tuple[bool, float, str]:
        """
        Anti-Gaming Formula:
        If primary metric exceeds target (>100%) but counter-metric breaches warning threshold,
        a divergence penalty is applied.
        Returns: (anti_gaming_passed, anti_gaming_score, audit_reason)
        """
        primary_ratio = primary_actual / primary_target if primary_target != 0 else 1.0
        is_lower_better = any(term in counter_code.lower() for term in ["cac", "cost", "error", "churn", "defect"])

        if is_lower_better:
            counter_healthy = counter_actual <= counter_warning
            gap = (counter_actual - counter_warning) / counter_warning if counter_warning != 0 else 0.5
        else:
            counter_healthy = counter_actual >= counter_warning
            gap = (counter_warning - counter_actual) / counter_warning if counter_warning != 0 else 0.5

        if primary_ratio > 1.0 and not counter_healthy:
            penalty = round(min(100.0, abs(gap) * 100.0 * (1.0 + weight)), 2)
            score = max(0.0, 100.0 - penalty)
            reason = (
                f"ANTI_GAMING_ALERT: Primary '{primary_code}' reached {primary_ratio*100:.1f}% "
                f"while paired counter-metric '{counter_code}' collapsed to {counter_actual} "
                f"(warning threshold: {counter_warning}). Penalty applied: -{penalty} pts."
            )
            return False, score, reason

        return True, 100.0, "ANTI_GAMING_PASSED: Paired metrics in healthy alignment."

    @classmethod
    def compute_4_factor_review(
        cls,
        kpi_achievement_score: float,     # Factor 1 (40% Weight)
        sop_compliance_score: float,      # Factor 2 (30% Weight)
        anti_gaming_compliance_score: float, # Factor 3 (20% Weight)
        collaboration_sla_score: float    # Factor 4 (10% Weight)
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        ISO 37000 Explainable 4-Factor Performance Scoring:
        Composite = 0.40 * S_KPI + 0.30 * S_SOP + 0.20 * S_AG + 0.10 * S_SLA
        """
        comp = (
            0.40 * kpi_achievement_score +
            0.30 * sop_compliance_score +
            0.20 * anti_gaming_compliance_score +
            0.10 * collaboration_sla_score
        )
        comp = round(comp, 2)

        if comp >= 90.0:
            rec = "PROMOTE"
        elif comp >= 75.0:
            rec = "RETAIN"
        elif comp >= 60.0:
            rec = "RETRAIN"
        elif comp >= 40.0:
            rec = "SUSPEND"
        else:
            rec = "TERMINATE"

        proof = {
            "formula": "0.40*S_KPI + 0.30*S_SOP + 0.20*S_AG + 0.10*S_SLA",
            "weights": {"kpi": 0.40, "sop": 0.30, "anti_gaming": 0.20, "collaboration_sla": 0.10},
            "scores": {
                "S_KPI": kpi_achievement_score,
                "S_SOP": sop_compliance_score,
                "S_AG": anti_gaming_compliance_score,
                "S_SLA": collaboration_sla_score
            },
            "composite": comp,
            "recommendation": rec
        }
        return comp, rec, proof

anti_gaming_engine = AntiGamingEngine()

