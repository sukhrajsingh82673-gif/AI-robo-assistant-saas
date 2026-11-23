"""
ZONATA Sovereign Core — Sub-Step 5E: Application & Supply-Chain Security Test Suite.
====================================================================================
Verifies:
- OWASP ASVS L2: Host header defense, strict CORS with credential safety, security headers.
- Brute-force protection with progressive exponential lockout.
- WAF attack payload inspection (SQLi, XSS, Path Traversal, Command Injection).
- CycloneDX SBOM validation & Rule 5 license allow-list enforcement.
- Cosign container image / artifact signing and verification via OpenBao Transit.
"""

import time
import pytest

from core.security.api_hardening import (
    APIHardeningConfig,
    BruteForceLockoutActive,
    BruteForceProtector,
    CORSSecurityViolation,
    CORSValidator,
    HostHeaderPoisoningError,
    HostHeaderValidator,
    SecurityAttackDetected,
    SecurityHeaderInjector,
    WAFPayloadInspector,
)
from core.security.supply_chain import (
    CosignSigner,
    CosignSignatureBundle,
    SBOMValidator,
    SupplyChainLicenseViolation,
    SupplyChainSecurityViolation,
    SupplyChainSignatureTamperedError,
)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestAppAndSupplyChainSecurity:

    def test_01_host_header_validation_and_poisoning_rejection(self):
        """Rejects spoofed or unapproved Host headers."""
        validator = HostHeaderValidator(
            allowed_hosts=["app.zonata.internal", "localhost", "127.0.0.1"]
        )

        # Approved hosts pass
        assert validator.validate_host("app.zonata.internal") is True
        assert validator.validate_host("app.zonata.internal:443") is True
        assert validator.validate_host("localhost:8000") is True

        # Unapproved hosts fail
        with pytest.raises(HostHeaderPoisoningError, match="not in the authorized hosts allow-list"):
            validator.validate_host("evil.com")

        with pytest.raises(HostHeaderPoisoningError, match="not in the authorized hosts allow-list"):
            validator.validate_host("attacker.internal")

        # Empty host fails
        with pytest.raises(HostHeaderPoisoningError, match="Empty Host header"):
            validator.validate_host("")

    def test_02_cors_origin_allowlist_and_credential_wildcard_rejection(self):
        """ASVS V14.4: Validates CORS origins and rejects wildcard with credentials."""
        validator = CORSValidator(
            allowed_origins=["https://console.zonata.internal", "https://app.zonata.internal"]
        )

        # Same origin (no Origin header) passes
        ok, _ = validator.validate_origin(None)
        assert ok is True

        # Allowed origin passes with credentials
        ok, headers = validator.validate_origin("https://console.zonata.internal", allows_credentials=True)
        assert ok is True
        assert headers["Access-Control-Allow-Origin"] == "https://console.zonata.internal"
        assert headers["Access-Control-Allow-Credentials"] == "true"

        # Wildcard with credentials strictly rejected
        with pytest.raises(CORSSecurityViolation, match=r"ASVS V14.4 Violation: Access-Control-Allow-Origin cannot be '\*'"):
            validator.validate_origin("*", allows_credentials=True)

        # Disallowed origin fails
        with pytest.raises(CORSSecurityViolation, match="not in the allowed CORS origins list"):
            validator.validate_origin("https://untrusted-site.com")

    def test_03_security_headers_injection(self):
        """Verifies standard OWASP / ASVS defense headers."""
        headers = SecurityHeaderInjector.get_security_headers()
        assert "Content-Security-Policy" in headers
        assert "default-src 'self'" in headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_04_brute_force_exponential_lockout(self):
        """Enforces progressive exponential lockout on authentication failures."""
        protector = BruteForceProtector(
            max_attempts=3, base_lockout_seconds=1.0, max_lockout_seconds=60.0
        )
        t0 = 1000.0

        # Attempt 1 & 2 fail: no lockout yet
        assert protector.record_failure("user:alice", now=t0) == 0.0
        protector.check_attempt("user:alice", now=t0)

        assert protector.record_failure("user:alice", now=t0) == 0.0
        protector.check_attempt("user:alice", now=t0)

        # Attempt 3 fails: 1.0s lockout triggered
        dur = protector.record_failure("user:alice", now=t0)
        assert dur == 1.0

        with pytest.raises(BruteForceLockoutActive, match="Too many failed attempts"):
            protector.check_attempt("user:alice", now=t0 + 0.5)

        # After lockout expires, checking attempt succeeds
        protector.check_attempt("user:alice", now=t0 + 1.1)

        # Attempt 4 fails: exponential escalation to 2.0s
        dur2 = protector.record_failure("user:alice", now=t0 + 1.1)
        assert dur2 == 2.0

        # Success resets tracking
        protector.record_success("user:alice")
        protector.check_attempt("user:alice", now=t0 + 1.2)

    def test_05_waf_payload_inspection_and_attacks(self):
        """WAF inspects and flags injection attacks and oversized payloads."""
        # Clean payload passes
        WAFPayloadInspector.inspect('{"user": "alice", "action": "view_report"}')

        # SQL Injection
        with pytest.raises(SecurityAttackDetected, match="SQL Injection"):
            WAFPayloadInspector.inspect("1' OR '1'='1")

        with pytest.raises(SecurityAttackDetected, match="SQL Injection"):
            WAFPayloadInspector.inspect("SELECT * FROM users UNION SELECT null, password FROM admin")

        # XSS
        with pytest.raises(SecurityAttackDetected, match="Cross-Site Scripting"):
            WAFPayloadInspector.inspect("<script>alert('pwned')</script>")

        with pytest.raises(SecurityAttackDetected, match="Cross-Site Scripting"):
            WAFPayloadInspector.inspect("<img src=x onerror=alert(1)>")

        # Path Traversal
        with pytest.raises(SecurityAttackDetected, match="Path Traversal"):
            WAFPayloadInspector.inspect("../../etc/shadow")

        # Command Injection
        with pytest.raises(SecurityAttackDetected, match="Command Injection"):
            WAFPayloadInspector.inspect("file.txt; cat /etc/passwd")

        # Payload Size Limit (oversized)
        huge_payload = "A" * (1024 * 1024 + 10)
        with pytest.raises(SecurityAttackDetected, match="Payload size.*exceeds maximum allowed limit"):
            WAFPayloadInspector.inspect(huge_payload, max_bytes=1024 * 1024)

    def test_06_cyclonedx_sbom_validation(self):
        """Validates standard CycloneDX SBOM structure and permissive licenses."""
        valid_sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "components": [
                {
                    "name": "fastapi",
                    "version": "0.115.0",
                    "licenses": [{"license": {"id": "MIT"}}],
                },
                {
                    "name": "pydantic",
                    "version": "2.8.2",
                    "licenses": [{"license": {"id": "MIT"}}],
                },
                {
                    "name": "cryptography",
                    "version": "43.0.0",
                    "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}],
                },
            ],
        }

        report = SBOMValidator.audit_sbom_dict(valid_sbom)
        assert report["is_compliant"] is True
        assert report["total_components"] == 3

        # Invalid format
        with pytest.raises(SupplyChainSecurityViolation, match="Invalid SBOM format"):
            SBOMValidator.audit_sbom_dict({"bomFormat": "SPDX"})

    def test_07_mutation_check_disallowed_license_in_sbom(self):
        """Mutation Check (Rule 8): SBOM containing component with AGPL/SSPL fails Rule 5."""
        tainted_sbom = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "components": [
                {
                    "name": "permitted-lib",
                    "version": "1.0.0",
                    "licenses": [{"license": {"id": "Apache-2.0"}}],
                },
                {
                    "name": "tainted-network-db",
                    "version": "2.1.0",
                    "licenses": [{"license": {"id": "AGPL-3.0-only"}}],
                },
            ],
        }

        with pytest.raises(SupplyChainLicenseViolation, match="Rule 5 Violation.*disallowed license 'AGPL-3.0-only'"):
            SBOMValidator.audit_sbom_dict(tainted_sbom)

        # SSPL mutation check
        tainted_sspl = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "components": [
                {
                    "name": "tainted-mongo",
                    "version": "5.0.0",
                    "licenses": [{"license": {"id": "SSPL-1.0"}}],
                }
            ],
        }
        with pytest.raises(SupplyChainLicenseViolation, match="Rule 5 Violation.*disallowed license 'SSPL-1.0'"):
            SBOMValidator.audit_sbom_dict(tainted_sspl)

    def test_08_cosign_artifact_signing_and_verification(self):
        """Cosign artifact signing and verification using OpenBao Transit key."""
        signer = CosignSigner(key_ref="openbao://transit/keys/release_signer")
        binary_payload = b"ZONATA_SOVEREIGN_CORE_BINARY_RELEASE_V1.0.0"

        bundle = signer.sign_artifact(
            binary_payload,
            image_ref="zonata.internal/core:v1.0.0",
            timestamp=1700000000.0,
        )

        assert bundle.payload_sha256 is not None
        assert bundle.signature is not None
        assert bundle.key_ref == "openbao://transit/keys/release_signer"

        # Verification succeeds
        assert signer.verify_artifact(
            binary_payload,
            bundle,
            expected_image_ref="zonata.internal/core:v1.0.0",
        ) is True

    def test_09_tampered_artifact_fails_cosign_verification(self):
        """Tampering with binary payload or signature fails closed."""
        signer = CosignSigner(key_ref="openbao://transit/keys/release_signer")
        payload = b"ORIGINAL_SOVEREIGN_PAYLOAD"
        bundle = signer.sign_artifact(payload, image_ref="zonata.internal/core:v1.0.0")

        # 1. Tampered payload
        tampered_payload = b"ORIGINAL_SOVEREIGN_PAYLOAD_TAMPERED"
        with pytest.raises(SupplyChainSignatureTamperedError, match="Artifact digest mismatch"):
            signer.verify_artifact(tampered_payload, bundle)

        # 2. Tampered signature
        tampered_bundle = CosignSignatureBundle(
            payload_sha256=bundle.payload_sha256,
            signature="tampered_base64_signature==",
            key_ref=bundle.key_ref,
            signed_payload=bundle.signed_payload,
            timestamp=bundle.timestamp,
        )
        with pytest.raises(SupplyChainSignatureTamperedError, match="Cryptographic verification failed"):
            signer.verify_artifact(payload, tampered_bundle)

        # 3. Identity mismatch
        with pytest.raises(SupplyChainSignatureTamperedError, match="Cosign identity mismatch"):
            signer.verify_artifact(
                payload, bundle, expected_image_ref="zonata.internal/untrusted:v1.0.0"
            )
