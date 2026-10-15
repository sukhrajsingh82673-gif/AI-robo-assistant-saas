"""
ZONATA Enterprise SaaS — PostgreSQL 16 Continuous WAL Archiving & PITR Qualification Suite
5-Test Disaster Recovery & Point-In-Time Restoration Suite

Verifies:
1. PostgreSQL 16 engine configuration: wal_level=replica, archive_mode=on, archive_command active
2. Consistent non-blocking physical base backup creation via pg_basebackup with SHA-256 manifest
3. Continuous WAL segment archiving and archive integrity validation
4. End-to-end Point-In-Time Recovery (PITR) drill to exact UTC target:
   - Pre-target baseline dataset restored and checksum verified
   - Post-target loss dataset completely absent
   - Server promoted to read-write mode
   - RTO (< 300s) and RPO (0 data loss of pre-target transactions) measured
   - Original primary instance untouched
5. Negative-path validation ensuring missing WAL archive fails safely without false recovery
"""

import os
import sys
import time
import json
import uuid
import hashlib
import unittest
import subprocess
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.postgres_disaster_recovery import PostgresDisasterRecoveryManager


def is_docker_available() -> bool:
    """Detect if Docker daemon is accessible in current execution environment."""
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return res.returncode == 0
    except Exception:
        return False


def run_cmd(cmd: List[str], check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
    """Helper to run CLI commands with project root cwd."""
    return subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=check
    )


