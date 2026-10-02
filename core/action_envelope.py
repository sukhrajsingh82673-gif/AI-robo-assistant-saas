"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Canonical ActionEnvelope Protocol & Asynchronous Command Architecture
Defines the universal envelope consumed by all execution subsystems (MCP, A2A, Nango, Browser, OpenHands, HAL).
"""

import time
import json
import uuid
import hashlib
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

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
        causality_id: Optional[str] = None
    ) -> 'ActionEnvelope':
        now = time.time()
        canonical_params = json.dumps(parameters, sort_keys=True)
        param_hash = hashlib.sha256(canonical_params.encode("utf-8")).hexdigest()
        action_id = f"act_{uuid.uuid4().hex[:16]}"
        contract_id = authorization_contract_id or f"auth_contract_{uuid.uuid4().hex[:12]}"
        idemp = idempotency_key or f"idemp_{param_hash[:16]}"
        caus = causality_id or f"caus_{uuid.uuid4().hex[:16]}"

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
            parameters=parameters
        )

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionEnvelope':
        return cls(**data)


class AsynchronousCommandBus:
    """
    Production-grade asynchronous job plane.
    Persists commands, enforces tenant admission control, dispatches to worker queues,
    and guarantees that HTTP handlers never synchronously execute long-running tasks.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        from core.database_engine import engine, WorkloadType
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

            # Transition state to ASSIGNED
            conn.execute("""
            UPDATE async_command_queue
            SET status = 'ASSIGNED', worker_id = ?, updated_at = ?
            WHERE action_id = ?
            """, (worker_id, now, action_id))

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

# Global asynchronous command bus instance
command_bus = AsynchronousCommandBus()
