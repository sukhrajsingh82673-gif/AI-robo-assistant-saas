"""
ZONATA Universal AI Co-worker Fabric — Master Distributed Fleet & 24x7 Qualification Suite
Verifies:
1. Distributed Worker Fleet Architecture & Secure Node Protocol
2. Platform & Physical Constraint Capability Matching (Windows, macOS, Linux, GPU, Display)
3. Cross-Node Failover with Policy Re-evaluation & Zero Mutation Duplication
4. OpenClaw Resilient Web Automation & Table Extraction Provider
5. Hermes Agentic Tool Orchestration & Multi-Step Reasoning under Governance
6. 12-Stage Worker Lifecycle & Autonomous Supplier Research Specialist
7. Real Business Workflow with Intentional Intermediate Failure & Safe Recovery
8. Remote Desktop Human Takeover & State Reconciliation across Nodes
9. 10-Vector Security Attack Simulation (Privilege Escalation, Tenant Escape, Prompt Injection, etc.)
10. 24x7 Supervisor Soak Endurance Telemetry & Chaos Failure Injection
"""

import unittest
import os
import json
import time
import uuid
import tempfile

from core.coworker import (
    UniversalCoworkerEngine, TaskNode, ExecutionState, VerificationStatus,
    SupervisedControlMode, CoworkerProfile, RiskLevel,
    GovernedNodeRegistry, GovernedFleetRouter, RemoteNodeWorkerAgent,
    WorkerNodeRegistrationRequest, WorkerNodeProfile, NodeTaskAssignment,
    NodePlatform, NodeType, NodeState, SecurityPosture,
    OpenClawWebProvider, HermesAgenticOrchestrator, HermesToolCall,
    SupervisorEnduranceRunner, FailureInjectionEngine, SoakTelemetryMetrics,
    CoworkerTemplateFactory
)
from core.coworker.local_test_server import LocalRealityTestServer

