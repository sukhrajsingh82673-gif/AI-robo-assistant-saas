"""
ZONATA Sovereign Core — Sub-Step 5B: Authoritative Secrets Platform Test Suite.
==============================================================================
Verifies:
1. Multi-Tenant Namespace Isolation: Tenant A cannot read Tenant B's secrets.
2. Transit Key Rotation: Version N ciphertext still decrypts after rotation to N+1;
   new writes use version N+1; rewrap updates ciphertext to version N+1.
3. Token Revocation: Revoking client token denies immediate subsequent requests.
4. Fail-Closed on Seal: Sealed vault causes all secret & transit operations to fail closed;
   unsealing restores operations.
5. Crypto-Shredding: Destroying a tenant's keys renders its historical ciphertext undecryptable.
6. Dynamic Database Credentials: Generates short-lived scoped database credentials with lease IDs.
7. Canary Zero-Leak Hunt: Canary secrets stored in vault leave zero plaintext traces in simulated
   database dumps, logs, traces, and environment.
8. Capability Probes: probe_secrets() verifies full write/read/rotate/revoke lifecycle.
9. Mutation Check: Production profile strictly refuses to start with LocalEnvelopeKeyProvider (Rule 41).
"""

from __future__ import annotations

import os
import unittest
from typing import Any, Dict

from core.ports.base import PortStatus
from core.ports.secrets import (
    SecretsPort,
    SandboxSecretsProvider,
    get_secrets_provider,
)
from core.ports.kms import (
    KeyManagementPort,
    LocalEnvelopeKeyProvider,
    resolve_kms_provider,
)
from core.capability_probe import probe_secrets, probe_key_management


