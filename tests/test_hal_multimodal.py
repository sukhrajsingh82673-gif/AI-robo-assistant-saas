"""
Unit and End-to-End Tests for ZONATA HAL Multimodal Capability Integration.
Covers Sections 49 and 50 of the Project 03 Specification:
- Provider Tests (1-5)
- Vision Tests (6-9)
- Voice Tests (10-15)
- Security Tests (16-24)
- Memory Tests (25-29)
- Workforce Tests (30-33)
- Execution & Host Control Tests (34-40)
- End-to-End Scenarios (TEST A through TEST J)
"""

import unittest
import os
import json
import time

from core.db import db
from core.multimodal_capability_runtime import (
    MultimodalCapabilityRegistry,
    multimodal_registry,
    screen_observer,
    hal_vision,
    hal_hearing,
    hal_voice,
    governed_shell,
    governed_files,
    governed_artifacts,
    governed_mcp,
    execution_manager,
    RedactionEngine,
    MemoryFirewall,
    CapabilityFamily,
    ExecutionState,
    RiskLevel,
    EpistemicType
)
from zonata.hal_multimodal_adapter import hal_multimodal_adapter
from core.stateful_agent_runtime import stateful_memory_gateway, MemoryScope, MemoryType


class TestHALMultimodalIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db._init_db()

    # =========================================================================
    # 1. Provider Tests (1-5)
    # =========================================================================

    def test_01_hal_provider_loads(self):
        """1. Verify HAL provider components load properly."""
        self.assertIsNotNone(hal_vision)
        self.assertIsNotNone(hal_hearing)
        self.assertIsNotNone(hal_voice)
        self.assertIsNotNone(hal_multimodal_adapter)

    def test_02_capability_registry_registration(self):
        """2. Verify capability registry registers all families."""
        caps = multimodal_registry.list_capabilities()
        self.assertGreaterEqual(len(caps), 12)
        families = {c["family"] for c in caps}
        self.assertIn(CapabilityFamily.VISION, families)
        self.assertIn(CapabilityFamily.SCREEN_OBSERVATION, families)
        self.assertIn(CapabilityFamily.SPEECH_TO_TEXT, families)
        self.assertIn(CapabilityFamily.TEXT_TO_SPEECH, families)
        self.assertIn(CapabilityFamily.LOCAL_COMMAND, families)
        self.assertIn(CapabilityFamily.FILE_ACCESS, families)
        self.assertIn(CapabilityFamily.MCP, families)

    def test_03_provider_health_probe(self):
        """3. Verify real environment telemetry probe without fake metrics."""
        env = multimodal_registry._probe_environment()
        self.assertIn("has_camera", env)
        self.assertIn("has_mic", env)
        self.assertIn("has_git", env)
        self.assertIsInstance(env["has_camera"], bool)

    def test_04_version_detection(self):
        """4. Verify HAL version detection."""
        cap = multimodal_registry.get_capability("hal.vision.screen")
        self.assertIsNotNone(cap)
        self.assertEqual(cap["version"], "1.5.0")
        self.assertEqual(cap["provider"], "HAL9000")

    def test_05_platform_detection(self):
        """5. Verify platform detection."""
        cap = multimodal_registry.get_capability("hal.shell.exec")
        self.assertIsNotNone(cap)
        self.assertIn("POSIX", cap["platform"])

    # =========================================================================
    # 2. Vision Tests (6-9)
    # =========================================================================

    def test_06_screenshot_capture(self):
        """6. Verify screenshot observation capture."""
        session = execution_manager.create_session("hal.vision.screen")
        obs = screen_observer.capture_observation(session["session_id"], window_title="Test Workspace")
        self.assertIsNotNone(obs["observation_id"])
        self.assertTrue(obs["raw_hash"])
        self.assertFalse(obs["is_business_success"])  # Invariant: Screenshot != Business Success

    def test_07_vision_observation_face_tracking(self):
        """7. Verify vision observation and face tracking calculations."""
        frame = hal_vision.capture_frame(blur_background=True)
        self.assertEqual(frame["status"], "CAPTURED")
        self.assertGreaterEqual(frame["faces_detected"], 1)
        self.assertTrue(frame["blur_applied"])

    def test_08_redaction_engine(self):
        """8. Verify secret and PII redaction on visual observation."""
        sensitive_text = "Contact john.doe@enterprise.com with token Bearer sk-secret12345678901234567890 and card 4111-2222-3333-4444"
        redacted = RedactionEngine.redact(sensitive_text)
        self.assertNotIn("john.doe@enterprise.com", redacted)
        self.assertNotIn("4111-2222-3333-4444", redacted)
        self.assertNotIn("sk-secret", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_CARD]", redacted)

    def test_09_observation_epistemic_classification(self):
        """9. Verify observation is classified as OBSERVATION and not FACT."""
        res = hal_multimodal_adapter.observe_screen(window_title="Financial Report")
        self.assertEqual(res["epistemic_classification"], EpistemicType.OBSERVATION)

    # =========================================================================
    # 3. Voice Tests (10-15)
    # =========================================================================

    def test_10_microphone_permission_and_telemetry(self):
        """10. Verify microphone telemetry is accurately reported."""
        cap = multimodal_registry.get_capability("hal.audio.microphone")
        self.assertIsNotNone(cap)
        self.assertIn(cap["health_status"], ("HEALTHY", "DEGRADED"))

    def test_11_stt_transcription(self):
        """11. Verify STT processing."""
        res = hal_hearing.process_audio_transcript("Generate a financial summary for Q3")
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["filtered"], "Generate a financial summary for Q3")

    def test_12_stt_hallucination_filtering(self):
        """12. Verify Whisper hallucination phrases are filtered out."""
        res = hal_hearing.process_audio_transcript("thank you for watching")
        self.assertFalse(res["is_valid"])
        self.assertIsNone(res["filtered"])

    def test_13_tts_synthesis(self):
        """13. Verify text-to-speech synthesis."""
        res = hal_voice.synthesize("Welcome to ZONATA enterprise operating core.")
        self.assertTrue(res["success"])
        self.assertTrue(res["audio_id"])
        self.assertTrue(res["audio_hash"])

    def test_14_voice_interrupt(self):
        """14. Verify voice interrupt / emergency stop signal."""
        session = execution_manager.create_session("hal.tts.voice")
        res = execution_manager.trigger_killswitch(session["session_id"], reason="Host voice stop")
        self.assertTrue(res["killswitch_active"])
        self.assertEqual(res["state"], ExecutionState.CANCELLED)

    def test_15_voice_mute_and_stop(self):
        """15. Verify voice stop request."""
        hal_voice.request_stop()
        self.assertFalse(hal_voice.is_speaking())

    # =========================================================================
    # 4. Security Tests (16-24)
    # =========================================================================

    def test_16_secret_protection_file_read(self):
        """16. Verify secret file reading (.env, private keys) is blocked."""
        res = governed_files.read_file(".env")
        self.assertFalse(res["success"])
        self.assertIn("Policy Violation", res["error"])

    def test_17_tenant_isolation(self):
        """17. Verify tenant isolation in capability registry."""
        with db.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tenants (tenant_id, name, created_at) VALUES ('tnt_foreign', 'Foreign Tenant', ?)", (time.time(),))
            conn.commit()
        reg_other = MultimodalCapabilityRegistry(tenant_id="tnt_foreign")
        caps = reg_other.list_capabilities()
        for c in caps:
            self.assertEqual(c["tenant_id"], "tnt_foreign")

    def test_18_company_isolation(self):
        """18. Verify company isolation in artifact management."""
        art1 = governed_artifacts.create_artifact("Doc 1", "Content 1", company_id="comp_alpha")
        art2 = governed_artifacts.create_artifact("Doc 2", "Content 2", company_id="comp_beta")
        alpha_list = governed_artifacts.list_artifacts(company_id="comp_alpha")
        self.assertTrue(any(a["artifact_id"] == art1["artifact_id"] for a in alpha_list))
        self.assertFalse(any(a["artifact_id"] == art2["artifact_id"] for a in alpha_list))

    def test_19_permission_enforcement(self):
        """19. Verify high-risk capability requires approval."""
        cap = multimodal_registry.get_capability("hal.shell.exec")
        self.assertTrue(cap["requires_approval"])
        self.assertEqual(cap["risk_level"], RiskLevel.DANGEROUS)

    def test_20_approval_enforcement(self):
        """20. Verify unapproved dangerous action transitions to WAITING_FOR_APPROVAL or BLOCKED."""
        res = hal_multimodal_adapter.execute_controlled_action("unauthorized_custom_binary --run")
        self.assertTrue(res["blocked"])
        self.assertEqual(res["state"], ExecutionState.WAITING_FOR_APPROVAL)

    def test_21_killswitch_enforcement(self):
        """21. Verify KillSwitch blocks further execution transitions."""
        session = execution_manager.create_session("hal.app.control")
        execution_manager.trigger_killswitch(session["session_id"], reason="Test KillSwitch")
        with self.assertRaises(RuntimeError):
            execution_manager.transition_state(session["session_id"], ExecutionState.EXECUTING)

    def test_22_shell_restriction_blocked_commands(self):
        """22. Verify dangerous shell commands are blocked."""
        res = governed_shell.execute_command("sudo rm -rf /etc/shadow")
        self.assertFalse(res["success"])
        self.assertTrue(res["blocked"])
        self.assertIn("PolicyEngine Violation", res["error"])

    def test_23_filesystem_restriction_sandbox(self):
        """23. Verify writing outside sandbox directory is blocked."""
        res = governed_files.write_file("/etc/cron.d/malicious", "malicious payload")
        self.assertFalse(res["success"])
        self.assertIn("Policy Violation", res["error"])

    def test_24_mcp_authorization(self):
        """24. Verify MCP calls cannot execute blocked privileged commands."""
        res = governed_mcp.handle_mcp_tool_call(
            client_id="claude_code",
            tool_name="run_shell",
            parameters={"command": "sudo shutdown -h now"}
        )
        self.assertEqual(res["policy_evaluation"], "BLOCKED")
        self.assertEqual(res["execution_status"], "BLOCKED")

    # =========================================================================
    # 5. Memory Tests (25-29)
    # =========================================================================

    def test_25_letta_integration(self):
        """25. Verify sanitized memory reaches Letta stateful memory gateway."""
        res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(
            "Executive requested margin decomposition report",
            candidate_type="OBSERVATION"
        )
        self.assertTrue(res["persisted"])
        self.assertTrue(res["memory_id"])

    def test_26_memory_classification(self):
        """26. Verify epistemic classification prevents promotion of inference to FACT."""
        res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(
            "Customer may be considering competitor product",
            candidate_type="FACT"
        )
        # Invariant: AI inferences/unverified claims are demoted to OBSERVATION
        self.assertEqual(res["epistemic_classification"], EpistemicType.OBSERVATION)

    def test_27_memory_secret_scanning(self):
        """27. Verify secret scanning rejects candidate memory with secrets."""
        res = MemoryFirewall.sanitize_and_classify("Here is the secret key: sk-live-99887766554433221100")
        self.assertFalse(res["allowed"])
        self.assertIn("Security Alert", res["reason"])

    def test_28_memory_scope(self):
        """28. Verify memory is saved with proper scope in Letta gateway."""
        res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(
            "Company quarterly objective verified",
            candidate_type="OBSERVATION",
            company_id="comp_test_scope"
        )
        self.assertTrue(res["persisted"])
        rec = stateful_memory_gateway.get_memory_record(res["memory_id"])
        self.assertEqual(rec.scope, MemoryScope.COMPANY)
        self.assertEqual(rec.scope_id, "comp_test_scope")

    def test_29_memory_rejection(self):
        """29. Verify rejected memory produces zero stateful writes."""
        res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(
            "Bearer sk-my-super-secret-token",
            candidate_type="FACT"
        )
        self.assertFalse(res["persisted"])

    # =========================================================================
    # 6. Workforce Tests (30-33)
    # =========================================================================

    def test_30_agency_swarm_to_hal_capability(self):
        """30. Verify Agency Swarm workforce delegation with HAL capability."""
        res = hal_multimodal_adapter.delegate_workforce_multimodal_task("Analyze pipeline bottlenecks")
        self.assertTrue(res["success"])
        self.assertEqual(res["state"], ExecutionState.COMPLETED)

    def test_31_task_delegation_execution(self):
        """31. Verify task delegation creates tracked session."""
        session = execution_manager.create_session("hal.tasks.background")
        self.assertIsNotNone(session["session_id"])
        self.assertEqual(session["state"], ExecutionState.IDLE)

    def test_32_capability_resolution(self):
        """32. Verify tool registry capability resolution."""
        cap = multimodal_registry.get_capability("hal.app.control")
        self.assertEqual(cap["family"], CapabilityFamily.APPLICATION_CONTROL)

    def test_33_workforce_cancellation(self):
        """33. Verify workforce session cancellation."""
        session = execution_manager.create_session("hal.tasks.background")
        res = execution_manager.trigger_killswitch(session["session_id"], reason="Delegation cancelled")
        self.assertEqual(res["state"], ExecutionState.CANCELLED)

    # =========================================================================
    # 7. Execution & Host Control Tests (34-40)
    # =========================================================================

    def test_34_desktop_execution(self):
        """34. Verify sandboxed coworker execution."""
        res = hal_multimodal_adapter.coworker_execute_report("Open monthly executive summary")
        self.assertTrue(res["success"])
        self.assertEqual(res["state"], ExecutionState.COMPLETED)

    def test_35_observation_recording(self):
        """35. Verify observation enters multimodal observation ledger."""
        session = execution_manager.create_session("hal.vision.screen")
        obs = screen_observer.capture_observation(session["session_id"], content_preview="Ledger state checked")
        self.assertTrue(obs["raw_hash"])

    def test_36_independent_verification(self):
        """36. Verify physical disk verification occurs independently of model text."""
        res = governed_files.write_file("audit_receipt.txt", "RECEIPT_CONFIRMED")
        self.assertEqual(res["verification"], "VERIFIED_ON_DISK")

    def test_37_ambiguous_outcome_handling(self):
        """37. Verify transition to AMBIGUOUS when outcome lacks evidence."""
        session = execution_manager.create_session("hal.tasks.background")
        sess = execution_manager.transition_state(session["session_id"], ExecutionState.AMBIGUOUS, "Evidence inconclusive")
        self.assertEqual(sess["state"], ExecutionState.AMBIGUOUS)

    def test_38_crash_recovery(self):
        """38. Verify crash recovery pauses session without blind replay."""
        res = hal_multimodal_adapter.run_crash_and_recovery_demonstration()
        self.assertTrue(res["recovered"])
        self.assertEqual(res["final_state"], ExecutionState.PAUSED)
        self.assertTrue(res["blind_replay_prevented"])

    def test_39_host_takeover(self):
        """39. Verify Host Takeover halts automated AI mutations."""
        res = hal_multimodal_adapter.run_host_takeover_demonstration()
        self.assertTrue(res["host_takeover_active"])
        self.assertEqual(res["state"], ExecutionState.HOST_TAKEOVER)
        self.assertTrue(res["automated_actions_halted"])

    def test_40_evidence_creation(self):
        """40. Verify artifact creation produces verifiable SHA-256 hash."""
        art = governed_artifacts.create_artifact("Test Architecture", "Mermaid Diagram Content", artifact_type="DIAGRAM")
        self.assertTrue(art["artifact_id"])
        self.assertTrue(art["integrity_hash"])

    # =========================================================================
    # 8. End-to-End Required Demonstrations (TEST A - TEST J)
    # =========================================================================

    def test_scenario_a_voice_to_ceo(self):
        """TEST A — VOICE TO CEO: Host speaks -> STT -> CEO -> Response -> TTS."""
        res = hal_multimodal_adapter.voice_to_ceo("Analyze our Q3 gross margins and draft an executive directive.")
        self.assertTrue(res["success"])
        self.assertTrue(res["ceo_response"])
        self.assertTrue(res["audio_payload"]["success"])
        self.assertEqual(res["state"], ExecutionState.COMPLETED)

    def test_scenario_b_screen_understanding(self):
        """TEST B — SCREEN UNDERSTANDING: Screen capture -> Redaction -> Evidence."""
        res = hal_multimodal_adapter.observe_screen(window_title="Financial Dashboard")
        self.assertTrue(res["success"])
        self.assertEqual(res["epistemic_classification"], EpistemicType.OBSERVATION)
        self.assertFalse(res["observation"]["is_business_success"])

    def test_scenario_c_coworker(self):
        """TEST C — COWORKER: 'Open my report and summarize it.'"""
        res = hal_multimodal_adapter.coworker_execute_report("Open my report and summarize it.")
        self.assertTrue(res["success"])
        self.assertEqual(res["verification"], "SHA256_MATCH_CONFIRMED")
        self.assertEqual(res["state"], ExecutionState.COMPLETED)

    def test_scenario_d_controlled_action(self):
        """TEST D — CONTROLLED ACTION: Valid safe command execution."""
        res = hal_multimodal_adapter.execute_controlled_action("pwd")
        self.assertTrue(res["success"])
        self.assertFalse(res["blocked"])
        self.assertEqual(res["state"], ExecutionState.COMPLETED)

    def test_scenario_e_destructive_action(self):
        """TEST E — DESTRUCTIVE ACTION: Block dangerous action."""
        res = hal_multimodal_adapter.execute_controlled_action("sudo rm -rf /etc")
        self.assertFalse(res["success"])
        self.assertTrue(res["blocked"])
        self.assertEqual(res["state"], ExecutionState.BLOCKED)

    def test_scenario_f_letta_memory(self):
        """TEST F — LETTA MEMORY: Secret scanning rejects credential leakage."""
        res = hal_multimodal_adapter.sync_hal_candidate_memory_to_letta(
            "API token is sk-live-secret-never-expose",
            candidate_type="FACT"
        )
        self.assertFalse(res["persisted"])

    def test_scenario_g_agency_swarm(self):
        """TEST G — AGENCY SWARM: AI CEO -> Workforce -> HAL Capability -> Evidence."""
        res = hal_multimodal_adapter.delegate_workforce_multimodal_task("Analyze operational pipeline bottlenecks")
        self.assertTrue(res["success"])
        self.assertEqual(res["state"], ExecutionState.COMPLETED)

    def test_scenario_h_mcp(self):
        """TEST H — MCP: MCP tool invocation cannot bypass security policy."""
        res = hal_multimodal_adapter.invoke_mcp_capability(
            client_id="claude-code",
            tool_name="run_shell",
            parameters={"command": "rm -rf /*"}
        )
        self.assertEqual(res["policy_evaluation"], "BLOCKED")
        self.assertEqual(res["execution_status"], "BLOCKED")

    def test_scenario_i_crash(self):
        """TEST I — CRASH: Kill execution, verify state preservation and safe recovery."""
        res = hal_multimodal_adapter.run_crash_and_recovery_demonstration()
        self.assertTrue(res["recovered"])
        self.assertEqual(res["final_state"], ExecutionState.PAUSED)
        self.assertTrue(res["blind_replay_prevented"])

    def test_scenario_j_host_takeover(self):
        """TEST J — HOST TAKEOVER: Host engages Take Control, halts automated actions."""
        res = hal_multimodal_adapter.run_host_takeover_demonstration()
        self.assertTrue(res["host_takeover_active"])
        self.assertTrue(res["automated_actions_halted"])
        self.assertEqual(res["state"], ExecutionState.HOST_TAKEOVER)


if __name__ == "__main__":
    unittest.main()
