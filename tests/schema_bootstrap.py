"""
Schema bootstrap helpers shared by the pytest fixtures and the isolated-database
factory in ``core.db``.

Kept in its own module so that ``core.db.configure_isolated_test_db()`` can
initialise subsystem tables without importing ``tests.conftest`` (which would
re-enter the database factory and create a second, empty database).
"""

import importlib
import time

from core.db import db


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
    ("core.skill_arena", "SkillArena", "_init_db"),
    ("core.ai_employee_os", "ai_employee_registry", "_init_db"),
    ("core.employee_template", "employee_template_registry", "_init_db"),
    ("core.employee_health_manager", "employee_health_manager", "_init_db"),
    ("core.ceo_workforce_controller", "ceo_workforce_controller", "_init_db"),
    ("core.employee_factory_v7", "employee_factory_v7", "_init_db"),
]


def init_all_subsystem_schemas():
    """Initializes auxiliary tables across all domain subsystems in the active database."""
    for mod_name, obj_name, meth_name in AUXILIARY_SCHEMA_TARGETS:
        try:
            mod = importlib.import_module(mod_name)
            obj = getattr(mod, obj_name, None)
            if obj and hasattr(obj, meth_name):
                getattr(obj, meth_name)()
        except Exception:
            pass

    # Tenant security and governance managers
    try:
        from core.killswitch_matrix import KillSwitchMatrix
        KillSwitchMatrix("tnt_bootstrap")._ensure_table()
    except Exception:
        pass
    try:
        from core.cost_governor import CostGovernor
        CostGovernor("tnt_bootstrap")._ensure_table()
    except Exception:
        pass
    try:
        from core.secret_vault import SecretVault
        SecretVault()._ensure_table()
    except Exception:
        pass
    try:
        from core.sovereign_key_manager import SovereignKeyManager
        SovereignKeyManager("tnt_bootstrap")._ensure_table()
    except Exception:
        pass
    try:
        from core.approval_revocation import ApprovalRevocationEngine
        ApprovalRevocationEngine("tnt_bootstrap")._ensure_table()
    except Exception:
        pass
    try:
        from core.llm import ensure_model_gateway_tables
        ensure_model_gateway_tables()
    except Exception:
        pass
    try:
        from core.authority import ensure_authority_tables
        ensure_authority_tables()
    except Exception:
        pass
    try:
        from core.organization import ensure_organization_tables
        ensure_organization_tables()
    except Exception:
        pass
    try:
        from core.agents import ensure_agent_runtime_tables
        ensure_agent_runtime_tables()
    except Exception:
        pass
    try:
        from core.work import ensure_work_kernel_tables
        ensure_work_kernel_tables()
    except Exception:
        pass
    try:
        from core.sop import ensure_sop_tables
        ensure_sop_tables()
    except Exception:
        pass
    try:
        from core.verification import ensure_verification_tables
        ensure_verification_tables()
    except Exception:
        pass


def seed_baseline_tenant_scope():
    """Creates the baseline tenant/company rows every domain table points at.

    Production tenants are created by signup; an isolated database starts empty,
    so tests that write tenant-scoped rows need this scope to exist or their
    foreign keys fail.
    """
    try:
        with db.get_connection() as conn:
            now = time.time()
            for tenant_id, name in (("tnt_primary", "Primary Tenant"), ("tnt_bootstrap", "Bootstrap Tenant")):
                conn.execute(
                    "INSERT INTO tenants (tenant_id, name, status, created_at) VALUES (?, ?, 'ACTIVE', ?) "
                    "ON CONFLICT(tenant_id) DO NOTHING",
                    (tenant_id, name, now),
                )
            conn.execute(
                "INSERT INTO companies (company_id, tenant_id, name, industry, company_type, status, created_at) "
                "VALUES ('comp_primary', 'tnt_primary', 'Primary Company', 'GENERAL', 'NEW', 'OPERATIONAL', ?) "
                "ON CONFLICT(company_id) DO NOTHING",
                (now,),
            )
            conn.commit()
    except Exception:
        pass
