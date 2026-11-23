"""
ZONATA Sovereign Core — Sub-Step 5D: Database Security & Tenant Isolation Tests.
================================================================================
Verifies:
- Rule 43: Tenant context is transaction-scoped (set_config(..., true)).
  Zero context leakage across connection reuses behind transaction poolers (PgBouncer/Neon).
- Rule 42: Least privilege database roles (NO SUPERUSER, NO BYPASSRLS for application workloads).
- Forced Row-Level Security (RLS) across all tenant-bearing tables.
- Mutation checks: Proves that session-level scoping (false) leaks context and is flagged.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from core.db import (
    db,
    tenant_scope,
    _current_tenant_id,
    _current_company_id,
    PostgresConnectionWrapper,
)
from core.db_security import (
    DBRoleAuditor,
    DBRoleSafetyReport,
    DatabaseSecurityViolation,
    RLSAuditor,
    RLSAuditReport,
    TransactionPoolerContract,
)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("ZONATA_TEST_MODE", "1")
    monkeypatch.setenv("APP_ENV", "test")


class TestDatabaseTenantIsolation:

    def test_01_transaction_scoped_tenant_context_rule43(self):
        """Rule 43: PostgresConnectionWrapper issues transaction-scoped set_config with true."""
        mock_raw_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_raw_conn.cursor.return_value = mock_cursor

        wrapper = PostgresConnectionWrapper(mock_raw_conn)

        with tenant_scope("tenant_gamma_777", "company_gamma"):
            wrapper.execute("SELECT 1;")

            # Check that set_config was called with is_local=True (Rule 43)
            calls = [
                call for call in mock_cursor.execute.call_args_list
                if "set_config('zonata.tenant_id'" in str(call)
            ]
            assert len(calls) >= 1
            executed_sql, params = calls[-1].args
            assert params[0] == "tenant_gamma_777"
            assert params[1] == "company_gamma"
            assert "set_config('zonata.tenant_id', %s, true)" in executed_sql
            assert "set_config('zonata.company_id', %s, true)" in executed_sql

        # On commit, cached applied tenant must be cleared so next transaction reapplies
        wrapper.commit()
        assert wrapper._applied_tenant is None
        assert wrapper._applied_company is None

        # On rollback, cached applied tenant must also be cleared
        wrapper._applied_tenant = "stale_tenant"
        wrapper.rollback()
        assert wrapper._applied_tenant is None

    def test_02_pooler_simulation_connection_reuse_zero_leak(self):
        """Rule 43: Simulating connection reuse across transactions confirms zero context leakage."""
        class MockPoolerConnection:
            def __init__(self):
                self.session_vars = {}
                self.local_vars = {}
                self.committed = False

            def cursor(self):
                return MockPoolerCursor(self)

            def commit(self):
                self.committed = True
                # Transaction commit clears transaction-local settings
                self.local_vars.clear()

            def rollback(self):
                self.local_vars.clear()

        class MockPoolerCursor:
            def __init__(self, conn):
                self.conn = conn
                self.last_result = None

            def execute(self, sql, params=()):
                if "set_config('zonata.tenant_id'" in sql:
                    val = params[0]
                    is_local = True if "true" in sql.lower() else False
                    if is_local:
                        self.conn.local_vars["zonata.tenant_id"] = val
                    else:
                        self.conn.session_vars["zonata.tenant_id"] = val
                    self.last_result = [(val,)]
                elif "current_setting('zonata.tenant_id'" in sql:
                    # Reads local first, then session, default empty
                    val = self.conn.local_vars.get(
                        "zonata.tenant_id",
                        self.conn.session_vars.get("zonata.tenant_id", "")
                    )
                    self.last_result = [(val,)]

            def fetchone(self):
                return self.last_result[0] if self.last_result else ("",)

            def close(self):
                pass

        mock_conn = MockPoolerConnection()
        assert TransactionPoolerContract.assert_no_context_leak(
            mock_conn,
            tenant_a="tenant_corp_alpha",
            tenant_b="tenant_corp_beta",
        ) is True

    def test_03_mutation_check_session_scoped_leaks_context(self):
        """Mutation Check (Rule 8): Proves that session-level scoping (false) leaks context and is flagged."""
        class LeakySessionPoolerConnection:
            def __init__(self):
                self.session_vars = {}
                self.local_vars = {}

            def cursor(self):
                return LeakySessionPoolerCursor(self)

            def commit(self):
                # Bug simulation: session-level settings persist across commit
                pass

            def rollback(self):
                pass

        class LeakySessionPoolerCursor:
            def __init__(self, conn):
                self.conn = conn
                self.last_result = None

            def execute(self, sql, params=()):
                if "set_config('zonata.tenant_id'" in sql:
                    val = params[0]
                    # Simulate old faulty behaviour: leaked into session
                    self.conn.session_vars["zonata.tenant_id"] = val
                    self.last_result = [(val,)]
                elif "current_setting('zonata.tenant_id'" in sql:
                    val = self.conn.session_vars.get("zonata.tenant_id", "")
                    self.last_result = [(val,)]

            def fetchone(self):
                return self.last_result[0] if self.last_result else ("",)

            def close(self):
                pass

        leaky_conn = LeakySessionPoolerConnection()
        with pytest.raises(DatabaseSecurityViolation, match="Rule 43 Violation: Transaction B leaked tenant context"):
            TransactionPoolerContract.assert_no_context_leak(
                leaky_conn,
                tenant_a="tenant_corp_alpha",
                tenant_b="tenant_corp_beta",
            )

    def test_04_db_role_safety_auditor_least_privilege_rule42(self, monkeypatch):
        """Rule 42: Database roles must not have superuser or bypassrls privileges in production."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        # Test safe unprivileged role
        mock_cur.fetchone.side_effect = [
            ("zonata_app",),  # current_user
            ("zonata_app", False, False),  # rolname, rolsuper, rolbypassrls
        ]
        report = DBRoleAuditor.verify_connection_role_safety(mock_conn)
        assert report.is_safe is True
        assert report.is_superuser is False
        assert report.is_bypass_rls is False
        assert len(report.violations) == 0

        # Test insecure superuser role in test profile (returns unsafe report)
        mock_cur.fetchone.side_effect = [
            ("postgres",),
            ("postgres", True, True),
        ]
        report_super = DBRoleAuditor.verify_connection_role_safety(mock_conn)
        assert report_super.is_safe is False
        assert report_super.is_superuser is True
        assert report_super.is_bypass_rls is True
        assert len(report_super.violations) == 2

        # Test production profile strictly raises DatabaseSecurityViolation on superuser
        monkeypatch.setenv("APP_ENV", "production")
        mock_cur.fetchone.side_effect = [
            ("postgres",),
            ("postgres", True, False),
        ]
        with pytest.raises(DatabaseSecurityViolation, match="Production DB Role Safety Check Failed"):
            DBRoleAuditor.verify_connection_role_safety(mock_conn)

    def test_05_forced_rls_auditor_enforcement(self):
        """Audits forced RLS compliance reporting."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        # Scenario: 2 tenant tables, both compliant
        mock_cur.fetchall.return_value = [
            ("invoices", True, True),
            ("audit_ledger", True, True),
        ]
        mock_cur.fetchone.side_effect = [
            (1,),  # policy count for invoices
            (1,),  # policy count for audit_ledger
        ]

        report = RLSAuditor.audit_tenant_tables(mock_conn)
        assert report.total_tables_inspected == 2
        assert report.is_compliant is True
        assert len(report.missing_rls) == 0
        assert len(report.missing_force_rls) == 0
        assert len(report.missing_policies) == 0

        # Scenario: Missing forced RLS on a table
        mock_cur.fetchall.return_value = [
            ("unprotected_table", True, False),  # relforcerowsecurity is False
        ]
        report_unforced = RLSAuditor.audit_tenant_tables(mock_conn)
        assert report_unforced.is_compliant is False
        assert "unprotected_table" in report_unforced.missing_force_rls

    def test_06_database_audit_security_integration(self):
        """Integrates security audit into db object."""
        result = db.audit_security()
        assert "role_safety" in result
        assert "rls_compliance" in result
        assert "dialect" in result
        assert isinstance(result["is_secure"], bool)

    def test_07_tenant_scope_context_manager_lifecycle(self):
        """tenant_scope sets and resets ContextVars properly on exit."""
        assert _current_tenant_id.get() is None
        assert _current_company_id.get() is None

        with tenant_scope("ten_xyz", "cmp_xyz"):
            assert _current_tenant_id.get() == "ten_xyz"
            assert _current_company_id.get() == "cmp_xyz"

        assert _current_tenant_id.get() is None
        assert _current_company_id.get() is None

        # Even with exception
        try:
            with tenant_scope("ten_err", "cmp_err"):
                raise ValueError("Boom")
        except ValueError:
            pass

        assert _current_tenant_id.get() is None
        assert _current_company_id.get() is None
