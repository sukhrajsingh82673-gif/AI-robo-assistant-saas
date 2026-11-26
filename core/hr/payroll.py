"""
Deterministic Statutory Payroll Engine
======================================
Adheres to:
- Rule 61: Statutory Content as Cited Data (rates loaded from packs/regions/india/payroll_rules.json)
- Deterministic calculation of Gross, EPF, ESIC, Professional Tax, TDS, and Net Pay.
"""

import os
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAYROLL_RULES_PATH = os.path.join(REPO_ROOT, "packs", "regions", "india", "payroll_rules.json")


def load_payroll_statutory_pack() -> Dict[str, Any]:
    with open(PAYROLL_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class PayrollSlip(BaseModel):
    employee_id: str
    month: str  # YYYY-MM
    currency: str = "INR"
    gross_pay: float
    basic_pay: float
    hra: float
    special_allowance: float
    epf_employee: float
    epf_employer: float
    esic_employee: float
    esic_employer: float
    professional_tax: float
    tds_deduction: float
    total_deductions: float
    net_pay: float


class DeterministicPayrollEngine:
    """Calculates employee monthly payroll according to cited statutory rules."""

    def __init__(self):
        self.pack = load_payroll_statutory_pack()
        self.rates = self.pack["rates"]

    def compute_monthly_payroll(
        self,
        employee_id: str,
        month: str,
        monthly_gross: float,
        annual_tds_estimated: float = 0.0
    ) -> PayrollSlip:
        # Salary Structure: Basic (50%), HRA (30%), Special Allowance (20%)
        basic_pay = round(monthly_gross * 0.50, 2)
        hra = round(monthly_gross * 0.30, 2)
        special_allowance = round(monthly_gross - (basic_pay + hra), 2)

        # 1. EPF (Employee Provident Fund: 12% of basic, capped at ceiling if basic > ceiling)
        epf_wage_base = min(basic_pay, self.rates["epf_wage_ceiling_inr"])
        epf_employee = round(epf_wage_base * self.rates["epf_employee_pct"], 2)
        epf_employer = round(epf_wage_base * self.rates["epf_employer_pct"], 2)

        # 2. ESIC (Applicable only if monthly gross <= 21,000 INR)
        if monthly_gross <= self.rates["esic_wage_ceiling_inr"]:
            esic_employee = round(monthly_gross * self.rates["esic_employee_pct"], 2)
            esic_employer = round(monthly_gross * self.rates["esic_employer_pct"], 2)
        else:
            esic_employee = 0.0
            esic_employer = 0.0

        # 3. Professional Tax (Standard 200 INR / month)
        pt = self.rates["professional_tax_monthly_inr"]

        # 4. TDS (Monthly fraction of annual estimate)
        monthly_tds = round(annual_tds_estimated / 12.0, 2)

        total_deductions = round(epf_employee + esic_employee + pt + monthly_tds, 2)
        net_pay = round(monthly_gross - total_deductions, 2)

        return PayrollSlip(
            employee_id=employee_id,
            month=month,
            gross_pay=monthly_gross,
            basic_pay=basic_pay,
            hra=hra,
            special_allowance=special_allowance,
            epf_employee=epf_employee,
            epf_employer=epf_employer,
            esic_employee=esic_employee,
            esic_employer=esic_employer,
            professional_tax=pt,
            tds_deduction=monthly_tds,
            total_deductions=total_deductions,
            net_pay=net_pay
        )
