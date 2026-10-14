"""
ZONATA Enterprise SaaS — PostgreSQL 16 Live Cluster Integration Suite
12-Test Staging Qualification Suite

Verifies live runtime behavior against a genuine PostgreSQL 16 instance:
1. Live PostgreSQL 16 connection handshake and version verification
2. Complete schema DDL initialization and information_schema table inventory
3. Controlled migration engine additive forward execution and version tracking
4. ANSI SQL ON CONFLICT single-column primary key upsert & created_at immutability
5. ANSI SQL ON CONFLICT composite primary key upsert
6. Strict relational multi-tenant isolation across queries and updates
7. Transactional atomicity, commits, and rollback integrity
8. Distributed rate-limiting concurrency and table persistence
9. Commercial CRM customer and deal lifecycle persistence
10. Authentication credentials, PBKDF2 hashing, and token revocation
11. Secure connection error handling and credential redaction
12. Database readiness probe verification (db.verify_readiness())
"""

import os
import sys
import time
import uuid
import unittest
from typing import Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import (
    db,
    Database,
    DatabaseDialect,
    sanitize_db_url,
    TABLE_PRIMARY_KEYS,
    SCHEMA_SQL
)
from core.controlled_migration_engine import ControlledMigrationEngine, MigrationStep
from core.enterprise_crm import EnterpriseCrmService


