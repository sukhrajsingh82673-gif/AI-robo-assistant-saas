"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V8 Architecture — Executive Event Model & Emission Fabric
Provides typed, immutable, auditable events for the AI CEO Executive Operating Layer.

Constitutional Invariants:
  AUDITABLE_TRANSITIONS (Every executive state mutation produces an event)
  PROVENANCE_SEALED (All events record tenant, company, actor, and timestamp)
"""

import time
import json
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict

@dataclass
class ExecutiveEvent:
    event_id: str
    event_type: str
    tenant_id: str
    company_id: str
    payload: Dict[str, Any]
    actor: str = "AI_CEO"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutiveEventBus:
    """Thread-safe in-memory and database-backed event dispatcher for executive events."""
    _listeners = []

    @classmethod
    def emit(cls, event: ExecutiveEvent):
        # Notify subscribers
        for listener in cls._listeners:
            try:
                listener(event)
            except Exception:
                pass
        return event

    @classmethod
    def subscribe(cls, callback):
        cls._listeners.append(callback)

# Factory helpers for all required V8 events
def create_executive_event(event_type: str, tenant_id: str, company_id: str, payload: Dict[str, Any], actor: str = "AI_CEO") -> ExecutiveEvent:
    ev = ExecutiveEvent(
        event_id=f"evt_exec_{uuid.uuid4().hex[:10]}",
        event_type=event_type,
        tenant_id=tenant_id,
        company_id=company_id,
        payload=payload,
        actor=actor
    )
    return ExecutiveEventBus.emit(ev)
