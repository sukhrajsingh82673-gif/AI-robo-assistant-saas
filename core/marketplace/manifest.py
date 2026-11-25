"""
Marketplace Package Manifest Specification (zonata.marketplace-package/v1).
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CapabilityRequirement:
    capability: str  # e.g., 'storage:read', 'webhooks:listen', 'network:egress'
    resource: Optional[str] = None  # e.g., 'api.partner.com' or 'invoices'
    justification: str = ""


@dataclass
class MarketplaceManifest:
    package_id: str
    name: str
    version: str
    publisher: str
    description: str
    entrypoint: str
    capabilities_requested: List[CapabilityRequirement]
    pricing_type: str = "free"  # free, paid
    price_cents: int = 0
    schema_version: str = "zonata.marketplace-package/v1"

    def compute_digest(self) -> str:
        payload = f"{self.schema_version}|{self.package_id}|{self.version}|{self.publisher}|{self.entrypoint}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketplaceManifest":
        schema_v = data.get("schema_version")
        if schema_v != "zonata.marketplace-package/v1":
            raise ValueError(f"Unsupported manifest schema version: '{schema_v}'. Expected 'zonata.marketplace-package/v1'.")

        caps = [
            CapabilityRequirement(
                capability=c.get("capability", ""),
                resource=c.get("resource"),
                justification=c.get("justification", ""),
            )
            for c in data.get("capabilities_requested", [])
        ]

        return cls(
            package_id=data["package_id"],
            name=data["name"],
            version=data["version"],
            publisher=data["publisher"],
            description=data["description"],
            entrypoint=data["entrypoint"],
            capabilities_requested=caps,
            pricing_type=data.get("pricing_type", "free"),
            price_cents=data.get("price_cents", 0),
            schema_version=schema_v,
        )
