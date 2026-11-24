"""
Campaign Lifecycle Engine
=========================
Manages campaign phases:
1. Brief creation
2. Creative copy generation
3. Automated Brand review (guidelines and claims)
4. Legal review gateway
5. Department budget commitment
6. Scheduled publication
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from core.departments.models import DepartmentBudget


class Campaign(BaseModel):
    campaign_id: str
    tenant_id: str
    company_id: str
    name: str
    channel: str  # 'google_ads', 'meta', 'linkedin', 'email'
    target_audience: str
    creative_copy: str
    budget_allocated: float
    stage: str = "brief"  # 'brief', 'creative', 'brand_approved', 'legal_approved', 'budget_committed', 'scheduled', 'active'
    brand_passed: bool = False
    legal_approved: bool = False
    legal_approval_token: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CampaignLifecycleManager:
    """Orchestrates campaign approvals, budget commits, and launch scheduling."""

    def advance_to_creative(self, campaign: Campaign, copy_text: str) -> Campaign:
        campaign.creative_copy = copy_text
        campaign.stage = "creative"
        return campaign

    def complete_brand_review(self, campaign: Campaign, is_brand_compliant: bool) -> Campaign:
        if not is_brand_compliant:
            raise ValueError("Campaign copy failed brand guidelines review")
        campaign.brand_passed = True
        campaign.stage = "brand_approved"
        return campaign

    def complete_legal_review(self, campaign: Campaign, approval_token: str, legal_principal_id: str) -> Campaign:
        if not campaign.brand_passed:
            raise RuntimeError("Cannot request legal review before brand approval")
        if not approval_token or not legal_principal_id:
            raise ValueError("Legal review requires a valid signature and authorizer principal")
        campaign.legal_approved = True
        campaign.legal_approval_token = approval_token
        campaign.stage = "legal_approved"
        return campaign

    def commit_campaign_budget(self, campaign: Campaign, department_budget: DepartmentBudget) -> Campaign:
        if not campaign.legal_approved:
            raise RuntimeError("Cannot commit budget without prior legal approval")
        success = department_budget.commit_spend(campaign.budget_allocated)
        if not success:
            raise ValueError(f"Insufficient department budget ({department_budget.available_budget()}) for campaign ({campaign.budget_allocated})")
        campaign.stage = "budget_committed"
        return campaign

    def schedule_campaign(self, campaign: Campaign) -> Campaign:
        if campaign.stage != "budget_committed":
            raise RuntimeError("Campaign must have budget committed before scheduling")
        campaign.stage = "scheduled"
        return campaign
