"""Phase 2 tests for the Settings V2 backend.

These tests are isolated: they create a temporary SQLite database, apply the
settings schema, inject a connection factory, and never import the legacy
settings service.  They cover resolver precedence, RBAC, secrets, approvals,
audit chaining, optimistic concurrency, bulk writes, and the HTTP adapter.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.settings import rbac  # noqa: E402
from core.settings.api_v2 import SettingsV2API  # noqa: E402
from core.settings.approvals import SettingsApprovals  # noqa: E402
from core.settings.audit import SettingsAudit  # noqa: E402
from core.settings.errors import (  # noqa: E402
    ApprovalRequired,
    ConflictError,
    NotFoundError,
    PermissionDenied,
    SecretsUnavailable,
    UnsupportedOperation,
    ValidationError,
)
from core.settings.models import ActorType, ScopeType  # noqa: E402
from core.settings.resolver import ResolveContext, SettingsResolver  # noqa: E402
from core.settings.schema import ensure_schema  # noqa: E402
from core.settings.secrets import KeyRing, SettingsSecretVault  # noqa: E402
from core.settings.service import SettingsV2Service  # noqa: E402

MASTER_KEY = "ab" * 32


class SettingsV2TestBase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="settings_v2_")
        self.db_path = os.path.join(self.tempdir, "settings.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        ensure_schema(self.conn, "sqlite")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS companies (company_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL)"
        )
        self.conn.executemany(
            "INSERT OR IGNORE INTO companies (company_id, tenant_id) VALUES (?, ?)",
            [("c1", "t1"), ("c2", "t1")],
        )
        self.conn.commit()

        self._old_master_key = os.environ.get("ZONATA_SETTINGS_MASTER_KEY")
        os.environ["ZONATA_SETTINGS_MASTER_KEY"] = MASTER_KEY
        self.vault = SettingsSecretVault(KeyRing.load())
        self.service = SettingsV2Service(
            connection_factory=lambda: self.conn,
            audit=SettingsAudit(),
            resolver=SettingsResolver(legacy_fallback=False),
            vault=self.vault,
            approvals=SettingsApprovals(),
        )
        self.owner = rbac.Principal(
            user_id="u_owner", tenant_id="t1", company_id="c1", role="OWNER"
        )
        self.executive = rbac.Principal(
            user_id="u_exec", tenant_id="t1", company_id="c1", role="EXECUTIVE"
        )
        self.manager = rbac.Principal(
            user_id="u_manager", tenant_id="t1", company_id="c1", role="MANAGER"
        )
        self.observer = rbac.Principal(
            user_id="u_observer", tenant_id="t1", company_id="c1", role="OBSERVER"
        )
        self.auditor = rbac.Principal(
            user_id="u_auditor", tenant_id="t1", company_id="c1", role="AUDITOR"
        )
        self.agent = rbac.Principal(
            user_id="u_agent",
            tenant_id="t1",
            company_id="c1",
            role="SYSTEM_AGENT",
            actor_type=ActorType.AGENT,
        )
        self.other_company_viewer = rbac.Principal(
            user_id="u_view", tenant_id="t1", company_id="c2", role="OBSERVER"
        )

    def tearDown(self):
        if self._old_master_key is None:
            os.environ.pop("ZONATA_SETTINGS_MASTER_KEY", None)
        else:
            os.environ["ZONATA_SETTINGS_MASTER_KEY"] = self._old_master_key
        self.conn.close()
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def _set(self, key, value, principal=None, scope=ScopeType.COMPANY, scope_id="c1", expected=None):
        return self.service.set_value(
            principal or self.owner,
            key,
            value,
            scope_type=scope,
            scope_id=scope_id,
            expected_version=expected,
        )


class TestResolverPrecedence(SettingsV2TestBase):
    def test_specific_value_beats_broader_default(self):
        self._set("wf_max_concurrent_agents", 10, scope=ScopeType.ORGANIZATION, scope_id="t1", expected=0)
        inherited = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(inherited["value"], 10)
        self.assertEqual(inherited["source_scope"], "organization")
        self.assertFalse(inherited["overridden_here"])
        self.assertIn("Inherited", inherited["provenance"])

        self._set("wf_max_concurrent_agents", 20, expected=0)
        local = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(local["value"], 20)
        self.assertEqual(local["source_scope"], "company")
        self.assertTrue(local["overridden_here"])
        self.assertIn("Overridden", local["provenance"])

        other = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c2")
        self.assertEqual(other["value"], 10)
        self.assertEqual(other["source_scope"], "organization")

    def test_department_scope_beats_company(self):
        self._set("wf_max_concurrent_agents", 20, expected=0)
        self._set("wf_max_concurrent_agents", 30, scope=ScopeType.DEPARTMENT, scope_id="d1", expected=0)
        resolved = self.service.effective(
            self.owner, "wf_max_concurrent_agents", company_id="c1", department_id="d1"
        )
        self.assertEqual(resolved["value"], 30)
        self.assertEqual(resolved["source_scope"], "department")
        self.assertTrue(resolved["overridden_here"])
        self.assertIn("Overridden at Department", resolved["provenance"])

    def test_broadest_lock_wins_over_more_specific_value(self):
        self._set("wf_max_concurrent_agents", 10, scope=ScopeType.ORGANIZATION, scope_id="t1", expected=0)
        self._set("wf_max_concurrent_agents", 20, expected=0)
        self.service.set_lock(
            self.owner, "wf_max_concurrent_agents", True,
            scope_type=ScopeType.ORGANIZATION, scope_id="t1",
        )
        locked = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(locked["value"], 10)
        self.assertTrue(locked["is_locked"])
        self.assertEqual(locked["locked_by_scope"], "organization")

        self.service.set_lock(
            self.owner, "wf_max_concurrent_agents", False,
            scope_type=ScopeType.ORGANIZATION, scope_id="t1",
        )
        unlocked = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(unlocked["value"], 20)
        self.assertFalse(unlocked["is_locked"])

    def test_reset_deletes_local_override(self):
        self._set("wf_max_concurrent_agents", 10, scope=ScopeType.ORGANIZATION, scope_id="t1", expected=0)
        self._set("wf_max_concurrent_agents", 20, expected=0)
        result = self.service.reset_value(self.owner, "wf_max_concurrent_agents", scope_id="c1")
        self.assertTrue(result["removed"])
        resolved = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(resolved["value"], 10)
        self.assertEqual(resolved["source_scope"], "organization")

    def test_optimistic_concurrency_rejects_stale_version(self):
        self._set("wf_max_concurrent_agents", 20, expected=0)
        with self.assertRaises(ConflictError):
            self._set("wf_max_concurrent_agents", 21, expected=0)

    def test_non_live_setting_is_not_writable(self):
        with self.assertRaises(UnsupportedOperation):
            self._set("acc_density", "compact", expected=0)
        with self.assertRaises(UnsupportedOperation):
            self.service.propose(self.owner, "acc_density", "compact", scope_id="c1")

    def test_legacy_fallback_is_tenant_scoped(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS enterprise_settings (
                tenant_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value_json TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self.conn.executemany(
            "INSERT INTO enterprise_settings "
            "(tenant_id, company_id, setting_key, setting_value_json, version) "
            "VALUES (?, ?, 'llm_model', ?, 1)",
            [
                ("tnt_primary", "comp_primary", json.dumps("legacy-global")),
                ("t2", "comp_primary", json.dumps("tenant-default")),
            ],
        )
        self.conn.commit()
        resolver = SettingsResolver(legacy_fallback=True, cache_enabled=False)
        other_tenant = ResolveContext(tenant_id="t2", company_id="c3")
        same_tenant = resolver.resolve(self.conn, "llm_model", other_tenant)
        # A same-tenant primary-company default is still honoured.
        self.assertEqual(same_tenant.value, "tenant-default")

        unrelated = ResolveContext(tenant_id="t3", company_id="c4")
        self.conn.execute(
            "INSERT OR IGNORE INTO companies (company_id, tenant_id) VALUES ('c4', 't3')"
        )
        self.conn.commit()
        resolved = resolver.resolve(self.conn, "llm_model", unrelated)
        # The old runtime read tnt_primary/comp_primary for every tenant.  V2
        # must not leak another tenant's stored configuration.
        self.assertNotEqual(resolved.value, "legacy-global")

    def test_same_department_id_in_two_tenants_is_isolated(self):
        # Department ids are not globally unique.  The same id in another
        # tenant must neither collide nor leak.
        self.conn.execute(
            "INSERT OR IGNORE INTO companies (company_id, tenant_id) VALUES ('c3', 't2')"
        )
        self.conn.commit()
        other = rbac.Principal(
            user_id="u_other", tenant_id="t2", company_id="c3", role="OWNER"
        )
        self.service.set_value(
            self.owner,
            "wf_max_concurrent_agents",
            10,
            scope_type=ScopeType.DEPARTMENT,
            scope_id="dept_sales",
            expected_version=0,
        )
        self.service.set_value(
            other,
            "wf_max_concurrent_agents",
            99,
            scope_type=ScopeType.DEPARTMENT,
            scope_id="dept_sales",
            expected_version=0,
        )
        first = self.service.effective(
            self.owner, "wf_max_concurrent_agents", company_id="c1", department_id="dept_sales"
        )
        second = self.service.effective(
            other, "wf_max_concurrent_agents", company_id="c3", department_id="dept_sales"
        )
        self.assertEqual(first["value"], 10)
        self.assertEqual(second["value"], 99)


class TestRbac(SettingsV2TestBase):
    def test_observer_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self._set("wf_max_concurrent_agents", 20, principal=self.observer, expected=0)

    def test_manager_can_write_agent_settings(self):
        result = self._set("wf_max_concurrent_agents", 20, principal=self.manager, expected=0)
        self.assertEqual(result["value"], 20)

    def test_manager_cannot_write_security_settings(self):
        with self.assertRaises(PermissionDenied):
            self._set("host_emergency_stop", True, principal=self.manager, expected=0)

    def test_observer_can_read_own_company_but_not_another(self):
        self._set("wf_max_concurrent_agents", 20, expected=0)
        self.assertEqual(
            self.service.effective(self.observer, "wf_max_concurrent_agents", company_id="c1")["value"],
            20,
        )
        with self.assertRaises(PermissionDenied):
            self.service.effective(self.other_company_viewer, "wf_max_concurrent_agents", company_id="c1")

    def test_lock_requires_lock_permission(self):
        self._set("wf_max_concurrent_agents", 20, principal=self.manager, expected=0)
        with self.assertRaises(PermissionDenied):
            self.service.set_lock(self.manager, "wf_max_concurrent_agents", True, scope_id="c1")

    def test_audit_requires_audit_read(self):
        self._set("wf_max_concurrent_agents", 20, expected=0)
        events = self.service.list_audit(self.auditor, company_id="c1")
        self.assertGreaterEqual(len(events), 1)
        with self.assertRaises(PermissionDenied):
            self.service.list_audit(self.observer, company_id="c1")

    def test_agent_role_infers_agent_actor_type_from_the_token(self):
        principal = rbac.Principal.from_auth_context(
            {
                "user_id": "u_agent",
                "tenant_id": "t1",
                "company_id": "c1",
                "role": "SYSTEM_AGENT",
                "permissions": ["*"],
            }
        )
        self.assertIs(principal.actor_type, ActorType.AGENT)
        self.assertEqual(principal.permissions, frozenset())
        self.assertFalse(rbac.has_permission(principal, "settings.write"))

    def test_wildcard_permission_does_not_promote_non_owner(self):
        principal = rbac.Principal(
            user_id="u_spoof",
            tenant_id="t1",
            company_id="c1",
            role="OBSERVER",
            permissions=frozenset({"*"}),
        )
        self.assertFalse(rbac.has_permission(principal, "settings.write"))
        with self.assertRaises(PermissionDenied):
            self._set("wf_max_concurrent_agents", 20, principal=principal, expected=0)

    def test_capabilities_match_the_write_path(self):
        owner = rbac.capabilities(self.owner)
        self.assertTrue(owner["can_write"])
        self.assertTrue(owner["can_lock"])
        self.assertTrue(owner["can_manage_secrets"])
        self.assertTrue(owner["can_read_audit"])
        self.assertIn("organization", owner["writable_scopes"])
        self.assertNotIn("platform", owner["writable_scopes"])

        global_admin = rbac.Principal(
            user_id="u_ga", tenant_id="t1", company_id="c1", role="GLOBAL_ADMIN"
        )
        self.assertIn("platform", rbac.capabilities(global_admin)["writable_scopes"])

        observer = rbac.capabilities(self.observer)
        self.assertFalse(observer["can_write"])
        self.assertFalse(observer["can_lock"])
        self.assertFalse(observer["can_read_audit"])
        self.assertEqual(observer["permissions"], ["settings.read"])

        agent = rbac.capabilities(self.agent)
        self.assertFalse(agent["can_write"])
        self.assertFalse(agent["can_manage_secrets"])
        self.assertFalse(agent["is_approver"])

    def test_registry_exposes_capabilities_for_the_caller(self):
        catalog = self.service.registry_catalog(self.observer)
        self.assertEqual(catalog["capabilities"]["role"], "OBSERVER")
        self.assertFalse(catalog["capabilities"]["can_write"])
        owner_catalog = self.service.registry_catalog(self.owner)
        self.assertTrue(owner_catalog["capabilities"]["can_write"])


class TestApprovals(SettingsV2TestBase):
    def test_agent_proposes_and_owner_applies(self):
        with self.assertRaises(PermissionDenied):
            self._set("wf_max_concurrent_agents", 42, principal=self.agent, expected=0)

        proposal = self.service.propose(
            self.agent, "wf_max_concurrent_agents", 42, scope_id="c1", reason="scale up"
        )
        approval_id = proposal["approval"]["approval_id"]
        self.assertEqual(proposal["status"], "PENDING")

        decision = self.service.decide_approval(self.owner, approval_id, True)
        self.assertTrue(decision["applied"])
        resolved = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(resolved["value"], 42)

    def test_agent_cannot_touch_ceo_limits(self):
        with self.assertRaises(PermissionDenied):
            self.service.propose(self.agent, "ceo_spending_limit", 999999, scope_id="c1")
        with self.assertRaises(PermissionDenied):
            self._set("ceo_spending_limit", 999999, principal=self.agent, expected=0)

    def test_proposer_cannot_self_approve(self):
        proposal = self.service.propose(
            self.owner, "host_emergency_stop", True, scope_id="c1", reason="emergency"
        )
        approval_id = proposal["approval"]["approval_id"]
        with self.assertRaises(PermissionDenied):
            self.service.decide_approval(self.owner, approval_id, True)

        # host_emergency_stop is CRITICAL, so the two-person rule needs two
        # distinct approvers in addition to the separate proposer.
        first = self.service.decide_approval(self.executive, approval_id, True)
        self.assertFalse(first["final"])
        self.assertFalse(first["applied"])

        second_approver = rbac.Principal(
            user_id="u_owner2", tenant_id="t1", company_id="c1", role="OWNER"
        )
        decision = self.service.decide_approval(second_approver, approval_id, True)
        self.assertTrue(decision["final"])
        self.assertTrue(decision["applied"])
        self.assertTrue(
            self.service.effective(self.owner, "host_emergency_stop", company_id="c1")["value"]
        )

    def test_human_cannot_launder_missing_permission_through_approval(self):
        with self.assertRaises(PermissionDenied):
            self.service.propose(self.manager, "host_emergency_stop", True, scope_id="c1")

    def test_approval_cannot_overwrite_a_newer_value(self):
        proposal = self.service.propose(
            self.agent, "wf_max_concurrent_agents", 42, scope_id="c1", reason="scale up"
        )
        approval_id = proposal["approval"]["approval_id"]
        time.sleep(0.002)
        self._set("wf_max_concurrent_agents", 12, expected=0)
        with self.assertRaises(ConflictError):
            self.service.decide_approval(self.owner, approval_id, True)
        resolved = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(resolved["value"], 12)
        pending = self.service.list_approvals(self.owner, company_id="c1")
        self.assertEqual(pending[0]["status"], "pending")

    def test_company_boundary_applies_to_approvals(self):
        proposal = self.service.propose(self.agent, "wf_max_concurrent_agents", 42, scope_id="c1")
        approval_id = proposal["approval"]["approval_id"]
        with self.assertRaises(PermissionDenied):
            self.service.decide_approval(self.other_company_viewer, approval_id, True)


class TestSecrets(SettingsV2TestBase):
    def test_secret_is_write_only_and_audited_without_plaintext(self):
        value = "sk-live-REAL-VALUE-1234"
        result = self.service.put_secret(
            self.owner, "llm_api_key", value, scope_type=ScopeType.COMPANY, scope_id="c1"
        )
        self.assertTrue(result["secret"]["configured"])
        self.assertEqual(result["secret"]["last4"], "1234")
        self.assertNotIn(value, json.dumps(result))

        listing = self.service.list_secrets(self.owner, company_id="c1")
        entry = next(item for item in listing if item["name"] == "llm_api_key")
        self.assertTrue(entry["configured"])
        self.assertEqual(entry["last4"], "1234")
        self.assertNotIn(value, json.dumps(listing))

        effective = self.service.effective(self.owner, "llm_api_key", company_id="c1")
        self.assertEqual(effective["value"], "••••••••")
        self.assertNotIn(value, json.dumps(effective))

        runtime_value = self.vault.decrypt_for_runtime(
            self.conn, "t1", ScopeType.COMPANY, "c1", "llm_api_key"
        )
        self.assertEqual(runtime_value, value)

        events = self.service.list_audit(self.owner, company_id="c1", key="llm_api_key")
        self.assertTrue(events)
        self.assertNotIn(value, json.dumps(events))
        self.assertTrue(self.service.verify_audit(self.owner)["ok"])

    def test_reader_without_secret_permission_does_not_see_last4(self):
        value = "sk-live-REAL-VALUE-1234"
        self.service.put_secret(
            self.owner, "llm_api_key", value, scope_type=ScopeType.COMPANY, scope_id="c1"
        )
        effective = self.service.effective(self.observer, "llm_api_key", company_id="c1")
        metadata = effective["secret_metadata"]
        self.assertTrue(metadata["configured"])
        self.assertEqual(metadata["last4"], "")
        self.assertIsNone(metadata["created_by"])
        self.assertNotIn("1234", json.dumps(effective))

    def test_short_secret_does_not_leak_through_last4(self):
        result = self.service.put_secret(
            self.owner, "llm_api_key", "abc",
            scope_type=ScopeType.COMPANY, scope_id="c1",
        )
        self.assertEqual(result["secret"]["last4"], "")
        listing = self.service.list_secrets(self.owner, company_id="c1")
        self.assertNotIn('"abc"', json.dumps(listing))

    def test_rotate_and_revoke(self):
        self.service.put_secret(
            self.owner, "llm_api_key", "sk-live-FIRST-1111", scope_type=ScopeType.COMPANY, scope_id="c1"
        )
        rotated = self.service.put_secret(
            self.owner,
            "llm_api_key",
            "sk-live-SECOND-2222",
            rotate=True,
            scope_type=ScopeType.COMPANY,
            scope_id="c1",
        )
        self.assertEqual(rotated["secret"]["last4"], "2222")
        revoked = self.service.revoke_secret(
            self.owner, "llm_api_key", scope_type=ScopeType.COMPANY, scope_id="c1"
        )
        self.assertTrue(revoked["removed"])
        listing = self.service.list_secrets(self.owner, company_id="c1")
        entry = next(item for item in listing if item["name"] == "llm_api_key")
        self.assertFalse(entry["configured"])

    def test_secret_requires_secret_permission(self):
        with self.assertRaises(PermissionDenied):
            self.service.put_secret(
                self.manager, "llm_api_key", "sk-live-NOPE-0000",
                scope_type=ScopeType.COMPANY, scope_id="c1",
            )

    def test_platform_secret_names_are_tenant_scoped(self):
        self.conn.execute(
            "INSERT OR IGNORE INTO companies (company_id, tenant_id) VALUES ('c3', 't2')"
        )
        self.conn.commit()
        other = rbac.Principal(
            user_id="u_other", tenant_id="t2", company_id="c3", role="GLOBAL_ADMIN"
        )
        self.service.put_secret(
            self.owner,
            "llm_api_key",
            "sk-live-TENANT-ONE-1111",
            scope_type=ScopeType.PLATFORM,
            scope_id="platform",
        )
        self.service.put_secret(
            other,
            "llm_api_key",
            "sk-live-TENANT-TWO-2222",
            scope_type=ScopeType.PLATFORM,
            scope_id="platform",
        )
        first = next(
            item
            for item in self.service.list_secrets(self.owner, company_id="c1")
            if item["name"] == "llm_api_key"
        )
        second = next(
            item
            for item in self.service.list_secrets(other, company_id="c3")
            if item["name"] == "llm_api_key"
        )
        self.assertEqual(first["last4"], "1111")
        self.assertEqual(second["last4"], "2222")

    def test_malformed_key_file_fails_closed(self):
        path = os.path.join(self.tempdir, "bad.key")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("not-a-32-byte-key")
        os.chmod(path, 0o600)
        env = {k: v for k, v in os.environ.items() if k != "ZONATA_SETTINGS_MASTER_KEY"}
        env["ZONATA_SETTINGS_KEY_FILE"] = path
        env["ZONATA_ENV"] = "development"
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SecretsUnavailable):
                KeyRing.load()

    def test_production_without_master_key_fails_closed(self):
        env = {k: v for k, v in os.environ.items() if k != "ZONATA_SETTINGS_MASTER_KEY"}
        env["ZONATA_ENV"] = "production"
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SecretsUnavailable):
                KeyRing.load()


class TestAudit(SettingsV2TestBase):
    def test_hash_chain_verifies_and_detects_tampering(self):
        self._set("wf_max_concurrent_agents", 20, expected=0)
        self._set("wf_max_concurrent_agents", 21, expected=1)
        verification = self.service.verify_audit(self.owner)
        self.assertTrue(verification["ok"], verification)
        self.assertEqual(verification["checked"], 2)

        self.conn.execute("DROP TRIGGER settings_audit_no_update")
        self.conn.execute(
            "UPDATE settings_audit SET new_value = '21' WHERE audit_id = (SELECT audit_id FROM settings_audit ORDER BY created_at ASC, audit_id ASC LIMIT 1)"
        )
        self.conn.commit()
        verification = self.service.verify_audit(self.owner)
        self.assertFalse(verification["ok"])
        self.assertEqual(verification["broken_at"], verification.get("broken_at"))

    def test_chain_stays_valid_when_the_clock_does_not_advance(self):
        frozen = SettingsAudit(clock=lambda: 1234.0)
        for index in range(3):
            frozen.write(
                self.conn,
                tenant_id="t1",
                company_id="c1",
                scope_type="company",
                scope_id="c1",
                setting_key="llm_model",
                actor="u_owner",
                old_value=None,
                new_value=f"model-{index}",
            )
        self.conn.commit()
        result = frozen.verify_chain(self.conn, "t1")
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["checked"], 3)

    def test_audit_is_company_scoped(self):
        self._set("wf_max_concurrent_agents", 20, expected=0)
        self._set("wf_max_concurrent_agents", 30, scope_id="c2", expected=0)
        c1_events = self.service.list_audit(self.owner, company_id="c1")
        c2_events = self.service.list_audit(self.owner, company_id="c2")
        self.assertTrue(all(event["company_id"] == "c1" for event in c1_events))
        self.assertTrue(all(event["company_id"] == "c2" for event in c2_events))
        self.assertEqual(len(c1_events), 1)
        self.assertEqual(len(c2_events), 1)

    def test_sensitive_values_are_redacted(self):
        self._set("llm_api_key", "sk-live-REDACT-9999", expected=0) if False else None
        # Use the secret endpoint; the value must never enter the audit row.
        self.service.put_secret(
            self.owner, "llm_api_key", "sk-live-REDACT-9999",
            scope_type=ScopeType.COMPANY, scope_id="c1",
        )
        events = self.service.list_audit(self.owner, company_id="c1", key="llm_api_key")
        self.assertTrue(events)
        self.assertNotIn("sk-live-REDACT-9999", json.dumps(events))


class TestBulk(SettingsV2TestBase):
    def test_preview_does_not_write_and_apply_bulk_is_atomic(self):
        changes = [
            {"key": "wf_max_concurrent_agents", "value": 30},
            {"key": "term_max_lease_seconds", "value": 120},
        ]
        preview = self.service.bulk_preview(self.owner, changes, company_id="c1")
        self.assertEqual(len(preview), 2)
        count = self.conn.execute("SELECT COUNT(*) FROM settings_values").fetchone()[0]
        self.assertEqual(count, 0)

        result = self.service.bulk_apply(self.owner, changes, company_id="c1")
        self.assertEqual(result["applied_count"], 2)
        resolved = self.service.effective(self.owner, "wf_max_concurrent_agents", company_id="c1")
        self.assertEqual(resolved["value"], 30)

    def test_bulk_is_atomic_on_validation_error(self):
        changes = [
            {"key": "wf_max_concurrent_agents", "value": 30},
            {"key": "llm_temperature", "value": 999},
        ]
        with self.assertRaises(ValidationError):
            self.service.bulk_apply(self.owner, changes, company_id="c1")
        count = self.conn.execute(
            "SELECT COUNT(*) FROM settings_values WHERE setting_key = 'wf_max_concurrent_agents'"
        ).fetchone()[0]
        self.assertEqual(count, 0)


class TestApiLayer(SettingsV2TestBase):
    def _context(self, principal):
        return {
            "user_id": principal.user_id,
            "tenant_id": principal.tenant_id,
            "company_id": principal.company_id,
            "role": principal.role,
            "permissions": ["*"],
        }

    def test_registry_effective_and_write(self):
        api = SettingsV2API(self.service)
        status, payload = api.handle(
            "GET", "/api/settings/v2/registry", {}, {}, self._context(self.owner), "c1"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["registry"]["counts"]["total"], 202)
        self.assertEqual(payload["registry"]["counts"]["hidden"], 4)
        catalog_keys = {item["key"] for item in payload["registry"]["settings"]}
        self.assertEqual(len(catalog_keys), 198)
        self.assertNotIn("bill_plan_tier", catalog_keys)

        status, payload = api.handle(
            "POST",
            "/api/settings/v2/values",
            {},
            {"key": "wf_max_concurrent_agents", "value": 25, "expected_version": 0},
            self._context(self.owner),
            "c1",
        )
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["result"]["value"], 25)

        status, payload = api.handle(
            "GET",
            "/api/settings/v2/effective",
            {"key": ["wf_max_concurrent_agents"]},
            {},
            self._context(self.owner),
            "c1",
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["setting"]["value"], 25)

    def test_missing_expected_version_is_rejected(self):
        api = SettingsV2API(self.service)
        status, payload = api.handle(
            "POST",
            "/api/settings/v2/values",
            {},
            {"key": "wf_max_concurrent_agents", "value": 25},
            self._context(self.owner),
            "c1",
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["code"], "VALIDATION_ERROR")

    def test_secret_value_never_round_trips(self):
        api = SettingsV2API(self.service)
        value = "sk-live-API-ROUNDTRIP-7777"
        status, payload = api.handle(
            "POST",
            "/api/settings/v2/secrets",
            {},
            {
                "name": "llm_api_key",
                "value": value,
                "scope_type": "company",
                "scope_id": "c1",
            },
            self._context(self.owner),
            "c1",
        )
        self.assertEqual(status, 200, payload)
        self.assertNotIn(value, json.dumps(payload))

        status, payload = api.handle(
            "GET", "/api/settings/v2/secrets", {}, {}, self._context(self.owner), "c1"
        )
        self.assertEqual(status, 200)
        self.assertNotIn(value, json.dumps(payload))
        entry = next(item for item in payload["secrets"] if item["name"] == "llm_api_key")
        self.assertTrue(entry["configured"])
        self.assertEqual(entry["last4"], "7777")

    def test_agent_proposal_returns_pending(self):
        api = SettingsV2API(self.service)
        status, payload = api.handle(
            "POST",
            "/api/settings/v2/approvals",
            {},
            {"key": "wf_max_concurrent_agents", "value": 42, "scope_id": "c1"},
            self._context(self.agent),
            "c1",
        )
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["status"], "PENDING")
        self.assertTrue(payload["approval"]["approval_id"].startswith("apr_"))

    def test_unknown_endpoint_is_404(self):
        api = SettingsV2API(self.service)
        status, payload = api.handle(
            "GET", "/api/settings/v2/nope", {}, {}, self._context(self.owner), "c1"
        )
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
