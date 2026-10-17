"""
ZONATA Enterprise SaaS — Off-Host Disaster Recovery & S3 Backup Replication Suite
Phase 7 Qualification Suite (BLK-01 & BLK-12)

Verifies:
1. Replicator initialization, bucket configuration, and S3 endpoint mapping.
2. PostgreSQL 16MB WAL segment replication to off-host S3 mirror.
3. Base backup directory packaging, checksumming, and off-host replication.
4. Hot SQLite snapshot & EvidenceLedger audit off-host replication.
5. Cryptographic checksum and envelope verification before restore.
6. Ransomware / bit-rot tamper detection failing closed with BackupSecurityViolationError.
7. Multi-tenant access separation preventing cross-tenant backup access.
8. Immutable WORM retention lock preventing unauthorized deletion.
9. End-to-end off-host disaster recovery restoration to a clean replacement environment.
10. Standardized RTO (< 2000ms) and RPO (0.0s) metrics reporting (BLK-12).
"""

import os
import sys
import time
import uuid
import shutil
import sqlite3
import hashlib
import tempfile
import unittest
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import db, configure_isolated_test_db
from core.backup_security import backup_security_manager, BackupSecurityViolationError
from core.offhost_backup_replicator import OffHostBackupReplicator, OffHostReplicationReceipt

MODULE_ORIG_DB_PATH = None
MODULE_TEMP_DIR = None

def setUpModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "offhost_dr_isolated.db")
    configure_isolated_test_db(isolated_db)

def tearDownModule():
    global MODULE_ORIG_DB_PATH, MODULE_TEMP_DIR
    if MODULE_ORIG_DB_PATH:
        db.set_db_path(MODULE_ORIG_DB_PATH)
        os.environ["ZONATA_DB_PATH"] = MODULE_ORIG_DB_PATH
    if MODULE_TEMP_DIR:
        MODULE_TEMP_DIR.cleanup()


