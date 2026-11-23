"""Phase 1 tests for the enterprise settings registry, schema, and dry-run.

These tests do not import ``core.settings_service``.  The legacy service creates
and seeds database tables at import time, so it is deliberately kept out of the
registry/schema unit tests.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.settings.definitions import CATEGORIES_CATALOG, SETTINGS_DEFINITIONS  # noqa: E402
from core.settings.models import (  # noqa: E402
    SCOPE_BROAD_TO_SPECIFIC,
    SCOPE_SPECIFIC_TO_BROAD,
    ScopeType,
    SettingStatus,
    ValidationSpec,
)
from core.settings.registry import (  # noqa: E402
    ENFORCED_BY,
    KNOWN_PERMISSIONS,
    SettingsRegistry,
    build_definition,
    settings_registry,
)
from core.settings.schema import (  # noqa: E402
    REQUIRED_TABLES,
    ensure_schema,
    schema_files,
    verify_schema,
)
from core.settings.sections import (  # noqa: E402
    CATEGORY_TO_SECTION,
    SECTIONS,
    SECTION_IDS,
    section_for_category,
)
from migrations.migration_manager import split_sql_statements  # noqa: E402

sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
import settings_migration_dry_run as dry_run  # noqa: E402


class TestRegistryIntegrity(unittest.TestCase):
    def test_counts_are_exact(self):
        counts = settings_registry.counts()
        self.assertEqual(counts["total"], 214)
        self.assertEqual(counts["categories"], 46)
        self.assertEqual(counts["sections"], 16)
        self.assertEqual(counts["live"] + counts["coming_soon"] + counts["hidden"] + counts["action"], 214)
        self.assertEqual(counts["live"], 30)
        self.assertEqual(counts["action"], 2)
        self.assertEqual(counts["hidden"], 4)
        self.assertEqual(counts["coming_soon"], 178)

    def test_keys_are_unique_and_match_source(self):
        keys = [definition.key for definition in settings_registry.all()]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), {definition["id"] for definition in SETTINGS_DEFINITIONS})

    def test_every_category_is_mapped_once(self):
        category_ids = [str(category["id"]) for category in CATEGORIES_CATALOG]
        self.assertEqual(len(category_ids), 46)
        self.assertEqual(set(category_ids), set(CATEGORY_TO_SECTION))
        for category in category_ids:
            self.assertIn(CATEGORY_TO_SECTION[category], SECTION_IDS)

    def test_sections_are_stable(self):
        self.assertEqual(len(SECTIONS), 16)
        self.assertEqual(len(SECTION_IDS), 16)
        numbers = [section["num"] for section in SECTIONS]
        self.assertEqual(numbers, [f"{index:02d}" for index in range(1, 17)])
        self.assertEqual(len(set(SECTION_IDS)), 16)
        for section in SECTIONS:
            self.assertTrue(section["name"])
            self.assertTrue(section["description"])

    def test_live_means_enforced(self):
        for definition in settings_registry.all():
            if definition.status is SettingStatus.LIVE:
                self.assertTrue(definition.enforced_by, definition.key)
                self.assertIn(definition.key, ENFORCED_BY)
        self.assertEqual(set(settings_registry.live_keys()), set(ENFORCED_BY))

    def test_actions_are_not_values(self):
        actions = [d for d in settings_registry.all() if d.status is SettingStatus.ACTION]
        self.assertEqual({d.key for d in actions}, {"danger_revoke_all_sessions", "danger_purge_telemetry"})
        for definition in actions:
            self.assertIsNotNone(definition.action_id)

    def test_permissions_are_known(self):
        for definition in settings_registry.all():
            self.assertIn(definition.required_permission, KNOWN_PERMISSIONS, definition.key)

    def test_scopes_are_ordered_and_valid(self):
        self.assertEqual(SCOPE_BROAD_TO_SPECIFIC[0], ScopeType.PLATFORM)
        self.assertEqual(SCOPE_BROAD_TO_SPECIFIC[-1], ScopeType.USER)
        self.assertEqual(tuple(reversed(SCOPE_BROAD_TO_SPECIFIC)), SCOPE_SPECIFIC_TO_BROAD)
        for definition in settings_registry.all():
            self.assertTrue(definition.allowed_scopes, definition.key)
            self.assertTrue(all(isinstance(scope, ScopeType) for scope in definition.allowed_scopes))

    def test_unknown_category_fails_validation(self):
        raw = {
            "id": "phase1_invalid_key",
            "category": "does_not_exist",
            "name": "Invalid",
            "type": "toggle",
            "default": False,
            "scope": "Host",
            "editable_by": "OWNER",
            "risk": "LOW",
        }
        with self.assertRaises(ValueError):
            SettingsRegistry([raw])

    def test_secret_defaults_are_masked(self):
        secret = settings_registry.require("llm_api_key")
        self.assertTrue(secret.secret)
        self.assertTrue(secret.sensitive)
        self.assertEqual(secret.to_public_dict()["default"], "••••••••")
        self.assertEqual(secret.required_permission, "secrets.manage")

        sensitive_text = settings_registry.require("acc_email")
        self.assertFalse(sensitive_text.secret)
        self.assertTrue(sensitive_text.sensitive)
        self.assertEqual(sensitive_text.required_permission, "settings.write")

    def test_section_for_unknown_category_is_not_dropped(self):
        self.assertEqual(section_for_category("no_such_category"), "advanced_danger")


class TestValidationSpec(unittest.TestCase):
    def test_number_bounds(self):
        spec = ValidationSpec("number", min_value=1, max_value=10, integer=True)
        self.assertEqual(spec.validate(5), (True, None))
        self.assertFalse(spec.validate(0)[0])
        self.assertFalse(spec.validate(11)[0])
        self.assertFalse(spec.validate(5.5)[0])
        self.assertFalse(spec.validate(True)[0])

    def test_select_options(self):
        spec = ValidationSpec("select", options=("A", "B"))
        self.assertEqual(spec.validate("A"), (True, None))
        self.assertFalse(spec.validate("C")[0])

    def test_toggle(self):
        spec = ValidationSpec("toggle")
        self.assertEqual(spec.validate(True), (True, None))
        self.assertFalse(spec.validate("true")[0])

    def test_text_length(self):
        spec = ValidationSpec("text", max_length=5)
        self.assertEqual(spec.validate("abc"), (True, None))
        self.assertFalse(spec.validate("abcdef")[0])


class TestMigrationSplitter(unittest.TestCase):
    def test_simple_statements(self):
        statements = split_sql_statements("CREATE TABLE a (x INT);\nCREATE TABLE b (y INT);", "sqlite")
        self.assertEqual(len(statements), 2)

    def test_sqlite_trigger_body_is_one_statement(self):
        path = os.path.join(
            REPO_ROOT, "migrations", "sqlite", "0004_settings_v2_append_only.sql"
        )
        with open(path, "r", encoding="utf-8") as handle:
            statements = split_sql_statements(handle.read(), "sqlite")
        self.assertEqual(len(statements), 2)
        for statement in statements:
            self.assertIn("CREATE TRIGGER", statement)
            self.assertIn("BEGIN", statement)
            self.assertIn("END", statement)

    def test_postgres_dollar_quoted_body(self):
        sql = """
        CREATE FUNCTION f() RETURNS void AS $$
        BEGIN
            PERFORM 1;
            PERFORM 2;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TABLE t (x INT);
        """
        statements = split_sql_statements(sql, "postgresql")
        self.assertEqual(len(statements), 2)
        self.assertIn("PERFORM 2;", statements[0])
        self.assertTrue(statements[1].startswith("CREATE TABLE"))

    def test_postgres_string_with_semicolon(self):
        sql = "INSERT INTO t VALUES ('a;b');\nINSERT INTO t VALUES ('c');"
        statements = split_sql_statements(sql, "postgresql")
        self.assertEqual(len(statements), 2)
        self.assertIn("'a;b'", statements[0])

    def test_postgres_line_and_block_comments(self):
        sql = "-- comment; with semicolon\n/* block; comment */\nCREATE TABLE t (x INT);"
        statements = split_sql_statements(sql, "postgresql")
        self.assertEqual(len(statements), 1)
        self.assertIn("CREATE TABLE", statements[0])


class TestSettingsSchema(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="settings_schema_")
        self.db_path = os.path.join(self.tempdir, "schema.db")
        self.conn = sqlite3.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_schema_files_are_ordered(self):
        files = schema_files("sqlite")
        self.assertEqual([name for name, _ in files], [
            "common/0003_settings_v2_schema.sql",
            "sqlite/0004_settings_v2_append_only.sql",
            "sqlite/0005_settings_v2_tenant_keys.sql",
        ])
        pg_files = schema_files("postgresql")
        self.assertEqual([name for name, _ in pg_files], [
            "common/0003_settings_v2_schema.sql",
            "pg/0006_settings_v2_append_only.sql",
            "pg/0007_settings_v2_tenant_keys.sql",
        ])

    def test_ensure_schema_creates_and_verifies(self):
        result = ensure_schema(self.conn, "sqlite")
        self.assertEqual(len(result["applied"]), 3)
        verified = verify_schema(self.conn, "sqlite")
        self.assertTrue(verified["ok"], verified)
        self.assertEqual(set(REQUIRED_TABLES), set(verified["required"]))
        for table in REQUIRED_TABLES:
            row = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            self.assertIsNotNone(row, table)

    def test_ensure_schema_is_idempotent(self):
        ensure_schema(self.conn, "sqlite")
        second = ensure_schema(self.conn, "sqlite")
        self.assertEqual(second["applied"], [])
        self.assertEqual(len(second["skipped"]), 3)

    def test_checksum_mismatch_is_rejected(self):
        ensure_schema(self.conn, "sqlite")
        with mock.patch("core.settings.schema._checksum", return_value="0" * 64):
            with self.assertRaises(RuntimeError):
                ensure_schema(self.conn, "sqlite")

    def test_settings_audit_is_append_only(self):
        ensure_schema(self.conn, "sqlite")
        self.conn.execute(
            """
            INSERT INTO settings_audit
                (audit_id, tenant_id, scope_type, scope_id, setting_key, actor, entry_hash, created_at)
            VALUES ('a1', 't1', 'company', 'c1', 'llm_model', 'human', 'hash', 1.0)
            """
        )
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE settings_audit SET reason='tampered' WHERE audit_id='a1'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("DELETE FROM settings_audit WHERE audit_id='a1'")
        count = self.conn.execute("SELECT COUNT(*) FROM settings_audit").fetchone()[0]
        self.assertEqual(count, 1)


class TestDryRun(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="settings_dry_run_")
        self.db_path = os.path.join(self.tempdir, "legacy.db")
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE enterprise_settings (
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'Company',
                category TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value_json TEXT NOT NULL,
                inherited_from TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                updated_at REAL NOT NULL,
                updated_by TEXT NOT NULL,
                PRIMARY KEY(tenant_id, company_id, setting_key)
            )
            """
        )
        rows = [
            ("t1", "c1", "Company", "ai_providers", "llm_model", json.dumps("model-a"), 1.0, "human"),
            ("t1", "c1", "Host", "ai_providers", "llm_api_key", json.dumps("sk_live_REAL_VALUE_1234567890"), 1.0, "human"),
            ("t1", "c1", "Host", "ai_providers", "mcp_auth_token", json.dumps("mcp_sec_live_9f81a7b3c2e5d1"), 1.0, "human"),
            ("t1", "c1", "Host", "danger", "danger_revoke_all_sessions", json.dumps("REVOKE_ACTION"), 1.0, "human"),
            ("t1", "c1", "Company", "does_not_exist", "legacy_unknown_key", json.dumps(True), 1.0, "human"),
        ]
        conn.executemany(
            """
            INSERT INTO enterprise_settings
                (tenant_id, company_id, scope, category, setting_key, setting_value_json, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        conn.close()

        self.mirror_path = os.path.join(self.tempdir, "enterprise_settings.json")
        with open(self.mirror_path, "w", encoding="utf-8") as handle:
            json.dump({"llm_model": "model-a", "account": "category-alias"}, handle)

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def _hash(self) -> str:
        digest = hashlib.sha256()
        with open(self.db_path, "rb") as handle:
            digest.update(handle.read())
        return digest.hexdigest()

    def test_report_is_read_only(self):
        before = self._hash()
        report = dry_run.build_report(self.db_path, self.mirror_path)
        after = self._hash()
        self.assertEqual(before, after)
        self.assertTrue(report["read_only"])

    def test_report_never_contains_secret_value(self):
        report = dry_run.build_report(self.db_path, self.mirror_path)
        rendered = json.dumps(report, sort_keys=True) + dry_run.render_markdown(report)
        self.assertNotIn("sk_live_REAL_VALUE_1234567890", rendered)
        self.assertNotIn("mcp_sec_live_9f81a7b3c2e5d1", rendered)

    def test_report_classifies_secrets_and_conflicts(self):
        report = dry_run.build_report(self.db_path, self.mirror_path)
        classifications = {
            item["key"]: item["classification"] for item in report["secrets_review"]
        }
        self.assertEqual(classifications["llm_api_key"], "configured")
        self.assertEqual(classifications["mcp_auth_token"], "placeholder")
        self.assertEqual(report["proposed_moves"]["move_to_secrets"], 1)
        kinds = {conflict["kind"] for conflict in report["conflicts"]}
        self.assertIn("unknown_registry_key", kinds)
        self.assertIn("secret_not_configured", kinds)

    def test_actions_are_reported_not_migrated(self):
        report = dry_run.build_report(self.db_path, self.mirror_path)
        self.assertEqual(report["proposed_moves"]["action_rows"], 1)
        action_items = [
            item for item in report["secrets_review"] if item["key"].startswith("danger_")
        ]
        self.assertEqual(action_items, [])

    def test_missing_database_is_a_clean_warning(self):
        report = dry_run.build_report(os.path.join(self.tempdir, "missing.db"), self.mirror_path)
        self.assertFalse(report["source"]["table_exists"])
        self.assertTrue(any("not found" in warning.lower() for warning in report["warnings"]))


class TestSideEffectFreeImport(unittest.TestCase):
    def test_settings_package_does_not_import_legacy_service(self):
        code = (
            "import sys; import core.settings; "
            "print('core.settings_service' in sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "False")


if __name__ == "__main__":
    unittest.main()
