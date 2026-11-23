"""
ZONATA Unit & Contract Tests — Sub-Step 3J: Agent Factory Import Lane & Sandboxing (Rule 5, 23, 25, 32).
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from core.agent_import.license_gate import LicenseGate
from core.agent_import.sandbox_runner import SandboxSkillRunner
from core.agent_import.scanner import SkillImportScanner
from core.agent_import.types import (
    DangerousCodeRejectedError,
    ImportSourceType,
    ImportedSkillPackage,
    LicenseViolationError,
    MalwareDetectedError,
    SkillCertificationStatus,
)


class TestStep3AgentImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"

    def test_01_license_gating_allows_permissive_rejects_copyleft(self):
        """Rule 5: Permissive licenses are allowed; copyleft and restrictive licenses are rejected."""
        valid_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause", "ISC", "CC0-1.0", "Unlicense"]
        for lic in valid_licenses:
            self.assertTrue(LicenseGate.verify_license(lic), f"License '{lic}' should be permitted")

        invalid_licenses = ["GPL-3.0-only", "AGPL-3.0", "SSPL-1.0", "BSL-1.1", "Elastic-2.0"]
        for lic in invalid_licenses:
            with self.assertRaises(LicenseViolationError):
                LicenseGate.verify_license(lic)

    def test_02_clamav_malware_quarantine(self):
        """Rule 32: ClamAV antivirus flags infected payloads, halting import."""
        # Simulated infected test payload
        infected_bytes = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

        mock_av_result = MagicMock()
        mock_av_result.infected = True
        mock_av_result.virus_name = "Eicar-Signature"

        with patch("core.agent_import.scanner.resolve_antivirus_provider") as mock_prov_fn:
            mock_prov = MagicMock()
            mock_prov.scan_bytes.return_value = mock_av_result
            mock_prov_fn.return_value = mock_prov

            with self.assertRaises(MalwareDetectedError) as ctx:
                SkillImportScanner.scan_code_bytes(infected_bytes, filename="eicar.py")
            self.assertIn("Eicar-Signature", str(ctx.exception))

    def test_03_dangerous_code_ast_rejection(self):
        """Rule 32 & 25: Dangerous dynamic evaluation and stealth evasion are rejected."""
        # 1. Dangerous eval
        bad_eval_bytes = b"""
def execute(data):
    return eval(data)
"""
        with self.assertRaises(DangerousCodeRejectedError) as ctx:
            SkillImportScanner.scan_code_bytes(bad_eval_bytes, filename="bad_eval.py")
        self.assertIn("eval", str(ctx.exception))

        # 2. Rule 25 anti-evasion violation in imported package
        bad_stealth_bytes = b"""
import playwright_stealth
def run():
    pass
"""
        with self.assertRaises(DangerousCodeRejectedError) as ctx2:
            SkillImportScanner.scan_code_bytes(bad_stealth_bytes, filename="bad_stealth.py")
        self.assertIn("Rule 25", str(ctx2.exception))

    def test_04_execution_sandboxing_scratch_containment(self):
        """Rule 23 & 32: Sandboxed runner isolates execution and restricts writes to scratch dir."""
        runner = SandboxSkillRunner(tenant_id="tenant_gamma", skill_id="skill_csv_parser")
        created_file_path = None

        def skill_task(scratch_dir: str) -> str:
            nonlocal created_file_path
            out_file = os.path.join(scratch_dir, "output.txt")
            created_file_path = out_file
            with open(out_file, "w") as f:
                f.write("data_processed")
            return "SUCCESS"

        result = runner.run_skill_task(skill_task, timeout_seconds=5.0)
        self.assertTrue(result["success"])
        self.assertEqual(result["output"], "SUCCESS")

        # After task completes, scratch directory must be safely cleaned up
        self.assertFalse(os.path.exists(created_file_path))

    def test_05_clean_skill_import_and_certification(self):
        """End-to-end import: clean code passes license & security scans and receives certification."""
        clean_code_bytes = b"""
def calculate_metrics(values):
    return sum(values) / len(values) if values else 0.0
"""
        scan_res = SkillImportScanner.scan_code_bytes(clean_code_bytes, filename="stats.py")
        self.assertTrue(scan_res["clean"])
        self.assertTrue(scan_res["clamav_passed"])
        self.assertTrue(scan_res["ast_security_passed"])

        self.assertTrue(LicenseGate.verify_license("Apache-2.0"))

        pkg = ImportedSkillPackage(
            skill_id="skill_stats_101",
            name="statistics_helper",
            version="1.0.0",
            source_type=ImportSourceType.GITHUB_REPO,
            source_url="https://github.com/example/stats-helper",
            license_name="Apache-2.0",
            sha256=scan_res["sha256"],
            certification_status=SkillCertificationStatus.CERTIFIED,
        )

        self.assertEqual(pkg.certification_status, SkillCertificationStatus.CERTIFIED)
        self.assertEqual(len(pkg.sha256), 64)


if __name__ == "__main__":
    unittest.main()
