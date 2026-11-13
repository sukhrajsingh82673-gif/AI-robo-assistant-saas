"""
ZONATA — Company Setup (Stages 1-6)

A dedicated, tenant-scoped company lifecycle module. It deliberately sits
beside ``core/portfolio.py`` instead of replacing it: the portfolio manager
keeps owning operating context, while this package owns the company record
lifecycle (draft -> creating/onboarding -> operational -> deletion), the
company-scoped permission model, drafts, connections and the audit trail.

Nothing in this package fabricates success. Features that are not wired to a
real provider return an explicit ``stub``/``simulated`` marker.
"""

from core.company_setup.service import CompanySetupService, CompanySetupError
from core.company_setup.status import CompanyStatus, InvalidTransition

__all__ = [
    "CompanySetupService",
    "CompanySetupError",
    "CompanyStatus",
    "InvalidTransition",
]
