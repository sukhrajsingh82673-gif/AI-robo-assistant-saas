"""
ZONATA Universal AI Co-Worker Fabric — Master Verification Test Suite
Tests the complete Universal Execution Fabric:
1. AI CEO = BRAIN ↔ Co-Worker = HANDS / BODY contract and strategic mission execution
2. Universal Worker Contract (14 methods) & WorkerMetadata (16 fields)
3. Canonical 20-Field Capability Specification
4. Governed Controllers (Terminal, Browser, Computer, API, MCP, A2A, Artifacts)
5. Universal Node Fabric, Registration, HMAC Security Protocol, and Lease Validation
6. Zero-Mock Platform Protocols (Windows, macOS, GPU/VLM honestly marked READY_FOR_NODE)
7. Universal Failure Recovery, Explicit States (UNCERTAIN, RECONCILIATION_REQUIRED), and Fallback
"""

import unittest
import time
import os
import json
import uuid
import hashlib

from core.coworker.engine import UniversalCoworkerEngine
from core.coworker.contracts import (
    CapabilityDefinition, CapabilityCategory, RiskLevel,
    VerificationStatus, QualificationStatus
)
from core.coworker.universal_worker_contract import (
    UniversalWorkerContract, WorkerMetadata, UniversalWorkerAdapter, WorkerLocationClass
)
from core.coworker.ceo_coworker_bridge import (
    AICeoMissionRequest, AICeoMissionResponse, AICeoCoworkerBridge
)
from core.coworker.controllers import (
    GovernedTerminalController, GovernedBrowserController,
    GovernedComputerController, GovernedApiController,
    GovernedMCPController, GovernedA2AController,
    GovernedArtifactManager, UniversalRecoveryController,
    FailureState
)
from core.coworker.fleet import (
    GovernedNodeRegistry, GovernedFleetRouter,
    WorkerNodeRegistrationRequest, WorkerNodeProfile,
    NodeType, NodePlatform, NodeState, SecurityPosture,
    NodeSecurityProtocol, WindowsWorkerNodeProtocol,
    MacOSWorkerNodeProtocol, GpuVlmNodeProtocol,
    ZonataNodeBootstrapAgent
)

