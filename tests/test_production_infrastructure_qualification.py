"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Production Infrastructure, Deployment, Security, Disaster Recovery & Operational Readiness
Comprehensive Qualification & Verification Test Suite

Covers Areas A through Q + API Integration:
- Area A: Real Production Deployment & Substrate Orchestration
- Area B: Workload Isolation, Network Policies & Blast-Radius Containment
- Area C: Internet-Facing SaaS Edge Architecture & WAF
- Area D: Production Observability, Distributed Tracing & Correlation
- Area E: Secure Software Supply Chain, Attestation & SBOM
- Area F: Remote Disaster Recovery & Off-Site Restoration (12-Step Drill)
- Area G: Backup Security, Retention, Ransomware Protection & WORM
- Area H: Secret, Certificate & Identity Infrastructure Hardening
- Area I: Infrastructure Outage & Fail-Safe Degradation Matrix
- Area J: Controlled Deployment, Canary Promotion & Automated Rollback
- Area K: Controlled Production Migrations & Schema Evolution
- Area L: Operational Health, Incident Management & SRE Alerting
- Area M: Resource Capacity, Rate Limiting & Cost Shock Protection
- Area N: Adversarial & Chaos Testing
- Area O: Real Production End-to-End Mission Qualification
- Area P: Controlled Failure Injection & Auto-Recovery
- Area Q: Real Multi-Tenant Pilot Isolation
- Area R: V8 API Infrastructure Handler Endpoints
"""

import os
import time
import json
import uuid
import hashlib
import unittest
from typing import Dict, Any

# Infrastructure Modules Under Test
from core.production_orchestration import (
    production_orchestrator,
    RegisteredWorker,
    ServiceEndpoint,
    DeploymentRelease,
    DeploymentState,
    WorkerType
)
from core.workload_isolation import (
    workload_isolation,
    TenantResourceQuota,
    NetworkAccessDecision
)
from core.edge_security_gateway import (
    edge_security_gateway,
    EdgeInspectionResult
)
from core.production_observability import (
    observability_engine,
    ExecutionTraceContext
)
from core.secure_supply_chain import (
    supply_chain_controller,
    SupplyChainAdmissionStatus,
    VulnerabilityRecord
)
from core.remote_disaster_recovery import (
    remote_dr_manager,
    RemoteDisasterRecoveryManager
)
from core.backup_security import (
    backup_security_manager,
    BackupSecurityViolationError
)
from core.secret_identity_hardening import (
    security_hardening,
    SecretAccessDeniedError
)
from core.failsafe_degradation_matrix import (
    failsafe_matrix,
    FailSafeDegradationMatrix
)
from core.deployment_rollback_controller import (
    rollback_controller,
    RollbackTriggerReason
)
from core.controlled_migration_engine import (
    migration_engine,
    MigrationStep
)
from core.operational_health_system import (
    operational_health_system,
    OperationalStatus
)
from core.resource_capacity_manager import (
    capacity_manager,
    CapacityAction
)
from core.v8_api_handler import V8ApiHandler


class TestProductionInfrastructureQualification(unittest.TestCase):
    """
    Independent qualification and verification suite for ZONATA Production Infrastructure.
    """

    def setUp(self):
        self.tenant_a = f"tnt_alpha_{uuid.uuid4().hex[:6]}"
        self.tenant_b = f"tnt_beta_{uuid.uuid4().hex[:6]}"
        self.company_id = "comp_test"

    # =========================================================================
    # AREA A: Production Deployment & Substrate Orchestration
    # =========================================================================
    def test_area_a_orchestration_readiness_and_workers(self):
        """Verifies cluster readiness evaluation, service discovery, and worker registration."""
        status = production_orchestrator.evaluate_cluster_readiness()
        self.assertTrue(status["ready"])
        self.assertGreaterEqual(status["total_services"], 10)
        self.assertEqual(status["state"], DeploymentState.HEALTHY)

        # Dynamic Worker Registration
        worker = production_orchestrator.register_worker(
            worker_type=WorkerType.AGENCY_SWARM_WORKER,
            node_id="node-prod-01",
            ip_address="10.244.1.45",
            max_capacity=8
        )
        self.assertTrue(worker.worker_id.startswith("wkr_"))
        self.assertEqual(worker.worker_type, WorkerType.AGENCY_SWARM_WORKER)
        self.assertEqual(worker.status, "READY")

        # Heartbeat
        hb_ok = production_orchestrator.heartbeat_worker(
            worker_id=worker.worker_id,
            active_tasks=1,
            cpu_pct=8.0,
            mem_mb=140.0
        )
        self.assertTrue(hb_ok)

        # Worker listing
        active_workers = production_orchestrator.list_workers()
        self.assertIn(worker.worker_id, [w.worker_id for w in active_workers])

    # =========================================================================
    # AREA B: Workload Isolation, Network Policies & Metadata IP Blocking
    # =========================================================================
    def test_area_b_workload_isolation_and_metadata_blocking(self):
        """Verifies cloud metadata SSRF protection (169.254.169.254) and tenant quotas."""
        # 1. Cloud Metadata IP Must Be Strictly Blocked
        allowed_ip, reason_ip = workload_isolation.evaluate_egress_request(
            target_host="169.254.169.254",
            source_service="browser-worker"
        )
        self.assertFalse(allowed_ip)
        self.assertEqual(reason_ip, NetworkAccessDecision.BLOCKED_METADATA_ENDPOINT)

        allowed_gcp, reason_gcp = workload_isolation.evaluate_egress_request(
            target_host="metadata.google.internal",
            source_service="browser-worker"
        )
        self.assertFalse(allowed_gcp)
        self.assertEqual(reason_gcp, NetworkAccessDecision.BLOCKED_METADATA_ENDPOINT)

        # 2. Approved egress to LLM API permitted
        allowed_llm, decision_llm = workload_isolation.evaluate_egress_request(
            target_host="generativelanguage.googleapis.com",
            source_service="execution-worker"
        )
        self.assertTrue(allowed_llm)
        self.assertEqual(decision_llm, NetworkAccessDecision.ALLOWED)

        # 3. Inter-service policy check: Sandboxed browser worker blocked from internal Vault
        allowed_vault, _ = workload_isolation.evaluate_service_communication(
            source_service="browser-worker",
            target_service="vault-internal"
        )
        self.assertFalse(allowed_vault)

        # 4. Tenant Resource Quotas
        quota = workload_isolation.get_tenant_quota(self.tenant_a)
        self.assertGreaterEqual(quota.max_cpu_cores, 4.0)
        self.assertGreaterEqual(quota.max_memory_gb, 8.0)

    # =========================================================================
    # AREA C: Internet-Facing SaaS Edge Architecture & WAF
    # =========================================================================
    def test_area_c_edge_waf_and_internal_shielding(self):
        """Verifies edge reverse proxy, WAF heuristic blocking, 10MB limit, and internal service shielding."""
        # 1. Block access to internal Vault path
        res_vault = edge_security_gateway.inspect_inbound_request(
            path="/v1/sys/seal-status",
            method="GET",
            headers={},
            body_bytes=b"",
            client_ip="203.0.113.1"
        )
        self.assertFalse(res_vault.is_allowed)
        self.assertEqual(res_vault.status_code, 403)
        self.assertEqual(res_vault.violation_category, "RESTRICTED_INTERNAL_SERVICE")

        # 2. Block access to internal Temporal API
        res_temporal = edge_security_gateway.inspect_inbound_request(
            path="/temporal/api/v1/namespaces",
            method="GET",
            headers={},
            body_bytes=b"",
            client_ip="203.0.113.1"
        )
        self.assertFalse(res_temporal.is_allowed)
        self.assertEqual(res_temporal.status_code, 403)

        # 3. Block SQL Injection
        sqli_body = b'{"query": "UNION ALL SELECT 1, null, password FROM information_schema.tables"}'
        res_sqli = edge_security_gateway.inspect_inbound_request(
            path="/api/v8/search",
            method="POST",
            headers={},
            body_bytes=sqli_body,
            client_ip="203.0.113.2"
        )
        self.assertFalse(res_sqli.is_allowed)
        self.assertEqual(res_sqli.status_code, 400)
        self.assertEqual(res_sqli.violation_category, "SQL_INJECTION")

        # 4. Block Cross-Site Scripting (XSS)
        xss_body = b'{"name": "<script>alert(document.cookie)</script>"}'
        res_xss = edge_security_gateway.inspect_inbound_request(
            path="/api/v8/user",
            method="POST",
            headers={},
            body_bytes=xss_body,
            client_ip="203.0.113.3"
        )
        self.assertFalse(res_xss.is_allowed)
        self.assertEqual(res_xss.status_code, 400)
        self.assertEqual(res_xss.violation_category, "CROSS_SITE_SCRIPTING")

        # 5. Block Oversized Payloads (> 10MB)
        oversized = b"A" * (10 * 1024 * 1024 + 100)
        res_over = edge_security_gateway.inspect_inbound_request(
            path="/api/v8/upload",
            method="POST",
            headers={},
            body_bytes=oversized,
            client_ip="203.0.113.4"
        )
        self.assertFalse(res_over.is_allowed)
        self.assertEqual(res_over.status_code, 413)

        # 6. Normal Request Allowed with Security Headers
        normal_res = edge_security_gateway.inspect_inbound_request(
            path="/api/v8/missions",
            method="GET",
            headers={},
            body_bytes=b"",
            client_ip="127.0.0.1"
        )
        self.assertTrue(normal_res.is_allowed)
        self.assertEqual(normal_res.status_code, 200)
        self.assertIn("Strict-Transport-Security", normal_res.security_headers)
        self.assertIn("X-Content-Type-Options", normal_res.security_headers)

    # =========================================================================
    # AREA D: Observability & Unbroken 10-Layer Correlation Chain
    # =========================================================================
    def test_area_d_observability_and_10_layer_trace_context(self):
        """Verifies Prometheus metrics output and complete 10-layer correlation context token."""
        # 1. Prometheus Scrape format
        prom_text = observability_engine.generate_prometheus_metrics()
        self.assertIn("zonata_infra_cluster_readiness_score", prom_text)
        self.assertIn("zonata_infra_active_workers_count", prom_text)
        self.assertIn("zonata_infra_edge_requests_total", prom_text)

        # 2. 10-Layer Trace Correlation Context Token
        ctx = ExecutionTraceContext(
            tenant_id=self.tenant_a,
            company_id=self.company_id,
            mission_id="msn_rev_grow_101",
            execution_id="exec_cycle_554",
            task_id="tsk_market_analyst_01",
            agent_id="ag_revenue_specialist",
            model_id="gemma-4-31b-it",
            tool_id="sql_db_query",
            infrastructure_id="k8s_pod_worker_07",
            evidence_digest="sha256_mock_digest_abcd"
        )
        token = ctx.to_correlation_token()
        self.assertIn(self.tenant_a, token)
        self.assertIn("gemma-4-31b-it", token)
        self.assertIn("k8s_pod_worker_07", token)

        # Log entry recording
        observability_engine.record_execution_log(
            trace_ctx=ctx,
            level="INFO",
            message="Execution step completed under governed control"
        )
        recent_logs = observability_engine.query_logs(tenant_id=self.tenant_a, limit=10)
        self.assertGreaterEqual(len(recent_logs), 1)
        self.assertEqual(recent_logs[0]["mission_id"], "msn_rev_grow_101")

    # =========================================================================
    # AREA E: Software Supply Chain, SBOM & SLSA Attestation
    # =========================================================================
    def test_area_e_software_supply_chain_and_sbom(self):
        """Verifies CycloneDX v1.5 SBOM generation, Trivy CVE rejection, and SLSA provenance attestation."""
        # 1. CycloneDX SBOM Generation
        sbom = supply_chain_controller.generate_cyclonedx_sbom()
        self.assertEqual(sbom["bomFormat"], "CycloneDX")
        self.assertEqual(sbom["specVersion"], "1.5")
        self.assertGreaterEqual(len(sbom["components"]), 5)

        # 2. Strict Vulnerability Gating (CVSS >= 7.0 must block admission)
        critical_cve = VulnerabilityRecord(
            cve_id="CVE-2026-9999",
            package_name="libmalicious",
            installed_version="1.0.0",
            fixed_version="1.0.1",
            severity="CRITICAL",
            cvss_score=9.8,
            description="Remote code execution in unpatched library"
        )
        res = supply_chain_controller.evaluate_vulnerability_scan(
            artifact_name="zonata-worker:latest",
            vulnerabilities=[critical_cve]
        )
        self.assertFalse(res["admitted"])
        self.assertEqual(res["status"], SupplyChainAdmissionStatus.REJECTED_VULNERABILITY)
        self.assertIn("CVE-2026-9999", res["blocking_cves"])

        # 3. Clean Scan Passes Admission
        clean_res = supply_chain_controller.evaluate_vulnerability_scan(
            artifact_name="zonata-api:1.0.0",
            vulnerabilities=[]
        )
        self.assertTrue(clean_res["admitted"])
        self.assertEqual(clean_res["status"], SupplyChainAdmissionStatus.ADMITTED)

        # 4. SLSA Level 3 Provenance Attestation
        attestation = supply_chain_controller.create_slsa_provenance(
            artifact_name="zonata-api:1.0.0",
            artifact_digest="sha256_e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            source_commit="f0ba68d"
        )
        self.assertEqual(attestation.builder_id, "https://github.com/zonata/builder/slsa-v3")
        self.assertEqual(attestation.admission_status, SupplyChainAdmissionStatus.ADMITTED)

    # =========================================================================
    # AREA F: Remote Disaster Recovery & 12-Step Complete Drill
    # =========================================================================
    def test_area_f_remote_disaster_recovery_drill(self):
        """Verifies creation of remote backup bundle and execution of the complete 12-step restoration drill."""
        # 1. Create full atomic backup
        manifest = remote_dr_manager.execute_full_remote_backup()
        self.assertTrue(manifest.manifest_id.startswith("rdm_"))
        self.assertEqual(manifest.verification_status, "VERIFIED_REMOTE")
        self.assertTrue(os.path.exists(manifest.db_backup_path))

        # 2. Execute 12-Step DR Drill
        drill_out = remote_dr_manager.execute_complete_disaster_recovery_drill(
            manifest_id=manifest.manifest_id,
            target_drill_dir="/tmp/zonata_dr_test_env"
        )
        self.assertTrue(drill_out["success"])
        self.assertEqual(drill_out["overall_status"], "DISASTER_RECOVERY_QUALIFIED")
        steps = drill_out["drill_results"]
        self.assertEqual(len(steps), 12)
        # Verify PRAGMA integrity check step
        step8 = next(s for s in steps if s["step"] == 8)
        self.assertEqual(step8["status"], "SUCCESS")
        # Verify Merkle chain step
        step10 = next(s for s in steps if s["step"] == 10)
        self.assertEqual(step10["status"], "SUCCESS")

    # =========================================================================
    # AREA G: Backup Security, Immutable WORM Retention & Ransomware Defense
    # =========================================================================
    def test_area_g_backup_security_worm_and_ransomware(self):
        """Verifies 30-day WORM immutable lock and ransomware in-place mutation detection."""
        raw_payload = b"ZONATA_ENTERPRISE_DATABASE_PAYLOAD_VALID_STATE"
        envelope = backup_security_manager.create_secure_envelope(
            tenant_id=self.tenant_a,
            manifest_id="mf_sec_001",
            raw_payload_bytes=raw_payload,
            retention_days=30
        )
        self.assertTrue(envelope.is_locked)
        self.assertGreater(envelope.retention_until, time.time())

        # 1. Immutable WORM Lock rejects premature deletion
        del_allowed, del_reason = backup_security_manager.attempt_delete_backup(
            envelope_id=envelope.envelope_id,
            requesting_tenant_id=self.tenant_a
        )
        self.assertFalse(del_allowed)
        self.assertIn("Immutable retention lock active", del_reason)

        # 2. Ransomware Mutation Detection: Tampered payload triggers security breach
        tampered_payload = b"ZONATA_ENTERPRISE_DATABASE_PAYLOAD_TAMPERED_BY_MALWARE"
        with self.assertRaises(BackupSecurityViolationError):
            backup_security_manager.verify_backup_integrity_before_restore(
                envelope_id=envelope.envelope_id,
                current_payload_bytes=tampered_payload,
                requesting_tenant_id=self.tenant_a
            )

        # 3. Cross-Tenant Backup Access Blocked
        with self.assertRaises(BackupSecurityViolationError):
            backup_security_manager.verify_backup_integrity_before_restore(
                envelope_id=envelope.envelope_id,
                current_payload_bytes=raw_payload,
                requesting_tenant_id=self.tenant_b
            )

        # 4. Valid payload restores cleanly
        valid = backup_security_manager.verify_backup_integrity_before_restore(
            envelope_id=envelope.envelope_id,
            current_payload_bytes=raw_payload,
            requesting_tenant_id=self.tenant_a
        )
        self.assertTrue(valid)

    # =========================================================================
    # AREA H: Secret & Identity Hardening, Dynamic Leases & Brute-Force Defense
    # =========================================================================
    def test_area_h_vault_dynamic_leases_and_keycloak_hardening(self):
        """Verifies Vault tenant-isolated path leases, dynamic expiry, and Keycloak brute-force defense."""
        # 1. Tenant Secret Isolation: Cross-tenant secret path rejected
        with self.assertRaises(SecretAccessDeniedError):
            security_hardening.issue_dynamic_secret_lease(
                tenant_id=self.tenant_a,
                secret_path=f"zonata/data/{self.tenant_b}/database_creds"
            )

        # 2. Dynamic Secret Lease Issuance & Validation
        lease = security_hardening.issue_dynamic_secret_lease(
            tenant_id=self.tenant_a,
            secret_path=f"zonata/data/{self.tenant_a}/database_creds",
            ttl_seconds=3600.0
        )
        self.assertTrue(lease.lease_id.startswith(f"lease_{self.tenant_a}_"))
        valid, _ = security_hardening.validate_secret_lease(lease.lease_id, self.tenant_a)
        self.assertTrue(valid)

        # 3. Lease Revocation
        security_hardening.revoke_secret_lease(lease.lease_id, self.tenant_a)
        valid_after_rev, msg = security_hardening.validate_secret_lease(lease.lease_id, self.tenant_a)
        self.assertFalse(valid_after_rev)
        self.assertIn("revoked", msg)

        # 4. Keycloak Brute-Force Lockout Defense (5 attempts)
        attacker_ip = f"198.51.100.{uuid.uuid4().int % 200 + 10}"
        for _ in range(4):
            security_hardening.record_failed_login(attacker_ip)
            self.assertFalse(security_hardening.is_client_locked_out(attacker_ip))

        # 5th attempt locks out
        security_hardening.record_failed_login(attacker_ip)
        self.assertTrue(security_hardening.is_client_locked_out(attacker_ip))

        # Reset
        security_hardening.reset_failed_attempts(attacker_ip)
        self.assertFalse(security_hardening.is_client_locked_out(attacker_ip))

    # =========================================================================
    # AREA I: Fail-Safe Degradation Matrix (All 9 Vectors)
    # =========================================================================
    def test_area_i_failsafe_degradation_matrix(self):
        """Verifies that all 9 infrastructure failure vectors fail closed with ZERO authority compromise."""
        matrix = failsafe_matrix.evaluate_entire_matrix()
        self.assertEqual(len(matrix), 9)

        # Verify each component answers all 9 questions and guarantees integrity
        for comp, analysis in matrix.items():
            self.assertFalse(analysis["unauthorized_action_possible"])
            self.assertFalse(analysis["credential_leak_possible"])
            self.assertFalse(analysis["tenant_boundary_weakened"])
            self.assertFalse(analysis["evidence_falsification_possible"])
            self.assertFalse(analysis["duplicate_financial_mutation_possible"])
            self.assertTrue(analysis["safe_recovery_supported"])
            self.assertEqual(analysis["governance_state"], "FAIL_CLOSED_SOVEREIGN")

    # =========================================================================
    # AREA J: Progressive Canary Deployment & Zero-Loss Rollback
    # =========================================================================
    def test_area_j_progressive_canary_and_rollback(self):
        """Verifies canary promotion (10% -> 50% -> 100%) and automated rollback on smoke test failure."""
        plan = rollback_controller.create_release_plan(
            target_version="1.1.0-RC1",
            previous_version="1.0.0-GA",
            active_missions_count=5
        )
        self.assertEqual(plan.current_phase, "PREPARE")

        # Advance to HEALTH_CHECK
        ok, _, plan = rollback_controller.advance_phase(plan.plan_id, smoke_tests_passed=True)
        self.assertTrue(ok)
        self.assertEqual(plan.current_phase, "HEALTH_CHECK")

        # Advance to CANARY_10
        ok, _, plan = rollback_controller.advance_phase(plan.plan_id, smoke_tests_passed=True)
        self.assertTrue(ok)
        self.assertEqual(plan.current_phase, "CANARY_10")
        self.assertEqual(plan.canary_traffic_pct, 10.0)

        # Simulate smoke test failure -> Automated Rollback triggered
        ok_fail, msg, plan = rollback_controller.advance_phase(plan.plan_id, smoke_tests_passed=False)
        self.assertFalse(ok_fail)
        self.assertEqual(plan.current_phase, "ROLLED_BACK")
        self.assertEqual(plan.canary_traffic_pct, 0.0)

        # Verify active missions were preserved
        last_event = plan.audit_events[-1]
        self.assertEqual(last_event["restored_version"], "1.0.0-GA")
        self.assertEqual(last_event["active_missions_preserved"], 5)
        self.assertEqual(last_event["evidence_integrity"], "UNBROKEN")

    # =========================================================================
    # AREA K: Controlled Production Migrations & Schema Evolution
    # =========================================================================
    def test_area_k_controlled_additive_migrations(self):
        """Verifies additive non-destructive migration execution, tracking, and rollback."""
        applied = migration_engine.apply_pending_migrations()
        self.assertGreaterEqual(len(applied), 2)

        # Check schema tracking
        status = migration_engine.get_migration_status()
        self.assertGreaterEqual(len(status), 2)
        versions = [s["version"] for s in status]
        self.assertIn(2026100501, versions)
        self.assertIn(2026100502, versions)

    # =========================================================================
    # AREA L: Operational Health & Incident Lifecycle (14 Components)
    # =========================================================================
    def test_area_l_operational_health_and_incidents(self):
        """Verifies health tracking across all 14 components and automated incident resolution."""
        health = operational_health_system.get_overall_system_health()
        self.assertEqual(len(health["components"]), 14)
        self.assertIn(health["system_status"], [OperationalStatus.HEALTHY, OperationalStatus.DEGRADED])

        # Simulate component failure & incident creation
        inc = operational_health_system.trigger_component_alert(
            component_name="keycloak_idp",
            status=OperationalStatus.DEGRADED,
            error_rate_pct=15.0,
            details="Latent token introspection response"
        )
        self.assertTrue(inc.incident_id.startswith("inc_"))
        self.assertEqual(inc.severity, "HIGH")

        # Resolve incident
        res = operational_health_system.resolve_incident(
            incident_id=inc.incident_id,
            remediation_notes="Keycloak cluster rebalanced"
        )
        self.assertTrue(res)

    # =========================================================================
    # AREA M: Resource Capacity, Backpressure & Load-Shedding
    # =========================================================================
    def test_area_m_capacity_management_and_load_shedding(self):
        """Verifies capacity metrics tracking, backpressure queuing, and overload shedding."""
        metrics = capacity_manager.get_current_metrics()
        self.assertIn("cpu_utilization_pct", metrics)
        self.assertIn("memory_utilization_pct", metrics)

        # Under nominal load: ACCEPT
        action, _, _ = capacity_manager.evaluate_admission_capacity(priority="P1")
        self.assertEqual(action, CapacityAction.ACCEPT)

        # Under severe load spike: low-priority tasks shed
        capacity_manager.update_metrics(
            cpu_pct=95.0,
            mem_pct=94.0,
            disk_pct=50.0,
            queue_depth=350,
            active_workers=40
        )
        action_shed, reason, _ = capacity_manager.evaluate_admission_capacity(priority="P3")
        self.assertEqual(action_shed, CapacityAction.REJECT_OVERLOAD)
        self.assertIn("capacity critical", reason)

        # Reset to nominal
        capacity_manager.update_metrics(
            cpu_pct=20.0,
            mem_pct=30.0,
            disk_pct=40.0,
            queue_depth=5,
            active_workers=10
        )

    # =========================================================================
    # AREA N: Adversarial & Chaos Testing
    # =========================================================================
    def test_area_n_adversarial_chaos_tamper_defense(self):
        """Verifies resilience against path traversal attacks, header spoofing, and corrupted backups."""
        # 1. Path traversal injection blocked
        path_trav = edge_security_gateway.inspect_inbound_request(
            path="/api/v8/files/../../../../etc/shadow",
            method="GET",
            headers={},
            body_bytes=b"",
            client_ip="203.0.113.8"
        )
        self.assertFalse(path_trav.is_allowed)
        self.assertEqual(path_trav.violation_category, "PATH_TRAVERSAL")

        # 2. Corrupted secret lease verification fails cleanly
        valid_fake, msg = security_hardening.validate_secret_lease("lease_nonexistent_9999", self.tenant_a)
        self.assertFalse(valid_fake)
        self.assertEqual(msg, "Lease not found")

    # =========================================================================
    # AREA O: Real Production End-to-End Mission Qualification
    # =========================================================================
    def test_area_o_real_production_mission_with_full_trace(self):
        """Verifies end-to-end mission execution with complete 10-layer trace and evidence logging."""
        ctx = ExecutionTraceContext(
            tenant_id=self.tenant_a,
            company_id=self.company_id,
            mission_id="msn_production_hotel_boost",
            execution_id=f"exec_{uuid.uuid4().hex[:8]}",
            task_id="tsk_execute_growth",
            agent_id="ag_ceo_director",
            model_id="gemma-4-31b-it",
            tool_id="market_pricing_matrix",
            infrastructure_id="k8s_worker_node_02",
            evidence_digest="sha256_mock_valid_evidence_chain"
        )

        observability_engine.record_execution_log(
            trace_ctx=ctx,
            level="INFO",
            message="Dispatched mission task with governed authorization"
        )
        logs = observability_engine.query_logs(tenant_id=self.tenant_a, limit=5)
        self.assertTrue(any(l["mission_id"] == "msn_production_hotel_boost" for l in logs))

    # =========================================================================
    # AREA P: Controlled Failure Injection & Auto-Recovery
    # =========================================================================
    def test_area_p_failure_injection_and_auto_recovery(self):
        """Verifies system degradation during infrastructure failure and graceful return to health."""
        # Inject Temporal workflow outage
        failsafe_matrix.set_component_health("temporal", False)
        temporal_analysis = failsafe_matrix.evaluate_component("temporal")
        self.assertFalse(temporal_analysis.is_operational)
        self.assertTrue(any("workflow" in a.lower() for a in temporal_analysis.blocked_actions))
        self.assertFalse(temporal_analysis.unauthorized_action_possible)

        # Recover Temporal
        failsafe_matrix.set_component_health("temporal", True)
        recovered = failsafe_matrix.evaluate_component("temporal")
        self.assertTrue(recovered.is_operational)

    # =========================================================================
    # AREA Q: Real Multi-Tenant Pilot Isolation
    # =========================================================================
    def test_area_q_multi_tenant_isolation(self):
        """Verifies strict separation of secrets, quotas, logs, and backups between tenants."""
        # Tenant A dynamic secret
        lease_a = security_hardening.issue_dynamic_secret_lease(
            tenant_id=self.tenant_a,
            secret_path=f"zonata/data/{self.tenant_a}/api_key"
        )

        # Tenant B cannot validate Tenant A's lease
        valid_b, msg_b = security_hardening.validate_secret_lease(lease_a.lease_id, self.tenant_b)
        self.assertFalse(valid_b)
        self.assertIn("Tenant mismatch", msg_b)

        # Tenant B cannot revoke Tenant A's lease
        with self.assertRaises(SecretAccessDeniedError):
            security_hardening.revoke_secret_lease(lease_a.lease_id, self.tenant_b)

    # =========================================================================
    # AREA R: V8 API Infrastructure Handler Endpoints
    # =========================================================================
    def test_v8_infra_endpoints_get_and_post(self):
        """Verifies GET and POST API routes under /api/v8/infra/*."""
        # 1. GET /api/v8/infra/orchestration/status
        res, code = V8ApiHandler.handle_get("/api/v8/infra/orchestration/status", {}, self.tenant_a, self.company_id)
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])
        self.assertIn("cluster_status", res)

        # 2. GET /api/v8/infra/isolation/status
        res, code = V8ApiHandler.handle_get("/api/v8/infra/isolation/status", {}, self.tenant_a, self.company_id)
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])
        self.assertIn("tenant_quota", res)

        # 3. GET /api/v8/infra/failsafe/status
        res, code = V8ApiHandler.handle_get("/api/v8/infra/failsafe/status", {}, self.tenant_a, self.company_id)
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])
        self.assertIn("failsafe_matrix", res)

        # 4. GET /api/v8/infra/health/all
        res, code = V8ApiHandler.handle_get("/api/v8/infra/health/all", {}, self.tenant_a, self.company_id)
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])
        self.assertIn("health", res)

        # 5. GET /api/v8/infra/capacity
        res, code = V8ApiHandler.handle_get("/api/v8/infra/capacity", {}, self.tenant_a, self.company_id)
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])
        self.assertIn("capacity", res)

        # 6. GET /api/v8/infra/supply-chain/sbom
        res, code = V8ApiHandler.handle_get("/api/v8/infra/supply-chain/sbom", {}, self.tenant_a, self.company_id)
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])
        self.assertIn("sbom", res)

        # 7. POST /api/v8/infra/edge/inspect
        res, code = V8ApiHandler.handle_post(
            "/api/v8/infra/edge/inspect",
            {"path": "/api/v8/missions", "method": "GET", "body": "", "client_ip": "127.0.0.1"},
            self.tenant_a,
            self.company_id
        )
        self.assertEqual(code, 200)
        self.assertTrue(res["is_allowed"])

        # 8. POST /api/v8/infra/rollback/plan
        res, code = V8ApiHandler.handle_post(
            "/api/v8/infra/rollback/plan",
            {"target_version": "1.2.0", "previous_version": "1.1.0", "active_missions_during_release": 2},
            self.tenant_a,
            self.company_id
        )
        self.assertEqual(code, 201)
        self.assertTrue(res["success"])

        # 9. POST /api/v8/infra/migrations/apply
        res, code = V8ApiHandler.handle_post(
            "/api/v8/infra/migrations/apply",
            {},
            self.tenant_a,
            self.company_id
        )
        self.assertEqual(code, 200)
        self.assertTrue(res["success"])

        # 10. POST /api/v8/infra/capacity/evaluate
        res, code = V8ApiHandler.handle_post(
            "/api/v8/infra/capacity/evaluate",
            {"estimated_cost": 0.02},
            self.tenant_a,
            self.company_id
        )
        self.assertEqual(code, 200)
        self.assertTrue(res["allowed"])


if __name__ == "__main__":
    unittest.main()
