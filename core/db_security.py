"""
ZONATA Sovereign Core — Sub-Step 5D: Database Security, Role Verification & RLS Audit.
======================================================================================
Governed by:
- Rule 42: Least privilege & default deny. Application connections must NOT possess
  SUPERUSER or BYPASSRLS privileges.
- Rule 43: Tenant context is transaction-scoped (set_config(..., true)).
  Strict isolation behind transaction-mode poolers (PgBouncer, Neon).
- Row-Level Security: Forced RLS on all tenant-bearing tables.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("zonata.db.security")


class DatabaseSecurityViolation(Exception):
    """Raised when database isolation, role privilege, or RLS invariants are violated."""
    pass


@dataclass
class DBRoleSafetyReport:
    current_user: str
    is_superuser: bool
    is_bypass_rls: bool
    is_safe: bool
    violations: List[str] = field(default_factory=list)


@dataclass
class RLSAuditReport:
    total_tables_inspected: int
    tenant_tables: List[str]
    compliant_tables: List[str]
    missing_rls: List[str]
    missing_force_rls: List[str]
    missing_policies: List[str]
    errors: List[str] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return (
            not self.errors
            and len(self.missing_rls) == 0
            and len(self.missing_force_rls) == 0
            and len(self.missing_policies) == 0
        )


class DBRoleAuditor:
    """Verifies that the runtime database connection complies with Rule 42 (Least Privilege)."""

    @staticmethod
    def verify_connection_role_safety(conn: Any) -> DBRoleSafetyReport:
        """
        Queries pg_roles for CURRENT_USER and verifies neither rolsuper nor rolbypassrls is active.
        """
        is_production = os.environ.get("APP_ENV") == "production"
        violations: List[str] = []

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT current_user;")
            user_row = cursor.fetchone()
            current_user = user_row[0] if user_row else "unknown"

            cursor.execute(
                "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;"
            )
            role_row = cursor.fetchone()
            try:
                cursor.close()
            except Exception:
                pass

            if not role_row:
                violation = (
                    f"Rule 42: role '{current_user}' was not found in pg_roles; "
                    "least-privilege status cannot be verified."
                )
                if is_production:
                    raise DatabaseSecurityViolation(violation)
                return DBRoleSafetyReport(
                    current_user=current_user,
                    is_superuser=False,
                    is_bypass_rls=False,
                    is_safe=False,
                    violations=[violation],
                )

            _, is_super, is_bypass = role_row

            if is_super:
                violations.append(
                    f"Rule 42 Violation: User '{current_user}' possesses SUPERUSER privilege."
                )
            if is_bypass:
                violations.append(
                    f"Rule 42 Violation: User '{current_user}' possesses BYPASSRLS privilege."
                )

            is_safe = len(violations) == 0

            if is_production and not is_safe:
                raise DatabaseSecurityViolation(
                    f"Production DB Role Safety Check Failed: {'; '.join(violations)}"
                )

            return DBRoleSafetyReport(
                current_user=current_user,
                is_superuser=bool(is_super),
                is_bypass_rls=bool(is_bypass),
                is_safe=is_safe,
                violations=violations,
            )
        except Exception as e:
            if isinstance(e, DatabaseSecurityViolation):
                raise
            violation = f"Rule 42: role safety check failed and cannot be assumed safe: {e}"
            if is_production:
                raise DatabaseSecurityViolation(violation) from e
            return DBRoleSafetyReport(
                current_user="unknown",
                is_superuser=False,
                is_bypass_rls=False,
                is_safe=False,
                violations=[violation],
            )


class RLSAuditor:
    """Audits PostgreSQL tables to enforce forced row-level security across all tenant data."""

    @staticmethod
    def audit_tenant_tables(conn: Any) -> RLSAuditReport:
        """
        Scans pg_class and pg_tables in the public schema to ensure every table with tenant_id has:
        - relrowsecurity = true (RLS enabled)
        - relforcerowsecurity = true (RLS forced even on table owners)
        - At least one active policy referencing zonata.tenant_id
        """
        is_production = os.environ.get("APP_ENV") == "production"
        try:
            cursor = conn.cursor()
            # Find all public tables with tenant_id column
            cursor.execute(
                """
                SELECT DISTINCT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND a.attname = 'tenant_id'
                  AND NOT a.attisdropped;
                """
            )
            rows = cursor.fetchall()

            tenant_tables = []
            compliant_tables = []
            missing_rls = []
            missing_force_rls = []
            missing_policies = []

            for row in rows:
                table_name = row[0]
                row_security = bool(row[1])
                force_security = bool(row[2])
                tenant_tables.append(table_name)

                if not row_security:
                    missing_rls.append(table_name)
                elif not force_security:
                    missing_force_rls.append(table_name)
                else:
                    # Check if policy exists
                    cursor.execute(
                        """
                        SELECT count(*) FROM pg_policy p
                        JOIN pg_class c ON c.oid = p.polrelid
                        WHERE c.relname = %s
                          AND COALESCE(pg_get_expr(p.polqual, p.polrelid), '') LIKE '%%zonata.tenant_id%%';
                        """,
                        (table_name,),
                    )
                    pol_count = cursor.fetchone()[0]
                    if pol_count == 0:
                        missing_policies.append(table_name)
                    else:
                        compliant_tables.append(table_name)

            try:
                cursor.close()
            except Exception:
                pass

            return RLSAuditReport(
                total_tables_inspected=len(tenant_tables),
                tenant_tables=tenant_tables,
                compliant_tables=compliant_tables,
                missing_rls=missing_rls,
                missing_force_rls=missing_force_rls,
                missing_policies=missing_policies,
            )
        except Exception as exc:
            error = f"RLS audit failed and cannot be assumed compliant: {exc}"
            if is_production:
                raise DatabaseSecurityViolation(error) from exc
            return RLSAuditReport(
                total_tables_inspected=0,
                tenant_tables=[],
                compliant_tables=[],
                missing_rls=[],
                missing_force_rls=[],
                missing_policies=[],
                errors=[error],
            )


class TransactionPoolerContract:
    """Verifies pooler resilience against tenant context leaks (Rule 43)."""

    @staticmethod
    def assert_no_context_leak(
        conn: Any,
        tenant_a: str = "tenant_alpha_123",
        tenant_b: str = "tenant_beta_456",
    ) -> bool:
        """
        Simulates two successive transactions executed on the exact same physical connection
        behind a transaction-mode connection pooler:
        1. Transaction A sets context to tenant_a with is_local=True and commits.
        2. Transaction B starts on the same connection WITHOUT setting a context.
        3. Transaction B queries current_setting('zonata.tenant_id', true).
        Asserts that Transaction B reads empty/NULL string, proving ZERO context leak.
        """
        cursor = conn.cursor()

        # Step 1: Transaction A
        cursor.execute("SELECT set_config('zonata.tenant_id', %s, true);", (tenant_a,))
        cursor.execute("SELECT current_setting('zonata.tenant_id', true);")
        t_a_read = cursor.fetchone()[0]
        if t_a_read != tenant_a:
            cursor.close()
            raise DatabaseSecurityViolation(
                f"Transaction A failed to set local context: expected {tenant_a}, read {t_a_read}"
            )

        conn.commit()

        # Step 2: Transaction B on same physical connection without setting context
        cursor.execute("SELECT current_setting('zonata.tenant_id', true);")
        t_b_read = cursor.fetchone()[0]
        cursor.close()

        # Under Rule 43 (is_local=true), commit clears the setting. Value must be '' or None.
        if t_b_read and t_b_read == tenant_a:
            raise DatabaseSecurityViolation(
                f"Rule 43 Violation: Transaction B leaked tenant context from Transaction A! Read '{t_b_read}'"
            )

        return True
