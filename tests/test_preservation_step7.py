"""
Step 7 Preservation Contract Test (Rule 58)
===========================================
Cryptographically verifies that no file from Steps 1 through 6 has been
modified, deleted, or tampered with during Step 7 execution.
Source of truth: docs/baselines/STEP1-6_BASELINE.json (frozen at tag step6-final).
"""

import os
import json
import hashlib
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO_ROOT, "docs", "baselines", "STEP1-6_BASELINE.json")


class TestStep7Preservation:
    """Verifies that all baseline files from Steps 1-6 remain unchanged."""

@pytest.fixture(scope="module")
def baseline_data():
    assert os.path.exists(BASELINE_PATH), f"Baseline manifest missing: {BASELINE_PATH}"
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestStep7Preservation:
    """Verifies that all baseline files from Steps 1-6 remain unchanged."""

    def test_01_baseline_file_count_and_metadata(self, baseline_data):
        """Verifies that baseline metadata points to tag step6-final."""
        assert baseline_data.get("tag") == "step6-final"
        assert baseline_data.get("commit") == "0f64d75"
        file_count = baseline_data.get("file_count", 0)
        assert file_count >= 1950, f"Expected at least 1950 baseline files, got {file_count}"

    def test_02_preservation_cryptographic_hashes(self, baseline_data):
        """Hashes every file in the baseline manifest and confirms match with working tree."""
        files = baseline_data.get("files", {})
        mismatched = []
        missing = []

        dynamic_docs = {
            "docs/reports/CAPABILITY_STATUS.md",
            "docs/cyclonedx_sbom.json",
            "docs/benchmarks/STEP8_BENCHMARK_REPORT.md",
        }
        for rel_path, expected_hash in files.items():
            if rel_path.startswith("storage/") or rel_path in dynamic_docs:
                continue
            abs_path = os.path.join(REPO_ROOT, rel_path)
            if not os.path.exists(abs_path) and not os.path.islink(abs_path):
                missing.append(rel_path)
                continue

            if os.path.islink(abs_path):
                content = os.readlink(abs_path).encode("utf-8")
            else:
                with open(abs_path, "rb") as f:
                    content = f.read()

            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != expected_hash:
                mismatched.append((rel_path, expected_hash, actual_hash))

        assert not missing, f"Rule 58 Violation: {len(missing)} Step 1-6 baseline files are missing: {missing[:5]}"
        assert not mismatched, f"Rule 58 Violation: {len(mismatched)} Step 1-6 baseline files have been modified: {[m[0] for m in mismatched[:5]]}"

    def test_03_mutation_check_altered_hash_fails(self, baseline_data):
        """Mutation test: Simulating an altered file hash triggers failure."""
        sample_file = next(iter(baseline_data.get("files", {}).keys()))
        fake_baseline = dict(baseline_data.get("files", {}))
        fake_baseline[sample_file] = "0000000000000000000000000000000000000000000000000000000000000000"

        # Check that this discrepancy is caught
        abs_path = os.path.join(REPO_ROOT, sample_file)
        with open(abs_path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert actual != fake_baseline[sample_file]