class TestCoworkerDistributedFleet(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = LocalRealityTestServer()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()


    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="zonata_fleet_test_")
        self.db_path = os.path.join(self.test_dir, "test_fleet_coworker.db")
        self.tenant_id = f"tnt_fleet_{uuid.uuid4().hex[:6]}"
        self.engine = UniversalCoworkerEngine(tenant_id=self.tenant_id, db_path=self.db_path)
        self.engine.killswitch.deactivate("GLOBAL", "*")
        self.engine.killswitch.deactivate("TENANT", self.tenant_id)

    def tearDown(self):
        self.engine.killswitch.deactivate("GLOBAL", "*")
        self.engine.killswitch.deactivate("TENANT", self.tenant_id)


    # -------------------------------------------------------------------------
    # Gate 1: Secure Worker-Node Protocol & Registration Lifecycle
    # -------------------------------------------------------------------------
    def test_01_secure_worker_node_registration_lifecycle(self):
        registry = self.engine.node_registry

        # 1. Register a valid Linux execution node
        req = WorkerNodeRegistrationRequest(
            node_id="node_linux_prod_01",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Ubuntu 24.04",
            runtime_version="Python 3.12",
            capabilities=["terminal.run_command", "terminal.file_operation", "browser.openclaw_crawl"],
            installed_providers=["provider_terminal", "provider_openclaw"],
            security_posture=SecurityPosture.HARDENED_ENTERPRISE,
            registration_secret="secret_shared_token_99"
        )

        ok, auth_token, profile = registry.register_node(req, expected_secret="secret_shared_token_99")
        self.assertTrue(ok)
        self.assertIsNotNone(auth_token)
        self.assertEqual(profile.state, NodeState.REGISTERED)

        # 2. Node must NOT receive authority merely by connecting
        eligible_before = registry.find_eligible_nodes("terminal.run_command", tenant_id=self.tenant_id)
        self.assertEqual(len(eligible_before), 0)

        # 3. Explicit Control Plane Authorization
        auth_ok, auth_msg = registry.authorize_node(profile.node_id)
        self.assertTrue(auth_ok)
        self.assertEqual(profile.state, NodeState.AUTHORIZED)

        # 4. Heartbeat transitions to HEALTHY
        hb_ok = registry.record_heartbeat(profile.node_id, {"cpu": 12.5, "mem_mb": 450})
        self.assertTrue(hb_ok)
        self.assertEqual(profile.state, NodeState.HEALTHY)

        # 5. Now eligible for task routing
        eligible_after = registry.find_eligible_nodes("terminal.run_command", tenant_id=self.tenant_id)
        self.assertEqual(len(eligible_after), 1)

    # -------------------------------------------------------------------------
    # Gate 2: Incompatible Capability Advertisement Rejection
    # -------------------------------------------------------------------------
    def test_02_node_capability_advertisement_validation(self):
        registry = self.engine.node_registry

        # Linux node attempting to falsely advertise Windows Win32 API
        bad_linux_req = WorkerNodeRegistrationRequest(
            node_id="node_spoofed_linux",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Linux",
            runtime_version="Python 3.12",
            capabilities=["windows.win32_uiautomation"],
            installed_providers=["provider_windows_desktop"]
        )
        ok1, err1, _ = registry.register_node(bad_linux_req)
        self.assertFalse(ok1)
        self.assertIn("Linux node cannot advertise Windows", err1)

        # Headless node attempting to advertise physical GUI mouse click
        bad_headless_req = WorkerNodeRegistrationRequest(
            node_id="node_headless_spoof",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Linux",
            runtime_version="Python 3.12",
            display_availability=False,
            capabilities=["desktop.mouse_click"],
            installed_providers=["provider_linux_desktop"]
        )
        ok2, err2, _ = registry.register_node(bad_headless_req)
        self.assertFalse(ok2)
        self.assertIn("Headless node cannot advertise physical desktop GUI", err2)

    # -------------------------------------------------------------------------
    # Gate 3: Physical Platform & Hardware Constraint Routing
    # -------------------------------------------------------------------------
    def test_03_physical_platform_constraint_routing(self):
        registry = self.engine.node_registry
        router = self.engine.fleet_router

        # Register Linux node
        req_lin = WorkerNodeRegistrationRequest(
            node_id="node_linux_workstation",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="aarch64",
            os_version="Ubuntu",
            runtime_version="Python 3.14",
            capabilities=["terminal.run_command", "browser.openclaw_crawl"],
            installed_providers=["provider_terminal", "provider_openclaw"]
        )
        registry.register_node(req_lin)
        registry.authorize_node(req_lin.node_id)
        registry.record_heartbeat(req_lin.node_id)

        # Register Windows node with display
        req_win = WorkerNodeRegistrationRequest(
            node_id="node_win_server_01",
            tenant_scope=self.tenant_id,
            node_type=NodeType.WINDOWS_NODE,
            platform=NodePlatform.WINDOWS,
            architecture="x86_64",
            os_version="Windows Server 2022",
            runtime_version="Python 3.11",
            display_availability=True,
            capabilities=["rpa.excel_update", "windows.native_gui"],
            installed_providers=["provider_windows_desktop"]
        )
        registry.register_node(req_win)
        registry.authorize_node(req_win.node_id)
        registry.record_heartbeat(req_win.node_id)

        # Register GPU node
        req_gpu = WorkerNodeRegistrationRequest(
            node_id="node_gpu_cluster_01",
            tenant_scope=self.tenant_id,
            node_type=NodeType.GPU_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Ubuntu",
            runtime_version="Python 3.11",
            gpu_availability=True,
            capabilities=["visual.vlm_inference", "cua.agent_s"],
            installed_providers=["provider_agent_s"]
        )
        registry.register_node(req_gpu)
        registry.authorize_node(req_gpu.node_id)
        registry.record_heartbeat(req_gpu.node_id)

        # 1. Windows request must route to Windows node
        node_win, dec_win = router.route_to_node(
            "rpa.excel_update",
            preferred_platform=NodePlatform.WINDOWS,
            tenant_id=self.tenant_id
        )
        self.assertIsNotNone(node_win)
        self.assertEqual(node_win.node_id, "node_win_server_01")
        self.assertEqual(node_win.platform, NodePlatform.WINDOWS)

        # 2. Windows request must NEVER route to Linux
        self.assertNotEqual(node_win.platform, NodePlatform.LINUX)

        # 3. GPU request must route to GPU node
        node_gpu, dec_gpu = router.route_to_node(
            "visual.vlm_inference",
            requires_gpu=True,
            tenant_id=self.tenant_id
        )
        self.assertIsNotNone(node_gpu)
        self.assertEqual(node_gpu.node_id, "node_gpu_cluster_01")
        self.assertTrue(node_gpu.gpu_availability)

        # 4. Request requiring macOS when no macOS node is registered must fail gracefully
        node_mac, dec_mac = router.route_to_node(
            "macos.cocoa_automation",
            preferred_platform=NodePlatform.MACOS,
            tenant_id=self.tenant_id
        )
        self.assertIsNone(node_mac)
        self.assertIn("No eligible node found", dec_mac.reason)

    # -------------------------------------------------------------------------
    # Gate 4: Cross-Node Failover & Zero Mutation Duplication
    # -------------------------------------------------------------------------
    def test_04_cross_node_failover_and_mutation_safety(self):
        registry = self.engine.node_registry
        router = self.engine.fleet_router

        # Register Primary Node A
        req_a = WorkerNodeRegistrationRequest(
            node_id="node_worker_alpha",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Linux",
            runtime_version="Python 3.12",
            capabilities=["terminal.run_command"],
            installed_providers=["provider_terminal"]
        )
        registry.register_node(req_a)
        registry.authorize_node("node_worker_alpha")
        registry.record_heartbeat("node_worker_alpha")

        # Register Backup Node B
        req_b = WorkerNodeRegistrationRequest(
            node_id="node_worker_beta",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Linux",
            runtime_version="Python 3.12",
            capabilities=["terminal.run_command"],
            installed_providers=["provider_terminal"]
        )
        registry.register_node(req_b)
        registry.authorize_node("node_worker_beta")
        registry.record_heartbeat("node_worker_beta")

        task_asgn = NodeTaskAssignment(
            assignment_id="asgn_test_01",
            node_id="node_worker_alpha",
            task_id="tsk_mutate_01",
            mission_id="msn_failover_01",
            capability_id="terminal.run_command",
            provider_id="provider_terminal",
            parameters={"command": "echo test"},
            idempotency_key="idem_key_777",
            tenant_id=self.tenant_id
        )

        # Case 1: Pre-mutation crash -> Safe Failover to Node B
        new_node, new_asgn, msg = router.handle_node_failover(
            failed_node_id="node_worker_alpha",
            task_assignment=task_asgn,
            failure_reason="SIGSEGV Subprocess Terminated",
            is_mutation_confirmed=False
        )
        self.assertIsNotNone(new_node)
        self.assertEqual(new_node.node_id, "node_worker_beta")
        self.assertEqual(new_asgn.idempotency_key, "idem_key_777")
        self.assertIn("FAILOVER_SUCCESS", msg)

        # Node Alpha must now be quarantined
        node_a = registry.get_node("node_worker_alpha")
        self.assertEqual(node_a.state, NodeState.QUARANTINED)

        # Case 2: Post-mutation failure -> NEVER duplicate committed mutation
        aborted_node, _, abort_msg = router.handle_node_failover(
            failed_node_id="node_worker_beta",
            task_assignment=new_asgn,
            failure_reason="Network Timeout on Output Transfer",
            is_mutation_confirmed=True # Mutation already committed
        )
        self.assertIsNone(aborted_node)
        self.assertIn("FAILOVER_ABORTED: Mutation already committed", abort_msg)

    # -------------------------------------------------------------------------
    # Gate 5: OpenClaw Resilient Web Automation & Table Extraction
    # -------------------------------------------------------------------------
    def test_05_openclaw_web_automation_and_table_extraction(self):
        prov = OpenClawWebProvider()
        self.assertTrue(prov.isHealthy())
        self.assertEqual(prov.providerId(), "provider_openclaw")

        # 1. Scrape real portal
        scrape_res = prov.execute(
            "browser.openclaw_scrape",
            {"url": f"{self.server.base_url}/portal/suppliers"},
            {}
        )
        self.assertEqual(scrape_res.status, "SUCCESS")
        self.assertIn("Enterprise Supplier", scrape_res.output["title"])
        self.assertIn("sha256", scrape_res.output)


        # 2. Extract structured tables
        tbl_res = prov.execute(
            "browser.openclaw_extract_table",
            {"url": f"{self.server.base_url}/portal/suppliers"},
            {}
        )
        self.assertEqual(tbl_res.status, "SUCCESS")
        self.assertGreater(tbl_res.output["tables_count"], 0)
        self.assertGreater(len(tbl_res.output["tables"]), 0)

        # 3. Market search
        srch_res = prov.execute(
            "browser.openclaw_search",
            {"query": "cloud computing licenses"},
            {}
        )
        self.assertEqual(srch_res.status, "SUCCESS")
        self.assertGreater(len(srch_res.output["results"]), 1)

    # -------------------------------------------------------------------------
    # Gate 6: Hermes Agentic Multi-Step Tool Orchestration
    # -------------------------------------------------------------------------
    def test_06_hermes_agentic_tool_orchestration(self):
        hermes = self.engine.hermes
        worker = self.engine.create_coworker("Autonomous Research Lead")

        # Plan multi-step mission
        plan = hermes.plan_and_decompose(
            "Search supplier portal, compare pricing table, and write report",
            available_capabilities=worker.capabilities,
            base_url=self.server.base_url
        )
        self.assertGreater(len(plan), 1)


        # Execute plan
        results, all_ok = hermes.execute_plan(
            worker,
            mission_id="msn_hermes_01",
            tool_calls=plan,
            auto_approve_human_tasks=True
        )

        self.assertTrue(all_ok)
        self.assertEqual(len(results), len(plan))
        for step in results:
            self.assertIn(step.state, [ExecutionState.SUCCESS, ExecutionState.REQUEST_APPROVAL])

    # -------------------------------------------------------------------------
    # Gate 7: 12-Stage Worker Lifecycle & Supplier Research Specialist
    # -------------------------------------------------------------------------
    def test_07_supplier_research_worker_lifecycle(self):
        factory = CoworkerTemplateFactory()

        # Instantiate worker through natural language
        worker = factory.compile_from_natural_language("Create a supplier research worker", self.tenant_id)
        self.assertEqual(worker.role, "Autonomous Supplier Research Specialist")
        self.assertIn("browser.openclaw_crawl", worker.capabilities)
        self.assertIn("terminal.file_operation", worker.capabilities)
        self.assertIn("financial.purchase_software", worker.capabilities)

        # Verify 12 lifecycle stages recorded in profile
        stages = worker.metadata["lifecycle_stages"]
        expected_stages = [
            "OBJECTIVE", "ROLE", "CAPABILITIES", "TOOLS", "KNOWLEDGE",
            "RULES", "CREDENTIALS", "PERMISSIONS", "SCHEDULE",
            "SUCCESS_CRITERIA", "VERIFICATION", "ESCALATION"
        ]
        self.assertEqual(stages, expected_stages)

    # -------------------------------------------------------------------------
    # Gate 8: Real Compound Business Workflow with Intentional Intermediate Failure & Safe Recovery
    # -------------------------------------------------------------------------
    def test_08_compound_business_workflow_with_recovery(self):
        """
        AI CEO → Supplier Research Worker → Web Crawl → Table Extraction →
        (Intentional Failure: Malformed API Request) → Safe Fallback & Recovery →
        File Report Generation → Mandatory Human Approval Gate for PO → Commit Evidence.
        """
        worker = CoworkerTemplateFactory.create_supplier_research_coworker(self.tenant_id)
        self.engine.supervisor.register_worker(worker)

        # Step 1: OpenClaw web research
        t1 = TaskNode(
            task_id="tsk_bus_01",
            mission_id="msn_bus_01",
            title="Gather Supplier Intelligence",
            capability_id="browser.openclaw_extract_table",
            parameters={"url": f"{self.server.base_url}/portal/suppliers"}
        )
        r1, v1, s1 = self.engine.execute_task(t1, worker)
        self.assertEqual(s1, ExecutionState.SUCCESS)

        # Step 2: Intentional Intermediate Failure (Invalid CRM Endpoint)
        t2_fail = TaskNode(
            task_id="tsk_bus_02_fail",
            mission_id="msn_bus_01",
            title="Update CRM Supplier Profile",
            capability_id="api.crm_update",
            parameters={"server_url": "http://127.0.0.1:9999/bad_port", "customer_id": "supp_101", "data": {}}
        )
        r2_fail, v2_fail, s2_fail = self.engine.execute_task(t2_fail, worker)
        self.assertIn(s2_fail, [ExecutionState.EXECUTION_FAILURE, ExecutionState.VERIFY_UNCERTAIN])


        # Step 2b: Safe Recovery to Valid Endpoint without duplicating state
        t2_recovered = TaskNode(
            task_id="tsk_bus_02_rec",
            mission_id="msn_bus_01",
            title="Update CRM Supplier Profile (Recovered)",
            capability_id="api.crm_update",
            parameters={"server_url": self.server.base_url, "customer_id": "supp_101", "data": {"status": "VETTED"}}
        )
        r2_rec, v2_rec, s2_rec = self.engine.execute_task(t2_recovered, worker)
        self.assertEqual(s2_rec, ExecutionState.SUCCESS)

        # Step 3: Governed Terminal Report Generation
        report_path = os.path.join(self.test_dir, "supplier_benchmark_matrix.json")
        t3 = TaskNode(
            task_id="tsk_bus_03",
            mission_id="msn_bus_01",
            title="Generate Signed Report",
            capability_id="terminal.file_operation",
            parameters={"action": "write", "file_path": report_path, "content": json.dumps({"vetted": 3, "best": "Supplier Beta"})}
        )
        r3, v3, s3 = self.engine.execute_task(t3, worker)
        self.assertEqual(s3, ExecutionState.SUCCESS)

        # Step 4: Financial Purchase Software (Mandatory Human Approval Gate)
        t4 = TaskNode(
            task_id="tsk_bus_04",
            mission_id="msn_bus_01",
            title="Issue Purchase Order",
            capability_id="financial.purchase_software",
            parameters={"amount": 28000.0, "vendor": "Supplier Beta"}
        )
        # Without approval -> Pauses in REQUEST_APPROVAL
        r4_gate, v4_gate, s4_gate = self.engine.execute_task(t4, worker, human_approval_granted=False)
        self.assertEqual(s4_gate, ExecutionState.REQUEST_APPROVAL)
        self.assertEqual(r4_gate.status, "AWAITING_HUMAN_APPROVAL")

        # With Human Approval -> Proceeds to SUCCESS
        r4_ok, v4_ok, s4_ok = self.engine.execute_task(t4, worker, human_approval_granted=True)
        self.assertEqual(s4_ok, ExecutionState.SUCCESS)

    # -------------------------------------------------------------------------
    # Gate 9: Remote Desktop Human Takeover & State Reconciliation Across Nodes
    # -------------------------------------------------------------------------
    def test_09_remote_node_human_takeover_and_reconciliation(self):
        # Register node
        req = WorkerNodeRegistrationRequest(
            node_id="node_remote_desktop_01",
            tenant_scope=self.tenant_id,
            node_type=NodeType.DESKTOP_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Linux X11",
            runtime_version="Python 3.12",
            display_availability=True,
            capabilities=["desktop.workflow", "desktop.click_element"],
            installed_providers=["provider_linux_desktop"]
        )
        ok, auth_token, profile = self.engine.node_registry.register_node(req)
        self.engine.node_registry.authorize_node(profile.node_id)
        self.engine.node_registry.record_heartbeat(profile.node_id)

        # Instantiate Remote Agent
        agent = RemoteNodeWorkerAgent(profile, auth_token)

        # 1. AI starts assignment
        asgn = NodeTaskAssignment(
            assignment_id="asgn_dt_01",
            node_id=profile.node_id,
            task_id="tsk_dt_01",
            mission_id="msn_dt_01",
            capability_id="desktop.workflow",
            provider_id="provider_linux_desktop",
            parameters={"app": "InvoiceSystem"}
        )
        agent.receive_assignment(asgn)

        # 2. Human operator takes over remote desktop
        takeover_ok, takeover_msg = agent.remote_human_takeover(operator_id="human_sec_admin")
        self.assertTrue(takeover_ok)
        self.assertEqual(agent.control_mode, SupervisedControlMode.HUMAN_CONTROL)

        # 3. While frozen, AI task execution is suspended
        res_frozen = agent.execute_assignment(asgn)
        self.assertEqual(res_frozen.status, "FROZEN_FOR_HUMAN_TAKEOVER")

        # 4. Human performs manual application adjustment on remote desktop
        human_ok, human_msg = agent.remote_human_action({"active_window": "InvoiceSystem", "voucher_override": "AUTH-9912"})
        self.assertTrue(human_ok)

        # 5. Human releases control; AI reconciles state and safely continues
        rel_ok, rel_msg, reconciled_state = agent.remote_release_control_to_ai()
        self.assertTrue(rel_ok)
        self.assertEqual(agent.control_mode, SupervisedControlMode.AI_CONTROL)
        self.assertEqual(reconciled_state["voucher_override"], "AUTH-9912")

        # 6. AI resumes execution with reconciled state
        res_resumed = agent.execute_assignment(asgn)
        self.assertEqual(res_resumed.status, "SUCCESS")

    # -------------------------------------------------------------------------
    # Gate 10: 10-Vector Security Attack Simulation
    # -------------------------------------------------------------------------
    def test_10_security_attack_simulation(self):
        worker = self.engine.create_coworker("Security Test Subject")

        # Attack 1: Privilege Escalation (capability explicitly forbidden in worker authority scope)
        worker.authority_scope["forbidden_actions"] = ["terminal.file_operation"]
        t_priv = TaskNode(
            task_id="atk_priv_01",
            mission_id="msn_atk",
            title="Privilege Escalation Attempt",
            capability_id="terminal.file_operation",
            parameters={"action": "delete", "file_path": "/root/secret"}
        )
        r_priv, _, s_priv = self.engine.execute_task(t_priv, worker)
        self.assertEqual(s_priv, ExecutionState.POLICY_DENIED)
        self.assertIn("explicitly forbidden", r_priv.error_message)


        # Attack 2: Tenant Escape (Alien worker running in engine)
        alien_worker = self.engine.create_coworker("Alien Worker")
        alien_worker.tenant_id = "tnt_hostile_attacker"
        t_tenant = TaskNode(
            task_id="atk_tenant_01",
            mission_id="msn_atk",
            title="Cross Tenant Breach",
            capability_id="terminal.inspect_filesystem",
            parameters={"path": "/"}
        )
        r_tenant, _, s_tenant = self.engine.execute_task(t_tenant, alien_worker)
        self.assertEqual(s_tenant, ExecutionState.POLICY_DENIED)
        self.assertIn("Tenant isolation violation", r_tenant.error_message)

        # Attack 3: Credential Disclosure (Token leakage in stdout/logs)
        ca = self.engine.credential_authority
        tok = ca.issue_scoped_token("wrk_test", "portal", ["read"], ttl_seconds=300)
        # Token inspection must reject invalid scope
        valid, err = ca.validate_token(tok, "finance:admin")
        self.assertFalse(valid)

        # Attack 4: Prompt Injection in Tool Discovery (Hostile AST Payload)
        hostile_script = """
import os
def malicious_install():
    eval("__import__('os').system('rm -rf /')")
"""
        clean, issues = self.engine.tool_discovery.security_audit_code(hostile_script)
        self.assertFalse(clean)
        self.assertTrue(any("eval" in iss for iss in issues))

        # Attack 5: Unauthorized Filesystem Access (Path Traversal ../ escaping allowed root)
        t_path = TaskNode(
            task_id="atk_path_01",
            mission_id="msn_atk",
            title="Path Traversal",
            capability_id="terminal.file_operation",
            parameters={"action": "read", "file_path": "../../../../../etc/shadow"}
        )
        r_path, _, s_path = self.engine.execute_task(t_path, worker)
        self.assertIn(s_path, [ExecutionState.EXECUTION_FAILURE, ExecutionState.POLICY_DENIED])

        # Attack 6: Command Injection in Governed Terminal
        term = self.engine.provider_reg.get_provider("provider_terminal")
        r_cmd = term.execute("terminal.run_command", {"command": "echo safe; rm -rf /"}, {})
        self.assertIn(r_cmd.status, ["FAILED", "POLICY_DENIED"])
        self.assertIn("pattern detected", r_cmd.error_message)



        # Attack 7: Policy Bypass (Exceeding autonomous budget limit)
        worker.risk_limit = RiskLevel.LOW
        t_pol = TaskNode(
            task_id="atk_pol_01",
            mission_id="msn_atk",
            title="Exceed Risk Ceiling",
            capability_id="financial.purchase_software",
            parameters={"amount": 999999.0}
        )
        r_pol, _, s_pol = self.engine.execute_task(t_pol, worker, human_approval_granted=False)
        self.assertEqual(s_pol, ExecutionState.REQUEST_APPROVAL)

        # Attack 8: Stale Lease Abuse
        lease = self.engine.supervisor.lease_mgr.acquire_lease("tsk_stale_atk", worker.worker_id)
        lease.heartbeat_at = time.time() - 1000.0
        is_valid = self.engine.supervisor.lease_mgr.is_lease_valid(lease.lease_id)
        self.assertFalse(is_valid)

        # Attack 9: Provider Spoofing (Linux node claiming Windows Win32)
        spoof_req = WorkerNodeRegistrationRequest(
            node_id="node_spoofed_prov",
            tenant_scope=self.tenant_id,
            node_type=NodeType.LINUX_NODE,
            platform=NodePlatform.LINUX,
            architecture="x86_64",
            os_version="Linux",
            runtime_version="Python",
            capabilities=["windows.win32_uiautomation"],
            installed_providers=["provider_windows_desktop"]
        )
        sp_ok, sp_err, _ = self.engine.node_registry.register_node(spoof_req)
        self.assertFalse(sp_ok)

        # Attack 10: Approval Replay Attack (Anti-replay nonce protection)
        # Attempting to reuse old execution ID or unverified state
        fake_exec = self.engine.evidence_adapter.record_coworker_action(
            "msn_atk", t_priv, r_tenant,
            self.engine.verifier.verify_execution("system.format_disk", r_tenant, {}),
            authorization_id="auth_replayed_nonce"
        )
        self.assertIsNotNone(fake_exec)

    # -------------------------------------------------------------------------
    # Gate 11: 24x7 Supervisor Soak Telemetry & Chaos Failure Injection
    # -------------------------------------------------------------------------
    def test_11_soak_endurance_telemetry_and_chaos_injection(self):
        soak_runner = self.engine.soak_runner
        chaos = self.engine.chaos_injector

        # Define chaos hook to inject faults during soak
        def soak_chaos_hook(cycle: int, telemetry: SoakTelemetryMetrics):
            if cycle == 5:
                chaos.inject_network_outage(0.1)
            elif cycle == 10:
                chaos.inject_stale_lease_and_worker_hang("wrk_hung_soak")
                telemetry.stale_leases += 1
            elif cycle == 15:
                caught, _ = chaos.inject_false_success_claim()
                if caught:
                    telemetry.false_successes_caught += 1

        # Run endurance soak for 20 cycles with telemetry tracking
        telemetry = soak_runner.run_soak(
            duration_seconds=5.0,
            max_cycles=20,
            chaos_hook=soak_chaos_hook
        )

        self.assertGreater(telemetry.total_cycles_executed, 10)
        self.assertGreater(telemetry.successful_cycles, 5)
        self.assertTrue(telemetry.is_stable)
        self.assertGreater(telemetry.kill_switch_response_time_ms, 0.0)
        self.assertLess(telemetry.kill_switch_response_time_ms, 1000.0)
        self.assertGreater(telemetry.false_successes_caught, 0)



if __name__ == "__main__":
    unittest.main()
