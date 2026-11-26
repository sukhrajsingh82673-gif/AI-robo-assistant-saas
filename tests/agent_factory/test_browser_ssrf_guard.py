"""Tests for Browser Gateway & SSRF Security Guard."""

import pytest
from agent_factory.capabilities.browser_gateway import (
    BrowserGateway, validate_outbound_url, SsrfSecurityError, DomainNotAllowedError
)


def test_ssrf_blocks_private_ips():
    allowed = ["*"]
    private_urls = [
        "http://127.0.0.1:8080/admin",
        "http://localhost:3000/api",
        "http://10.0.0.5/internal",
        "http://192.168.1.100/router",
        "http://172.16.0.1/secrets"
    ]
    for url in private_urls:
        with pytest.raises(SsrfSecurityError):
            validate_outbound_url(url, allowed)


def test_ssrf_blocks_cloud_metadata():
    allowed = ["*"]
    metadata_urls = [
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/"
    ]
    for url in metadata_urls:
        with pytest.raises(SsrfSecurityError):
            validate_outbound_url(url, allowed)


def test_domain_allowlist_enforcement():
    allowed = ["api.github.com", "*.trustedcorp.com"]

    # Allowed
    assert validate_outbound_url("https://api.github.com/repos", allowed)[0] is True
    assert validate_outbound_url("https://reports.trustedcorp.com/daily", allowed)[0] is True

    # Not allowed
    with pytest.raises(DomainNotAllowedError):
        validate_outbound_url("https://malicious.evil.com/exfil", allowed)


def test_browser_gateway_fetch_safe():
    gw = BrowserGateway(allowed_hosts=["example.org"])
    res = gw.fetch("https://example.org/index.html")
    assert res["status"] == 200
    assert "Safe content" in res["content"]
