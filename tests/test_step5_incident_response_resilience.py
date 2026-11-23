"""
Unit and Contract Tests for Step 5G: Incident Response & Security Resilience.
=============================================================================
Tests:
- Leaked Secret Containment: automated token revocation, session invalidation,
  vault secret rotation, and high-priority SIEM alert emission.
- Rogue Agent Quarantine: rogue agent isolation, SPIFFE workload credential revocation,
  in-flight workflow cancellation, and sealed forensic evidence in EvidenceLedger.
- Security Chaos Harness Drills:
  1. Vault Outage Fail-Closed Drill (Rule 41: zero plaintext fallback).
  2. Database Dynamic Credential Rotation Drill (zero-downtime rotation).
  3. Token Theft Cascade Revocation Drill (immediate family invalidation).
"""

import os
import pytest
import time
import uuid

from core.audit.siem_exporter import SIEMExporter
from core.distributed_coordination import coordination
from core.evidence_ledger import EvidenceLedger
from core.identity.api_keys import APIKeyManager
from core.identity.types import RoleTier
from core.identity.workload import WorkloadIdentityValidator
from core.incident.chaos_drills import SecurityChaosHarness
from core.incident.playbooks import (
    AgentQuarantinedError,
    AgentQuarantinePlaybook,
    IncidentContainmentResult,
    LeakedSecretPlaybook,
    QuarantineResult,
)
from core.ports.identity import SandboxIdentityProvider
from core.ports.secrets import SandboxSecretsProvider


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")
    ledger_path = str(tmp_path / "test_ledger.jsonl")
    monkeypatch.setenv("ZONATA_EVIDENCE_PATH", ledger_path)
    AgentQuarantinePlaybook.reset_quarantine()


