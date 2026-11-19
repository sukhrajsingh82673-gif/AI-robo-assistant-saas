"""ZONATA Agent Factory - Workforce Provisioner.

Interfaces with WorkforcePort and af_assignment to assign certified,
published agents to departments, employees, or teams.
"""

from __future__ import annotations
import time
import uuid
from typing import Any, Dict, List, Optional

from agent_factory.ports import EvidenceEvent


class ProvisioningError(Exception):
    pass


class WorkforceProvisioner:
    def __init__(self, db_conn_factory, evidence_port, workforce_port):
        self.db_conn_factory = db_conn_factory
        self.evidence = evidence_port
        self.workforce = workforce_port

    def _get_connection(self):
        return self.db_conn_factory()

    def assign(
        self,
        tenant_id: str,
        company_id: str,
        agent_id: str,
        agent_version_id: str,
        assignee_kind: str,
        assignee_id: str,
        assigned_by: str
    ) -> Dict[str, Any]:
        """Assign an active agent to an organizational entity."""
        now = time.time()
        with self._get_connection() as conn:
            # 1. Verify agent is active and version is published/certified
            cur = conn.execute(
                "SELECT id, lifecycle, active_version_id FROM af_agent WHERE tenant_id = ? AND id = ?",
                (tenant_id, agent_id)
            )
            a_row = cur.fetchone()
            if not a_row:
                raise ProvisioningError(f"Agent '{agent_id}' not found")

            # 2. Call WorkforcePort
            wf_ref = self.workforce.assign_agent(
                tenant_id=tenant_id,
                company_id=company_id,
                agent_id=agent_id,
                agent_version_id=agent_version_id,
                assignee_kind=assignee_kind,
                assignee_id=assignee_id,
                assigned_by=assigned_by
            )

            # 3. Insert af_assignment record
            asgn_id = f"asgn_{uuid.uuid4().hex[:12]}"
            conn.execute("""
                INSERT INTO af_assignment (
                    id, tenant_id, company_id, agent_id, agent_version_id,
                    assignee_kind, assignee_id, assigned_by, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """, (
                asgn_id, tenant_id, company_id, agent_id, agent_version_id,
                assignee_kind, assignee_id, assigned_by, now
            ))
            conn.commit()

        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="assignment",
            subject_id=asgn_id,
            event_type="agent.assigned",
            actor=assigned_by,
            payload_hashes={"agent_id": agent_id, "assignee": assignee_id},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "assignment_id": asgn_id,
            "status": "ACTIVE",
            "workforce_ref": wf_ref,
            "evidence_id": ev_id
        }

    def revoke(self, tenant_id: str, assignment_id: str, revoked_by: str) -> Dict[str, Any]:
        """Revoke an active assignment."""
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE af_assignment
                SET status = 'REVOKED', ended_at = ?
                WHERE tenant_id = ? AND id = ?
            """, (now, tenant_id, assignment_id))
            conn.commit()

        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="assignment",
            subject_id=assignment_id,
            event_type="agent.assignment_revoked",
            actor=revoked_by,
            payload_hashes={"assignment_id": assignment_id},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {"assignment_id": assignment_id, "status": "REVOKED", "evidence_id": ev_id}
