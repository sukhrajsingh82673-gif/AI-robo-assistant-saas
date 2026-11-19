"""
ZONATA Universal AI Co-worker Fabric — Database Persistence Store
Ensures all Coworker profiles, execution graphs, tasks, leases, and supervision sessions
survive application restarts and system crashes.
"""

import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from .contracts import CoworkerProfile, ExecutionGraph, TaskNode, ExecutionState, RiskLevel

class CoworkerDBStore:
    """SQLite backing store for the Co-worker Fabric."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from core.db import get_default_db_path
            self.db_path = get_default_db_path()
        else:
            self.db_path = db_path
        self._init_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS coworker_profiles (
                    worker_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT,
                    skills TEXT,
                    capabilities TEXT,
                    authority_scope TEXT,
                    credential_scope TEXT,
                    allowed_providers TEXT,
                    risk_limit TEXT,
                    budget_limit REAL,
                    status TEXT,
                    created_at REAL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS coworker_execution_graphs (
                    mission_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    owner_objective TEXT,
                    status TEXT,
                    created_at REAL,
                    updated_at REAL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS coworker_execution_nodes (
                    task_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    title TEXT,
                    capability_id TEXT,
                    selected_provider TEXT,
                    state TEXT,
                    parameters TEXT,
                    risk_level TEXT,
                    idempotency_key TEXT,
                    result_json TEXT,
                    attempts INTEGER,
                    updated_at REAL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS coworker_supervision_sessions (
                    session_id TEXT PRIMARY KEY,
                    worker_id TEXT,
                    mode TEXT,
                    captured_state TEXT,
                    updated_at REAL
                );
            """)
            conn.commit()

    def save_worker_profile(self, profile: CoworkerProfile):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO coworker_profiles (
                    worker_id, tenant_id, role, department, skills, capabilities,
                    authority_scope, credential_scope, allowed_providers, risk_limit,
                    budget_limit, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (worker_id) DO UPDATE SET
                    tenant_id = EXCLUDED.tenant_id,
                    role = EXCLUDED.role,
                    department = EXCLUDED.department,
                    skills = EXCLUDED.skills,
                    capabilities = EXCLUDED.capabilities,
                    authority_scope = EXCLUDED.authority_scope,
                    credential_scope = EXCLUDED.credential_scope,
                    allowed_providers = EXCLUDED.allowed_providers,
                    risk_limit = EXCLUDED.risk_limit,
                    budget_limit = EXCLUDED.budget_limit,
                    status = EXCLUDED.status
            """, (
                profile.worker_id, profile.tenant_id, profile.role, profile.department,
                json.dumps(profile.skills), json.dumps(profile.capabilities),
                json.dumps(profile.authority_scope), json.dumps(profile.credential_scope),
                json.dumps(profile.allowed_providers), profile.risk_limit.value,
                profile.budget_limit, profile.status, profile.created_at
            ))
            conn.commit()

    def get_worker_profile(self, worker_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT * FROM coworker_profiles WHERE worker_id = ?", (worker_id,)).fetchone()
            if row:
                return dict(row)
            return None

    def save_graph(self, graph: ExecutionGraph):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO coworker_execution_graphs (
                    mission_id, tenant_id, owner_objective, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (mission_id) DO UPDATE SET
                    tenant_id = EXCLUDED.tenant_id,
                    owner_objective = EXCLUDED.owner_objective,
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
            """, (
                graph.mission_id, graph.tenant_id, graph.owner_objective,
                graph.status.value, graph.created_at, graph.updated_at
            ))

            for task_id, node in graph.nodes.items():
                cur.execute("""
                    INSERT INTO coworker_execution_nodes (
                        task_id, mission_id, title, capability_id, selected_provider,
                        state, parameters, risk_level, idempotency_key, attempts, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (task_id) DO UPDATE SET
                        mission_id = EXCLUDED.mission_id,
                        title = EXCLUDED.title,
                        capability_id = EXCLUDED.capability_id,
                        selected_provider = EXCLUDED.selected_provider,
                        state = EXCLUDED.state,
                        parameters = EXCLUDED.parameters,
                        risk_level = EXCLUDED.risk_level,
                        idempotency_key = EXCLUDED.idempotency_key,
                        attempts = EXCLUDED.attempts,
                        updated_at = EXCLUDED.updated_at
                """, (
                    node.task_id, node.mission_id, node.title, node.capability_id,
                    node.selected_provider, node.state.value, json.dumps(node.parameters),
                    node.risk_level.value, node.idempotency_key, node.attempts, time.time()
                ))
            conn.commit()