class TestIncidentResponseAndResilience:
    """Verifies automated incident containment playbooks and security chaos drills."""

    def test_01_leaked_secret_automated_containment(self):
        """Playbook 1: Leaked secret containment revokes token, invalidates sessions, and rotates."""
        secrets_port = SandboxSecretsProvider()
        api_key_mgr = APIKeyManager()
        identity_port = SandboxIdentityProvider()
        siem_exporter = SIEMExporter()

        # Pre-populate a secret in the vault
        secret_key = "api/stripe_webhook_secret"
        tenant_id = "tenant_sigma_11"
        secrets_port.set_secret(secret_key, "whsec_leaked_value_0001", tenant_id=tenant_id)

        # Generate an API key associated with this actor
        raw_key, key_rec = api_key_mgr.generate_key(
            tenant_id=tenant_id,
            company_id="company_sigma",
            name="Stripe Webhook Ingestion",
            scopes=["webhooks:read", "payments:write"],
        )

        # Issue user session
        user_id = "usr_compromised_admin"
        at, rt = identity_port.issue_token(
            user_id=user_id,
            tenant_id=tenant_id,
            company_id="company_sigma",
            role=RoleTier.MANAGER.value,
            email="admin@sigma.example.com",
        )

        # Instantiate playbook
        playbook = LeakedSecretPlaybook(
            secrets_port=secrets_port,
            api_key_manager=api_key_mgr,
            identity_port=identity_port,
            siem_exporter=siem_exporter,
        )

        # Trigger automated containment
        res: IncidentContainmentResult = playbook.contain_leaked_secret(
            secret_id=secret_key,
            tenant_id=tenant_id,
            actor_id=user_id,
            reason="Token leaked in public GitHub repository",
            api_key_id=key_rec.key_id,
            auto_rotate=True,
        )

        assert res.status == "CONTAINED"
        assert res.api_key_revoked is True
        assert res.sessions_invalidated >= 1
        assert res.rotated_version is not None

        # Verify old API key is now revoked
        with pytest.raises(PermissionError, match="revoked"):
            api_key_mgr.verify_key(raw_key)

        # Verify refresh token is revoked
        rec = identity_port._refresh_family.get(rt)
        assert rec is not None and rec["revoked"] is True

        # Verify SIEM log chain
        assert len(siem_exporter._events) == 1
        event = siem_exporter._events[0]
        assert event.action == "CONTAIN_LEAKED_SECRET"
        assert "CEF:0|ZONATA|SovereignOS" in event.to_cef()

    def test_02_rogue_agent_quarantine_and_isolation(self, tmp_path):
        """Playbook 2: Rogue agent quarantine revokes SPIFFE, sets killswitch, and seals evidence."""
        ledger = EvidenceLedger(ledger_file=str(tmp_path / "quarantine_ledger.jsonl"))
        workload_val = WorkloadIdentityValidator()
        siem_exporter = SIEMExporter()

        playbook = AgentQuarantinePlaybook(
            evidence_ledger=ledger,
            workload_validator=workload_val,
            siem_exporter=siem_exporter,
        )

        agent_id = "agent_rogue_999"
        tenant_id = "tenant_omega_42"
        spiffe_id = "spiffe://zonata.internal/ns/tenant_omega_42/sa/agent_runtime"

        # Quarantine rogue agent
        q_res: QuarantineResult = playbook.quarantine_agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            reason="Agent attempted unauthorized model prompt injection to write root policy",
            spiffe_id=spiffe_id,
            active_workflow_ids=["wf_task_101", "wf_task_102"],
        )

        assert q_res.status == "QUARANTINED"
        assert q_res.spiffe_revoked is True
        assert q_res.workflows_cancelled == 2
        assert q_res.evidence_package_id is not None

        # Verify playbook quarantine barrier
        assert AgentQuarantinePlaybook.is_quarantined(agent_id) is True
        with pytest.raises(AgentQuarantinedError, match="barred from submitting action proposals"):
            AgentQuarantinePlaybook.assert_not_quarantined(agent_id)

        # Verify coordination killswitch is set
        is_killed, kill_reason = coordination.is_killed("AGENT", agent_id)
        assert is_killed is True
        assert "Security Incident Quarantine" in kill_reason

        # Verify SPIFFE workload identity access revoked
        assert workload_val.is_spiffe_revoked(spiffe_id) is True
        ident = workload_val.parse_spiffe_id(spiffe_id)
        assert workload_val.check_service_access(ident, "action_gateway") is False

        # Verify EvidenceLedger contains sealed package
        assert len(ledger.chain) >= 1
        sealed = ledger.chain[-1]
        assert sealed["evidence_id"] == q_res.evidence_package_id
        assert sealed["agent_id"] == agent_id

        # Verify CEF SIEM event
        assert len(siem_exporter._events) == 1
        event = siem_exporter._events[0]
        assert event.action == "QUARANTINE_ROGUE_AGENT"
        assert "CEF:0|ZONATA|SovereignOS" in event.to_cef()

    def test_03_chaos_drill_vault_outage_fail_closed(self):
        """Chaos Drill 1: Vault outage simulation verifies fail-closed and zero plaintext leak."""
        harness = SecurityChaosHarness()
        secrets_port = SandboxSecretsProvider()

        report = harness.drill_vault_outage_fail_closed(
            secrets_port=secrets_port,
            test_key="config/prod_encryption_master_key",
            tenant_id="tenant_drill_1",
        )

        assert report["status"] == "PASSED"
        assert report["failed_closed"] is True
        assert report["zero_plaintext_fallback"] is True
        assert report["recovered_on_unseal"] is True

    def test_04_chaos_drill_db_credential_rotation(self):
        """Chaos Drill 2: Database dynamic credential rotation generates distinct non-overlapping leases."""
        harness = SecurityChaosHarness()
        secrets_port = SandboxSecretsProvider()

        report = harness.drill_db_credential_rotation(
            secrets_port=secrets_port,
            role="app_worker",
            tenant_id="tenant_drill_2",
        )

        assert report["status"] == "PASSED"
        assert report["distinct_credentials"] is True
        assert report["zero_downtime_rotation"] is True
        assert report["lease_1"] != report["lease_2"]

    def test_05_chaos_drill_token_theft_cascade_revocation(self):
        """Chaos Drill 3: Token theft detection triggers immediate family cascade revocation."""
        harness = SecurityChaosHarness()
        id_port = SandboxIdentityProvider()

        report = harness.drill_token_theft_cascade_revocation(
            identity_port=id_port,
            user_id="usr_theft_victim_7",
            tenant_id="tenant_drill_3",
            company_id="co_drill_3",
        )

        assert report["status"] == "PASSED"
        assert report["reuse_detected"] is True
        assert report["cascade_family_revoked"] is True

    def test_06_mutation_check_unquarantined_agent_fails_verification(self):
        """Rule 8: Verify that an active non-quarantined agent does not raise AgentQuarantinedError."""
        active_agent_id = "agent_legitimate_001"
        assert AgentQuarantinePlaybook.is_quarantined(active_agent_id) is False
        # Should not raise
        AgentQuarantinePlaybook.assert_not_quarantined(active_agent_id)

        # Mutate to quarantined
        AgentQuarantinePlaybook._quarantined_agents.add(active_agent_id)
        with pytest.raises(AgentQuarantinedError):
            AgentQuarantinePlaybook.assert_not_quarantined(active_agent_id)
