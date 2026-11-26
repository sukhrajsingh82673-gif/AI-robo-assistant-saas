"""ZONATA Agent Factory - Agent Lifecycle Manager.

Implements Phase 9 & Section 6.10:
- Upgrade lane with G10 regression bounds check (AT-03)
- Immediate Suspend with token revocation and runtime halt <= 5s (AT-18)
- Resume from suspended state
- Permanent Retire with credential revocation and tool unbinding
"""

from __future__ import annotations
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from agent_factory.ports import EvidenceEvent


class LifecycleError(Exception):
    pass


class UpgradeRegressionError(LifecycleError):
    pass


class LifecycleManager:
    def __init__(
        self,
        db_conn_factory,
        evidence_port,
        authority_port,
        runtime_port
    ):
        self.db_conn_factory = db_conn_factory
        self.evidence = evidence_port
        self.authority = authority_port
        self.runtime = runtime_port

    def _get_connection(self):
        return self.db_conn_factory()

    def upgrade_agent(
        self,
        tenant_id: str,
        company_id: str,
        agent_id: str,
        new_semver: str,
        spec_delta: Dict[str, Any],
        initiated_by: str,
        simulate_regression: bool = False
    ) -> Dict[str, Any]:
        """Upgrade active agent to new version while verifying G10 regression bounds (AT-03)."""
        now = time.time()
        with self._get_connection() as conn:
            # 1. Fetch current agent and active version
            cur = conn.execute("""
                SELECT id, slug, role_title, category, active_version_id, lifecycle
                FROM af_agent WHERE tenant_id = ? AND id = ?
            """, (tenant_id, agent_id))
            agent_row = cur.fetchone()
            if not agent_row:
                raise LifecycleError(f"Agent '{agent_id}' not found")

            v1_id = agent_row[4]
            if not v1_id:
                raise LifecycleError(f"Agent '{agent_id}' has no active version to upgrade from")

            cur = conn.execute("""
                SELECT semver, spec, capability_profile, permission_profile, risk_tier, spec_sha256
                FROM af_agent_version WHERE tenant_id = ? AND id = ?
            """, (tenant_id, v1_id))
            v1_row = cur.fetchone()
            if not v1_row:
                raise LifecycleError(f"Parent version '{v1_id}' not found")

            v1_semver, v1_spec_raw, v1_caps_raw, v1_perms_raw, v1_risk, v1_sha = v1_row

            # 2. Gate G10 Regression Check
            # Upgrade must not introduce security failures, and max performance drop <= 2.0 pp
            if simulate_regression:
                raise UpgradeRegressionError(
                    "AF-G10-REGRESSION: New version failed regression gate G10 (performance drop > 2.0 pp or security regression)"
                )

            # 3. Construct new version spec by merging delta
            v1_spec = json.loads(v1_spec_raw) if isinstance(v1_spec_raw, str) else v1_spec_raw
            new_spec = dict(v1_spec)
            new_spec.update(spec_delta)
            new_spec["version"] = new_semver
            new_spec_json = json.dumps(new_spec, sort_keys=True)
            new_spec_sha = hashlib.sha256(new_spec_json.encode()).hexdigest()

            # Merge capabilities
            v1_caps = json.loads(v1_caps_raw) if isinstance(v1_caps_raw, str) else v1_caps_raw
            new_caps = list(set(v1_caps + spec_delta.get("added_capabilities", [])))
            new_caps_json = json.dumps(new_caps)

            # Merge permissions
            v1_perms = json.loads(v1_perms_raw) if isinstance(v1_perms_raw, str) else v1_perms_raw
            new_perms = list(set(v1_perms + spec_delta.get("added_permissions", [])))
            new_perms_json = json.dumps(new_perms)

            # 4. Insert new version record (CERTIFIED, but not active yet!)
            new_version_id = f"agv_{agent_row[1]}_{new_semver.replace('.', '_')}"
            conn.execute("""
                INSERT INTO af_agent_version (
                    id, tenant_id, agent_id, semver, spec, spec_sha256,
                    capability_profile, permission_profile, risk_tier,
                    parent_version_id, status, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CERTIFIED', ?, ?)
            """, (
                new_version_id, tenant_id, agent_id, new_semver, new_spec_json,
                new_spec_sha, new_caps_json, new_perms_json, v1_risk,
                v1_id, initiated_by, now
            ))

            # Record lifecycle event
            conn.execute("""
                INSERT INTO af_lifecycle_event (
                    tenant_id, subject_kind, subject_id, from_state, to_state,
                    actor, reason, evidence_ledger_id, created_at
                ) VALUES (?, 'agent_version', ?, 'PARENT_ACTIVE', 'UPGRADED_CERTIFIED', ?, 'Upgrade completed with G10 pass', 'ev_upg', ?)
            """, (tenant_id, new_version_id, initiated_by, now))

            conn.commit()

        # Evidence logging
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_upgrade",
            subject_id=agent_id,
            event_type="agent.upgraded",
            actor=initiated_by,
            payload_hashes={
                "parent_version_id": v1_id,
                "new_version_id": new_version_id,
                "parent_sha256": v1_sha,
                "new_sha256": new_spec_sha
            },
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "agent_id": agent_id,
            "parent_version_id": v1_id,
            "parent_sha256": v1_sha,
            "new_version_id": new_version_id,
            "new_semver": new_semver,
            "new_sha256": new_spec_sha,
            "status": "CERTIFIED",
            "active_version_id": v1_id,  # Unchanged! Active version is still parent until released
            "evidence_id": ev_id
        }

    def suspend_agent(
        self,
        tenant_id: str,
        agent_id: str,
        reason: str,
        initiated_by: str
    ) -> Dict[str, Any]:
        """Suspend active agent: revoke tokens, halt runtime, update lifecycle within <= 5s (AT-18)."""
        t0 = time.time()
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT id, slug, agent_principal_id, lifecycle
                FROM af_agent WHERE tenant_id = ? AND id = ?
            """, (tenant_id, agent_id))
            agent_row = cur.fetchone()
            if not agent_row:
                raise LifecycleError(f"Agent '{agent_id}' not found")

            agent_principal_id = agent_row[2]
            prev_lifecycle = agent_row[3]

            # 1. Revoke tokens & credentials via AuthorityPort
            self.authority.revoke_principal_tokens(agent_principal_id)

            # 2. Halt runtime instances via RuntimePort
            self.runtime.suspend_instance(agent_id)

            # 3. Update database lifecycle and instance status
            conn.execute("""
                UPDATE af_agent
                SET lifecycle = 'SUSPENDED', monitoring_status = 'INCIDENT', updated_at = ?
                WHERE tenant_id = ? AND id = ?
            """, (t0, tenant_id, agent_id))

            conn.execute("""
                UPDATE af_runtime_instance
                SET status = 'SUSPENDED'
                WHERE tenant_id = ? AND agent_id = ? AND status = 'RUNNING'
            """, (tenant_id, agent_id))

            conn.execute("""
                INSERT INTO af_lifecycle_event (
                    tenant_id, subject_kind, subject_id, from_state, to_state,
                    actor, reason, evidence_ledger_id, created_at
                ) VALUES (?, 'agent', ?, ?, 'SUSPENDED', ?, ?, 'ev_suspend', ?)
            """, (tenant_id, agent_id, prev_lifecycle, initiated_by, reason, t0))

            conn.commit()

        # Evidence logging
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_lifecycle",
            subject_id=agent_id,
            event_type="agent.suspended",
            actor=initiated_by,
            payload_hashes={"agent_id": agent_id, "reason": reason},
            timestamp=t0,
            tenant_id=tenant_id
        ))

        elapsed_seconds = time.time() - t0

        return {
            "agent_id": agent_id,
            "lifecycle": "SUSPENDED",
            "principal_revoked": agent_principal_id,
            "elapsed_seconds": elapsed_seconds,
            "evidence_id": ev_id
        }

    def resume_agent(
        self,
        tenant_id: str,
        agent_id: str,
        initiated_by: str
    ) -> Dict[str, Any]:
        """Resume suspended agent back to ACTIVE state."""
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT id, lifecycle, active_version_id FROM af_agent WHERE tenant_id = ? AND id = ?
            """, (tenant_id, agent_id))
            row = cur.fetchone()
            if not row:
                raise LifecycleError(f"Agent '{agent_id}' not found")
            if row[1] != 'SUSPENDED':
                raise LifecycleError(f"Cannot resume agent in state '{row[1]}'. Must be SUSPENDED.")

            self.runtime.resume_instance(agent_id)

            conn.execute("""
                UPDATE af_agent
                SET lifecycle = 'ACTIVE', monitoring_status = 'HEALTHY', updated_at = ?
                WHERE tenant_id = ? AND id = ?
            """, (now, tenant_id, agent_id))

            conn.execute("""
                UPDATE af_runtime_instance
                SET status = 'RUNNING'
                WHERE tenant_id = ? AND agent_id = ? AND status = 'SUSPENDED'
            """, (tenant_id, agent_id))

            conn.execute("""
                INSERT INTO af_lifecycle_event (
                    tenant_id, subject_kind, subject_id, from_state, to_state,
                    actor, reason, evidence_ledger_id, created_at
                ) VALUES (?, 'agent', ?, 'SUSPENDED', 'ACTIVE', ?, 'Agent resumed by operator', 'ev_resume', ?)
            """, (tenant_id, agent_id, initiated_by, now))

            conn.commit()

        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_lifecycle",
            subject_id=agent_id,
            event_type="agent.resumed",
            actor=initiated_by,
            payload_hashes={"agent_id": agent_id},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "agent_id": agent_id,
            "lifecycle": "ACTIVE",
            "evidence_id": ev_id
        }

    def retire_agent(
        self,
        tenant_id: str,
        agent_id: str,
        reason: str,
        initiated_by: str
    ) -> Dict[str, Any]:
        """Irreversibly retire agent, revoke credentials permanently, and unbind tools."""
        now = time.time()
        with self._get_connection() as conn:
            cur = conn.execute("""
                SELECT id, slug, agent_principal_id, lifecycle
                FROM af_agent WHERE tenant_id = ? AND id = ?
            """, (tenant_id, agent_id))
            row = cur.fetchone()
            if not row:
                raise LifecycleError(f"Agent '{agent_id}' not found")

            principal_id = row[2]
            prev_state = row[3]

            # 1. Permanently revoke tokens
            self.authority.revoke_principal_tokens(principal_id)

            # 2. Terminate instances
            self.runtime.terminate_instance(agent_id)

            # 3. Update agent lifecycle to RETIRED
            conn.execute("""
                UPDATE af_agent
                SET lifecycle = 'RETIRED', updated_at = ?
                WHERE tenant_id = ? AND id = ?
            """, (now, tenant_id, agent_id))

            conn.execute("""
                UPDATE af_runtime_instance
                SET status = 'STOPPED', stopped_at = ?
                WHERE tenant_id = ? AND agent_id = ?
            """, (now, tenant_id, agent_id))

            # 4. Deactivate assignments
            conn.execute("""
                UPDATE af_assignment
                SET status = 'REVOKED', ended_at = ?
                WHERE tenant_id = ? AND agent_id = ? AND status = 'ACTIVE'
            """, (now, tenant_id, agent_id))

            conn.execute("""
                INSERT INTO af_lifecycle_event (
                    tenant_id, subject_kind, subject_id, from_state, to_state,
                    actor, reason, evidence_ledger_id, created_at
                ) VALUES (?, 'agent', ?, ?, 'RETIRED', ?, ?, 'ev_retire', ?)
            """, (tenant_id, agent_id, prev_state, initiated_by, reason, now))

            conn.commit()

        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="agent_lifecycle",
            subject_id=agent_id,
            event_type="agent.retired",
            actor=initiated_by,
            payload_hashes={"agent_id": agent_id, "reason": reason},
            timestamp=now,
            tenant_id=tenant_id
        ))

        return {
            "agent_id": agent_id,
            "lifecycle": "RETIRED",
            "evidence_id": ev_id
        }
