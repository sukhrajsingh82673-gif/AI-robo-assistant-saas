"""
Independent Status Page Probe Engine and Incident State Machine (ADR 0053, Rule 83).
Monitors service health out-of-band and manages incident life cycles.
"""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class ServiceStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    PARTIAL_OUTAGE = "PARTIAL_OUTAGE"
    MAJOR_OUTAGE = "MAJOR_OUTAGE"


@dataclass
class IncidentRecord:
    incident_id: str
    title: str
    impact: str  # degraded, minor, major
    status: str  # investigating, identified, monitoring, resolved
    updates: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None


class StatusProbeEngine:
    """
    Simulates external out-of-band probe running on separate infrastructure.
    Survives core database/cluster outages.
    """

    SERVICES = ["Core API", "Edge Gateway", "Billing & Metering", "Agent Runtime", "Webhooks Delivery"]

    def __init__(self):
        # service_name -> ServiceStatus
        self._service_states: Dict[str, ServiceStatus] = {s: ServiceStatus.OPERATIONAL for s in self.SERVICES}
        # incident_id -> IncidentRecord
        self._incidents: Dict[str, IncidentRecord] = {}

    def get_overall_system_status(self) -> ServiceStatus:
        statuses = list(self._service_states.values())
        if ServiceStatus.MAJOR_OUTAGE in statuses:
            return ServiceStatus.MAJOR_OUTAGE
        if ServiceStatus.PARTIAL_OUTAGE in statuses:
            return ServiceStatus.PARTIAL_OUTAGE
        if ServiceStatus.DEGRADED in statuses:
            return ServiceStatus.DEGRADED
        return ServiceStatus.OPERATIONAL

    def update_service_status(self, service: str, status: ServiceStatus):
        if service not in self._service_states:
            raise KeyError(f"Unknown service: {service}")
        self._service_states[service] = status

    def declare_incident(self, title: str, impact: str, initial_message: str) -> IncidentRecord:
        incident_id = f"inc_{uuid.uuid4().hex[:8]}"
        record = IncidentRecord(
            incident_id=incident_id,
            title=title,
            impact=impact,
            status="investigating",
            updates=[{"timestamp": time.time(), "status": "investigating", "message": initial_message}],
        )
        self._incidents[incident_id] = record
        return record

    def update_incident(self, incident_id: str, new_status: str, message: str) -> IncidentRecord:
        record = self._incidents.get(incident_id)
        if not record:
            raise KeyError(f"Incident '{incident_id}' not found")

        record.status = new_status
        record.updates.append({"timestamp": time.time(), "status": new_status, "message": message})
        if new_status == "resolved":
            record.resolved_at = time.time()
        return record

    def list_active_incidents(self) -> List[IncidentRecord]:
        return [inc for inc in self._incidents.values() if inc.status != "resolved"]

    def export_status_json(self) -> Dict[str, Any]:
        """Renders static JSON consumed by independent CDN status dashboard."""
        return {
            "status": self.get_overall_system_status().value,
            "services": {k: v.value for k, v in self._service_states.items()},
            "active_incidents": [
                {
                    "incident_id": inc.incident_id,
                    "title": inc.title,
                    "impact": inc.impact,
                    "status": inc.status,
                    "latest_update": inc.updates[-1] if inc.updates else None,
                }
                for inc in self.list_active_incidents()
            ],
            "updated_at": time.time(),
        }
