"""
ZONATA Durable Transactional Outbox (OpenCode Step 1I)
Guarantees reliable, at-least-once asynchronous side-effect processing
with exponential backoff, dead-letter queue, and idempotent execution keys.
"""

from dataclasses import dataclass
from enum import Enum
import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

from core.db import db

logger = logging.getLogger("zonata.baseline.outbox")


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass
class OutboxEventRecord:
    id: str
    tenant_id: str
    company_id: str
    topic: str
    idempotency_key: str
    payload: Dict[str, Any]
    status: OutboxStatus
    attempts: int
    max_attempts: int
    last_error: Optional[str]
    next_retry_at: float
    locked_by: Optional[str]
    locked_until: Optional[float]
    dispatched_at: Optional[float]
    created_at: float


def ensure_outbox_tables(conn: Optional[Any] = None) -> None:
    """Ensures outbox_events table exists with multi-tenant RLS."""
    import pathlib
    from core.db import db, DatabaseDialect

    migration_file = "0018_always_on_baseline.sql"
    root_dir = pathlib.Path(__file__).resolve().parent.parent.parent

    if conn is not None:
        if hasattr(conn, "executescript") and db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                conn.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                conn.execute(sql_path.read_text(encoding="utf-8"))
        return

    with db.get_connection() as connection:
        if db.dialect == DatabaseDialect.SQLITE:
            sql_path = root_dir / "migrations" / "common" / migration_file
            if sql_path.exists():
                connection.executescript(sql_path.read_text(encoding="utf-8"))
        else:
            sql_path = root_dir / "migrations" / "pg" / migration_file
            if sql_path.exists():
                connection.execute(sql_path.read_text(encoding="utf-8"))


