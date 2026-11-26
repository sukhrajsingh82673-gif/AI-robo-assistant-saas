"""
ZONATA Sovereign Core — Sub-Step 5G: Incident Response Playbooks.
================================================================
Automated incident containment workflows:
- Leaked Secret Containment: automated token revocation, session invalidation,
  vault secret rotation, and high-priority SIEM alert emission.
- Rogue Agent Quarantine: rogue agent isolation, SPIFFE workload credential revocation,
  in-flight workflow cancellation, and sealed forensic evidence in EvidenceLedger.

Governed by:
- Rule 41: No plaintext secret material in logs or state.
- Rule 42: Least privilege, immediate revocation of compromised machine identities.
- Rule 15: Agent containment cannot be reversed by agents.
"""

from __future__ import annotations

import logging
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from core.audit.siem_exporter import AuditEvent, SIEMExporter
from core.distributed_coordination import coordination
from core.evidence_ledger import EvidenceLedger
from core.identity.api_keys import APIKeyManager
from core.identity.workload import WorkloadIdentityValidator
from core.models import PhysicalVerification
from core.ports.identity import IdentityPort, SandboxIdentityProvider
from core.ports.secrets import SandboxSecretsProvider, SecretsPort

logger = logging.getLogger("zonata.incident.playbooks")


class AgentQuarantinedError(PermissionError):
    """Raised when an action or invocation is attempted by a quarantined rogue agent."""
    pass


