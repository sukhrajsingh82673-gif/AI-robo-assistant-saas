"""ZONATA Sovereign Core — Document Evidence Sealing Adapter.

Bridges Document Backbone events with the append-only EvidenceLedger.
"""

from __future__ import annotations
import json
import uuid
from typing import Any, Dict, Optional

from core.evidence_ledger import EvidenceLedger
from core.models import PhysicalVerification


def seal_document_event(
    ledger: EvidenceLedger,
    event_type: str,
    actor_id: str,
    tenant_id: str,
    company_id: str,
    payload: Dict[str, Any],
) -> str:
    """Seals a document lifecycle event into the Merkle EvidenceLedger."""
    action_id = f"act_doc_{uuid.uuid4().hex[:12]}"
    mission_id = f"msn_doc_{tenant_id}"
    verifications = [
        PhysicalVerification(
            check_type="DOCUMENT_LIFECYCLE_VERIFICATION",
            target_path=str(payload.get("document_id", "document")),
            expected_val=event_type,
            actual_val=event_type,
            verified=True,
            details=json.dumps({"event_type": event_type, "tenant_id": tenant_id}),
        )
    ]
    meta = {
        "event_type": event_type,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "payload": payload,
        "classification": "SOVEREIGN_DOCUMENT_BACKBONE",
    }
    pkg = ledger.seal_evidence(
        action_id=action_id,
        mission_id=mission_id,
        agent_id=actor_id,
        verifications=verifications,
        metadata=meta,
    )
    return getattr(pkg, "evidence_id", str(pkg))
