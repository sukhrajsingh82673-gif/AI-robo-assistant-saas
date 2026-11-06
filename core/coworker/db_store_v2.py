"""
ZONATA Autonomous Coworker 2.0 — Relational Storage Engine (Phase A)
Manages transactional persistence for Coworker 2.0 tasks, state transitions,
leases, cleanup manifests, subworker records, and security patrol findings.
"""

from __future__ import annotations
import sqlite3
import json
import time
import uuid
import os
import sys
from typing import Optional, List, Dict, Any, Tuple
from .contracts_v2 import (
    TaskLifecycleState, CoworkerV2Task, TaskStateTransition,
    CoworkerExecutionLease, CleanupManifestRecord, CleanupResourceType,
    CleanupStatus, SecurityPatrolFinding, PatrolType, PatrolSeverity,
    LeaseStatus, SubworkerV2Record
)


class CoworkerDbStoreV2:
    """
    Thread-safe, crash-resilient SQLite storage adapter for Coworker 2.0.
    Integrates with core.db or operates standalone against any specified SQLite path.
    """

    SCHEMA_SQL = """
    -- 1. Tasks Table
    CREATE TABLE IF NOT EXISTS coworker_v2_tasks (
        task_id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        tenant_id TEXT NOT NULL DEFAULT 'tnt_primary',
        company_id TEXT NOT NULL DEFAULT 'cmp_primary',
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL DEFAULT 'TASK_RECEIVED',
        parameters JSON NOT NULL DEFAULT '{}',
        risk_level TEXT NOT NULL DEFAULT 'LOW',
        authority_scope JSON NOT NULL DEFAULT '["read_only"]',
        budget_allocated_usd REAL NOT NULL DEFAULT 5.0,
        budget_spent_usd REAL NOT NULL DEFAULT 0.0,
        lease_id TEXT,
        assigned_worker_id TEXT,
        result JSON,
        verification JSON,
        error_message TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        completed_at REAL,
        metadata JSON NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_task_state ON coworker_v2_tasks(state);
    CREATE INDEX IF NOT EXISTS idx_cw2_task_mission ON coworker_v2_tasks(mission_id);
    CREATE INDEX IF NOT EXISTS idx_cw2_task_tenant ON coworker_v2_tasks(tenant_id);

    -- 2. State Transitions Log (Immutable Audit Trail)
    CREATE TABLE IF NOT EXISTS coworker_v2_task_transitions (
        transition_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        from_state TEXT NOT NULL,
        to_state TEXT NOT NULL,
        reason TEXT NOT NULL,
        trigger TEXT NOT NULL DEFAULT 'orchestrator',
        timestamp REAL NOT NULL,
        metadata JSON NOT NULL DEFAULT '{}',
        FOREIGN KEY (task_id) REFERENCES coworker_v2_tasks(task_id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_trans_task ON coworker_v2_task_transitions(task_id);
    CREATE INDEX IF NOT EXISTS idx_cw2_trans_time ON coworker_v2_task_transitions(timestamp);

    -- 3. Execution Leases
    CREATE TABLE IF NOT EXISTS coworker_v2_leases (
        lease_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        worker_id TEXT NOT NULL,
        acquired_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        heartbeat_at REAL NOT NULL,
        ttl_seconds REAL NOT NULL DEFAULT 300.0,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        FOREIGN KEY (task_id) REFERENCES coworker_v2_tasks(task_id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_lease_task ON coworker_v2_leases(task_id);
    CREATE INDEX IF NOT EXISTS idx_cw2_lease_status ON coworker_v2_leases(status);

    -- 4. Ephemeral Subworkers
    CREATE TABLE IF NOT EXISTS coworker_v2_subworkers (
        worker_id TEXT PRIMARY KEY,
        parent_task_id TEXT NOT NULL,
        parent_worker_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        archetype TEXT NOT NULL,
        authority_scope JSON NOT NULL DEFAULT '[]',
        budget_limit_usd REAL NOT NULL DEFAULT 1.0,
        budget_spent_usd REAL NOT NULL DEFAULT 0.0,
        lease_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at REAL NOT NULL,
        decommissioned_at REAL,
        metadata JSON NOT NULL DEFAULT '{}',
        FOREIGN KEY (parent_task_id) REFERENCES coworker_v2_tasks(task_id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_subworker_task ON coworker_v2_subworkers(parent_task_id);

    -- 5. Cleanup Manifests
    CREATE TABLE IF NOT EXISTS coworker_v2_cleanup_manifests (
        manifest_id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_path TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at REAL NOT NULL,
        cleaned_at REAL,
        error TEXT,
        metadata JSON NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_cleanup_status ON coworker_v2_cleanup_manifests(status);
    CREATE INDEX IF NOT EXISTS idx_cw2_cleanup_task ON coworker_v2_cleanup_manifests(task_id);

    -- 6. Security Patrol Findings
    CREATE TABLE IF NOT EXISTS coworker_v2_security_patrols (
        finding_id TEXT PRIMARY KEY,
        patrol_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        description TEXT NOT NULL,
        target TEXT NOT NULL,
        auto_remediated INTEGER NOT NULL DEFAULT 0,
        remediation_action TEXT,
        detected_at REAL NOT NULL,
        metadata JSON NOT NULL DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_patrol_sev ON coworker_v2_security_patrols(severity);
    CREATE INDEX IF NOT EXISTS idx_cw2_patrol_time ON coworker_v2_security_patrols(detected_at);

    -- 7. Transactional Outbox for Reliable PostgreSQL Sync
    CREATE TABLE IF NOT EXISTS coworker_v2_outbox (
        event_id TEXT PRIMARY KEY,
        aggregate_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload JSON NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        retry_count INTEGER NOT NULL DEFAULT 0,
        next_retry_at REAL NOT NULL DEFAULT 0.0,
        created_at REAL NOT NULL,
        synced_at REAL,
        last_error TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_cw2_outbox_status ON coworker_v2_outbox(status, next_retry_at);
    CREATE INDEX IF NOT EXISTS idx_cw2_outbox_agg ON coworker_v2_outbox(aggregate_id);
    """

    _instance: Optional[CoworkerDbStoreV2] = None

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> CoworkerDbStoreV2:
        if cls._instance is None:
            cls._instance = cls(db_path=db_path)
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            env_path = os.environ.get("ZONATA_SESSION_TEST_DB") or os.environ.get("ZONATA_DB_PATH")
            if env_path:
                self.db_path = env_path
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                storage_dir = os.path.join(base_dir, "storage")
                os.makedirs(storage_dir, exist_ok=True)
                self.db_path = os.path.join(storage_dir, "roboassistant.db")
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self) -> None:
        """Executes table creation script with atomic commit."""
        with self.get_connection() as conn:
            conn.executescript(self.SCHEMA_SQL)
            conn.commit()

    # --- Task Persistence ---

    def save_task(self, task: CoworkerV2Task) -> CoworkerV2Task:
        sql = """
        INSERT INTO coworker_v2_tasks (
            task_id, mission_id, tenant_id, company_id, title, description,
            state, parameters, risk_level, authority_scope, budget_allocated_usd,
            budget_spent_usd, lease_id, assigned_worker_id, result, verification,
            error_message, created_at, updated_at, completed_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            title=excluded.title,
            description=excluded.description,
            state=excluded.state,
            parameters=excluded.parameters,
            risk_level=excluded.risk_level,
            authority_scope=excluded.authority_scope,
            budget_allocated_usd=excluded.budget_allocated_usd,
            budget_spent_usd=excluded.budget_spent_usd,
            lease_id=excluded.lease_id,
            assigned_worker_id=excluded.assigned_worker_id,
            result=excluded.result,
            verification=excluded.verification,
            error_message=excluded.error_message,
            updated_at=excluded.updated_at,
            completed_at=excluded.completed_at,
            metadata=excluded.metadata;
        """
        now = time.time()
        task.updated_at = now
        outbox_id = f"evt_{uuid.uuid4().hex[:12]}"
        payload = {
            "task_id": task.task_id,
            "tenant_id": task.tenant_id,
            "company_id": task.company_id,
            "assigned_worker_id": task.assigned_worker_id or "coworker_2.0",
            "title": task.title or task.description,
            "description": task.description,
            "state": task.state.value,
            "risk_level": task.risk_level,
            "lease_id": task.lease_id,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "completed_at": task.completed_at
        }
        with self.get_connection() as conn:
            conn.execute(sql, (
                task.task_id, task.mission_id, task.tenant_id, task.company_id,
                task.title, task.description, task.state.value,
                json.dumps(task.parameters), task.risk_level,
                json.dumps(task.authority_scope), task.budget_allocated_usd,
                task.budget_spent_usd, task.lease_id, task.assigned_worker_id,
                json.dumps(task.result) if task.result is not None else None,
                json.dumps(task.verification) if task.verification is not None else None,
                task.error_message, task.created_at, task.updated_at,
                task.completed_at, json.dumps(task.metadata)
            ))
            # Transactional Outbox write in the same atomic SQLite transaction
            conn.execute("""
                INSERT INTO coworker_v2_outbox (
                    event_id, aggregate_id, event_type, payload, status, retry_count, next_retry_at, created_at
                ) VALUES (?, ?, ?, ?, 'PENDING', 0, ?, ?);
            """, (outbox_id, task.task_id, "TASK_STATE_CHANGE", json.dumps(payload), now, now))
            conn.commit()

        # Opportunistic outbox sync attempt (asynchronous relay, bypassed in pytest to prevent remote network latency)
        if "pytest" not in sys.modules and not os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("COWORKER_DISABLE_OUTBOX_AUTOFLUSH"):
            try:
                self.flush_outbox(batch_size=25)
            except Exception:
                pass
        return task

    def flush_outbox(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Durable Transactional Outbox Flush:
        Reads PENDING outbox events where next_retry_at <= now,
        attempts atomic upsert to PostgreSQL coworker_tasks,
        and marks events SYNCED on success or increments retry_count with exponential backoff on failure.
        """
        now = time.time()
        sql_fetch = """
        SELECT * FROM coworker_v2_outbox
        WHERE status = 'PENDING' AND next_retry_at <= ?
        ORDER BY created_at ASC LIMIT ?;
        """
        events_to_sync: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            cur = conn.execute(sql_fetch, (now, batch_size))
            events_to_sync = [dict(r) for r in cur.fetchall()]

        if not events_to_sync:
            return {"synced": 0, "failed": 0, "pending": 0}

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            try:
                import dotenv
                dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
                db_url = os.environ.get("DATABASE_URL")
            except Exception:
                pass

        if not db_url:
            return {"synced": 0, "failed": 0, "pending": len(events_to_sync)}

        synced_count = 0
        failed_count = 0

        try:
            import psycopg2
            with psycopg2.connect(db_url, connect_timeout=5) as pg_conn:
                with pg_conn.cursor() as cur:
                    for ev in events_to_sync:
                        p = json.loads(ev["payload"])
                        try:
                            # Ensure tenant exists in PostgreSQL authoritative schema to prevent FK violations
                            tnt_id = p.get("tenant_id") or "tnt_primary"
                            cur.execute("""
                                INSERT INTO tenants (tenant_id, name, plan, status, created_at)
                                VALUES (%s, %s, 'ENTERPRISE', 'ACTIVE', %s)
                                ON CONFLICT (tenant_id) DO NOTHING;
                            """, (tnt_id, f"Tenant {tnt_id}", p.get("created_at", now)))

                            cur.execute("""
                                INSERT INTO coworker_tasks (
                                    task_id, tenant_id, company_id, user_id, workspace_mode,
                                    prompt, target_outcome, status, permission_tier,
                                    approval_status, execution_log, receipt_id, created_at, completed_at
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT(task_id) DO UPDATE SET
                                    status = EXCLUDED.status,
                                    execution_log = EXCLUDED.execution_log,
                                    completed_at = EXCLUDED.completed_at;
                            """, (
                                p["task_id"], tnt_id, p.get("company_id", "cmp_primary"), p.get("assigned_worker_id", "worker_primary"),
                                "SANDBOX", p["title"], p["description"], p["state"],
                                p["risk_level"], "APPROVED",
                                json.dumps({"state": p["state"], "error": p.get("error_message"), "lease": p.get("lease_id")}),
                                p.get("lease_id"), p["created_at"], p.get("completed_at")
                            ))
                            with self.get_connection() as s_conn:
                                s_conn.execute("""
                                    UPDATE coworker_v2_outbox
                                    SET status = 'SYNCED', synced_at = ?, last_error = NULL
                                    WHERE event_id = ?;
                                """, (time.time(), ev["event_id"]))
                                s_conn.commit()
                            synced_count += 1
                        except Exception as item_err:
                            with self.get_connection() as s_conn:
                                s_conn.execute("""
                                    UPDATE coworker_v2_outbox
                                    SET status = 'ITEM_FAILED', last_error = ?
                                    WHERE event_id = ?;
                                """, (str(item_err)[:255], ev["event_id"]))
                                s_conn.commit()
                            failed_count += 1
                pg_conn.commit()
        except Exception as conn_err:
            now_err = time.time()
            with self.get_connection() as s_conn:
                for ev in events_to_sync:
                    retries = ev.get("retry_count", 0) + 1
                    backoff = min(300.0, 2.0 ** min(retries, 8))
                    s_conn.execute("""
                        UPDATE coworker_v2_outbox
                        SET retry_count = ?, next_retry_at = ?, last_error = ?
                        WHERE event_id = ?;
                    """, (retries, now_err + backoff, str(conn_err)[:255], ev["event_id"]))
                s_conn.commit()
            failed_count = len(events_to_sync)

        return {"synced": synced_count, "failed": failed_count, "pending": len(events_to_sync) - synced_count}

    def reconcile_outbox(self, retry_failed: bool = True) -> Dict[str, int]:
        """Runs complete sweep of all pending and retriable outbox events."""
        if retry_failed:
            with self.get_connection() as conn:
                conn.execute("UPDATE coworker_v2_outbox SET status = 'PENDING', next_retry_at = 0.0 WHERE status = 'ITEM_FAILED';")
                conn.commit()
        total_synced = 0
        total_failed = 0
        while True:
            res = self.flush_outbox(batch_size=50)
            total_synced += res["synced"]
            total_failed += res["failed"]
            if res["synced"] == 0 and res["failed"] == 0:
                break
        return {"total_synced": total_synced, "total_failed": total_failed}

    def get_outbox_stats(self) -> Dict[str, int]:
        sql = "SELECT status, COUNT(*) as cnt FROM coworker_v2_outbox GROUP BY status;"
        stats = {"PENDING": 0, "SYNCED": 0, "ITEM_FAILED": 0}
        with self.get_connection() as conn:
            cur = conn.execute(sql)
            for r in cur.fetchall():
                stats[r["status"]] = r["cnt"]
        return stats

    def get_task(self, task_id: str) -> Optional[CoworkerV2Task]:
        sql = "SELECT * FROM coworker_v2_tasks WHERE task_id = ?;"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def list_active_tasks(self, tenant_id: Optional[str] = None) -> List[CoworkerV2Task]:
        terminal_states = (
            TaskLifecycleState.IDLE.value,
            TaskLifecycleState.TERMINATED.value,
            TaskLifecycleState.REPORTING_TO_CEO.value,
        )
        placeholders = ",".join("?" for _ in terminal_states)
        params: List[Any] = list(terminal_states)
        sql = f"SELECT * FROM coworker_v2_tasks WHERE state NOT IN ({placeholders})"
        if tenant_id:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY updated_at DESC;"

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [self._row_to_task(r) for r in cursor.fetchall()]

    def list_tasks_by_state(self, state: TaskLifecycleState, tenant_id: Optional[str] = None) -> List[CoworkerV2Task]:
        params: List[Any] = [state.value]
        sql = "SELECT * FROM coworker_v2_tasks WHERE state = ?"
        if tenant_id:
            sql += " AND tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY updated_at DESC;"

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [self._row_to_task(r) for r in cursor.fetchall()]

    # --- Transitions ---

    def record_transition(self, transition: TaskStateTransition) -> None:
        sql = """
        INSERT INTO coworker_v2_task_transitions (
            transition_id, task_id, from_state, to_state, reason, trigger, timestamp, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.get_connection() as conn:
            conn.execute(sql, (
                transition.transition_id, transition.task_id,
                transition.from_state.value, transition.to_state.value,
                transition.reason, transition.trigger,
                transition.timestamp, json.dumps(transition.metadata)
            ))
            conn.commit()

    def get_transitions(self, task_id: str) -> List[TaskStateTransition]:
        sql = "SELECT * FROM coworker_v2_task_transitions WHERE task_id = ? ORDER BY timestamp ASC;"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (task_id,))
            results = []
            for r in cursor.fetchall():
                results.append(TaskStateTransition(
                    transition_id=r["transition_id"],
                    task_id=r["task_id"],
                    from_state=TaskLifecycleState(r["from_state"]),
                    to_state=TaskLifecycleState(r["to_state"]),
                    reason=r["reason"],
                    trigger=r["trigger"],
                    timestamp=r["timestamp"],
                    metadata=json.loads(r["metadata"] or "{}")
                ))
            return results

    def get_task_transitions(self, task_id: str) -> List[TaskStateTransition]:
        return self.get_transitions(task_id)

    def list_tasks(self, limit: int = 50, tenant_id: Optional[str] = None) -> List[CoworkerV2Task]:
        sql = "SELECT * FROM coworker_v2_tasks"
        params: List[Any] = []
        if tenant_id:
            sql += " WHERE tenant_id = ?"
            params.append(tenant_id)
        sql += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)
        with self.get_connection() as conn:
            cursor = conn.execute(sql, tuple(params))
            return [self._row_to_task(r) for r in cursor.fetchall()]

    # --- Leases ---

    def save_lease(self, lease: CoworkerExecutionLease) -> None:
        sql = """
        INSERT INTO coworker_v2_leases (
            lease_id, task_id, worker_id, acquired_at, expires_at, heartbeat_at, ttl_seconds, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(lease_id) DO UPDATE SET
            expires_at=excluded.expires_at,
            heartbeat_at=excluded.heartbeat_at,
            status=excluded.status;
        """
        with self.get_connection() as conn:
            conn.execute(sql, (
                lease.lease_id, lease.task_id, lease.worker_id,
                lease.acquired_at, lease.expires_at, lease.heartbeat_at,
                lease.ttl_seconds, lease.status.value
            ))
            conn.commit()

    def get_lease(self, lease_id: str) -> Optional[CoworkerExecutionLease]:
        sql = "SELECT * FROM coworker_v2_leases WHERE lease_id = ?;"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (lease_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return CoworkerExecutionLease(
                lease_id=r["lease_id"],
                task_id=r["task_id"],
                worker_id=r["worker_id"],
                acquired_at=r["acquired_at"],
                expires_at=r["expires_at"],
                heartbeat_at=r["heartbeat_at"],
                ttl_seconds=r["ttl_seconds"],
                status=LeaseStatus(r["status"])
            )

    def get_active_lease(self, task_id: str) -> Optional[CoworkerExecutionLease]:
        task = self.get_task(task_id)
        if not task or not task.lease_id:
            return None
        lease = self.get_lease(task.lease_id)
        if lease and lease.status == LeaseStatus.ACTIVE and time.time() > lease.expires_at:
            lease.status = LeaseStatus.EXPIRED
            self.save_lease(lease)
        return lease

    # --- Ephemeral Subworkers ---

    def save_subworker(self, subworker: SubworkerV2Record) -> None:
        sql = """
        INSERT INTO coworker_v2_subworkers (
            worker_id, parent_task_id, parent_worker_id, mission_id, archetype,
            authority_scope, budget_limit_usd, budget_spent_usd, lease_id,
            status, created_at, decommissioned_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(worker_id) DO UPDATE SET
            budget_spent_usd=excluded.budget_spent_usd,
            status=excluded.status,
            decommissioned_at=excluded.decommissioned_at,
            metadata=excluded.metadata;
        """
        with self.get_connection() as conn:
            conn.execute(sql, (
                subworker.worker_id, subworker.parent_task_id, subworker.parent_worker_id,
                subworker.mission_id, subworker.archetype,
                json.dumps(subworker.authority_scope), subworker.budget_limit_usd,
                subworker.budget_spent_usd, subworker.lease_id,
                subworker.status, subworker.created_at, subworker.decommissioned_at,
                json.dumps(subworker.metadata)
            ))
            conn.commit()

    def get_subworker(self, worker_id: str) -> Optional[SubworkerV2Record]:
        sql = "SELECT * FROM coworker_v2_subworkers WHERE worker_id = ?;"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (worker_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return SubworkerV2Record(
                worker_id=r["worker_id"],
                parent_task_id=r["parent_task_id"],
                parent_worker_id=r["parent_worker_id"],
                mission_id=r["mission_id"],
                archetype=r["archetype"],
                authority_scope=json.loads(r["authority_scope"] or "[]"),
                budget_limit_usd=r["budget_limit_usd"],
                budget_spent_usd=r["budget_spent_usd"],
                lease_id=r["lease_id"],
                status=r["status"],
                created_at=r["created_at"],
                decommissioned_at=r["decommissioned_at"],
                metadata=json.loads(r["metadata"] or "{}")
            )

    def list_subworkers(self, parent_task_id: str) -> List[SubworkerV2Record]:
        sql = "SELECT * FROM coworker_v2_subworkers WHERE parent_task_id = ? ORDER BY created_at ASC;"
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (parent_task_id,))
            return [
                SubworkerV2Record(
                    worker_id=r["worker_id"],
                    parent_task_id=r["parent_task_id"],
                    parent_worker_id=r["parent_worker_id"],
                    mission_id=r["mission_id"],
                    archetype=r["archetype"],
                    authority_scope=json.loads(r["authority_scope"] or "[]"),
                    budget_limit_usd=r["budget_limit_usd"],
                    budget_spent_usd=r["budget_spent_usd"],
                    lease_id=r["lease_id"],
                    status=r["status"],
                    created_at=r["created_at"],
                    decommissioned_at=r["decommissioned_at"],
                    metadata=json.loads(r["metadata"] or "{}")
                )
                for r in cursor.fetchall()
            ]

    # --- Cleanup Manifests ---

    def add_cleanup_record(self, record: CleanupManifestRecord) -> None:
        sql = """
        INSERT INTO coworker_v2_cleanup_manifests (
            manifest_id, task_id, mission_id, resource_type, resource_path,
            status, created_at, cleaned_at, error, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.get_connection() as conn:
            conn.execute(sql, (
                record.manifest_id, record.task_id, record.mission_id,
                record.resource_type.value, record.resource_path,
                record.status.value, record.created_at, record.cleaned_at,
                record.error, json.dumps(record.metadata)
            ))
            conn.commit()

    def list_pending_cleanups(self, mission_id: Optional[str] = None, task_id: Optional[str] = None) -> List[CleanupManifestRecord]:
        params: List[Any] = [CleanupStatus.PENDING.value]
        sql = "SELECT * FROM coworker_v2_cleanup_manifests WHERE status = ?"
        if mission_id:
            sql += " AND mission_id = ?"
            params.append(mission_id)
        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)
        sql += " ORDER BY created_at ASC;"

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [
                CleanupManifestRecord(
                    manifest_id=r["manifest_id"],
                    task_id=r["task_id"],
                    mission_id=r["mission_id"],
                    resource_type=CleanupResourceType(r["resource_type"]),
                    resource_path=r["resource_path"],
                    status=CleanupStatus(r["status"]),
                    created_at=r["created_at"],
                    cleaned_at=r["cleaned_at"],
                    error=r["error"],
                    metadata=json.loads(r["metadata"] or "{}")
                )
                for r in cursor.fetchall()
            ]

    def mark_cleaned(self, manifest_id: str, success: bool, error: Optional[str] = None) -> None:
        status = CleanupStatus.CLEANED.value if success else CleanupStatus.FAILED.value
        now = time.time()
        sql = """
        UPDATE coworker_v2_cleanup_manifests
        SET status = ?, cleaned_at = ?, error = ?
        WHERE manifest_id = ?;
        """
        with self.get_connection() as conn:
            conn.execute(sql, (status, now, error, manifest_id))
            conn.commit()

    # --- Security Patrol Findings ---

    def record_patrol_finding(self, finding: SecurityPatrolFinding) -> None:
        sql = """
        INSERT INTO coworker_v2_security_patrols (
            finding_id, patrol_type, severity, description, target,
            auto_remediated, remediation_action, detected_at, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with self.get_connection() as conn:
            conn.execute(sql, (
                finding.finding_id, finding.patrol_type.value, finding.severity.value,
                finding.description, finding.target, 1 if finding.auto_remediated else 0,
                finding.remediation_action, finding.detected_at, json.dumps(finding.metadata)
            ))
            conn.commit()

    def list_patrol_findings(self, limit: int = 50, severity: Optional[str] = None) -> List[SecurityPatrolFinding]:
        params: List[Any] = []
        sql = "SELECT * FROM coworker_v2_security_patrols"
        if severity:
            sql += " WHERE severity = ?"
            params.append(severity)
        sql += " ORDER BY detected_at DESC LIMIT ?;"
        params.append(limit)

        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [
                SecurityPatrolFinding(
                    finding_id=r["finding_id"],
                    patrol_type=PatrolType(r["patrol_type"]),
                    severity=PatrolSeverity(r["severity"]),
                    description=r["description"],
                    target=r["target"],
                    auto_remediated=bool(r["auto_remediated"]),
                    remediation_action=r["remediation_action"],
                    detected_at=r["detected_at"],
                    metadata=json.loads(r["metadata"] or "{}")
                )
                for r in cursor.fetchall()
            ]

    # --- Crash Recovery Helper ---

    def recover_orphaned_tasks(self, max_stale_seconds: float = 300.0) -> List[CoworkerV2Task]:
        """
        Identifies active tasks whose lease has expired or whose heartbeats
        have stalled past max_stale_seconds, updates them to ERROR_RECOVERY.
        """
        now = time.time()
        active_states = (
            TaskLifecycleState.TASK_ANALYSIS.value,
            TaskLifecycleState.TOOL_DISCOVERY.value,
            TaskLifecycleState.EXECUTION.value,
            TaskLifecycleState.VERIFICATION.value,
        )
        placeholders = ",".join("?" for _ in active_states)
        sql = f"""
        SELECT t.* FROM coworker_v2_tasks t
        LEFT JOIN coworker_v2_leases l ON t.lease_id = l.lease_id
        WHERE t.state IN ({placeholders})
          AND (l.lease_id IS NULL OR l.expires_at < ? OR (? - l.heartbeat_at) > ?);
        """
        recovered: List[CoworkerV2Task] = []
        with self.get_connection() as conn:
            cursor = conn.execute(sql, (*active_states, now, now, max_stale_seconds))
            for r in cursor.fetchall():
                task = self._row_to_task(r)
                prev_state = task.state
                task.state = TaskLifecycleState.ERROR_RECOVERY
                task.error_message = f"Lease heartbeat expired (stale > {max_stale_seconds}s). Auto-recovered from crash."
                task.updated_at = now
                self.save_task(task)

                if task.lease_id:
                    lease = self.get_lease(task.lease_id)
                    if lease and lease.status == LeaseStatus.ACTIVE:
                        lease.status = LeaseStatus.EXPIRED
                        self.save_lease(lease)

                trans = TaskStateTransition(
                    transition_id=f"tr_rec_{uuid.uuid4().hex[:8]}",
                    task_id=task.task_id,
                    from_state=prev_state,
                    to_state=TaskLifecycleState.ERROR_RECOVERY,
                    reason="Lease expired / node crash recovery",
                    trigger="crash_recovery_engine",
                    timestamp=now
                )
                self.record_transition(trans)
                recovered.append(task)
        return recovered

    def _row_to_task(self, r: sqlite3.Row) -> CoworkerV2Task:
        return CoworkerV2Task(
            task_id=r["task_id"],
            mission_id=r["mission_id"],
            tenant_id=r["tenant_id"],
            company_id=r["company_id"],
            title=r["title"],
            description=r["description"],
            state=TaskLifecycleState(r["state"]),
            parameters=json.loads(r["parameters"] or "{}"),
            risk_level=r["risk_level"],
            authority_scope=json.loads(r["authority_scope"] or "[]"),
            budget_allocated_usd=r["budget_allocated_usd"],
            budget_spent_usd=r["budget_spent_usd"],
            lease_id=r["lease_id"],
            assigned_worker_id=r["assigned_worker_id"],
            result=json.loads(r["result"]) if r["result"] else None,
            verification=json.loads(r["verification"]) if r["verification"] else None,
            error_message=r["error_message"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            completed_at=r["completed_at"],
            metadata=json.loads(r["metadata"] or "{}")
        )