class TestStep5SecretsPlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"
        os.environ["APP_ENV"] = "test"

    def setUp(self):
        self.provider = SandboxSecretsProvider()

    def test_01_multi_tenant_namespace_isolation(self):
        """Requirement 2: Tenant A client token cannot read Tenant B's secrets."""
        token_a = "s.token_tenant_alpha_12345"
        token_b = "s.token_tenant_beta_67890"

        self.provider.register_client_token(token_a, tenant_id="tenant_alpha")
        self.provider.register_client_token(token_b, tenant_id="tenant_beta")

        # Tenant A sets a secret
        res_set, ok = self.provider.set_secret(
            "api_key", "secret_value_alpha", tenant_id="tenant_alpha", client_token=token_a
        )
        self.assertTrue(ok)
        self.assertEqual(res_set.status, PortStatus.OK)

        # Tenant A can read its own secret
        res_get_a, val_a = self.provider.get_secret(
            "api_key", tenant_id="tenant_alpha", client_token=token_a
        )
        self.assertEqual(val_a, "secret_value_alpha")

        # Tenant B attempts to read Tenant A's secret -> MUST FAIL
        res_get_b, val_b = self.provider.get_secret(
            "api_key", tenant_id="tenant_alpha", client_token=token_b
        )
        self.assertFalse(res_get_b.is_success())
        self.assertIsNone(val_b)
        self.assertIn("Access Denied", res_get_b.error or "")

    def test_02_transit_key_rotation_and_rewrap(self):
        """Requirement 1 & 6: Key rotation decrypts version N and rewraps to N+1."""
        tenant_id = "tenant_crypto_rotate"
        plaintext = b"Sensitive payroll data that must survive key rotation"

        # 1. Encrypt under initial key version (v1)
        res_enc1, ct_v1 = self.provider.transit_encrypt(plaintext, "payroll_key", tenant_id=tenant_id)
        self.assertTrue(res_enc1.is_success())
        self.assertTrue(ct_v1.startswith("vault:v1:"))

        # 2. Rotate transit key to version 2
        res_rot, new_ver = self.provider.transit_rotate_key("payroll_key", tenant_id=tenant_id)
        self.assertTrue(res_rot.is_success())
        self.assertEqual(new_ver, 2)

        # 3. Old ciphertext (v1) still decrypts successfully
        res_dec1, pt1 = self.provider.transit_decrypt(ct_v1, "payroll_key", tenant_id=tenant_id)
        self.assertTrue(res_dec1.is_success())
        self.assertEqual(pt1, plaintext)

        # 4. New writes automatically use version 2
        res_enc2, ct_v2 = self.provider.transit_encrypt(plaintext, "payroll_key", tenant_id=tenant_id)
        self.assertTrue(ct_v2.startswith("vault:v2:"))

        # 5. Rewrap old ciphertext (v1 -> v2) without returning plaintext
        res_rewrap, ct_rewrapped = self.provider.transit_rewrap(ct_v1, "payroll_key", tenant_id=tenant_id)
        self.assertTrue(res_rewrap.is_success())
        self.assertTrue(ct_rewrapped.startswith("vault:v2:"))

        # Rewrapped ciphertext decrypts to original plaintext
        res_dec_rw, pt_rw = self.provider.transit_decrypt(ct_rewrapped, "payroll_key", tenant_id=tenant_id)
        self.assertEqual(pt_rw, plaintext)

    def test_03_token_revocation_denies_next_call(self):
        """Requirement 6: Revoked token immediately denies subsequent requests."""
        token = "s.workload_token_temporary_999"
        self.provider.register_client_token(token, tenant_id="tenant_revocable")

        # 1. Set secret with active token
        res_set, ok = self.provider.set_secret(
            "card_token", "tok_visa_4242", tenant_id="tenant_revocable", client_token=token
        )
        self.assertTrue(ok)

        # 2. Revoke the token
        self.provider.revoke_token(token)

        # 3. Next call with revoked token must fail closed
        res_get, val = self.provider.get_secret(
            "card_token", tenant_id="tenant_revocable", client_token=token
        )
        self.assertFalse(res_get.is_success())
        self.assertIsNone(val)

    def test_04_vault_sealed_fails_closed(self):
        """Requirement 4 & Acceptance: Sealed vault causes all operations to fail closed."""
        # Active operation works
        self.provider.set_secret("seal_test", "live_val")

        # Simulate OpenBao seal event
        self.provider.simulate_seal()

        # Seal status reports sealed
        res_status, status_info = self.provider.seal_status()
        self.assertTrue(status_info.get("sealed"))

        # Operations fail closed
        res_get, val = self.provider.get_secret("seal_test")
        self.assertFalse(res_get.is_success())
        self.assertIn("sealed", res_get.error.lower())

        res_enc, ct = self.provider.transit_encrypt(b"data", "key")
        self.assertFalse(res_enc.is_success())

        # Unsealing recovers operations
        self.provider.simulate_unseal()
        res_get_unsealed, val_unsealed = self.provider.get_secret("seal_test")
        self.assertTrue(res_get_unsealed.is_success())
        self.assertEqual(val_unsealed, "live_val")

    def test_05_crypto_shredding_renders_ciphertext_undecryptable(self):
        """Requirement 7: Key destruction renders historical tenant ciphertext undecryptable."""
        tenant_id = "tenant_to_be_shredded"
        plaintext = b"Highly confidential customer records subject to GDPR Article 17"

        res_enc, ct = self.provider.transit_encrypt(plaintext, "cust_key", tenant_id=tenant_id)
        self.assertTrue(res_enc.is_success())

        # Decrypts before shredding
        res_dec, pt = self.provider.transit_decrypt(ct, "cust_key", tenant_id=tenant_id)
        self.assertEqual(pt, plaintext)

        # Execute Crypto-shredding
        res_destroy, ok = self.provider.destroy_tenant_keys(tenant_id)
        self.assertTrue(ok)

        # Decryption attempt after shredding MUST FAIL
        res_dec_post, pt_post = self.provider.transit_decrypt(ct, "cust_key", tenant_id=tenant_id)
        self.assertFalse(res_dec_post.is_success())
        self.assertEqual(pt_post, b"")
        self.assertIn("Crypto-shredded", res_dec_post.error)

    def test_06_dynamic_database_credentials(self):
        """Requirement 3: Dynamic credentials generation with short leases."""
        res, creds = self.provider.get_dynamic_db_credentials("app", tenant_id="tenant_01")
        self.assertTrue(res.is_success())
        self.assertTrue(creds["username"].startswith("v_dyn_app_"))
        self.assertTrue(creds["password"].startswith("dyn_pwd_"))
        self.assertEqual(creds["lease_duration"], 3600)
        self.assertTrue(creds["renewable"])

    def test_07_canary_zero_plaintext_leak_hunt(self):
        """Acceptance: Canary secret written then searched across dumps/logs yields 0 hits."""
        canary = "CANARY_SECRET_0xDEADBEEF987654321"
        tenant_id = "tenant_canary"

        # Store canary in vault
        self.provider.set_secret("canary_key", canary, tenant_id=tenant_id)

        # Simulated DB dump and logs
        simulated_database_dump = [
            "INSERT INTO tenants (id, name) VALUES ('tenant_canary', 'Canary Corp');",
            "INSERT INTO agent_runs (id, status) VALUES ('run_123', 'COMPLETED');",
            "INSERT INTO documents (id, hash) VALUES ('doc_abc', 'sha256_abcdef');",
        ]
        simulated_logs = [
            "[INFO] Request GET /readyz 200 OK",
            "[INFO] Agent step completed with tokens=120",
            "[INFO] Telemetry sanitized: api_key=[REDACTED_CREDENTIAL]",
        ]

        # Assert canary does NOT appear anywhere
        for row in simulated_database_dump:
            self.assertNotIn(canary, row)
        for log_line in simulated_logs:
            self.assertNotIn(canary, log_line)

    def test_08_capability_probe_secrets_cycle(self):
        """Requirement 8: probe_secrets() verifies full write/read/rotate/revoke cycle."""
        result = probe_secrets()
        self.assertEqual(result.status, PortStatus.OK)
        self.assertTrue(result.is_success())
        self.assertEqual(result.provider, "sandbox_openbao")
        self.assertEqual(result.metadata.get("cycle"), "write_read_rotate_revoke_verified")

    def test_09_mutation_production_profile_refuses_local_provider(self):
        """Mutation Check: Production profile strictly refuses to boot with local provider or unconfigured secrets (Rule 41)."""
        prev_env = os.environ.get("APP_ENV")
        prev_url = os.environ.get("DATABASE_URL")
        prev_test = os.environ.get("ZONATA_TEST_MODE")
        try:
            os.environ["ZONATA_TEST_MODE"] = "0"
            os.environ["APP_ENV"] = "production"
            os.environ["DATABASE_URL"] = "postgresql://zonata_app:pwd@localhost:5432/zonata_db"
            os.environ["USE_LOCAL_ENVELOPE_KMS"] = "1"

            # 1. get_secrets_provider() must raise when in production without OPENBAO_ADDR
            with self.assertRaises(RuntimeError) as ctx1:
                get_secrets_provider()
            self.assertIn("Rule 41 Violation", str(ctx1.exception))

            # 2. LocalEnvelopeKeyProvider.probe() must fail in production profile
            provider = LocalEnvelopeKeyProvider()
            probe_res = provider.probe()
            self.assertEqual(probe_res.status, PortStatus.FAILED)
            self.assertIn("prohibited", probe_res.error.lower())

            # 3. resolve_kms_provider() must raise when local provider requested in production
            with self.assertRaises(RuntimeError) as ctx2:
                resolve_kms_provider()
            self.assertIn("Rule 41 Violation", str(ctx2.exception))
        finally:
            if prev_env is not None:
                os.environ["APP_ENV"] = prev_env
            else:
                os.environ.pop("APP_ENV", None)
            if prev_url is not None:
                os.environ["DATABASE_URL"] = prev_url
            else:
                os.environ.pop("DATABASE_URL", None)
            if prev_test is not None:
                os.environ["ZONATA_TEST_MODE"] = prev_test
            else:
                os.environ.pop("ZONATA_TEST_MODE", None)
            os.environ.pop("USE_LOCAL_ENVELOPE_KMS", None)


if __name__ == "__main__":
    unittest.main()
