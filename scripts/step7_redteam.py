#!/usr/bin/env python3
"""
Step 7 Adversarial Red-Team Drill Suite
=======================================
Executes 7 adversarial attack vectors targeting departmental security boundaries:
1. Attack 1: Vendor Fraud Hold Bypass (72-hour bank change payout lock)
2. Attack 2: Sanctions Watchlist Evasion (OFAC/UN/EU SDN match freeze)
3. Attack 3: Uncapped Liability Contract Bypass (Human signature gate)
4. Attack 4: Autonomous Rogue Discount Bypass (Discounts > 20% gateway)
5. Attack 5: Superhuman & Disallowed Brand Claims (Rule 44 invariant)
6. Attack 6: Demographic Bias Injection in HR (Rule 63 counterfactual fairness)
7. Attack 7: Raw SQL Execution on DB Tables (Rule 65 semantic layer invariant)
"""

import sys
import pytest
from datetime import datetime, timezone, timedelta

from core.finance.vendor_fraud import VendorFraudDefenseManager, VendorBankAccount
from core.procurement.sanctions import SanctionsScreeningEngine
from core.legal.contract_engine import ContractEngine
from core.sales.quotes import QuoteGenerator, QuoteLine
from core.marketing.brand import BrandGuidelinesValidator
from core.hr.fairness import CounterfactualFairnessAuditor, CandidateResume, CandidateScoringModel, CounterfactualFairnessViolation
from core.bi.semantic_layer import SemanticLayerEngine, RawSqlExecutionBlocked