@unittest.skipUnless(is_docker_available(), "Docker daemon not available in local PRoot/Termux environment; qualified in Linux CI")
class TestPostgreSQLWalPitrDrill(unittest.TestCase):
    """
    Dedicated qualification suite for PostgreSQL 16 Continuous WAL Archiving
    and Point-In-Time Recovery (PITR).
    """

    @classmethod
    def setUpClass(cls):
        cls.compose_file = os.path.join(PROJECT_ROOT, "docker-compose.prod.yml")
        cls.manager = PostgresDisasterRecoveryManager(
            compose_file="docker-compose.prod.yml",
            postgres_user="zonata_admin",
            postgres_db="zonata_production",
            project_root=PROJECT_ROOT
        )

    # =========================================================================
    # TEST 1: WAL Archiving Configuration & Engine Readiness
    # =========================================================================
    def test_01_wal_archiving_configuration_and_engine_readiness(self):
        """Verifies PostgreSQL 16 engine version, wal_level, archive_mode, and archive_command."""
        config = self.manager.get_wal_archiving_config()

        # 1. Verify wal_level is replica or logical
        self.assertIn(
            config.wal_level.lower(),
            ("replica", "logical"),
            f"wal_level must be replica or logical for PITR, got: {config.wal_level}"
        )

        # 2. Verify archive_mode is enabled
        self.assertIn(
            config.archive_mode.lower(),
            ("on", "always"),
            f"archive_mode must be 'on' or 'always', got: {config.archive_mode}"
        )

        # 3. Verify archive_command is configured
        self.assertTrue(
            bool(config.archive_command.strip()),
            "archive_command must not be empty"
        )
        self.assertIn(
            "wal_archive",
            config.archive_command,
            f"archive_command must target wal_archive directory, got: {config.archive_command}"
        )

        # 4. Verify archive_timeout
        self.assertGreater(
            config.archive_timeout,
            0,
            f"archive_timeout must be positive, got: {config.archive_timeout}"
        )

        # 5. Verify PostgreSQL version is 16
        ver_str = self.manager.execute_sql("SELECT version();")
        self.assertIn("PostgreSQL 16", ver_str, f"Expected PostgreSQL 16 engine, got: {ver_str}")

    # =========================================================================
    # TEST 2: Consistent Base Backup Creation & Integrity
    # =========================================================================
    def test_02_consistent_base_backup_creation_and_integrity(self):
        """Verifies pg_basebackup execution, physical backup layout, and SHA-256 checksum."""
        backup_name = f"qual_base_{uuid.uuid4().hex[:8]}"
        manifest = self.manager.create_base_backup(backup_name)

        # Verify manifest attributes
        self.assertEqual(manifest.verification_status, "VERIFIED")
        self.assertGreater(manifest.size_bytes, 10 * 1024 * 1024, "Base backup must be > 10MB")
        self.assertEqual(len(manifest.sha256_checksum), 64, "Checksum must be 64-char hex SHA-256")

        # Verify backup files via docker exec
        ls_res = self.manager.run_docker_exec(
            ["ls", "-1", f"/var/lib/postgresql/base_backups/{backup_name}"],
            user="postgres"
        )
        self.assertEqual(ls_res.returncode, 0)
        files = set(ls_res.stdout.strip().splitlines())
        self.assertIn("PG_VERSION", files, "PG_VERSION missing from base backup")
        self.assertIn("backup_label", files, "backup_label missing from base backup")
        self.assertIn("base", files, "base data directory missing from base backup")

    # =========================================================================
    # TEST 3: WAL Segment Archiving and Retrieval
    # =========================================================================
    def test_03_wal_segment_archiving_and_retrieval(self):
        """Verifies that forced WAL switch archives a valid 16MB WAL segment."""
        # Insert a marker transaction to generate WAL activity
        marker_id = f"wal_marker_{uuid.uuid4().hex[:8]}"
        self.manager.execute_sql(f"""
            INSERT INTO tenants (tenant_id, name, created_at)
            VALUES ('{marker_id}', 'WAL Archival Test Tenant', EXTRACT(EPOCH FROM NOW()))
            ON CONFLICT (tenant_id) DO NOTHING;
        """)

        # Force WAL switch
        switched_wal = self.manager.trigger_wal_switch()
        time.sleep(2)

        # Verify WAL segment files are present in archive
        archived_wals = self.manager.list_archived_wals()
        self.assertGreater(
            len(archived_wals),
            0,
            "Expected at least one archived WAL segment in /var/lib/postgresql/wal_archive"
        )

        # Inspect the first archived WAL segment file size (must be 16MB = 16777216 bytes)
        target_wal = archived_wals[-1]
        size_res = self.manager.run_docker_exec(
            ["stat", "-c", "%s", f"/var/lib/postgresql/wal_archive/{target_wal}"],
            user="postgres"
        )
        self.assertEqual(size_res.returncode, 0)
        wal_size = int(size_res.stdout.strip())
        self.assertEqual(
            wal_size,
            16 * 1024 * 1024,
            f"PostgreSQL WAL segment must be exactly 16MB (16777216 bytes), got: {wal_size}"
        )

        # Cleanup test marker
        self.manager.execute_sql(f"DELETE FROM tenants WHERE tenant_id = '{marker_id}';")

    # =========================================================================
    # TEST 4: End-to-End Point-In-Time Recovery (PITR) Drill Execution
    # =========================================================================
    def test_04_point_in_time_recovery_drill_execution(self):
        """
        Executes a real Point-In-Time Recovery drill against an isolated instance:
        - Commits baseline dataset T1
        - Takes consistent base backup
        - Selects exact UTC target timestamp
        - Commits unwanted / loss dataset T2
        - Restores base backup and replays WAL up to target
        - Validates T1 present, T2 absent, and DB promoted to read-write
        - Measures RTO (< 300s) and RPO (0s)
        """
        drill_id = f"pitr_drill_{uuid.uuid4().hex[:8]}"
        t_drill_start = time.time()

        # Step 1: Insert Baseline Dataset T1
        base_tenant = f"tnt_base_{drill_id}"
        self.manager.execute_sql(f"""
            INSERT INTO tenants (tenant_id, name, created_at)
            VALUES ('{base_tenant}', 'Baseline Enterprise Tenant', EXTRACT(EPOCH FROM NOW()))
            ON CONFLICT (tenant_id) DO NOTHING;
        """)

        base_customers = [
            f"cust_{drill_id}_base_01",
            f"cust_{drill_id}_base_02",
            f"cust_{drill_id}_base_03"
        ]
        for cid in base_customers:
            self.manager.execute_sql(f"""
                INSERT INTO crm_customers (customer_id, tenant_id, company_id, name, created_at, updated_at)
                VALUES ('{cid}', '{base_tenant}', 'comp_pitr', 'Base Customer', EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW()))
                ON CONFLICT (customer_id) DO NOTHING;
            """)

        # Deterministic baseline checksum
        base_checksum = hashlib.sha256("".join(sorted(base_customers)).encode("utf-8")).hexdigest()

        # Step 2: Create Consistent Base Backup
        base_backup_name = f"backup_{drill_id}"
        manifest = self.manager.create_base_backup(base_backup_name)
        self.assertEqual(manifest.verification_status, "VERIFIED")

        # Step 3: Record Recovery Target Time (UTC)
        # Select target 1 second after base backup, with clock separation
        time.sleep(1)
        raw_target_time = self.manager.execute_sql("SELECT NOW() AT TIME ZONE 'UTC';")
        target_timestamp = raw_target_time.strip()
        time.sleep(2)

        # Step 4: Insert Simulated Unwanted / Loss Transactions T2 (post-target)
        loss_customers = [
            f"cust_{drill_id}_loss_01",
            f"cust_{drill_id}_loss_02"
        ]
        for cid in loss_customers:
            self.manager.execute_sql(f"""
                INSERT INTO crm_customers (customer_id, tenant_id, company_id, name, created_at, updated_at)
                VALUES ('{cid}', '{base_tenant}', 'comp_pitr', 'Accidental Post-Target Loss', EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW()))
                ON CONFLICT (customer_id) DO NOTHING;
            """)

        # Confirm loss records are present in primary DB
        primary_loss_cnt = int(self.manager.execute_sql(f"""
            SELECT count(*) FROM crm_customers WHERE customer_id LIKE 'cust_{drill_id}_loss_%';
        """))
        self.assertEqual(primary_loss_cnt, 2, "Post-target loss records must be present in primary")

        # Step 5: Force WAL Segment Archiving
        self.manager.trigger_wal_switch()
        time.sleep(2)

        # Step 6: Prepare Isolated Recovery Environment
        # Clean any stale recovery containers/volumes
        run_cmd(["docker", "rm", "-f", "postgres-pitr-recovery"], check=False)
        run_cmd(["docker", "volume", "rm", "-f", "postgres-recovery-data"], check=False)
        run_cmd(["docker", "volume", "create", "postgres-recovery-data"], check=True)

        # Populate recovery volume from base backup and configure recovery.signal
        prep_cmd = [
            "docker", "run", "--rm",
            "-v", "postgres-base-backups:/backups:ro",
            "-v", "postgres-recovery-data:/target",
            "alpine", "sh", "-c", f"""
            cp -a /backups/{base_backup_name}/. /target/
            rm -f /target/postmaster.pid
            touch /target/recovery.signal
            cat << 'EOF' >> /target/postgresql.auto.conf
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '{target_timestamp}'
recovery_target_action = 'promote'
port = 5432
EOF
            chown -R 70:70 /target
            chmod 700 /target
            """
        ]
        prep_res = run_cmd(prep_cmd, check=True, timeout=60)
        self.assertEqual(prep_res.returncode, 0)

        # Step 7: Launch Isolated Recovery PostgreSQL Container on Port 5433
        t_restore_start = time.time()
        launch_cmd = [
            "docker", "run", "-d",
            "--name", "postgres-pitr-recovery",
            "-v", "postgres-recovery-data:/var/lib/postgresql/data",
            "-v", "postgres-wal-archive:/var/lib/postgresql/wal_archive:ro",
            "-p", "5433:5432",
            "-e", "POSTGRES_USER=zonata_admin",
            "-e", "POSTGRES_PASSWORD=zonata_secure_prod_password_2026",
            "-e", "POSTGRES_DB=zonata_production",
            "postgres:16-alpine"
        ]
        launch_res = run_cmd(launch_cmd, check=True)
        self.assertEqual(launch_res.returncode, 0)

        # Step 8: Poll Recovery Promotion and Readiness
        promoted = False
        for _ in range(30):
            check_res = run_cmd([
                "docker", "exec", "postgres-pitr-recovery",
                "pg_isready", "-U", "zonata_admin", "-d", "zonata_production"
            ], check=False)
            if check_res.returncode == 0:
                # Confirm recovery mode has promoted to read-write
                in_rec = run_cmd([
                    "docker", "exec", "postgres-pitr-recovery",
                    "psql", "-U", "zonata_admin", "-d", "zonata_production",
                    "-tAc", "SELECT pg_is_in_recovery();"
                ], check=False)
                if in_rec.returncode == 0 and in_rec.stdout.strip() == "f":
                    promoted = True
                    break
            time.sleep(1)

        t_restore_end = time.time()
        rto_seconds = round(t_restore_end - t_restore_start, 2)

        # Retrieve recovery logs
        log_res = run_cmd(["docker", "logs", "postgres-pitr-recovery"], check=False)
        recovery_logs = log_res.stdout + log_res.stderr

        self.assertTrue(promoted, f"PostgreSQL recovery instance failed to promote to read-write within 30s.\nLogs:\n{recovery_logs[-2000:]}")
        self.assertLess(rto_seconds, 300.0, f"RTO target < 300s violated! Measured RTO: {rto_seconds}s")

        # Step 9: Validate Data State in Recovered Database
        # A. Baseline dataset T1 MUST BE PRESENT
        rec_base_res = run_cmd([
            "docker", "exec", "postgres-pitr-recovery",
            "psql", "-U", "zonata_admin", "-d", "zonata_production",
            "-tAc", f"SELECT customer_id FROM crm_customers WHERE customer_id LIKE 'cust_{drill_id}_base_%' ORDER BY customer_id;"
        ], check=True)
        rec_base_ids = rec_base_res.stdout.strip().splitlines()
        self.assertEqual(len(rec_base_ids), 3, f"Expected 3 baseline customers, got: {rec_base_ids}")
        rec_checksum = hashlib.sha256("".join(rec_base_ids).encode("utf-8")).hexdigest()
        self.assertEqual(rec_checksum, base_checksum, "Baseline dataset cryptographic checksum mismatch!")

        # B. Post-target loss dataset T2 MUST BE COMPLETELY ABSENT
        rec_loss_res = run_cmd([
            "docker", "exec", "postgres-pitr-recovery",
            "psql", "-U", "zonata_admin", "-d", "zonata_production",
            "-tAc", f"SELECT count(*) FROM crm_customers WHERE customer_id LIKE 'cust_{drill_id}_loss_%';"
        ], check=True)
        rec_loss_cnt = int(rec_loss_res.stdout.strip())
        self.assertEqual(
            rec_loss_cnt,
            0,
            f"Point-In-Time Recovery Failed! {rec_loss_cnt} post-target loss records were restored!"
        )

        # C. Confirm write ability on recovered instance
        write_test_id = f"cust_{drill_id}_post_rec"
        write_res = run_cmd([
            "docker", "exec", "postgres-pitr-recovery",
            "psql", "-U", "zonata_admin", "-d", "zonata_production",
            "-tAc", f"""
                INSERT INTO crm_customers (customer_id, tenant_id, company_id, name, created_at, updated_at)
                VALUES ('{write_test_id}', '{base_tenant}', 'comp_pitr', 'Post Recovery Test', EXTRACT(EPOCH FROM NOW()), EXTRACT(EPOCH FROM NOW()))
                RETURNING customer_id;
            """
        ], check=True)
        self.assertEqual(write_res.stdout.strip(), write_test_id)

        # Step 10: Verify Original Primary Instance Remains UNTOUCHED
        primary_loss_check = int(self.manager.execute_sql(f"""
            SELECT count(*) FROM crm_customers WHERE customer_id LIKE 'cust_{drill_id}_loss_%';
        """))
        self.assertEqual(
            primary_loss_check,
            2,
            "Primary database instance was mutated during recovery! Isolation failure."
        )

        # Teardown recovery instance
        run_cmd(["docker", "rm", "-f", "postgres-pitr-recovery"], check=False)
        run_cmd(["docker", "volume", "rm", "-f", "postgres-recovery-data"], check=False)

        # Cleanup drill records on primary
        self.manager.execute_sql(f"DELETE FROM crm_customers WHERE tenant_id = '{base_tenant}';")
        self.manager.execute_sql(f"DELETE FROM tenants WHERE tenant_id = '{base_tenant}';")

    # =========================================================================
    # TEST 5: Negative Test — Missing WAL Archive Fails Safely
    # =========================================================================
    def test_05_negative_test_missing_wal_fails_safely(self):
        """
        Verifies that recovery with missing or corrupt WAL archive fails closed
        and does not falsely claim recovery or promote corrupt state.
        """
        drill_id = f"pitr_neg_{uuid.uuid4().hex[:8]}"

        # Base backup
        base_backup_name = f"backup_{drill_id}"
        self.manager.create_base_backup(base_backup_name)

        run_cmd(["docker", "rm", "-f", "postgres-pitr-negative"], check=False)
        run_cmd(["docker", "volume", "rm", "-f", "postgres-neg-data"], check=False)
        run_cmd(["docker", "volume", "create", "postgres-neg-data"], check=True)

        # Prepare recovery volume with invalid restore_command
        future_time = "2099-01-01 00:00:00.000000+00"
        prep_cmd = [
            "docker", "run", "--rm",
            "-v", "postgres-base-backups:/backups:ro",
            "-v", "postgres-neg-data:/target",
            "alpine", "sh", "-c", f"""
            cp -a /backups/{base_backup_name}/. /target/
            rm -f /target/postmaster.pid
            touch /target/recovery.signal
            cat << 'EOF' >> /target/postgresql.auto.conf
restore_command = 'cp /nonexistent_archive/%f %p'
recovery_target_time = '{future_time}'
recovery_target_action = 'promote'
port = 5432
EOF
            chown -R 70:70 /target
            chmod 700 /target
            """
        ]
        run_cmd(prep_cmd, check=True, timeout=60)

        # Launch negative container
        launch_cmd = [
            "docker", "run", "-d",
            "--name", "postgres-pitr-negative",
            "-v", "postgres-neg-data:/var/lib/postgresql/data",
            "-p", "5434:5432",
            "-e", "POSTGRES_USER=zonata_admin",
            "-e", "POSTGRES_PASSWORD=zonata_secure_prod_password_2026",
            "-e", "POSTGRES_DB=zonata_production",
            "postgres:16-alpine"
        ]
        run_cmd(launch_cmd, check=True)

        time.sleep(5)

        # Check container state: it must NOT have promoted to normal operation
        check_promoted = run_cmd([
            "docker", "exec", "postgres-pitr-negative",
            "psql", "-U", "zonata_admin", "-d", "zonata_production",
            "-tAc", "SELECT pg_is_in_recovery();"
        ], check=False)

        # It must either fail to connect or remain in recovery mode ('t')
        if check_promoted.returncode == 0:
            self.assertEqual(
                check_promoted.stdout.strip(),
                "t",
                "Negative recovery test failed: database promoted despite missing WAL segments!"
            )

        # Inspect logs for expected failure message
        log_res = run_cmd(["docker", "logs", "postgres-pitr-negative"], check=False)
        logs = log_res.stdout + log_res.stderr
        self.assertTrue(
            "nonexistent_archive" in logs or "No such file or directory" in logs or "could not open file" in logs or "could not restore file" in logs,
            f"Expected archive retrieval error in logs, got:\n{logs[-1000:]}"
        )

        # Cleanup negative test
        run_cmd(["docker", "rm", "-f", "postgres-pitr-negative"], check=False)
        run_cmd(["docker", "volume", "rm", "-f", "postgres-neg-data"], check=False)


if __name__ == "__main__":
    unittest.main()
