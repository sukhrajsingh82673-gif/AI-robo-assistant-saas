"""
ZONATA Universal AI CEO — Company Knowledge Graph
Persistent, provenance-tracked, multi-entity graph linking companies, subsidiaries,
locations, processes, systems, workforce, financial streams, risks, and goals.
"""

from typing import Dict, List, Optional, Any, Set, Tuple
import json
import time
import uuid

from core.db import db
from zonata.models import EntityType, RelationType, EpistemicState

class KnowledgeNode:
    def __init__(
        self,
        node_id: str,
        entity_type: EntityType,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        epistemic_state: EpistemicState = EpistemicState.FACT,
        confidence: float = 1.0,
        tenant_id: str = "default_tenant",
        company_id: str = "default_company",
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None
    ):
        self.node_id = node_id
        self.entity_type = entity_type if isinstance(entity_type, EntityType) else EntityType(entity_type)
        self.name = name
        self.properties = properties or {}
        self.epistemic_state = epistemic_state if isinstance(epistemic_state, EpistemicState) else EpistemicState(epistemic_state)
        self.confidence = confidence
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "properties": self.properties,
            "epistemic_state": self.epistemic_state.value,
            "confidence": self.confidence,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class KnowledgeEdge:
    def __init__(
        self,
        edge_id: str,
        source_node_id: str,
        target_node_id: str,
        relation: RelationType,
        properties: Optional[Dict[str, Any]] = None,
        epistemic_state: EpistemicState = EpistemicState.FACT,
        tenant_id: str = "default_tenant",
        company_id: str = "default_company",
        created_at: Optional[float] = None
    ):
        self.edge_id = edge_id
        self.source_node_id = source_node_id
        self.target_node_id = target_node_id
        self.relation = relation if isinstance(relation, RelationType) else RelationType(relation)
        self.properties = properties or {}
        self.epistemic_state = epistemic_state if isinstance(epistemic_state, EpistemicState) else EpistemicState(epistemic_state)
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.created_at = created_at or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relation": self.relation.value,
            "properties": self.properties,
            "epistemic_state": self.epistemic_state.value,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "created_at": self.created_at
        }

