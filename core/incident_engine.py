"""
RoboAssistant Enterprise — Executive Incident Engine
Tracks, triages, contains, and post-mortems production anomalies, authority violations,
security breaches, and external system drifts.
"""

import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from .db import db

logger = logging.getLogger("ZonataIncidents")

class IncidentSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentState:
    DETECTED = "DETECTED"
    TRIAGED = "TRIAGED"
    CONTAINED = "CONTAINED"
    INVESTIGATING = "INVESTIGATING"
    RECOVERING = "RECOVERING"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    POSTMORTEM_REQUIRED = "POSTMORTEM_REQUIRED"

class IncidentCategory:
    SECURITY = "SECURITY"
    FINANCIAL_VARIANCE = "FINANCIAL_VARIANCE"
    SYSTEM_DRIFT = "SYSTEM_DRIFT"
    AUTONOMY_VIOLATION = "AUTONOMY_VIOLATION"
    DATA_INTEGRITY = "DATA_INTEGRITY"

class ExecutiveIncidentEngine:
    """
    Enterprise incident management engine enforcing strict state machine transitions
    and automatic containment for critical enterprise events.
    """

    ALLOWED_TRANSITIONS = {
        IncidentState.DETECTED: [IncidentState.TRIAGED, IncidentState.CONTAINED],
        IncidentState.TRIAGED: [IncidentState.CONTAINED, IncidentState.INVESTIGATING],
        IncidentState.CONTAINED: [IncidentState.INVESTIGATING, IncidentState.RECOVERING],
        IncidentState.INVESTIGATING: [IncidentState.RECOVERING, IncidentState.CONTAINED],
        IncidentState.RECOVERING: [IncidentState.VERIFIED, IncidentState.INVESTIGATING],
        IncidentState.VERIFIED: [IncidentState.CLOSED, IncidentState.POSTMORTEM_REQUIRED],
        IncidentState.POSTMORTEM_REQUIRED: [IncidentState.CLOSED],
        IncidentState.CLOSED: []
    }

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    def create_incident(
        self,
        company_id: str,
        title: str,
        severity: str,
        category: str,
        description: str,
        evidence_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates and logs a new enterprise incident."""
        incident_id = f"inc_{uuid.uuid4().hex[:12]}"
        now = time.time()
        
        # Auto-contain if CRITICAL
        initial_state = IncidentState.DETECTED
        containment = None
        if severity == IncidentSeverity.CRITICAL:
            initial_state = IncidentState.CONTAINED
            containment = "AUTOMATIC_KILLSWITCH_TRIGGERED: Operations suspended pending owner review"

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO executive_incidents (
                    incident_id, tenant_id, company_id, title,
                    severity, category, current_state, description,
                    evidence_ref, containment_action, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    self.tenant_id,
                    company_id,
                    title,
                    severity,
                    category,
                    initial_state,
                    description,
                    evidence_ref,
                    containment,
                    now,
                    now
                )
            )
            conn.commit()

        return {
            "incident_id": incident_id,
            "title": title,
            "severity": severity,
            "category": category,
            "current_state": initial_state,
            "containment_action": containment,
            "created_at": now
        }

    def transition_state(
        self,
        incident_id: str,
        target_state: str,
        notes: str,
        containment_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transitions an incident to a new state along approved paths."""
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM executive_incidents WHERE incident_id = ? AND tenant_id = ?",
                (incident_id, self.tenant_id)
            ).fetchone()
            if not row:
                raise ValueError(f"Incident {incident_id} not found")

            current = row["current_state"]
            valid_targets = self.ALLOWED_TRANSITIONS.get(current, [])
            if target_state not in valid_targets:
                raise ValueError(f"Invalid transition from {current} to {target_state}. Allowed: {valid_targets}")

            containment = containment_action or row["containment_action"]
            closed_at = now if target_state == IncidentState.CLOSED else None

            conn.execute(
                """
                UPDATE executive_incidents
                SET current_state = ?, containment_action = ?, updated_at = ?, closed_at = ?
                WHERE incident_id = ?
                """,
                (target_state, containment, now, closed_at, incident_id)
            )
            conn.commit()

            return {
                "incident_id": incident_id,
                "previous_state": current,
                "current_state": target_state,
                "containment_action": containment,
                "updated_at": now,
                "notes": notes
            }

    def attach_postmortem(
        self,
        incident_id: str,
        root_cause: str,
        corrective_actions: List[str],
        preventive_controls: List[str]
    ) -> Dict[str, Any]:
        """Attaches a formal postmortem analysis to a resolved incident."""
        now = time.time()
        postmortem_data = {
            "root_cause": root_cause,
            "corrective_actions": corrective_actions,
            "preventive_controls": preventive_controls,
            "completed_at": now
        }
        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE executive_incidents
                SET postmortem = ?, current_state = 'CLOSED', closed_at = ?, updated_at = ?
                WHERE incident_id = ? AND tenant_id = ?
                """,
                (json.dumps(postmortem_data), now, now, incident_id, self.tenant_id)
            )
            conn.commit()

        return {
            "incident_id": incident_id,
            "postmortem": postmortem_data,
            "status": "CLOSED"
        }

    def list_incidents(self, active_only: bool = True) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM executive_incidents WHERE tenant_id = ? AND current_state != 'CLOSED' ORDER BY created_at DESC",
                    (self.tenant_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM executive_incidents WHERE tenant_id = ? ORDER BY created_at DESC",
                    (self.tenant_id,)
                ).fetchall()

            res = []
            for r in rows:
                item = dict(r)
                if item["postmortem"]:
                    item["postmortem"] = json.loads(item["postmortem"])
                res.append(item)
            return res