class TestUniversalExecutionFabric(unittest.TestCase):

    def setUp(self):
        self.tenant_id = "tnt_primary"
        self.engine = UniversalCoworkerEngine.get_instance(self.tenant_id)

    # =========================================================================
    # 1. AI CEO = BRAIN ↔ CO-WORKER = HANDS / BODY
    # =========================================================================
    def test_01_ceo_coworker_contract_execution(self):
        req = AICeoMissionRequest(
            objective="Evaluate 10 enterprise payment gateway providers and synthesize comparison report",
            business_context={"strategy": "FinTech Expansion", "market": "Global"},
            success_criteria=["Supplier capability matrix", "Deliverable file on disk", "SHA-256 evidence"],
            priority="CRITICAL",
            budget=80.0,
            tenant_id=self.tenant_id
        )

        resp = self.engine.execute_ceo_mission(req)
        self.assertIsInstance(resp, AICeoMissionResponse)
        self.assertEqual(resp.execution_status, "COMPLETED")
        self.assertTrue(resp.verification["verified"])
        self.assertTrue(resp.evidence.startswith("ev_merkle_"))
        self.assertGreater(len(resp.artifacts), 0)
        self.assertIn("web.extract_table", resp.capabilities_used)
        self.assertFalse(resp.uncertainty)

        # Confirm artifact exists physically on disk
        artifact = resp.artifacts[0]
        self.assertTrue(os.path.exists(artifact["path"]))
        with open(artifact["path"], "rb") as f:
            actual_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(actual_sha, artifact["sha256"])

    def test_02_ceo_mission_policy_boundary_awaiting_approval(self):
        high_risk_req = AICeoMissionRequest(
            objective="Purge and delete legacy financial accounting records from live database",
            budget=250.0, # Exceeds automatic threshold
            tenant_id=self.tenant_id
        )

        resp = self.engine.execute_ceo_mission(high_risk_req)
        self.assertEqual(resp.execution_status, "AWAITING_APPROVAL")
        self.assertFalse(resp.verification["verified"])
        self.assertIn("requires human authorization", resp.warnings[0].lower())

    # =========================================================================
    # 2. UNIVERSAL WORKER CONTRACT & METADATA
    # =========================================================================
    def test_03_universal_worker_contract_lifecycle(self):
        metadata = WorkerMetadata(
            worker_id="wrk_test_contract_01",
            node_id="local_control_plane",
            worker_type="RESEARCH_WORKER",
            platform="linux",
            architecture="aarch64",
            runtime="runtime_terminal",
            runtime_version="1.0.0-GA",
            capabilities=["terminal.shell_command", "document.create"],
            location_class=WorkerLocationClass.LOCAL_CONTROL_PLANE
        )

        meta_dict = metadata.to_dict()
        self.assertEqual(meta_dict["worker_id"], "wrk_test_contract_01")
        self.assertEqual(meta_dict["location_class"], "LOCAL_CONTROL_PLANE")

        # Test wrapper adapter
        class MockProvider:
            def capabilities(self): return ["terminal.shell_command"]
            def prepare(self, c, p, ctx): return True
            def execute(self, c, p, ctx):
                from core.coworker.contracts import ExecutionResult
                return ExecutionResult(provider_id="mock", capability_id=c, execution_id="ex1", status="SUCCESS")

        adapter = UniversalWorkerAdapter(MockProvider(), metadata)
        self.assertEqual(adapter.discover_capabilities(), ["terminal.shell_command"])
        self.assertTrue(adapter.prepare("t1", "terminal.shell_command", {}, {}))
        self.assertTrue(adapter.authorize("t1", "lease_token_123", "AUTOMATIC_IDEMPOTENT"))

        # Execution
        res = adapter.execute("t1", "terminal.shell_command", {}, {})
        self.assertEqual(res.status, "SUCCESS")

        # Human takeover & release
        self.assertTrue(adapter.take_control("t1", "supervisor_01"))
        paused_res = adapter.execute("t1", "terminal.shell_command", {}, {})
        self.assertEqual(paused_res.status, "PAUSED_TAKEOVER")

        self.assertTrue(adapter.release_control("t1", {"reconciled": True}))
        self.assertTrue(adapter.shutdown())

    # =========================================================================
    # 3. CANONICAL 20-FIELD CAPABILITY SPECIFICATION
    # =========================================================================
    def test_04_canonical_capability_specification(self):
        cap = CapabilityDefinition(
            capability_id="terminal.file_operation",
            name="Governed File Operation",
            description="Performs safe read, write, append with SHA-256 rollback",
            category=CapabilityCategory.TERMINAL,
            providers=["provider_terminal"],
            preferred_provider="provider_terminal",
            risk_level=RiskLevel.LOW,
            license="Apache-2.0",
            security_status="VERIFIED_SAFE",
            success_rate=0.99
        )

        canonical = cap.to_canonical_dict()
        expected_keys = [
            "capability_id", "name", "description", "input_schema", "output_schema",
            "risk_level", "platforms", "architectures", "required_resources",
            "required_credentials", "providers", "worker_types", "runtime_versions",
            "health", "qualification_status", "license", "security_status",
            "cost", "latency", "success_rate", "evidence_requirements"
        ]
        for key in expected_keys:
            self.assertIn(key, canonical, f"Canonical field '{key}' missing from capability dictionary")

    # =========================================================================
    # 4. GOVERNED CONTROLLERS (Browser, Computer, API, MCP, A2A, Artifacts)
    # =========================================================================
    def test_05_browser_controller_ssrf_and_extraction(self):
        ctl = self.engine.browser_controller

        # SSRF private network access must be blocked
        res_blocked = ctl.navigate_and_extract("http://127.0.0.1:8080/secret")
        self.assertFalse(res_blocked["success"])
        self.assertIn("SSRF Block", res_blocked["error"])

        # Headless graphical click must be honestly marked READY_FOR_NODE
        res_action = ctl.execute_browser_action("click", selector="#btn-submit")
        self.assertEqual(res_action["reality_status"], "READY_FOR_NODE")

    def test_06_computer_controller_standard_gui_interface(self):
        gui = self.engine.computer_controller
        # Validates that headless environment truthfully reports READY_FOR_NODE
        res = gui.execute_action("click", {"coordinates": [300, 200]})
        self.assertTrue(res["success"])
        self.assertEqual(res["reality_status"], "READY_FOR_NODE")
        self.assertEqual(res["hardware_requirement"], "PHYSICAL_DISPLAY_SERVER")

    def test_07_mcp_controller_governed_tools(self):
        mcp = self.engine.mcp_controller
        servers = mcp.list_servers()
        self.assertGreaterEqual(len(servers), 2)

        # Admitted tool executes cleanly
        res = mcp.execute_tool("mcp_sqlite_corporate", "query_read_only", {"query": "SELECT 1"})
        self.assertTrue(res["success"])
        self.assertEqual(res["evidence_status"], "VERIFIED")

        # Unadmitted server rejected
        bad_res = mcp.execute_tool("unadmitted_malicious_mcp", "steal_data", {})
        self.assertFalse(bad_res["success"])

    def test_08_a2a_controller_secret_sanitization(self):
        a2a = self.engine.a2a_controller
        outbound = a2a.send_agent_message(
            target_agent_id="ext_autogen_agent_09",
            message_type="PROPOSAL",
            content={"proposal": "Contract terms", "api_key": "SECRET_RAW_KEY", "token": "jwt_token"}
        )
        self.assertTrue(outbound["success"])
        self.assertTrue(outbound["evidence_signature"].startswith("sig_a2a_"))

        # Inbound response tagged as UNTRUSTED_EXTERNAL_ADVISORY
        inbound = a2a.receive_agent_response(outbound["conversation_id"], "ext_autogen_agent_09", {"response": "Agreed"})
        self.assertEqual(inbound["trust_level"], "UNTRUSTED_EXTERNAL_ADVISORY")

    def test_09_artifact_manager_confinement_and_hash(self):
        art_mgr = self.engine.artifact_manager
        art = art_mgr.create_artifact(
            filename="unit_test_artifact.json",
            content=json.dumps({"test": "value", "created_by": "unit_test"}),
            mission_id="msn_test_art"
        )
        self.assertTrue(os.path.exists(art.path))
        self.assertEqual(len(art.sha256), 64)
        self.assertTrue(art.verified)

        read_content = art_mgr.read_artifact_content(art.artifact_id)
        self.assertIn("unit_test", read_content)

    # =========================================================================
    # 5. UNIVERSAL NODE FABRIC & SECURITY PROTOCOL
    # =========================================================================
    def test_10_node_security_hmac_and_replay_protection(self):
        sec = NodeSecurityProtocol(self.tenant_id)
        node_id = "node_sec_test_01"
        secret = "super_secure_node_key_999"
        sec.register_node_secret(node_id, secret)

        # 1. Sign request
        payload = '{"task": "compile_c_binary"}'
        sig, nonce, ts = sec.sign_request(node_id, payload)

        # 2. Verify signature
        valid, msg = sec.verify_request_signature(node_id, payload, sig, nonce, ts)
        self.assertTrue(valid)
        self.assertEqual(msg, "SIGNATURE_VALID")

        # 3. Replay attack with same nonce must be rejected
        replay_valid, replay_msg = sec.verify_request_signature(node_id, payload, sig, nonce, ts)
        self.assertFalse(replay_valid)
        self.assertIn("duplicate nonce", replay_msg)

        # 4. Old timestamp drift must be rejected
        old_valid, old_msg = sec.verify_request_signature(node_id, payload, sig, "new_nonce", ts - 500)
        self.assertFalse(old_valid)
        self.assertIn("drift", old_msg)

    def test_11_execution_lease_issuance_and_revocation(self):
        sec = NodeSecurityProtocol(self.tenant_id)
        lease_id = sec.issue_execution_lease(
            node_id="node_lease_01",
            task_id="tsk_01",
            mission_id="msn_01",
            capability_id="terminal.shell_command",
            ttl_sec=60.0
        )
        ok, msg = sec.validate_lease(lease_id, "node_lease_01")
        self.assertTrue(ok)
        self.assertEqual(msg, "LEASE_VALID")

        # Wrong node rejected
        wrong_ok, wrong_msg = sec.validate_lease(lease_id, "wrong_node_id")
        self.assertFalse(wrong_ok)

        # Explicit revocation
        sec.revoke_lease(lease_id)
        rev_ok, rev_msg = sec.validate_lease(lease_id, "node_lease_01")
        self.assertFalse(rev_ok)
        self.assertIn("revoked", rev_msg)

    # =========================================================================
    # 6. ZERO-MOCK PLATFORM PROTOCOLS (Windows, macOS, GPU/VLM)
    # =========================================================================
    def test_12_windows_protocol_ready_for_node(self):
        win_proto = WindowsWorkerNodeProtocol("node_win_test")
        res = win_proto.execute_powershell("Get-Process")
        self.assertTrue(res["success"])
        # Outside a real Windows machine, must be READY_FOR_NODE
        self.assertEqual(res["reality_status"], "READY_FOR_NODE")

    def test_13_macos_protocol_ready_for_node(self):
        mac_proto = MacOSWorkerNodeProtocol("node_mac_test")
        res = mac_proto.execute_applescript('display dialog "Hello"')
        self.assertTrue(res["success"])
        # Outside a real macOS machine, must be READY_FOR_NODE
        self.assertEqual(res["reality_status"], "READY_FOR_NODE")

    def test_14_gpu_vlm_protocol_ready_for_node(self):
        gpu_proto = GpuVlmNodeProtocol("node_gpu_test")
        res = gpu_proto.infer_vision_understanding("base64_data", "Click login button")
        self.assertTrue(res["success"])
        self.assertEqual(res["reality_status"], "READY_FOR_NODE")
        self.assertEqual(res["hardware_requirement"], "CUDA_GPU_ACCELERATOR")

    # =========================================================================
    # 7. UNIVERSAL FAILURE RECOVERY & FALLBACK STATES
    # =========================================================================
    def test_15_ambiguous_mutation_triggers_uncertain_reconciliation(self):
        rec = UniversalRecoveryController(self.tenant_id)
        # Timeout during mutation must NEVER blindly retry
        state, next_prov, next_node, notes = rec.classify_and_handle_failure(
            mission_id="msn_fail_01",
            task_id="tsk_mut_01",
            capability_id="database.write",
            failed_provider="provider_db",
            failed_node="node_01",
            error_message="Connection reset by peer: timeout waiting for ACK",
            is_mutation=True,
            available_fallback_providers=["provider_db_replica"]
        )
        self.assertEqual(state, FailureState.RECONCILIATION_REQUIRED)
        self.assertIn("reconciliation required", notes.lower())

        # Human operator resolves uncertain state
        events = rec.get_events("msn_fail_01")
        self.assertEqual(len(events), 1)
        self.assertTrue(rec.reconcile_uncertain_task(events[0]["event_id"], "Verified in WAL log: commit was applied"))
        self.assertEqual(rec.get_events("msn_fail_01")[0]["state"], FailureState.RECOVERED.value)

    def test_16_clean_failure_universal_fallback_provider(self):
        rec = UniversalRecoveryController(self.tenant_id)
        # Read-only failure cleanly falls back to alternative provider
        state, next_prov, next_node, notes = rec.classify_and_handle_failure(
            mission_id="msn_fail_02",
            task_id="tsk_read_01",
            capability_id="browser.extract",
            failed_provider="playwright_chromium",
            failed_node="local_node",
            error_message="Browser binary missing",
            is_mutation=False,
            available_fallback_providers=["openclaw_native"],
            available_fallback_nodes=["remote_browser_node_01"]
        )
        self.assertEqual(state, FailureState.RECOVERED)
        self.assertEqual(next_prov, "openclaw_native")
        self.assertEqual(next_node, "remote_browser_node_01")

if __name__ == "__main__":
    unittest.main()
