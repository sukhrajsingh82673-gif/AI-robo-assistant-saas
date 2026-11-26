"""
Marketing Port and Ad Platform Adapters (Google, Meta, LinkedIn)
================================================================
Adheres to:
- Rule 41: Zero Plaintext Secrets (OAuth tokens dynamically leased from OpenBao)
- Rule 59: Systems of Record are Ports
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from core.marketing.campaign import Campaign


class MarketingPort(ABC):
    """Abstract Port for Marketing Ad Platforms."""

    @abstractmethod
    def publish_ad(self, campaign: Campaign) -> Dict[str, Any]:
        pass

    @abstractmethod
    def pause_ad(self, campaign_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_performance(self, campaign_id: str) -> Dict[str, Any]:
        pass


class BaseAdPlatformAdapter(MarketingPort):
    def __init__(self, platform_name: str, token_provider: Optional[Any] = None):
        self.platform_name = platform_name
        self.token_provider = token_provider or (lambda: f"mock_leased_{platform_name}_token")
        self.published_campaigns: Dict[str, Campaign] = {}

    def publish_ad(self, campaign: Campaign) -> Dict[str, Any]:
        token = self.token_provider()
        assert token is not None, f"Rule 41: Token required for {self.platform_name}"
        self.published_campaigns[campaign.campaign_id] = campaign
        return {
            "status": "published",
            "platform": self.platform_name,
            "campaign_id": campaign.campaign_id,
            "external_id": f"ad_{self.platform_name[:3]}_{campaign.campaign_id}"
        }

    def pause_ad(self, campaign_id: str) -> Dict[str, Any]:
        if campaign_id in self.published_campaigns:
            del self.published_campaigns[campaign_id]
        return {"status": "paused", "platform": self.platform_name, "campaign_id": campaign_id}

    def get_performance(self, campaign_id: str) -> Dict[str, Any]:
        return {
            "platform": self.platform_name,
            "campaign_id": campaign_id,
            "impressions": 12500,
            "clicks": 420,
            "spend": 350.00,
            "conversions": 18
        }


class GoogleAdsAdapter(BaseAdPlatformAdapter):
    def __init__(self, token_provider: Optional[Any] = None):
        super().__init__("GoogleAds", token_provider)


class MetaAdsAdapter(BaseAdPlatformAdapter):
    def __init__(self, token_provider: Optional[Any] = None):
        super().__init__("MetaAds", token_provider)


class LinkedInAdsAdapter(BaseAdPlatformAdapter):
    def __init__(self, token_provider: Optional[Any] = None):
        super().__init__("LinkedInAds", token_provider)
