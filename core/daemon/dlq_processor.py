"""
ZONATA Dead-Letter Queue (DLQ) & Outbox Event Processor
======================================================
Processes outbox events with exponential backoff and jitter.
Isolates poison-pill events to DEAD_LETTER after max_attempts to preserve pipeline throughput.
"""

import time
import json
import random
import logging
from typing import Dict, Any, Callable, Optional, List
from core.db import db

logger = logging.getLogger("zonata.daemon.dlq")


class OutboxDLQProcessor:
    """Manages transactional outbox draining, exponential retry backoff, and DLQ isolation."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        base_backoff_sec: float = 1.0,
        max_backoff_sec: float = 300.0,
        lock_timeout_sec: float = 30.0,
    ):
        import uuid
        self.worker_id = worker_id or f"dlq_worker_{uuid.uuid4().hex[:8]}"
        self.base_backoff_sec = base_backoff_sec
        self.max_backoff_sec = max_backoff_sec
        self.lock_timeout_sec = lock_timeout_sec
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def register_handler(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        """Registers an asynchronous event processor for a specific topic."""
        self._handlers[topic] = handler

    def process_batch(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Drains a batch of ready outbox events.
        Returns counts of {'processed': int, 'succeeded': int, 'retried': int, 'dead_lettered': int}.
        """
        now = time.time()
        counts = {"processed": 0, "succeeded": 0, "retried": 0, "dead_lettered": 0}

        with db.get_connection() as conn:
            cur = conn.cursor()

            # Ensure outbox table exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS outbox_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 5,
                    last_error TEXT,
                    next_retry_at REAL NOT NULL,
                    locked_by TEXT,
                    locked_until REAL,
                    dispatched_at REAL,
                    created_at REAL NOT NULL
                )
            """)

            # Fetch ready events
            cur.execute(
                """
                SELECT id, topic, payload, attempts, max_attempts
                FROM outbox_events
                WHERE status IN ('PENDING', 'FAILED')
                  AND next_retry_at <= ?
                  AND (locked_until IS NULL OR locked_until < ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (now, now, batch_size),
            )
            rows = cur.fetchall()

            if not rows:
                return counts

            event_ids = [r[0] for r in rows]
            # Lock events
            placeholders = ",".join("?" for _ in event_ids)
            cur.execute(
                f"""
                UPDATE outbox_events
                SET status = 'PROCESSING', locked_by = ?, locked_until = ?
                WHERE id IN ({placeholders})
                """,
                [self.worker_id, now + self.lock_timeout_sec] + event_ids,
            )
            conn.commit()

            # Process locked events
            for event_id, topic, raw_payload, attempts, max_attempts in rows:
                counts["processed"] += 1
                try:
                    payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
                    handler = self._handlers.get(topic)
                    if handler:
                        handler(payload)
                    else:
                        logger.warning("No handler registered for topic '%s'; marking dispatched", topic)

                    # Success: mark dispatched
                    cur.execute(
                        """
                        UPDATE outbox_events
                        SET status = 'DISPATCHED', dispatched_at = ?, locked_by = NULL, locked_until = NULL
                        WHERE id = ?
                        """,
                        (time.time(), event_id),
                    )
                    counts["succeeded"] += 1
                except Exception as exc:
                    new_attempts = attempts + 1
                    err_msg = str(exc)
                    if new_attempts >= max_attempts:
                        # Move to DEAD_LETTER
                        cur.execute(
                            """
                            UPDATE outbox_events
                            SET status = 'DEAD_LETTER', attempts = ?, last_error = ?, locked_by = NULL, locked_until = NULL
                            WHERE id = ?
                            """,
                            (new_attempts, err_msg, event_id),
                        )
                        counts["dead_lettered"] += 1
                        logger.error("Event %s failed %d/%d times; moved to DEAD_LETTER: %s", event_id, new_attempts, max_attempts, err_msg)
                    else:
                        # Exponential backoff with jitter
                        delay = min(self.max_backoff_sec, self.base_backoff_sec * (2 ** new_attempts))
                        jitter = delay * random.uniform(0.1, 0.3)
                        next_retry = time.time() + delay + jitter
                        cur.execute(
                            """
                            UPDATE outbox_events
                            SET status = 'FAILED', attempts = ?, last_error = ?, next_retry_at = ?, locked_by = NULL, locked_until = NULL
                            WHERE id = ?
                            """,
                            (new_attempts, err_msg, next_retry, event_id),
                        )
                        counts["retried"] += 1
                        logger.info("Event %s scheduled for retry %d in %.2fs", event_id, new_attempts, delay + jitter)

                conn.commit()

        return counts

    def reprocess_dead_letter(self, event_id: str) -> bool:
        """Manually moves a dead-letter event back to PENDING for reprocessing."""
        now = time.time()
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE outbox_events
                SET status = 'PENDING', attempts = 0, next_retry_at = ?, last_error = NULL, locked_by = NULL, locked_until = NULL
                WHERE id = ? AND status = 'DEAD_LETTER'
                """,
                (now, event_id),
            )
            conn.commit()
            return cur.rowcount > 0
