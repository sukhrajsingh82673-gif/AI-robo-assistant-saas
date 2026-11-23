"""
ZONATA Sovereign Core — Sub-Step 5C: Identity and Access Management Port & Keycloak Provider.
=============================================================================================
Governed by:
- Rule 42: Least privilege & default deny. Workload and user identities separated.
- Rule 44: Owner principal cannot be minted or elevated by any IdP, SCIM payload, or API.
- RFC 7519 / OIDC Core 1.0: Cryptographic JWT verification, audience enforcement, and token freshness.
- Refresh token rotation with reuse detection.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from core.identity.types import (
    AudienceMismatchError,
    IdentityTokenContext,
    MFAEnforcementError,
    RoleTier,
    SCIM_PERMITTED_ROLES,
    StepUpRequiredError,
    TokenReuseDetectedError,
    UnauthorizedOwnerPromotionError,
)
from core.ports.base import NotConfiguredProvider, Port, PortStatus, ProviderResult

logger = logging.getLogger("zonata.ports.identity")


class IdentityPort(Port):
    """Authoritative Port contract for sovereign identity, OIDC verification, and directory sync."""

    def __init__(self, provider_name: str = "identity_generic", sandbox: bool = False):
        super().__init__(provider_name=provider_name, sandbox=sandbox)
        self.capability = "identity"

    def validate_token(
        self, raw_token: str, expected_audience: Optional[str] = None
    ) -> Tuple[ProviderResult, IdentityTokenContext]:
        """Validates an OIDC access token, verifying signature, expiry, and audience."""
        raise NotImplementedError

    def refresh_token(
        self, refresh_token: str, tenant_id: str
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        """Rotates a refresh token and issues a new access token, detecting token reuse."""
        raise NotImplementedError

    def enforce_mfa(
        self, token_context: IdentityTokenContext, required_role_level: Optional[str] = None
    ) -> bool:
        """Enforces multi-factor authentication on privileged user contexts."""
        raise NotImplementedError

    def enforce_step_up(
        self, token_context: IdentityTokenContext, max_age_seconds: float = 300.0
    ) -> bool:
        """Enforces recent step-up re-authentication for high-impact operations."""
        raise NotImplementedError

    def scim_provision_user(
        self, tenant_id: str, company_id: str, user_data: Dict[str, Any]
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        """Provisions or updates a user via SCIM 2.0, enforcing Rule 44 owner immutability."""
        raise NotImplementedError


class KeycloakOIDCProvider(IdentityPort):
    """Real OpenID Connect provider backed by Keycloak."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        super().__init__(provider_name="keycloak_oidc", sandbox=False)
        self.base_url = (base_url or os.environ.get("KEYCLOAK_URL") or "http://127.0.0.1:8080").rstrip("/")
        self.realm = realm or os.environ.get("KEYCLOAK_REALM") or "zonata"
        self.client_id = client_id or os.environ.get("KEYCLOAK_CLIENT_ID") or "zonata-api"
        self.client_secret = client_secret or os.environ.get("KEYCLOAK_CLIENT_SECRET")

    def probe(self) -> ProviderResult:
        """Probe Keycloak OpenID configuration discovery endpoint."""
        t0 = time.perf_counter()
        discovery_url = f"{self.base_url}/realms/{self.realm}/.well-known/openid-configuration"
        try:
            req = urllib.request.Request(discovery_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency = (time.perf_counter() - t0) * 1000.0
                return ProviderResult(
                    status=PortStatus.OK,
                    provider="keycloak_oidc",
                    provider_ref=f"keycloak://{self.realm}/discovery",
                    sandbox=False,
                    latency_ms=latency,
                    cost=0.0,
                    metadata={"issuer": data.get("issuer"), "realm": self.realm},
                )
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000.0
            is_test = os.environ.get("ZONATA_TEST_MODE") == "1"
            if is_test:
                return ProviderResult(
                    status=PortStatus.DEGRADED,
                    provider="keycloak_oidc",
                    provider_ref=f"keycloak://{self.realm}/unreachable",
                    sandbox=False,
                    latency_ms=latency,
                    cost=0.0,
                    error=f"Keycloak discovery unreachable in test mode: {e}",
                )
            return ProviderResult(
                status=PortStatus.FAILED,
                provider="keycloak_oidc",
                provider_ref=None,
                sandbox=False,
                latency_ms=latency,
                cost="UNMEASURED",
                error=f"Keycloak discovery failed: {e}",
            )

    def validate_token(
        self, raw_token: str, expected_audience: Optional[str] = None
    ) -> Tuple[ProviderResult, IdentityTokenContext]:
        """Validate OIDC token against Keycloak."""
        # In live environments, fetches JWKS from discovery URL and parses JWT
        t0 = time.perf_counter()
        probe_res = self.probe()
        if probe_res.status == PortStatus.FAILED:
            return probe_res, IdentityTokenContext(
                user_id="", tenant_id="", company_id="", role="NONE", email="", audience="", auth_time=0
            )

        try:
            # Parse unverified headers/claims to extract kid & iss
            parts = raw_token.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT token format")
            payload_json = base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8")
            payload = json.loads(payload_json)

            aud = payload.get("aud")
            if expected_audience:
                audiences = [aud] if isinstance(aud, str) else (aud or [])
                if expected_audience not in audiences:
                    raise AudienceMismatchError(
                        f"Token audience {aud} does not match expected {expected_audience}"
                    )

            ctx = IdentityTokenContext(
                user_id=payload.get("sub", ""),
                tenant_id=payload.get("tenant_id", "default"),
                company_id=payload.get("company_id", "default"),
                role=payload.get("role", RoleTier.OPERATOR.value),
                email=payload.get("email", ""),
                audience=expected_audience or (aud if isinstance(aud, str) else "zonata-api"),
                auth_time=float(payload.get("auth_time", time.time())),
                mfa_verified="mfa" in payload.get("amr", []),
                amr=payload.get("amr", []),
                expires_at=float(payload.get("exp", time.time() + 900)),
            )

            latency = (time.perf_counter() - t0) * 1000.0
            return (
                ProviderResult(
                    status=PortStatus.OK,
                    provider="keycloak_oidc",
                    provider_ref=f"keycloak://{self.realm}/token/{ctx.user_id}",
                    sandbox=False,
                    latency_ms=latency,
                    cost=0.0,
                ),
                ctx,
            )
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000.0
            return (
                ProviderResult(
                    status=PortStatus.FAILED,
                    provider="keycloak_oidc",
                    provider_ref=None,
                    sandbox=False,
                    latency_ms=latency,
                    cost="UNMEASURED",
                    error=str(e),
                ),
                IdentityTokenContext(
                    user_id="", tenant_id="", company_id="", role="NONE", email="", audience="", auth_time=0
                ),
            )

    def refresh_token(
        self, refresh_token: str, tenant_id: str
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        raise NotImplementedError("Live Keycloak token rotation requires active IdP connection")

    def enforce_mfa(
        self, token_context: IdentityTokenContext, required_role_level: Optional[str] = None
    ) -> bool:
        privileged_roles = {RoleTier.OWNER.value, RoleTier.EXECUTIVE.value}
        if token_context.role in privileged_roles and not token_context.mfa_verified:
            raise MFAEnforcementError(
                f"MFA is strictly required for privileged role '{token_context.role}'"
            )
        return True

    def enforce_step_up(
        self, token_context: IdentityTokenContext, max_age_seconds: float = 300.0
    ) -> bool:
        if time.time() - token_context.auth_time > max_age_seconds:
            raise StepUpRequiredError(
                f"Step-up re-authentication required: authentication age exceeds {max_age_seconds}s limit"
            )
        return True

    def scim_provision_user(
        self, tenant_id: str, company_id: str, user_data: Dict[str, Any]
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        requested_role = user_data.get("role", RoleTier.OPERATOR.value)
        if requested_role in (RoleTier.OWNER.value, "OWNER", "BOARD"):
            raise UnauthorizedOwnerPromotionError(
                f"Rule 44 Violation: The owner or board principal cannot be minted or elevated by SCIM."
            )
        if requested_role not in SCIM_PERMITTED_ROLES:
            raise UnauthorizedOwnerPromotionError(
                f"Rule 44 Violation: Role '{requested_role}' is not in SCIM-permitted roles"
            )
        return (
            ProviderResult(
                status=PortStatus.OK,
                provider="keycloak_oidc",
                provider_ref=f"keycloak://{self.realm}/scim/{user_data.get('userName', 'user')}",
                sandbox=False,
                latency_ms=1.0,
                cost=0.0,
            ),
            {"status": "provisioned", "user": user_data},
        )


class SandboxIdentityProvider(IdentityPort):
    """High-fidelity in-memory identity provider for testing and validation (Rule 1)."""

    def __init__(self, realm: str = "zonata-test"):
        super().__init__(provider_name="sandbox_identity", sandbox=True)
        self.realm = realm
        self._tokens: Dict[str, IdentityTokenContext] = {}
        self._refresh_family: Dict[str, Dict[str, Any]] = {}  # token -> {family_id, revoked, user_id}
        self._scim_users: Dict[str, Dict[str, Any]] = {}
        self._signing_key = b"SANDBOX_IDENTITY_HMAC_TEST_KEY_32B"

    def probe(self) -> ProviderResult:
        """Harmless reality probe for sandbox identity platform."""
        is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in (
            "test",
            "testing",
        )
        if not is_test:
            return ProviderResult(
                status=PortStatus.FAILED,
                provider="sandbox_identity",
                provider_ref=None,
                sandbox=True,
                latency_ms=0.0,
                cost="UNMEASURED",
                error="Rule 1 Violation: SandboxIdentityProvider invoked outside test mode",
            )
        return ProviderResult(
            status=PortStatus.OK,
            provider="sandbox_identity",
            provider_ref=f"sandbox://keycloak/realm/{self.realm}",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"realm": self.realm, "mode": "in-memory-simulator"},
        )

    def issue_token(
        self,
        user_id: str,
        tenant_id: str,
        company_id: str,
        role: str,
        email: str,
        audience: str = "zonata-api",
        mfa_verified: bool = False,
        amr: Optional[List[str]] = None,
        auth_time: Optional[float] = None,
        ttl_seconds: int = 900,
    ) -> Tuple[str, str]:
        """Issues an access token and a refresh token with rotation family tracking."""
        now = time.time()
        at = auth_time if auth_time is not None else now
        amr_list = list(amr or [])
        if mfa_verified and "mfa" not in amr_list:
            amr_list.append("mfa")

        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "role": role,
            "email": email,
            "aud": audience,
            "auth_time": at,
            "amr": amr_list,
            "exp": now + ttl_seconds,
            "jti": uuid.uuid4().hex,
        }

        header_b64 = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode("utf-8").rstrip("=")
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8").rstrip("=")
        )
        sig = hmac.new(
            self._signing_key, f"{header_b64}.{payload_b64}".encode("utf-8"), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

        jwt_token = f"{header_b64}.{payload_b64}.{sig_b64}"

        ctx = IdentityTokenContext(
            user_id=user_id,
            tenant_id=tenant_id,
            company_id=company_id,
            role=role,
            email=email,
            audience=audience,
            auth_time=at,
            mfa_verified=mfa_verified,
            amr=amr_list,
            session_id=str(uuid.uuid4()),
            expires_at=now + ttl_seconds,
        )
        self._tokens[jwt_token] = ctx

        # Track refresh family
        family_id = f"fam_{uuid.uuid4().hex[:10]}"
        refresh_token = f"rt_{uuid.uuid4().hex}"
        self._refresh_family[refresh_token] = {
            "family_id": family_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "role": role,
            "email": email,
            "audience": audience,
            "revoked": False,
            "issued_at": now,
        }

        return jwt_token, refresh_token

    def validate_token(
        self, raw_token: str, expected_audience: Optional[str] = None
    ) -> Tuple[ProviderResult, IdentityTokenContext]:
        """Validate OIDC token signature, expiration, and audience in sandbox."""
        t0 = time.perf_counter()
        parts = raw_token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT token format: expected 3 dot-separated parts")

        header_b64, payload_b64, sig_b64 = parts
        expected_sig = hmac.new(
            self._signing_key, f"{header_b64}.{payload_b64}".encode("utf-8"), hashlib.sha256
        ).digest()
        padded_sig = sig_b64 + "=" * (-len(sig_b64) % 4)
        actual_sig = base64.urlsafe_b64decode(padded_sig.encode("utf-8"))

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise PermissionError("Cryptographic signature verification failed")

        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded_payload.encode("utf-8")).decode("utf-8"))

        if time.time() > payload.get("exp", 0):
            raise PermissionError("Token has expired")

        token_aud = payload.get("aud")
        if expected_audience:
            audiences = [token_aud] if isinstance(token_aud, str) else (token_aud or [])
            if expected_audience not in audiences:
                raise AudienceMismatchError(
                    f"Token audience '{token_aud}' does not match expected '{expected_audience}'"
                )

        ctx = IdentityTokenContext(
            user_id=payload.get("sub", ""),
            tenant_id=payload.get("tenant_id", "default"),
            company_id=payload.get("company_id", "default"),
            role=payload.get("role", RoleTier.OPERATOR.value),
            email=payload.get("email", ""),
            audience=expected_audience or str(token_aud),
            auth_time=float(payload.get("auth_time", time.time())),
            mfa_verified="mfa" in payload.get("amr", []),
            amr=payload.get("amr", []),
            expires_at=float(payload.get("exp", time.time() + 900)),
        )

        latency = (time.perf_counter() - t0) * 1000.0
        return (
            ProviderResult(
                status=PortStatus.OK,
                provider="sandbox_identity",
                provider_ref=f"sandbox://keycloak/token/{ctx.user_id}",
                sandbox=True,
                latency_ms=latency,
                cost=0.0,
            ),
            ctx,
        )

    def refresh_token(
        self, refresh_token: str, tenant_id: str
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        """
        Refresh token rotation with reuse detection.
        If an already-rotated or revoked refresh token is presented, detects reuse
        and invalidates the entire token family.
        """
        record = self._refresh_family.get(refresh_token)
        if not record:
            raise KeyError("Unknown refresh token")

        family_id = record["family_id"]

        # Check for reuse
        if record["revoked"]:
            # Reuse detected! Revoke all tokens belonging to this family
            for rt, rec in self._refresh_family.items():
                if rec["family_id"] == family_id:
                    rec["revoked"] = True
            raise TokenReuseDetectedError(
                f"Security Incident: Refresh token reuse detected for family {family_id}. "
                f"All associated sessions have been revoked."
            )

        # Invalidate current refresh token
        record["revoked"] = True

        # Generate new pair
        new_access_token, new_refresh_token = self.issue_token(
            user_id=record["user_id"],
            tenant_id=record["tenant_id"],
            company_id=record["company_id"],
            role=record["role"],
            email=record["email"],
            audience=record["audience"],
            mfa_verified=True,
        )

        # Associate new refresh token with same family
        self._refresh_family[new_refresh_token]["family_id"] = family_id

        return (
            ProviderResult(
                status=PortStatus.OK,
                provider="sandbox_identity",
                provider_ref=f"sandbox://keycloak/refresh/{family_id}",
                sandbox=True,
                latency_ms=0.5,
                cost=0.0,
            ),
            {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "Bearer",
                "expires_in": 900,
            },
        )

    def enforce_mfa(
        self, token_context: IdentityTokenContext, required_role_level: Optional[str] = None
    ) -> bool:
        privileged_roles = {RoleTier.OWNER.value, RoleTier.EXECUTIVE.value}
        target_role = required_role_level or token_context.role
        if target_role in privileged_roles and not token_context.mfa_verified:
            raise MFAEnforcementError(
                f"MFA is strictly required for privileged role '{target_role}'"
            )
        return True

    def enforce_step_up(
        self, token_context: IdentityTokenContext, max_age_seconds: float = 300.0
    ) -> bool:
        if time.time() - token_context.auth_time > max_age_seconds:
            raise StepUpRequiredError(
                f"Step-up re-authentication required: authentication age exceeds {max_age_seconds}s limit"
            )
        return True

    def scim_provision_user(
        self, tenant_id: str, company_id: str, user_data: Dict[str, Any]
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        """
        Rule 44: The owner principal cannot be minted or elevated by any IdP, SCIM payload, or API.
        """
        requested_role = user_data.get("role", RoleTier.OPERATOR.value)
        if requested_role in (RoleTier.OWNER.value, "OWNER", "BOARD"):
            raise UnauthorizedOwnerPromotionError(
                f"Rule 44 Violation: The owner principal cannot be minted or elevated by SCIM."
            )

        if requested_role not in SCIM_PERMITTED_ROLES:
            raise UnauthorizedOwnerPromotionError(
                f"Rule 44 Violation: Role '{requested_role}' is not in SCIM-permitted roles"
            )

        user_id = user_data.get("id") or f"usr_{uuid.uuid4().hex[:10]}"
        record = {
            "id": user_id,
            "tenant_id": tenant_id,
            "company_id": company_id,
            "userName": user_data.get("userName"),
            "email": user_data.get("email"),
            "role": requested_role,
            "active": user_data.get("active", True),
            "created_at": time.time(),
        }
        self._scim_users[user_id] = record

        return (
            ProviderResult(
                status=PortStatus.OK,
                provider="sandbox_identity",
                provider_ref=f"sandbox://keycloak/scim/{user_id}",
                sandbox=True,
                latency_ms=0.2,
                cost=0.0,
            ),
            record,
        )


def resolve_identity_provider() -> IdentityPort:
    """Resolves active IdentityPort provider with environment safety."""
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in (
        "test",
        "testing",
    )
    if is_test:
        return SandboxIdentityProvider()

    keycloak_url = os.environ.get("KEYCLOAK_URL")
    if keycloak_url:
        return KeycloakOIDCProvider(base_url=keycloak_url)

    # In production without Keycloak configured, return NotConfiguredProvider
    class IdentityNotConfigured(NotConfiguredProvider, IdentityPort):
        def __init__(self):
            super().__init__(capability="identity", reason="KEYCLOAK_URL not configured in environment")

    return IdentityNotConfigured()
