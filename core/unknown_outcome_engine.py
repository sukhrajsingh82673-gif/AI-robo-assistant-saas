"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 16 — Unknown Outcome Engine & Deterministic Reconciliation
Explicit state machine and reconciliation workflows for ambiguous mutations.

Constitutional Invariants:
  UNKNOWN_OUTCOME != FAILURE
  UNKNOWN_OUTCOME != SUCCESS
  NEVER_AUTOMATICALLY_RETRY_UNKNOWN_MUTATION_WITHOUT_RECONCILIATION
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.unknown_outcome.engine")

class ReconciledStatus:
    PENDING_RECONCILIATION = "PENDING_RECONCILIATION"
    CONFIRMED_SUCCESS = "CONFIRMED_SUCCESS"
    CONFIRMED_FAILURE = "CONFIRMED_FAILURE"
    HUMAN_ESCALATION_REQUIRED = "HUMAN_ESCALATION_REQUIRED"
    COMPENSATED = "COMPENSATED"

@dataclass
class UnknownOutcomeRecord:
    record_id: str
    action_id: str
    tenant_id: str
    company_id: str
    employee_id: str
    target_system: str
    mutation_type: str
    parameters: Dict[str, Any]
    idempotency_key: str
    status: str
    reconciliation_attempts: int
    reconciliation_result: Optional[Dict[str, Any]]
    created_at: float
    updated_at: float

class UnknownOutcomeEngine:
    """
    State machine for ambiguous mutations (timeouts, network drops, unacknowledged writes).
    Guarantees that no financial or mutating action is blindly retried.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS unknown_outcomes (
                record_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                target_system TEXT NOT NULL,
                mutation_type TEXT NOT NULL,
                parameters JSON NOT NULL,
                idempotency_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING_RECONCILIATION',
                reconciliation_attempts INTEGER NOT NULL DEFAULT 0,
                reconciliation_result JSON,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_unk_tenant ON unknown_outcomes(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_unk_status ON unknown_outcomes(status);")

    def register_unknown_outcome(
        self,
        action_id: str,
        tenant_id: str,
        company_id: str,
        employee_id: str,
        target_system: str,
        mutation_type: str,
        parameters: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> UnknownOutcomeRecord:
        """Register an ambiguous transaction requiring deterministic verification."""
        record_id = f"unk_{uuid.uuid4().hex[:12]}"
        idemp = idempotency_key or f"idemp_{uuid.uuid4().hex[:16]}"
        now = time.time()

        rec = UnknownOutcomeRecord(
            record_id=record_id,
            action_id=action_id,
            tenant_id=tenant_id,
            company_id=company_id,
            employee_id=employee_id,
            target_system=target_system,
            mutation_type=mutation_type,
            parameters=parameters,
            idempotency_key=idemp,
            status=ReconciledStatus.PENDING_RECONCILIATION,
            reconciliation_attempts=0,
            reconciliation_result=None,
            created_at=now,
            updated_at=now
        )

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO unknown_outcomes (
                record_id, action_id, tenant_id, company_id, employee_id,
                target_system, mutation_type, parameters, idempotency_key,
                status, reconciliation_attempts, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                rec.record_id, rec.action_id, rec.tenant_id, rec.company_id,
                rec.employee_id, rec.target_system, rec.mutation_type,
                json.dumps(rec.parameters), rec.idempotency_key, rec.status, now, now
            ))

        evidence_service.record_event(
            tenant_id=tenant_id,
            company_id=company_id,
            event_type="UNKNOWN_OUTCOME_CAPTURED",
            payload={
                "record_id": record_id,
                "action_id": action_id,
                "target_system": target_system,
                "idempotency_key": idemp
            }
        )
        logger.warning(f"[UNKNOWN OUTCOME] Action {action_id} entered state UNKNOWN_OUTCOME. Automated retry prohibited.")
        return rec

    def reconcile(
        self,
        record_id: str,
        query_provider_fn: Optional[Any] = None
    ) -> str:
        """
        Execute deterministic reconciliation flow:
        UNKNOWN -> RECONCILE -> CONFIRMED_SUCCESS / CONFIRMED_FAILURE / HUMAN_ESCALATION
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM unknown_outcomes WHERE record_id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Unknown outcome record '{record_id}' not found.")

        attempts = row["reconciliation_attempts"] + 1
        now = time.time()
        final_status = ReconciledStatus.HUMAN_ESCALATION_REQUIRED
        result_payload = {}

        if query_provider_fn:
            try:
                # Poll provider with idempotency key
                verified, outcome = query_provider_fn(row["idempotency_key"])
                if verified:
                    final_status = ReconciledStatus.CONFIRMED_SUCCESS
                    result_payload = {"provider_confirmed": True, "details": outcome}
                else:
                    final_status = ReconciledStatus.CONFIRMED_FAILURE
                    result_payload = {"provider_confirmed": False, "details": outcome}
            except Exception as e:
                logger.error(f"Reconciliation query failed: {e}")
                final_status = ReconciledStatus.HUMAN_ESCALATION_REQUIRED
                result_payload = {"error": str(e)}
        else:
            # If no provider query available, escalate after 3 attempts
            if attempts >= 3:
                final_status = ReconciledStatus.HUMAN_ESCALATION_REQUIRED
                result_payload = {"reason": "Max automatic reconciliation attempts exceeded. Halting for human audit."}
            else:
                final_status = ReconciledStatus.PENDING_RECONCILIATION

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE unknown_outcomes
            SET status = ?, reconciliation_attempts = ?, reconciliation_result = ?, updated_at = ?
            WHERE record_id = ?
            """, (final_status, attempts, json.dumps(result_payload), now, record_id))

        evidence_service.record_event(
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
            event_type="RECONCILIATION_RESOLVED",
            payload={
                "record_id": record_id,
                "action_id": row["action_id"],
                "final_status": final_status,
                "attempts": attempts
            }
        )

        return final_status

# Global singleton
unknown_outcome_engine = UnknownOutcomeEngine()
