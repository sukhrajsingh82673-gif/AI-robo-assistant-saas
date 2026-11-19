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

@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment():
    """Sets up an isolated test database and isolated evidence ledger for the entire pytest session."""
    import tempfile
    os.environ["ZONATA_TEST_MODE"] = "1"
    tmp_evidence = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tmp_evidence.close()
    os.environ["ZONATA_EVIDENCE_PATH"] = tmp_evidence.name

    test_db_path = ISOLATED_DB_PATH
    db.set_db_path(test_db_path)
    os.environ["ZONATA_DB_PATH"] = test_db_path
    os.environ["ZONATA_SESSION_TEST_DB"] = test_db_path
    init_all_subsystem_schemas()
    seed_baseline_tenant_scope()
    yield test_db_path
    try:
        if os.path.exists(tmp_evidence.name):
            os.remove(tmp_evidence.name)
    except Exception:
        pass

@pytest.fixture(autouse=True)
def preserve_test_database_isolation():
    """Ensures test database pointer remains valid across test classes with destructive teardowns."""
    session_db = os.environ.get("ZONATA_SESSION_TEST_DB")
    if session_db and (not db.db_path or not os.path.exists(os.path.dirname(os.path.abspath(db.db_path)))):
        db.set_db_path(session_db)
        os.environ["ZONATA_DB_PATH"] = session_db
    yield
    session_db = os.environ.get("ZONATA_SESSION_TEST_DB")
    if session_db and (not db.db_path or not os.path.exists(os.path.dirname(os.path.abspath(db.db_path)))):
        db.set_db_path(session_db)
        os.environ["ZONATA_DB_PATH"] = session_db