class DurableOutbox:
    """Manages transactional enqueuing, safe concurrency leasing, and worker draining."""

    def __init__(self, db_conn_factory=None):
        self.db_conn_factory = db_conn_factory or db.get_connection
        self._handlers: Dict[str, List[Tuple[str, Callable[[OutboxEventRecord], None]]]] = {}
        ensure_outbox_tables()

    def register_handler(
        self,
        topic: str,
        handler: Callable[[OutboxEventRecord], None],
        handler_key: Optional[str] = None,
    ) -> None:
        """Registers a durable side-effect handler for a topic with an idempotent handler key."""
        key = handler_key or getattr(handler, "__name__", str(uuid.uuid4()))
        if topic not in self._handlers:
            self._handlers[topic] = []
        # Prevent duplicate registration of the same handler key
        self._handlers[topic] = [h for h in self._handlers[topic] if h[0] != key]
        self._handlers[topic].append((key, handler))

    def enqueue(
        self,
        tenant_id: str,
        company_id: str,
        topic: str,
        idempotency_key: str,
        payload: Dict[str, Any],
        conn: Optional[Any] = None,
        max_attempts: int = 5,
    ) -> str:
        """Enqueues an outbox event within an existing or new database transaction.
        
        Strictly multi-tenant: scoped to tenant_id and company_id.
        Idempotent: Duplicate (tenant_id, company_id, idempotency_key) returns existing id.
        """
        now = time.time()
        event_id = f"obx_{uuid.uuid4().hex[:16]}"
        payload_json = json.dumps(payload, sort_keys=True)

        sql = """
        INSERT INTO outbox_events (
            id, tenant_id, company_id, topic, idempotency_key, payload,
            status, attempts, max_attempts, next_retry_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, ?, ?, ?)
        """

        def _do_insert(c):
            cur = c.cursor()
            try:
                cur.execute(
                    sql,
                    (
                        event_id,
                        tenant_id,
                        company_id,
                        topic,
                        idempotency_key,
                        payload_json,
                        max_attempts,
                        now,
                        now,
                    ),
                )
                if conn is None:
                    c.commit()
                return event_id
            except Exception as exc:
                # Idempotency collision check
                cur.execute(
                    """
                    SELECT id FROM outbox_events
                    WHERE tenant_id = ? AND company_id = ? AND idempotency_key = ?
                    """,
                    (tenant_id, company_id, idempotency_key),
                )
                row = cur.fetchone()
                if row:
                    return row[0]
                raise exc

        if conn is not None:
            return _do_insert(conn)
        else:
            with self.db_conn_factory() as c:
                return _do_insert(c)

    def drain(
        self,
        worker_id: str,
        batch_size: int = 50,
        lease_seconds: float = 30.0,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> int:
        """Drains pending or failed outbox events with lease locking and at-least-once delivery."""
        import contextlib
        from core.db import tenant_scope
        scope_ctx = tenant_scope(tenant_id, company_id) if tenant_id else contextlib.nullcontext()
        with scope_ctx:
            now = time.time()
            processed_count = 0

            with self.db_conn_factory() as conn:
                cur = conn.cursor()

                # 1. Claim eligible events with lease
                if db.is_postgresql():
                    cur.execute(
                        """
                        SELECT id, tenant_id, company_id, topic, idempotency_key, payload,
                               status, attempts, max_attempts, last_error, next_retry_at,
                               locked_by, locked_until, dispatched_at, created_at
                        FROM outbox_events
                        WHERE (status IN ('PENDING', 'FAILED') OR (status = 'PROCESSING' AND locked_until < ?))
                          AND next_retry_at <= ?
                        ORDER BY created_at ASC
                        LIMIT ?
                        FOR UPDATE SKIP LOCKED
                        """,
                        (now, now + 5.0, batch_size),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, tenant_id, company_id, topic, idempotency_key, payload,
                               status, attempts, max_attempts, last_error, next_retry_at,
                               locked_by, locked_until, dispatched_at, created_at
                        FROM outbox_events
                        WHERE (status IN ('PENDING', 'FAILED') OR (status = 'PROCESSING' AND locked_until < ?))
                          AND next_retry_at <= ?
                        ORDER BY created_at ASC
                        LIMIT ?
                        """,
                        (now, now + 5.0, batch_size),
                    )

                rows = cur.fetchall()
                if not rows:
                    return 0

                events: List[OutboxEventRecord] = []
                for r in rows:
                    ev = OutboxEventRecord(
                        id=r[0],
                        tenant_id=r[1],
                        company_id=r[2],
                        topic=r[3],
                        idempotency_key=r[4],
                        payload=json.loads(r[5]) if isinstance(r[5], str) else r[5],
                        status=OutboxStatus(r[6]),
                        attempts=r[7],
                        max_attempts=r[8],
                        last_error=r[9],
                        next_retry_at=r[10],
                        locked_by=r[11],
                        locked_until=r[12],
                        dispatched_at=r[13],
                        created_at=r[14],
                    )
                    events.append(ev)

                # Mark all claimed rows as PROCESSING with lease lock
                claimed_ids = [e.id for e in events]
                locked_until = now + lease_seconds
                placeholders = ",".join(["?"] * len(claimed_ids))
                cur.execute(
                    f"""
                    UPDATE outbox_events
                    SET status = 'PROCESSING', locked_by = ?, locked_until = ?
                    WHERE id IN ({placeholders})
                    """,
                    [worker_id, locked_until] + claimed_ids,
                )
                conn.commit()

            # 2. Process each event outside the claim lock
            for event in events:
                handlers = self._handlers.get(event.topic, []) + self._handlers.get("*", [])
                success = True
                handler_error = None

                try:
                    for handler_key, fn in handlers:
                        fn(event)
                except Exception as e:
                    success = False
                    handler_error = str(e)
                    logger.error(f"[Outbox Worker {worker_id}] Error executing handler for {event.id}: {e}")

                finish_time = time.time()
                with self.db_conn_factory() as update_conn:
                    update_cur = update_conn.cursor()
                    if success:
                        update_cur.execute(
                            """
                            UPDATE outbox_events
                            SET status = 'DISPATCHED', dispatched_at = ?, locked_by = NULL, locked_until = NULL, last_error = NULL
                            WHERE id = ?
                            """,
                            (finish_time, event.id),
                        )
                        processed_count += 1
                    else:
                        new_attempts = event.attempts + 1
                        if new_attempts >= event.max_attempts:
                            # Move to Dead Letter Queue
                            update_cur.execute(
                                """
                                UPDATE outbox_events
                                SET status = 'DEAD_LETTER', attempts = ?, last_error = ?, locked_by = NULL, locked_until = NULL
                                WHERE id = ?
                                """,
                                (new_attempts, handler_error, event.id),
                            )
                        else:
                            # Exponential backoff: base 2 seconds (2, 4, 8, 16...)
                            backoff_seconds = 2.0 ** new_attempts
                            next_retry = finish_time + backoff_seconds
                            update_cur.execute(
                                """
                                UPDATE outbox_events
                                SET status = 'FAILED', attempts = ?, next_retry_at = ?, last_error = ?, locked_by = NULL, locked_until = NULL
                                WHERE id = ?
                                """,
                                (new_attempts, next_retry, handler_error, event.id),
                            )
                    update_conn.commit()

            return processed_count

    def get_event(self, event_id: str) -> Optional[OutboxEventRecord]:
        """Fetches an outbox event by ID."""
        with self.db_conn_factory() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, tenant_id, company_id, topic, idempotency_key, payload,
                       status, attempts, max_attempts, last_error, next_retry_at,
                       locked_by, locked_until, dispatched_at, created_at
                FROM outbox_events
                WHERE id = ?
                """,
                (event_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            return OutboxEventRecord(
                id=r[0],
                tenant_id=r[1],
                company_id=r[2],
                topic=r[3],
                idempotency_key=r[4],
                payload=json.loads(r[5]) if isinstance(r[5], str) else r[5],
                status=OutboxStatus(r[6]),
                attempts=r[7],
                max_attempts=r[8],
                last_error=r[9],
                next_retry_at=r[10],
                locked_by=r[11],
                locked_until=r[12],
                dispatched_at=r[13],
                created_at=r[14],
            )
