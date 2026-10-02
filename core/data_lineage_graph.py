"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 13 & 14 — Enterprise Data Lineage Graph & AI Action Provenance Plane
Tracks the complete provenance chain:
USER -> AI EMPLOYEE -> MISSION -> MODEL -> RETRIEVED DATA -> TOOL -> ACTION -> EXTERNAL SYSTEM -> RESULT -> VERIFICATION -> BUSINESS OUTCOME

Constitutional Invariants:
  NO_ORPHAN_ACTIONS
  NO_ANONYMOUS_AI_MUTATIONS
  EVERY_BUSINESS_OUTCOME_MUST_TRACE_TO_IDENTITY_AND_EVIDENCE
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from core.database_engine import engine, WorkloadType

logger = logging.getLogger("zonata.data.lineage")

@dataclass
class LineageNode:
    node_id: str
    node_type: str         # USER, AI_EMPLOYEE, MISSION, MODEL, DATA_OBJECT, TOOL, ACTION, EXTERNAL_SYSTEM, OUTCOME
    tenant_id: str
    company_id: str
    label: str
    attributes: Dict[str, Any]
    created_at: float

@dataclass
class LineageEdge:
    edge_id: str
    source_id: str
    target_id: str
    relationship: str      # INITIATED_BY, RETRIEVED, PROCESSED_BY, INVOKED_TOOL, MUTATED_SYSTEM, RESULTED_IN, VERIFIED_BY
    metadata: Dict[str, Any]
    created_at: float

class DataLineageGraph:
    """
    Authoritative Data Lineage and AI Decision Provenance Graph.
    Allows enterprise administrators and auditors to trace any action back to its root.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS lineage_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                label TEXT NOT NULL,
                attributes JSON NOT NULL,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lin_node_tenant ON lineage_nodes(tenant_id);")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS lineage_edges (
                edge_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                metadata JSON,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lin_edge_src ON lineage_edges(source_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lin_edge_tgt ON lineage_edges(target_id);")

    def record_step(
        self,
        tenant_id: str,
        company_id: str,
        source_id: str,
        source_type: str,
        source_label: str,
        target_id: str,
        target_type: str,
        target_label: str,
        relationship: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a causal step in the lineage graph."""
        now = time.time()
        edge_id = f"ln_edge_{uuid.uuid4().hex[:12]}"

        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            # Upsert source node
            conn.execute("""
            INSERT OR IGNORE INTO lineage_nodes (node_id, node_type, tenant_id, company_id, label, attributes, created_at)
            VALUES (?, ?, ?, ?, ?, '{}', ?)
            """, (source_id, source_type, tenant_id, company_id, source_label, now))

            # Upsert target node
            conn.execute("""
            INSERT OR IGNORE INTO lineage_nodes (node_id, node_type, tenant_id, company_id, label, attributes, created_at)
            VALUES (?, ?, ?, ?, ?, '{}', ?)
            """, (target_id, target_type, tenant_id, company_id, target_label, now))

            # Insert causal directed edge
            conn.execute("""
            INSERT INTO lineage_edges (edge_id, tenant_id, company_id, source_id, target_id, relationship, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (edge_id, tenant_id, company_id, source_id, target_id, relationship, json.dumps(metadata or {}), now))

    def get_provenance_trail(self, target_id: str) -> List[Dict[str, Any]]:
        """
        Backtrace all causal ancestors that led to the given outcome, action, or decision.
        """
        trail = []
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("""
            SELECT e.source_id, e.target_id, e.relationship, e.metadata, e.created_at,
                   s.node_type as source_type, s.label as source_label,
                   t.node_type as target_type, t.label as target_label
            FROM lineage_edges e
            JOIN lineage_nodes s ON e.source_id = s.node_id
            JOIN lineage_nodes t ON e.target_id = t.node_id
            WHERE e.target_id = ?
            ORDER BY e.created_at DESC
            """, (target_id,))
            rows = cursor.fetchall()
            for r in rows:
                trail.append({
                    "source_id": r["source_id"],
                    "source_type": r["source_type"],
                    "source_label": r["source_label"],
                    "relationship": r["relationship"],
                    "target_id": r["target_id"],
                    "target_type": r["target_type"],
                    "target_label": r["target_label"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                    "timestamp": r["created_at"]
                })
        return trail

# Global singleton
data_lineage_graph = DataLineageGraph()