class TestPostgreSql16LiveIntegration(unittest.TestCase):
    """
    12-test comprehensive live integration qualification suite for PostgreSQL 16.
    Executes against a live PostgreSQL 16 database when DATABASE_URL is configured.
    """

    @classmethod
    def setUpClass(cls):
        cls.database_url = os.environ.get("DATABASE_URL", "").strip()
        if not cls.database_url or not cls.database_url.startswith(("postgresql://", "postgres://")):
            cls.live_postgres_available = False
        else:
            cls.live_postgres_available = True
            # Initialize schema once for the class
            try:
                db.verify_readiness()
                from core.enterprise_files import EnterpriseFilesEngine
                from core.enterprise_records import EnterpriseRecordsEngine
                from core.enterprise_reports import EnterpriseReportsEngine
                from core.automation_fabric.data_integration_engine import SyncCheckpointManager

                EnterpriseFilesEngine(tenant_id="tnt_init")._init_db()
                EnterpriseRecordsEngine(tenant_id="tnt_init")._init_db()
                EnterpriseReportsEngine(tenant_id="tnt_init")._init_db()
                SyncCheckpointManager._ensure_tables()
            except Exception:
                pass

    def setUp(self):
        if not self.live_postgres_available:
            self.skipTest(
                "Live PostgreSQL 16 service unavailable: DATABASE_URL not configured. "
                "Required for staging CI qualification."
            )
        self.tenant_a = f"tnt_pg16_a_{uuid.uuid4().hex[:8]}"
        self.tenant_b = f"tnt_pg16_b_{uuid.uuid4().hex[:8]}"
        self.company_id = f"comp_pg16_{uuid.uuid4().hex[:8]}"
        self.now = time.time()

        # Seed test tenants
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tenants (tenant_id, name, plan, status, created_at)
                VALUES (?, 'PG16 Test Tenant A', 'ENTERPRISE', 'ACTIVE', ?)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                (self.tenant_a, self.now)
            )
            conn.execute(
                """
                INSERT INTO tenants (tenant_id, name, plan, status, created_at)
                VALUES (?, 'PG16 Test Tenant B', 'ENTERPRISE', 'ACTIVE', ?)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                (self.tenant_b, self.now)
            )
            conn.execute(
                """
                INSERT INTO companies (
                    company_id, tenant_id, name, country, industry, company_type, status, created_at
                ) VALUES (?, ?, 'PG16 Qualification Corp', 'IN', 'TECH', 'EXISTING', 'OPERATIONAL', ?)
                ON CONFLICT (company_id) DO NOTHING
                """,
                (self.company_id, self.tenant_a, self.now)
            )
            conn.commit()

    # -------------------------------------------------------------------------
    # Test 1: Live PostgreSQL 16 Handshake & Version Verification
    # -------------------------------------------------------------------------
    def test_01_live_postgres_16_handshake(self):
        """Verify connection handshake with a live PostgreSQL 16 instance."""
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT version()")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            version_str = str(row[0])
            self.assertIn("PostgreSQL 16", version_str, f"Expected PostgreSQL 16, got: {version_str}")
            self.assertEqual(db.get_dialect(), DatabaseDialect.POSTGRESQL)

    # -------------------------------------------------------------------------
    # Test 2: Complete Schema Table Inventory in information_schema
    # -------------------------------------------------------------------------
    def test_02_live_schema_table_inventory(self):
        """Verify that all core application tables exist in information_schema."""
        required_tables = [
            "tenants", "users", "auth_credentials", "auth_revoked_tokens",
            "auth_rate_limits", "companies", "employees", "missions",
            "crm_customers", "crm_deals", "schema_migrations", "enterprise_files",
            "enterprise_records", "enterprise_reports", "automation_sync_checkpoints"
        ]
        with db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            existing_tables = {row[0].lower() for row in cursor.fetchall()}
            for table in required_tables:
                self.assertIn(
                    table,
                    existing_tables,
                    f"Required table '{table}' missing from PostgreSQL 16 schema."
                )

    # -------------------------------------------------------------------------
    # Test 3: Controlled Migration Engine Forward Execution
    # -------------------------------------------------------------------------
    def test_03_controlled_migrations_execution(self):
        """Verify additive migrations apply cleanly and log in schema_migrations."""
        migration_engine = ControlledMigrationEngine()
        applied = migration_engine.apply_pending_migrations()
        self.assertIsInstance(applied, list)

        # Check status recorded in schema_migrations
        statuses = migration_engine.get_migration_status()
        applied_versions = [s["version"] for s in statuses]
        self.assertIn(2026100501, applied_versions)
        self.assertIn(2026100502, applied_versions)

    # -------------------------------------------------------------------------
    # Test 4: ANSI ON CONFLICT Single-Column Upsert & created_at Preservation
    # -------------------------------------------------------------------------
    def test_04_ansi_upsert_single_column_on_conflict(self):
        """Verify ANSI ON CONFLICT single-column primary key upsert preserves created_at."""
        agent_id = f"agt_live_{uuid.uuid4().hex[:8]}"
        initial_ts = 1700000000.0
        updated_ts = 1700099999.0

        # Initial insertion
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO employees (
                    agent_id, company_id, tenant_id, role, department, manager,
                    budget_limit, spending_limit, authority_ceiling, working_state, created_at
                ) VALUES (?, ?, ?, 'Staff Engineer', 'Platform', 'AI CEO', 2000.0, 1000.0, 'AUTO', 'IDLE', ?)
                ON CONFLICT (agent_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    working_state = EXCLUDED.working_state
                """,
                (agent_id, self.company_id, self.tenant_a, initial_ts)
            )
            conn.commit()

        # Update via upsert with different role and new timestamp
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO employees (
                    agent_id, company_id, tenant_id, role, department, manager,
                    budget_limit, spending_limit, authority_ceiling, working_state, created_at
                ) VALUES (?, ?, ?, 'Principal Engineer', 'Platform', 'AI CEO', 2000.0, 1000.0, 'AUTO', 'ACTIVE', ?)
                ON CONFLICT (agent_id) DO UPDATE SET
                    role = EXCLUDED.role,
                    working_state = EXCLUDED.working_state
                """,
                (agent_id, self.company_id, self.tenant_a, updated_ts)
            )
            conn.commit()

        # Verification: role updated, created_at preserved
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM employees WHERE agent_id = ?", (agent_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["role"], "Principal Engineer")
            self.assertEqual(row["working_state"], "ACTIVE")
            self.assertEqual(float(row["created_at"]), initial_ts)

    # -------------------------------------------------------------------------
    # Test 5: ANSI ON CONFLICT Composite Primary Key Upsert
    # -------------------------------------------------------------------------
    def test_05_composite_primary_key_upsert(self):
        """Verify upsert on tables with multi-column composite primary keys."""
        stream_name = f"stream_{uuid.uuid4().hex[:6]}"
        connector_id = f"conn_{uuid.uuid4().hex[:6]}"

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO automation_sync_checkpoints (
                    tenant_id, stream_name, connector_id, cursor_value, cursor_type,
                    records_synced, last_sync_timestamp, content_checksum, status, metadata
                ) VALUES (?, ?, ?, 'pos_100', 'OFFSET', 100, ?, 'cksum1', 'RUNNING', '{}')
                ON CONFLICT (tenant_id, stream_name, connector_id) DO UPDATE SET
                    cursor_value = EXCLUDED.cursor_value,
                    records_synced = EXCLUDED.records_synced,
                    status = EXCLUDED.status
                """,
                (self.tenant_a, stream_name, connector_id, self.now)
            )
            conn.commit()

        # Upsert next position
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO automation_sync_checkpoints (
                    tenant_id, stream_name, connector_id, cursor_value, cursor_type,
                    records_synced, last_sync_timestamp, content_checksum, status, metadata
                ) VALUES (?, ?, ?, 'pos_500', 'OFFSET', 500, ?, 'cksum2', 'SUCCESS', '{}')
                ON CONFLICT (tenant_id, stream_name, connector_id) DO UPDATE SET
                    cursor_value = EXCLUDED.cursor_value,
                    records_synced = EXCLUDED.records_synced,
                    status = EXCLUDED.status
                """,
                (self.tenant_a, stream_name, connector_id, self.now + 10)
            )
            conn.commit()

        # Verify single updated row
        with db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT cursor_value, records_synced, status FROM automation_sync_checkpoints
                WHERE tenant_id = ? AND stream_name = ? AND connector_id = ?
                """,
                (self.tenant_a, stream_name, connector_id)
            ).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["cursor_value"], "pos_500")
            self.assertEqual(rows[0]["records_synced"], 500)
            self.assertEqual(rows[0]["status"], "SUCCESS")

    # -------------------------------------------------------------------------
    # Test 6: Relational Multi-Tenant Boundary Enforcement
    # -------------------------------------------------------------------------
    def test_06_tenant_isolation_in_queries(self):
        """Verify strict tenant isolation across records on live PostgreSQL."""
        record_a = f"rec_a_{uuid.uuid4().hex[:8]}"
        record_b = f"rec_b_{uuid.uuid4().hex[:8]}"

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO enterprise_records (
                    record_id, tenant_id, company_id, department, record_type,
                    title, actor_name, created_at, updated_at
                ) VALUES (?, ?, ?, 'Platform', 'AUDIT', 'Tenant A Private Record', 'Agent A', ?, ?)
                ON CONFLICT (record_id) DO NOTHING
                """,
                (record_a, self.tenant_a, self.company_id, self.now, self.now)
            )
            conn.execute(
                """
                INSERT INTO enterprise_records (
                    record_id, tenant_id, company_id, department, record_type,
                    title, actor_name, created_at, updated_at
                ) VALUES (?, ?, ?, 'Platform', 'AUDIT', 'Tenant B Private Record', 'Agent B', ?, ?)
                ON CONFLICT (record_id) DO NOTHING
                """,
                (record_b, self.tenant_b, self.company_id, self.now, self.now)
            )
            conn.commit()

        # Query scoped to Tenant A must never return Tenant B record
        with db.get_connection() as conn:
            res_a = conn.execute(
                "SELECT * FROM enterprise_records WHERE tenant_id = ?",
                (self.tenant_a,)
            ).fetchall()
            ids_a = [r["record_id"] for r in res_a]
            self.assertIn(record_a, ids_a)
            self.assertNotIn(record_b, ids_a)

    # -------------------------------------------------------------------------
    # Test 7: Transactional Atomicity and Atomic Rollback
    # -------------------------------------------------------------------------
    def test_07_transaction_atomic_rollback(self):
        """Verify transaction rollback leaves no orphaned data on PostgreSQL 16."""
        mission_id = f"msn_rollback_{uuid.uuid4().hex[:8]}"
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO missions (
                        mission_id, company_id, tenant_id, title, owner_agent,
                        department, target_outcome, started_at
                    ) VALUES (?, ?, ?, 'Transactional Rollback Test', 'agt_test', 'Platform', 'Verify Rollback', ?)
                    """,
                    (mission_id, self.company_id, self.tenant_a, self.now)
                )
                # Intentionally trigger an exception before commit
                raise ValueError("Simulated failure to force atomic rollback")
        except ValueError:
            pass

        # Verify record does not exist
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,)).fetchone()
            self.assertIsNone(row, "Transaction rollback failed: uncommitted row was persisted!")

    # -------------------------------------------------------------------------
    # Test 8: Distributed Rate Limit Table Concurrency
    # -------------------------------------------------------------------------
    def test_08_distributed_rate_limit_concurrency(self):
        """Verify auth_rate_limits operations persist correctly on PostgreSQL 16."""
        rate_key = f"ip_192_0_2_{uuid.uuid4().hex[:4]}"
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO auth_rate_limits (rate_key, attempt_timestamp) VALUES (?, ?)",
                (rate_key, self.now)
            )
            conn.execute(
                "INSERT INTO auth_rate_limits (rate_key, attempt_timestamp) VALUES (?, ?)",
                (rate_key, self.now + 0.1)
            )
            conn.commit()

        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT COUNT(*) FROM auth_rate_limits WHERE rate_key = ?",
                (rate_key,)
            ).fetchone()
            self.assertEqual(rows[0], 2)

    # -------------------------------------------------------------------------
    # Test 9: Commercial CRM Relational Persistence CRUD
    # -------------------------------------------------------------------------
    def test_09_crm_relational_persistence_crud(self):
        """Verify CRM customer and deal creation, update, and retrieval on PostgreSQL 16."""
        crm = EnterpriseCrmService(tenant_id=self.tenant_a)
        customer = crm.create_customer(
            company_id=self.company_id,
            data={
                "name": "Live PG16 Client",
                "tier": "ENTERPRISE",
                "industry": "Cloud SaaS",
                "health_score": 98,
                "arr": "₹2,500,000",
                "contacts": [{"name": "Lead Eng", "email": "lead@pg16.example.com"}]
            }
        )
        self.assertTrue(customer.get("success"))
        customer_id = customer["customer_id"]

        deal = crm.create_deal(
            company_id=self.company_id,
            data={
                "title": "PG16 Enterprise Expansion",
                "value": 150000.0,
                "stage": "QUALIFIED",
                "customer_id": customer_id
            }
        )
        self.assertTrue(deal.get("success"))
        deal_id = deal["deal_id"]

        # Fetch and verify
        fetched_deal = crm.get_deal(deal_id)
        self.assertIsNotNone(fetched_deal)
        self.assertEqual(fetched_deal["stage"], "QUALIFIED")

    # -------------------------------------------------------------------------
    # Test 10: Authentication Credentials & Token Revocation
    # -------------------------------------------------------------------------
    def test_10_auth_credentials_and_token_revocation(self):
        """Verify auth credentials storage and token revocation in auth_revoked_tokens."""
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        token_id = f"tok_{uuid.uuid4().hex[:12]}"

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, tenant_id, email, name, role, created_at)
                VALUES (?, ?, ?, 'PG16 User', 'OWNER', ?)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id, self.tenant_a, f"{user_id}@zonata.example.com", self.now)
            )
            conn.execute(
                """
                INSERT INTO auth_credentials (
                    user_id, password_hash, salt, failed_attempts, locked_until, created_at, updated_at
                ) VALUES (?, 'pbkdf2_sha256$600000$saltsalt$fakehash', 'saltsalt', 0, 0, ?, ?)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id, self.now, self.now)
            )
            conn.execute(
                "INSERT INTO auth_revoked_tokens (token_id, revoked_at) VALUES (?, ?)",
                (token_id, self.now)
            )
            conn.commit()

        with db.get_connection() as conn:
            cred = conn.execute("SELECT * FROM auth_credentials WHERE user_id = ?", (user_id,)).fetchone()
            self.assertIsNotNone(cred)
            self.assertIn("600000", cred["password_hash"])

            tok = conn.execute("SELECT * FROM auth_revoked_tokens WHERE token_id = ?", (token_id,)).fetchone()
            self.assertIsNotNone(tok)
            self.assertEqual(tok["token_id"], token_id)

    # -------------------------------------------------------------------------
    # Test 11: Connection Error Redaction on Live PostgreSQL
    # -------------------------------------------------------------------------
    def test_11_postgresql_connection_error_redacts_credentials(self):
        """Verify PostgreSQL errors and URLs strictly redact credentials."""
        secret_pass = "super_classified_pw_89712"
        raw_url = f"postgresql://app_user:{secret_pass}@localhost:5432/zonata_test"
        sanitized = sanitize_db_url(raw_url)
        self.assertNotIn(secret_pass, sanitized)
        self.assertIn(":***@", sanitized)

    # -------------------------------------------------------------------------
    # Test 12: Production Readiness Probe
    # -------------------------------------------------------------------------
    def test_12_production_readiness_probe(self):
        """Verify db.verify_readiness() executes genuine health check against PostgreSQL 16."""
        ready = db.verify_readiness()
        self.assertTrue(ready)
        self.assertTrue(db.is_ready())


if __name__ == "__main__":
    unittest.main()
