"""
URA / ZONATA Enterprise SaaS — Secret Redaction & Least-Privilege Role Suite
Validates BLK-03:
- Zero plaintext passwords in version-controlled manifests
- Multi-role PostgreSQL separation (zonata_app, zonata_worker, zonata_migrator, zonata_backup)
- ProductionConfigValidator fail-closed enforcement against default/weak credentials & superuser DB roles
- production.env.example contract completeness
- Memory & log credential redaction via ContentSanitizer
"""

import os
import sys
import unittest
import yaml
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.production_config import ProductionConfigValidator, ConfigurationError
from core.secrets import SecretManager, ContentSanitizer

COMPOSE_FILE = os.path.join(BASE_DIR, "docker-compose.prod.yml")
INIT_ROLES_SQL = os.path.join(BASE_DIR, "docker", "init-db-roles.sql")
PROD_ENV_EXAMPLE = os.path.join(BASE_DIR, "production.env.example")


class TestSecretsLeastPrivilege(unittest.TestCase):
    """Verifies that secrets are never hardcoded and least-privilege database roles are enforced."""

    def test_01_docker_compose_has_no_hardcoded_secrets(self):
        """Verifies zero plaintext passwords in docker-compose.prod.yml."""
        self.assertTrue(os.path.exists(COMPOSE_FILE), "docker-compose.prod.yml must exist")
        with open(COMPOSE_FILE, "r") as f:
            content = f.read()

        forbidden_secrets = [
            "zonata_secure_prod_password_2026",
            "zonata_minio_secret_password_2026",
            "zonata_admin_password_2026",
        ]
        for secret in forbidden_secrets:
            self.assertNotIn(
                secret,
                content,
                f"Forbidden plaintext secret '{secret}' found hardcoded in docker-compose.prod.yml!"
            )

        # Confirm environment variable interpolation patterns are used
        self.assertIn("${POSTGRES_PASSWORD}", content)
        self.assertIn("${S3_SECRET_KEY}", content)
        self.assertIn("${GF_SECURITY_ADMIN_PASSWORD}", content)

    def test_02_docker_compose_least_privilege_role_separation(self):
        """Verifies that compose manifest enforces role separation across services."""
        with open(COMPOSE_FILE, "r") as f:
            manifest = yaml.safe_load(f)

        services = manifest.get("services", {})

        # zonata-api must use least-privilege zonata_app
        api_env = services["zonata-api"].get("environment", [])
        api_db_env = [e for e in api_env if "DATABASE_URL" in e]
        self.assertTrue(api_db_env, "zonata-api must define DATABASE_URL")
        self.assertIn("zonata_app", api_db_env[0], "zonata-api DATABASE_URL must configure zonata_app role")
        self.assertNotIn("zonata_admin", api_db_env[0], "zonata-api must NOT use superuser zonata_admin")

        # zonata-worker must use least-privilege zonata_worker
        worker_env = services["zonata-worker"].get("environment", [])
        worker_db_env = [e for e in worker_env if "DATABASE_URL" in e]
        self.assertTrue(worker_db_env, "zonata-worker must define DATABASE_URL")
        self.assertIn("zonata_worker", worker_db_env[0], "zonata-worker DATABASE_URL must configure zonata_worker role")
        self.assertNotIn("zonata_admin", worker_db_env[0], "zonata-worker must NOT use superuser zonata_admin")

        # postgres must mount init-db-roles.sql
        pg_vols = services["postgres"].get("volumes", [])
        init_mounts = [v for v in pg_vols if "init-db-roles.sql" in str(v) or "01-init-roles.sql" in str(v)]
        self.assertTrue(init_mounts, "postgres service must mount docker/init-db-roles.sql into /docker-entrypoint-initdb.d/")

    def test_03_init_db_roles_sql_structure_and_least_privilege(self):
        """Verifies that docker/init-db-roles.sql enforces least-privilege role separation."""
        self.assertTrue(os.path.exists(INIT_ROLES_SQL), f"{INIT_ROLES_SQL} must exist")
        with open(INIT_ROLES_SQL, "r") as f:
            sql = f.read()

        # Check required roles are created
        self.assertIn("zonata_app", sql)
        self.assertIn("zonata_worker", sql)
        self.assertIn("zonata_migrator", sql)
        self.assertIn("zonata_backup", sql)

        # Check that CREATE on schema public is revoked from non-admin roles
        self.assertIn("REVOKE CREATE ON SCHEMA public FROM zonata_app", sql)
        self.assertIn("REVOKE CREATE ON SCHEMA public FROM zonata_worker", sql)

        # Check that DML is granted to app and worker
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zonata_app", sql)
        self.assertIn("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO zonata_worker", sql)

        # Check that DDL is granted only to migrator
        self.assertIn("GRANT USAGE, CREATE ON SCHEMA public TO zonata_migrator", sql)

    def test_04_production_config_rejects_insecure_passwords(self):
        """Verifies ProductionConfigValidator fails closed when default/weak secrets are passed."""
        insecure_env = {
            "ZONATA_ENV": "production",
            "DEBUG": "false",
            "SECRET_VAULT_KEY": "0123456789abcdef0123456789abcdef",
            "APPLICATION_SIGNING_KEY": "fedcba9876543210fedcba9876543210",
            "SOVEREIGN_ROOT_KEY_ID": "key_root_prod_01",
            "ALLOWED_ORIGINS": "https://admin.enterprise.internal",
            "DATABASE_DIALECT": "postgresql",
            "DATABASE_URL": "postgresql://zonata_app:zonata_secure_prod_password_2026@pg:5432/zonata_production"
        }
        with self.assertRaises(ConfigurationError) as ctx:
            ProductionConfigValidator.validate_environment(insecure_env)
        self.assertIn("insecure default password", str(ctx.exception))

    def test_05_production_config_rejects_superuser_db_role_in_production(self):
        """Verifies ProductionConfigValidator fails closed when superuser DB credentials are configured for runtime."""
        superuser_env = {
            "ZONATA_ENV": "production",
            "DEBUG": "false",
            "SECRET_VAULT_KEY": "0123456789abcdef0123456789abcdef",
            "APPLICATION_SIGNING_KEY": "fedcba9876543210fedcba9876543210",
            "SOVEREIGN_ROOT_KEY_ID": "key_root_prod_01",
            "ALLOWED_ORIGINS": "https://admin.enterprise.internal",
            "DATABASE_DIALECT": "postgresql",
            "DATABASE_URL": "postgresql://zonata_admin:ComplexRandomProdKey2026!@pg:5432/zonata_production"
        }
        with self.assertRaises(ConfigurationError) as ctx:
            ProductionConfigValidator.validate_environment(superuser_env)
        self.assertIn("violates least privilege", str(ctx.exception))

        # Using least-privilege zonata_app passes
        app_env = dict(superuser_env)
        app_env["DATABASE_URL"] = "postgresql://zonata_app:ComplexRandomProdKey2026!@pg:5432/zonata_production"
        res = ProductionConfigValidator.validate_environment(app_env)
        self.assertTrue(res["valid"])

        # Superuser override via break-glass flag passes with warning
        superuser_override_env = dict(superuser_env)
        superuser_override_env["ZONATA_ALLOW_SUPERUSER_DB"] = "1"
        res_override = ProductionConfigValidator.validate_environment(superuser_override_env)
        self.assertTrue(res_override["valid"])

    def test_06_production_env_example_completeness(self):
        """Verifies that production.env.example documents all required least-privilege secrets."""
        self.assertTrue(os.path.exists(PROD_ENV_EXAMPLE), f"{PROD_ENV_EXAMPLE} must exist")
        with open(PROD_ENV_EXAMPLE, "r") as f:
            env_content = f.read()

        required_vars = [
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "DB_APP_PASSWORD",
            "DATABASE_URL",
            "DB_WORKER_PASSWORD",
            "WORKER_DATABASE_URL",
            "DB_MIGRATOR_PASSWORD",
            "MIGRATOR_DATABASE_URL",
            "ZONATA_AUTH_SECRET",
            "S3_SECRET_KEY",
            "GF_SECURITY_ADMIN_PASSWORD"
        ]
        for var in required_vars:
            self.assertIn(var, env_content, f"Variable '{var}' must be documented in production.env.example")

    def test_07_content_sanitizer_redacts_credentials_and_tokens(self):
        """Verifies ContentSanitizer reliably redacts credentials from logs and evidence strings."""
        sample_log = (
            "Connecting with password=SuperSecretPassword123! to database. "
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token body here. "
            "Using api_key: ak_live_1234567890abcdef123456 for payment."
        )
        sanitized = ContentSanitizer.sanitize(sample_log)
        self.assertNotIn("SuperSecretPassword123!", sanitized)
        self.assertNotIn("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", sanitized)
        self.assertNotIn("ak_live_1234567890abcdef123456", sanitized)
        self.assertIn("[REDACTED_PASSWORD]", sanitized)
        self.assertIn("[REDACTED_AUTH_TOKEN]", sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)


if __name__ == "__main__":
    unittest.main()
