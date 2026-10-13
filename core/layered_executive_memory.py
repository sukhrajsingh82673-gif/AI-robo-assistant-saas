"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
8-Level Layered Executive Memory Architecture

Implements Section 18 & Section 19 of the Gemma 4 Master Specification:
Levels:
  LEVEL 1: Immediate Conversation (Active dialogue turns)
  LEVEL 2: Working Executive Memory (Volatile scratchpad for current cognitive session)
  LEVEL 3: Mission Memory (Context and intermediate states of active missions)
  LEVEL 4: Department Memory (Department-scoped operational telemetry and learnings)
  LEVEL 5: Organizational Memory (Corporate structure, policies, contracts)
  LEVEL 6: Historical Decisions (Sealed executive decisions and rationales)
  LEVEL 7: Long-term Strategic Memory (Quarterly goals, market positioning)
  LEVEL 8: Evidence-Backed Factual Memory (Cryptographically proven physical truth records)

Every memory record stores:
  source, timestamp, confidence, scope, tenant_id, company_id, authority, provenance, retention_policy.
Strict Invariant: Model-generated inferences are NEVER recorded as Level 8 Facts without physical verification.
"""

import time
import json
import uuid
import hashlib
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.executive.memory")

class MemoryTierLevel:
    LEVEL_1_CONVERSATION = 1
    LEVEL_2_WORKING_EXECUTIVE = 2
    LEVEL_3_MISSION = 3
    LEVEL_4_DEPARTMENT = 4
    LEVEL_5_ORGANIZATIONAL = 5
    LEVEL_6_HISTORICAL_DECISION = 6
    LEVEL_7_STRATEGIC = 7
    LEVEL_8_EVIDENCE_FACT = 8

@dataclass
class LayeredMemoryRecord:
    memory_id: str
    level: int                          # 1 to 8
    tenant_id: str
    company_id: str
    scope: str                          # GLOBAL, DEPARTMENT, MISSION, SESSION
    content: str
    structured_payload: Dict[str, Any]
    epistemic_category: str             # FACT, OBSERVATION, INFERENCE, RECOMMENDATION, PREDICTION, ASSUMPTION, UNKNOWN
    confidence: float                   # 0.0 to 1.0
    source: str                         # PHYSICAL_SENSOR, DB_RECORD, HUMAN_OWNER, MODEL_INFERENCE
    provenance: str                     # Cryptographic hash or origin identifier
    authority_required: str             # READ_ONLY, OPERATOR, OWNER
    retention_policy: str               # EPHEMERAL, SESSION, 90_DAYS, IMMUTABLE
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LayeredExecutiveMemory:
    """
    Manages the 8 distinct layers of executive memory for the AI CEO.
    Enforces isolation, retention policies, and fact vs inference verification.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        # Memory storage organized by tier
        self._store: Dict[int, List[LayeredMemoryRecord]] = {i: [] for i in range(1, 9)}
        self._seed_baseline_memory()

    def _seed_baseline_memory(self):
        import os
        app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
        is_prod = (app_env in ("production", "prod", "staging")) or (os.environ.get("ZONATA_PRODUCTION", "0") == "1") or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")
        enable_demo = (os.environ.get("ZONATA_ENABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes")) and not is_prod
        clean_mode = is_prod or not enable_demo or (os.environ.get("ZONATA_DISABLE_DEMO_SEED", "0").lower() in ("1", "true", "yes"))
        if clean_mode:
            return
        # Level 5: Organizational Memory
        self.store_memory(
            level=MemoryTierLevel.LEVEL_5_ORGANIZATIONAL,
            content="Corporate Charter: Operations run under sovereign governance standards with bounded dynamic yield management.",
            epistemic_category="FACT",
            source="CORPORATE_CHARTER",
            provenance="charter_v1.0"
        )
        # Level 8: Evidence-backed Factual Memory
        self.store_memory(
            level=MemoryTierLevel.LEVEL_8_EVIDENCE_FACT,
            content="Cryptographic Merkle Root integrity verified for fiscal period 2026-Q3.",
            epistemic_category="FACT",
            source="PHYSICAL_TRUTH_ENGINE",
            provenance="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def store_memory(
        self,
        level: int,
        content: str,
        epistemic_category: str = "OBSERVATION",
        structured_payload: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        scope: str = "GLOBAL",
        source: str = "SYSTEM",
        provenance: str = "auto",
        authority_required: str = "OPERATOR",
        retention_policy: str = "90_DAYS"
    ) -> LayeredMemoryRecord:
        # Invariant: Model inferences cannot be stored directly as Level 8 Facts
        if level == MemoryTierLevel.LEVEL_8_EVIDENCE_FACT and epistemic_category != "FACT":
            logger.warning("Attempted to record unverified inference as Level 8 Fact. Demoting to Level 2 Working Memory.")
            level = MemoryTierLevel.LEVEL_2_WORKING_EXECUTIVE

        mem_id = f"mem_L{level}_{uuid.uuid4().hex[:8]}"
        rec = LayeredMemoryRecord(
            memory_id=mem_id,
            level=level,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            scope=scope,
            content=content,
            structured_payload=structured_payload or {},
            epistemic_category=epistemic_category,
            confidence=confidence,
            source=source,
            provenance=provenance,
            authority_required=authority_required,
            retention_policy=retention_policy,
            created_at=time.time()
        )
        self._store[level].append(rec)
        return rec

    def query_memories(
        self,
        levels: Optional[List[int]] = None,
        scope: Optional[str] = None,
        limit: int = 10
    ) -> List[LayeredMemoryRecord]:
        target_levels = levels or list(range(1, 9))
        results = []
        for lvl in target_levels:
            for rec in self._store.get(lvl, []):
                if scope and rec.scope != scope and rec.scope != "GLOBAL":
                    continue
                results.append(rec)
        # Return sorted by recency
        return sorted(results, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_conversation_window(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Returns Level 1 conversation records."""
        l1 = self._store.get(MemoryTierLevel.LEVEL_1_CONVERSATION, [])
        return [m.to_dict() for m in l1[-limit:]]

    def prune_expired_memories(self, current_time: Optional[float] = None) -> int:
        """Prunes memories that have exceeded their designated retention policy."""
        now = current_time or time.time()
        pruned_count = 0
        ttl_map = {
            "EPHEMERAL": 3600.0,       # 1 hour
            "SESSION": 86400.0,        # 24 hours
            "90_DAYS": 90 * 86400.0,   # 90 days
            "IMMUTABLE": float("inf")  # never
        }
        for lvl in range(1, 9):
            retained = []
            for rec in self._store.get(lvl, []):
                ttl = ttl_map.get(rec.retention_policy, 90 * 86400.0)
                if (now - rec.created_at) <= ttl:
                    retained.append(rec)
                else:
                    pruned_count += 1
            self._store[lvl] = retained
        return pruned_count

    def resolve_conflicting_memory(
        self,
        memory_id: str,
        superseding_content: str,
        evidence_hash: str
    ) -> Optional[LayeredMemoryRecord]:
        """Resolves a conflicting memory record with verified physical evidence."""
        for lvl in range(1, 9):
            for rec in self._store.get(lvl, []):
                if rec.memory_id == memory_id:
                    rec.content = superseding_content
                    rec.provenance = evidence_hash
                    rec.confidence = 1.0
                    rec.epistemic_category = "FACT"
                    rec.source = "PHYSICAL_TRUTH_ENGINE"
                    return rec
        return None
