"""
Unit and Integration Tests for Sub-Step 6J: Evolution Safety, Red Team & Step 6 Qualification.
"""

import pytest
from core.evolution.safety import (
    EvolutionSafetyEngine,
    TripwireManager,
    EvalDriftMonitor,
    EvolutionJournal,
    EvolutionSuspendedError,
    TripwireBreachError,
    EvaluationDriftDetectedError,
)
from scripts.step6_redteam import Step6RedTeamRunner
from scripts.step6_scenario import Step6ScenarioRunner


class TestStep6Qualification:

    def test_01_evolution_kill_switch_blocks_operations(self):
        """Kill switch halts all autonomous evolution across global and company scopes."""
        safety = EvolutionSafetyEngine()
        assert safety.is_evolution_enabled("company_acme") is True

        # Activate global kill switch
        safety.activate_kill_switch(scope="GLOBAL", actor_principal="human:admin", reason="Safety audit")
        assert safety.is_evolution_enabled("company_acme") is False

        with pytest.raises(EvolutionSuspendedError):
            safety.check_evolution_permitted("company_acme")

        # Deactivate global with owner principal
        safety.deactivate_kill_switch(scope="GLOBAL", actor_principal="owner:sukhraj")
        assert safety.is_evolution_enabled("company_acme") is True

        # Per-company kill switch
        safety.activate_kill_switch(scope="company_acme", actor_principal="human:admin")
        assert safety.is_evolution_enabled("company_acme") is False
        assert safety.is_evolution_enabled("company_beta") is True

    def test_02_tripwire_manager_suspends_evolution_on_protected_path_write(self):
        """AI attempting to write protected path triggers tripwire and immediately suspends company evolution."""
        safety = EvolutionSafetyEngine()
        tripwire = TripwireManager(safety)

        # Non-protected path write succeeds
        tripwire.check_write_attempt(
            target_path="core/evolution/optimizer.py",
            actor_principal="agent:improver",
            company_id="comp_1",
        )

        # Protected path write trips wire
        with pytest.raises(TripwireBreachError) as exc_info:
            tripwire.check_write_attempt(
                target_path="security/protected_paths.yaml",
                actor_principal="agent:improver",
                company_id="comp_1",
            )
        assert "Tripwire Breach" in str(exc_info.value)
        assert safety.is_evolution_enabled("comp_1") is False

    def test_03_eval_drift_monitor_flags_safety_or_accuracy_drop(self):
        """Evaluation drift monitor strictly enforces the safety floor and accuracy tolerance."""
        baseline = {"safety_pass_rate": 1.0, "task_accuracy": 0.90}

        # Candidate with dropped safety fails immediately (Rule 52)
        with pytest.raises(EvaluationDriftDetectedError) as exc_info:
            EvalDriftMonitor.evaluate_drift(
                baseline,
                {"safety_pass_rate": 0.95, "task_accuracy": 0.95},
            )
        assert "Safety floor breached" in str(exc_info.value)

        # Candidate with acceptable drift passes
        res = EvalDriftMonitor.evaluate_drift(
            baseline,
            {"safety_pass_rate": 1.0, "task_accuracy": 0.88},  # 2% delta <= 5% tolerance
        )
        assert res["drift_detected"] is False

        # Candidate with excessive regression (> 5%) fails
        with pytest.raises(EvaluationDriftDetectedError):
            EvalDriftMonitor.evaluate_drift(
                baseline,
                {"safety_pass_rate": 1.0, "task_accuracy": 0.82},  # 8% delta > 5% tolerance
            )

    def test_04_evolution_journal_logs_events_and_generates_weekly_digest(self):
        """Evolution journal records changes and formats human-readable weekly digests."""
        journal = EvolutionJournal()
        journal.record_evolution(
            change_class="PROMPT_OPT",
            target_name="support_triage_prompt",
            rationale="Clarify routing for billing issues",
            measured_effect={"accuracy_gain": "+4.2%"},
            rollback_id="rb_9812",
            company_id="comp_acme",
        )

        digest = journal.generate_weekly_digest("comp_acme")
        assert "Weekly Evolution Journal (Company: comp_acme)" in digest
        assert "[PROMPT_OPT] support_triage_prompt" in digest
        assert "Clarify routing for billing issues" in digest
        assert "rb_9812" in digest

    def test_05_redteam_suite_executes_and_neutralizes_all_adversarial_drills(self):
        """All 5 adversarial red-team drills are executed and neutralized."""
        runner = Step6RedTeamRunner()
        success = runner.run_all_drills()
        assert success is True
        assert len(runner.results) == 5
        assert all(r["status"] == "BLOCKED" for r in runner.results)

    def test_06_step6_qualification_scenario_runs_all_10_phases_successfully(self):
        """Complete 10-phase qualification drill runs from preflight to safety shutdown."""
        scenario = Step6ScenarioRunner()
        success = scenario.run_all_phases()
        assert success is True

    def test_07_mutation_check_unauthorized_kill_switch_deactivation_blocked(self):
        """Only human owner accounts can deactivate the evolution kill switch."""
        safety = EvolutionSafetyEngine()
        safety.activate_kill_switch(scope="GLOBAL", actor_principal="human:admin")

        # Non-owner principal cannot deactivate
        with pytest.raises(PermissionError):
            safety.deactivate_kill_switch(scope="GLOBAL", actor_principal="agent:optimizer")

        with pytest.raises(PermissionError):
            safety.deactivate_kill_switch(scope="GLOBAL", actor_principal="human:admin")

        # Owner succeeds
        safety.deactivate_kill_switch(scope="GLOBAL", actor_principal="owner:sukhraj")
        assert safety.is_evolution_enabled() is True
