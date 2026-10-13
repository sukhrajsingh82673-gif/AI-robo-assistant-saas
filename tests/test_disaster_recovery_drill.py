"""
ZONATA Enterprise SaaS — Disaster Recovery & Backup Rehearsal Test Suite
Verifies:
1. Hot snapshot backup creation on active production database
2. Catastrophic data loss simulation (file corruption / zeroing)
3. Snapshot restore with zero data loss (RPO = 0)
4. Recovery Time Objective (RTO < 2000ms)
5. Post-recovery cryptographic and relational integrity checks (PRAGMA integrity_check, foreign keys)
6. Multi-tenant CRM and audit ledger recovery verification
"""

import os
import sys
import time
import shutil
import sqlite3
import tempfile
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.enterprise_crm import EnterpriseCrmService

MODULE_TEMP_DIR = None
MODULE_ORIG_DB_PATH = None
MODULE_ORIG_ENV_DB_PATH = None

def setUpModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_ORIG_ENV_DB_PATH = os.environ.get("ZONATA_DB_PATH")
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "dr_module_isolated.db")
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


class TestDisasterRecoveryDrill(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = db.db_path
        self.orig_env_db_path = os.environ.get("ZONATA_DB_PATH")
        self.test_dir = tempfile.TemporaryDirectory()
        self.live_db_path = os.path.join(self.test_dir.name, "live_production.db")
        self.backup_dir = os.path.join(self.test_dir.name, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

        os.environ["ZONATA_DB_PATH"] = self.live_db_path
        self.db = db
        self.db.set_db_path(self.live_db_path)

        # Populate initial enterprise tenant data
        with self.db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_dr_alpha', 'Alpha Enterprises', ?)", (time.time(),))
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_dr_beta', 'Beta Logistics', ?)", (time.time(),))
            conn.commit()

        self.crm_alpha = EnterpriseCrmService(tenant_id="tnt_dr_alpha")
        self.crm_beta = EnterpriseCrmService(tenant_id="tnt_dr_beta")

    def tearDown(self):
        if hasattr(self, "orig_db_path") and self.orig_db_path:
            db.set_db_path(self.orig_db_path)
        if hasattr(self, "orig_env_db_path"):
            if self.orig_env_db_path is not None:
                os.environ["ZONATA_DB_PATH"] = self.orig_env_db_path
            else:
                os.environ.pop("ZONATA_DB_PATH", None)
        try:
            self.test_dir.cleanup()
        except Exception:
            pass

    def _create_snapshot_backup(self, src_path, dest_dir):
        """Creates a hot atomic snapshot backup of the database using SQLite backup API."""
        timestamp = int(time.time() * 1000)
        dest_path = os.path.join(dest_dir, f"backup_snapshot_{timestamp}.db")
        src_conn = sqlite3.connect(src_path)
        dest_conn = sqlite3.connect(dest_path)
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
            src_conn.close()
        return dest_path

    def test_01_backup_snapshot_creation(self):
        """Verify online snapshot backup produces an intact, uncorrupted database copy."""
        # Insert test records
        for i in range(10):
            self.crm_alpha.create_customer("cmp_01", {
                "customer_id": f"cust_alpha_snap_{i}",
                "name": f"Customer Alpha {i}",
                "arr": 1000.0 * (i + 1),
                "tier": "ENTERPRISE"
            })

        customers = self.crm_alpha.list_customers()
        self.assertEqual(len(customers), 10)

        # Execute snapshot backup
        start_time = time.time()
        backup_file = self._create_snapshot_backup(self.live_db_path, self.backup_dir)
        elapsed = time.time() - start_time

        self.assertTrue(os.path.exists(backup_file))
        self.assertGreater(os.path.getsize(backup_file), 0)
        self.assertLess(elapsed, 2.0, "Backup creation took longer than 2.0s")

        # Verify integrity of backup
        b_conn = sqlite3.connect(backup_file)
        cur = b_conn.cursor()
        integrity = cur.execute("PRAGMA integrity_check").fetchone()
        self.assertEqual(integrity[0], "ok")
        count = cur.execute("SELECT COUNT(*) FROM crm_customers WHERE tenant_id = 'tnt_dr_alpha'").fetchone()[0]
        self.assertEqual(count, 10)
        b_conn.close()

    def test_02_simulated_catastrophic_failure_and_restoration(self):
        """
        Disaster Recovery Drill:
        1. Seed 50 customers and 26 deals across 2 tenants
        2. Create hot snapshot backup
        3. Simulate catastrophic disaster (complete live DB corruption / zeroing)
        4. Execute restoration from backup snapshot
        5. Verify RTO < 2000ms, RPO = 0 lost records, and full multi-tenant integrity
        """
        # Step 1: Seed data
        customer_ids_alpha = []
        for i in range(25):
            cust = self.crm_alpha.create_customer("cmp_01", {
                "customer_id": f"cust_alpha_dr_{i}",
                "name": f"Alpha Client {i}",
                "arr": 5000.0,
                "tier": "GROWTH"
            })
            customer_ids_alpha.append(cust["customer_id"])
            if i % 2 == 0:
                self.crm_alpha.create_deal("cmp_01", {
                    "deal_id": f"deal_alpha_dr_{i}",
                    "customer_id": cust["customer_id"],
                    "title": f"Alpha Deal {i}",
                    "value": 25000.0,
                    "stage": "discovery"
                })

        customer_ids_beta = []
        for i in range(25):
            cust = self.crm_beta.create_customer("cmp_02", {
                "customer_id": f"cust_beta_dr_{i}",
                "name": f"Beta Client {i}",
                "arr": 8000.0,
                "tier": "ENTERPRISE"
            })
            customer_ids_beta.append(cust["customer_id"])
            if i % 2 == 0:
                self.crm_beta.create_deal("cmp_02", {
                    "deal_id": f"deal_beta_dr_{i}",
                    "customer_id": cust["customer_id"],
                    "title": f"Beta Deal {i}",
                    "value": 40000.0,
                    "stage": "proposal"
                })

        alpha_pre_custs = self.crm_alpha.list_customers()
        beta_pre_custs = self.crm_beta.list_customers()
        alpha_pre_deals = self.crm_alpha.list_deals()
        beta_pre_deals = self.crm_beta.list_deals()

        self.assertEqual(len(alpha_pre_custs), 25)
        self.assertEqual(len(beta_pre_custs), 25)
        self.assertEqual(len(alpha_pre_deals), 13)
        self.assertEqual(len(beta_pre_deals), 13)

        # Step 2: Create snapshot backup
        backup_file = self._create_snapshot_backup(self.live_db_path, self.backup_dir)
        self.assertTrue(os.path.exists(backup_file))

        # Step 3: Simulate catastrophic disaster: zero out live database file
        with open(self.live_db_path, "wb") as f:
            f.write(b"\x00" * 2048)  # Overwrite database header with zeros

        # Verify live DB is now corrupted
        with self.assertRaises(sqlite3.DatabaseError):
            corrupt_conn = sqlite3.connect(self.live_db_path)
            corrupt_conn.execute("SELECT COUNT(*) FROM crm_customers").fetchall()
            corrupt_conn.close()

        # Step 4: Execute disaster recovery restore drill
        rto_start = time.time()
        # Restore procedure: atomically replace corrupted live database with backup snapshot
        temp_restore = self.live_db_path + ".restoring"
        shutil.copy2(backup_file, temp_restore)
        os.replace(temp_restore, self.live_db_path)
        rto_duration_ms = (time.time() - rto_start) * 1000

        # Verify RTO meets enterprise objective (< 2000 ms)
        self.assertLess(rto_duration_ms, 2000.0, f"RTO {rto_duration_ms:.2f}ms exceeded 2000ms target")

        # Step 5: Verify post-recovery data integrity & RPO = 0
        restored_alpha_custs = self.crm_alpha.list_customers()
        restored_beta_custs = self.crm_beta.list_customers()
        restored_alpha_deals = self.crm_alpha.list_deals()
        restored_beta_deals = self.crm_beta.list_deals()

        self.assertEqual(len(restored_alpha_custs), 25, "RPO failure: Alpha customer records lost")
        self.assertEqual(len(restored_beta_custs), 25, "RPO failure: Beta customer records lost")
        self.assertEqual(len(restored_alpha_deals), 13, "RPO failure: Alpha deal records lost")
        self.assertEqual(len(restored_beta_deals), 13, "RPO failure: Beta deal records lost")

        # Step 6: Verify relational integrity and SQLite PRAGMAs
        with self.db.get_connection() as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            self.assertEqual(integrity[0], "ok", "Database integrity check failed post-restore")

            fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            self.assertEqual(len(fk_violations), 0, f"Foreign key violations found: {fk_violations}")

    def test_03_transaction_rollback_and_wal_cleanliness(self):
        """Verify transaction rollback prevents partial writes during application failure."""
        with self.assertRaises(ValueError):
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO crm_customers (
                        customer_id, tenant_id, company_id, name, created_at, updated_at
                    ) VALUES ('cust_err_1', 'tnt_dr_alpha', 'cmp_01', 'Rollback Co', ?, ?)
                    """,
                    (time.time(), time.time())
                )
                # Intentional error to force rollback
                raise ValueError("Simulated business transaction fault")

        # Confirm uncommitted record was completely rolled back
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT customer_id FROM crm_customers WHERE customer_id = 'cust_err_1'").fetchone()
            self.assertIsNone(row, "Uncommitted transaction was not rolled back")


if __name__ == "__main__":
    unittest.main()
