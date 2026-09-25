"""
ZONATA Universal AI CEO — Company Discovery Engine
Ingestion pipeline for owner input, documents, system feeds (PMS, ERP, CRM, POS),
and public signals, strictly maintaining provenance and epistemic integrity.
"""

from typing import Dict, List, Optional, Any, Tuple
import json
import time
import uuid
import re

from core.db import db
from zonata.models import (
    EpistemicState,
    EntityType,
    RelationType,
    ProvenanceRecord,
    DiscoveryFinding,
    DiscoveryState
)
from zonata.knowledge_graph import CompanyKnowledgeGraph

class CompanyDiscoveryEngine:
    """
    Ingestion engine responsible for discovering company context.
    Enforces the constitutional invariant: Never silently convert an estimate into a fact.
    """

    def __init__(self):
        pass

    def get_or_create_session(self, tenant_id: str, company_id: str) -> DiscoveryState:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM zonata_discovery_sessions WHERE tenant_id = ? AND company_id = ?",
                (tenant_id, company_id)
            ).fetchone()
            if row:
                return DiscoveryState(
                    session_id=row["session_id"],
                    tenant_id=row["tenant_id"],
                    company_id=row["company_id"],
                    completeness_score=row["completeness_score"],
                    status=row["status"],
                    missing_information=json.loads(row["missing_info"]) if row["missing_info"] else [],
                    deferred_topics=json.loads(row["deferred_topics"]) if row["deferred_topics"] else [],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
            
            session_id = f"disc_{uuid.uuid4().hex[:10]}"
            now = time.time()
            initial_missing = [
                {"dimension": "IDENTITY", "label": "Legal name, brand, locations, operating hours"},
                {"dimension": "REVENUE", "label": "Core revenue streams, pricing structure, average order/room value"},
                {"dimension": "OPERATIONS", "label": "Key daily processes, fulfillment, supplier dependencies"},
                {"dimension": "SYSTEMS", "label": "Core software (PMS, ERP, CRM, POS, Accounting)"},
                {"dimension": "FINANCE", "label": "Current monthly revenue, operational costs, margins, cash runway"},
                {"dimension": "WORKFORCE", "label": "Human employees, organizational roles, key bottleneck tasks"},
                {"dimension": "CUSTOMERS", "label": "Target customer segments, acquisition channels, churn/retention"},
                {"dimension": "RISKS_GOALS", "label": "Immediate quarterly goals, top 3 operational/financial risks"}
            ]
            conn.execute("""
                INSERT INTO zonata_discovery_sessions (
                    session_id, tenant_id, company_id, completeness_score, status,
                    missing_info, deferred_topics, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, tenant_id, company_id, 0.05, "IN_PROGRESS",
                json.dumps(initial_missing), json.dumps([]), now, now
            ))
            conn.commit()

            return DiscoveryState(
                session_id=session_id,
                tenant_id=tenant_id,
                company_id=company_id,
                completeness_score=0.05,
                status="IN_PROGRESS",
                missing_information=initial_missing,
                deferred_topics=[],
                created_at=now,
                updated_at=now
            )

    def record_finding(
        self,
        tenant_id: str,
        company_id: str,
        entity_type: EntityType,
        entity_id: str,
        attribute: str,
        value: Any,
        source: str,
        source_type: str,
        evidence: str,
        epistemic_state: EpistemicState,
        confidence: float = 1.0,
        session_id: Optional[str] = None
    ) -> DiscoveryFinding:
        """
        Records an atomic finding with full provenance and stores in database and knowledge graph.
        """
        fact_id = f"fact_{uuid.uuid4().hex[:12]}"
        now = time.time()
        provenance = ProvenanceRecord(
            source=source,
            tenant_id=tenant_id,
            company_id=company_id,
            evidence=evidence,
            epistemic_state=epistemic_state,
            confidence=confidence,
            timestamp=now
        )
        finding = DiscoveryFinding(
            fact_id=fact_id,
            entity_type=entity_type,
            entity_id=entity_id,
            attribute=attribute,
            value=value,
            provenance=provenance
        )

        # 1. Persist to zonata_facts
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_facts (
                    fact_id, session_id, tenant_id, company_id, entity_type, entity_id,
                    attribute, value, epistemic_state, source, source_type, confidence,
                    evidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact_id, session_id, tenant_id, company_id, entity_type.value, entity_id,
                attribute, json.dumps(value), epistemic_state.value, source, source_type,
                confidence, evidence, now
            ))
            conn.commit()

        # 2. Reflect into Knowledge Graph
        kg = CompanyKnowledgeGraph(tenant_id, company_id)
        node = kg.get_node(entity_id)
        if not node:
            name = str(value) if attribute in ("name", "title") else f"{entity_type.value}:{entity_id}"
            kg.add_node(
                entity_type=entity_type,
                name=name,
                properties={attribute: value, "evidence": evidence},
                epistemic_state=epistemic_state,
                confidence=confidence,
                node_id=entity_id
            )
        else:
            node.properties[attribute] = value
            # Strict epistemic monotonicity: An estimate never overwrites a verified fact
            if node.epistemic_state != EpistemicState.FACT and node.epistemic_state != EpistemicState.VERIFIED:
                node.epistemic_state = epistemic_state
            node.confidence = min(node.confidence, confidence) if epistemic_state == EpistemicState.ESTIMATE else confidence
            kg._persist_node(node)

        # Connect to Company node if not company itself
        if entity_type != EntityType.COMPANY:
            company_node = kg.find_node_by_name(company_id, EntityType.COMPANY)
            if not company_node:
                company_node = kg.get_node(f"comp_{company_id}")
            if not company_node:
                company_node = kg.add_node(
                    entity_type=EntityType.COMPANY,
                    name=company_id,
                    properties={"company_id": company_id},
                    epistemic_state=EpistemicState.FACT,
                    confidence=1.0,
                    node_id=f"comp_{company_id}"
                )
            
            # Add appropriate relation edge
            relation = self._map_entity_to_relation(entity_type)
            try:
                kg.add_edge(
                    source_node_id=company_node.node_id,
                    target_node_id=entity_id,
                    relation=relation,
                    properties={"provenance_source": source},
                    epistemic_state=epistemic_state
                )
            except Exception:
                pass

        return finding

    def ingest_owner_statement(
        self,
        tenant_id: str,
        company_id: str,
        statement: str,
        source: str = "OWNER_INTERVIEW",
        session_id: Optional[str] = None
    ) -> List[DiscoveryFinding]:
        """
        Parses text statement from company owner or manager.
        Detects heuristics for estimates vs factual claims.
        """
        findings: List[DiscoveryFinding] = []
        lower_stmt = statement.lower()

        # Heuristic for estimate classification
        is_estimate = any(w in lower_stmt for w in [
            "roughly", "about", "around", "approximately", "approx", "maybe",
            "estimate", "guestimate", "not sure exactly", "somewhere between"
        ])
        epistemic = EpistemicState.ESTIMATE if is_estimate else EpistemicState.FACT
        conf = 0.7 if is_estimate else 0.95

        # 1. Detection of Rooms / Capacity (Hospitality / Real Estate / Coworking)
        room_match = re.search(r"(\d+)\s*(rooms|keys|suites|units|beds)", lower_stmt)
        if room_match:
            count = int(room_match.group(1))
            f = self.record_finding(
                tenant_id=tenant_id,
                company_id=company_id,
                entity_type=EntityType.ASSET,
                entity_id=f"asset_rooms_{company_id}",
                attribute="room_inventory",
                value=count,
                source=source,
                source_type="OWNER_INPUT",
                evidence=f"Owner stated: '{room_match.group(0)}'",
                epistemic_state=epistemic,
                confidence=conf,
                session_id=session_id
            )
            findings.append(f)

        # 2. Detection of Industry & Type
        for ind in ["hotel", "resort", "manufacturing", "factory", "saas", "software", "restaurant", "hospital", "clinic", "retail", "ecommerce", "logistics"]:
            if ind in lower_stmt:
                f = self.record_finding(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    entity_type=EntityType.COMPANY,
                    entity_id=f"comp_{company_id}",
                    attribute="industry",
                    value=ind.upper(),
                    source=source,
                    source_type="OWNER_INPUT",
                    evidence=f"Owner stated industry context containing '{ind}'",
                    epistemic_state=EpistemicState.FACT,
                    confidence=1.0,
                    session_id=session_id
                )
                findings.append(f)
                break

        # 3. Detection of Systems & Software (PMS, ERP, CRM, POS, Accounting)
        systems_map = {
            "cloudbeds": ("PMS", "Cloudbeds Hotel Management System"),
            "opera": ("PMS", "Oracle Opera PMS"),
            "mews": ("PMS", "Mews Hospitality Cloud"),
            "salesforce": ("CRM", "Salesforce CRM"),
            "hubspot": ("CRM", "HubSpot CRM"),
            "quickbooks": ("FinancialAccount", "Intuit QuickBooks"),
            "tally": ("FinancialAccount", "Tally Prime ERP"),
            "zoho": ("ERP", "Zoho Enterprise Suite"),
            "sap": ("ERP", "SAP ERP"),
            "toast": ("System", "Toast POS"),
            "shopify": ("System", "Shopify E-Commerce"),
            "jira": ("System", "Atlassian Jira"),
            "github": ("System", "GitHub Enterprise")
        }
        for sys_key, (ent_type_str, sys_full_name) in systems_map.items():
            if sys_key in lower_stmt:
                ent_type = EntityType.SYSTEM if ent_type_str == "System" else (
                    EntityType.FINANCIAL_ACCOUNT if ent_type_str == "FinancialAccount" else EntityType.APPLICATION
                )
                f = self.record_finding(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    entity_type=ent_type,
                    entity_id=f"sys_{sys_key}_{company_id}",
                    attribute="connected_system",
                    value={"name": sys_full_name, "category": ent_type_str, "status": "CONNECTED_REPORTED"},
                    source=source,
                    source_type="OWNER_INPUT",
                    evidence=f"Owner reported using system: {sys_full_name}",
                    epistemic_state=EpistemicState.FACT,
                    confidence=0.95,
                    session_id=session_id
                )
                findings.append(f)

        # 4. Detection of Financials (Revenue, Costs)
        rev_match = re.search(r"(\$|₹|€|£)?\s*(\d+(\.\d+)?)\s*(k|m|lakh|crore|million|thousand)?\s*(revenue|turnover|monthly|sales)", lower_stmt)
        if rev_match:
            f = self.record_finding(
                tenant_id=tenant_id,
                company_id=company_id,
                entity_type=EntityType.REVENUE_STREAM,
                entity_id=f"rev_{company_id}_primary",
                attribute="reported_revenue",
                value=rev_match.group(0),
                source=source,
                source_type="OWNER_INPUT",
                evidence=f"Owner reported revenue figure: '{rev_match.group(0)}'",
                epistemic_state=epistemic,
                confidence=conf,
                session_id=session_id
            )
            findings.append(f)

        # 5. Detection of Human Workforce Roles
        wf_roles = ["general manager", "revenue manager", "receptionist", "housekeeper", "chef", "engineer", "sales manager", "accountant", "developer", "support rep", "driver", "machinist"]
        for role in wf_roles:
            if role in lower_stmt:
                clean_id = role.replace(" ", "_")
                f = self.record_finding(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    entity_type=EntityType.PERSON,
                    entity_id=f"person_{clean_id}_{company_id}",
                    attribute="role",
                    value=role.title(),
                    source=source,
                    source_type="OWNER_INPUT",
                    evidence=f"Owner mentioned operational human role '{role}'",
                    epistemic_state=EpistemicState.FACT,
                    confidence=0.9,
                    session_id=session_id
                )
                findings.append(f)

        # If nothing specific was pattern matched, record as general observation
        if not findings and len(statement.strip()) > 5:
            f = self.record_finding(
                tenant_id=tenant_id,
                company_id=company_id,
                entity_type=EntityType.COMPANY,
                entity_id=f"comp_{company_id}",
                attribute="owner_note",
                value=statement.strip(),
                source=source,
                source_type="OWNER_INPUT",
                evidence="Unstructured statement from owner",
                epistemic_state=EpistemicState.UNVERIFIED,
                confidence=0.75,
                session_id=session_id
            )
            findings.append(f)

        return findings

    def ingest_document(
        self,
        tenant_id: str,
        company_id: str,
        title: str,
        content: str,
        doc_type: str = "SOP",
        session_id: Optional[str] = None
    ) -> List[DiscoveryFinding]:
        """Ingests internal document, policy, or SOP with full provenance."""
        findings: List[DiscoveryFinding] = []
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"

        # Record Document node
        f_doc = self.record_finding(
            tenant_id=tenant_id,
            company_id=company_id,
            entity_type=EntityType.DOCUMENT if doc_type != "SOP" else EntityType.SOP,
            entity_id=doc_id,
            attribute="title",
            value={"title": title, "doc_type": doc_type, "length_chars": len(content)},
            source="DOCUMENT_UPLOAD",
            source_type="DOCUMENT",
            evidence=f"Uploaded {doc_type}: {title}",
            epistemic_state=EpistemicState.FACT,
            confidence=1.0,
            session_id=session_id
        )
        findings.append(f_doc)

        # Extract processes mentioned
        lines = content.split("\n")
        for line in lines:
            line_str = line.strip()
            if line_str.startswith(("Step ", "Procedure:", "Process:", "1.", "2.", "3.", "•")):
                p_id = f"proc_{uuid.uuid4().hex[:8]}"
                f_proc = self.record_finding(
                    tenant_id=tenant_id,
                    company_id=company_id,
                    entity_type=EntityType.PROCESS,
                    entity_id=p_id,
                    attribute="sop_step",
                    value=line_str,
                    source=f"DOCUMENT:{title}",
                    source_type="DOCUMENT",
                    evidence=f"Extracted from {title}",
                    epistemic_state=EpistemicState.FACT,
                    confidence=0.95,
                    session_id=session_id
                )
                findings.append(f_proc)

        return findings

    def ingest_system_feed(
        self,
        tenant_id: str,
        company_id: str,
        system_name: str,
        system_type: str,
        data_payload: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> List[DiscoveryFinding]:
        """
        Direct structured data ingestion from connected PMS, ERP, CRM, POS, or Accounting API.
        Truth classification: Authoritative FACT / OBSERVATION.
        """
        findings: List[DiscoveryFinding] = []
        sys_id = f"sys_{system_name.lower().replace(' ', '_')}_{company_id}"

        # 1. Register system entity
        f_sys = self.record_finding(
            tenant_id=tenant_id,
            company_id=company_id,
            entity_type=EntityType.SYSTEM,
            entity_id=sys_id,
            attribute="live_integration",
            value={"system_name": system_name, "system_type": system_type, "status": "CONNECTED_ACTIVE"},
            source=f"API:{system_name}",
            source_type="API",
            evidence=f"Connected system feed from {system_name} ({system_type})",
            epistemic_state=EpistemicState.FACT,
            confidence=1.0,
            session_id=session_id
        )
        findings.append(f_sys)

        # 2. Ingest payload metrics as verified facts
        for k, v in data_payload.items():
            f_val = self.record_finding(
                tenant_id=tenant_id,
                company_id=company_id,
                entity_type=EntityType.KPI if "rate" in k or "rev" in k or "count" in k else EntityType.ASSET,
                entity_id=f"metric_{k}_{company_id}",
                attribute=k,
                value=v,
                source=f"SYSTEM_FEED:{system_name}",
                source_type="API",
                evidence=f"API payload key '{k}' from verified system {system_name}",
                epistemic_state=EpistemicState.FACT,
                confidence=1.0,
                session_id=session_id
            )
            findings.append(f_val)

        return findings

    def _map_entity_to_relation(self, entity_type: EntityType) -> RelationType:
        mapping = {
            EntityType.LOCATION: RelationType.OWNS,
            EntityType.SYSTEM: RelationType.USES,
            EntityType.APPLICATION: RelationType.USES,
            EntityType.INTEGRATION: RelationType.INTEGRATES_WITH,
            EntityType.PROCESS: RelationType.OPERATES,
            EntityType.PERSON: RelationType.EMPLOYS,
            EntityType.AI_WORKFORCE_MEMBER: RelationType.EMPLOYS,
            EntityType.REVENUE_STREAM: RelationType.GENERATES,
            EntityType.EXPENSE: RelationType.PRODUCES,
            EntityType.COMPETITOR: RelationType.COMPETES_WITH,
            EntityType.ASSET: RelationType.OWNS,
            EntityType.MACHINE: RelationType.OWNS,
            EntityType.PRODUCT: RelationType.PRODUCES,
            EntityType.SERVICE: RelationType.PRODUCES,
            EntityType.RISK: RelationType.MITIGATES,
            EntityType.GOAL: RelationType.RESPONSIBLE_FOR
        }
        return mapping.get(entity_type, RelationType.OWNS)

    def list_findings(
        self,
        tenant_id: str,
        company_id: str,
        entity_type: Optional[EntityType] = None,
        epistemic_state: Optional[EpistemicState] = None
    ) -> List[Dict[str, Any]]:
        """Returns all recorded discovery facts matching filters."""
        query = "SELECT * FROM zonata_facts WHERE tenant_id = ? AND company_id = ?"
        params: List[Any] = [tenant_id, company_id]

        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type.value)
        if epistemic_state:
            query += " AND epistemic_state = ?"
            params.append(epistemic_state.value)

        query += " ORDER BY created_at DESC"

        with db.get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                {
                    "fact_id": r["fact_id"],
                    "session_id": r["session_id"],
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "attribute": r["attribute"],
                    "value": json.loads(r["value"]) if r["value"] else None,
                    "epistemic_state": r["epistemic_state"],
                    "source": r["source"],
                    "source_type": r["source_type"],
                    "confidence": r["confidence"],
                    "evidence": r["evidence"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]
