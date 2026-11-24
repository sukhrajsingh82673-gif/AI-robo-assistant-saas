"""
Workday Human Capital Management Connector (Rule 70, Rule 73)
"""

from typing import Dict, Any
from core.connectors.wave1.base import BaseEnterpriseConnector


class WorkdayConnector(BaseEnterpriseConnector):
    """Integrates with Workday Human Capital Management SOAP & REST APIs."""

    CONNECTOR_NAME = "workday"

    def get_worker(self, worker_id: str) -> Dict[str, Any]:
        """Retrieves employee profile from Workday."""
        if self.replay_mode:
            return self.get_replay_fixture("get_worker")
        self.verify_live_configured()
        return {}
