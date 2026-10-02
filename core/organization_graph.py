"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 2 — Enterprise Organization Model & Workforce Graph
Defines the enterprise structural hierarchy:
Tenant -> Company -> Business Unit -> Department -> Team -> Employee (Human/AI) -> Mission -> Task -> Action

Constitutional Invariant:
  ORGANIZATIONAL_MEMBERSHIP != AUTHORIZATION
  (Belonging to a department or team does not confer automatic execution or data access authority)
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, asdict
from core.database_engine import engine, WorkloadType

logger = logging.getLogger("zonata.org.graph")

class OrgNodeType:
    TENANT = "TENANT"
    COMPANY = "COMPANY"
    BUSINESS_UNIT = "BUSINESS_UNIT"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    EMPLOYEE_HUMAN = "EMPLOYEE_HUMAN"
    EMPLOYEE_AI = "EMPLOYEE_AI"
    MISSION = "MISSION"
    TASK = "TASK"
    ACTION = "ACTION"

@dataclass
class OrgNode:
    node_id: str
    node_type: str
    tenant_id: str
    company_id: str
    name: str
    parent_id: Optional[str]
    metadata: Dict[str, Any]

class OrganizationGraph:
    """
    Authoritative Enterprise Organizational Hierarchy & Workforce Graph.
    Tracks reporting structures, departments, cross-functional teams, and business units.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS organization_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                parent_id TEXT,
                metadata JSON,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_org_tenant_comp ON organization_nodes(tenant_id, company_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_org_parent ON organization_nodes(parent_id);")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS organization_edges (
                edge_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL, -- REPORTS_TO, MEMBER_OF, MANAGES, SHARED_SERVICE_WITH
                metadata JSON,
                created_at REAL NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_org_edge_src ON organization_edges(source_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_org_edge_tgt ON organization_edges(target_id);")

    def add_node(
        self,
        node_id: str,
        node_type: str,
        tenant_id: str,
        company_id: str,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OrgNode:
        now = time.time()
        node = OrgNode(
            node_id=node_id,
            node_type=node_type,
            tenant_id=tenant_id,
            company_id=company_id,
            name=name,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO organization_nodes (
                node_id, node_type, tenant_id, company_id, name, parent_id, metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.node_id, node.node_type, node.tenant_id, node.company_id,
                node.name, node.parent_id, json.dumps(node.metadata), now, now
            ))
        return node

    def add_relation(
        self,
        tenant_id: str,
        company_id: str,
        source_id: str,
        target_id: str,
        relation_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        edge_id = f"edge_{source_id}_{relation_type}_{target_id}"
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT OR REPLACE INTO organization_edges (
                edge_id, tenant_id, company_id, source_id, target_id, relation_type, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (edge_id, tenant_id, company_id, source_id, target_id, relation_type, json.dumps(metadata or {}), now))
        return edge_id

    def get_node(self, node_id: str) -> Optional[OrgNode]:
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM organization_nodes WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return OrgNode(
                node_id=row["node_id"],
                node_type=row["node_type"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                name=row["name"],
                parent_id=row["parent_id"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

    def get_department_hierarchy(self, tenant_id: str, company_id: str) -> List[Dict[str, Any]]:
        """Retrieve full tree of business units, departments, and teams."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("""
            SELECT node_id, node_type, name, parent_id, metadata
            FROM organization_nodes
            WHERE tenant_id = ? AND company_id = ?
            ORDER BY created_at ASC
            """, (tenant_id, company_id))
            rows = cursor.fetchall()
            return [
                {
                    "node_id": r["node_id"],
                    "node_type": r["node_type"],
                    "name": r["name"],
                    "parent_id": r["parent_id"],
                    "metadata": json.loads(r["metadata"]) if r["metadata"] else {}
                }
                for r in rows
            ]

    def get_members(self, parent_id: str) -> List[OrgNode]:
        """Fetch all direct child employees or sub-units under a department or team."""
        with engine.connection(workload=WorkloadType.READ) as conn:
            cursor = conn.execute("SELECT * FROM organization_nodes WHERE parent_id = ?", (parent_id,))
            rows = cursor.fetchall()
            return [
                OrgNode(
                    node_id=r["node_id"],
                    node_type=r["node_type"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    name=r["name"],
                    parent_id=r["parent_id"],
                    metadata=json.loads(r["metadata"]) if r["metadata"] else {}
                )
                for r in rows
            ]

    def is_ancestor_of(self, potential_ancestor_id: str, target_node_id: str) -> bool:
        """Walk up the hierarchy tree to determine if node is an ancestor of target."""
        curr = self.get_node(target_node_id)
        visited = set()
        while curr and curr.parent_id:
            if curr.parent_id in visited:
                break  # Cycle protection
            visited.add(curr.parent_id)
            if curr.parent_id == potential_ancestor_id:
                return True
            curr = self.get_node(curr.parent_id)
        return False

# Global instance
organization_graph = OrganizationGraph()
