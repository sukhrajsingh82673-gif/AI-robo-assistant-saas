"""
RoboAssistant Company OS 2.0 — Universal Host & Robot Execution Test Suite
Validates host agent telemetry, resource locks, quarantine boundaries,
desktop robot actions, physical reality verifications, software lifecycle, and browser automation.
"""

import unittest
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core.models import ActionContract, AuthorityLevel, HostType
from core.host_fabric import UniversalHostAgent, HostStatus
from core.desktop_robot import UniversalDesktopRobot
from core.software_manager import SoftwareLifecycleManager
from core.file_intelligence import FileIntelligenceEngine
from core.browser_robot import BrowserExecutionFabric

class TestHostAndRobot(unittest.TestCase):
    def setUp(self):
        self.tenant_id = f"tnt_host_{int(time.time()*1000)}"
        self.host_agent = UniversalHostAgent(tenant_id=self.tenant_id)
        self.robot = UniversalDesktopRobot(self.host_agent)
        self.sandbox_dir = self.robot.sandbox_dir

    def test_host_telemetry_and_quarantine(self):
        telemetry = self.host_agent.get_telemetry()
        self.assertEqual(telemetry["status"], HostStatus.ONLINE)
        self.assertGreater(telemetry["cpu_cores"], 0)

        # Resource locking
        res_uri = "file:///storage/sandbox/test_lock.txt"
        self.assertTrue(self.host_agent.acquire_resource_lock(res_uri))
        self.assertFalse(self.host_agent.acquire_resource_lock(res_uri))  # cannot re-lock concurrently
        self.host_agent.release_resource_lock(res_uri)
        self.assertTrue(self.host_agent.acquire_resource_lock(res_uri))
        self.host_agent.release_resource_lock(res_uri)

        # Quarantine
        self.host_agent.quarantine(reason="Anomalous outbound traffic")
        self.assertTrue(self.host_agent.quarantined)
        self.assertEqual(self.host_agent.get_telemetry()["status"], HostStatus.QUARANTINED)

        # Quarantined host blocks execution
        proc_res = self.host_agent.execute_governed_process(["echo", "hello"])
        self.assertFalse(proc_res["success"])
        self.assertIn("QUARANTINED", proc_res["error"])

        self.host_agent.unquarantine()
        self.assertFalse(self.host_agent.quarantined)

    def test_desktop_robot_file_and_process_physical_verification(self):
        test_file = os.path.join(self.sandbox_dir, "test_robot_artifact.txt")
        if os.path.exists(test_file):
            os.remove(test_file)

        # 1. ActionContract: file_write
        write_contract = ActionContract(
            action_id="act_write_01",
            mission_id="mis_test_01",
            agent_id="agt_desktop_op",
            capability="file_write",
            target=test_file,
            host=HostType.LINUX_CLOUD,
            scope="SANDBOX",
            permissions_required=AuthorityLevel.AUTOMATIC_IDEMPOTENT,
            resources_locked=[f"file://{test_file}"],
            expected_outcome="Physical file creation with verified checksum",
            verification_requirements=["sha256_match", "file_exists"]
        )

        res = self.robot.execute_action(write_contract, {"content": "RoboAssistant 2.0 Physical Verification"})
        self.assertTrue(res["success"])
        self.assertTrue(res["verified"])
        self.assertTrue(os.path.exists(test_file))
        self.assertIn("evidence_id", res)

        # 2. ActionContract: file_read
        read_contract = ActionContract(
            action_id="act_read_01",
            mission_id="mis_test_01",
            agent_id="agt_desktop_op",
            capability="file_read",
            target=test_file,
            host=HostType.LINUX_CLOUD,
            scope="SANDBOX",
            permissions_required=AuthorityLevel.SANDBOXED_READ_ONLY,
            resources_locked=[],
            expected_outcome="Read file content",
            verification_requirements=["file_exists"]
        )
        read_res = self.robot.execute_action(read_contract, {})
        self.assertTrue(read_res["success"])
        self.assertIn("Physical Verification", read_res["content_preview"])

        # 3. ActionContract: process_execute
        proc_contract = ActionContract(
            action_id="act_proc_01",
            mission_id="mis_test_01",
            agent_id="agt_desktop_op",
            capability="process_execute",
            target="host_process",
            host=HostType.LINUX_CLOUD,
            scope="HOST",
            permissions_required=AuthorityLevel.AUTOMATIC_IDEMPOTENT,
            resources_locked=[],
            expected_outcome="Execute deterministic command and check exit code zero",
            verification_requirements=["exit_code_zero"]
        )
        proc_res = self.robot.execute_action(proc_contract, {"command": ["python3", "-c", "print('EXEC_OK')"]})
        self.assertTrue(proc_res["success"])
        self.assertEqual(proc_res["exit_code"], 0)
        self.assertIn("EXEC_OK", proc_res["stdout"])

        # 4. ActionContract: file_delete
        del_contract = ActionContract(
            action_id="act_del_01",
            mission_id="mis_test_01",
            agent_id="agt_desktop_op",
            capability="file_delete",
            target=test_file,
            host=HostType.LINUX_CLOUD,
            scope="SANDBOX",
            permissions_required=AuthorityLevel.AUTOMATIC_IDEMPOTENT,
            resources_locked=[f"file://{test_file}"],
            expected_outcome="Physical file deletion",
            verification_requirements=["file_absent"]
        )
        del_res = self.robot.execute_action(del_contract, {})
        self.assertTrue(del_res["success"])
        self.assertFalse(os.path.exists(test_file))

    def test_software_and_file_intelligence(self):
        sw_mgr = SoftwareLifecycleManager(self.host_agent, tenant_id=self.tenant_id)
        # Whitelisted package
        whitelisted = sw_mgr.verify_package_policy("jq")
        self.assertTrue(whitelisted["allowed"])

        # Non-whitelisted package requires owner escalation
        unauthorized = sw_mgr.install_package("malicious_unverified_crypto_miner")
        self.assertFalse(unauthorized["success"])
        self.assertEqual(unauthorized["status"], "BLOCKED_PENDING_APPROVAL")

        # File intelligence
        fi = FileIntelligenceEngine(self.sandbox_dir)
        temp_data_file = os.path.join(self.sandbox_dir, "test_download.json")
        with open(temp_data_file, "w") as f:
            f.write('{"data": "untrusted_payload"}')

        verification = fi.verify_downloaded_data(temp_data_file)
        self.assertTrue(verification["verified"])
        self.assertTrue(verification["untrusted_data_flag"])
        self.assertTrue(verification["executable_stripped"])
        if os.path.exists(temp_data_file):
            os.remove(temp_data_file)

    def test_browser_robot_structured_automation(self):
        browser = BrowserExecutionFabric()
        nav_res = browser.navigate("https://example.com/bookings")
        self.assertEqual(nav_res["url"], "https://example.com/bookings")
        # Navigation is a real HTTP GET: either it succeeds with an observed
        # status code, or it fails with a real transport error.
        if nav_res["success"]:
            self.assertEqual(nav_res["execution_mode"], "LIVE_HTTP")
            self.assertTrue(nav_res["http_status"] >= 200)
        else:
            self.assertIn("error", nav_res)
        self.assertFalse(nav_res["simulated"])

        # No DOM engine is installed: extraction returns no fixtures.
        ext_res = browser.extract_structured_data(query="rates")
        self.assertFalse(ext_res["success"])
        self.assertEqual(ext_res["code"], "DOM_ENGINE_NOT_AVAILABLE")
        self.assertEqual(ext_res["extracted_items"], [])

        form_res = browser.submit_form("login_form", {"user": "admin", "password": "SuperSecretPassword123"})
        self.assertFalse(form_res["success"])
        self.assertEqual(form_res["code"], "BROWSER_DRIVER_NOT_CONFIGURED")
        self.assertEqual(form_res["fields_submitted"]["password"], "***REDACTED***")

if __name__ == "__main__":
    unittest.main()
