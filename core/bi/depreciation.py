"""
Fixed Asset Depreciation Engine & Ledger Journal Integration
============================================================
Supports:
- Straight-Line Depreciation: (Cost - Salvage) / Useful Life
- Declining-Balance Depreciation: Book Value * Rate
- Sum-of-Years'-Digits (SYD) Depreciation
Generates balanced double-entry ledger journal entries.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class DepreciationScheduleEntry(BaseModel):
    year: int
    depreciation_expense: float
    accumulated_depreciation: float
    ending_book_value: float


class DepreciationSchedule(BaseModel):
    asset_id: str
    method: str  # 'STRAIGHT_LINE', 'DECLINING_BALANCE', 'SUM_OF_YEARS_DIGITS'
    initial_cost: float
    salvage_value: float
    useful_life_years: int
    annual_entries: List[DepreciationScheduleEntry]


class LedgerJournalEntry(BaseModel):
    journal_id: str
    date: str
    asset_id: str
    debit_account: str = "6000_Depreciation_Expense"
    debit_amount: float
    credit_account: str = "1500_Accumulated_Depreciation"
    credit_amount: float
    is_balanced: bool = True


class AssetDepreciationEngine:
    """Calculates multi-method asset depreciation schedules and journal entries."""

    @staticmethod
    def calculate_straight_line(asset_id: str, cost: float, salvage: float, useful_life_years: int) -> DepreciationSchedule:
        if useful_life_years <= 0 or cost <= salvage:
            raise ValueError("Invalid asset cost or useful life")

        depreciable_base = cost - salvage
        annual_expense = round(depreciable_base / useful_life_years, 2)

        entries: List[DepreciationScheduleEntry] = []
        accum = 0.0
        book_val = cost

        for y in range(1, useful_life_years + 1):
            accum = round(accum + annual_expense, 2)
            book_val = round(cost - accum, 2)
            entries.append(DepreciationScheduleEntry(
                year=y,
                depreciation_expense=annual_expense,
                accumulated_depreciation=accum,
                ending_book_value=book_val
            ))

        return DepreciationSchedule(
            asset_id=asset_id,
            method="STRAIGHT_LINE",
            initial_cost=cost,
            salvage_value=salvage,
            useful_life_years=useful_life_years,
            annual_entries=entries
        )

    @staticmethod
    def calculate_declining_balance(asset_id: str, cost: float, salvage: float, useful_life_years: int, factor: float = 2.0) -> DepreciationSchedule:
        rate = factor / useful_life_years
        entries: List[DepreciationScheduleEntry] = []
        accum = 0.0
        book_val = cost

        for y in range(1, useful_life_years + 1):
            expense = round(book_val * rate, 2)
            # Ensure not depreciating below salvage value
            if book_val - expense < salvage:
                expense = max(0.0, round(book_val - salvage, 2))

            accum = round(accum + expense, 2)
            book_val = round(cost - accum, 2)
            entries.append(DepreciationScheduleEntry(
                year=y,
                depreciation_expense=expense,
                accumulated_depreciation=accum,
                ending_book_value=book_val
            ))

        return DepreciationSchedule(
            asset_id=asset_id,
            method="DECLINING_BALANCE",
            initial_cost=cost,
            salvage_value=salvage,
            useful_life_years=useful_life_years,
            annual_entries=entries
        )

    @staticmethod
    def calculate_sum_of_years_digits(asset_id: str, cost: float, salvage: float, useful_life_years: int) -> DepreciationSchedule:
        depreciable_base = cost - salvage
        syd = (useful_life_years * (useful_life_years + 1)) / 2.0

        entries: List[DepreciationScheduleEntry] = []
        accum = 0.0

        for y in range(1, useful_life_years + 1):
            fraction = (useful_life_years - y + 1) / syd
            expense = round(depreciable_base * fraction, 2)
            accum = round(accum + expense, 2)
            book_val = round(cost - accum, 2)
            entries.append(DepreciationScheduleEntry(
                year=y,
                depreciation_expense=expense,
                accumulated_depreciation=accum,
                ending_book_value=book_val
            ))

        return DepreciationSchedule(
            asset_id=asset_id,
            method="SUM_OF_YEARS_DIGITS",
            initial_cost=cost,
            salvage_value=salvage,
            useful_life_years=useful_life_years,
            annual_entries=entries
        )

    @staticmethod
    def generate_monthly_journal_entry(asset_id: str, annual_expense: float, month_date: str) -> LedgerJournalEntry:
        import uuid
        monthly = round(annual_expense / 12.0, 2)
        return LedgerJournalEntry(
            journal_id=f"jrn_{uuid.uuid4().hex[:10]}",
            date=month_date,
            asset_id=asset_id,
            debit_account="6000_Depreciation_Expense",
            debit_amount=monthly,
            credit_account="1500_Accumulated_Depreciation",
            credit_amount=monthly,
            is_balanced=True
        )
