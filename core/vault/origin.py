"""
ZONATA Origin Normalizer and Matcher (OpenCode Step 3D)
Enforces strict origin binding (scheme, host, port) with zero subdomain leakage.
"""

from __future__ import annotations

from urllib.parse import urlparse
import logging

logger = logging.getLogger("zonata.vault.origin")


class OriginValidator:
    """
    Normalizes and validates target URLs against registered credential origins.
    """

    DEFAULT_PORTS = {
        "http": 80,
        "https": 443,
        "ws": 80,
        "wss": 443,
    }

    @classmethod
    def normalize_origin(cls, raw_url_or_origin: str) -> str:
        """
        Extracts and normalizes scheme, hostname, and explicit port.
        e.g. 'https://app.example.com/login?redirect=true' -> 'https://app.example.com:443'
             'https://api.stripe.com:8443/' -> 'https://api.stripe.com:8443'
        """
        if not raw_url_or_origin:
            return ""

        url = raw_url_or_origin.strip()
        if "://" not in url:
            # Default to https if no scheme supplied
            url = f"https://{url}"

        parsed = urlparse(url)
        scheme = (parsed.scheme or "https").lower()
        host = (parsed.hostname or "").lower()

        if not host:
            raise ValueError(f"Invalid origin: unable to parse hostname from '{raw_url_or_origin}'")

        port = parsed.port or cls.DEFAULT_PORTS.get(scheme)
        if port is None:
            port = 443 if "https" in scheme else 80

        return f"{scheme}://{host}:{port}"

    @classmethod
    def match_origin(cls, bound_origin: str, target_url: str, allow_subdomains: bool = False) -> bool:
        """
        Checks if target_url matches the bound origin strictly.
        Refuses scheme downgrade (https -> http) and port/host mismatches.
        """
        try:
            norm_bound = cls.normalize_origin(bound_origin)
            norm_target = cls.normalize_origin(target_url)
        except Exception:
            return False

        if norm_bound == norm_target:
            return True

        if allow_subdomains:
            # Only if explicitly declared in grant
            b_parsed = urlparse(norm_bound)
            t_parsed = urlparse(norm_target)
            if b_parsed.scheme == t_parsed.scheme and b_parsed.port == t_parsed.port:
                if t_parsed.hostname and t_parsed.hostname.endswith(f".{b_parsed.hostname}"):
                    return True

        return False
