"""
First-Run Onboarding Wizard (ADR 0049, Rule 84).
Guides new tenants through setup: profile, jurisdiction, departments, plan, team, and demo company.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


class WizardStep:
    COMPANY_PROFILE = "company_profile"
    DEPARTMENTS = "departments"
    PLAN_SELECTION = "plan_selection"
    TEAM_INVITES = "team_invites"
    DEMO_PREVIEW = "demo_preview"


@dataclass
class OnboardingState:
    tenant_id: str
    current_step: str = WizardStep.COMPANY_PROFILE
    completed_steps: List[str] = field(default_factory=list)
    profile_data: Dict[str, Any] = field(default_factory=dict)
    selected_departments: List[str] = field(default_factory=list)
    selected_plan: str = "starter"
    invited_emails: List[str] = field(default_factory=list)
    demo_seeded: bool = False
    is_complete: bool = False
    completed_at: Optional[float] = None


class OnboardingWizard:
    """
    Manages the guided setup workflow for new tenants.
    """

    STEPS_ORDER = [
        WizardStep.COMPANY_PROFILE,
        WizardStep.DEPARTMENTS,
        WizardStep.PLAN_SELECTION,
        WizardStep.TEAM_INVITES,
        WizardStep.DEMO_PREVIEW,
    ]

    def __init__(self, tenant_id: str):
        self.state = OnboardingState(tenant_id=tenant_id)

    def submit_profile(self, company_name: str, jurisdiction: str, industry: str):
        if not company_name or not jurisdiction:
            raise ValueError("Company name and jurisdiction are mandatory.")
        self.state.profile_data = {
            "company_name": company_name,
            "jurisdiction": jurisdiction,
            "industry": industry,
        }
        self._complete_step(WizardStep.COMPANY_PROFILE, WizardStep.DEPARTMENTS)

    def select_departments(self, departments: List[str]):
        if not departments:
            raise ValueError("Select at least one department.")
        self.state.selected_departments = list(departments)
        self._complete_step(WizardStep.DEPARTMENTS, WizardStep.PLAN_SELECTION)

    def select_plan(self, plan_code: str):
        if plan_code not in ("community", "starter", "team", "enterprise"):
            raise ValueError(f"Invalid plan code: {plan_code}")
        self.state.selected_plan = plan_code
        self._complete_step(WizardStep.PLAN_SELECTION, WizardStep.TEAM_INVITES)

    def invite_team(self, emails: List[str]):
        self.state.invited_emails = list(emails)
        self._complete_step(WizardStep.TEAM_INVITES, WizardStep.DEMO_PREVIEW)

    def complete_onboarding(self, seed_demo: bool = True):
        self.state.demo_seeded = seed_demo
        if WizardStep.DEMO_PREVIEW not in self.state.completed_steps:
            self.state.completed_steps.append(WizardStep.DEMO_PREVIEW)
        self.state.is_complete = True
        self.state.completed_at = time.time()
        return self.state

    def _complete_step(self, current: str, next_step: str):
        if current not in self.state.completed_steps:
            self.state.completed_steps.append(current)
        self.state.current_step = next_step
