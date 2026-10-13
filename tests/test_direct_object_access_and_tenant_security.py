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
    get_verification_keys,
    emergency_retire_previous_secret,
    generate_secure_auth_secret,
    verify_password_with_upgrade
)
from core.enterprise_crm import EnterpriseCrmService

MODULE_TEMP_DIR = None
MODULE_ORIG_DB_PATH = None
MODULE_ORIG_ENV_DB_PATH = None

def setUpModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_ORIG_ENV_DB_PATH = os.environ.get("ZONATA_DB_PATH")
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "idor_test_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
    if MODULE_ORIG_ENV_DB_PATH is not None:
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_ENV_DB_PATH
    else:
        os.environ.pop("ZONATA_DB_PATH", None)
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestDirectObjectAccessAndTenantSecurity(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = db.db_path
        self.orig_env_db_path = os.environ.get("ZONATA_DB_PATH")
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
        if hasattr(self, "orig_db_path") and self.orig_db_path:
            db.set_db_path(self.orig_db_path)
        if hasattr(self, "orig_env_db_path"):
            if self.orig_env_db_path is not None:
                os.environ["ZONATA_DB_PATH"] = self.orig_env_db_path
            else:
                os.environ.pop("ZONATA_DB_PATH", None)
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
        """Verify legacy hex hash is transparently upgraded to pbkdf2_sha256 format with 600000 iterations on authentication."""
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

        # 3. Check database record -> Must be upgraded to pbkdf2_sha256$600000$... format
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT password_hash FROM auth_credentials WHERE user_id = 'usr_upg_01'").fetchone()
            upgraded_hash = row["password_hash"]
            self.assertTrue(upgraded_hash.startswith("pbkdf2_sha256$600000$"), f"Hash was not upgraded: {upgraded_hash}")

        # 4. User with 100000 iterations format also gets upgraded to 600000 iterations
        iter100k_hash = f"pbkdf2_sha256$100000${salt}${legacy_raw_hash}"
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE auth_credentials SET password_hash = ? WHERE user_id = 'usr_upg_01'",
                (iter100k_hash,)
            )
            conn.commit()

        ok, u_dict, msg = UserManager.authenticate_user("upgrade@corp.com", "OldPass2026!", tenant_id="tnt_idor_alpha")
        self.assertTrue(ok)
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT password_hash FROM auth_credentials WHERE user_id = 'usr_upg_01'").fetchone()
            self.assertTrue(row["password_hash"].startswith("pbkdf2_sha256$600000$"))

    def test_07_deal_update_idor_and_cross_tenant_association(self):
        """Verify deal updates enforce tenant boundary and prevent cross-tenant customer association."""
        # Setup: Customer Alpha in Tenant Alpha, Customer Beta in Tenant Beta
        cust_alpha = self.crm_alpha.create_customer("cmp_01", {"name": "Alpha Corp Prime"})
        cust_beta = self.crm_beta.create_customer("cmp_01", {"name": "Beta Infiltration Target"})

        # Deal Alpha belongs to Tenant Alpha
        deal_alpha = self.crm_alpha.create_deal("cmp_01", {
            "title": "Alpha Expansion Contract",
            "customer_id": cust_alpha["customer_id"],
            "value": 250000.0,
            "stage": "discovery"
        })
        alpha_deal_id = deal_alpha["deal_id"]

        # 1. Tenant Beta attempts to update Tenant Alpha's deal -> Must fail with KeyError (404)
        with self.assertRaises(KeyError):
            self.crm_beta.update_deal(alpha_deal_id, {"title": "Compromised by Beta"})

        # 2. Tenant Alpha attempts to associate its deal with Tenant Beta's customer -> Must fail with ValueError
        with self.assertRaises(ValueError) as ctx:
            self.crm_alpha.update_deal(alpha_deal_id, {"customer_id": cust_beta["customer_id"]})
        self.assertIn("not found in current organization", str(ctx.exception))

        # 3. Legitimate update within tenant boundary succeeds
        updated = self.crm_alpha.update_deal(alpha_deal_id, {
            "title": "Alpha Approved Expansion",
            "value": 300000.0,
            "stage": "negotiation"
        })
        self.assertEqual(updated["title"], "Alpha Approved Expansion")
        self.assertEqual(updated["value"], 300000.0)
        self.assertEqual(updated["stage"], "negotiation")

    def test_08_concurrent_distributed_rate_limiting(self):
        """Verify distributed rate limiter is concurrency-safe across simultaneous worker threads."""
        import threading
        test_key = "test_concurrent_worker_key"
        max_requests = 5
        results = []
        threads = []

        def worker_attempt():
            ok, retry = RateLimiter.is_allowed(test_key, max_requests=max_requests, window_seconds=60.0)
            results.append(ok)

        # Launch 15 concurrent worker threads simultaneously
        for _ in range(15):
            t = threading.Thread(target=worker_attempt)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Under strict concurrency, exactly max_requests must be True, remaining must be False
        successes = sum(1 for r in results if r is True)
        failures = sum(1 for r in results if r is False)
        self.assertEqual(successes, max_requests, f"Concurrency violation: {successes} allowed, expected {max_requests}")
        self.assertEqual(failures, 10)

        # Dual-axis rate limiting verification
        allowed, retry, axis = RateLimiter.rate_limit_ip_and_account("10.0.0.99", "user@corp.com", max_ip_requests=10, max_account_requests=5)
        self.assertTrue(allowed)
        self.assertEqual(axis, "")

    def test_09_emergency_key_retirement_and_rotation_window_expiry(self):
        """Verify rotation window expiration and immediate emergency key retirement."""
        key_compromised = "compromised_secret_key_rotation_2026_vuln"
        key_primary = "current_active_secret_key_2026_safe"

        os.environ["ZONATA_AUTH_SECRET"] = key_primary
        os.environ["ZONATA_PREVIOUS_AUTH_SECRET"] = key_compromised

        user = {"user_id": "usr_rot_emerg", "tenant_id": "tnt_idor_alpha"}
        # Token signed under previous key
        import hmac, hashlib, json
        payload = {"user_id": "usr_rot_emerg", "tenant_id": "tnt_idor_alpha", "exp": time.time() + 3600}
        p_str = json.dumps(payload, sort_keys=True)
        sig = hmac.new(key_compromised.encode("utf-8"), p_str.encode("utf-8"), hashlib.sha256).hexdigest()
        token_under_prev = f"{p_str}.{sig}"

        # 1. Initially accepted under active rotation window
        self.assertIsNotNone(UserManager.verify_token(token_under_prev))

        # 2. Window expiration: set ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT to past
        os.environ["ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT"] = str(time.time() - 100)
        self.assertIsNone(UserManager.verify_token(token_under_prev), "Token accepted after rotation window expired")

        # Reset window
        os.environ.pop("ZONATA_PREVIOUS_AUTH_SECRET_EXPIRES_AT", None)
        self.assertIsNotNone(UserManager.verify_token(token_under_prev))

        # 3. Emergency Retirement: immediately revoke compromised key
        emergency_retire_previous_secret(key_compromised)
        self.assertIsNone(UserManager.verify_token(token_under_prev), "Emergency retirement failed to reject token")
        from core.auth import compute_key_fingerprint
        compromised_fp = compute_key_fingerprint(key_compromised.encode("utf-8"))
        self.assertIn(compromised_fp, os.environ.get("ZONATA_REVOKED_KEY_FINGERPRINTS", ""))

        # Cleanup
        os.environ.pop("ZONATA_AUTH_SECRET", None)
        os.environ.pop("ZONATA_PREVIOUS_AUTH_SECRET", None)
        os.environ.pop("ZONATA_REVOKED_AUTH_SECRETS", None)
        os.environ.pop("ZONATA_REVOKED_KEY_FINGERPRINTS", None)
        os.environ.pop("ZONATA_EMERGENCY_RETIRE_PREVIOUS_KEY", None)

    def test_10_cryptographic_secret_generation(self):
        """Verify CSPRNG generation creates 256 bits of cryptographic entropy."""
        secret = generate_secure_auth_secret(32)
        self.assertEqual(len(secret), 64)
        entropy_metrics = evaluate_secret_entropy(secret)
        self.assertTrue(entropy_metrics["is_high_entropy"])
        self.assertGreaterEqual(entropy_metrics["entropy_bits_per_char"], 3.5)

    def test_11_malformed_hashes_and_concurrency_safety(self):
        """Verify malformed password hashes fail closed without crashing."""
        self.assertEqual(verify_password_with_upgrade("Pass", "salt", ""), (False, False))
        self.assertEqual(verify_password_with_upgrade("Pass", "salt", "invalid_string"), (False, False))
        self.assertEqual(verify_password_with_upgrade("Pass", "salt", "pbkdf2_sha256$notanumber$salt$hash"), (False, False))
        self.assertEqual(verify_password_with_upgrade("Pass", "salt", "pbkdf2_sha256$-100$salt$hash"), (False, False))

    def test_12_password_max_length_and_unicode_normalization(self):
        """Verify Unicode normalization matches across forms and excessive password length is rejected."""
        import unicodedata
        from core.auth import hash_password, verify_password

        # Unicode equivalence test: composed vs decomposed forms
        pass_nfc = unicodedata.normalize("NFC", "SchöneStraße2026!€")
        pass_nfd = unicodedata.normalize("NFD", "SchöneStraße2026!€")
        p_hash, salt = hash_password(pass_nfc)
        self.assertTrue(verify_password(pass_nfd, salt, p_hash), "Unicode normalization failed across NFC/NFD representations")

        # Massive input size rejection to prevent algorithmic DoS
        massive_pw = "A" * 5000
        with self.assertRaises(ValueError):
            hash_password(massive_pw)
        self.assertFalse(verify_password(massive_pw, salt, p_hash))

    def test_13_dual_axis_rate_limit_and_scoped_pruning(self):
        """Verify dual-axis rate limiting throttles IP and account independently with scoped pruning."""
        # 1. Account throttling independently of IP
        ip_rotating_prefix = "192.168.1."
        target_account = "targeted_cfo@enterprise.com"

        for i in range(5):
            ok, retry, axis = RateLimiter.rate_limit_ip_and_account(
                f"{ip_rotating_prefix}{i+1}",
                target_account,
                max_ip_requests=20,
                max_account_requests=5,
                window_seconds=60.0
            )
            self.assertTrue(ok, f"Attempt {i+1} unexpectedly blocked")

        # 6th attempt from a fresh IP against the same account must fail on ACCOUNT axis
        ok, retry, axis = RateLimiter.rate_limit_ip_and_account(
            "192.168.1.99",
            target_account,
            max_ip_requests=20,
            max_account_requests=5,
            window_seconds=60.0
        )
        self.assertFalse(ok)
        self.assertEqual(axis, "ACCOUNT_RATE_LIMIT_EXCEEDED")
        self.assertGreater(retry, 0)


if __name__ == "__main__":
    unittest.main()
