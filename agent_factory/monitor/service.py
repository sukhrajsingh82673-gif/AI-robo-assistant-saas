"""ZONATA Agent Factory - Monitoring & SLO Service.

Implements Phase 9:
- Health status and incident tracking
- SLO compliance checks (latency, error rate, cost)
- Employee and user feedback logging in af_feedback
- Operational metrics recording in af_lifecycle_event and EvidenceLedger
"""

from __future__ import annotations
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from agent_factory.ports import EvidenceEvent


class MonitoringError(Exception):
    pass


class MonitoringService:
    def __init__(self, db_conn_factory, evidence_port):
        self.db_conn_factory = db_conn_factory
        self.evidence = evidence_port

    def _get_connection(self):
        return self.db_conn_factory()

    def record_feedback(
        self,
        tenant_id: str,
        agent_id: str,
        agent_version_id: Optional[str],
        from_principal: str,
        rating: int,
        category: str = "quality",
        comment: Optional[str] = None,
        task_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record employee or user feedback on an agent."""
        if not (1 <= rating <= 5):
            raise MonitoringError(f"Feedback rating must be between 1 and 5, got {rating}")
        
        valid_cats = {'quality', 'speed', 'safety', 'cost', 'missing_capability', 'other'}
        if category not in valid_cats:
            raise MonitoringError(f"Invalid category '{category}'. Must be one of: {valid_cats}")

        now = time.time()
        feedback_id = f"fbk_{uuid.uuid4().hex[:12]}"

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO af_feedback (
                    id, tenant_id, agent_id, agent_version_id, from_principal,
                    rating, category, comment, task_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback_id, tenant_id, agent_id, agent_version_id, from_principal,
                rating, category, comment or "", task_ref or "", now
            ))
            conn.commit()

        # Evidence logging
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_feedback",
            subject_id=agent_id,
            event_type="feedback.recorded",
            actor=from_principal,
            payload_hashes={"feedback_id": feedback_id, "rating": str(rating), "category": category},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "feedback_id": feedback_id,
            "agent_id": agent_id,
            "rating": rating,
            "category": category,
            "evidence_id": ev_id
        }

    def record_incident(
        self,
        tenant_id: str,
        agent_id: str,
        reason: str,
        severity: str = "high",
        reported_by: str = "system.monitor"
    ) -> Dict[str, Any]:
        """Flag agent into INCIDENT or DEGRADED status upon SLO breach or failure."""
        now = time.time()
        new_status = "INCIDENT" if severity in ("high", "critical") else "DEGRADED"

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE af_agent
                SET monitoring_status = ?, updated_at = ?
                WHERE tenant_id = ? AND id = ?
            """, (new_status, now, tenant_id, agent_id))

            conn.execute("""
                INSERT INTO af_lifecycle_event (
                    tenant_id, subject_kind, subject_id, from_state, to_state,
                    actor, reason, evidence_ledger_id, created_at
                ) VALUES (?, 'agent', ?, 'HEALTHY', ?, ?, ?, 'ev_incident', ?)
            """, (tenant_id, agent_id, new_status, reported_by, reason, now))
            conn.commit()

        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_incident",
            subject_id=agent_id,
            event_type="agent.incident_flagged",
            actor=reported_by,
            payload_hashes={"status": new_status, "reason": reason, "severity": severity},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "agent_id": agent_id,
            "monitoring_status": new_status,
            "reason": reason,
            "evidence_id": ev_id
        }

    def get_monitoring_summary(
        self,
        tenant_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Fetch real-time health, feedback, and runtime instance stats."""
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT id, slug, role_title, lifecycle, monitoring_status, active_version_id
                FROM af_agent WHERE tenant_id = ? AND id = ?
            """, (tenant_id, agent_id))
            agent_row = cur.fetchone()
            if not agent_row:
                raise MonitoringError(f"Agent '{agent_id}' not found")

            # Feedback aggregation
            cur = conn.execute("""
                SELECT COUNT(*), AVG(rating) FROM af_feedback WHERE tenant_id = ? AND agent_id = ?
            """, (tenant_id, agent_id))
            fb_count, fb_avg = cur.fetchone()

            # Active runtime instances
            cur = conn.execute("""
                SELECT id, channel, traffic_percent, status, started_at
                FROM af_runtime_instance WHERE tenant_id = ? AND agent_id = ?
            """, (tenant_id, agent_id))
            instances = [
                {
                    "instance_id": r[0],
                    "channel": r[1],
                    "traffic_percent": r[2],
                    "status": r[3],
                    "started_at": r[4]
                }
                for r in cur.fetchall()
            ]

        return {
            "agent_id": agent_id,
            "slug": agent_row[1],
            "role_title": agent_row[2],
            "lifecycle": agent_row[3],
            "monitoring_status": agent_row[4],
            "active_version_id": agent_row[5],
            "feedback": {
                "total_count": fb_count or 0,
                "average_rating": round(fb_avg or 0.0, 2)
            },
            "runtime_instances": instances
        }
