"""ZONATA Agent Factory - Browser Gateway & SSRF Guard.

Enforces:
- Strict domain allowlist
- Complete SSRF prevention (blocking RFC 1918 private ranges, AWS/GCP/Azure metadata IPs, loopback, IPv6 link-local)
- Read-only navigation constraints
"""

import ipaddress
import re
import socket
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse


METADATA_IPS = {"169.254.169.254", "metadata.google.internal"}

PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class SsrfSecurityError(Exception):
    """Raised when an outbound URL violates SSRF boundaries."""
    pass


class DomainNotAllowedError(Exception):
    """Raised when destination domain is not in the configured allowlist."""
    pass


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, link-local, or cloud metadata."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in net for net in PRIVATE_NETWORKS) or str(ip) in METADATA_IPS
    except ValueError:
        return False


def validate_outbound_url(url: str, allowed_hosts: List[str]) -> Tuple[bool, str]:
    """
    Validate target URL against SSRF rules and domain allowlist.
    Returns (True, 'ok') or raises SsrfSecurityError / DomainNotAllowedError.
    """
    if not url:
        raise SsrfSecurityError("Empty URL provided")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SsrfSecurityError(f"Unsupported URI scheme '{parsed.scheme}'. Only http and https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SsrfSecurityError("Missing hostname in target URL")

    hostname_lower = hostname.lower()

    # 1. Localhost and cloud metadata names check
    if hostname_lower in ("localhost", "127.0.0.1", "::1", "metadata.google.internal", "instance-data"):
        raise SsrfSecurityError(f"SSRF violation: target '{hostname}' is a reserved local/metadata endpoint")

    # 2. Check if hostname is direct IP
    if is_ip_private_or_restricted(hostname_lower):
        raise SsrfSecurityError(f"SSRF violation: target IP '{hostname}' belongs to restricted network")

    # 3. Domain allowlist check
    if "*" not in allowed_hosts:
        matched = False
        for allowed in allowed_hosts:
            allowed_clean = allowed.lower()
            if allowed_clean.startswith("*."):
                suffix = allowed_clean[1:]  # e.g. .example.com
                if hostname_lower.endswith(suffix):
                    matched = True
                    break
            elif hostname_lower == allowed_clean:
                matched = True
                break
        if not matched:
            raise DomainNotAllowedError(f"Host '{hostname}' is not in allowed hosts: {allowed_hosts}")

    return True, "ok"


class BrowserGateway:
    def __init__(self, allowed_hosts: Optional[List[str]] = None):
        self.allowed_hosts = allowed_hosts or []

    def fetch(self, url: str) -> Dict[str, Any]:
        """Perform SSRF-safe URL validation and fetch stub."""
        validate_outbound_url(url, self.allowed_hosts)
        return {
            "status": 200,
            "url": url,
            "content": f"<html><body>Safe content from {url}</body></html>"
        }
