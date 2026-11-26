"""
IT Asset Inventory & Certificate Renewal Engine
===============================================
Tracks:
- Hardware, Software licenses, SaaS subscriptions, and TLS/mTLS certificates
- Automated renewal alerts at 30 days, 15 days, and 7 days before expiry
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field


class ITAsset(BaseModel):
    asset_id: str
    tenant_id: str
    company_id: str
    asset_type: str  # 'hardware', 'software_license', 'saas_subscription', 'tls_certificate'
    name: str
    identifier: str  # Serial number, domain, or license key hash
    assigned_owner: str
    expires_at: Optional[str] = None  # ISO-8601
    status: str = "active"


class AssetAlert(BaseModel):
    asset_id: str
    name: str
    asset_type: str
    days_until_expiry: int
    urgency: str  # 'critical', 'warning', 'info'
    message: str


class AssetInventoryManager:
    """Manages asset registries and computes expiration clocks."""

    def __init__(self):
        self.assets: Dict[str, ITAsset] = {}

    def register_asset(self, asset: ITAsset) -> ITAsset:
        key = f"{asset.tenant_id}:{asset.company_id}:{asset.asset_id}"
        self.assets[key] = asset
        return asset

    def check_expirations(self, current_time: Optional[datetime] = None) -> List[AssetAlert]:
        now = current_time or datetime.now(timezone.utc)
        alerts: List[AssetAlert] = []

        for asset in self.assets.values():
            if not asset.expires_at or asset.status != "active":
                continue

            exp_dt = datetime.fromisoformat(asset.expires_at)
            delta = (exp_dt - now).total_seconds() / 86400.0
            days = int(delta)

            if days <= 7:
                alerts.append(AssetAlert(
                    asset_id=asset.asset_id,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    days_until_expiry=days,
                    urgency="critical",
                    message=f"CRITICAL: {asset.asset_type} '{asset.name}' expires in {days} days!"
                ))
            elif days <= 15:
                alerts.append(AssetAlert(
                    asset_id=asset.asset_id,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    days_until_expiry=days,
                    urgency="warning",
                    message=f"WARNING: {asset.asset_type} '{asset.name}' expires in {days} days."
                ))
            elif days <= 30:
                alerts.append(AssetAlert(
                    asset_id=asset.asset_id,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    days_until_expiry=days,
                    urgency="info",
                    message=f"INFO: {asset.asset_type} '{asset.name}' expires in {days} days."
                ))

        return alerts
