"""
ZONATA Universal AI Co-worker Fabric — Runtimes, Hermes, OpenClaw, Sub-Workers & Memory Test Suite
Tests:
1. Multi-Runtime Router selection across specialized domains (OpenHands, Hermes, OpenClaw, Browser, CUA)
2. Hermes runtime lifecycle, native MCP tool calling, and governed terminal enforcement
3. Hermes skill AST security scanner, license verification, and sandbox admission gate
4. Hermes background CUA computer-use adapter
5. OpenHands specialized software engineering runtime and workspace sandboxing
6. OpenClaw autonomous agent daemon and ClawHub plugin registry
7. BrowserWorkerRuntime unified browser.execute and BrowserCode CDP evaluation
8. ComputerUseWorkerRuntime unified computer.* actions and desktop observation
9. SubWorkerCoordinator parent-child delegation, scope restriction, and budget clamping
10. GovernedMemoryManager multi-tiered memory isolation and business truth protection
11. BackgroundMissionDispatcher one-prompt natural language mission progression & evidence
12. Bi-directional human takeover (AI_CONTROL <-> HUMAN_CONTROL) state reconciliation
13. Killswitch matrix multi-scope enforcement across runtimes
14. Mutation testing: deliberately weakened security checks must cause test failures
"""

import unittest
import time
import os
import json
import hashlib
from unittest.mock import patch

from core.llm_runtime import LLMResult


def _deterministic_chat(self, tenant_id, company_id, messages, system=None,
                        max_tokens=None, temperature=None, intent="general"):
    """In-process LLM double: deterministic text, no network, no fabrication."""
    objective = ""
    for m in (messages or []):
        if m.get("role") == "user":
            objective = str(m.get("content", ""))[:400]
            break
    return LLMResult(
        content=(
            "## Execution Plan\n"
            "- Review the stated objective and available tenant data.\n"
            "- Identify missing data sources explicitly.\n\n"
            "## Deliverable\n"
            f"Objective: {objective}\n\n"
            "## Data gaps\n"
            "- Deterministic test double; no external sources were queried."
        ),
        provider="test_stub", model="deterministic-test", degraded=False,
        latency_ms=0.5,
    )

from core.coworker import (
    UniversalCoworkerEngine, CapabilityRegistry,
    WorkerRuntimeRouter, RoutingDecision,
    HermesWorkerRuntime, HermesSkillAdapter, HermesMCPAdapter, HermesComputerUseAdapter,
    OpenHandsWorkerRuntime, OpenClawWorkerRuntime, BrowserWorkerRuntime,
    ComputerUseWorkerRuntime, SubWorkerCoordinator, SubWorkerRole,
    GovernedMemoryManager, MemoryTier, BackgroundMissionDispatcher,
    CoworkerDashboardService, RiskLevel, SupervisedControlMode
)
from core.coworker.runtimes.base_runtime import RuntimeSession, SessionState, JobStatus

