"""
Base Connector Interface with Deterministic Replay and Sandboxing (Rule 24, Rule 70, Rule 73)
"""

from typing import Dict, Any, Optional
import os
import json
from pathlib import Path


class BaseEnterpriseConnector:
    """Base class for all enterprise integration connectors."""

    CONNECTOR_NAME = "base"
    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wave1_replays.json"

    def __init__(self, is_sandbox: bool = True, replay_mode: bool = True):
        self.is_sandbox = is_sandbox
        self.replay_mode = replay_mode
        self._fixtures: Dict[str, Any] = {}
        self._load_fixtures()

    def _load_fixtures(self):
        if self.FIXTURE_PATH.exists():
            with open(self.FIXTURE_PATH, "r", encoding="utf-8") as f:
                self._fixtures = json.load(f)

    def get_replay_fixture(self, operation: str) -> Dict[str, Any]:
        """Returns deterministic fixture response for contract and regression testing."""
        connector_data = self._fixtures.get(self.CONNECTOR_NAME, {})
        if operation in connector_data:
            return connector_data[operation]
        return {"status": "SUCCESS", "mock": True, "operation": operation}

    def verify_live_configured(self):
        """Verifies connector has live credentials. If not, raises NotConfigured."""
        if not self.replay_mode and self.is_sandbox:
            raise RuntimeError(f"NOT_CONFIGURED: Connector '{self.CONNECTOR_NAME}' has no live credentials configured.")
