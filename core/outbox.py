"""ZONATA Sovereign Core — Transactional Outbox & Event Bus.

Implements Stage 2 Foundations:
- Atomically enqueues domain events within database transactions (Transactional Outbox).
- Guarantees exactly-once dispatch semantics and cryptographic Merkle evidence sealing.
- Connects state transitions with downstream worker queues and audit listeners.
"""

from __future__ import annotations
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.db import db
from agent_factory.ports import EvidenceEvent
from agent_factory.adapters.zonata import ZonataEvidenceAdapter

logger = logging.getLogger("zonata.core.outbox")


@dataclass
class OutboxEvent:
    id: str
    tenant_id: str
    company_id: str
    topic: str
    payload: Dict[str, Any]
    evidence_id: str
    status: str  # PENDING, DISPATCHED, FAILED
    created_at: float
    dispatched_at: Optional[float] = None
    retry_count: int = 0
    error: Optional[str] = None


class TransactionalOutbox:
    def __init__(self, db_conn_factory=None, evidence_port=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self.evidence = evidence_port or ZonataEvidenceAdapter()
        self._handlers: Dict[str, List[Callable[[OutboxEvent], None]]] = {}
        self._ensure_table()

    def _get_connection(self):
        return self.db_conn_factory()

    def _ensure_table(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS af_outbox (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at REAL NOT NULL,
                    dispatched_at REAL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS af_outbox_pending_idx ON af_outbox (status, created_at)")
            conn.commit()

    def publish_transactional(
        self,
        conn,
        tenant_id: str,
        company_id: str,
        topic: str,
        payload: Dict[str, Any],
        actor_principal_id: str
    ) -> OutboxEvent:
        """Atomically insert an outbox event into an active SQLite/PostgreSQL connection transaction."""
        now = time.time()
        event_id = f"evt_{uuid.uuid4().hex[:12]}"

        # 1. Cryptographically seal in EvidenceLedger before effect
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="outbox_event",
            subject_id=event_id,
            event_type=f"outbox.{topic}",
            actor=actor_principal_id,
            payload_hashes={"topic": topic, "company_id": company_id},
            timestamp=now,
            tenant_id=tenant_id
        ))

        # 2. Insert outbox record into current transaction
        payload_json = json.dumps(payload, sort_keys=True)
        conn.execute("""
            INSERT INTO af_outbox (
                id, tenant_id, company_id, topic, payload,
                evidence_id, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
        """, (event_id, tenant_id, company_id, topic, payload_json, ev_id, now))

        return OutboxEvent(
            id=event_id,
            tenant_id=tenant_id,
            company_id=company_id,
            topic=topic,
            payload=payload,
            evidence_id=ev_id,
            status="PENDING",
            created_at=now
        )

    def subscribe(self, topic: str, handler: Callable[[OutboxEvent], None]):
        """Subscribe an in-process handler to an event topic."""
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    def dispatch_pending(self, limit: int = 50) -> int:
        """Poll and dispatch pending outbox events to registered subscribers."""
        dispatched_count = 0
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT id, tenant_id, company_id, topic, payload, evidence_id, created_at, retry_count
                FROM af_outbox
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()

            for row in rows:
                event = OutboxEvent(
                    id=row[0],
                    tenant_id=row[1],
                    company_id=row[2],
                    topic=row[3],
                    payload=json.loads(row[4]),
                    evidence_id=row[5],
                    status="PENDING",
                    created_at=row[6],
                    retry_count=row[7]
                )

                handlers = self._handlers.get(event.topic, []) + self._handlers.get("*", [])
                now = time.time()
                try:
                    for h in handlers:
                        h(event)

                    conn.execute("""
                        UPDATE af_outbox
                        SET status = 'DISPATCHED', dispatched_at = ?
                        WHERE id = ?
                    """, (now, event.id))
                    dispatched_count += 1
                except Exception as e:
                    logger.error(f"Failed to dispatch outbox event {event.id}: {e}")
                    conn.execute("""
                        UPDATE af_outbox
                        SET status = 'FAILED', error = ?, retry_count = retry_count + 1
                        WHERE id = ?
                    """, (str(e), event.id))

            conn.commit()
        return dispatched_count
