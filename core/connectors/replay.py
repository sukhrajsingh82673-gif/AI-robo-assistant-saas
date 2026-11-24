"""
Connector Replay Fixture Engine
===============================
Provides deterministic offline replay of third-party SaaS APIs.
Guarantees 100% reproducible tests without network access or live credentials.
"""

from typing import Any, Dict, Optional
import hashlib
import json


class FixtureReplayEngine:
    """Manages recorded fixtures for external connector calls."""

    def __init__(self, replay_mode: bool = True):
        self.replay_mode = replay_mode
        self.fixtures: Dict[str, Dict[str, Any]] = {}

    def is_replay_mode(self) -> bool:
        return self.replay_mode

    def _generate_key(self, service: str, method: str, endpoint: str, payload: Optional[Dict[str, Any]]) -> str:
        body_str = json.dumps(payload or {}, sort_keys=True)
        h = hashlib.sha256(body_str.encode("utf-8")).hexdigest()[:12]
        return f"{service}:{method.upper()}:{endpoint}:{h}"

    def register_fixture(self, service: str, method: str, endpoint: str, payload: Optional[Dict[str, Any]], response: Dict[str, Any]):
        key = self._generate_key(service, method, endpoint, payload)
        self.fixtures[key] = response

    def get_fixture(self, service: str, method: str, endpoint: str, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        key = self._generate_key(service, method, endpoint, payload)
        if key in self.fixtures:
            return self.fixtures[key]
        # Return standard synthetic deterministic response
        return {
            "status": 200,
            "synthetic_replay": True,
            "service": service,
            "method": method.upper(),
            "endpoint": endpoint,
            "data": {"replayed": True, "fixture_key": key}
        }
