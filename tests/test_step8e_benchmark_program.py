"""
Tests for Sub-Step 8E: Human-Baseline Benchmark Program (Rule 67, 68, 69, 71, ADR 0045, ADR 0046)
Validates Benchmark Vault encryption, ACLs, consent-driven telemetry recorder, PII scrubber,
external calibration adapters with spend caps, and the governed claims registry.
"""

import pytest
import os
from pathlib import Path

from core.benchmarks.vault import (
    BenchmarkVault,
    BenchmarkVaultAccessDeniedError,
    BenchmarkTamperError,
)
from core.benchmarks.recorder import (
    HumanBaselineRecorder,
    ParticipantConsentMissingError,
)
from core.benchmarks.calibration import (
    SpendCapEnforcer,
    EvaluationBudgetExceededError,
    TheAgentCompanyAdapter,
    GDPvalAdapter,
    RemoteLaborIndexAdapter,
)
from core.benchmarks.claims import (
    BenchmarkClaim,
    BenchmarkClaimsRegistry,
    UnverifiedClaimBlockedError,
)


class TestStep8EBenchmarkProgram:

    # 1. Methodology Specification
    def test_01_methodology_doc_configurations_and_rules(self):
        method_path = Path("docs/benchmarks/HUMAN_BASELINE_METHOD.md")
        assert method_path.exists()
        content = method_path.read_text(encoding="utf-8")
        assert "Config A" in content
        assert "Config B" in content
        assert "Config C" in content
        assert "Config D" in content
        assert "Rule of Claim Equivalence" in content
        assert "Critical Safety Violation Rate" in content
        assert "Minimum Sample Size ($N$):** $N \\ge 30$" in content or "N >= 30" in content or "N \\ge 30" in content

    # 2. Benchmark Vault Encryption, ACLs, and Tamper Detection
    def test_02_vault_encryption_acls_and_tamper_detection(self):
        vault = BenchmarkVault()

        # Setup roles
        vault.assign_role("author-alice", "BENCHMARK_AUTHOR")
        vault.assign_role("eval-bob", "BENCHMARK_EVALUATOR")
        vault.assign_role("guest-charlie", "AUDITOR")

        # Author stores golden task
        task_data = {
            "task_id": "GOLD-INVOICE-001",
            "industry": "C28",
            "prompt": "Reconcile discrete manufacturing PO #9982 against delivery note",
            "ground_truth_total_minor": 4500000,
        }
        digest = vault.store_golden_task("GOLD-INVOICE-001", task_data, principal_id="author-alice")
        assert len(digest) == 64

        # Evaluator can retrieve and decrypt
        retrieved = vault.retrieve_golden_task("GOLD-INVOICE-001", principal_id="eval-bob")
        assert retrieved["ground_truth_total_minor"] == 4500000

        # Unauthorized write attempt raises BenchmarkVaultAccessDeniedError
        with pytest.raises(BenchmarkVaultAccessDeniedError):
            vault.store_golden_task("GOLD-HACK-001", {"malicious": True}, principal_id="eval-bob")

        # Tampering with ciphertext causes MAC verification failure
        raw_sealed = vault._golden_tasks["GOLD-INVOICE-001"]
        original_envelope = raw_sealed["encrypted_envelope"]
        # Corrupt one character in ciphertext
        raw_sealed["encrypted_envelope"] = original_envelope[:-2] + "AA"

        with pytest.raises(BenchmarkTamperError):
            vault.retrieve_golden_task("GOLD-INVOICE-001", principal_id="eval-bob")

    # 3. Baseline Recorder Consent Safeguard
    def test_03_baseline_recorder_requires_consent(self):
        recorder = HumanBaselineRecorder()

        # Without consent -> raises ParticipantConsentMissingError
        with pytest.raises(ParticipantConsentMissingError) as exc:
            recorder.start_session(
                session_id="SESS-001",
                real_participant_id="dr_john_doe_cpa",
                task_id="GOLD-INVOICE-001",
                domain_code="C28",
                consent_given=False
            )
        assert "PARTICIPANT_CONSENT_MISSING" in str(exc.value)

        # With explicit consent -> initiates recording
        res = recorder.start_session(
            session_id="SESS-001",
            real_participant_id="dr_john_doe_cpa",
            task_id="GOLD-INVOICE-001",
            domain_code="C28",
            consent_given=True
        )
        assert res["status"] == "RECORDING"
        assert res["pseudo_participant_id"].startswith("PSEUDO-")
        assert "dr_john_doe" not in res["pseudo_participant_id"]

    # 4. Telemetry Logging and PII Scrubbing
    def test_04_telemetry_scrubbing_and_session_completion(self):
        recorder = HumanBaselineRecorder()
        recorder.start_session("SESS-002", "sarah_finance_mgr", "GOLD-002", "G47", consent_given=True)

        # Log action containing PII and password
        dirty_input = "User sarah@company.com reviewed PO for account with password secret123 and card 4111-2222-3333-4444"
        recorder.log_action("SESS-002", "INVOICE_INSPECT", dirty_input)

        session = recorder.complete_session("SESS-002", is_success=True, error_count=0)
        assert session["status"] == "COMPLETED"
        assert session["actions_count"] == 1
        assert "session_seal_sha256" in session

        logged_text = session["action_log"][0]["payload_scrubbed"]
        assert "sarah@company.com" not in logged_text
        assert "[REDACTED_EMAIL]" in logged_text
        assert "secret123" not in logged_text
        assert "4111-2222-3333-4444" not in logged_text

    # 5. External Calibration Adapters
    def test_05_external_calibration_adapters(self):
        enforcer = SpendCapEnforcer(campaign_id="CAMP-2026-Q4", spend_cap_usd=25.0)

        # TheAgentCompany
        tac = TheAgentCompanyAdapter(spend_enforcer=enforcer)
        tac_res = tac.evaluate_task("manage_purchase_order_approval", complexity_tier="T2")
        assert tac_res["benchmark"] == "TheAgentCompany"
        assert tac_res["score"] == 0.94

        # GDPval
        gdp = GDPvalAdapter(spend_enforcer=enforcer)
        gdp_res = gdp.evaluate_economic_task("contract_review", runs=3)
        assert gdp_res["benchmark"] == "GDPval_WorkArena"
        assert gdp_res["runs_evaluated"] == 3

        # Remote Labor Index
        rli = RemoteLaborIndexAdapter(spend_enforcer=enforcer)
        rli_res = rli.calibrate_cost_and_speed(
            task_category="AP_INVOICE_RECONCILIATION",
            human_median_minutes=15.0,  # 15 mins for human ($8.75)
            system_seconds=12.0,        # 12 seconds for Zonata
            system_cost_minor=25        # $0.25
        )
        assert rli_res["speedup_factor"] == 75.0
        assert rli_res["cost_savings_percent"] > 90.0

    # 6. Evaluation Spend Cap Ceiling
    def test_06_spend_cap_ceiling_enforced(self):
        tight_enforcer = SpendCapEnforcer(campaign_id="TIGHT-BUDGET", spend_cap_usd=1.0)
        tac = TheAgentCompanyAdapter(spend_enforcer=tight_enforcer)

        # Two T2 evaluations ($0.35 * 2 = $0.70) pass
        tac.evaluate_task("task_1", "T2")
        tac.evaluate_task("task_2", "T2")
        assert tight_enforcer.current_spend_usd == pytest.approx(0.70, 0.01)

        # Third T2 evaluation ($0.70 + $0.35 = $1.05 > $1.00) raises EvaluationBudgetExceededError
        with pytest.raises(EvaluationBudgetExceededError) as exc:
            tac.evaluate_task("task_3", "T2")
        assert "EVALUATION_BUDGET_EXCEEDED" in str(exc.value)

    # 7. Governed Claims Registry - Valid Claim
    def test_07_governed_claims_registry_valid_claim(self):
        registry = BenchmarkClaimsRegistry()

        claim = BenchmarkClaim(
            claim_id="CLAIM-2026-INV-001",
            statement="Zonata Autonomous Accounts Payable reconciles multi-line invoices 4.2x faster than unassisted human professionals with 99.2% accuracy.",
            benchmark_run_id="RUN-SEALED-20261124-001",
            configuration_comparison="C_VS_A",
            sample_size=60,  # N >= 30
            effect_size_d=1.45,
            ci_95=(1.20, 1.70),
            critical_safety_violations=0,
            approved_by_lead="PRINCIPAL-RESEARCHER-01"
        )

        record = registry.register_claim(claim)
        assert record["status"] == "EMPIRICALLY_VERIFIED"
        assert "claim_seal_sha256" in record
        assert registry.get_verified_claim("CLAIM-2026-INV-001")["sample_size"] == 60

    # 8. Governed Claims Registry - Invalid Comparisons Blocked
    def test_08_claims_registry_blocks_config_b_and_small_n(self):
        registry = BenchmarkClaimsRegistry()

        # Case 1: Prohibited comparison against Config B (Unassisted AI)
        invalid_comp_claim = BenchmarkClaim(
            claim_id="CLAIM-BAD-COMP",
            statement="Zonata is 10x better than raw GPT-4",
            benchmark_run_id="RUN-002",
            configuration_comparison="C_VS_B",  # Invalid under Rule 69
            sample_size=50,
            effect_size_d=2.1,
            ci_95=(1.8, 2.4),
            critical_safety_violations=0
        )
        with pytest.raises(UnverifiedClaimBlockedError) as exc:
            registry.register_claim(invalid_comp_claim)
        assert "mandates comparison against unassisted human baseline" in str(exc.value)

        # Case 2: Under-sampled claim (N < 30)
        small_sample_claim = BenchmarkClaim(
            claim_id="CLAIM-SMALL-N",
            statement="Zonata speedup on 10 trials",
            benchmark_run_id="RUN-003",
            configuration_comparison="C_VS_A",
            sample_size=12,  # N < 30
            effect_size_d=1.1,
            ci_95=(0.5, 1.7),
            critical_safety_violations=0
        )
        with pytest.raises(UnverifiedClaimBlockedError) as exc:
            registry.register_claim(small_sample_claim)
        assert "Minimum sample size N >= 30 is required" in str(exc.value)

        # Case 3: Critical Safety Violation Veto
        unsafe_claim = BenchmarkClaim(
            claim_id="CLAIM-UNSAFE",
            statement="Fast clinical billing automation",
            benchmark_run_id="RUN-004",
            configuration_comparison="C_VS_A",
            sample_size=40,
            effect_size_d=1.5,
            ci_95=(1.2, 1.8),
            critical_safety_violations=1  # Non-zero!
        )
        with pytest.raises(UnverifiedClaimBlockedError) as exc:
            registry.register_claim(unsafe_claim)
        assert "critical safety violations" in str(exc.value)