class TestOffHostDisasterRecovery(unittest.TestCase):
    """Qualification suite for off-host backup replication, WORM retention, and standardized RTO/RPO."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.s3_mirror_dir = os.path.join(self.test_dir.name, "s3_mirror")
        self.replicator = OffHostBackupReplicator(
            s3_endpoint="mock://minio:9000",
            bucket_name="zonata-test-backups",
            offhost_mirror_dir=self.s3_mirror_dir,
            project_root=self.test_dir.name
        )
        self.tenant_a = f"tnt_alpha_{uuid.uuid4().hex[:6]}"
        self.tenant_b = f"tnt_beta_{uuid.uuid4().hex[:6]}"

    def tearDown(self):
        try:
            self.test_dir.cleanup()
        except Exception:
            pass

    def test_01_offhost_replicator_initialization_and_configuration(self):
        """Verify replicator bucket name, mirror path, and registry state."""
        self.assertEqual(self.replicator.bucket_name, "zonata-test-backups")
        self.assertTrue(os.path.exists(self.s3_mirror_dir))
        self.assertEqual(len(self.replicator._manifest_registry), 0)

    def test_02_wal_segment_offhost_replication_and_checksum(self):
        """Verify 16MB WAL segment is replicated off-host with exact SHA-256 and WORM envelope."""
        wal_file = os.path.join(self.test_dir.name, "000000010000000000000001")
        # Generate synthetic 1MB sample (proportional to 16MB segment)
        sample_data = b"POSTGRESQL_WAL_HEADER" + (b"\x00" * (1024 * 1024 - 21))
        with open(wal_file, "wb") as f:
            f.write(sample_data)

        receipt = self.replicator.replicate_wal_segment(wal_file, tenant_id=self.tenant_a)
        self.assertEqual(receipt.artifact_type, "WAL_SEGMENT")
        self.assertEqual(receipt.status, "SYNCED_OFFHOST")
        self.assertEqual(receipt.size_bytes, 1024 * 1024)
        self.assertEqual(receipt.sha256_checksum, hashlib.sha256(sample_data).hexdigest())

        # Verify presence in off-host mirror
        expected_offhost_file = os.path.join(self.s3_mirror_dir, "postgres", "wal_archive", receipt.file_name)
        self.assertTrue(os.path.exists(expected_offhost_file), "WAL file missing from off-host S3 mirror")

    def test_03_base_backup_packaging_and_offhost_sync(self):
        """Verify PostgreSQL base backup directory is bundled, checksummed, and synced off-host."""
        bb_dir = os.path.join(self.test_dir.name, "base_backup_sample")
        os.makedirs(bb_dir, exist_ok=True)
        with open(os.path.join(bb_dir, "PG_VERSION"), "w") as f:
            f.write("16\n")
        with open(os.path.join(bb_dir, "backup_label"), "w") as f:
            f.write("START WAL LOCATION: 0/10000000\n")

        receipt = self.replicator.replicate_base_backup(bb_dir, "base_20261017", tenant_id=self.tenant_a)
        self.assertEqual(receipt.artifact_type, "BASE_BACKUP")
        self.assertTrue(receipt.file_name.endswith(".tar.gz"))
        self.assertGreater(receipt.size_bytes, 0)

        expected_offhost_tar = os.path.join(self.s3_mirror_dir, "postgres", "base_backups", receipt.file_name)
        self.assertTrue(os.path.exists(expected_offhost_tar))

    def test_04_sqlite_snapshot_and_evidence_offhost_replication(self):
        """Verify SQLite snapshot and audit ledger replication to off-host S3 mirror."""
        db_file = os.path.join(self.test_dir.name, "snapshot_test.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE test_data (id INT PRIMARY KEY, val TEXT);")
        conn.execute("INSERT INTO test_data VALUES (1, 'replicated_record');")
        conn.commit()
        conn.close()

        receipt = self.replicator.replicate_sqlite_snapshot(db_file, tenant_id=self.tenant_a)
        self.assertEqual(receipt.artifact_type, "SQLITE_SNAPSHOT")
        self.assertEqual(receipt.status, "SYNCED_OFFHOST")

        expected_offhost_db = os.path.join(self.s3_mirror_dir, "sqlite", "snapshots", receipt.file_name)
        self.assertTrue(os.path.exists(expected_offhost_db))

    def test_05_offhost_object_integrity_verification(self):
        """Verify verify_offhost_object confirms authentic, untampered off-host artifacts."""
        wal_file = os.path.join(self.test_dir.name, "000000010000000000000002")
        with open(wal_file, "wb") as f:
            f.write(b"SAMPLE_WAL_PAYLOAD_TEST_05")

        receipt = self.replicator.replicate_wal_segment(wal_file, tenant_id=self.tenant_a)
        verified = self.replicator.verify_offhost_object(receipt.receipt_id, requesting_tenant_id=self.tenant_a)
        self.assertTrue(verified)

    def test_06_ransomware_tamper_defense_fails_closed(self):
        """Verify altered or corrupted off-host backups trigger BackupSecurityViolationError."""
        wal_file = os.path.join(self.test_dir.name, "000000010000000000000003")
        with open(wal_file, "wb") as f:
            f.write(b"GENUINE_ORIGINAL_BACKUP")

        receipt = self.replicator.replicate_wal_segment(wal_file, tenant_id=self.tenant_a)

        # Simulate ransomware modifying off-host mirror file
        remote_key = receipt.remote_uri.replace(f"s3://{self.replicator.bucket_name}/", "")
        offhost_file = os.path.join(self.s3_mirror_dir, remote_key)
        with open(offhost_file, "wb") as f:
            f.write(b"RANSOMWARE_ENCRYPTED_MUTATION_DATA")

        with self.assertRaises(BackupSecurityViolationError):
            self.replicator.verify_offhost_object(receipt.receipt_id, requesting_tenant_id=self.tenant_a)

    def test_07_tenant_isolation_in_offhost_backup_access(self):
        """Verify Tenant B cannot access or restore Tenant A's off-host backup."""
        wal_file = os.path.join(self.test_dir.name, "000000010000000000000004")
        with open(wal_file, "wb") as f:
            f.write(b"TENANT_A_CONFIDENTIAL_WAL")

        receipt = self.replicator.replicate_wal_segment(wal_file, tenant_id=self.tenant_a)

        # Tenant B requests verification
        with self.assertRaises(BackupSecurityViolationError) as ctx:
            self.replicator.verify_offhost_object(receipt.receipt_id, requesting_tenant_id=self.tenant_b)
        self.assertIn("Access denied", str(ctx.exception))

    def test_08_immutable_worm_retention_blocks_premature_deletion(self):
        """Verify WORM retention lock strictly rejects deletion of active off-host backups."""
        wal_file = os.path.join(self.test_dir.name, "000000010000000000000005")
        with open(wal_file, "wb") as f:
            f.write(b"WORM_IMMUTABLE_BACKUP")

        receipt = self.replicator.replicate_wal_segment(wal_file, tenant_id=self.tenant_a, retention_days=30)
        success, msg = backup_security_manager.attempt_delete_backup(receipt.envelope_id, requesting_tenant_id=self.tenant_a)
        self.assertFalse(success)
        self.assertIn("BLOCKED: Immutable retention lock active", msg)

    def test_09_complete_offhost_disaster_recovery_restoration_drill(self):
        """Verify restoring off-host bundle to clean environment succeeds with intact database."""
        db_file = os.path.join(self.test_dir.name, "prod_sample.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE tenants (tenant_id TEXT PRIMARY KEY, name TEXT);")
        conn.execute("INSERT INTO tenants VALUES (?, 'Alpha Enterprise Corp');", (self.tenant_a,))
        conn.commit()
        conn.close()

        receipt = self.replicator.replicate_sqlite_snapshot(db_file, tenant_id=self.tenant_a)

        # Execute restore drill into clean isolated directory
        target_restore_dir = os.path.join(self.test_dir.name, "replacement_env")
        report = self.replicator.execute_offhost_disaster_recovery_drill(
            receipt_id=receipt.receipt_id,
            target_dir=target_restore_dir,
            requesting_tenant_id=self.tenant_a
        )

        self.assertEqual(report.verdict, "QUALIFIED_PASS")
        self.assertEqual(report.database_integrity, "VERIFIED_OK")
        self.assertTrue(report.tenant_isolation_verified)

    def test_10_standardized_rto_and_rpo_measurement(self):
        """Verify standardized RTO and RPO metrics reporting resolving BLK-12."""
        db_file = os.path.join(self.test_dir.name, "metrics_sample.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE tenants (tenant_id TEXT PRIMARY KEY, name TEXT);")
        conn.execute("INSERT INTO tenants VALUES (?, 'Metrics Corp');", (self.tenant_a,))
        conn.commit()
        conn.close()

        receipt = self.replicator.replicate_sqlite_snapshot(db_file, tenant_id=self.tenant_a)
        target_dir = os.path.join(self.test_dir.name, "metrics_env")
        report = self.replicator.execute_offhost_disaster_recovery_drill(
            receipt_id=receipt.receipt_id,
            target_dir=target_dir,
            requesting_tenant_id=self.tenant_a
        )

        # Standardized RTO and RPO bounds
        self.assertIsInstance(report.rto_seconds, float)
        self.assertGreater(report.rto_seconds, 0.0)
        self.assertLess(report.rto_seconds, 2.0, "SQLite drill RTO must be < 2000ms (2.0s)")
        self.assertEqual(report.rpo_seconds, 0.0, "Snapshot restore RPO must be 0.0s (zero pre-disaster loss)")


if __name__ == "__main__":
    unittest.main()
