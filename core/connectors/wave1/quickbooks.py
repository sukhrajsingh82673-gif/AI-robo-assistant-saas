"""
Intuit QuickBooks Online Accounting Connector (Rule 70, Rule 73)
"""

from typing import Dict, Any
from core.connectors.wave1.base import BaseEnterpriseConnector


class QuickBooksConnector(BaseEnterpriseConnector):
    """Integrates with QuickBooks Online v3 REST APIs."""

    CONNECTOR_NAME = "quickbooks"

    def get_company_info(self) -> Dict[str, Any]:
        """Retrieves QuickBooks company profile and base settings."""
        if self.replay_mode:
            return self.get_replay_fixture("get_company_info")
        self.verify_live_configured()
        return {}

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates invoice in QuickBooks Online."""
        if self.replay_mode:
            return self.get_replay_fixture("create_invoice")
        self.verify_live_configured()
        return {}