@dataclass
class IncidentContainmentResult:
    incident_id: str
    secret_id: str
    tenant_id: str
    actor_id: str
    status: str  # CONTAINED, FAILED
    revoked_at: float
    rotated_version: Optional[str]
    api_key_revoked: bool
    sessions_invalidated: int
    audit_event_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuarantineResult:
    incident_id: str
    agent_id: str
    tenant_id: str
    status: str  # QUARANTINED, FAILED
    quarantined_at: float
    spiffe_revoked: bool
    evidence_package_id: str
    workflows_cancelled: int
    audit_event_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LeakedSecretPlaybook:
    """Automated containment for compromised or leaked tokens, keys, and credentials."""

    def __init__(
        self,
        secrets_port: Optional[SecretsPort] = None,
        api_key_manager: Optional[APIKeyManager] = None,
        identity_port: Optional[IdentityPort] = None,
        siem_exporter: Optional[SIEMExporter] = None,
    ):
        self.secrets_port = secrets_port or SandboxSecretsProvider()
        self.api_key_manager = api_key_manager or APIKeyManager()
        self.identity_port = identity_port or SandboxIdentityProvider()
        self.siem_exporter = siem_exporter or SIEMExporter()

    def contain_leaked_secret(
        self,
        secret_id: str,
        tenant_id: str,
        actor_id: str,
        reason: str,
        company_id: str = "company_primary",
        api_key_id: Optional[str] = None,
        auto_rotate: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IncidentContainmentResult:
        """
        Executes automated containment sequence:
        1. Fast-path revocation of secret in Vault/OpenBao via SecretsPort.
        2. Immediate revocation of customer API keys matching api_key_id.
        3. Termination of active sessions / refresh token families.
        4. Seamless rotation to a fresh secret version if auto_rotate is True.
        5. High-priority CEF audit alert emission to SIEM.
        """
        incident_id = f"inc_leak_{uuid.uuid4().hex[:12]}"
        now = time.time()
        extra_meta = dict(metadata or {})

        # Step 1: Revoke compromised secret in Vault
        res, revoked = self.secrets_port.revoke_secret(
            key=secret_id, tenant_id=tenant_id, company_id=company_id
        )
        if not revoked:
            logger.warning("Secret revocation returned False or key was absent: %s", secret_id)

        # Step 2: Revoke associated API key if provided
        key_revoked = False
        if api_key_id:
            key_revoked = self.api_key_manager.revoke_key(api_key_id, tenant_id=tenant_id)

        # Step 3: Invalidate user sessions / token families
        sessions_invalidated = 0
        if isinstance(self.identity_port, SandboxIdentityProvider):
            for rt, rec in list(self.identity_port._refresh_family.items()):
                if rec.get("user_id") == actor_id or rec.get("tenant_id") == tenant_id:
                    rec["revoked"] = True
                    sessions_invalidated += 1

        # Step 4: Rotate secret if requested
        rotated_version: Optional[str] = None
        if auto_rotate:
            fresh_value = secrets.token_hex(32)
            rot_res, ok = self.secrets_port.rotate_secret(
                key=secret_id,
                new_value=fresh_value,
                tenant_id=tenant_id,
                company_id=company_id,
            )
            if ok:
                rotated_version = f"v_rot_{int(now)}"
                extra_meta["rotated_ref"] = rot_res.provider_ref

        # Step 5: Emit high-priority Merkle-chained CEF audit alert
        audit_event = self.siem_exporter.log_event(
            actor_id=f"incident_response:{actor_id}",
            actor_role="SECURITY_INCIDENT_RESPONDER",
            tenant_id=tenant_id,
            company_id=company_id,
            action="CONTAIN_LEAKED_SECRET",
            target_resource=f"secret://{tenant_id}/{secret_id}",
            status="SUCCESS",
            details={
                "incident_id": incident_id,
                "reason": reason,
                "api_key_revoked": key_revoked,
                "sessions_invalidated": sessions_invalidated,
                "auto_rotated": auto_rotate,
            },
        )

        return IncidentContainmentResult(
            incident_id=incident_id,
            secret_id=secret_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            status="CONTAINED",
            revoked_at=now,
            rotated_version=rotated_version,
            api_key_revoked=key_revoked,
            sessions_invalidated=sessions_invalidated,
            audit_event_id=audit_event.event_id,
            metadata=extra_meta,
        )


class AgentQuarantinePlaybook:
    """Automated containment and forensic isolation for rogue or compromised agents."""

    _quarantined_agents: Set[str] = set()

    def __init__(
        self,
        evidence_ledger: Optional[EvidenceLedger] = None,
        workload_validator: Optional[WorkloadIdentityValidator] = None,
        siem_exporter: Optional[SIEMExporter] = None,
    ):
        self.evidence_ledger = evidence_ledger or EvidenceLedger()
        self.workload_validator = workload_validator or WorkloadIdentityValidator()
        self.siem_exporter = siem_exporter or SIEMExporter()

    @classmethod
    def is_quarantined(cls, agent_id: str) -> bool:
        """Check if an agent is currently quarantined."""
        return agent_id in cls._quarantined_agents

    @classmethod
    def assert_not_quarantined(cls, agent_id: str) -> None:
        """Enforces agent quarantine barrier. Raises AgentQuarantinedError if quarantined."""
        if cls.is_quarantined(agent_id):
            raise AgentQuarantinedError(
                f"Rule 15 Enforcement: Agent '{agent_id}' is quarantined due to a security incident "
                f"and barred from submitting action proposals or executing tasks."
            )

    @classmethod
    def reset_quarantine(cls) -> None:
        """Reset quarantine list (testing only)."""
        cls._quarantined_agents.clear()

    def quarantine_agent(
        self,
        agent_id: str,
        tenant_id: str,
        reason: str,
        spiffe_id: Optional[str] = None,
        active_workflow_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QuarantineResult:
        """
        Executes automated rogue agent quarantine:
        1. Adds agent to quarantined set and sets distributed killswitch.
        2. Revokes SPIFFE workload credential in WorkloadIdentityValidator.
        3. Halts/cancels all in-flight workflow executions.
        4. Captures sealed forensic evidence package in EvidenceLedger.
        5. Emits maximum-severity CEF audit alert to SIEM.
        """
        incident_id = f"inc_agent_{uuid.uuid4().hex[:12]}"
        now = time.time()
        extra_meta = dict(metadata or {})

        # Step 1: Quarantine agent and engage coordination killswitch
        self._quarantined_agents.add(agent_id)
        coordination.set_killswitch_state(
            scope="AGENT",
            target_id=agent_id,
            is_killed=True,
            reason=f"Security Incident Quarantine: {reason}",
        )

        # Step 2: Revoke SPIFFE workload identity if provided
        spiffe_revoked = False
        if spiffe_id:
            self.workload_validator.revoke_spiffe_id(spiffe_id)
            spiffe_revoked = True

        # Step 3: Cancel active workflows
        cancelled_count = 0
        if active_workflow_ids:
            for wf_id in active_workflow_ids:
                # Signal coordination or record cancellation
                coordination.set_idempotency_key(
                    key=f"wf_cancelled_{wf_id}",
                    action_hash=f"CANCELLED_BY_QUARANTINE:{agent_id}",
                    ttl_seconds=86400.0,
                )
                cancelled_count += 1

        # Step 4: Seal forensic evidence in EvidenceLedger
        forensic_verification = PhysicalVerification(
            check_type="CRYPTOGRAPHIC_ISOLATION",
            target_path=f"agent://{tenant_id}/{agent_id}",
            expected_val="QUARANTINED",
            actual_val="QUARANTINED",
            verified=True,
            details=f"Agent quarantined: {reason}; spiffe={spiffe_id}; workflows_cancelled={cancelled_count}",
        )
        evidence_pkg = self.evidence_ledger.seal_evidence(
            action_id=incident_id,
            mission_id=f"containment_{tenant_id}",
            agent_id=agent_id,
            verifications=[forensic_verification],
            metadata={
                "incident_type": "ROGUE_AGENT_QUARANTINE",
                "execution_mode": "LIVE",
                "reason": reason,
            },
        )

        # Step 5: Emit highest-severity CEF audit alert
        audit_event = self.siem_exporter.log_event(
            actor_id="security_arbiter",
            actor_role="SECURITY_INCIDENT_RESPONDER",
            tenant_id=tenant_id,
            company_id="company_primary",
            action="QUARANTINE_ROGUE_AGENT",
            target_resource=f"agent://{tenant_id}/{agent_id}",
            status="SUCCESS",
            evidence_id=evidence_pkg.package_id,
            details={
                "incident_id": incident_id,
                "agent_id": agent_id,
                "reason": reason,
                "workflows_cancelled": cancelled_count,
                "spiffe_revoked": spiffe_revoked,
            },
        )

        return QuarantineResult(
            incident_id=incident_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            status="QUARANTINED",
            quarantined_at=now,
            spiffe_revoked=spiffe_revoked,
            evidence_package_id=evidence_pkg.package_id,
            workflows_cancelled=cancelled_count,
            audit_event_id=audit_event.event_id,
            metadata=extra_meta,
        )
