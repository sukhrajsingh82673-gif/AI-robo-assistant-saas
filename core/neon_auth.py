"""
ZONATA Enterprise SaaS — Neon Auth Client & Identity Integration
Provides verification and session routing for Neon Auth (Managed Better Auth).
Supports JWKS key fetching, session verification, and schema query integration.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

from core.neon_env import get_neon_auth_base_url, get_neon_auth_jwks_url


class NeonAuthClient:
    """Client for interacting with Neon Auth (Managed Better Auth)."""

    def __init__(self):
        self._cached_jwks: Optional[Dict[str, Any]] = None
        self._jwks_fetched_at: float = 0.0
        self._cache_ttl_sec: float = 3600.0  # 1 hour cache

    @property
    def base_url(self) -> str:
        return get_neon_auth_base_url()

    @property
    def jwks_url(self) -> str:
        return get_neon_auth_jwks_url()

    def is_configured(self) -> bool:
        return bool(self.base_url and self.jwks_url)

    def get_jwks(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch and cache JWKS public keys from Neon Auth."""
        now = time.time()
        if not force_refresh and self._cached_jwks and (now - self._jwks_fetched_at < self._cache_ttl_sec):
            return self._cached_jwks

        if not self.jwks_url:
            return {"keys": []}

        req = urllib.request.Request(
            self.jwks_url,
            headers={"User-Agent": "ZONATA-Enterprise/1.0", "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._cached_jwks = data
                self._jwks_fetched_at = now
                return data
        except Exception as e:
            if self._cached_jwks:
                return self._cached_jwks
            raise RuntimeError(f"Failed to fetch JWKS from Neon Auth ({self.jwks_url}): {e}")

    def verify_session(self, session_token: str) -> Dict[str, Any]:
        """
        Verify an active user session with Neon Auth.
        Calls the Managed Better Auth get-session endpoint.
        """
        if not self.base_url:
            return {"valid": False, "error": "Neon Auth not configured"}

        url = f"{self.base_url.rstrip('/')}/get-session"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ZONATA-Enterprise/1.0",
                "Cookie": f"better-auth.session_token={session_token}",
                "Authorization": f"Bearer {session_token}",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"valid": True, "session": data}
        except urllib.error.HTTPError as e:
            return {"valid": False, "status_code": e.code, "error": str(e.reason)}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_public_config(self) -> Dict[str, Any]:
        """Return public auth endpoints suitable for frontend web client."""
        return {
            "type": "Managed Better Auth",
            "provider": "Neon Auth",
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "jwks_url": self.jwks_url,
            "login_url": f"{self.base_url.rstrip('/')}/sign-in",
            "signup_url": f"{self.base_url.rstrip('/')}/sign-up"
        }


# Singleton instance
neon_auth = NeonAuthClient()
