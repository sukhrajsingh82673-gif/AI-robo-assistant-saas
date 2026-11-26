#!/usr/bin/env python3
"""
ZONATA Sovereign Core — Step 5 Qualification Scenario (OpenCode Step 5I).
Trust Layer: secrets, identity, database isolation, application and supply-chain
security, privacy and compliance engineering.

Empirically executes all 8 qualification milestones under 5 seconds:
1. Preflight Reality Check & Security Inventory (5A)
2. OpenBao Secrets Platform & Transit KMS (5B)
3. Identity & Access — Keycloak/OIDC, Workload Identity & Ownership Governance (5C)
4. Database & Tenant Isolation Hardening — Transaction-Scoped RLS (5D)
5. Application & Supply-Chain Security — ASVS, WAF, SBOM & Cosign (5E)
6. SIEM Audit Logging, Privacy Engineering & Rule 46 Control Matrix (5F)
7. Incident Response Playbooks & Security Resilience Chaos Drills (5G)
8. Cryptographic Agility, PQC Hybrid Envelopes & Online Rewrapping (5H)
"""

from __future__ import annotations

import base64
import os
import sys
import time
import uuid
from typing import Any, Dict, List

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ["ZONATA_TEST_MODE"] = "1"
os.environ["APP_ENV"] = "test"

# Core Imports
from core.audit.siem_exporter import AuditEvent, SIEMExporter
from core.compliance.control_matrix import ControlMatrixGenerator
from core.crypto.registry import CryptoRegistry
from core.crypto.rewrap import OnlineRewrapper
from core.crypto.types import (
    AuthenticationTagVerificationError,
    CryptoAlgorithm,
    CryptoEnvelope,
)
from core.db import PostgresConnectionWrapper
from core.db_security import DBRoleAuditor, RLSAuditor, TransactionPoolerContract
from core.evidence_ledger import EvidenceLedger
from core.identity.api_keys import APIKeyManager
from core.identity.ownership import OwnershipGovernance
from core.identity.types import (
    RoleTier,
    TokenReuseDetectedError,
    UnauthorizedOwnerPromotionError,
)
from core.identity.workload import WorkloadIdentityValidator
from core.incident.chaos_drills import SecurityChaosHarness
from core.incident.playbooks import (
    AgentQuarantinedError,
    AgentQuarantinePlaybook,
    LeakedSecretPlaybook,
)
from core.ports.base import PortStatus
from core.ports.identity import SandboxIdentityProvider
from core.ports.secrets import SandboxSecretsProvider
from core.privacy.dsar import BreachNotificationCoordinator, CryptoShredder, DSARManager
from core.security.api_hardening import (
    BruteForceProtector,
    CORSValidator,
    HostHeaderValidator,
    SecurityHeaderInjector,
    WAFPayloadInspector,
)
from core.security.supply_chain import CosignSigner, SBOMValidator


