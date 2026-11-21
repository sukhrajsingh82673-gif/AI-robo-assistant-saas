"""Unit & Mutation Tests for AST Truth Linter.

Verifies OpenCode Step 1C.4:
1. AST linter scans adapter/port modules and passes on honest implementations.
2. Mutation checks (Standing Rule 8): Proves that the linter catches:
   - Success status without setting a non-empty provider_ref.
   - Rigorous status (DELIVERED, SENT, STORED, POSTED) without a live check.
"""

import os
import unittest
from core.lint.truth_linter import (
    lint_code_string,
    lint_file,
    TruthASTVisitor,
)


class TestTruthASTLinter(unittest.TestCase):

    def test_linter_passes_on_current_ports_and_capability_probe(self):
        """Current codebase ports and probe files must be 100% compliant with truth rules."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_files = [
            os.path.join(base_dir, "core", "ports", "base.py"),
            os.path.join(base_dir, "core", "capability_probe.py"),
        ]
        all_violations = []
        for f in target_files:
            if os.path.exists(f):
                violations = lint_file(f)
                all_violations.extend(violations)

        self.assertEqual(all_violations, [], f"Unexpected AST truth violations: {all_violations}")

    def test_mutation_flags_success_without_provider_ref(self):
        """Mutation Check: Returning OK without a provider_ref MUST fail the linter."""
        bad_code = """
from core.ports.base import ProviderResult, PortStatus

def do_fake_store():
    return ProviderResult(
        status=PortStatus.OK,
        provider="fake_s3",
        provider_ref=None,
        latency_ms=1.0
    )
"""
        violations = lint_code_string(bad_code, filename="bad_adapter.py")
        self.assertTrue(len(violations) >= 1)
        self.assertTrue(any("returns success status 'OK' without setting a non-empty provider_ref" in v for v in violations))

    def test_mutation_flags_success_with_empty_string_provider_ref(self):
        """Mutation Check: Returning ACCEPTED_BY_PROVIDER with empty string provider_ref MUST fail."""
        bad_code = """
from core.ports.base import ProviderResult

def do_fake_send():
    return ProviderResult(
        status="ACCEPTED_BY_PROVIDER",
        provider="fake_smtp",
        provider_ref="",
        latency_ms=1.0
    )
"""
        violations = lint_code_string(bad_code, filename="bad_adapter.py")
        self.assertTrue(len(violations) >= 1)
        self.assertTrue(any("returns success status 'ACCEPTED_BY_PROVIDER' without setting a non-empty provider_ref" in v for v in violations))

    def test_mutation_flags_stored_without_live_check(self):
        """Mutation Check: Claiming STORED without live verification check MUST fail."""
        bad_code = """
from core.ports.base import ProviderResult

def store_object_dishonest(data):
    # Fabricates success without inspecting response or verifying hash
    return ProviderResult(
        status="STORED",
        provider="s3",
        provider_ref="obj_123"
    )
"""
        violations = lint_code_string(bad_code, filename="dishonest_s3.py")
        self.assertTrue(len(violations) >= 1)
        self.assertTrue(any("claims 'STORED' without performing a live verification check" in v for v in violations))

    def test_mutation_allows_stored_with_live_check(self):
        """Mutation Check: Claiming STORED with live verification check (hashlib/read_back) passes."""
        honest_code = """
import hashlib
from core.ports.base import ProviderResult

def store_object_honest(data, expected_sha):
    calc_sha = hashlib.sha256(data).hexdigest()
    if calc_sha != expected_sha:
        raise ValueError("Checksum mismatch")
    return ProviderResult(
        status="STORED",
        provider="s3",
        provider_ref=f"sha_{calc_sha}"
    )
"""
        violations = lint_code_string(honest_code, filename="honest_s3.py")
        self.assertEqual(violations, [])

    def test_not_configured_and_not_implemented_allowed_without_provider_ref(self):
        """NOT_CONFIGURED and NOT_IMPLEMENTED are non-success and may omit provider_ref."""
        clean_code = """
from core.ports.base import ProviderResult, PortStatus

def probe_unconfigured():
    return ProviderResult(
        status=PortStatus.NOT_CONFIGURED,
        provider="none",
        provider_ref=None,
        error="Not configured"
    )

def probe_unimplemented():
    return ProviderResult(
        status=PortStatus.NOT_IMPLEMENTED,
        provider="none",
        provider_ref=None,
        error="Not implemented"
    )
"""
        violations = lint_code_string(clean_code, filename="ports.py")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
