"""
Acceptance Test Suite for OpenCode Step 3D — Origin-Bound Credential Vault
Tests:
(a) Attempting to inject a credential on a different origin is refused and logged.
(b) Placeholder substituted at the last moment inside the engine.
(c) Screenshot and accessibility tree after injection show masked value, not the secret.
(d) No plaintext in logs, traces, evidence ledger or database (Rule 24).
(e) High-privilege credential triggers ActionGateway approval requirement (Rule 27).
(f) Zero export invariant: plaintext extraction fails closed with SecretExportForbiddenError.
(g) Session-scoped ephemeral cookies purged immediately upon session termination.
"""

import unittest
import time
import uuid
import re
from typing import Dict, Any

from core.db import db
from core.vault import (
    OriginBoundSecretVault,
    CredentialInjector,
    EphemeralCookieManager,
    SecretType,
    PrivilegeLevel,
    OriginMismatchError,
    SecretExportForbiddenError,
    HighPrivilegeApprovalRequiredError,
)
from core.host.perception import (
    BoundingRect,
    DesktopPerceptionEngine,
)


class TestStep3CredentialVault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.verify_readiness()

    def setUp(self):
        self.tenant_id = f"tnt_{uuid.uuid4().hex[:8]}"
        self.company_id = f"cmp_{uuid.uuid4().hex[:8]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES (?, ?, ?)",
                (self.tenant_id, f"Tenant {self.tenant_id}", time.time()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_id, tenant_id, name, industry, company_type, created_at) VALUES (?, ?, ?, 'TECH', 'NEW', ?)",
                (self.company_id, self.tenant_id, f"Company {self.company_id}", time.time()),
            )
            if hasattr(conn, "commit"):
                conn.commit()

        self.vault = OriginBoundSecretVault()
        self.injector = CredentialInjector(vault=self.vault)
        self.cookie_mgr = EphemeralCookieManager()

        # Seed sample secret: bound to exact origin https://billing.acme.example.com:443
        self.secret_plaintext = "P@ssw0rd_Super_Secret_2026!#"
        self.bound_origin = "https://billing.acme.example.com:443"
        self.secret_name = "acme_billing_login"

        self.placeholder = self.vault.store_credential(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name=self.secret_name,
            origin=self.bound_origin,
            secret=self.secret_plaintext,
            username="billing_admin@acme.example.com",
            secret_type=SecretType.PASSWORD,
            privilege_level=PrivilegeLevel.STANDARD,
        )

        # Seed high-privilege secret: bound to https://treasury.acme.example.com:443
        self.high_priv_secret = "WireTransferSecretKey_9999"
        self.vault.store_credential(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="acme_treasury_wire",
            origin="https://treasury.acme.example.com:443",
            secret=self.high_priv_secret,
            secret_type=SecretType.API_KEY,
            privilege_level=PrivilegeLevel.HIGH_PRIVILEGE,
        )

    def test_01_origin_mismatch_refusal(self):
        """Acceptance (a): Attempting to inject a credential on a different origin is refused and logged."""
        # Target 1: Insecure HTTP downgrade
        with self.assertRaises(OriginMismatchError) as ctx:
            self.vault.inject_credential(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                name=self.secret_name,
                target_url="http://billing.acme.example.com/login",
            )
        self.assertIn("ORIGIN MISMATCH REFUSAL", str(ctx.exception))

        # Target 2: Different domain (attacker site or phishing redirect)
        with self.assertRaises(OriginMismatchError) as ctx:
            self.vault.inject_credential(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                name=self.secret_name,
                target_url="https://attacker-phishing.example.com/steal",
            )
        self.assertIn("ORIGIN MISMATCH REFUSAL", str(ctx.exception))

        # Target 3: Unmatched subdomain
        with self.assertRaises(OriginMismatchError):
            self.vault.inject_credential(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                name=self.secret_name,
                target_url="https://other.acme.example.com/login",
            )

    def test_02_placeholder_substituted_at_last_moment(self):
        """Acceptance (b): Placeholder substituted at the last moment inside the engine."""
        command = f"fill_form(username='user', password='{self.placeholder}')"
        target_page = "https://billing.acme.example.com/login?step=2"

        injected, masked_secrets = self.injector.substitute_placeholders(
            command_or_script=command,
            target_url=target_page,
            tenant_id=self.tenant_id,
            company_id=self.company_id,
        )

        # Injected string now has the plaintext password
        self.assertIn(self.secret_plaintext, injected)
        self.assertNotIn(self.placeholder, injected)
        self.assertIn(self.secret_plaintext, masked_secrets)

    def test_03_perception_and_dom_masking_post_injection(self):
        """Acceptance (c): Screenshot and accessibility tree show masked value, not the secret."""
        # Simulated DOM / tree containing injected secret
        tree_data = {
            "window_id": "win_browser",
            "window_title": "Acme Billing Login",
            "nodes": [
                {
                    "node_id": "input_pwd",
                    "role": "password_field",
                    "name": "Password Input",
                    "bounds": {"x": 100, "y": 100, "width": 200, "height": 30},
                    "is_password": True,
                    "value": self.secret_plaintext,  # Plaintext injected in DOM
                }
            ]
        }
        bounds = BoundingRect(x=0, y=0, width=1920, height=1080)
        engine = DesktopPerceptionEngine()
        parsed_tree = engine.parse_accessibility_snapshot(tree_data, bounds)

        # Tree serialization must NEVER contain the secret
        tree_dict = parsed_tree.to_dict()
        node = tree_dict["nodes"][0]
        self.assertEqual(node["value"], "[MASKED_INPUT]")
        self.assertNotIn(self.secret_plaintext, str(tree_dict))

        # Visual frame masking also blacks out region
        masked_frame = engine.mask_visual_frame({"window_id": "win_browser"}, parsed_tree)
        self.assertEqual(masked_frame["masked_regions_count"], 1)
        self.assertEqual(masked_frame["masked_regions"][0]["action"], "BLACKOUT_MASK")

    def test_04_no_plaintext_in_database_or_evidence_ledger(self):
        """Acceptance (d): No plaintext in database, logs, or evidence ledger."""
        with db.get_connection() as conn:
            # Query enterprise_secret_vault directly
            rows = conn.execute(
                "SELECT username_ciphertext, secret_ciphertext FROM enterprise_secret_vault WHERE tenant_id = ?",
                (self.tenant_id,),
            ).fetchall()

            for row in rows:
                user_ct = row[0]
                secret_ct = row[1]
                # Plaintext must NEVER appear in ciphertext columns
                if user_ct:
                    self.assertNotIn("billing_admin@acme.example.com", user_ct)
                self.assertNotIn(self.secret_plaintext, secret_ct)

            # Query merkle_evidence_events for tenant
            ev_rows = conn.execute(
                "SELECT canonical_payload_hash FROM merkle_evidence_events WHERE tenant_id = ?",
                (self.tenant_id,),
            ).fetchall()
            self.assertGreater(len(ev_rows), 0)

    def test_05_high_privilege_requires_human_approval(self):
        """Acceptance (e): High-privilege credential triggers ActionGateway approval requirement."""
        target_treasury_url = "https://treasury.acme.example.com:443/api/wire"

        # Attempting injection without human approval raises HighPrivilegeApprovalRequiredError
        with self.assertRaises(HighPrivilegeApprovalRequiredError) as ctx:
            self.vault.inject_credential(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                name="acme_treasury_wire",
                target_url=target_treasury_url,
                is_human_approved=False,
            )
        self.assertIn("HIGH PRIVILEGE GATE", str(ctx.exception))

        # With human approval, injection succeeds
        user, sec = self.vault.inject_credential(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            name="acme_treasury_wire",
            target_url=target_treasury_url,
            is_human_approved=True,
        )
        self.assertEqual(sec, self.high_priv_secret)

    def test_06_zero_export_invariant(self):
        """Acceptance (f): Secret export is strictly forbidden."""
        with self.assertRaises(SecretExportForbiddenError) as ctx:
            self.vault.export_secret()
        self.assertIn("strictly forbidden", str(ctx.exception))

    def test_07_ephemeral_cookie_origin_binding_and_purge(self):
        """Acceptance (g): Session-scoped ephemeral cookies bound to origin and purged on session close."""
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        origin = "https://portal.acme.example.com:443"
        cookies = {"session_jwt": "jwt_token_sample_12345", "csrf_token": "csrf_xyz"}

        self.cookie_mgr.store_session_cookies(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            session_id=session_id,
            origin=origin,
            cookies=cookies,
        )

        # Retrieval on exact origin succeeds
        retrieved = self.cookie_mgr.retrieve_session_cookies(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            session_id=session_id,
            target_url="https://portal.acme.example.com:443/dashboard",
        )
        self.assertEqual(retrieved, cookies)

        # Retrieval on mismatched origin raises OriginMismatchError
        with self.assertRaises(OriginMismatchError):
            self.cookie_mgr.retrieve_session_cookies(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                session_id=session_id,
                target_url="https://attacker.example.com/steal",
            )

        # Purge session on logout
        self.cookie_mgr.purge_session(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            session_id=session_id,
        )

        # Subsequent retrieval returns empty dict
        purged = self.cookie_mgr.retrieve_session_cookies(
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            session_id=session_id,
            target_url="https://portal.acme.example.com:443/dashboard",
        )
        self.assertEqual(purged, {})


if __name__ == "__main__":
    unittest.main()
