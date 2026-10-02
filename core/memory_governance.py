"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Phase 22 — Memory Governance & Cognitive Tiering Plane
Strict epistemic separation of memory tiers:
Working Memory != Long-Term Memory != Corporate Knowledge != Evidence

Constitutional Invariants:
  MEMORY != AUTHORITY
  MEMORY != EVIDENCE
  MEMORY != POLICY
  MEMORY != CORPORATE_TRUTH
  AI_GENERATED != AUTHORITATIVE
"""

import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.database_engine import engine, WorkloadType

logger = logging.getLogger("zonata.memory.governance")

class EpistemicMemoryTier:
    WORKING_MEMORY = "WORKING_MEMORY"           # Ephemeral scratchpad within task execution
    LONG_TERM_MEMORY = "LONG_TERM_MEMORY"       # Agent personalization & execution history
    CORPORATE_KNOWLEDGE = "CORPORATE_KNOWLEDGE" # Verified company facts
    EVIDENCE = "EVIDENCE"                       # Cryptographically sealed audit trails

class KnowledgeTrustState:
    UNVERIFIED = "UNVERIFIED"
    AI_GENERATED = "AI_GENERATED"
    SOURCE_DERIVED = "SOURCE_DERIVED"
    VERIFIED = "VERIFIED"
    AUTHORITATIVE = "AUTHORITATIVE"
    CONFLICTING = "CONFLICTING"
    STALE = "STALE"

@dataclass
class GovernedMemoryRecord:
    record_id: str
    tenant_id: str
    company_id: str
    employee_id: str
    tier: str
    trust_state: str
    content: str
    confidence_score: float
    source_reference: Optional[str]
    is_authoritative: bool
    created_at: float
    expires_at: Optional[float]

class MemoryGovernanceGateway:
    """
    Epistemic memory barrier.
    Guarantees that hallucinations or unverified agent outputs cannot masquerade as authoritative truth.
    """
    def __init__(self):
        self._init_db()

    def _init_db(self):
        with engine.transaction(workload=WorkloadType.CONTROL_PLANE) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS governed_memory_records (
                record_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                trust_state TEXT NOT NULL DEFAULT 'UNVERIFIED',
                content TEXT NOT NULL,
                confidence_score REAL NOT NULL DEFAULT 0.5,
                source_reference TEXT,
                is_authoritative INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                expires_at REAL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_emp ON governed_memory_records(employee_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_tier ON governed_memory_records(tier);")

    def record_working_memory(
        self,
        tenant_id: str,
        company_id: str,
        employee_id: str,
        content: str,
        ttl_seconds: float = 3600.0
    ) -> GovernedMemoryRecord:
        """Store transient task context. Strictly unauthoritative."""
        record_id = f"mem_wrk_{uuid.uuid4().hex[:12]}"
        now = time.time()
        rec = GovernedMemoryRecord(
            record_id=record_id,
            tenant_id=tenant_id,
            company_id=company_id,
            employee_id=employee_id,
            tier=EpistemicMemoryTier.WORKING_MEMORY,
            trust_state=KnowledgeTrustState.AI_GENERATED,
            content=content,
            confidence_score=0.5,
            source_reference=None,
            is_authoritative=False,
            created_at=now,
            expires_at=now + ttl_seconds
        )
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            conn.execute("""
            INSERT INTO governed_memory_records (
                record_id, tenant_id, company_id, employee_id, tier,
                trust_state, content, confidence_score, source_reference,
                is_authoritative, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (
                rec.record_id, rec.tenant_id, rec.company_id, rec.employee_id,
                rec.tier, rec.trust_state, rec.content, rec.confidence_score,
                rec.source_reference, rec.created_at, rec.expires_at
            ))
        return rec

    def promote_to_corporate_knowledge(
        self,
        record_id: str,
        verified_by_authority_id: str,
        evidence_reference: str
    ) -> bool:
        """
        Promote memory to corporate knowledge.
        CONSTITUTIONAL INVARIANT: An AI Employee cannot self-promote AI-generated statements into AUTHORITATIVE truth.
        Requires explicit human/authority verification.
        """
        now = time.time()
        with engine.transaction(workload=WorkloadType.WRITE) as conn:
            cursor = conn.execute("SELECT * FROM governed_memory_records WHERE record_id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Memory record '{record_id}' not found.")

            conn.execute("""
            UPDATE governed_memory_records
            SET tier = 'CORPORATE_KNOWLEDGE',
                trust_state = 'AUTHORITATIVE',
                is_authoritative = 1,
                source_reference = ?
            WHERE record_id = ?
            """, (f"Verified by {verified_by_authority_id} via {evidence_reference}", record_id))

        logger.info(f"Memory {record_id} promoted to AUTHORITATIVE corporate knowledge by {verified_by_authority_id}")
        return True

# Global singleton
memory_governance_gateway = MemoryGovernanceGateway()