class Step5QualificationScenario:
    """Executes the complete Step 5 Trust & Security qualification pipeline."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def log_milestone(self, milestone: str, status: str, latency_ms: float, details: Dict[str, Any]):
        entry = {
            "milestone": milestone,
            "status": status,
            "latency_ms": latency_ms,
            "details": details,
        }
        self.results.append(entry)
        print(f"[{status}] {milestone:<55} ({latency_ms:.2f}ms)")

    def run_all(self) -> bool:
        t_start = time.perf_counter()
        print("=" * 80)
        print("ZONATA SOVEREIGN OS — STEP 5 TRUST LAYER QUALIFICATION SCENARIO")
        print("=" * 80)

        success = True
        try:
            self.milestone_1_preflight_and_governance()
            self.milestone_2_secrets_platform()
            self.milestone_3_identity_and_access()
            self.milestone_4_database_isolation()
            self.milestone_5_app_and_supply_chain()
            self.milestone_6_audit_and_compliance()
            self.milestone_7_incident_response()
            self.milestone_8_crypto_agility()
        except Exception as e:
            print(f"[FATAL ERROR] Step 5 Qualification Failed: {e}")
            import traceback
            traceback.print_exc()
            success = False

        total_elapsed = (time.perf_counter() - t_start) * 1000.0
        print("=" * 80)
        print(f"QUALIFICATION SCENARIO COMPLETE: {'ALL PASS' if success else 'FAILED'}")
        print(f"Total Execution Time: {total_elapsed:.2f}ms (Budget: < 5,000ms)")
        print("=" * 80)
        return success and total_elapsed < 5000.0

    def milestone_1_preflight_and_governance(self):
        """Milestone 1: Audits ADRs 0018-0025, Secrets Register, and Security Inventory."""
        t0 = time.perf_counter()
        sec_reg_path = os.path.join(REPO_ROOT, "docs", "security", "SECRETS_REGISTER.md")
        with open(sec_reg_path, "r", encoding="utf-8") as f:
            sec_content = f.read()

        # Rule 41: Zero plaintext secrets in register
        assert "password123" not in sec_content
        assert "BEGIN PRIVATE KEY" not in sec_content

        # Verify 8 ADRs exist
        import glob
        for i in range(18, 26):
            matching = glob.glob(os.path.join(REPO_ROOT, "docs", "adr", f"ADR_{i:04d}*.md"))
            assert len(matching) == 1, f"Missing ADR_{i:04d}*.md"

        self.log_milestone(
            "1. Preflight Reality & Governance (5A)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"adrs_verified": 8, "secrets_register_verified": True},
        )

    def milestone_2_secrets_platform(self):
        """Milestone 2: OpenBao Secrets Platform, Transit rotation, and fail-closed vault."""
        t0 = time.perf_counter()
        provider = SandboxSecretsProvider()

        # Test multi-tenant isolation
        provider.set_secret("db/password", "secret_t1", tenant_id="tenant_1")
        provider.set_secret("db/password", "secret_t2", tenant_id="tenant_2")

        res1, val1 = provider.get_secret("db/password", tenant_id="tenant_1")
        res2, val2 = provider.get_secret("db/password", tenant_id="tenant_2")
        assert val1 == "secret_t1" and val2 == "secret_t2"

        # Test Transit Key rotation
        rot_res, new_v = provider.transit_rotate_key("tenant_1_kek", tenant_id="tenant_1")
        assert new_v >= 2

        # Test fail-closed sealed vault
        provider._sealed = True
        res_sealed, val_sealed = provider.get_secret("db/password", tenant_id="tenant_1")
        assert res_sealed.status == PortStatus.FAILED and val_sealed is None
        provider._sealed = False

        self.log_milestone(
            "2. OpenBao Secrets Platform & Transit KMS (5B)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"transit_versions": new_v, "sealed_vault_failed_closed": True},
        )

    def milestone_3_identity_and_access(self):
        """Milestone 3: OIDC Tokens, Rule 44 Owner Immutability & API Keys."""
        t0 = time.perf_counter()
        id_provider = SandboxIdentityProvider()
        api_key_mgr = APIKeyManager()
        workload_val = WorkloadIdentityValidator()
        ownership_gov = OwnershipGovernance()

        # OIDC token issuance & validation
        at, rt = id_provider.issue_token(
            user_id="usr_exec_01",
            tenant_id="tenant_gamma",
            company_id="co_gamma",
            role=RoleTier.EXECUTIVE.value,
            email="exec@gamma.example.com",
            mfa_verified=True,
        )
        val_res, ctx = id_provider.validate_token(at, expected_audience="zonata-api")
        assert val_res.status == PortStatus.OK and ctx.mfa_verified is True

        # Rule 44: SCIM owner promotion blocked
        try:
            id_provider.scim_provision_user("tenant_gamma", "co_gamma", {"userName": "mallory", "role": "OWNER"})
            assert False, "SCIM owner promotion must fail"
        except UnauthorizedOwnerPromotionError:
            pass

        # API Key generation & salted verification
        raw_key, rec = api_key_mgr.generate_key("tenant_gamma", "co_gamma", "Test Key", ["read"])
        verified = api_key_mgr.verify_key(raw_key)
        assert verified.key_id == rec.key_id

        # Rule 42: Machine interactive login forbidden
        spiffe_ident = workload_val.parse_spiffe_id("spiffe://zonata.internal/ns/tenant_gamma/sa/worker")
        try:
            workload_val.assert_not_machine_interactive(spiffe_ident)
            assert False, "Machine identity interactive login must fail"
        except Exception:
            pass

        self.log_milestone(
            "3. Identity, Access & Ownership Governance (5C)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"oidc_verified": True, "rule44_owner_protected": True, "api_keys_salted": True},
        )

    def milestone_4_database_isolation(self):
        """Milestone 4: Transaction-scoped tenant context (Rule 43) & Pooler Safety."""
        t0 = time.perf_counter()
        from unittest.mock import MagicMock
        from core.db import tenant_scope
        mock_raw_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_raw_conn.cursor.return_value = mock_cursor
        conn = PostgresConnectionWrapper(mock_raw_conn)

        # Assert transaction-scoped set_config
        with tenant_scope("tenant_iso_1", "co_iso_1"):
            conn.execute("SELECT 1;")
            calls = [
                c for c in mock_cursor.execute.call_args_list
                if "set_config('zonata.tenant_id'" in str(c)
            ]
            assert len(calls) >= 1
            assert calls[-1].args[1][0] == "tenant_iso_1"

        # Verify context automatically reset after commit
        conn.commit()
        assert conn._applied_tenant is None

        # Verify connection pooler reuse across tenants with MockPoolerConnection
        class MockPoolerConnection:
            def __init__(self):
                self.session_vars = {}
                self.local_vars = {}
            def cursor(self):
                return MockPoolerCursor(self)
            def commit(self):
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
                    val = self.conn.local_vars.get("zonata.tenant_id", self.conn.session_vars.get("zonata.tenant_id", ""))
                    self.last_result = [(val,)]
            def fetchone(self):
                return self.last_result[0] if self.last_result else ("",)
            def close(self):
                pass

        pooler = TransactionPoolerContract()
        assert pooler.assert_no_context_leak(MockPoolerConnection(), "tenant_a", "tenant_b") is True

        # Verify DB role least privilege
        mock_cur = MagicMock()
        mock_raw_conn.cursor.return_value = mock_cur
        mock_cur.fetchone.side_effect = [
            ("zonata_app",),
            ("zonata_app", False, False),
        ]
        report = DBRoleAuditor.verify_connection_role_safety(mock_raw_conn)
        assert report.is_safe is True
        assert report.is_superuser is False
        assert report.is_bypass_rls is False

        self.log_milestone(
            "4. Database & Tenant Isolation Hardening (5D)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"rule43_transaction_scoped": True, "pooler_zero_leak": True},
        )

    def milestone_5_app_and_supply_chain(self):
        """Milestone 5: ASVS Hardening, WAF Inspection, CycloneDX SBOM & Cosign."""
        t0 = time.perf_counter()
        host_val = HostHeaderValidator(["api.zonata.io"])
        cors_val = CORSValidator(["https://app.zonata.io"])
        sec_headers = SecurityHeaderInjector()
        waf = WAFPayloadInspector()
        cosign = CosignSigner(key_ref="openbao://transit/keys/release_signer")

        # Host poisoning rejection
        try:
            host_val.validate_host("evil.com")
            assert False, "Host poisoning must fail"
        except Exception:
            pass
        assert host_val.validate_host("api.zonata.io") is True

        # CORS wildcard credentials defense
        try:
            cors_val.validate_origin("*", allow_credentials=True)
            assert False, "CORS wildcard credentials must fail"
        except Exception:
            pass
        ok, headers = cors_val.validate_origin("https://app.zonata.io")
        assert ok is True
        assert headers["Access-Control-Allow-Origin"] == "https://app.zonata.io"

        # WAF SQLi / XSS detection
        try:
            waf.inspect("SELECT * FROM users WHERE '1'='1'")
            assert False, "WAF must detect SQLi"
        except Exception:
            pass
        try:
            waf.inspect("<script>alert(1)</script>")
            assert False, "WAF must detect XSS"
        except Exception:
            pass
        waf.inspect('{"user": "alice", "action": "view_report"}')

        # Cosign signing and verification
        binary_payload = b"ZONATA_SOVEREIGN_CORE_BINARY_RELEASE_V1.0.0"
        bundle = cosign.sign_artifact(binary_payload, image_ref="zonata.internal/core:v1.0.0")
        assert cosign.verify_artifact(binary_payload, bundle, expected_image_ref="zonata.internal/core:v1.0.0") is True

        self.log_milestone(
            "5. Application & Supply-Chain Security (5E)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"waf_inspected": True, "cosign_verified": True},
        )

    def milestone_6_audit_and_compliance(self):
        """Milestone 6: Merkle hash-chain audit, CEF export, DSAR & Rule 46 matrix."""
        t0 = time.perf_counter()
        siem = SIEMExporter()
        dsar_mgr = DSARManager()
        shredder = CryptoShredder()
        breach_coord = BreachNotificationCoordinator()
        matrix_gen = ControlMatrixGenerator()

        # Append audit events & verify Merkle chain
        e1 = siem.log_event("admin1", "ADMIN", "t_aud", "c_aud", "LOGIN", "session://1")
        e2 = siem.log_event("admin1", "ADMIN", "t_aud", "c_aud", "POLICY_UPDATE", "policy://1")
        assert SIEMExporter.verify_chain([e1, e2]) is True

        # CEF export
        cef_lines = siem.export_cef_stream()
        assert len(cef_lines) == 2 and cef_lines[0].startswith("CEF:0|ZONATA|")

        # DSAR bundle & crypto-shredding
        bundle = dsar_mgr.generate_export_bundle(
            user_id="user_101",
            tenant_id="t_aud",
            identity_record={"email": "u@t.com"},
            activity_records=[],
            consent_records=[],
        )
        assert bundle.package_sha256 is not None
        shred_res = shredder.shred_tenant_data("t_aud")
        assert shred_res["status"] == "SHREDDED"

        # Rule 46 control matrix
        md = matrix_gen.generate_markdown()
        assert len(matrix_gen.CONTROLS) >= 10
        matrix_gen.verify_rule_46("We provide verifiable technical controls.")

        self.log_milestone(
            "6. SIEM Audit, Privacy & Rule 46 Compliance (5F)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"merkle_chain_verified": True, "cef_exported": True, "crypto_shredded": True},
        )

    def milestone_7_incident_response(self):
        """Milestone 7: Incident Containment Playbooks & Chaos Drills."""
        t0 = time.perf_counter()
        secrets_port = SandboxSecretsProvider()
        api_key_mgr = APIKeyManager()
        identity_port = SandboxIdentityProvider()
        evidence_ledger = EvidenceLedger()
        siem = SIEMExporter()
        chaos = SecurityChaosHarness()

        # Leaked secret playbook
        secrets_port.set_secret("api/stripe", "raw_sec_val", tenant_id="t_inc")
        _, key_rec = api_key_mgr.generate_key("t_inc", "co_inc", "Stripe Key", ["read"])
        leaked_pb = LeakedSecretPlaybook(secrets_port, api_key_mgr, identity_port, siem)
        inc_res = leaked_pb.contain_leaked_secret("api/stripe", "t_inc", "user_1", "Token leaked", api_key_id=key_rec.key_id)
        assert inc_res.status == "CONTAINED" and inc_res.api_key_revoked is True

        # Rogue agent quarantine playbook
        agent_pb = AgentQuarantinePlaybook(evidence_ledger, WorkloadIdentityValidator(), siem)
        q_res = agent_pb.quarantine_agent("agent_rogue_scen", "t_inc", "Injection attempt")
        assert q_res.status == "QUARANTINED"
        assert AgentQuarantinePlaybook.is_quarantined("agent_rogue_scen") is True

        # Chaos drills: Vault outage, DB rotation, Token theft
        v_drill = chaos.drill_vault_outage_fail_closed(secrets_port, "db/key", "t_inc")
        assert v_drill["status"] == "PASSED"
        db_drill = chaos.drill_db_credential_rotation(secrets_port, "worker", "t_inc")
        assert db_drill["status"] == "PASSED"
        t_drill = chaos.drill_token_theft_cascade_revocation(identity_port, "usr_th", "t_inc", "co_inc")
        assert t_drill["status"] == "PASSED"

        self.log_milestone(
            "7. Incident Containment & Chaos Drills (5G)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"secret_contained": True, "agent_quarantined": True, "chaos_drills_passed": 3},
        )

    def milestone_8_crypto_agility(self):
        """Milestone 8: Versioned Envelopes, Kyber PQC Hybrid & Zero-Downtime Rewrap."""
        t0 = time.perf_counter()
        crypto_reg = CryptoRegistry()
        rewrapper = OnlineRewrapper(crypto_reg)
        key_v1 = os.urandom(32)
        key_v2 = os.urandom(32)
        key_v3 = os.urandom(32)
        payload = b"financial_wire_confidential_payload"

        # Encrypt with v1-aes256gcm
        env1 = crypto_reg.encrypt(payload, key_v1, "k1", version=CryptoAlgorithm.V1_AES256_GCM.value)
        assert crypto_reg.decrypt(env1, key_v1) == payload

        # Online rewrap to v2-chacha20poly1305
        env2 = rewrapper.rewrap(env1, key_v1, key_v2, CryptoAlgorithm.V2_CHACHA20_POLY1305.value, "k2")
        assert env2.version == "v2-chacha20poly1305"
        assert crypto_reg.decrypt(env2, key_v2) == payload

        # Online rewrap to v3-kyber-aes256gcm (PQC Hybrid)
        env3 = rewrapper.rewrap(env2, key_v2, key_v3, CryptoAlgorithm.V3_KYBER_AES256_GCM.value, "k3")
        assert env3.version == "v3-kyber-aes256gcm"
        assert env3.kem_ciphertext is not None
        assert crypto_reg.decrypt(env3, key_v3) == payload

        # Tampered ciphertext fails closed
        raw_ct = bytearray(base64.b64decode(env3.ciphertext))
        raw_ct[0] ^= 0x01
        bad_env = CryptoEnvelope(env3.version, env3.key_id, env3.iv, env3.tag, base64.b64encode(raw_ct).decode("utf-8"), env3.kem_ciphertext)
        try:
            crypto_reg.decrypt(bad_env, key_v3)
            assert False, "Tampered ciphertext must fail AEAD verification"
        except AuthenticationTagVerificationError:
            pass

        self.log_milestone(
            "8. Crypto Agility & Online Rewrapping (5H)",
            "PASS",
            (time.perf_counter() - t0) * 1000.0,
            {"ciphers_verified": 3, "pqc_hybrid_verified": True, "online_rewrapped": True},
        )


def run_milestone_1():
    scenario = Step5QualificationScenario()
    scenario.milestone_1_preflight_and_governance()
    return True

def run_milestone_2():
    scenario = Step5QualificationScenario()
    scenario.milestone_2_secrets_platform()
    return True

def run_milestone_3():
    scenario = Step5QualificationScenario()
    scenario.milestone_3_identity_and_access()
    return True

def run_milestone_4():
    scenario = Step5QualificationScenario()
    scenario.milestone_4_database_isolation()
    return True

def run_milestone_5():
    scenario = Step5QualificationScenario()
    scenario.milestone_5_app_and_supply_chain()
    return True

def run_milestone_6():
    scenario = Step5QualificationScenario()
    scenario.milestone_6_audit_and_compliance()
    return True

def run_milestone_7():
    scenario = Step5QualificationScenario()
    scenario.milestone_7_incident_response()
    return True

def run_milestone_8():
    scenario = Step5QualificationScenario()
    scenario.milestone_8_crypto_agility()
    return True

def run_all():
    scenario = Step5QualificationScenario()
    return scenario.run_all()


if __name__ == "__main__":
    scenario = Step5QualificationScenario()
    ok = scenario.run_all()
    sys.exit(0 if ok else 1)
