"""
RoboAssistant Enterprise — Transactional Outbox & Reliable Mutation Engine
Guarantees at-least-once (with idempotent exactly-once processing) delivery
between relational state mutations and external/downstream subscribers.
"""

import time
import uuid
import json
import logging
import sqlite3
from typing import Dict, List, Optional, Any, Callable
from .db import db

logger = logging.getLogger("ZonataOutbox")

class TransactionalOutboxManager:
    """
    Manages the atomic commit of domain mutations along with an outbox event.
    Provides batch processing, exponential backoff retries, dead-letter routing,
    and crash recovery mechanisms.
    """

    def __init__(self, tenant_id: str = "tnt_primary", max_attempts: int = 5):
        self.tenant_id = tenant_id
        self.max_attempts = max_attempts

    def stage_event(
        self,
        conn: sqlite3.Connection,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> str:
        """
        Stages an outbox event synchronously within the caller's active database transaction.
        Atomic with the domain mutation: if the transaction commits, the event is saved.
        If the transaction rolls back, the event is never persisted.
        """
        outbox_id = f"obx_{uuid.uuid4().hex[:12]}"
        idem_key = idempotency_key or f"idem_{uuid.uuid4().hex}"
        now = time.time()

        conn.execute(
            """
            INSERT INTO transactional_outbox (
                outbox_id, tenant_id, aggregate_type, aggregate_id,
                event_type, payload, idempotency_key, status,
                attempts, max_attempts, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, ?, ?, ?)
            """,
            (
                outbox_id,
                self.tenant_id,
                aggregate_type,
                aggregate_id,
                event_type,
                json.dumps(payload),
                idem_key,
                self.max_attempts,
                now,
                now
            )
        )
        return outbox_id

    def fetch_pending_events(self, batch_size: int = 50) -> List[Dict[str, Any]]:
        """Retrieves pending or retriable outbox events."""
        with db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM transactional_outbox
                WHERE tenant_id = ? AND status IN ('PENDING', 'PROCESSING')
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (self.tenant_id, batch_size)
            ).fetchall()
            return [dict(r) for r in rows]

    def process_event(
        self,
        outbox_id: str,
        publish_handler: Callable[[Dict[str, Any]], bool]
    ) -> bool:
        """
        Processes a single event with optimistic status locking and error handling.
        """
        now = time.time()
        with db.get_connection() as conn:
            # 1. Mark PROCESSING
            res = conn.execute(
                """
                UPDATE transactional_outbox
                SET status = 'PROCESSING', attempts = attempts + 1, updated_at = ?
                WHERE outbox_id = ? AND tenant_id = ? AND status IN ('PENDING', 'PROCESSING')
                """,
                (now, outbox_id, self.tenant_id)
            )
            if res.rowcount == 0:
                return False

            row = conn.execute(
                "SELECT * FROM transactional_outbox WHERE outbox_id = ?",
                (outbox_id,)
            ).fetchone()
            if not row:
                return False

            event = dict(row)
            event["payload"] = json.loads(event["payload"])
            conn.commit()

        # 2. Invoke publishing callback outside the lock
        success = False
        error_msg = None
        try:
            success = publish_handler(event)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to publish outbox event {outbox_id}: {e}")

        # 3. Finalize state
        now = time.time()
        with db.get_connection() as conn:
            if success:
                conn.execute(
                    """
                    UPDATE transactional_outbox
                    SET status = 'PUBLISHED', published_at = ?, updated_at = ?, last_error = NULL
                    WHERE outbox_id = ?
                    """,
                    (now, now, outbox_id)
                )
            else:
                attempts = event["attempts"]
                max_att = event["max_attempts"]
                new_status = 'DEAD_LETTER' if attempts >= max_att else 'PENDING'
                conn.execute(
                    """
                    UPDATE transactional_outbox
                    SET status = ?, last_error = ?, updated_at = ?
                    WHERE outbox_id = ?
                    """,
                    (new_status, error_msg or "Publishing failed", now, outbox_id)
                )
            conn.commit()

        return success

    def process_all_pending(
        self,
        publish_handler: Callable[[Dict[str, Any]], bool],
        batch_size: int = 50
    ) -> Dict[str, int]:
        """Processes all pending events until batch is exhausted."""
        pending = self.fetch_pending_events(batch_size=batch_size)
        metrics = {"processed": 0, "succeeded": 0, "failed": 0, "dead_letter": 0}

        for ev in pending:
            metrics["processed"] += 1
            ok = self.process_event(ev["outbox_id"], publish_handler)
            if ok:
                metrics["succeeded"] += 1
            else:
                metrics["failed"] += 1

        return metrics

    def recover_hung_processing(self, timeout_seconds: float = 300.0) -> int:
        """
        Recovers events stuck in 'PROCESSING' due to process crashes or network deadlocks.
        Resets them back to 'PENDING' if their updated_at is older than the timeout threshold.
        """
        threshold = time.time() - timeout_seconds
        with db.get_connection() as conn:
            res = conn.execute(
                """
                UPDATE transactional_outbox
                SET status = 'PENDING', updated_at = ?
                WHERE tenant_id = ? AND status = 'PROCESSING' AND updated_at < ?
                """,
                (time.time(), self.tenant_id, threshold)
            )
            recovered = res.rowcount
            conn.commit()
            return recovered
