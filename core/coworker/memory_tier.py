"""
ZONATA Universal AI Co-worker Fabric — Multi-Tiered Memory Architecture
Implements segregated, governed memory pools inspired by Hermes & Letta paradigms:
1. BUSINESS_MEMORY: Authoritative corporate truths, financials, policies (Worker cannot overwrite).
2. OPERATIONAL_MEMORY: Worker's internal active state, operational state.
3. TASK_MEMORY: Transient mission and task context.
4. SKILL_MEMORY: Admitted learned procedures and workflows.
5. EPISODIC_MEMORY: Historical trajectories, verified tool outputs.
6. CONVERSATION_MEMORY: User interaction dialogues.

Critical Invariant:
Worker memory NEVER becomes an authority source.
Writes to BUSINESS_MEMORY require explicit sovereign authority.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
import time
import uuid
import hashlib
from dataclasses import dataclass, field

class MemoryTier(str, Enum):
    BUSINESS_MEMORY = "BUSINESS_MEMORY"
    OPERATIONAL_MEMORY = "OPERATIONAL_MEMORY"
    TASK_MEMORY = "TASK_MEMORY"
    SKILL_MEMORY = "SKILL_MEMORY"
    EPISODIC_MEMORY = "EPISODIC_MEMORY"
    CONVERSATION_MEMORY = "CONVERSATION_MEMORY"

@dataclass
class MemoryRecord:
    memory_id: str
    tier: MemoryTier
    tenant_id: str
    company_id: str
    worker_id: str
    mission_id: Optional[str]
    key: str
    value: Any
    source: str
    confidence: float
    timestamp: float = field(default_factory=time.time)
    provenance: str = "zonata_runtime"
    retention_days: int = 90
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            payload = f"{self.tenant_id}:{self.key}:{str(self.value)}"
            self.hash = hashlib.sha256(payload.encode()).hexdigest()

class GovernedMemoryManager:
    """
    Authoritative manager for multi-tiered Co-Worker memory.
    """

    def __init__(self, tenant_id: str = "tnt_primary", company_id: str = "comp_primary"):
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._store: Dict[MemoryTier, Dict[str, MemoryRecord]] = {
            tier: {} for tier in MemoryTier
        }

    def store_memory(
        self,
        tier: MemoryTier,
        key: str,
        value: Any,
        worker_id: str,
        mission_id: Optional[str] = None,
        source: str = "runtime_execution",
        confidence: float = 1.0,
        is_sovereign_write: bool = False
    ) -> MemoryRecord:
        """
        Stores a memory record under governed access control.
        Prevents non-sovereign worker processes from polluting BUSINESS_MEMORY.
        """
        if tier == MemoryTier.BUSINESS_MEMORY and not is_sovereign_write:
            raise PermissionError("Worker memory cannot directly write to Authoritative BUSINESS_MEMORY without sovereign approval")

        # Memory DLP Gate: scrub raw credentials, keys, or prohibited secrets before persistence
        from core.ai_dlp_gateway import ai_dlp_gateway
        _, sanitized_val, _ = ai_dlp_gateway.inspect_memory_persistence(
            tier_name=tier.value,
            key=key,
            value=value,
            tenant_id=self.tenant_id,
            worker_id=worker_id
        )

        mid = f"mem_{uuid.uuid4().hex[:8]}"
        record = MemoryRecord(
            memory_id=mid,
            tier=tier,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            worker_id=worker_id,
            mission_id=mission_id,
            key=key,
            value=sanitized_val,
            source=source,
            confidence=confidence
        )
        self._store[tier][key] = record
        return record

    def retrieve_memory(self, tier: MemoryTier, key: str) -> Optional[MemoryRecord]:
        return self._store[tier].get(key)

    def query_tier(self, tier: MemoryTier, prefix: Optional[str] = None) -> List[MemoryRecord]:
        records = list(self._store[tier].values())
        if prefix:
            return [r for r in records if r.key.startswith(prefix)]
        return records

    def clear_task_memory(self, mission_id: str):
        """Cleans up transient task memory once a mission completes."""
        to_del = [k for k, v in self._store[MemoryTier.TASK_MEMORY].items() if v.mission_id == mission_id]
        for k in to_del:
            del self._store[MemoryTier.TASK_MEMORY][k]
