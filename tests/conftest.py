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

from core.db import configure_isolated_test_db, db

AUXILIARY_SCHEMA_TARGETS = [
    ("core.settings_service", "settings_service", "_ensure_schema"),
    ("core.saas_billing", "saas_billing_engine", "_init_db_tables"),
    ("core.evidence_service", "evidence_service", "_init_db"),
    ("core.security_center", "security_center", "_init_db"),
    ("core.automation_fabric.fabric", "universal_automation_fabric", "_init_automation_tables"),
    ("core.automation_fabric.fabric", "universal_automation_fabric", "_ensure_signing_keys_table"),
    ("core.automation_fabric.connector_registry", "connector_registry", "_ensure_idempotency_table"),
    ("core.economic_governance", "economic_governor", "_ensure_tables"),
    ("core.cryptographic_approvals", "cryptographic_approvals", "_ensure_tables"),
    ("core.automation_fabric.data_integration_engine", "sync_checkpoint_manager", "_ensure_tables"),
    ("core.autonomy_governor", "autonomy_governor", "_init_db"),
    ("core.identity_gateway", "identity_gateway", "_init_db"),
    ("core.knowledge_gateway", "knowledge_gateway", "_init_db"),
    ("core.kpi_kra_engine", "kpi_kra_engine", "_init_db"),
    ("core.spend_governor", "spend_governor", "_init_db"),
    ("core.data_lineage_graph", "data_lineage_graph", "_init_db"),
    ("core.workforce_scheduler", "workforce_scheduler", "_init_db"),
    ("core.usage_meter", "usage_meter", "_init_db"),
    ("core.memory_governance", "memory_governance_gateway", "_init_db"),
    ("core.organization_graph", "organization_graph", "_init_db"),
    ("core.tool_factory_v2", "tool_factory_v2", "_init_db"),
    ("core.agent_factory_v2", "agent_factory_v2", "_init_db"),
    ("core.model_gateway_v4", "model_gateway_v4", "_init_db"),
    ("core.action_envelope", "command_bus", "_init_db"),
    ("core.corporate_data_plane", "corporate_data_gateway", "_init_db"),
    ("core.workforce_collaboration_hub", "workforce_collaboration_hub", "_init_db"),
    ("core.tenant_resource_quota", "tenant_quota_manager", "_init_db"),
    ("core.enterprise_records", "records_engine", "_init_db"),
    ("core.enterprise_files", "files_engine", "_init_db"),
    ("core.enterprise_reports", "reports_engine", "_init_db"),
    ("core.enterprise_finance", "finance_engine", "_init_db"),
]

def init_all_subsystem_schemas():
    """Initializes auxiliary tables across all domain subsystems in the active test database."""
    for mod_name, obj_name, meth_name in AUXILIARY_SCHEMA_TARGETS:
        try:
            mod = importlib.import_module(mod_name)
            obj = getattr(mod, obj_name, None)
            if obj and hasattr(obj, meth_name):
                getattr(obj, meth_name)()
        except Exception:
            pass

@pytest.fixture(scope="session", autouse=True)
def isolate_test_environment():
    """Sets up an isolated test database and isolated evidence ledger for the entire pytest session."""
    import tempfile
    os.environ["ZONATA_TEST_MODE"] = "1"
    tmp_evidence = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
    tmp_evidence.close()
    os.environ["ZONATA_EVIDENCE_PATH"] = tmp_evidence.name

    test_db_path = configure_isolated_test_db()
    init_all_subsystem_schemas()
    yield test_db_path
    try:
        if os.path.exists(tmp_evidence.name):
            os.remove(tmp_evidence.name)
    except Exception:
        pass