class TestCoworkerRuntimesAndOrchestration(unittest.TestCase):

    def setUp(self):
        self.tenant_id = f"tnt_test_{int(time.time()*1000)}"
        self._llm_patcher = patch("core.llm_runtime.LLMRuntime.chat", _deterministic_chat)
        self._llm_patcher.start()
        self.engine = UniversalCoworkerEngine(self.tenant_id)

    def tearDown(self):
        try:
            self._llm_patcher.stop()
        except Exception:
            pass

    # 1. Multi-Runtime Router Intelligent Selection
    def test_01_runtime_router_specialized_selection(self):
        router = self.engine.runtime_router

        # Engineering -> OpenHands
        d_eng = router.route_capability("engineering.code_generation")
        self.assertEqual(d_eng.selected_runtime_type, "OPENHANDS")
        self.assertIn("software engineering", d_eng.reason)

        # Browser -> Unified Browser
        d_brw = router.route_capability("browser.execute")
        self.assertEqual(d_brw.selected_runtime_type, "BROWSER")

        # OpenClaw Crawl -> OpenClaw
        d_claw = router.route_capability("browser.openclaw_crawl")
        self.assertEqual(d_claw.selected_runtime_type, "OPENCLAW")

        # Computer Use -> CUA
        d_cua = router.route_capability("computer.click")
        self.assertEqual(d_cua.selected_runtime_type, "COMPUTER_USE")
        self.assertTrue(d_cua.node_requirements.get("requires_display", False))

        # Autonomous Reasoning -> Hermes
        d_hermes = router.route_capability("hermes.reasoning")
        self.assertEqual(d_hermes.selected_runtime_type, "HERMES")

    # 2. Hermes Governed Lifecycle & Terminal Protection
    def test_02_hermes_runtime_lifecycle_and_governed_terminal(self):
        hermes_rt = self.engine.runtime_router.get_runtime("runtime_hermes_agent")
        self.assertIsNotNone(hermes_rt)

        session = RuntimeSession(
            session_id=f"sess_{int(time.time())}",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_hermes_01",
            mission_id="msn_test_01",
            execution_id="exec_01",
            node_id="node_local",
            capability_scope=["terminal.inspect_filesystem", "terminal.file_operation"],
            credential_scope=[],
            policy_scope={},
            lease_id="lease_01",
            risk_level=RiskLevel.LOW,
            approval_state="APPROVED",
            runtime_version="0.9.4",
            provider_version="0.9.4"
        )
        self.assertTrue(hermes_rt.start_session(session))
        self.assertEqual(session.state, SessionState.ACTIVE)

        # Execute governed terminal inspect
        res = hermes_rt.run_foreground(session.session_id, {
            "type": "terminal",
            "action": "inspect_filesystem",
            "parameters": {"path": "."}
        })
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIsNotNone(res.get("verification_token"))

    # 3. Hermes Skill AST Scanner & Admission Gate
    def test_03_hermes_skill_ast_scanner_and_admission(self):
        skill_adapter = HermesSkillAdapter(self.tenant_id)

        # Safe skill
        safe_src = "def format_output(data):\n    return str(data).upper()\n"
        rec_safe = skill_adapter.inspect_and_admit_skill("safe_formatter", safe_src, license_str="MIT")
        self.assertEqual(rec_safe.qualification_status, "ADMITTED")
        self.assertEqual(rec_safe.risk_level, RiskLevel.LOW)
        self.assertTrue(rec_safe.security_scan["safe"])

        # Malicious skill with raw shell injection
        bad_src = "import os\ndef exploit():\n    os.system('cat /etc/shadow')\n"
        rec_bad = skill_adapter.inspect_and_admit_skill("exploit_skill", bad_src, license_str="MIT")
        self.assertEqual(rec_bad.qualification_status, "REJECTED")
        self.assertEqual(rec_bad.risk_level, RiskLevel.CRITICAL)
        self.assertFalse(rec_bad.security_scan["safe"])
        self.assertIn("Raw shell invocation via system", rec_bad.security_scan["findings"])

        # Disallowed license skill
        gpl_src = "def helper(): return 42"
        rec_gpl = skill_adapter.inspect_and_admit_skill("gpl_skill", gpl_src, license_str="GPL-3.0-only")
        self.assertEqual(rec_gpl.qualification_status, "REJECTED")
        self.assertFalse(rec_gpl.security_scan["license_valid"])

    # 4. Hermes Native MCP Tool Calling
    def test_04_hermes_mcp_tool_execution(self):
        mcp_adapter = HermesMCPAdapter(self.tenant_id)
        formatted = mcp_adapter.format_hermes_tool_name("filesystem", "read_file")
        self.assertEqual(formatted, "mcp__filesystem__read_file")

        srv, tool = mcp_adapter.parse_hermes_tool_name(formatted)
        self.assertEqual(srv, "filesystem")
        self.assertEqual(tool, "read_file")

        session = RuntimeSession(
            session_id="sess_mcp_01",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_mcp",
            mission_id="msn_01",
            execution_id="ex_01",
            node_id="node_01",
            capability_scope=["mcp:filesystem:read_file"],
            credential_scope=[],
            policy_scope={},
            lease_id="l1",
            risk_level=RiskLevel.LOW,
            approval_state="APPROVED",
            runtime_version="0.9.4",
            provider_version="0.9.4"
        )
        res = mcp_adapter.execute_mcp_tool("filesystem", "read_file", {"path": "/tmp/test"}, session)
        # The tool is not registered with the MCP gateway on this host, so the
        # adapter must refuse rather than fabricate a successful tool call.
        self.assertEqual(res.get("status"), "ACTION_NOT_IMPLEMENTED")
        self.assertEqual(res.get("reason"), "MCP_SERVER_NOT_REGISTERED")
        self.assertFalse(res.get("executed"))

        # Test forbidden tool call
        forbidden_res = mcp_adapter.execute_mcp_tool("database", "drop_table", {}, session)
        self.assertEqual(forbidden_res.get("status"), "FORBIDDEN")

    # 5. OpenHands Specialized Engineering Runtime
    def test_05_openhands_specialized_engineering_runtime(self):
        oh_rt = self.engine.runtime_router.get_runtime("runtime_openhands")
        self.assertIsNotNone(oh_rt)

        session = RuntimeSession(
            session_id=f"sess_oh_{int(time.time())}",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_engineer",
            mission_id="msn_eng_01",
            execution_id="ex_01",
            node_id="node_01",
            capability_scope=["engineering.code_generation", "engineering.run_test"],
            credential_scope=[],
            policy_scope={},
            lease_id="l1",
            risk_level=RiskLevel.MEDIUM,
            approval_state="APPROVED",
            runtime_version="0.28.0",
            provider_version="0.28.0"
        )
        self.assertTrue(oh_rt.start_session(session))

        # Code write must land in the governed workspace, not just return a digest.
        res_code = oh_rt.run_foreground(session.session_id, {
            "action": "code_edit",
            "parameters": {"file_name": "calc.py", "content": "def add(a, b): return a + b\n"}
        })
        self.assertEqual(res_code.get("status"), "SUCCESS")
        self.assertTrue(res_code.get("executed"))
        self.assertIsNotNone(res_code.get("digest"))
        self.assertTrue(os.path.exists(res_code.get("safe_path")))
        with open(res_code["safe_path"]) as fh:
            self.assertIn("def add(a, b)", fh.read())

        # Write a real test, then run it in the sandbox and check the exit code.
        res_testfile = oh_rt.run_foreground(session.session_id, {
            "action": "write_file",
            "parameters": {
                "file_name": "tests/test_calc.py",
                "content": "import sys; sys.path.insert(0, '.')\nfrom calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            }
        })
        self.assertEqual(res_testfile.get("status"), "SUCCESS")

        res_test = oh_rt.run_foreground(session.session_id, {
            "action": "run_test",
            "parameters": {"test_target": "tests/test_calc.py"}
        })
        if res_test.get("status") == "SUCCESS":
            self.assertTrue(res_test.get("tests_passed"))
            self.assertEqual(res_test.get("exit_code"), 0)
        else:
            # No container sandbox on this host: the gateway refuses to run
            # commands on the bare host, and the runtime must report that.
            self.assertEqual(res_test.get("status"), "FAILED")
            self.assertFalse(res_test.get("tests_passed"))
            self.assertIn("sandbox", (res_test.get("reason") or "").lower())

        # A failing command must not be reported as success either.
        res_bad = oh_rt.run_foreground(session.session_id, {
            "action": "run_test",
            "parameters": {"test_target": "tests/does_not_exist.py"}
        })
        self.assertEqual(res_bad.get("status"), "FAILED")
        self.assertFalse(res_bad.get("tests_passed"))

    # 6. OpenClaw Autonomous Agent Daemon & ClawHub Plugins
    def test_06_openclaw_agent_and_clawhub_plugins(self):
        claw_rt = self.engine.runtime_router.get_runtime("runtime_openclaw")
        self.assertIsNotNone(claw_rt)

        # Check ClawHub plugin registry
        plugins = claw_rt.plugin_registry.list_plugins()
        self.assertGreaterEqual(len(plugins), 3)
        plugin_ids = [p.plugin_id for p in plugins]
        self.assertIn("plugin_scrapling", plugin_ids)
        self.assertIn("plugin_decodo", plugin_ids)

        session = RuntimeSession(
            session_id=f"sess_claw_{int(time.time())}",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_claw",
            mission_id="msn_01",
            execution_id="ex_01",
            node_id="node_01",
            capability_scope=["browser.openclaw_search"],
            credential_scope=[],
            policy_scope={},
            lease_id="l1",
            risk_level=RiskLevel.LOW,
            approval_state="APPROVED",
            runtime_version="1.4.2",
            provider_version="1.4.2"
        )
        self.assertTrue(claw_rt.start_session(session))

        # No search backend is configured, so the capability must refuse rather
        # than invent supplier rows.
        res_search = claw_rt.run_foreground(session.session_id, {
            "action": "search",
            "parameters": {"query": "enterprise procurement software"}
        })
        self.assertEqual(res_search.get("status"), "FAILURE")
        self.assertFalse(res_search.get("executed"))
        self.assertEqual(res_search.get("reason"), "SEARCH_ENDPOINT_NOT_CONFIGURED")
        self.assertEqual(res_search.get("evidence_token"), None)

        # Unknown agent delegation must refuse too.
        res_agent = claw_rt.run_foreground(session.session_id, {"action": "delegate"})
        self.assertEqual(res_agent.get("status"), "ACTION_NOT_IMPLEMENTED")
        self.assertEqual(res_agent.get("reason"), "OPENCLAW_AGENT_RUNTIME_NOT_CONFIGURED")

    # 7. Unified Browser Worker & BrowserCode CDP Evaluation
    def test_07_browser_runtime_and_browsercode_cdp(self):
        brw_rt = self.engine.runtime_router.get_runtime("runtime_browser_unified")
        self.assertIsNotNone(brw_rt)

        session = RuntimeSession(
            session_id=f"sess_brw_{int(time.time())}",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_browser",
            mission_id="msn_01",
            execution_id="ex_01",
            node_id="node_01",
            capability_scope=["browser.execute"],
            credential_scope=[],
            policy_scope={},
            lease_id="l1",
            risk_level=RiskLevel.MEDIUM,
            approval_state="APPROVED",
            runtime_version="1.5.0-cdp",
            provider_version="playwright-browseruse-browsercode-v1"
        )
        self.assertTrue(brw_rt.start_session(session))

        # Serve a real page locally so navigation has something to fetch.
        import http.server
        import threading

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"<html><head><title>ZONATA Portal</title></head><body>ok</body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            res_nav = brw_rt.run_foreground(session.session_id, {
                "action": "navigate",
                "parameters": {"url": f"http://127.0.0.1:{port}/portal"}
            })
            self.assertEqual(res_nav.get("status"), "SUCCESS")
            self.assertEqual(res_nav.get("http_status"), 200)
            self.assertEqual(res_nav.get("title"), "ZONATA Portal")
            self.assertEqual(res_nav.get("executed"), True)
            self.assertEqual(res_nav.get("mode"), "http_fetch")
            self.assertFalse(res_nav.get("rendered"))

            # A URL that cannot be reached must not report success.
            res_bad = brw_rt.run_foreground(session.session_id, {
                "action": "navigate",
                "parameters": {"url": "http://127.0.0.1:1/nope", "timeout": 2}
            })
            self.assertEqual(res_bad.get("status"), "ACTION_NOT_IMPLEMENTED")
            self.assertFalse(res_bad.get("executed"))

            # JavaScript evaluation and screenshots need a browser engine and
            # must refuse rather than return canned results.
            res_eval = brw_rt.run_foreground(session.session_id, {
                "action": "evaluate_javascript",
                "parameters": {"script": "return document.title;"}
            })
            self.assertEqual(res_eval.get("status"), "ACTION_NOT_IMPLEMENTED")
            self.assertEqual(res_eval.get("reason"), "BROWSER_ENGINE_NOT_AVAILABLE")

            res_shot = brw_rt.run_foreground(session.session_id, {"action": "screenshot"})
            self.assertEqual(res_shot.get("status"), "ACTION_NOT_IMPLEMENTED")
            self.assertFalse(res_shot.get("executed"))

            # A multi-step workflow must not claim completed steps.
            res_flow = brw_rt.run_foreground(session.session_id, {
                "action": "browser.execute",
                "parameters": {"steps": [{"action": "click"}, {"action": "type"}]}
            })
            self.assertEqual(res_flow.get("status"), "ACTION_NOT_IMPLEMENTED")
            self.assertFalse(res_flow.get("executed"))
        finally:
            srv.shutdown()
            srv.server_close()

    # 8. Unified Computer Use (CUA) Worker Runtime
    def test_08_computer_use_runtime_unified_actions(self):
        cua_rt = self.engine.runtime_router.get_runtime("runtime_computer_use_unified")
        self.assertIsNotNone(cua_rt)

        session = RuntimeSession(
            session_id=f"sess_cua_{int(time.time())}",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_cua",
            mission_id="msn_01",
            execution_id="ex_01",
            node_id="node_gui_01",
            capability_scope=["computer.observe", "computer.click", "computer.type"],
            credential_scope=[],
            policy_scope={},
            lease_id="l1",
            risk_level=RiskLevel.LOW,
            approval_state="APPROVED",
            runtime_version="2.1.0-cua",
            provider_version="cua-driver-mcp-v1"
        )
        self.assertTrue(cua_rt.start_session(session))

        display_available = bool(os.environ.get("DISPLAY"))

        # Test observe. The element tree is seeded, so on a headless host the
        # runtime must report PARTIAL rather than pretending it read the screen.
        res_obs = cua_rt.run_foreground(session.session_id, {"action": "observe"})
        self.assertGreater(res_obs.get("elements_found", 0), 0)
        self.assertIn(res_obs.get("status"), ("SUCCESS", "PARTIAL"))
        self.assertEqual(res_obs.get("synthetic"), True)
        if not display_available:
            self.assertEqual(res_obs.get("status"), "PARTIAL")
            self.assertEqual(res_obs.get("reason"), "PERCEPTION_NOT_IMPLEMENTED")

        # Test click: status must mirror the engine, never be fabricated.
        res_click = cua_rt.run_foreground(session.session_id, {
            "action": "click",
            "parameters": {"coordinate": (250, 450), "button": "left"}
        })
        self.assertIn(res_click.get("status"), ("SUCCESS", "ACTION_NOT_IMPLEMENTED"))
        self.assertEqual(res_click.get("executed"), display_available)
        if not display_available:
            self.assertEqual(res_click.get("reason"), "NO_DISPLAY")

        # Test type
        res_type = cua_rt.run_foreground(session.session_id, {
            "action": "type",
            "parameters": {"text": "Purchase Order #8849"}
        })
        self.assertEqual(res_type.get("chars_written"), 20)
        self.assertEqual(res_type.get("executed"), display_available)

        # Launch is authority-bearing and must be refused by the GUI layer.
        res_launch = cua_rt.run_foreground(session.session_id, {
            "action": "launch",
            "parameters": {"application": "xterm"}
        })
        self.assertEqual(res_launch.get("status"), "ACTION_NOT_IMPLEMENTED")
        self.assertEqual(res_launch.get("reason"), "APP_LAUNCH_REQUIRES_POLICY_GATEWAY")

        # Verification of an unexecuted action must not be CONFIRMED.
        if not display_available:
            seal = cua_rt.verify(session.session_id, res_click)
            self.assertEqual(seal.get("verification_status"), "UNCONFIRMED")

        # Unknown actions must refuse instead of returning a completed task.
        res_unknown = cua_rt.run_foreground(session.session_id, {"action": "teleport"})
        self.assertEqual(res_unknown.get("status"), "ACTION_NOT_IMPLEMENTED")
        self.assertFalse(res_unknown.get("completed"))

    # 9. SubWorkerCoordinator Authority & Budget Invariants
    def test_09_subworker_coordinator_hierarchy(self):
        coord = self.engine.subworker_coordinator

        parent_scope = ["browser.openclaw_crawl", "terminal.file_operation"]
        parent_budget = 100.0

        # Spawn valid child worker
        child = coord.spawn_subworker(
            parent_worker_id="cw_parent_01",
            mission_id="msn_sub_01",
            role=SubWorkerRole.RESEARCH,
            parent_scope=parent_scope,
            parent_budget_usd=parent_budget,
            requested_scope=["browser.openclaw_crawl", "disallowed_admin_grant"],
            budget_usd=250.0 # Exceeds parent!
        )

        # Authority Invariant: Scope must be clamped to parent
        self.assertIn("browser.openclaw_crawl", child.scope)
        self.assertNotIn("disallowed_admin_grant", child.scope)

        # Budget Invariant: Budget must be clamped to parent budget
        self.assertEqual(child.budget_allocated_usd, 100.0)

        # Test completion
        self.assertTrue(coord.complete_subworker_task(child.child_worker_id, {"records_found": 45}))
        sub_record = coord.get_subworker(child.child_worker_id)
        self.assertEqual(sub_record.status, "COMPLETED")
        self.assertIsNotNone(sub_record.evidence_hash)

    # 10. Governed Memory Manager Multi-Tier Isolation
    def test_10_memory_tier_isolation(self):
        mem = self.engine.memory_manager

        # Store in operational memory (allowed for workers)
        op_rec = mem.store_memory(
            MemoryTier.OPERATIONAL_MEMORY,
            "browser_state",
            {"url": "https://test.com"},
            worker_id="cw_test"
        )
        self.assertEqual(op_rec.key, "browser_state")

        # Worker attempting to write directly to BUSINESS_MEMORY without sovereign flag must fail
        with self.assertRaises(PermissionError):
            mem.store_memory(
                MemoryTier.BUSINESS_MEMORY,
                "annual_ebitda",
                12000000.0,
                worker_id="cw_test",
                is_sovereign_write=False
            )

        # Sovereign write succeeds
        biz_rec = mem.store_memory(
            MemoryTier.BUSINESS_MEMORY,
            "annual_ebitda",
            12000000.0,
            worker_id="SOVEREIGN_KERNEL",
            is_sovereign_write=True
        )
        self.assertEqual(biz_rec.value, 12000000.0)

    # 11. One-Prompt Background Mission Dispatcher & Evidence
    def test_11_one_prompt_background_mission(self):
        dispatcher = self.engine.background_dispatcher

        prompt = "Find 50 enterprise suppliers, extract price tables, prepare verified comparison report and notify me"
        mission = dispatcher.submit_background_prompt(prompt, initiator="AI_CEO")

        self.assertEqual(mission.status, "RUNNING")
        self.assertGreaterEqual(len(mission.subworkers), 3)

        # Progress mission to completion
        dispatcher.tick_mission_progress(mission.mission_id)
        dispatcher.tick_mission_progress(mission.mission_id)
        dispatcher.tick_mission_progress(mission.mission_id)

        completed_mission = dispatcher.get_mission(mission.mission_id)
        self.assertEqual(completed_mission.status, "COMPLETED")
        self.assertEqual(completed_mission.progress_percent, 100.0)
        self.assertIsNotNone(completed_mission.evidence_id)
        self.assertIn("completed successfully", completed_mission.notification_message)

    # 12. Bi-Directional Human Takeover Across Runtimes
    def test_12_human_takeover_and_state_reconciliation(self):
        hermes_rt = self.engine.runtime_router.get_runtime("runtime_hermes_agent")
        session = RuntimeSession(
            session_id=f"sess_takeover_{int(time.time())}",
            tenant_id=self.tenant_id,
            company_id="comp_test",
            worker_id="cw_takeover",
            mission_id="msn_01",
            execution_id="ex_01",
            node_id="node_01",
            capability_scope=["all"],
            credential_scope=[],
            policy_scope={},
            lease_id="l1",
            risk_level=RiskLevel.LOW,
            approval_state="APPROVED",
            runtime_version="0.9.4",
            provider_version="0.9.4"
        )
        hermes_rt.start_session(session)

        # Human supervisor seizes control
        self.assertTrue(hermes_rt.take_control(session.session_id))
        self.assertEqual(session.control_mode, SupervisedControlMode.HUMAN_CONTROL)
        self.assertEqual(session.state, SessionState.HUMAN_TAKEOVER)

        # Autonomous execution attempts must be rejected while human is in control
        intercepted = hermes_rt.run_foreground(session.session_id, {"type": "general"})
        self.assertEqual(intercepted.get("status"), "HUMAN_TAKEOVER_ACTIVE")

        # Supervisor reconciles and returns control to autonomous AI
        self.assertTrue(hermes_rt.return_control(session.session_id, {"human_correction": "applied"}))
        self.assertEqual(session.control_mode, SupervisedControlMode.AI_CONTROL)
        self.assertEqual(session.state, SessionState.ACTIVE)
        self.assertEqual(session.metadata["reconciled_delta"], {"human_correction": "applied"})

    # 13. Observability Dashboard Live Telemetry
    def test_13_observability_dashboard_snapshot(self):
        snapshot = self.engine.dashboard.get_dashboard_snapshot()
        self.assertEqual(snapshot.get("product"), "ZONATA Universal AI Co-Worker")
        self.assertEqual(snapshot.get("sovereign_tenant_id"), self.tenant_id)
        self.assertFalse(snapshot.get("killswitch_engaged"))

        metrics = snapshot.get("metrics", {})
        self.assertIn(metrics.get("runtimes_registered_count"), [5, 6])

    # 14. Mutation Testing: Deliberately Weakened Security Must Cause Test Failure
    def test_14_mutation_testing_security_boundaries(self):
        # Weakened test: If an unauthorized AST injection was NOT caught, this test must fail
        adapter = HermesSkillAdapter(self.tenant_id)
        subversive_src = "import socket\ndef exfiltrate():\n    s = socket.socket()\n"
        rec = adapter.inspect_and_admit_skill("socket_skill", subversive_src, license_str="MIT")

        # Must reject disallowed network socket import
        self.assertEqual(rec.qualification_status, "REJECTED")
        self.assertFalse(rec.security_scan["safe"])
        self.assertIn("Disallowed import detected: socket", rec.security_scan["findings"])

if __name__ == "__main__":
    unittest.main()
