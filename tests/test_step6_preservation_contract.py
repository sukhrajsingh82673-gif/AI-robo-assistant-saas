"""
Unit and Integration Tests for Antigravity Sub-Step 6B:
The Preservation Contract & Regression Gate (Rule 49 & Rule 50).
"""

import os
import json
import pytest
from core.evolution.preservation import (
    PreservationEngine,
    PreservationViolationError,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep6PreservationContract:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = PreservationEngine(repo_root=REPO_ROOT)

    def test_01_step5_baseline_manifest_exists_and_valid(self):
        """Verifies STEP1-5_BASELINE.json exists, is valid, and matches tag step5-final."""
        manifest = self.engine.load_baseline()
        assert manifest.get("schema_version") == "zonata.baseline/v1"
        assert manifest.get("tag") == "step5-final"
        assert manifest.get("step5_commit_sha") == "914f5331bfb7325888c0c0090e4fc6677a913681"
        assert manifest.get("total_files") >= 1900
        assert "core/db.py" in manifest.get("files", {})
        assert "requirements.txt" in manifest.get("files", {})

    def test_02_preservation_engine_verifies_working_copy_integrity(self):
        """Verifies that every baseline file currently on disk matches its Step 5 SHA-256."""
        res = self.engine.verify_baseline_integrity()
        assert res["status"] == "PASS"
        assert res["verified_files"] >= 1900

    def test_03_preservation_engine_detects_tampered_step5_file(self, monkeypatch):
        """Mutation test: verifies tampering with a Step 5 file triggers PreservationViolationError."""
        # Monkeypatch compute_sha256 to simulate tampered content for core/db.py
        orig_compute = self.engine.compute_sha256

        def fake_compute(rel_path):
            if rel_path == "core/db.py":
                return "0000000000000000000000000000000000000000000000000000000000000000"
            return orig_compute(rel_path)

        monkeypatch.setattr(self.engine, "compute_sha256", fake_compute)
        with pytest.raises(PreservationViolationError) as exc_info:
            self.engine.verify_baseline_integrity()
        assert "core/db.py tampered" in str(exc_info.value)

    def test_04_protected_paths_policy_blocks_unauthorized_paths(self):
        """Verifies path allowance logic strictly rejects alterations outside Step 6 scope."""
        # Allowed Step 6 additions
        assert self.engine.is_path_allowed("core/evolution/optimizer.py") is True
        assert self.engine.is_path_allowed("security/protected_paths.yaml") is True
        assert self.engine.is_path_allowed("docs/adr/ADR_0026_OPTIMIZER_STACK_DSPY_GEPA.md") is True
        assert self.engine.is_path_allowed("tests/test_step6_preservation_contract.py") is True
        assert self.engine.is_path_allowed("scripts/step6_scenario.py") is True
        assert self.engine.is_path_allowed(".github/workflows/ci-evolution.yml") is True

        # Forbidden mutations to Step 1-5 files or roots
        assert self.engine.is_path_allowed("core/db.py") is False
        assert self.engine.is_path_allowed("models/agent.py") is False
        assert self.engine.is_path_allowed("web/app.js") is False
        assert self.engine.is_path_allowed("tests/test_truth_linter.py") is False
        assert self.engine.is_path_allowed("rogue_exploit.py") is False

    def test_05_migration_linter_blocks_destructive_ddl(self):
        """Verifies migration linter detects and rejects destructive DDL statements."""
        # Clean additive migration
        clean_ddl = """
        -- Additive migration for evolution knowledge store
        CREATE TABLE IF NOT EXISTS evolution_playbooks (
            id UUID PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            company_id VARCHAR(64) NOT NULL,
            playbook_json JSONB NOT NULL
        );
        ALTER TABLE evolution_playbooks ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON evolution_playbooks FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
        """
        res = self.engine.lint_migration(clean_ddl)
        assert res["status"] == "PASS"

        # Destructive migrations violating Rule 49
        destructive_cases = [
            ("DROP TABLE users CASCADE;", "DROP TABLE"),
            ("ALTER TABLE organizations DROP COLUMN company_id;", "DROP COLUMN"),
            ("ALTER TABLE agents DROP something;", "ALTER TABLE DROP"),
            ("ALTER TABLE ledgers DISABLE ROW LEVEL SECURITY;", "Disabling RLS"),
            ("DROP POLICY pii_access_policy ON audit_logs;", "DROP POLICY"),
        ]

        for ddl, expected_kw in destructive_cases:
            with pytest.raises(PreservationViolationError) as exc_info:
                self.engine.lint_migration(ddl)
            assert expected_kw.lower() in str(exc_info.value).lower()

    def test_06_evolution_flag_defaults_to_false_and_preserves_step5_behavior(self, monkeypatch):
        """Verifies Rule 50: evolution defaults to OFF, maintaining bit-for-bit Step 5 equivalence."""
        monkeypatch.delenv("EVOLUTION_ENABLED", raising=False)
        res = self.engine.verify_evolution_flag_equivalence()
        assert res["status"] == "PASS"
        assert res["evolution_enabled"] is False
        assert res["is_default_off"] is True

        # When explicitly enabled
        monkeypatch.setenv("EVOLUTION_ENABLED", "true")
        res_enabled = self.engine.verify_evolution_flag_equivalence()
        assert res_enabled["evolution_enabled"] is True

    def test_07_git_diff_integrity_against_step5_final(self):
        """Verifies git diff from tag step5-final contains zero illegal mutations."""
        diff_res = self.engine.verify_git_diff_integrity("step5-final")
        assert diff_res["status"] == "PASS"
        assert diff_res["allowed_additions"] >= 10
