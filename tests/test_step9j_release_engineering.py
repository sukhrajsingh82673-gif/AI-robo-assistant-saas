"""
Tests for Sub-Step 9J: Release Engineering, Canary Rollouts, SBOM, and Provenance.
"""

import os
import json
import pytest
from core.release.canary import ProgressiveCanaryRollout, CanaryStage, CanaryHealthMetric
from core.release.provenance import SbomProvenanceGenerator
from scripts.release_readiness import evaluate_release_readiness

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestStep9jReleaseEngineering:

    def test_progressive_canary_rollout_full_success_path(self):
        """Verify canary rollout advances through 5% -> 25% -> 50% -> 100% under healthy telemetry."""
        rollout = ProgressiveCanaryRollout(target_version="v9.0.0", baseline_version="v8.0.0")
        assert rollout.current_stage == CanaryStage.STAGE_0_INACTIVE

        # Stage 1: 5% traffic
        m1 = CanaryHealthMetric(stage_percent=5, error_rate_5xx_percent=0.02, p99_latency_ms=110.0, health_check_pass=True)
        ok1, msg1 = rollout.advance_stage(m1)
        assert ok1
        assert rollout.current_stage == CanaryStage.STAGE_1_CANARY_5
        assert rollout.active_traffic_percent == 5

        # Stage 2: 25% traffic
        m2 = CanaryHealthMetric(stage_percent=25, error_rate_5xx_percent=0.03, p99_latency_ms=115.0, health_check_pass=True)
        ok2, _ = rollout.advance_stage(m2)
        assert ok2
        assert rollout.current_stage == CanaryStage.STAGE_2_CANARY_25
        assert rollout.active_traffic_percent == 25

        # Stage 3: 50% traffic
        m3 = CanaryHealthMetric(stage_percent=50, error_rate_5xx_percent=0.04, p99_latency_ms=120.0, health_check_pass=True)
        ok3, _ = rollout.advance_stage(m3)
        assert ok3
        assert rollout.current_stage == CanaryStage.STAGE_3_CANARY_50

        # Stage 4: 100% full release
        m4 = CanaryHealthMetric(stage_percent=100, error_rate_5xx_percent=0.02, p99_latency_ms=118.0, health_check_pass=True)
        ok4, _ = rollout.advance_stage(m4)
        assert ok4
        assert rollout.current_stage == CanaryStage.STAGE_4_FULL_100
        assert rollout.active_traffic_percent == 100
        assert not rollout.is_rolled_back

    def test_canary_auto_rollback_on_5xx_spike(self):
        """Verify canary immediately shifts 100% traffic back to baseline version when 5xx errors breach threshold."""
        rollout = ProgressiveCanaryRollout(target_version="v9.0.0", baseline_version="v8.0.0")

        # Advance to 5%
        rollout.advance_stage(CanaryHealthMetric(5, 0.05, 120.0, True))

        # Sudden spike: 1.5% 5xx errors (> 0.5% threshold)
        bad_metric = CanaryHealthMetric(stage_percent=25, error_rate_5xx_percent=1.5, p99_latency_ms=130.0, health_check_pass=True)
        ok, reason = rollout.advance_stage(bad_metric)

        assert not ok
        assert rollout.is_rolled_back is True
        assert rollout.current_stage == CanaryStage.ROLLED_BACK
        assert rollout.active_traffic_percent == 0
        assert "CANARY ROLLBACK TRIGGERED" in reason
        assert "exceeds threshold 0.5%" in reason

    def test_canary_auto_rollback_on_latency_spike(self):
        """Verify canary rolls back immediately on severe p99 latency degradation."""
        rollout = ProgressiveCanaryRollout(target_version="v9.0.0", baseline_version="v8.0.0")
        rollout.advance_stage(CanaryHealthMetric(5, 0.05, 120.0, True))

        # Severe latency degradation: 650ms p99 (> 300ms threshold)
        laggy_metric = CanaryHealthMetric(stage_percent=25, error_rate_5xx_percent=0.1, p99_latency_ms=650.0, health_check_pass=True)
        ok, reason = rollout.advance_stage(laggy_metric)

        assert not ok
        assert rollout.is_rolled_back is True
        assert "p99 latency 650.0ms exceeds threshold" in reason

    def test_cyclonedx_sbom_generation(self):
        """Verify SbomProvenanceGenerator produces valid CycloneDX v1.5 JSON."""
        sbom = SbomProvenanceGenerator.generate_cyclonedx_sbom("9.0.0", "commit_abc123")
        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == "1.5"
        assert len(sbom["components"]) >= 5
        comp_names = [c["name"] for c in sbom["components"]]
        assert "zonata-core" in comp_names
        assert "fastapi" in comp_names

    def test_release_readiness_script(self):
        """Verify scripts/release_readiness.py runs and passes all qualification gates."""
        res = evaluate_release_readiness()
        assert res["all_gates_passed"] is True
        assert res["release_version"] == "9.0.0"
        for gate_name, passed in res["checklist"].items():
            assert passed is True, f"Gate '{gate_name}' failed in release readiness report"
