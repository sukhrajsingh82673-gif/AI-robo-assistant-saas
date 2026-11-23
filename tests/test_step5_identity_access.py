"""
ZONATA Sovereign Core — Sub-Step 5C: Identity, Access & Governance Test Suite.
==============================================================================
Verifies:
- Rule 42: Least privilege, default deny, machine interactive login forbidden.
- Rule 44: Owner immutability. No SCIM or API owner elevation. Dual-control
  cooling-off transfers. Sealed evidence logging. Multi-channel recovery.
- OIDC JWT validation, audience enforcement, refresh token reuse detection.
- Customer integration API keys with salted hashes and scopes.
- SPIFFE workload identities and GitHub App scoped tokens.
"""

import os
import time
import pytest

from core.identity.types import (
    AudienceMismatchError,
    DualControlApprovalRequiredError,
    IdentityTokenContext,
    MachineInteractiveLoginForbiddenError,
    MFAEnforcementError,
    OwnershipTransferCoolingOffError,
    RecoveryForbiddenByEmailAloneError,
    RoleTier,
    StepUpRequiredError,
    TokenReuseDetectedError,
    UnauthorizedOwnerPromotionError,
    WorkloadIdentity,
)
from core.identity.ownership import OwnershipGovernance, OwnershipTransferRecord
from core.identity.api_keys import APIKeyManager
from core.identity.workload import GitHubAppTokenManager, WorkloadIdentityValidator
from core.ports.base import PortStatus
from core.ports.identity import (
    IdentityPort,
    KeycloakOIDCProvider,
    SandboxIdentityProvider,
    resolve_identity_provider,
)
from core.capability_probe import probe_identity


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestIdentityAccessGovernance:

    def test_01_oidc_token_validation_lifecycle(self):
        """OIDC token validation in SandboxIdentityProvider verifies signature and claims."""
        provider = SandboxIdentityProvider()
        token, refresh_tok = provider.issue_token(
            user_id="usr_alice_123",
            tenant_id="ten_alpha",
            company_id="cmp_alpha",
            role=RoleTier.OPERATOR.value,
            email="alice@alpha.corp",
            audience="zonata-api",
            mfa_verified=True,
        )

        res, ctx = provider.validate_token(token, expected_audience="zonata-api")
        assert res.status == PortStatus.OK
        assert ctx.user_id == "usr_alice_123"
        assert ctx.tenant_id == "ten_alpha"
        assert ctx.role == RoleTier.OPERATOR.value
        assert ctx.mfa_verified is True

        # Malformed token check
        with pytest.raises(ValueError, match="Invalid JWT token format"):
            provider.validate_token("not.a.valid.jwt.token")

        # Cryptographic tamper check
        parts = token.split(".")
        tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature"
        with pytest.raises(PermissionError, match="Cryptographic signature verification failed"):
            provider.validate_token(tampered_token)

    def test_02_audience_mismatch_rejected(self):
        """Rule 42: Presenting a token with mismatched audience must be rejected."""
        provider = SandboxIdentityProvider()
        token, _ = provider.issue_token(
            user_id="usr_bob_456",
            tenant_id="ten_beta",
            company_id="cmp_beta",
            role=RoleTier.OPERATOR.value,
            email="bob@beta.corp",
            audience="zonata-reporting-service",
        )

        with pytest.raises(AudienceMismatchError, match="does not match expected 'zonata-api'"):
            provider.validate_token(token, expected_audience="zonata-api")

    def test_03_refresh_token_rotation_and_reuse_detection(self):
        """Rotates refresh tokens and raises TokenReuseDetectedError if an old token is reused."""
        provider = SandboxIdentityProvider()
        _, rt1 = provider.issue_token(
            user_id="usr_charlie_789",
            tenant_id="ten_gamma",
            company_id="cmp_gamma",
            role=RoleTier.OPERATOR.value,
            email="charlie@gamma.corp",
        )

        # Legitimate rotation
        res, new_pair = provider.refresh_token(rt1, tenant_id="ten_gamma")
        assert res.status == PortStatus.OK
        rt2 = new_pair["refresh_token"]
        assert rt2 != rt1

        # Attacker replays rt1 (reuse detection)
        with pytest.raises(TokenReuseDetectedError, match="Refresh token reuse detected"):
            provider.refresh_token(rt1, tenant_id="ten_gamma")

        # Legitimate rt2 is now also invalidated due to family revocation
        with pytest.raises(TokenReuseDetectedError, match="Refresh token reuse detected"):
            provider.refresh_token(rt2, tenant_id="ten_gamma")

    def test_04_mfa_enforced_on_privileged_roles(self):
        """Privileged roles (OWNER, EXECUTIVE) require MFA enforcement."""
        provider = SandboxIdentityProvider()

        # Non-MFA Owner context
        unverified_owner_tok, _ = provider.issue_token(
            user_id="usr_owner_1",
            tenant_id="ten_delta",
            company_id="cmp_delta",
            role=RoleTier.OWNER.value,
            email="owner@delta.corp",
            mfa_verified=False,
        )
        _, owner_ctx = provider.validate_token(unverified_owner_tok)
        with pytest.raises(MFAEnforcementError, match="MFA is strictly required for privileged role 'OWNER'"):
            provider.enforce_mfa(owner_ctx)

        # MFA Verified Owner context
        verified_owner_tok, _ = provider.issue_token(
            user_id="usr_owner_1",
            tenant_id="ten_delta",
            company_id="cmp_delta",
            role=RoleTier.OWNER.value,
            email="owner@delta.corp",
            mfa_verified=True,
        )
        _, verified_ctx = provider.validate_token(verified_owner_tok)
        assert provider.enforce_mfa(verified_ctx) is True

        # Non-privileged role doesn't require MFA for basic access
        op_tok, _ = provider.issue_token(
            user_id="usr_op_1",
            tenant_id="ten_delta",
            company_id="cmp_delta",
            role=RoleTier.OPERATOR.value,
            email="op@delta.corp",
            mfa_verified=False,
        )
        _, op_ctx = provider.validate_token(op_tok)
        assert provider.enforce_mfa(op_ctx) is True

    def test_05_step_up_authentication_enforcement(self):
        """Enforces recent authentication for high-impact actions."""
        provider = SandboxIdentityProvider()

        # Auth from 400 seconds ago (older than 300s limit)
        stale_auth_time = time.time() - 400.0
        tok_stale, _ = provider.issue_token(
            user_id="usr_exec_1",
            tenant_id="ten_eps",
            company_id="cmp_eps",
            role=RoleTier.EXECUTIVE.value,
            email="exec@eps.corp",
            auth_time=stale_auth_time,
        )
        _, stale_ctx = provider.validate_token(tok_stale)
        with pytest.raises(StepUpRequiredError, match="Step-up re-authentication required"):
            provider.enforce_step_up(stale_ctx, max_age_seconds=300.0)

        # Fresh auth (10s ago)
        tok_fresh, _ = provider.issue_token(
            user_id="usr_exec_1",
            tenant_id="ten_eps",
            company_id="cmp_eps",
            role=RoleTier.EXECUTIVE.value,
            email="exec@eps.corp",
            auth_time=time.time() - 10.0,
        )
        _, fresh_ctx = provider.validate_token(tok_fresh)
        assert provider.enforce_step_up(fresh_ctx, max_age_seconds=300.0) is True

    def test_06_scim_owner_promotion_forbidden_rule44(self):
        """Rule 44: SCIM payload cannot mint or elevate any principal to OWNER or BOARD."""
        provider = SandboxIdentityProvider()

        # Attempt to provision OWNER via SCIM
        with pytest.raises(UnauthorizedOwnerPromotionError, match="Rule 44 Violation"):
            provider.scim_provision_user(
                tenant_id="ten_zeta",
                company_id="cmp_zeta",
                user_data={"userName": "mallory", "role": "OWNER", "email": "mallory@zeta.corp"},
            )

        # Attempt to provision BOARD via SCIM
        with pytest.raises(UnauthorizedOwnerPromotionError, match="Rule 44 Violation"):
            provider.scim_provision_user(
                tenant_id="ten_zeta",
                company_id="cmp_zeta",
                user_data={"userName": "mallory", "role": "BOARD", "email": "mallory@zeta.corp"},
            )

        # Permitted SCIM role succeeds
        res, data = provider.scim_provision_user(
            tenant_id="ten_zeta",
            company_id="cmp_zeta",
            user_data={"userName": "david", "role": RoleTier.OPERATOR.value, "email": "david@zeta.corp"},
        )
        assert res.status == PortStatus.OK
        assert data["role"] == RoleTier.OPERATOR.value

    def test_07_dual_control_ownership_transfer_and_cooling_off(self):
        """Rule 44: Ownership transfer requires dual control, cooling-off period, and evidence ledger."""
        gov = OwnershipGovernance()

        # 1. Initiate transfer
        record = gov.initiate_transfer(
            tenant_id="ten_corp",
            current_owner_id="usr_founder_1",
            target_owner_id="usr_successor_2",
            reason="Succession plan 2026",
            cooling_off_seconds=3600.0,  # 1 hour
        )
        assert record.status == "PENDING"
        assert len(record.approvals) == 1

        # 2. Cannot execute with only 1 approval
        with pytest.raises(DualControlApprovalRequiredError, match="at least 2 distinct approvals"):
            gov.execute_transfer(record.request_id, executor_id="usr_founder_1")

        # 3. Target owner cannot self-approve
        with pytest.raises(DualControlApprovalRequiredError, match="Target owner cannot self-approve"):
            gov.approve_transfer(
                request_id=record.request_id,
                approver_id="usr_successor_2",
                approver_role="EXECUTIVE",
                mfa_verified=True,
            )

        # 4. Independent board member approves
        updated = gov.approve_transfer(
            request_id=record.request_id,
            approver_id="usr_board_member_3",
            approver_role="BOARD",
            mfa_verified=True,
        )
        assert updated.status == "APPROVED"
        assert len(updated.approvals) == 2

        # 5. Premature execution blocked by cooling-off timer
        with pytest.raises(OwnershipTransferCoolingOffError, match="Cooling-off period in effect"):
            gov.execute_transfer(record.request_id, executor_id="usr_founder_1")

        # 6. Execute after cooling-off elapses
        future_time = record.initiated_at + 3601.0
        final_record = gov.execute_transfer(
            record.request_id, executor_id="usr_founder_1", current_time=future_time
        )
        assert final_record.status == "EXECUTED"
        assert final_record.executed_at == future_time
        assert final_record.evidence_package_id is not None

    def test_08_multi_channel_recovery_rejects_email_alone_rule44(self):
        """Rule 44: Multi-channel recovery rejects email alone."""
        # Email alone fails
        with pytest.raises(RecoveryForbiddenByEmailAloneError, match="Rule 44 Violation.*Email alone is forbidden"):
            OwnershipGovernance.verify_recovery_channels(["email"])

        with pytest.raises(RecoveryForbiddenByEmailAloneError, match="Rule 44 Violation.*Email alone is forbidden"):
            OwnershipGovernance.verify_recovery_channels(["EMAIL "])

        # Weak secondary factor without cryptographic authenticator fails
        with pytest.raises(RecoveryForbiddenByEmailAloneError, match="Secondary recovery channel must be a strong"):
            OwnershipGovernance.verify_recovery_channels(["email", "security_question"])

        # Email + FIDO2 passkey succeeds
        assert OwnershipGovernance.verify_recovery_channels(["email", "fido2"]) is True
        # Email + Hardware key succeeds
        assert OwnershipGovernance.verify_recovery_channels(["email", "hardware_key"]) is True

    def test_09_customer_api_key_lifecycle_and_scopes(self):
        """Customer API keys use salted SHA-256 hashes, prefix lookup, and scope enforcement."""
        mgr = APIKeyManager()

        plain_key, record = mgr.generate_key(
            tenant_id="ten_api",
            company_id="cmp_api",
            name="Production Stripe Sync",
            scopes=["payments:read", "invoices:write"],
            is_live=True,
            expires_in_seconds=3600.0,
        )

        assert plain_key.startswith("zonata_live_sk_")
        assert record.hashed_secret != plain_key

        # Valid verification with granted scope
        verified = mgr.verify_key(plain_key, required_scope="payments:read")
        assert verified.key_id == record.key_id
        assert verified.last_used_at is not None

        # Verification with ungranted scope fails
        with pytest.raises(PermissionError, match="lacks required scope: admin:all"):
            mgr.verify_key(plain_key, required_scope="admin:all")

        # Revocation
        assert mgr.revoke_key(record.key_id, tenant_id="ten_api") is True
        with pytest.raises(PermissionError, match="API key has been revoked"):
            mgr.verify_key(plain_key)

    def test_10_workload_identity_and_machine_interactive_forbidden(self):
        """Rule 42: SPIFFE workload identities parsed and machine interactive login strictly forbidden."""
        validator = WorkloadIdentityValidator(trust_domain="zonata.internal")

        spiffe_id = "spiffe://zonata.internal/ns/ten_finance/sa/agent_runtime"
        ident = validator.parse_spiffe_id(spiffe_id)
        assert ident.tenant_id == "ten_finance"
        assert ident.service_name == "agent_runtime"
        assert ident.is_machine is True

        # Service-to-service ACL checks
        assert validator.check_service_access(ident, "action_gateway") is True
        assert validator.check_service_access(ident, "unauthorized_internal_db") is False

        # Rule 42: Machine identities cannot acquire interactive human sessions
        with pytest.raises(MachineInteractiveLoginForbiddenError, match="Rule 42 Violation.*cannot acquire interactive"):
            validator.assert_not_machine_interactive(ident)

    def test_11_github_app_installation_token_validation(self):
        """Issues and verifies scoped GitHub App installation tokens."""
        mgr = GitHubAppTokenManager()

        token_obj = mgr.issue_installation_token(
            installation_id="inst_123456",
            repositories=["sukhrajsingh82673-gif/AI-robo-assistant-saas"],
            permissions={"pull_requests": "write", "contents": "read"},
            ttl_seconds=1800,
        )

        # Successful verification
        verified = mgr.verify_token(
            token_obj.token,
            required_repo="sukhrajsingh82673-gif/AI-robo-assistant-saas",
            required_perm=("pull_requests", "write"),
        )
        assert verified.installation_id == "inst_123456"

        # Out-of-scope repo fails
        with pytest.raises(PermissionError, match="not authorized for repository"):
            mgr.verify_token(token_obj.token, required_repo="other-org/other-repo")

        # Insufficient permission level fails
        with pytest.raises(PermissionError, match="insufficient permission level"):
            mgr.verify_token(token_obj.token, required_perm=("pull_requests", "admin"))

    def test_12_probe_identity_reality(self):
        """Reality probe for identity capability reports OK with provider_ref in test mode."""
        res = probe_identity()
        assert res.is_success()
        assert res.status == PortStatus.OK
        assert res.provider == "sandbox_identity"
        assert res.provider_ref.startswith("sandbox://keycloak/realm/")
        assert res.latency_ms >= 0.0
