"""
ZONATA Pytest Root Configuration & Test Isolation Fixture
Ensures every pytest test execution operates in a strictly isolated temporary database,
preventing any contamination of the constitutional database 'storage/roboassistant.db'.
"""

import os
import sys
import importlib
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ["ZONATA_DB_DIALECT"] = "sqlite"
os.environ["ZONATA_TEST_MODE"] = "1"

# Test-only webhook secrets. Production ships with no default secret and
# rejects unverifiable webhooks; the suite must supply its own.
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_zonata_tests_only")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "rzp_zonata_tests_only")

from core.db import configure_isolated_test_db, db
from tests.schema_bootstrap import init_all_subsystem_schemas, seed_baseline_tenant_scope

# Create the isolated database exactly once per process, so that module-level
# singletons bind to the same database the tests later use.
ISOLATED_DB_PATH = os.environ.get("ZONATA_SESSION_TEST_DB") or configure_isolated_test_db()
os.environ["ZONATA_SESSION_TEST_DB"] = ISOLATED_DB_PATH

_SESSION_ENV_DEFAULTS = {}


def _restore_session_env() -> None:
    for key, val in _SESSION_ENV_DEFAULTS.items():
        if not os.environ.get(key):
            os.environ[key] = val


@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment():
    """Sets up an isolated test database and isolated evidence ledger for the entire pytest session."""
    import hashlib
    import tempfile
    os.environ["ZONATA_TEST_MODE"] = "1"
    prod_db_candidate = os.path.join(BASE_DIR, "storage", "roboassistant.db")
    if os.path.exists(prod_db_candidate):
        with open(prod_db_candidate, "rb") as _pf:
            os.environ["ZONATA_PRETEST_DB_SHA256"] = hashlib.sha256(_pf.read()).hexdigest()
    tmp_evidence = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tmp_evidence.close()
    os.environ["ZONATA_EVIDENCE_PATH"] = tmp_evidence.name

    tmp_sbom = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp_sbom.close()
    os.environ["ZONATA_SBOM_PATH"] = tmp_sbom.name

    tmp_settings = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp_settings.close()
    os.environ["ZONATA_SETTINGS_PATH"] = tmp_settings.name

    tmp_cap = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
    tmp_cap.close()
    os.environ["ZONATA_CAPABILITY_REPORT_PATH"] = tmp_cap.name

    _SESSION_ENV_DEFAULTS.clear()
    _SESSION_ENV_DEFAULTS.update({
        "ZONATA_TEST_MODE": "1",
        "ZONATA_EVIDENCE_PATH": tmp_evidence.name,
        "ZONATA_SBOM_PATH": tmp_sbom.name,
        "ZONATA_SETTINGS_PATH": tmp_settings.name,
        "ZONATA_CAPABILITY_REPORT_PATH": tmp_cap.name,
    })

    test_db_path = ISOLATED_DB_PATH
    db.set_db_path(test_db_path)
    os.environ["ZONATA_DB_PATH"] = test_db_path
    os.environ["ZONATA_SESSION_TEST_DB"] = test_db_path
    init_all_subsystem_schemas()
    seed_baseline_tenant_scope()
    yield test_db_path
    for tmp_path in (tmp_evidence.name, tmp_sbom.name, tmp_settings.name, tmp_cap.name):
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def _restore_session_db(session_db: str) -> None:
    db.set_db_path(session_db)
    os.environ["ZONATA_DB_PATH"] = session_db
    try:
        from core.database_engine import engine
        engine.db_path = session_db
    except Exception:
        pass
    if not os.path.exists(session_db):
        init_all_subsystem_schemas()
        seed_baseline_tenant_scope()


@pytest.fixture(scope="module", autouse=True)
def preserve_module_database_isolation():
    """Restores session DB pointer and isolated env paths after any module teardown."""
    yield
    for key, val in _SESSION_ENV_DEFAULTS.items():
        os.environ[key] = val
    session_db = os.environ.get("ZONATA_SESSION_TEST_DB")
    if session_db and (
        db.db_path != session_db
        or os.environ.get("ZONATA_DB_PATH") != session_db
        or not os.path.exists(db.db_path)
    ):
        _restore_session_db(session_db)


@pytest.fixture(autouse=True)
def preserve_test_database_isolation():
    """Ensures test database pointer remains valid across test classes with destructive teardowns."""
    _restore_session_env()
    session_db = os.environ.get("ZONATA_SESSION_TEST_DB")
    if session_db and (
        not db.db_path
        or not os.path.exists(db.db_path)
        or not os.path.exists(os.path.dirname(os.path.abspath(db.db_path)))
    ):
        _restore_session_db(session_db)
    yield
    _restore_session_env()
    session_db = os.environ.get("ZONATA_SESSION_TEST_DB")
    if session_db and (
        not db.db_path
        or not os.path.exists(db.db_path)
        or not os.path.exists(os.path.dirname(os.path.abspath(db.db_path)))
    ):
        _restore_session_db(session_db)
