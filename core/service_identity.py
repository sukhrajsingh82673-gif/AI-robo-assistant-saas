"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V5 — Enterprise Service Identity & Machine-to-Machine (M2M) Security Plane
Validates cryptographically attributable identities across internal microservices:
API -> Worker -> Temporal -> PostgreSQL -> Redis -> Object Storage -> External SaaS.

Enforces:
  - Expired credential rejection
  - Revoked credential rejection
  - Wrong audience rejection
  - Wrong issuer rejection
  - Wrong tenant rejection
  - Wrong service scope rejection
  - Replay attack rejection (nonce / jti cache)
"""

import time
import json
import uuid
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from core.distributed_coordination import coordination
from core.evidence_service import evidence_service

logger = logging.getLogger("zonata.service.identity")

class ServiceSecurityViolation(PermissionError):
    """Raised when an M2M service call fails cryptographic verification."""
    pass

@dataclass
class ServiceTokenClaims:
    jti: str
    iss: str
    aud: str
    sub: str                # Service ID (e.g. svc_api_gateway)
    service_name: str       # E.g. "api_gateway", "worker_runtime", "temporal_worker"
    tenant_id: str
    allowed_actions: List[str]
    iat: int
    exp: int

class ServiceIdentityGateway:
    """
    Authoritative machine-to-machine service token broker and verification gate.
    """
    DEFAULT_ISSUER = "zonata:internal:service-mesh"
    TOKEN_TTL_SEC = 300     # 5-minute maximum lifetime for machine tokens

    def __init__(self):
        self._service_secret = hashlib.sha256(b"zonata_m2m_enterprise_secret_2026").hexdigest()

    def issue_service_token(
        self,
        service_id: str,
        service_name: str,
        target_audience: str,
        tenant_id: str,
        allowed_actions: List[str],
        ttl_seconds: int = 300
    ) -> str:
        """Issue a short-lived, signed M2M service token."""
        now = int(time.time())
        claims = {
            "jti": f"m2m_{uuid.uuid4().hex}",
            "iss": self.DEFAULT_ISSUER,
            "aud": target_audience,
            "sub": service_id,
            "service_name": service_name,
            "tenant_id": tenant_id,
            "allowed_actions": allowed_actions,
            "iat": now,
            "exp": now + ttl_seconds
        }
        payload_bytes = json.dumps(claims, sort_keys=True).encode("utf-8")
        sig = hmac.new(self._service_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"{payload_bytes.hex()}.{sig}"

    def verify_service_token(
        self,
        token_str: str,
        expected_audience: str,
        expected_tenant_id: str,
        required_action: Optional[str] = None
    ) -> ServiceTokenClaims:
        """
        Verify M2M token against cryptographic signature, expiry, audience,
        tenant boundary, revocation list, and single-use replay protection.
        """
        now = int(time.time())

        # 1. Format verification
        parts = token_str.split(".")
        if len(parts) != 2:
            self._audit_violation("MALFORMED_SERVICE_TOKEN", "Token structure invalid", expected_tenant_id)
            raise ServiceSecurityViolation("Invalid service token format.")

        raw_hex, sig = parts[0], parts[1]
        try:
            payload_bytes = bytes.fromhex(raw_hex)
            expected_sig = hmac.new(self._service_secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                self._audit_violation("INVALID_SIGNATURE", "HMAC signature mismatch", expected_tenant_id)
                raise ServiceSecurityViolation("Service token cryptographic signature verification failed.")

            claims_dict = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            if isinstance(e, ServiceSecurityViolation):
                raise
            self._audit_violation("TOKEN_DECODE_ERROR", str(e), expected_tenant_id)
            raise ServiceSecurityViolation(f"Failed to decode service token: {e}")

        claims = ServiceTokenClaims(
            jti=claims_dict["jti"],
            iss=claims_dict["iss"],
            aud=claims_dict["aud"],
            sub=claims_dict["sub"],
            service_name=claims_dict["service_name"],
            tenant_id=claims_dict["tenant_id"],
            allowed_actions=claims_dict.get("allowed_actions", []),
            iat=claims_dict["iat"],
            exp=claims_dict["exp"]
        )

        # 2. Issuer check
        if claims.iss != self.DEFAULT_ISSUER:
            self._audit_violation("UNTRUSTED_ISSUER", f"Expected {self.DEFAULT_ISSUER}, got {claims.iss}", claims.tenant_id, claims.sub)
            raise ServiceSecurityViolation(f"Untrusted service token issuer: {claims.iss}")

        # 3. Audience check
        if claims.aud != expected_audience:
            self._audit_violation("WRONG_AUDIENCE", f"Expected {expected_audience}, got {claims.aud}", claims.tenant_id, claims.sub)
            raise ServiceSecurityViolation(f"Service token audience mismatch. Intended for '{claims.aud}', received by '{expected_audience}'.")

        # 4. Tenant boundary check
        if claims.tenant_id != expected_tenant_id:
            self._audit_violation("WRONG_TENANT", f"Expected {expected_tenant_id}, got {claims.tenant_id}", expected_tenant_id, claims.sub)
            raise ServiceSecurityViolation(f"Tenant isolation boundary breach: Token tenant '{claims.tenant_id}' != '{expected_tenant_id}'.")

        # 5. Expiration check
        if now > claims.exp:
            self._audit_violation("EXPIRED_CREDENTIAL", f"Token expired at {claims.exp}, now {now}", claims.tenant_id, claims.sub)
            raise ServiceSecurityViolation("Service token has expired.")

        # 6. Revocation check
        if coordination.get_idempotency_key(f"revoked_service:{claims.sub}") == "REVOKED":
            self._audit_violation("REVOKED_SERVICE", f"Service identity '{claims.sub}' is revoked", claims.tenant_id, claims.sub)
            raise ServiceSecurityViolation(f"Service identity '{claims.sub}' has been revoked.")

        # 7. Replay protection (JTI nonce check)
        jti_key = f"seen_service_jti:{claims.jti}"
        if coordination.get_idempotency_key(jti_key):
            self._audit_violation("REPLAY_ATTACK_DETECTED", f"Token JTI '{claims.jti}' already consumed", claims.tenant_id, claims.sub)
            raise ServiceSecurityViolation("Service token replay detected: JTI already consumed.")
        
        # Mark JTI as consumed with remaining TTL
        remaining_ttl = max(1.0, float(claims.exp - now))
        coordination.set_idempotency_key(jti_key, "CONSUMED", ttl_seconds=remaining_ttl)

        # 8. Action check
        if required_action and required_action not in claims.allowed_actions and "*" not in claims.allowed_actions:
            self._audit_violation("UNAUTHORIZED_ACTION", f"Action '{required_action}' not in {claims.allowed_actions}", claims.tenant_id, claims.sub)
            raise ServiceSecurityViolation(f"Action '{required_action}' not authorized for service '{claims.sub}'.")

        return claims

    def revoke_service_identity(self, service_id: str, reason: str, authorized_by: str) -> bool:
        """Revoke a service identity immediately across the cluster."""
        coordination.set_idempotency_key(f"revoked_service:{service_id}", "REVOKED", ttl_seconds=604800.0)
        coordination.set_killswitch_state("SERVICE", service_id, True, reason=f"Revoked by {authorized_by}: {reason}")
        evidence_service.record_event(
            tenant_id="SYSTEM_GLOBAL",
            company_id="SYSTEM_INTERNAL",
            event_type="SERVICE_IDENTITY_REVOKED",
            payload={"service_id": service_id, "reason": reason, "authorized_by": authorized_by}
        )
        logger.warning(f"[SERVICE IDENTITY REVOKED] Service '{service_id}' revoked by '{authorized_by}': {reason}")
        return True

    def _audit_violation(self, violation_type: str, detail: str, tenant_id: str, service_id: Optional[str] = None):
        """Record immediate security denial in Merkle Evidence Ledger."""
        try:
            evidence_service.record_event(
                tenant_id=tenant_id or "SYSTEM_GLOBAL",
                company_id="SECURITY_GATEWAY",
                event_type="M2M_SECURITY_VIOLATION",
                payload={"violation_type": violation_type, "detail": detail, "service_id": service_id, "timestamp": time.time()}
            )
        except Exception as e:
            logger.error(f"Failed to record evidence for M2M violation: {e}")

# Global singleton
service_identity_gateway = ServiceIdentityGateway()