class CompanyKnowledgeGraph:
    """
    In-memory and SQLite-backed Knowledge Graph for a specific company.
    Enforces epistemic truth tracking and multi-hop relationship discovery.
    """

    def __init__(self, tenant_id: str, company_id: str):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: Dict[str, KnowledgeEdge] = {}
        # Adjacency indexes for fast lookups
        self._outgoing: Dict[str, List[str]] = {} # source_node_id -> [edge_id]
        self._incoming: Dict[str, List[str]] = {} # target_node_id -> [edge_id]
        self._type_index: Dict[str, Set[str]] = {} # entity_type -> {node_id}
        self.load_from_db()

    def add_node(
        self,
        entity_type: EntityType,
        name: str,
        properties: Optional[Dict[str, Any]] = None,
        epistemic_state: EpistemicState = EpistemicState.FACT,
        confidence: float = 1.0,
        node_id: Optional[str] = None
    ) -> KnowledgeNode:
        """Adds or updates a node in the graph."""
        nid = node_id or f"node_{uuid.uuid4().hex[:12]}"
        node = KnowledgeNode(
            node_id=nid,
            entity_type=entity_type,
            name=name,
            properties=properties or {},
            epistemic_state=epistemic_state,
            confidence=confidence,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            updated_at=time.time()
        )
        self.nodes[nid] = node

        # Update type index
        type_key = node.entity_type.value
        if type_key not in self._type_index:
            self._type_index[type_key] = set()
        self._type_index[type_key].add(nid)

        # Persist to DB
        self._persist_node(node)
        return node

    def add_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relation: RelationType,
        properties: Optional[Dict[str, Any]] = None,
        epistemic_state: EpistemicState = EpistemicState.FACT,
        edge_id: Optional[str] = None
    ) -> KnowledgeEdge:
        """Adds a directed relation between two existing nodes."""
        if source_node_id not in self.nodes:
            raise ValueError(f"Source node {source_node_id} does not exist in graph")
        if target_node_id not in self.nodes:
            raise ValueError(f"Target node {target_node_id} does not exist in graph")

        eid = edge_id or f"edge_{uuid.uuid4().hex[:12]}"
        edge = KnowledgeEdge(
            edge_id=eid,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation=relation,
            properties=properties or {},
            epistemic_state=epistemic_state,
            tenant_id=self.tenant_id,
            company_id=self.company_id
        )
        self.edges[eid] = edge

        # Update adjacency
        if source_node_id not in self._outgoing:
            self._outgoing[source_node_id] = []
        self._outgoing[source_node_id].append(eid)

        if target_node_id not in self._incoming:
            self._incoming[target_node_id] = []
        self._incoming[target_node_id].append(eid)

        self._persist_edge(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self.nodes.get(node_id)

    def find_nodes_by_type(self, entity_type: EntityType) -> List[KnowledgeNode]:
        type_key = entity_type.value if isinstance(entity_type, EntityType) else str(entity_type)
        node_ids = self._type_index.get(type_key, set())
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def find_node_by_name(self, name: str, entity_type: Optional[EntityType] = None) -> Optional[KnowledgeNode]:
        for node in self.nodes.values():
            if node.name.lower() == name.lower():
                if entity_type is None or node.entity_type == entity_type:
                    return node
        return None

    def get_related_nodes(
        self,
        node_id: str,
        relation: Optional[RelationType] = None,
        direction: str = "outgoing"
    ) -> List[Tuple[KnowledgeEdge, KnowledgeNode]]:
        """Finds all related nodes and the corresponding edge."""
        results = []
        if direction in ("outgoing", "both"):
            for eid in self._outgoing.get(node_id, []):
                edge = self.edges.get(eid)
                if edge and (relation is None or edge.relation == relation):
                    target = self.nodes.get(edge.target_node_id)
                    if target:
                        results.append((edge, target))

        if direction in ("incoming", "both"):
            for eid in self._incoming.get(node_id, []):
                edge = self.edges.get(eid)
                if edge and (relation is None or edge.relation == relation):
                    source = self.nodes.get(edge.source_node_id)
                    if source:
                        results.append((edge, source))

        return results

    def query_by_epistemic_state(self, states: List[EpistemicState]) -> List[KnowledgeNode]:
        """Finds nodes that match specific truth classifications."""
        return [node for node in self.nodes.values() if node.epistemic_state in states]

    def get_unverified_entities(self) -> List[KnowledgeNode]:
        """Returns all nodes requiring verification (UNVERIFIED, ESTIMATE, PREDICTION)."""
        return self.query_by_epistemic_state([
            EpistemicState.UNVERIFIED,
            EpistemicState.ESTIMATE,
            EpistemicState.PREDICTION
        ])

    def export_summary(self) -> Dict[str, Any]:
        """Exports high-level metrics and statistics of the knowledge graph."""
        type_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            k = node.entity_type.value
            type_counts[k] = type_counts.get(k, 0) + 1

        state_counts: Dict[str, int] = {}
        for node in self.nodes.values():
            s = node.epistemic_state.value
            state_counts[s] = state_counts.get(s, 0) + 1

        return {
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "entity_counts": type_counts,
            "epistemic_distribution": state_counts
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()]
        }

    # --- Persistence Helpers ---

    def _persist_node(self, node: KnowledgeNode):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_kg_nodes (
                    node_id, tenant_id, company_id, entity_type, name, properties,
                    epistemic_state, confidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    name=excluded.name,
                    properties=excluded.properties,
                    epistemic_state=excluded.epistemic_state,
                    confidence=excluded.confidence,
                    updated_at=excluded.updated_at
            """, (
                node.node_id, node.tenant_id, node.company_id, node.entity_type.value,
                node.name, json.dumps(node.properties), node.epistemic_state.value,
                node.confidence, node.created_at, node.updated_at
            ))
            conn.commit()

    def _persist_edge(self, edge: KnowledgeEdge):
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_kg_edges (
                    edge_id, tenant_id, company_id, source_node_id, target_node_id,
                    relation, properties, epistemic_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(edge_id) DO UPDATE SET
                    relation=excluded.relation,
                    properties=excluded.properties,
                    epistemic_state=excluded.epistemic_state
            """, (
                edge.edge_id, edge.tenant_id, edge.company_id, edge.source_node_id,
                edge.target_node_id, edge.relation.value, json.dumps(edge.properties),
                edge.epistemic_state.value, edge.created_at
            ))
            conn.commit()

    def load_from_db(self):
        """Loads all nodes and edges for this tenant and company from SQLite."""
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM zonata_kg_nodes WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id)
            ).fetchall()
            for r in rows:
                props = json.loads(r["properties"]) if r["properties"] else {}
                node = KnowledgeNode(
                    node_id=r["node_id"],
                    entity_type=EntityType(r["entity_type"]),
                    name=r["name"],
                    properties=props,
                    epistemic_state=EpistemicState(r["epistemic_state"]),
                    confidence=r["confidence"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                )
                self.nodes[node.node_id] = node
                tkey = node.entity_type.value
                if tkey not in self._type_index:
                    self._type_index[tkey] = set()
                self._type_index[tkey].add(node.node_id)

            edge_rows = conn.execute(
                "SELECT * FROM zonata_kg_edges WHERE tenant_id = ? AND company_id = ?",
                (self.tenant_id, self.company_id)
            ).fetchall()
            for er in edge_rows:
                eprops = json.loads(er["properties"]) if er["properties"] else {}
                edge = KnowledgeEdge(
                    edge_id=er["edge_id"],
                    source_node_id=er["source_node_id"],
                    target_node_id=er["target_node_id"],
                    relation=RelationType(er["relation"]),
                    properties=eprops,
                    epistemic_state=EpistemicState(er["epistemic_state"]),
                    tenant_id=er["tenant_id"],
                    company_id=er["company_id"],
                    created_at=er["created_at"]
                )
                self.edges[edge.edge_id] = edge
                if edge.source_node_id not in self._outgoing:
                    self._outgoing[edge.source_node_id] = []
                self._outgoing[edge.source_node_id].append(edge.edge_id)
                if edge.target_node_id not in self._incoming:
                    self._incoming[edge.target_node_id] = []
                self._incoming[edge.target_node_id].append(edge.edge_id)
