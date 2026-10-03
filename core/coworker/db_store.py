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

    def __init__(self, db_path: str = "storage/roboassistant.db"):
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
                INSERT OR REPLACE INTO coworker_profiles (
                    worker_id, tenant_id, role, department, skills, capabilities,
                    authority_scope, credential_scope, allowed_providers, risk_limit,
                    budget_limit, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                INSERT OR REPLACE INTO coworker_execution_graphs (
                    mission_id, tenant_id, owner_objective, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                graph.mission_id, graph.tenant_id, graph.owner_objective,
                graph.status.value, graph.created_at, graph.updated_at
            ))

            for task_id, node in graph.nodes.items():
                cur.execute("""
                    INSERT OR REPLACE INTO coworker_execution_nodes (
                        task_id, mission_id, title, capability_id, selected_provider,
                        state, parameters, risk_level, idempotency_key, attempts, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node.task_id, node.mission_id, node.title, node.capability_id,
                    node.selected_provider, node.state.value, json.dumps(node.parameters),
                    node.risk_level.value, node.idempotency_key, node.attempts, time.time()
                ))
            conn.commit()
