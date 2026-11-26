"""
ZONATA Unit & Contract Tests — Sub-Step 3F: Anti-Evasion Policy & Dependency Deny-List (Rule 25).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from core.browser.challenge_policy import ChallengePolicyEngine
from core.browser.rate_limiter import BackoffBudget, GovernedRateLimiter
from core.browser.types import ChallengeDetectionResult, ChallengeType
from core.security.anti_evasion import (
    AntiEvasionViolationError,
    scan_dependency_file,
    scan_python_code,
    scan_repository_anti_evasion,
)


class TestStep3AntiEvasion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["ZONATA_TEST_MODE"] = "1"

    def test_01_ast_scanner_flags_banned_imports(self):
        """Rule 25: AST scanner must flag banned stealth and solver imports."""
        code_with_stealth = """
import playwright_stealth
def run():
    pass
"""
        violations = scan_python_code(code_with_stealth, filename="bad_agent.py")
        self.assertTrue(len(violations) >= 1)
        self.assertEqual(violations[0].violation_type, "BANNED_IMPORT")
        self.assertIn("playwright_stealth", violations[0].offending_symbol)

        code_with_2captcha = """
from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
def solve():
    pass
"""
        violations2 = scan_python_code(code_with_2captcha, filename="bad_solver.py")
        self.assertTrue(len(violations2) >= 1)
        self.assertEqual(violations2[0].violation_type, "BANNED_IMPORT")

    def test_02_ast_scanner_flags_banned_endpoints_and_stealth_patterns(self):
        """Rule 25: AST scanner must flag solver endpoints and webdriver evasion."""
        code_with_endpoint = """
url = "https://2captcha.com/in.php"
api_key = "test_key"
"""
        violations = scan_python_code(code_with_endpoint, filename="solver_caller.py")
        self.assertTrue(any(v.violation_type == "BANNED_SOLVER_ENDPOINT" for v in violations))

    def test_03_dependency_manifest_scanning(self):
        """Rule 25: Dependency scanner must flag banned packages in requirements.txt and package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = os.path.join(tmpdir, "requirements.txt")
            with open(req_file, "w") as f:
                f.write("requests==2.31.0\nplaywright-stealth>=1.0.0\n2captcha-python\n")

            violations = scan_dependency_file(req_file)
            symbols = [v.offending_symbol for v in violations]
            self.assertIn("playwright-stealth", symbols)
            self.assertIn("2captcha-python", symbols)

            pkg_json = os.path.join(tmpdir, "package.json")
            with open(pkg_json, "w") as f:
                f.write('{"dependencies": {"puppeteer-extra-plugin-stealth": "^2.11.2"}}')

            json_violations = scan_dependency_file(pkg_json)
            self.assertTrue(any(v.offending_symbol == "puppeteer-extra-plugin-stealth" for v in json_violations))

    def test_04_challenge_policy_halts_and_suggests_official_routes(self):
        """Rule 25: Challenge encounters halt task, set BLOCKED state, and provide official routes."""
        detection = ChallengeDetectionResult(
            has_challenge=True,
            challenge_type=ChallengeType.CLOUDFLARE_TURNSTILE,
            signatures_detected=["challenges.cloudflare.com"],
            masked_widget_bounds={"x": 100, "y": 200, "width": 300, "height": 65},
        )

        res = ChallengePolicyEngine.evaluate_challenge(
            detection=detection,
            task_id="task_audit_99",
            tenant_id="tenant_alpha",
            company_id="company_omega",
            url="https://github.com/login",
        )

        self.assertEqual(res["status"], "BLOCKED")
        self.assertEqual(res["action"], "HALT_AND_HANDOFF_TO_HUMAN")
        inbox = res["inbox_item"]
        self.assertEqual(inbox["status"], "BLOCKED")
        self.assertEqual(inbox["challenge_type"], "CLOUDFLARE_TURNSTILE")
        self.assertEqual(inbox["widget_bounding_box"], {"x": 100, "y": 200, "width": 300, "height": 65})

        suggestions = inbox["official_route_suggestions"]
        self.assertTrue(len(suggestions) >= 2)
        categories = [s["category"] for s in suggestions]
        self.assertIn("OFFICIAL_API", categories)
        self.assertIn("IP_ALLOWLIST", categories)

    def test_05_rate_limiter_jittered_backoff_and_no_ip_rotation(self):
        """Rule 25: Governed rate limiter applies jittered backoff and forbids IP rotation."""
        budget = BackoffBudget(max_retries=3, base_delay_seconds=0.01, max_delay_seconds=0.1)
        limiter = GovernedRateLimiter(budget=budget)

        # 1. Attempting proxy rotation must fail unconditionally
        with self.assertRaises(AntiEvasionViolationError):
            limiter.request_proxy_rotation("http://192.168.1.100:8080")

        # 2. Governed backoff simulation on HTTP 429
        mock_op = MagicMock()
        err_429 = Exception("Rate limited")
        err_429.status_code = 429
        mock_op.side_effect = [err_429, err_429, "SUCCESS"]

        delays = []
        result = limiter.execute_with_backoff(
            mock_op,
            on_retry=lambda attempt, delay: delays.append(delay),
            sleeper=lambda d: None,  # no-op sleep for test speed
        )

        self.assertEqual(result, "SUCCESS")
        self.assertEqual(len(delays), 2)
        for d in delays:
            self.assertGreater(d, 0.0)

    def test_06_current_codebase_anti_evasion_clean(self):
        """Rule 25 AST check across entire repository must have zero violations."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        violations = scan_repository_anti_evasion(repo_root)
        self.assertEqual(
            violations,
            [],
            f"Repository contains Rule 25 violations: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
