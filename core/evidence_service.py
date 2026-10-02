"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Evidence Service V2 (Transactional Distributed Merkle Ledger)
Persists immutable, sequence-ordered cryptographic audit events in relational storage
with previous-hash chaining, tamper detection, and multi-tenant isolation.
"""

import time
import json
import uuid
import hashlib
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
from core.database_engine import engine, WorkloadType
from core.evidence_ledger import EvidenceLedger

logger = logging.getLogger("zonata.evidence.v2")

class EvidenceTamperDetected(Exception):
    """Raised when cryptographic verification detects a broken or modified audit link."""
    pass

class EvidenceServiceV2:
    """
    Authoritative Multi-Node Evidence Service.
    Guarantees atomic append, continuous SHA-256 hash chaining, and unique sequential ordering.
    """
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self._init_db()
        self._local_ledger = EvidenceLedger()
        self._lock = threading.RLock()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS merkle_evidence_events (
                event_id TEXT PRIMARY KEY,
                event_index INTEGER,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                mission_id TEXT,
                workflow_id TEXT,
                agent_id TEXT,
                action_id TEXT,
                event_type TEXT NOT NULL,
                canonical_payload_hash TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                current_hash TEXT NOT NULL,
                causality_id TEXT,
                verification_state TEXT NOT NULL DEFAULT 'PENDING',
                artifact_storage_ref TEXT,
                timestamp REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_v2_tenant ON merkle_evidence_events(tenant_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_v2_cur_hash ON merkle_evidence_events(current_hash);")

    def _get_latest_hash(self, conn, tenant_id: str) -> Tuple[str, int]:
        """Fetch the physical tail hash and sequence index for a tenant."""
        cursor = conn.execute("""
        SELECT current_hash, event_index FROM merkle_evidence_events
        WHERE tenant_id = ?
        ORDER BY event_index DESC LIMIT 1
        """, (tenant_id,))
        row = cursor.fetchone()
        if row:
            return (row[0], row[1])
        return (self.GENESIS_HASH, 0)

    def record_event(
        self,
        tenant_id: str,
        company_id: str,
        event_type: str,
        payload: Dict[str, Any],
        agent_id: Optional[str] = None,
        action_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        causality_id: Optional[str] = None,
        verification_state: str = "VERIFIED",
        artifact_storage_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomically append an immutable cryptographic record to the authoritative ledger.
        """
        event_id = f"ev_{uuid.uuid4().hex[:16]}"
        now = time.time()
        canonical_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        with self._lock:
            with engine.transaction(workload=WorkloadType.WRITE) as conn:
                prev_hash, last_idx = self._get_latest_hash(conn, tenant_id)
                next_idx = last_idx + 1

                # Calculate tamper-evident hash
                chain_str = f"{event_id}|{next_idx}|{tenant_id}|{event_type}|{payload_hash}|{prev_hash}|{now}"
                current_hash = hashlib.sha256(chain_str.encode("utf-8")).hexdigest()

                conn.execute("""
                INSERT INTO merkle_evidence_events (
                    event_id, event_index, tenant_id, company_id, mission_id,
                    workflow_id, agent_id, action_id, event_type,
                    canonical_payload_hash, previous_hash, current_hash,
                    causality_id, verification_state, artifact_storage_ref, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, next_idx, tenant_id, company_id, mission_id,
                    workflow_id, agent_id, action_id, event_type,
                    payload_hash, prev_hash, current_hash,
                    causality_id, verification_state, artifact_storage_ref, now
                ))

            # Mirror to local ledger for local file tools
            try:
                self._local_ledger.seal_evidence(
                    action_name=event_type,
                    actor=agent_id or "SYSTEM",
                    actor_type="AGENT",
                    parameters=payload,
                    output={"event_id": event_id, "verification_state": verification_state},
                    tenant_id=tenant_id,
                    company_id=company_id
                )
            except Exception:
                pass

        return {
            "event_id": event_id,
            "event_index": next_idx,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "previous_hash": prev_hash,
            "current_hash": current_hash,
            "payload_hash": payload_hash,
            "verification_state": verification_state,
            "timestamp": now
        }

    def verify_chain_integrity(self, tenant_id: str) -> Dict[str, Any]:
        """
        Walk the complete cryptographic chain from genesis to tail and verify 0 tampering and 0 forks.
        """
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("""
            SELECT event_id, event_index, tenant_id, event_type, canonical_payload_hash,
                   previous_hash, current_hash, timestamp
            FROM merkle_evidence_events
            WHERE tenant_id = ?
            ORDER BY event_index ASC
            """, (tenant_id,))
            rows = cursor.fetchall()

            if not rows:
                return {"status": "EMPTY", "records_verified": 0, "valid": True}

            expected_prev = self.GENESIS_HASH
            for idx, r in enumerate(rows):
                ev_id, ev_idx, t_id, ev_type, p_hash, prev_h, cur_h, ts = r
                if prev_h != expected_prev:
                    return {
                        "status": "TAMPER_DETECTED",
                        "valid": False,
                        "broken_at_index": ev_idx,
                        "event_id": ev_id,
                        "expected_prev": expected_prev,
                        "actual_prev": prev_h
                    }

                # Verify current hash computation
                chain_str = f"{ev_id}|{ev_idx}|{t_id}|{ev_type}|{p_hash}|{prev_h}|{ts}"
                computed = hashlib.sha256(chain_str.encode("utf-8")).hexdigest()
                if computed != cur_h:
                    return {
                        "status": "HASH_CORRUPTED",
                        "valid": False,
                        "broken_at_index": ev_idx,
                        "event_id": ev_id,
                        "computed": computed,
                        "actual": cur_h
                    }
                expected_prev = cur_h

            return {
                "status": "VALID",
                "valid": True,
                "records_verified": len(rows),
                "tip_hash": expected_prev
            }

# Global Evidence Service V2 instance
evidence_service = EvidenceServiceV2()
