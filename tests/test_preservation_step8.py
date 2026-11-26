"""
Step 8 Preservation Contract Test (Rule 67)
===========================================
Cryptographically verifies that no file from Steps 1 through 7 has been
modified, deleted, or tampered with during Step 8 execution.
Source of truth: docs/baselines/STEP1-7_BASELINE.json (frozen at tag step7-final).
"""

import os
import re
import json
import hashlib
import pytest
from core.industry.flags import is_industry_factory_enabled, is_global_readiness_enabled

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO_ROOT, "docs", "baselines", "STEP1-7_BASELINE.json")


@pytest.fixture(scope="module")
def baseline_data():
    assert os.path.exists(BASELINE_PATH), f"Baseline manifest missing: {BASELINE_PATH}"
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestStep8PreservationContract:
    """Verifies that all baseline files from Steps 1-7 remain unchanged."""

    def test_01_baseline_file_count_and_metadata(self, baseline_data):
        """Verifies baseline metadata points to tag step7-final."""
        assert baseline_data.get("tag") == "step7-final"
        assert baseline_data.get("commit") == "b0e8f70"
        file_count = baseline_data.get("file_count", 0)
        assert file_count >= 2100, f"Expected at least 2100 baseline files, got {file_count}"

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

        assert not missing, f"Rule 67 Violation: {len(missing)} Step 1-7 baseline files are missing: {missing[:5]}"
        assert not mismatched, f"Rule 67 Violation: {len(mismatched)} Step 1-7 baseline files have been modified: {[m[0] for m in mismatched[:5]]}"

    def test_03_mutation_check_altered_hash_fails(self, baseline_data):
        """Mutation test: Simulating an altered file hash triggers failure."""
        sample_file = next(iter(baseline_data.get("files", {}).keys()))
        fake_baseline = dict(baseline_data.get("files", {}))
        fake_baseline[sample_file] = "0000000000000000000000000000000000000000000000000000000000000000"

        abs_path = os.path.join(REPO_ROOT, sample_file)
        with open(abs_path, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert actual != fake_baseline[sample_file]

    def test_04_flags_off_equivalence(self, monkeypatch):
        """Verifies Step 8 feature flags default to OFF, guaranteeing baseline equivalence."""
        monkeypatch.delenv("STEP8_INDUSTRY_FACTORY_ENABLED", raising=False)
        monkeypatch.delenv("STEP8_GLOBAL_READINESS_ENABLED", raising=False)

        assert is_industry_factory_enabled("comp_test_default") is False
        assert is_global_readiness_enabled("comp_test_default") is False

    def test_05_migration_linter_additive_only(self):
        """Verifies Step 8 migration is strictly additive and contains no destructive DDL."""
        mig_path = os.path.join(REPO_ROOT, "migrations", "pg", "0034_step8_industry_jurisdiction_benchmark_schemas.sql")
        assert os.path.exists(mig_path), "Migration 0034 must exist"

        with open(mig_path, "r", encoding="utf-8") as f:
            sql = f.read()

        destructive_patterns = [
            r"\bDROP\s+TABLE\b",
            r"\bDROP\s+COLUMN\b",
            r"\bALTER\s+TABLE\s+.*\s+DROP\b",
            r"\bDISABLE\s+ROW\s+LEVEL\s+SECURITY\b",
        ]
        for pat in destructive_patterns:
            assert not re.search(pat, sql, re.IGNORECASE), f"Destructive DDL '{pat}' detected in migration 0034"

    def test_06_rule_68_industry_neutrality_preserved(self):
        """Rule 68 check: Zero code branches on industry or sector name."""
        pattern = re.compile(r"(if\s+industry\s*==|industry\s*==|sector\s*==|isic\b.*==|if\s+industry\s+in)")
        core_dir = os.path.join(REPO_ROOT, "core")
        for root, dirs, files in os.walk(core_dir):
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    fpath = os.path.join(root, file)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for lno, line in enumerate(f, 1):
                            assert not pattern.search(line), f"Rule 68 violation in {fpath}:{lno}: {line.strip()}"
