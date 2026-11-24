"""
Unit & Contract Tests for Step 7F: Human Resources & Workforce Operations.
==========================================================================
"""

import pytest
from core.hr.recruiting import RecruitingManager, CandidateResume, InclusiveLanguageLinter
from core.hr.fairness import (
    CounterfactualFairnessAuditor, CandidateScoringModel, CounterfactualFairnessViolation
)
from core.hr.lifecycle import Employee, EmployeeLifecycleManager
from core.hr.payroll import DeterministicPayrollEngine
from core.hr.offboarding import OffboardingManager


# --- 1. RECRUITING & INCLUSIVE LANGUAGE TESTS ---

def test_01_recruiting_linter_and_salary_transparency():
    # 1. Biased job description detected
    biased_desc = "We are seeking a rockstar developer with a killer instinct to dominate our competition."
    passed, warnings = InclusiveLanguageLinter.lint_job_description(biased_desc)
    assert passed is False
    assert len(warnings) >= 2

    # 2. Compliant job description passes
    clean_desc = "We are seeking a senior software engineer to build scalable distributed systems and collaborate with cross-functional teams."
    c_passed, c_warnings = InclusiveLanguageLinter.lint_job_description(clean_desc)
    assert c_passed is True
    assert len(c_warnings) == 0

    # 3. Salary transparency enforcement (invalid range raises ValueError)
    with pytest.raises(ValueError):
        RecruitingManager.create_job_posting(
            "JOB-1", "t1", "c1", "Engineer", "Engineering", clean_desc,
            min_salary=0.0, max_salary=0.0  # Missing salary transparency
        )

    # Valid posting
    posting = RecruitingManager.create_job_posting(
        "JOB-2", "t1", "c1", "Engineer", "Engineering", clean_desc,
        min_salary=1500000.0, max_salary=2200000.0
    )
    assert posting.inclusive_lint_passed is True
    assert posting.min_salary == 1500000.0


# --- 2. RULE 63 COUNTERFACTUAL FAIRNESS TESTS ---

def test_02_counterfactual_fairness_passes_on_unbiased_model():
    base_candidate = CandidateResume(
        candidate_id="cand_alpha",
        tenant_id="t1",
        company_id="c1",
        raw_name="Aarav Sharma",
        years_experience=6.0,
        skills=["python", "temporal", "postgresql", "distributed_systems"],
        education_level="masters",
        gender_marker="M",
        age_indicator=29
    )

    auditor = CounterfactualFairnessAuditor()
    result = auditor.audit_counterfactual_fairness(base_candidate)

    # Rule 63: 100 demographic permutations audited
    assert result.audit_samples_count >= 100
    assert result.is_fair is True
    # Disparity ratio strictly within [0.95, 1.05]
    assert 0.95 <= result.min_disparity_ratio <= 1.05
    assert 0.95 <= result.max_disparity_ratio <= 1.05


def test_03_counterfactual_fairness_halts_on_biased_model():
    class BiasedModel(CandidateScoringModel):
        def score_candidate(self, candidate: CandidateResume) -> float:
            base = super().score_candidate(candidate)
            # Artificially inject demographic bias against specific gender or names
            if candidate.gender_marker == "F":
                return base * 0.85  # 15% penalty based on gender marker
            return base

    biased_auditor = CounterfactualFairnessAuditor(scoring_model=BiasedModel())
    candidate = CandidateResume(
        candidate_id="cand_test",
        tenant_id="t1",
        company_id="c1",
        raw_name="John Doe",
        years_experience=5.0,
        skills=["python", "sql"],
        education_level="bachelors",
        gender_marker="M",
        age_indicator=30
    )

    # Rule 63: Disparity outside [0.95, 1.05] MUST raise CounterfactualFairnessViolation
    with pytest.raises(CounterfactualFairnessViolation) as exc_info:
        biased_auditor.audit_counterfactual_fairness(candidate)

    assert exc_info.value.disparity_ratio < 0.95


# --- 3. EMPLOYEE LIFECYCLE & SALARY GATEWAY TESTS ---

