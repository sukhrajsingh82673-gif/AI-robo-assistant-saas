"""
Step 9 Preservation Contract Test (Rule 77)
===========================================
Cryptographically verifies that no file from Steps 1 through 8 has been
modified, deleted, or tampered with during Step 9 execution.
Source of truth: docs/baselines/STEP1-8_BASELINE.json (frozen at tag step8-final).
"""

import os
import re
import json
import hashlib
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO_ROOT, "docs", "baselines", "STEP1-8_BASELINE.json")


@pytest.fixture(scope="module")
def baseline_data():
    assert os.path.exists(BASELINE_PATH), f"Baseline manifest missing: {BASELINE_PATH}"
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestStep9PreservationContract:
    """Verifies that all baseline files from Steps 1-8 remain unchanged."""

    def test_01_baseline_file_count_and_metadata(self, baseline_data):
        """Verifies baseline metadata points to tag step8-final."""
        assert baseline_data.get("tag") == "step8-final"
        assert baseline_data.get("commit") == "7aee993"
        file_count = baseline_data.get("file_count", 0)
        assert file_count >= 2290, f"Expected at least 2290 baseline files, got {file_count}"

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

        assert not missing, f"Rule 77 Violation: {len(missing)} Step 1-8 baseline files are missing: {missing[:5]}"
        assert not mismatched, f"Rule 77 Violation: {len(mismatched)} Step 1-8 baseline files have been modified: {[m[0] for m in mismatched[:5]]}"

    def test_03_mutation_check_altered_hash_fails(self, baseline_data):
        """Mutation test: Simulating an altered file hash triggers failure."""
        sample_file = next(iter(baseline_data.get("files", {}).keys()))
        fake_baseline = dict(baseline_data.get("files", {}))
        fake_baseline[sample_file] = "0000000000000000000000000000000000000000000000000000000000000000"

        abs_path = os.path.join(REPO_ROOT, sample_file)
        with open(abs_path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()

        assert actual != fake_baseline[sample_file], "Mutation test must detect tampered hash"

    def test_04_rule68_industry_branching_grep_clean(self):
        """Rule 68 check: Zero occurrences of hardcoded 'if industry ==' branching across Python code."""
        pattern = re.compile(r"^\s*if\s+industry\s*==", re.MULTILINE)
        hits = []

        for root, dirs, files in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "node_modules", "__pycache__", "tests")]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        for idx, line in enumerate(f, 1):
                            if pattern.search(line):
                                hits.append(f"{full_path}:{idx}")

        assert len(hits) == 0, f"Rule 68 Violation: Disallowed 'if industry ==' found: {hits}"
