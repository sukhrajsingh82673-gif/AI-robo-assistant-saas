"""
Unit and Integration Tests for Antigravity Sub-Step 6F:
Governed Self-Improvement Engine (DSPy + GEPA, Held-Out Tests, Safety Floor, Canary & Rollback).
"""

import pytest
from core.evolution.optimizer import (
    GovernedSelfImprovementEngine,
    OptimizationTargetType,
    OptimizationCandidate,
    SafetyFloorViolationError,
    CageIntegrityViolationError,
    RollbackTriggeredError,
)


class TestStep6Optimizer:
    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = GovernedSelfImprovementEngine()
        self.engine.set_baseline_metrics("financial_doc_classifier", accuracy=0.82, error_rate=0.01)

    def test_01_optimizer_candidate_improves_training_metric(self):
        """Verifies candidate proposal with improved training metric is created as DRAFT."""
        candidate = self.engine.propose_candidate(
            target_type=OptimizationTargetType.PROMPT,
            target_name="financial_doc_classifier",
            proposed_payload={
                "system_prompt": "You are a senior financial auditor classifying ledger extracts.",
                "few_shot_seed": 42,
            },
            baseline_id="prompt_v1",
            training_score=0.94,
        )
        assert candidate.status == "DRAFT"
        assert candidate.training_score == 0.94
        assert candidate.target_type == OptimizationTargetType.PROMPT

    def test_02_held_out_evaluation_confirms_generalization(self):
        """Verifies evaluation on held-out test set approves generalized candidate."""
        candidate = self.engine.propose_candidate(
            target_type=OptimizationTargetType.TOOL_ROUTING,
            target_name="document_routing_heuristic",
            proposed_payload={"routing_order": ["tika_ocr", "pdf_parser", "raw_text"]},
            baseline_id="route_v1",
            training_score=0.90,
        )

        # 20 held-out test cases (all passing, including 5 safety checks)
        test_cases = [
            {"id": f"tc_{i}", "simulated_pass": True, "is_safety_check": (i % 4 == 0)}
            for i in range(20)
        ]

        res = self.engine.evaluate_held_out(candidate.candidate_id, test_cases)
        assert res["status"] == "APPROVED"
        assert res["safety_score"] == 1.0
        assert res["held_out_accuracy"] == 1.0
        assert candidate.status == "APPROVED"

    def test_03_safety_semantic_floor_rejects_candidate_with_any_safety_regression(self):
        """Rule 52: Even with 95% accuracy, 1 failed safety check causes immediate rejection."""
        candidate = self.engine.propose_candidate(
            target_type=OptimizationTargetType.PROMPT,
            target_name="financial_doc_classifier",
            proposed_payload={"system_prompt": "Fast classifier with relaxed boundary."},
            baseline_id="prompt_v1",
            training_score=0.98,
        )

        # 20 test cases: 19 pass, but 1 safety check fails
        test_cases = [
            {"id": f"tc_{i}", "simulated_pass": (i != 0), "is_safety_check": (i == 0)}
            for i in range(20)
        ]

        with pytest.raises(SafetyFloorViolationError) as exc:
            self.engine.evaluate_held_out(candidate.candidate_id, test_cases)

        assert "breached safety semantic floor" in str(exc.value)
        assert candidate.status == "REJECTED"
        assert candidate.safety_score < 1.0

    def test_04_canary_rollout_allocates_ten_percent_traffic(self):
        """Rule 53: Approved candidate receives 10% canary traffic allocation."""
        candidate = self.engine.propose_candidate(
            target_type=OptimizationTargetType.FEW_SHOT_DEMO,
            target_name="financial_doc_classifier",
            proposed_payload={"few_shots": ["example1", "example2"]},
            baseline_id="demo_v1",
            training_score=0.91,
        )
        self.engine.evaluate_held_out(
            candidate.candidate_id,
            [{"id": "tc1", "simulated_pass": True, "is_safety_check": True}],
        )

        dep = self.engine.deploy_canary(candidate.candidate_id, canary_ratio=0.10)
        assert dep["status"] == "CANARY"
        assert dep["canary_ratio"] == 0.10

        # Simulate 500 requests
        canary_routed = 0
        baseline_routed = 0
        for i in range(500):
            dest = self.engine.route_traffic("financial_doc_classifier", f"req_{i}")
            if dest == candidate.candidate_id:
                canary_routed += 1
            else:
                baseline_routed += 1

        # Assert approximately 10% (between 30 and 70 out of 500)
        assert 30 <= canary_routed <= 70
        assert baseline_routed >= 430

    def test_05_simulated_canary_regression_triggers_auto_rollback(self):
        """Rule 53: Canary degradation >2% over baseline triggers circuit-breaker auto-rollback."""
        candidate = self.engine.propose_candidate(
            target_type=OptimizationTargetType.PROMPT,
            target_name="financial_doc_classifier",
            proposed_payload={"system_prompt": "Experimental prompt"},
            baseline_id="prompt_v1",
        )
        self.engine.evaluate_held_out(
            candidate.candidate_id,
            [{"id": "tc1", "simulated_pass": True, "is_safety_check": True}],
        )
        self.engine.deploy_canary(candidate.candidate_id)

        # Baseline error rate is 0.01 (1%). Feed 10 canary calls with 5 failures (50% error rate).
        with pytest.raises(RollbackTriggeredError) as exc:
            for i in range(10):
                self.engine.record_canary_telemetry(candidate.candidate_id, success=(i >= 5))

        assert "Canary Circuit Breaker" in str(exc.value)
        assert "Auto-rollback executed" in str(exc.value)
        assert candidate.status == "ROLLED_BACK"
        # Confirm candidate was removed from active canaries
        assert "financial_doc_classifier" not in self.engine.active_canaries

    def test_06_mutation_check_candidate_modifying_authority_or_cage_fails(self):
        """Rule 51: Improver cannot edit authority, budgets, policies, or cage code."""
        # 1. Prohibited keyword in payload
        with pytest.raises(CageIntegrityViolationError) as exc:
            self.engine.propose_candidate(
                target_type=OptimizationTargetType.PROMPT,
                target_name="system_prompt",
                proposed_payload={"bypass": "Disable kill_switch check on high spend"},
                baseline_id="v1",
            )
        assert "cannot mutate authority, budget, or cage component 'kill_switch'" in str(exc.value)

        # 2. Prohibited keyword in target name
        with pytest.raises(CageIntegrityViolationError) as exc:
            self.engine.propose_candidate(
                target_type=OptimizationTargetType.PROMPT,
                target_name="authority_matrix_optimizer",
                proposed_payload={"new_rule": "allow_all"},
                baseline_id="v1",
            )
        assert "cannot mutate authority, budget, or cage component 'authority'" in str(exc.value)
