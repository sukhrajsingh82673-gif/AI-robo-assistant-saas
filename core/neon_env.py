"""
ZONATA Enterprise SaaS — Neon Environment & Service Configuration Loader
Automatically discovers and loads Neon branch variables from .env.local and .env,
configures PostgreSQL connection routing (pooled vs unpooled), and provides
unified access to Neon services (Postgres, Auth, Functions, AI Gateway, Data API).
"""

import os
import sys
import re
from typing import Dict, Optional, Any

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure pure-Python PostgreSQL driver in Termux environment is accessible
_TERMUX_SITE = "/data/data/com.termux/files/usr/lib/python3.14/site-packages"
if os.path.exists(_TERMUX_SITE) and _TERMUX_SITE not in sys.path:
    sys.path.insert(0, _TERMUX_SITE)


def load_env_file(filepath: str, overwrite: bool = False) -> Dict[str, str]:
    """Parse a .env or .env.local file into a dictionary and populate os.environ."""
    loaded = {}
    if not os.path.exists(filepath):
        return loaded

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    # Strip outer single or double quotes
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    loaded[key] = val
                    if overwrite or key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to load env file '{filepath}': {e}\n")

    return loaded


def load_neon_env(force: bool = False) -> Dict[str, str]:
    """
    Load environment variables from .env and .env.local.
    .env.local takes precedence over .env as per standard conventions.
    """
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    env_local_path = os.path.join(_PROJECT_ROOT, ".env.local")

    # Load .env first, then .env.local (which overrides .env)
    loaded = {}
    loaded.update(load_env_file(env_path, overwrite=force))
    loaded.update(load_env_file(env_local_path, overwrite=True))

    # If DATABASE_URL is set to a postgresql URL, automatically adjust dialect if not explicitly SQLite
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url.startswith(("postgres://", "postgresql://")):
        if "ZONATA_DB_DIALECT" not in os.environ:
            os.environ["ZONATA_DB_DIALECT"] = "postgresql"

    return loaded


# Automatically execute env load on import
load_neon_env()


def get_database_url(unpooled: bool = False) -> str:
    """
    Return the active database connection string.
    - unpooled=False (default): Returns pooled connection (PgBouncer) for high-concurrency web transactions.
    - unpooled=True: Returns direct compute endpoint (required for DDL migrations and session-level locks).
    """
    load_neon_env()
    if unpooled:
        unpooled_url = os.environ.get("DATABASE_URL_UNPOOLED", "").strip()
        if unpooled_url:
            return unpooled_url
        base_url = os.environ.get("DATABASE_URL", "").strip()
        return base_url.replace("-pooler.", ".")
    return os.environ.get("DATABASE_URL", "").strip()


def get_neon_auth_base_url() -> str:
    """Return Neon Auth (Managed Better Auth) base URL."""
    load_neon_env()
    return os.environ.get("NEON_AUTH_BASE_URL", "").strip()


def get_neon_auth_jwks_url() -> str:
    """Return Neon Auth JWKS public key verification URL."""
    load_neon_env()
    return os.environ.get("NEON_AUTH_JWKS_URL", "").strip()


def get_neon_function_url(function_name: str = "hello") -> str:
    """Return invocation URL for a deployed Neon Function."""
    load_neon_env()
    env_var_name = f"NEON_FUNCTION_{function_name.upper().replace('-', '_')}_BASE_URL"
    return os.environ.get(env_var_name, "").strip()


def get_neon_ai_gateway_base_url() -> str:
    """Return Neon AI Gateway base URL."""
    load_neon_env()
    return os.environ.get("NEON_AI_GATEWAY_BASE_URL", "").strip()


def get_neon_ai_gateway_token() -> str:
    """Return Neon AI Gateway bearer token."""
    load_neon_env()
    return os.environ.get("NEON_AI_GATEWAY_TOKEN", "").strip()


def get_neon_data_api_url() -> str:
    """Return Neon PostgREST Data API URL."""
    load_neon_env()
    return os.environ.get("NEON_DATA_API_URL", "").strip()


def get_neon_services_status() -> Dict[str, Any]:
    """Return status summary of all configured Neon services."""
    load_neon_env()
    db_url = get_database_url()
    auth_url = get_neon_auth_base_url()
    hello_fn = get_neon_function_url("hello")
    ai_gw = get_neon_ai_gateway_base_url()
    data_api = get_neon_data_api_url()

    return {
        "branch": os.environ.get("NEON_BRANCH", "production"),
        "postgres": {
            "configured": bool(db_url),
            "pooled": bool("-pooler." in db_url),
            "dialect": os.environ.get("ZONATA_DB_DIALECT", "postgresql" if db_url else "sqlite")
        },
        "auth": {
            "configured": bool(auth_url),
            "base_url": auth_url,
            "jwks_url": get_neon_auth_jwks_url(),
            "type": "Managed Better Auth"
        },
        "functions": {
            "configured": bool(hello_fn),
            "hello_url": hello_fn
        },
        "ai_gateway": {
            "configured": bool(ai_gw),
            "base_url": ai_gw,
            "tier_support": "Available on Neon Pro/Scale plans (disabled on Free plan)"
        },
        "data_api": {
            "configured": bool(data_api),
            "url": data_api
        }
    }
