# Step 5D Handoff Dossier: Database & Tenant Isolation Hardening

## 1. Summary of Changes
- **Transaction-Scoped Tenant Context (Rule 43):**
  - Updated `core/db.py` (`PostgresConnectionWrapper._apply_rls_context`):
    `SELECT set_config('zonata.tenant_id', %s, true), set_config('zonata.company_id', %s, true)`
  - Enforced `is_local=true` (equivalent to `SET LOCAL`), guaranteeing that settings are discarded automatically by PostgreSQL upon `commit()` or `rollback()`.
  - Added cache invalidation on `commit()` and `rollback()`: resets `self._applied_tenant = None` and `self._applied_company = None` on connection wrappers.
  - Added `db.audit_security()` delegating to role and RLS verification.
- **Database Role Least Privilege (Rule 42):**
  - Implemented `core/db_security.py` (`DBRoleAuditor`): audits connection roles, verifying that normal application workloads do not execute as `SUPERUSER` or with `BYPASSRLS`.
  - In production profiles, raises `DatabaseSecurityViolation` if a privileged role is used.
- **Forced Row-Level Security Audit:**
  - Implemented `RLSAuditor.audit_tenant_tables()`: validates that every tenant-bearing table has `relrowsecurity = true` AND `relforcerowsecurity = true` with active isolation policies.
- **Transaction Pooler Contract & Mutation Verification:**
  - Implemented `TransactionPoolerContract.assert_no_context_leak()` simulating connection reuse behind transaction poolers (PgBouncer, Neon).
  - Validated with mutation test that session-scoped context (`false`) leaks data across transactions and is caught.
- **CI Test Suite (`tests/test_step5_database_isolation.py` & `.github/workflows/ci.yml`):**
  - 7 test cases covering Rule 42, Rule 43, pooler reuse, role safety, and forced RLS. Integrated into both SQLite and PostgreSQL 16 CI pipelines.

---

## 2. Changed Files (`git diff --stat`)
```text
 .github/workflows/ci.yml               |   4 +-
 core/db.py                             |  37 ++++--
 core/db_security.py                    | 223 +++++++++++++++++++++++++++++++++
 docs/reports/STEP5_REPORT.md           |  34 +++++
 tests/test_step5_database_isolation.py | 270 +++++++++++++++++++++++++++++++++++++++++
 5 files changed, 558 insertions(+), 10 deletions(-)
```

---

## 3. Commands to Re-run
```bash
# Verify Python bytecode compilation across repository
python3 -m compileall -q .

# Run Step 5D Database Isolation Suite
python3 -m pytest tests/test_step5_database_isolation.py -v

# Run Full Step 5 Cumulative Test Suites & AST Truth Linter
python3 -m pytest tests/test_step5_preflight.py tests/test_step5_secrets_platform.py tests/test_step5_identity_access.py tests/test_step5_database_isolation.py tests/test_truth_linter.py -v
```

---

## 4. Claims & Evidence
| Claim | Rule | Evidence |
|---|---|---|
| Tenant context is transaction-scoped (is_local=true) | Rule 43 | `tests/test_step5_database_isolation.py::test_01_transaction_scoped_tenant_context_rule43` |
| Pooled connection reuse does not leak tenant context | Rule 43 | `tests/test_step5_database_isolation.py::test_02_pooler_simulation_connection_reuse_zero_leak` |
| Session-scoped context leaks data and is detected | Mutation / Rule 8 | `tests/test_step5_database_isolation.py::test_03_mutation_check_session_scoped_leaks_context` |
| Application connections must not possess SUPERUSER / BYPASSRLS | Rule 42 | `tests/test_step5_database_isolation.py::test_04_db_role_safety_auditor_least_privilege_rule42` |
| Forced RLS verified across all tenant tables | Security Invariant | `tests/test_step5_database_isolation.py::test_05_forced_rls_auditor_enforcement` |
| AST Truth Linter passes with zero violations | Rule 8 | `tests/test_truth_linter.py` (6/6 passing) |

---

## 5. Mutation Checks Done
1. **Session-Level Context Leak:** Setting `is_local=False` causes subsequent transactions on the same physical connection to read the prior tenant's ID; `assert_no_context_leak()` detects the leak and raises `DatabaseSecurityViolation`.
2. **Superuser Application Connection:** Connecting with `rolsuper=True` in production mode raises `DatabaseSecurityViolation`.
3. **Bypass RLS Role:** Connecting with `rolbypassrls=True` in production mode raises `DatabaseSecurityViolation`.
4. **Missing Forced RLS:** Tables with `relrowsecurity=True` but `relforcerowsecurity=False` fail compliance check.

---

## 6. Known Gaps / Follow-ups
- Sub-Step 5E will address Application & Supply-Chain Security (OWASP ASVS API hardening, Cosign container signing, SAST/DAST CI gates).
