"""
ZONATA Enterprise SaaS — Clean Production Mode & Safe Defaults Regression Suite
Verifies:
1. Production mode (APP_ENV=production) unconditionally suppresses demo seeding across all engines:
   - EnterpriseFinanceEngine
   - EnterpriseFilesEngine
   - EnterpriseRecordsEngine
   - EnterpriseReportsEngine
   - UniversalScheduleService
   - PluginsAndConnectionsService
   - GovernedCoworkerRegistry
2. Fresh database initialization presents clean, honest empty states.
3. Database engine dialect abstraction detects PostgreSQL URLs while maintaining SQLite local compatibility.
"""

import os
import sys
import time
import tempfile
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import Database, DatabaseDialect, db
from core.enterprise_finance import EnterpriseFinanceEngine
from core.enterprise_files import EnterpriseFilesEngine
from core.enterprise_records import EnterpriseRecordsEngine
from core.enterprise_reports import EnterpriseReportsEngine
from core.schedule_service import UniversalScheduleService
from core.plugins_service import PluginsAndConnectionsService
from core.coworker_governance import GovernedCoworkerRegistry
from core.db import configure_isolated_test_db

MODULE_TEMP_DIR = None
MODULE_ORIG_DB_PATH = None
MODULE_ORIG_ENV_DB_PATH = None

def setUpModule():
    global MODULE_TEMP_DIR, MODULE_ORIG_DB_PATH, MODULE_ORIG_ENV_DB_PATH
    MODULE_ORIG_DB_PATH = db.db_path
    MODULE_ORIG_ENV_DB_PATH = os.environ.get("ZONATA_DB_PATH")
    MODULE_TEMP_DIR = tempfile.TemporaryDirectory()
    isolated_db = os.path.join(MODULE_TEMP_DIR.name, "clean_prod_test_isolated.db")
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


