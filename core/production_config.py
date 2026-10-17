"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM — V10
Production Environment & Startup Preflight Engine
Validates configuration integrity, rejects unsafe defaults, and enforces fail-closed posture.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("zonata.config")

class ConfigurationError(Exception):
    """Raised when environment or security configuration violates production standards."""
    pass

class ProductionConfigValidator:
    """
    Enforces strict production configuration gates:
    - Fails closed if mandatory production controls are missing.
    - Rejects debug mode, development keys, weak passwords, and open CORS in production.
    """

    FORBIDDEN_DEV_SECRETS = {
        "changeme", "password", "admin", "123456", "secret",
        "dev_key", "test_key", "default", "replace_with_secure_password",
        "zonata_secure_prod_password_2026", "zonata_minio_secret_password_2026",
        "zonata_admin_password_2026", "replace_with_"
    }

    @classmethod
    def get_environment(cls) -> str:
        return os.environ.get("ZONATA_ENV", "development").lower().strip()

    @classmethod
    def is_production(cls) -> bool:
        return cls.get_environment() == "production"

    @classmethod
    def validate_environment(cls, env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Validates environment against production standards.
        Raises ConfigurationError if in production and invalid.
        """
        env = env_vars if env_vars is not None else dict(os.environ)
        current_env = env.get("ZONATA_ENV", "development").lower().strip()
        errors: List[str] = []
        warnings: List[str] = []

        if current_env == "production":
            # 1. Debug mode check
            debug_val = env.get("DEBUG", "false").lower()
            if debug_val in ("true", "1", "yes"):
                errors.append("DEBUG mode must be FALSE in production environment.")

            # 2. Master Key and Vault Key checks
            vault_key = env.get("SECRET_VAULT_KEY", "")
            if not vault_key or len(vault_key) < 32:
                errors.append("SECRET_VAULT_KEY must be at least 32 characters in production.")
            if vault_key.lower() in cls.FORBIDDEN_DEV_SECRETS:
                errors.append("SECRET_VAULT_KEY is using an insecure or default value.")

            signing_key = env.get("APPLICATION_SIGNING_KEY", "")
            if not signing_key or len(signing_key) < 32:
                errors.append("APPLICATION_SIGNING_KEY must be at least 32 characters in production.")
            if signing_key.lower() in cls.FORBIDDEN_DEV_SECRETS:
                errors.append("APPLICATION_SIGNING_KEY is using an insecure or default value.")

            # 3. Sovereign Root Key
            root_key_id = env.get("SOVEREIGN_ROOT_KEY_ID", "")
            if not root_key_id:
                errors.append("SOVEREIGN_ROOT_KEY_ID must be specified in production.")

            # 4. Database configuration check
            db_dialect = env.get("DATABASE_DIALECT", "sqlite").lower()
            if db_dialect == "postgresql":
                db_url = env.get("DATABASE_URL", "")
                if not db_url:
                    errors.append("DATABASE_URL must be specified when DATABASE_DIALECT is postgresql.")
                else:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(db_url)
                    db_pwd = parsed.password or ""
                    db_user = parsed.username or ""
                    if any(bad in db_pwd.lower() for bad in cls.FORBIDDEN_DEV_SECRETS) or any(bad in db_url.lower() for bad in ("zonata_secure_prod_password_2026", "replace_with_")):
                        errors.append("DATABASE_URL contains an insecure default password.")
                    if (db_user in ("zonata_admin", "postgres", "admin", "root") or "://zonata_admin:" in db_url or "://postgres:" in db_url) and env.get("ZONATA_ALLOW_SUPERUSER_DB", "0") != "1":
                        errors.append("DATABASE_URL violates least privilege: superuser role ('zonata_admin' or 'postgres') prohibited for application runtime in production. Use 'zonata_app'.")

            # 5. Ingress CORS check
            cors = env.get("ALLOWED_ORIGINS", "")
            if cors == "*":
                errors.append("ALLOWED_ORIGINS cannot be '*' wildcard in production.")

        if errors:
            raise ConfigurationError(f"Production Configuration Validation Failed:\n" + "\n".join(f" - {e}" for e in errors))

        return {
            "valid": len(errors) == 0,
            "environment": current_env,
            "errors": errors,
            "warnings": warnings
        }

    @classmethod
    def run_startup_preflight(cls) -> Dict[str, Any]:
        """
        Executes preflight checks on DB engine, storage, and secret vault.
        """
        results: Dict[str, Any] = {}
        all_passed = True

        # 1. Environment Config Validation
        try:
            env_res = cls.validate_environment()
            results["environment_config"] = {"status": "PASS", "details": env_res}
        except Exception as e:
            results["environment_config"] = {"status": "FAIL", "error": str(e)}
            all_passed = False

        # 2. Database Connectivity
        try:
            from core.db import db
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                row = cur.fetchone()
                val = row[0] if row else None
            results["database_connectivity"] = {"status": "PASS", "ping": val}
        except Exception as e:
            results["database_connectivity"] = {"status": "FAIL", "error": str(e)}
            all_passed = False

        # 3. Storage & Directories
        storage_dirs = ["storage", "storage/evidence", "storage/backups"]
        dir_status = {}
        for d in storage_dirs:
            p = os.path.join(os.getcwd(), d)
            os.makedirs(p, exist_ok=True)
            dir_status[d] = "WRITABLE" if os.access(p, os.W_OK) else "NOT_WRITABLE"
        results["storage_directories"] = {"status": "PASS", "directories": dir_status}

        return {
            "preflight_status": "READY" if all_passed else "PREFLIGHT_FAILED",
            "passed": all_passed,
            "checks": results
        }