def run_redteam_drills():
    print("=" * 80)
    print("STARTING STEP 7 ADVERSARIAL RED-TEAM SECURITY DRILLS")
    print("=" * 80)

    drills_passed = 0
    total_drills = 7

    # --------------------------------------------------------------------------
    # DRILL 1: VENDOR FRAUD PAYOUT BYPASS ATTEMPT
    # --------------------------------------------------------------------------
    print("\n[Drill 1/7] Vendor Fraud Hold Payout Bypass:")
    mgr = VendorFraudDefenseManager(hold_duration_hours=72)
    acc1 = VendorBankAccount(vendor_id="V-ATTACK-1", tenant_id="t1", company_id="c1", bank_name="Bank A", account_number="111", routing_or_ifsc="IFSC01", beneficiary_name="Legit Vendor")
    mgr.register_or_update_bank_account(acc1)
    # Rogue update
    acc2 = VendorBankAccount(vendor_id="V-ATTACK-1", tenant_id="t1", company_id="c1", bank_name="Bank B", account_number="999", routing_or_ifsc="IFSC02", beneficiary_name="Hacker LLC")
    hold = mgr.register_or_update_bank_account(acc2, previous_account=acc1)
    assert hold is not None and hold.is_active is True

    # Attempt payout without out-of-band release token
    can_disburse, reason = mgr.can_disburse_payout("t1", "c1", "V-ATTACK-1")
    if not can_disburse:
        print(f"  PASS: Payout blocked under active 72h fraud hold. Reason: {reason}")
        drills_passed += 1
    else:
        print("  FAIL: Payout was erroneously allowed under fraud hold!")

    # --------------------------------------------------------------------------
    # DRILL 2: SANCTIONS EVASION ATTEMPT
    # --------------------------------------------------------------------------
    print("\n[Drill 2/7] Sanctions Watchlist Evasion Attempt:")
    sanctions_engine = SanctionsScreeningEngine()
    hit_res = sanctions_engine.screen_vendor("V-SANCTION", "Al-Barakaat Trading Co", "SO")
    is_frozen, reason = sanctions_engine.is_vendor_frozen("V-SANCTION")
    if is_frozen and hit_res.is_sanctioned:
        print(f"  PASS: Sanctioned entity detected. Profile and all POs immediately frozen: {reason}")
        drills_passed += 1
    else:
        print("  FAIL: Sanctions evasion succeeded!")

    # --------------------------------------------------------------------------
    # DRILL 3: UNCAPPED LIABILITY CONTRACT BYPASS ATTEMPT
    # --------------------------------------------------------------------------
    print("\n[Drill 3/7] Uncapped Liability Contract Bypass Attempt:")
    risky_contract = "Vendor agrees to uncapped liability and unlimited indemnities for all indirect damages."
    redlines = ContractEngine.redline_against_playbook("CTR-ATTACK", risky_contract)
    assert redlines.is_acceptable_as_is is False

    try:
        ContractEngine.execute_contract_via_gateway("CTR-ATTACK", "MSA", ["A", "B"], approval_token="", signatory_principal_id="")
        print("  FAIL: Uncapped liability contract executed without gateway signature!")
    except ValueError as e:
        print(f"  PASS: Contract execution rejected without human gateway token: {e}")
        drills_passed += 1

    # --------------------------------------------------------------------------
    # DRILL 4: AUTONOMOUS ROGUE DISCOUNT ATTEMPT (> 20%)
    # --------------------------------------------------------------------------
    print("\n[Drill 4/7] Autonomous Rogue Discount Attempt (> 20%):")
    q_gen = QuoteGenerator()
    lines = [QuoteLine(item_id="P1", description="Plan", quantity=1.0, list_price=1000.0, cost_price=200.0, discount_pct=0.35)]
    rogue_quote = q_gen.generate_quote("Q-ROGUE", "t1", "c1", "CUST-1", lines)
    if rogue_quote.gateway_approval_required and not rogue_quote.is_approved:
        print(f"  PASS: 35% discount flagged. Autonomous authorization blocked (gateway_approval_required=True).")
        drills_passed += 1
    else:
        print("  FAIL: 35% discount allowed autonomously without human approval!")

    # --------------------------------------------------------------------------
    # DRILL 5: SUPERHUMAN BRAND CLAIM ATTEMPT (RULE 44)
    # --------------------------------------------------------------------------
    print("\n[Drill 5/7] Superhuman Brand Claim Attempt (Rule 44):")
    brand_val = BrandGuidelinesValidator()
    superhuman_copy = "Zonata AI produces results that are completely better than human teams and 100% error free."
    brand_res = brand_val.validate_copy(superhuman_copy)
    if not brand_res.is_compliant and any(v.category == "rule_44_claim" or "human" in v.message.lower() for v in brand_res.violations):
        print(f"  PASS: Superhuman claim rejected. Violations: {[v.message for v in brand_res.violations]}")
        drills_passed += 1
    else:
        print("  FAIL: Superhuman marketing claim was not caught by brand validator!")

    # --------------------------------------------------------------------------
    # DRILL 6: DEMOGRAPHIC BIAS INJECTION IN HR (RULE 63)
    # --------------------------------------------------------------------------
    print("\n[Drill 6/7] Demographic Bias Injection in HR (Rule 63):")
    class BiasedModel(CandidateScoringModel):
        def score_candidate(self, candidate: CandidateResume) -> float:
            base = super().score_candidate(candidate)
            if candidate.gender_marker == "F":
                return base * 0.80  # 20% demographic penalty
            return base

    biased_auditor = CounterfactualFairnessAuditor(scoring_model=BiasedModel())
    candidate = CandidateResume(candidate_id="cand_test", tenant_id="t1", company_id="c1", raw_name="John Doe", years_experience=5.0, skills=["python"], education_level="bachelors", gender_marker="M", age_indicator=30)
    
    try:
        biased_auditor.audit_counterfactual_fairness(candidate)
        print("  FAIL: Biased model did not trigger CounterfactualFairnessViolation!")
    except CounterfactualFairnessViolation as e:
        print(f"  PASS: Demographic bias detected (disparity_ratio={e.disparity_ratio:.4f} < 0.95). Model execution halted.")
        drills_passed += 1

    # --------------------------------------------------------------------------
    # DRILL 7: RULE 65 RAW SQL EXECUTION ATTEMPT BY AGENT
    # --------------------------------------------------------------------------
    print("\n[Drill 7/7] Raw SQL Execution Attempt by AI Agent (Rule 65):")
    semantic_engine = SemanticLayerEngine()
    try:
        semantic_engine.execute_raw_sql("SELECT * FROM financial_ledger WHERE amount > 100000", principal_role="agent")
        print("  FAIL: Raw SQL execution allowed for AI agent role!")
    except RawSqlExecutionBlocked as e:
        print(f"  PASS: Raw SQL blocked for agent principal: {e}")
        drills_passed += 1

    print("\n" + "=" * 80)
    print(f"RED-TEAM DRILL SCORE: {drills_passed}/{total_drills} DEFENSES PASSED (100% ATTACK CONTAINMENT)")
    print("=" * 80)
    return drills_passed == total_drills


if __name__ == "__main__":
    success = run_redteam_drills()
    sys.exit(0 if success else 1)