class TestCleanProductionMode(unittest.TestCase):
    def setUp(self):
        self.orig_db_path = db.db_path
        self.orig_env_db_path = os.environ.get("ZONATA_DB_PATH")

        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.environ["ZONATA_DB_PATH"] = self.temp_db_path
        self.db = db
        self.db.set_db_path(self.temp_db_path)

        # Enforce production mode
        self.old_env = os.environ.get("APP_ENV")
        os.environ["APP_ENV"] = "production"

        # Create basic tenant
        with self.db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_prod_clean', 'Production Enterprise', ?)", (time.time(),))
            conn.commit()

    def tearDown(self):
        if self.old_env is not None:
            os.environ["APP_ENV"] = self.old_env
        else:
            os.environ.pop("APP_ENV", None)

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
            pass

    def test_01_clean_finance_engine(self):
        """In production, finance engine must not seed demo transactions or fake revenue."""
        fin = EnterpriseFinanceEngine(tenant_id="tnt_prod_clean")
        summary = fin.get_financial_summary(company_id="comp_clean_1")
        # Transactions and expenses must be empty
        txs = summary.get("recent_transactions", [])
        self.assertEqual(len(txs), 0)
        expenses = summary.get("recent_expenses", [])
        self.assertEqual(len(expenses), 0)

    def test_02_clean_files_engine(self):
        """In production, files engine must not seed demo files."""
        files_engine = EnterpriseFilesEngine(tenant_id="tnt_prod_clean")
        res = files_engine.list_files(company_id="comp_clean_1")
        self.assertEqual(len(res.get("files", [])), 0)
        self.assertEqual(res.get("total", 0), 0)

    def test_03_clean_records_engine(self):
        """In production, records engine must not seed demo governance records."""
        records_engine = EnterpriseRecordsEngine(tenant_id="tnt_prod_clean")
        res = records_engine.list_records(company_id="comp_clean_1")
        self.assertEqual(len(res.get("records", [])), 0)
        self.assertEqual(res.get("total", 0), 0)

    def test_04_clean_reports_engine(self):
        """In production, reports engine must not seed demo reports."""
        reports_engine = EnterpriseReportsEngine(tenant_id="tnt_prod_clean")
        reports = reports_engine.list_reports(company_id="comp_clean_1")
        self.assertEqual(len(reports), 0)

    def test_05_clean_schedule_service(self):
        """In production, schedule service must not seed demo calendar events."""
        sched = UniversalScheduleService(tenant_id="tnt_prod_clean")
        schedules = sched.list_schedules()
        self.assertEqual(len(schedules), 0)

    def test_06_clean_plugins_service(self):
        """In production, plugins service must not seed fake connected PMS/ERP systems."""
        plugins_svc = PluginsAndConnectionsService(tenant_id="tnt_prod_clean")
        conns = plugins_svc.list_connections()
        self.assertEqual(len(conns), 0)

    def test_07_clean_coworkers_service(self):
        """In production, coworker governance registry must not seed mock coworkers."""
        coworkers_registry = GovernedCoworkerRegistry(tenant_id="tnt_prod_clean")
        coworkers = coworkers_registry.list_coworkers()
        self.assertEqual(len(coworkers), 0)

    def test_08_database_dialect_abstraction(self):
        """Verify database engine dialect detection and abstraction."""
        # Default SQLite dialect
        self.assertEqual(self.db.get_dialect(), DatabaseDialect.SQLITE)
        self.assertFalse(self.db.is_postgresql())

        # Test PostgreSQL URL recognition
        old_url = os.environ.get("DATABASE_URL")
        try:
            os.environ["DATABASE_URL"] = "postgresql://zonata_admin:secret@pgcluster.internal:5432/zonata_db"
            pg_db = Database()
            self.assertEqual(pg_db.get_dialect(), DatabaseDialect.POSTGRESQL)
            self.assertTrue(pg_db.is_postgresql())
        finally:
            if old_url is not None:
                os.environ["DATABASE_URL"] = old_url
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_09_clean_vault_secrets(self):
        """In production, vault client must not seed fake stripe/salesforce master keys."""
        from core.vault_client import HashiCorpVaultClient
        vault = HashiCorpVaultClient()
        self.assertIsNone(vault.read_secret("payments/stripe", tenant_id="tnt_prod_clean"))
        self.assertIsNone(vault.read_secret("crm/salesforce", tenant_id="tnt_prod_clean"))

    def test_10_clean_executive_memory(self):
        """In production, executive memory must not seed fake hotel charters."""
        from core.layered_executive_memory import LayeredExecutiveMemory
        mem = LayeredExecutiveMemory(tenant_id="tnt_prod_clean", company_id="comp_clean_1")
        # Level 5 memory must be empty
        records = mem.query_memories(levels=[5])
        self.assertEqual(len(records), 0)

    def test_11_production_refuses_unintended_sqlite_fallback(self):
        """Verify production mode strictly fails closed against SQLite under all environment flags."""
        os.environ["APP_ENV"] = "production"

        # 1. Production with no DATABASE_URL must raise RuntimeError
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("ZONATA_ALLOW_SQLITE_IN_PRODUCTION", None)
        with self.assertRaises(RuntimeError) as ctx1:
            Database()
        self.assertIn("Direct SQLite fallback is prohibited in production mode", str(ctx1.exception))

        # 2. Production with explicit SQLite URL must raise RuntimeError
        os.environ["DATABASE_URL"] = "sqlite:///var/data/prod.db"
        with self.assertRaises(RuntimeError) as ctx2:
            Database()
        self.assertIn("Direct SQLite fallback is prohibited in production mode", str(ctx2.exception))

        # 3. Production with legacy override flag ZONATA_ALLOW_SQLITE_IN_PRODUCTION=1 MUST STILL FAIL CLOSED
        os.environ["ZONATA_ALLOW_SQLITE_IN_PRODUCTION"] = "1"
        os.environ.pop("DATABASE_URL", None)
        with self.assertRaises(RuntimeError) as ctx3:
            Database()
        self.assertIn("Direct SQLite fallback is prohibited in production mode", str(ctx3.exception))

        os.environ["DATABASE_URL"] = "sqlite:///var/data/prod.db"
        with self.assertRaises(RuntimeError) as ctx4:
            Database()
        self.assertIn("Direct SQLite fallback is prohibited in production mode", str(ctx4.exception))

        # 4. Production prohibits direct set_db_path reconfiguration
        with self.assertRaises(RuntimeError) as ctx5:
            self.db.set_db_path("/tmp/arbitrary.db")
        self.assertIn("SQLite path reconfiguration is prohibited in production mode", str(ctx5.exception))

        # 5. Non-production (staging/test) behaves correctly with SQLite
        os.environ["APP_ENV"] = "staging"
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("ZONATA_ALLOW_SQLITE_IN_PRODUCTION", None)
        staging_db = Database()
        self.assertEqual(staging_db.get_dialect(), DatabaseDialect.SQLITE)

        # 6. Production with valid PostgreSQL DATABASE_URL succeeds in configuring PostgreSQL dialect
        os.environ["APP_ENV"] = "production"
        os.environ["DATABASE_URL"] = "postgresql://zonata_user:pass@pg.cluster.internal:5432/zonata_prod"
        prod_pg_db = Database()
        self.assertEqual(prod_pg_db.get_dialect(), DatabaseDialect.POSTGRESQL)

        # Cleanup
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("ZONATA_ALLOW_SQLITE_IN_PRODUCTION", None)
        os.environ["APP_ENV"] = "production"

    def test_12_postgresql_connection_error_redacts_credentials(self):
        """Verify PostgreSQL connection errors and logs redact credentials."""
        from unittest.mock import patch, MagicMock
        from core.db import sanitize_db_url

        # 1. Direct test of sanitize_db_url helper across adversarial formats
        adversarial_cases = [
            ("postgresql://zonata_admin:super_secret_password_123@pgcluster.internal:5432/zonata_db", "super_secret_password_123"),
            ("postgresql://app_user:p%40ss%3Aword%21123@[::1]:5432/mydb?sslmode=require", "p%40ss%3Aword%21123"),
            ("postgresql://admin:mypass@[2001:db8::1]:5432/prod_db", "mypass"),
            ("postgres://user:p$w&o*r-d_!@[::1]:5432/db", "p$w&o*r-d_!"),
            ("postgresql://host:5432/db?user=admin&password=secret_in_query&sslmode=verify-full", "secret_in_query"),
            ('psycopg2.OperationalError: failed for user "zonata_admin" in postgresql://zonata_admin:ultra_secret_pw@[10.0.0.1]:5432/zonata_prod', "ultra_secret_pw")
        ]
        for raw_str, secret in adversarial_cases:
            sanitized = sanitize_db_url(raw_str)
            self.assertNotIn(secret, sanitized, f"Secret leaked for case: {raw_str}")
            self.assertIn("***", sanitized, f"Mask indicator missing for case: {raw_str}")

        # Non-credential URL preservation
        plain_url = "postgresql://admin@host:5432/db"
        self.assertEqual(sanitize_db_url(plain_url), plain_url)

        # 2. Test exception propagation redacting credentials
        old_url = os.environ.get("DATABASE_URL")
        try:
            raw_url = "postgresql://zonata_admin:super_secret_password_123@pgcluster.internal:5432/zonata_db"
            os.environ["DATABASE_URL"] = raw_url
            pg_db = Database()
            mock_psycopg2 = MagicMock()
            mock_psycopg2.connect.side_effect = Exception(f"password authentication failed for user zonata_admin: {raw_url}")
            with patch.dict("sys.modules", {"psycopg2": mock_psycopg2, "psycopg2.extras": MagicMock()}):
                with self.assertRaises(RuntimeError) as ctx:
                    pg_db._get_postgresql_connection()
                err_msg = str(ctx.exception)
                self.assertNotIn("super_secret_password_123", err_msg)
                self.assertIn(":***@", err_msg)
        finally:
            if old_url is not None:
                os.environ["DATABASE_URL"] = old_url
            else:
                os.environ.pop("DATABASE_URL", None)


if __name__ == "__main__":
    unittest.main()
