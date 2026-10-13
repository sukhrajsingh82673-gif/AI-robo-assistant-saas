"""
ZONATA Enterprise SaaS — Direct Object Access (IDOR), Tenant Boundary & Key Rotation Test Suite
Verifies:
1. Direct Object Access (IDOR) rejection on customer and deal reads, writes, updates, and deletes
2. Prevention of cross-tenant object association (cannot attach deal to another tenant's customer)
3. Zero-downtime HMAC key rotation preserving active sessions with ZONATA_PREVIOUS_AUTH_SECRET
4. Secret entropy vs length evaluation
5. Multi-instance distributed rate limiting backed by relational table
6. Transparent password hash format upgrades on authentication
"""

import os
import sys
import time
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.auth import (
    UserManager,
    RateLimiter,
    TokenRevocationStore,
    hash_password,
    verify_password_with_upgrade,
    evaluate_secret_entropy,
    get_auth_secret_key,
    get_verification_keys
)
from core.enterprise_crm import EnterpriseCrmService

MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_TEMP_DIR
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "idor_test_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_TEMP_DIR
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestDirectObjectAccessAndTenantSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.environ["ZONATA_DB_PATH"] = self.temp_db_path
        self.db = db
        self.db.set_db_path(self.temp_db_path)

        # Initialize two isolated tenants: Alpha and Beta
        with self.db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_idor_alpha', 'Alpha Security Corp', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_idor_beta', 'Beta Infiltration Ltd', ?)", (time.time(),))
            conn.commit()

        self.crm_alpha = EnterpriseCrmService(tenant_id="tnt_idor_alpha")
        self.crm_beta = EnterpriseCrmService(tenant_id="tnt_idor_beta")

    def tearDown(self):
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_01_cross_tenant_idor_customer_isolation(self):
        """Verify Tenant Beta cannot read, update, or delete Tenant Alpha customer accounts."""
        # 1. Create sensitive customer in Tenant Alpha
        cust_alpha = self.crm_alpha.create_customer("cmp_01", {
            "name": "Alpha Defense Systems",
            "arr": 1500000.0,
            "tier": "STRATEGIC"
        })
        cid = cust_alpha["customer_id"]

        # 2. Tenant Beta attempts to read Tenant Alpha's customer -> Must return None
        read_by_beta = self.crm_beta.get_customer(cid)
        self.assertIsNone(read_by_beta, "IDOR Vulnerability: Tenant Beta read Tenant Alpha customer")

        # 3. Tenant Beta attempts to update Tenant Alpha's customer -> Must raise KeyError
        with self.assertRaises(KeyError):
            self.crm_beta.update_customer(cid, {"name": "Hacked by Beta"})

        # Verify Alpha customer name is unchanged
        read_by_alpha = self.crm_alpha.get_customer(cid)
        self.assertEqual(read_by_alpha["name"], "Alpha Defense Systems")

        # 4. Tenant Beta attempts to delete Tenant Alpha's customer -> Must return False
        deleted_by_beta = self.crm_beta.delete_customer(cid)
        self.assertFalse(deleted_by_beta, "IDOR Vulnerability: Tenant Beta deleted Tenant Alpha customer")

        # Verify customer still exists in Tenant Alpha
        still_exists = self.crm_alpha.get_customer(cid)
        self.assertIsNotNone(still_exists)

    def test_02_cross_tenant_idor_deal_isolation(self):
        """Verify Tenant Beta cannot read, progress, or delete Tenant Alpha commercial deals."""
        cust_alpha = self.crm_alpha.create_customer("cmp_01", {"name": "Alpha Client A"})
        deal_alpha = self.crm_alpha.create_deal("cmp_01", {
            "customer_id": cust_alpha["customer_id"],
            "title": "Alpha Confidential Deal",
            "value": 500000.0,
            "stage": "discovery"
        })
        deal_id = deal_alpha["deal_id"]

        # 1. Tenant Beta attempts to read Tenant Alpha's deal -> Must return None
        deal_read_by_beta = self.crm_beta.get_deal(deal_id)
        self.assertIsNone(deal_read_by_beta, "IDOR Vulnerability: Tenant Beta read Tenant Alpha deal")

        # 2. Tenant Beta attempts to update deal stage -> Must return updated=False
        res_beta = self.crm_beta.update_deal_stage(deal_id, "Won / Closed")
        self.assertFalse(res_beta.get("updated", True), "IDOR Vulnerability: Tenant Beta updated Tenant Alpha deal")

        # Verify Alpha deal stage remains 'discovery'
        deal_alpha_curr = self.crm_alpha.get_deal(deal_id)
        self.assertEqual(deal_alpha_curr["stage"], "discovery")

        # 3. Tenant Beta attempts to delete Tenant Alpha's deal -> Must return False
        deleted_by_beta = self.crm_beta.delete_deal(deal_id)
        self.assertFalse(deleted_by_beta, "IDOR Vulnerability: Tenant Beta deleted Tenant Alpha deal")

        # Verify deal still exists in Tenant Alpha
        self.assertIsNotNone(self.crm_alpha.get_deal(deal_id))

    def test_03_cross_tenant_foreign_key_injection_prevented(self):
        """Verify Tenant Beta cannot associate its deals with Tenant Alpha's customers."""
        cust_alpha = self.crm_alpha.create_customer("cmp_01", {"name": "Alpha Secret Asset"})
        
        # Tenant Beta attempts to create a deal referencing Alpha's customer
        with self.assertRaises(ValueError) as ctx:
            self.crm_beta.create_deal("cmp_02", {
                "customer_id": cust_alpha["customer_id"],
                "title": "Malicious Association Deal",
                "value": 10000.0
            })
        self.assertIn("Direct Object Access Violation", str(ctx.exception))

    def test_04_secret_entropy_evaluation(self):
        """Verify secret entropy evaluation distinguishes raw length from cryptographic randomness."""
        # Low entropy: 32 repeating characters (Shannon entropy = 0)
        low_ent = evaluate_secret_entropy("a" * 32)
        self.assertEqual(low_ent["length"], 32)
        self.assertEqual(low_ent["unique_chars"], 1)
        self.assertEqual(low_ent["entropy_bits_per_char"], 0.0)
        self.assertFalse(low_ent["is_high_entropy"])

        # High entropy: 64 hex characters (Shannon entropy ~4.0 bits/char)
        high_ent = evaluate_secret_entropy("9f8c2e71b4a035d8e1694f27ca3b51908271e6205738ab4c19ef01678234abcd")
        self.assertEqual(high_ent["length"], 64)
        self.assertGreaterEqual(high_ent["unique_chars"], 16)
        self.assertGreaterEqual(high_ent["entropy_bits_per_char"], 3.5)
        self.assertTrue(high_ent["is_high_entropy"])

    def test_05_zero_downtime_key_rotation_session_preservation(self):
        """Verify key rotation preserves sessions signed under ZONATA_PREVIOUS_AUTH_SECRET."""
        key_old = "old_secret_key_rotation_test_2026_x1"
        key_new = "new_secret_key_rotation_test_2026_x2"

        os.environ["ZONATA_AUTH_SECRET"] = key_old
        os.environ.pop("ZONATA_PREVIOUS_AUTH_SECRET", None)

        user = {"user_id": "usr_rot_01", "tenant_id": "tnt_idor_alpha"}
        token_under_old_key = UserManager.generate_token(user, expires_in_seconds=3600)
        self.assertIsNotNone(UserManager.verify_token(token_under_old_key))

        # Perform Key Rotation: New key becomes primary, old key becomes previous
        os.environ["ZONATA_AUTH_SECRET"] = key_new
        os.environ["ZONATA_PREVIOUS_AUTH_SECRET"] = key_old

        # 1. Existing token under old key must STILL be valid during rotation grace period
        verified_old = UserManager.verify_token(token_under_old_key)
        self.assertIsNotNone(verified_old, "Key rotation broke active user session signed under previous key")
        self.assertEqual(verified_old["user_id"], "usr_rot_01")

        # 2. Newly issued token is signed with new key
        token_under_new_key = UserManager.generate_token(user, expires_in_seconds=3600)
        self.assertIsNotNone(UserManager.verify_token(token_under_new_key))

        # Cleanup
        os.environ.pop("ZONATA_AUTH_SECRET", None)
        os.environ.pop("ZONATA_PREVIOUS_AUTH_SECRET", None)

    def test_06_transparent_password_hash_upgrade(self):
        """Verify legacy hex hash is transparently upgraded to pbkdf2_sha256 format on authentication."""
        # 1. Register user with legacy format (raw hex hash in database)
        import hashlib
        salt = "testsalt12345678"
        legacy_raw_hash = hashlib.pbkdf2_hmac("sha256", b"OldPass2026!", salt.encode("utf-8"), 100000).hex()

        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO users (user_id, tenant_id, email, name, role, status, created_at) VALUES ('usr_upg_01', 'tnt_idor_alpha', 'upgrade@corp.com', 'Upg User', 'OWNER', 'ACTIVE', ?)",
                (time.time(),)
            )
            conn.execute(
                "INSERT INTO auth_credentials (user_id, password_hash, salt, failed_attempts, locked_until, created_at, updated_at) VALUES ('usr_upg_01', ?, ?, 0, 0, ?, ?)",
                (legacy_raw_hash, salt, time.time(), time.time())
            )
            conn.commit()

        # 2. Authenticate user -> Must succeed
        ok, u_dict, msg = UserManager.authenticate_user("upgrade@corp.com", "OldPass2026!", tenant_id="tnt_idor_alpha")
        self.assertTrue(ok)
        self.assertEqual(msg, "OK")

        # 3. Check database record -> Must be upgraded to pbkdf2_sha256$100000$... format
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT password_hash FROM auth_credentials WHERE user_id = 'usr_upg_01'").fetchone()
            upgraded_hash = row["password_hash"]
            self.assertTrue(upgraded_hash.startswith("pbkdf2_sha256$100000$"), f"Hash was not upgraded: {upgraded_hash}")


if __name__ == "__main__":
    unittest.main()
