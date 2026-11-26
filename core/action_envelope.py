"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Canonical ActionEnvelope Protocol & Asynchronous Command Architecture
Defines the universal envelope consumed by all execution subsystems (MCP, A2A, Nango, Browser, OpenHands, HAL).
"""

import os
import time
import json
import uuid
import hashlib
import threading
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger("zonata.action_envelope")

class RiskClass:
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    DATA_ENTRY = "DATA_ENTRY"
    SAFE_RETRY = "SAFE_RETRY"
    MUTATING = "MUTATING"
    HIGH_RISK = "HIGH_RISK"
    FINANCIAL = "FINANCIAL"
    DESTRUCTIVE = "DESTRUCTIVE"
    IRREVERSIBLE = "IRREVERSIBLE"

@dataclass
class ActionEnvelope:
    """
    Constitutional execution envelope. No subsystem may invent its own authorization format.
    Every real-world action must be packaged in this immutable, auditable structure.
    """
    action_id: str
    tenant_id: str
    company_id: str
    mission_id: Optional[str]
    workflow_id: Optional[str]
    agent_id: str
    parent_agent_id: Optional[str]
    capability_id: str
    target: str
    intent: str
    parameters_hash: str
    risk_class: str
    authorization_contract_id: str
    approval_id: Optional[str]
    credential_handle: Optional[str]
    idempotency_key: str
    deadline: float
    parent_action_id: Optional[str]
    causality_id: str
    created_at: float
    expires_at: float
    parameters: Optional[Dict[str, Any]] = None
    action_class: str = "READ_INTERNAL"
    principal_type: str = "AGENT"
    principal_id: Optional[str] = None
    principal_grade: Optional[str] = None
    spend_amount_minor_units: int = 0
    target_principal_type: Optional[str] = None
    target_principal_id: Optional[str] = None
    is_autonomous: bool = False

    @classmethod
    def create(
        cls,
        tenant_id: str,
        company_id: str,
        agent_id: str,
        capability_id: str,
        target: str,
        intent: str,
        parameters: Dict[str, Any],
        risk_class: str = RiskClass.LOW_RISK,
        mission_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        authorization_contract_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        credential_handle: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        ttl_seconds: float = 300.0,
        parent_action_id: Optional[str] = None,
        causality_id: Optional[str] = None,
        action_class: Optional[str] = None,
        principal_type: str = "AGENT",
        principal_id: Optional[str] = None,
        principal_grade: Optional[str] = None,
        spend_amount_minor_units: int = 0,
        target_principal_type: Optional[str] = None,
        target_principal_id: Optional[str] = None,
        is_autonomous: bool = False,
    ) -> 'ActionEnvelope':
        now = time.time()
        canonical_params = json.dumps(parameters, sort_keys=True)
        param_hash = hashlib.sha256(canonical_params.encode("utf-8")).hexdigest()
        action_id = f"act_{uuid.uuid4().hex[:16]}"
        contract_id = authorization_contract_id or f"auth_contract_{uuid.uuid4().hex[:12]}"
        idemp = idempotency_key or f"idemp_{param_hash[:16]}"
        caus = causality_id or f"caus_{uuid.uuid4().hex[:16]}"

        # Infer action class if not explicitly provided
        resolved_action_class = action_class
        if not resolved_action_class:
            cap_lower = capability_id.lower()
            if any(w in cap_lower for w in ["spend", "payment", "payout", "charge", "refund"]):
                resolved_action_class = "COMMIT_SPEND"
            elif any(w in cap_lower for w in ["ledger", "journal"]):
                resolved_action_class = "POST_LEDGER"
            elif any(w in cap_lower for w in ["document.create", "document.upload"]):
                resolved_action_class = "CREATE_DOCUMENT"
            elif any(w in cap_lower for w in ["email.send", "message.send", "slack.post"]):
                resolved_action_class = "SEND_EXTERNAL_MESSAGE"
            elif any(w in cap_lower for w in ["hire", "provision"]):
                resolved_action_class = "PROVISION_AGENT_OR_HIRE"
            elif any(w in cap_lower for w in ["permission", "grant"]):
                resolved_action_class = "CHANGE_PERMISSION"
            elif any(w in cap_lower for w in ["delete", "purge"]):
                resolved_action_class = "DELETE_DATA"
            elif any(w in cap_lower for w in ["legal", "contract.sign"]):
                resolved_action_class = "LEGAL_COMMITMENT"
            elif any(w in cap_lower for w in ["write", "update"]):
                resolved_action_class = "WRITE_INTERNAL"
            else:
                resolved_action_class = "READ_INTERNAL"

        return cls(
            action_id=action_id,
            tenant_id=tenant_id,
            company_id=company_id,
            mission_id=mission_id,
            workflow_id=workflow_id,
            agent_id=agent_id,
            parent_agent_id=parent_agent_id,
            capability_id=capability_id,
            target=target,
            intent=intent,
            parameters_hash=param_hash,
            risk_class=risk_class,
            authorization_contract_id=contract_id,
            approval_id=approval_id,
            credential_handle=credential_handle,
            idempotency_key=idemp,
            deadline=now + ttl_seconds,
            parent_action_id=parent_action_id,
            causality_id=caus,
            created_at=now,
            expires_at=now + ttl_seconds,
            parameters=parameters,
            action_class=resolved_action_class,
            principal_type=principal_type,
            principal_id=principal_id or agent_id,
            principal_grade=principal_grade,
            spend_amount_minor_units=spend_amount_minor_units,
            target_principal_type=target_principal_type,
            target_principal_id=target_principal_id,
            is_autonomous=is_autonomous,
        )

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionEnvelope':
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)


class AsynchronousCommandBus:
    """
    Production-grade asynchronous job plane.
    Persists commands, enforces tenant admission control, dispatches to worker queues,
    and guarantees that HTTP handlers never synchronously execute long-running tasks.
    """
    def __init__(self):
        self._claim_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._init_db()

    def stop(self):
        """Signals background worker to stop gracefully."""
        self._stop_event.set()

    def reset_worker(self):
        """Resets stop event to allow starting/restarting worker."""
        self._stop_event.clear()

    def recover_interrupted_jobs(self, timeout_seconds: float = 300.0) -> int:
        """
        Detects actions left in ASSIGNED status from an interrupted worker,
        sleep cycle, crash, or restart.
        Safely transitions them back to QUEUED or marks FAILED if retry limit (3) exceeded.
        """
        from core.database_engine import engine, WorkloadType
        now = time.time()
        cutoff = now - timeout_seconds
        recovered_count = 0
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            cursor = conn.execute("""
                SELECT action_id, envelope_payload, updated_at
                FROM async_command_queue
                WHERE status = 'ASSIGNED' AND updated_at < ?
            """, (cutoff,))
            rows = cursor.fetchall()
            for row in rows:
                action_id = row[0]
                try:
                    payload = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
                except Exception:
                    payload = {}
                retry_count = payload.get("_retry_count", 0) + 1
                payload["_retry_count"] = retry_count

                if retry_count > 3:
                    conn.execute("""
                        UPDATE async_command_queue
                        SET status = 'FAILED', error_message = 'Action exceeded maximum retry attempts (3) after worker interruption or sleep cycle', updated_at = ?, completed_at = ?
                        WHERE action_id = ?
                    """, (now, now, action_id))
                    logger.warning(f"Action '{action_id}' marked FAILED: exceeded retry limit after worker interruption.")
                else:
                    conn.execute("""
                        UPDATE async_command_queue
                        SET status = 'QUEUED', worker_id = NULL, envelope_payload = ?, updated_at = ?
                        WHERE action_id = ?
                    """, (json.dumps(payload), now, action_id))
                    logger.info(f"Action '{action_id}' recovered back to QUEUED (Attempt {retry_count}/3).")
                    recovered_count += 1
        return recovered_count

    def _init_db(self):
        from core.database_engine import engine, WorkloadType
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        protected_db = os.path.abspath(os.path.join(base_dir, "storage", "roboassistant.db"))
        if engine.dialect == "sqlite" and os.path.abspath(engine.db_path) == protected_db and os.path.exists(protected_db):
            # Protected baseline database — never mutate or execute schema scripts automatically
            return
        if engine.dialect == "postgresql" and not getattr(engine, "_deferred_import_mode", False):
            with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
                try:
                    reg = conn.execute("SELECT to_regclass('public.async_command_queue')").fetchone()
                    if reg and reg[0]:
                        return
                except Exception:
                    pass
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS async_command_queue (
                action_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                mission_id TEXT,
                workflow_id TEXT,
                agent_id TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED, ASSIGNED, EXECUTING, COMPLETED, FAILED, TIMED_OUT, UNKNOWN_OUTCOME
                envelope_payload JSON NOT NULL,
                worker_id TEXT,
                result_payload JSON,
                error_message TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cmd_queue_tenant ON async_command_queue(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cmd_queue_status ON async_command_queue(status);")

    def enqueue(self, envelope: ActionEnvelope) -> str:
        """Enqueue an ActionEnvelope for background asynchronous execution."""
        from core.database_engine import engine, WorkloadType
        from core.distributed_coordination import coordination

        # Verify not killed
        killed, reason = coordination.is_killed("AGENT", envelope.agent_id)
        if killed:
            raise PermissionError(f"Action blocked by distributed killswitch: {reason}")

        payload_json = json.dumps(envelope.to_dict())
        now = time.time()

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO async_command_queue (
                action_id, tenant_id, company_id, mission_id, workflow_id,
                agent_id, capability_id, risk_class, status, envelope_payload,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', ?, ?, ?)
            """, (
                envelope.action_id, envelope.tenant_id, envelope.company_id,
                envelope.mission_id, envelope.workflow_id, envelope.agent_id,
                envelope.capability_id, envelope.risk_class, payload_json,
                now, now
            ))

        coordination.increment_backpressure(f"queue_depth:{envelope.tenant_id}")
        return envelope.action_id

    def fetch_next(self, worker_id: str, tenant_id: Optional[str] = None) -> Optional[ActionEnvelope]:
        """Atomically claim the next queued action for a worker."""
        from core.database_engine import engine, WorkloadType
        from core.distributed_coordination import coordination
        now = time.time()

        with self._claim_lock:
            with engine.transaction(workload=WorkloadType.WRITE) as conn:
                query = "SELECT action_id, envelope_payload FROM async_command_queue WHERE status = 'QUEUED'"
                params = []
                if tenant_id:
                    query += " AND tenant_id = ?"
                    params.append(tenant_id)
                query += " ORDER BY created_at ASC LIMIT 1"

                cursor = conn.execute(query, params)
                row = cursor.fetchone()
                if not row:
                    return None

                action_id = row[0]
                envelope_data = json.loads(row[1])

                # Transition state to ASSIGNED with atomic compare-and-swap
                cur = conn.execute("""
                UPDATE async_command_queue
                SET status = 'ASSIGNED', worker_id = ?, updated_at = ?
                WHERE action_id = ? AND status = 'QUEUED'
                """, (worker_id, now, action_id))

                if hasattr(cur, 'rowcount') and cur.rowcount == 0:
                    # Concurrently claimed by another worker
                    return None

                if tenant_id:
                    coordination.decrement_backpressure(f"queue_depth:{tenant_id}")

                return ActionEnvelope.from_dict(envelope_data)

    def mark_completed(self, action_id: str, result: Dict[str, Any]):
        from core.database_engine import engine, WorkloadType
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE async_command_queue
            SET status = 'COMPLETED', result_payload = ?, updated_at = ?, completed_at = ?
            WHERE action_id = ?
            """, (json.dumps(result), now, now, action_id))

    def mark_failed(self, action_id: str, error_message: str, outcome_status: str = "FAILED"):
        from core.database_engine import engine, WorkloadType
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            UPDATE async_command_queue
            SET status = ?, error_message = ?, updated_at = ?, completed_at = ?
            WHERE action_id = ?
            """, (outcome_status, error_message, now, now, action_id))

    def get_status(self, action_id: str) -> Optional[Dict[str, Any]]:
        from core.database_engine import engine, WorkloadType
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT status, result_payload, error_message, created_at, completed_at FROM async_command_queue WHERE action_id = ?", (action_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "action_id": action_id,
                "status": row[0],
                "result": json.loads(row[1]) if row[1] else None,
                "error": row[2],
                "created_at": row[3],
                "completed_at": row[4]
            }

    def run_worker(self, worker_id: Optional[str] = None, poll_interval: float = 0.5, max_iterations: Optional[int] = None):
        """Run continuous asynchronous worker processing loop with crash recovery and graceful shutdown."""
        from core.action_gateway import ZonataActionGateway
        worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        iterations = 0
        logger.info(f"Asynchronous worker '{worker_id}' started.")

        if self._stop_event.is_set():
            logger.info(f"Worker '{worker_id}' stop event already set; aborting loop.")
            return

        # On worker startup: immediately recover any orphaned jobs left in flight
        try:
            recovered = self.recover_interrupted_jobs(timeout_seconds=0.0)
            if recovered > 0:
                logger.info(f"Worker startup recovered {recovered} interrupted actions.")
        except Exception as rec_err:
            logger.warning(f"Could not perform startup job recovery: {rec_err}")

        last_recovery_check = time.time()
        while not self._stop_event.is_set():
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1

            # Periodic sweep for orphaned jobs every 60 seconds
            now = time.time()
            if now - last_recovery_check > 60.0:
                last_recovery_check = now
                try:
                    self.recover_interrupted_jobs(timeout_seconds=300.0)
                except Exception:
                    pass

            try:
                envelope = self.fetch_next(worker_id=worker_id)
                if envelope:
                    try:
                        gateway = ZonataActionGateway()
                        result = gateway.execute_action(envelope)
                        self.mark_completed(envelope.action_id, result)
                    except Exception as exec_err:
                        self.mark_failed(envelope.action_id, str(exec_err))
                else:
                    self._stop_event.wait(timeout=poll_interval)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                self._stop_event.wait(timeout=poll_interval)
        logger.info(f"Asynchronous worker '{worker_id}' gracefully stopped.")

# Global asynchronous command bus instance
command_bus = AsynchronousCommandBus()

if __name__ == "__main__":
    import sys
    worker_id = sys.argv[2] if len(sys.argv) > 2 else f"worker_{uuid.uuid4().hex[:8]}"
    command_bus.run_worker(worker_id=worker_id)