def test_04_employee_lifecycle_and_salary_gateway():
    mgr = EmployeeLifecycleManager()
    emp = Employee(
        employee_id="EMP-101",
        tenant_id="t1",
        company_id="c1",
        full_name="Sarah Connor",
        email="s.connor@zonata.io",
        department_id="dept_ops",
        role_title="Operations Specialist",
        annual_salary=1200000.0,
        status="onboarding"
    )
    mgr.register_new_hire(emp)

    # Complete onboarding checklist
    mgr.complete_onboarding_step("t1", "c1", "EMP-101", "contract_signed")
    mgr.complete_onboarding_step("t1", "c1", "EMP-101", "equipment_provisioned")
    mgr.complete_onboarding_step("t1", "c1", "EMP-101", "sso_account_created")
    emp_active = mgr.complete_onboarding_step("t1", "c1", "EMP-101", "compliance_training_completed")

    assert emp_active.status == "active"

    # Salary change without gateway token fails (Rule 62)
    with pytest.raises(ValueError):
        mgr.apply_compensation_adjustment(
            "t1", "c1", "EMP-101", 1500000.0,
            approval_token="", authorizer_principal_id=""
        )

    # Salary change with gateway token succeeds
    updated = mgr.apply_compensation_adjustment(
        "t1", "c1", "EMP-101", 1500000.0,
        approval_token="GATEWAY-PAY-SIG-9900", authorizer_principal_id="hr_director_principal"
    )
    assert updated.annual_salary == 1500000.0


# --- 4. DETERMINISTIC PAYROLL ENGINE (RULE 61) ---

def test_05_deterministic_payroll_engine():
    engine = DeterministicPayrollEngine()

    # Case 1: Standard Employee (Monthly Gross = 100,000 INR)
    # Basic = 50,000, EPF wage ceiling is 15,000 -> EPF employee is 12% of 15,000 = 1,800
    # Gross > 21,000 ceiling -> ESIC is 0
    # PT = 200, TDS = 5,000 (annual 60,000)
    slip1 = engine.compute_monthly_payroll(
        employee_id="EMP-201",
        month="2026-10",
        monthly_gross=100000.0,
        annual_tds_estimated=60000.0
    )
    assert slip1.basic_pay == 50000.0
    assert slip1.epf_employee == 1800.0
    assert slip1.esic_employee == 0.0
    assert slip1.professional_tax == 200.0
    assert slip1.tds_deduction == 5000.0
    assert slip1.total_deductions == 7000.0
    assert slip1.net_pay == 93000.0

    # Case 2: Entry-level Employee below ESIC ceiling (Monthly Gross = 20,000 INR)
    # Basic = 10,000. EPF = 12% of 10,000 = 1,200.
    # Gross <= 21,000 -> ESIC is 0.75% of 20,000 = 150.
    slip2 = engine.compute_monthly_payroll(
        employee_id="EMP-202",
        month="2026-10",
        monthly_gross=20000.0,
        annual_tds_estimated=0.0
    )
    assert slip2.basic_pay == 10000.0
    assert slip2.epf_employee == 1200.0
    assert slip2.esic_employee == 150.0
    assert slip2.professional_tax == 200.0
    assert slip2.total_deductions == 1550.0
    assert slip2.net_pay == 18450.0


# --- 5. RAPID OFFBOARDING & SHA256 RECEIPT TESTS ---

def test_06_offboarding_checklist_and_audit_hash():
    mgr = OffboardingManager()
    sessions = ["sess_oidc_1", "sess_oidc_2"]
    leases = ["openbao_lease_kv_99", "openbao_lease_db_102"]
    roles = ["developer_role", "billing_viewer"]

    receipt = mgr.execute_complete_offboarding(
        employee_id="EMP-999",
        tenant_id="t1",
        company_id="c1",
        active_sessions=sessions,
        openbao_lease_ids=leases,
        db_roles=roles
    )

    assert receipt.is_fully_revoked is True
    assert receipt.revoked_sessions_count == 2
    assert receipt.revoked_leases_count == 2
    assert len(receipt.revoked_db_roles) == 2
    # Verify execution speed (< 60,000 ms SLA)
    assert receipt.execution_duration_ms < 60000.0
    # Cryptographic proof: 64 hex characters
    assert len(receipt.sha256_audit_hash) == 64
