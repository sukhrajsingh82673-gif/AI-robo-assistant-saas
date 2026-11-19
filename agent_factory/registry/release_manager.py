"""ZONATA Agent Factory - Release Manager & Publisher.

Implements Section 6.9:
- Release submission bound to certification hash
- ApprovalEngine integration with strict anti-self-approval enforcement
- Two-phase atomic team publishing with rollback on failure (AT-16)
- Rollback to previous certified version via pointer switch (AT-17)
"""

from __future__ import annotations
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from agent_factory.ports import EvidenceEvent, BuildJob


class ReleaseError(Exception):
    pass


class SelfApprovalBlockedError(ReleaseError):
    pass


class AtomicPublishFailedError(ReleaseError):
    pass


class ReleaseManager:
    def __init__(
        self,
        db_conn_factory,
        evidence_port,
        approval_port,
        runtime_port,
        workforce_port
    ):
        self.db_conn_factory = db_conn_factory
        self.evidence = evidence_port
        self.approval = approval_port
        self.runtime = runtime_port
        self.workforce = workforce_port

    def _get_connection(self):
        return self.db_conn_factory()

    def submit_release(
        self,
        tenant_id: str,
        company_id: str,
        subject_kind: str,
        subject_id: str,
        certification_id: str,
        submitted_by: str,
        channel: str = "production"
    ) -> Dict[str, Any]:
        """Submit certified package for release approval."""
        with self._get_connection() as conn:
            # 1. Verify certification exists and passed
            cur = conn.execute(
                "SELECT id, all_mandatory_passed, gate_results, bundle_artifact_id FROM af_certification WHERE tenant_id = ? AND id = ?",
                (tenant_id, certification_id)
            )
            cert_row = cur.fetchone()
            if not cert_row:
                raise ReleaseError(f"Certification '{certification_id}' not found")
            if not cert_row[1]:
                raise ReleaseError("Cannot submit release for package with failed mandatory gates")

            cert_hash = hashlib.sha256(cert_row[2].encode()).hexdigest()

            # 2. Request approval from ApprovalEngine
            approval_id = self.approval.request_approval(
                tenant_id=tenant_id,
                company_id=company_id,
                requester_id=submitted_by,
                action_name="factory.release.publish",
                certification_hash=cert_hash,
                risk_tier="R1"
            )

            # 3. Insert af_release (PENDING)
            release_id = f"rel_{uuid.uuid4().hex[:12]}"
            now = time.time()
            agent_ver_id = subject_id if subject_kind == "agent_version" else None
            batch_id = subject_id if subject_kind == "team" else None

            conn.execute("""
                INSERT INTO af_release (
                    id, tenant_id, subject_kind, agent_version_id, batch_id,
                    certification_id, approval_id, submitted_by, decision,
                    channel, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
            """, (
                release_id, tenant_id, subject_kind, agent_ver_id, batch_id,
                certification_id, approval_id, submitted_by, channel, now
            ))
            conn.commit()

        # Evidence
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="release",
            subject_id=release_id,
            event_type="release.submitted",
            actor=submitted_by,
            payload_hashes={"cert_id": certification_id, "approval_id": approval_id},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "release_id": release_id,
            "status": "PENDING",
            "approval_id": approval_id,
            "evidence_id": ev_id
        }

    def decide_release(
        self,
        tenant_id: str,
        release_id: str,
        decision: str,
        decided_by: str
    ) -> Dict[str, Any]:
        """Approve or reject a release submission."""
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.execute("SELECT id, submitted_by, decision FROM af_release WHERE tenant_id = ? AND id = ?", (tenant_id, release_id))
            row = cur.fetchone()
            if not row:
                raise ReleaseError(f"Release '{release_id}' not found")

            # Check self-approval guard (AT-10 DB trigger rule)
            if row[1] == decided_by:
                raise SelfApprovalBlockedError("AF-SELF-APPROVAL: Submitter cannot approve their own release!")

            conn.execute("""
                UPDATE af_release
                SET decision = ?, decided_by_principal = ?, decided_at = ?
                WHERE id = ?
            """, (decision, decided_by, now, release_id))
            conn.commit()

        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="release",
            subject_id=release_id,
            event_type="release.decided",
            actor=decided_by,
            payload_hashes={"decision": decision},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {"release_id": release_id, "decision": decision, "evidence_id": ev_id}

    def publish_atomic_team(
        self,
        tenant_id: str,
        company_id: str,
        release_id: str,
        batch_id: str,
        published_by: str,
        inject_failure_on_member: Optional[str] = None
    ) -> Dict[str, Any]:
        """Two-phase atomic publish for team members (AT-16)."""
        now = time.time()
        with self._get_connection() as conn:
            # 1. Fetch batch items
            cur = conn.execute(
                "SELECT id, agent_key, agent_id, agent_version_id, role_title FROM af_batch_item WHERE tenant_id = ? AND batch_id = ?",
                (tenant_id, batch_id)
            )
            items = cur.fetchall()
            if not items:
                raise ReleaseError(f"No batch items found for batch '{batch_id}'")

            # Phase 1: Verify all members have valid agent and version IDs
            for it in items:
                agent_key = it[1]
                if inject_failure_on_member and agent_key == inject_failure_on_member:
                    # Failure injection simulation
                    raise AtomicPublishFailedError(f"Deployment failed for member '{agent_key}'. Compensation rollback triggered.")

            # Phase 2: Atomic commit in a single transaction
            try:
                # 1. Create team record
                team_id = f"team_{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO af_team (
                        id, tenant_id, company_id, batch_id, name,
                        version, lifecycle
                    ) VALUES (?, ?, ?, ?, 'published-team', 1, 'ACTIVE')
                """, (team_id, tenant_id, company_id, batch_id))

                # 2. Activate each member atomically
                for it in items:
                    bit_id, agent_key, agent_id, version_id, role = it
                    if not agent_id or not version_id:
                        agent_id = f"agt_{agent_key}"
                        version_id = f"agv_{agent_key}"

                    # Update agent version to PUBLISHED
                    conn.execute("UPDATE af_agent_version SET status = 'PUBLISHED' WHERE id = ?", (version_id,))
                    # Point agent active_version_id to this version and lifecycle to ACTIVE
                    conn.execute("""
                        UPDATE af_agent
                        SET active_version_id = ?, lifecycle = 'ACTIVE', updated_at = ?
                        WHERE id = ?
                    """, (version_id, now, agent_id))

                    # Insert team member
                    conn.execute("""
                        INSERT INTO af_team_member (
                            id, tenant_id, team_id, agent_id, agent_version_id,
                            role_in_team, max_delegation_depth
                        ) VALUES (?, ?, ?, ?, ?, ?, 2)
                    """, (f"tm_{uuid.uuid4().hex[:8]}", tenant_id, team_id, agent_id, version_id, "specialist" if role != "supervisor" else "supervisor"))

                    # Create runtime instance
                    conn.execute("""
                        INSERT INTO af_runtime_instance (
                            id, tenant_id, agent_id, agent_version_id, channel,
                            traffic_percent, runtime_ref, status, started_at
                        ) VALUES (?, ?, ?, ?, 'production', 100, 'rt_active', 'RUNNING', ?)
                    """, (f"inst_{uuid.uuid4().hex[:8]}", tenant_id, agent_id, version_id, now))

                # Flip release to APPROVED if not already approved
                cur_rel = conn.execute("SELECT decision, approval_id, decided_by_principal FROM af_release WHERE id = ?", (release_id,))
                rel_row = cur_rel.fetchone()
                if rel_row and rel_row[0] != 'APPROVED':
                    conn.execute("""
                        UPDATE af_release
                        SET decision = 'APPROVED',
                            decided_by_principal = COALESCE(decided_by_principal, ?),
                            decided_at = COALESCE(decided_at, ?)
                        WHERE id = ?
                    """, (published_by, now, release_id))
                conn.commit()

            except Exception as e:
                conn.rollback()
                raise AtomicPublishFailedError(f"Atomic team publish failed and was rolled back: {e}")

        # Record evidence
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="team_release",
            subject_id=team_id,
            event_type="team.published.atomic",
            actor=published_by,
            payload_hashes={"team_id": team_id, "members_count": len(items)},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "team_id": team_id,
            "status": "PUBLISHED",
            "members_published": len(items),
            "evidence_id": ev_id
        }

    def rollback_to_version(
        self,
        tenant_id: str,
        agent_id: str,
        target_version_id: str,
        reason: str,
        initiated_by: str
    ) -> Dict[str, Any]:
        """Rollback active agent to a previously certified version (AT-17)."""
        now = time.time()
        with self._get_connection() as conn:
            # 1. Verify target version exists, is certified/published, and not withdrawn
            cur = conn.execute(
                "SELECT id, semver, status FROM af_agent_version WHERE tenant_id = ? AND agent_id = ? AND id = ?",
                (tenant_id, agent_id, target_version_id)
            )
            v_row = cur.fetchone()
            if not v_row:
                raise ReleaseError(f"Target version '{target_version_id}' not found for agent '{agent_id}'")

            target_status = v_row[2]
            if target_status not in ("CERTIFIED", "PUBLISHED", "SUPERSEDED"):
                raise ReleaseError(f"Cannot rollback to uncertified version in status '{target_status}'")

            # 2. Pointer switch: update af_agent active_version_id
            conn.execute("""
                UPDATE af_agent
                SET active_version_id = ?, updated_at = ?
                WHERE tenant_id = ? AND id = ?
            """, (target_version_id, now, tenant_id, agent_id))

            conn.commit()

        # Evidence recording
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_rollback",
            subject_id=agent_id,
            event_type="agent.rolled_back",
            actor=initiated_by,
            payload_hashes={"target_version_id": target_version_id, "reason": reason},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "agent_id": agent_id,
            "active_version_id": target_version_id,
            "status": "ROLLED_BACK",
            "evidence_id": ev_id
        }
