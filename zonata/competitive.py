"""
ZONATA Universal AI CEO — Competitive Intelligence Engine
Ethical, legal, and public-data competitive monitoring.
Constitutional Invariant: Strictly respects legal boundaries: no unauthorized system access,
no credential bypass, purely public data and owner-provided competitive benchmarks.
"""

from typing import Dict, List, Optional, Any
import json
import time
import uuid

from core.db import db
from zonata.models import (
    CompetitorProfile,
    EntityType,
    RelationType,
    EpistemicState
)
from zonata.knowledge_graph import CompanyKnowledgeGraph

class CompetitiveIntelligenceEngine:
    """
    Monitors competitive landscape using authorized public signals and owner benchmarks.
    """

    def __init__(self):
        pass

    def register_competitor(
        self,
        tenant_id: str,
        company_id: str,
        name: str,
        website: Optional[str] = None,
        products: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        public_pricing: Optional[Dict[str, Any]] = None,
        positioning: Optional[str] = None,
        customer_sentiment: Optional[str] = None,
        source: str = "OWNER_DISCOVERY",
        confidence: float = 0.9
    ) -> CompetitorProfile:
        """
        Registers a competitor profile with verified provenance.
        Connects competitor to Company in Knowledge Graph via 'competes_with' relation.
        """
        comp_id = f"comp_{uuid.uuid4().hex[:10]}"
        now = time.time()
        profile = CompetitorProfile(
            competitor_id=comp_id,
            tenant_id=tenant_id,
            company_id=company_id,
            name=name,
            website=website,
            products=products or [],
            services=services or [],
            public_pricing=public_pricing or {},
            positioning=positioning,
            customer_sentiment=customer_sentiment,
            source=source,
            confidence=confidence,
            discovered_at=now
        )

        # 1. Store in SQLite
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_competitor_profiles (
                    competitor_id, tenant_id, company_id, name, website, products,
                    services, public_pricing, positioning, customer_sentiment, source,
                    confidence, discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comp_id, tenant_id, company_id, name, website,
                json.dumps(profile.products), json.dumps(profile.services),
                json.dumps(profile.public_pricing), positioning, customer_sentiment,
                source, confidence, now
            ))
            conn.commit()

        # 2. Reflect in Company Knowledge Graph
        kg = CompanyKnowledgeGraph(tenant_id, company_id)
        comp_node = kg.add_node(
            entity_type=EntityType.COMPETITOR,
            name=name,
            properties={
                "website": website,
                "products": profile.products,
                "public_pricing": profile.public_pricing,
                "positioning": positioning,
                "source": source
            },
            epistemic_state=EpistemicState.OBSERVATION,
            confidence=confidence,
            node_id=comp_id
        )

        # Connect to company node
        company_node = kg.find_node_by_name(company_id, EntityType.COMPANY)
        if company_node:
            try:
                kg.add_edge(
                    source_node_id=company_node.node_id,
                    target_node_id=comp_node.node_id,
                    relation=RelationType.COMPETES_WITH,
                    properties={"discovered_at": now},
                    epistemic_state=EpistemicState.FACT
                )
            except Exception:
                pass

        return profile

    def list_competitors(self, tenant_id: str, company_id: str) -> List[CompetitorProfile]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM zonata_competitor_profiles WHERE tenant_id = ? AND company_id = ? ORDER BY discovered_at DESC",
                (tenant_id, company_id)
            ).fetchall()
            return [
                CompetitorProfile(
                    competitor_id=r["competitor_id"],
                    tenant_id=r["tenant_id"],
                    company_id=r["company_id"],
                    name=r["name"],
                    website=r["website"],
                    products=json.loads(r["products"]) if r["products"] else [],
                    services=json.loads(r["services"]) if r["services"] else [],
                    public_pricing=json.loads(r["public_pricing"]) if r["public_pricing"] else {},
                    positioning=r["positioning"],
                    customer_sentiment=r["customer_sentiment"],
                    source=r["source"],
                    confidence=r["confidence"],
                    discovered_at=r["discovered_at"]
                )
                for r in rows
            ]

    def analyze_competitive_opportunities(self, tenant_id: str, company_id: str) -> Dict[str, Any]:
        """
        Analyzes known competitors against company offerings to find market opportunities.
        """
        competitors = self.list_competitors(tenant_id, company_id)
        if not competitors:
            return {
                "competitor_count": 0,
                "pricing_insights": "No competitors monitored yet.",
                "differentiators": ["Market differentiation requires competitor discovery."],
                "strategic_recommendations": ["Conduct initial public competitor scan or provide primary competitor names."]
            }

        pricing_notes = []
        for c in competitors:
            if c.public_pricing:
                pricing_notes.append(f"{c.name}: {c.public_pricing}")

        return {
            "competitor_count": len(competitors),
            "tracked_competitors": [c.name for c in competitors],
            "pricing_insights": pricing_notes or ["Public pricing benchmarks recorded from public web presence."],
            "differentiators": [f"Direct positioning comparison against {competitors[0].name}"],
            "strategic_recommendations": [
                "Deploy proactive dynamic pricing agent to maintain occupancy/win rate vs competitors",
                "Highlight direct booking incentives to avoid competitor OTA aggregator bidding"
            ]
        }
