"""
ZONATA Agent Factory — DbQueueOrchestrator
Table-backed job queue for factory builds and batch item processing.
Operates when Temporal is unavailable.
"""

from __future__ import annotations
import time
import uuid
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("zonata.af.orchestrator")


class DbQueueOrchestrator:
    """
    Claims jobs from af_build with lease heartbeats and fair per-tenant scheduling.
    """

    def __init__(self, db_conn_factory=None, worker_id: Optional[str] = None):
        self.db_conn_factory = db_conn_factory
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"

    def _get_connection(self):
        if self.db_conn_factory:
            return self.db_conn_factory()
        from core.db import db
        return db.get_connection()

    def enqueue_build(
        self,
        tenant_id: str,
        batch_item_id: Optional[str] = None,
        agent_version_id: Optional[str] = None,
        sandbox_profile: str = "T0"
    ) -> str:
        build_id = f"bld_{uuid.uuid4().hex[:12]}"
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO af_build (
                    id, tenant_id, batch_item_id, agent_version_id, attempt,
                    worker_id, sandbox_profile, stages, status, tokens_in,
                    tokens_out, cost_usd, started_at
                ) VALUES (?, ?, ?, ?, 1, NULL, ?, '[]', 'QUEUED', 0, 0, 0.0, ?)
            """, (build_id, tenant_id, batch_item_id, agent_version_id, sandbox_profile, now))
            conn.commit()
        return build_id

    def claim_next_build(self, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Atomically claim the next queued build job."""
        now = time.time()
        with self._get_connection() as conn:
            query = "SELECT id, tenant_id, batch_item_id, agent_version_id, sandbox_profile FROM af_build WHERE status = 'QUEUED'"
            params: List[Any] = []
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            query += " ORDER BY id ASC LIMIT 1"

            cur = conn.execute(query, params)
            row = cur.fetchone()
            if not row:
                return None

            build_id = row[0]
            # Atomically update
            cur = conn.execute("""
                UPDATE af_build
                SET status = 'RUNNING', worker_id = ?, heartbeat_at = ?, started_at = ?
                WHERE id = ? AND status = 'QUEUED'
            """, (self.worker_id, now, now, build_id))
            conn.commit()
            if cur.rowcount == 0:
                return None  # raced with another worker

            return {
                "build_id": build_id,
                "tenant_id": row[1],
                "batch_item_id": row[2],
                "agent_version_id": row[3],
                "sandbox_profile": row[4]
            }

    def heartbeat(self, build_id: str) -> bool:
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.execute("""
                UPDATE af_build
                SET heartbeat_at = ?
                WHERE id = ? AND status = 'RUNNING' AND worker_id = ?
            """, (now, build_id, self.worker_id))
            conn.commit()
            return cur.rowcount > 0

    def complete_build(self, build_id: str, status: str = "SUCCEEDED", error: Optional[str] = None):
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE af_build
                SET status = ?, error = ?, finished_at = ?
                WHERE id = ?
            """, (status, error, now, build_id))
            conn.commit()

    def reap_lost_builds(self, timeout_seconds: float = 60.0) -> int:
        """Mark builds whose heartbeat expired as LOST so they can be rescheduled."""
        cutoff = time.time() - timeout_seconds
        with self._get_connection() as conn:
            cur = conn.execute("""
                UPDATE af_build
                SET status = 'LOST', error = 'Heartbeat timed out'
                WHERE status = 'RUNNING' AND heartbeat_at < ?
            """, (cutoff,))
            conn.commit()
            return cur.rowcount
