"""
Official ZONATA Python SDK (Rule 80).
"""

from .client import ZonataClient
from .webhooks import WebhookVerifier

__version__ = "1.0.0"
__provenance__ = "commit:step9-product-readiness"
__all__ = ["ZonataClient", "WebhookVerifier"]
