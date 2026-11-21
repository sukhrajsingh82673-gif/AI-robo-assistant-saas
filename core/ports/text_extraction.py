"""ZONATA Sovereign Core — Text Extraction Port & Apache Tika Server Adapter.

Implements OpenCode Step 1D.3:
- Port interface: TextExtractionPort
- RealProvider: ApacheTikaProvider (HTTP PUT /tika, /version, /meta).
- Enforces byte length limits and cleans control characters.
- NotConfiguredProvider: When TIKA_ENDPOINT missing.
- SandboxProvider: Test-only simulation when ZONATA_TEST_MODE=1.
"""

from __future__ import annotations
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
)


def _sanitize_extracted_text(text: str, max_bytes: int = 1_000_000) -> str:
    """Strip non-printable and control characters (preserving tab, newline, CR) and clamp size."""
    # Allow whitespace: \t (0x09), \n (0x0A), \r (0x0D), and printable chars >= 0x20
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    encoded = cleaned.encode("utf-8")
    if len(encoded) > max_bytes:
        encoded = encoded[:max_bytes]
        cleaned = encoded.decode("utf-8", "ignore")
    return cleaned


class TextExtractionPort(Port):
    name = "text_extraction"
    capability = "text_extraction"

    def extract_text(
        self,
        data: bytes,
        mime_type: Optional[str] = None,
        max_bytes: int = 1_000_000
    ) -> Tuple[ProviderResult, str]:
        raise NotImplementedError


class ApacheTikaProvider(TextExtractionPort):
    """Real text extraction adapter backed by Apache Tika Server (HTTP API)."""

    def __init__(self, endpoint_url: Optional[str] = None):
        endpoint = endpoint_url or os.environ.get("TIKA_ENDPOINT", "http://localhost:9998")
        self.endpoint = endpoint.rstrip("/")
        super().__init__(provider_name="apache_tika", sandbox=False)

    def _get_version(self) -> str:
        try:
            req = urllib.request.Request(f"{self.endpoint}/version")
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read().decode("utf-8", "ignore").strip()
                return raw or "Apache Tika"
        except Exception:
            return "apache_tika_server"

    def probe(self) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(f"{self.endpoint}/version")
            with urllib.request.urlopen(req, timeout=3) as resp:
                ver = resp.read().decode("utf-8", "ignore").strip()
                lat = (time.perf_counter() - t0) * 1000.0
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=ver or "tika_version_ok",
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={"version": ver, "endpoint": self.endpoint}
                )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"Apache Tika server unreachable: {str(e)}"
            )

    def extract_text(
        self,
        data: bytes,
        mime_type: Optional[str] = None,
        max_bytes: int = 1_000_000
    ) -> Tuple[ProviderResult, str]:
        t0 = time.perf_counter()
        headers = {
            "Accept": "text/plain",
            "Content-Length": str(len(data))
        }
        if mime_type:
            headers["Content-Type"] = mime_type

        try:
            # 1. HTTP PUT to /tika for extracted plain text
            req = urllib.request.Request(
                f"{self.endpoint}/tika",
                data=data,
                headers=headers,
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw_text = resp.read().decode("utf-8", "replace")
                status_code = resp.status

            # 2. Extract detected MIME & metadata via /meta
            detected_mime = mime_type or "application/octet-stream"
            meta_dict: Dict[str, Any] = {}
            try:
                meta_headers = dict(headers)
                meta_headers["Accept"] = "application/json"
                meta_req = urllib.request.Request(
                    f"{self.endpoint}/meta",
                    data=data,
                    headers=meta_headers,
                    method="PUT"
                )
                with urllib.request.urlopen(meta_req, timeout=10) as meta_resp:
                    meta_dict = json.loads(meta_resp.read().decode("utf-8", "ignore"))
                    detected_mime = meta_dict.get("Content-Type", detected_mime)
            except Exception:
                pass

            cleaned_text = _sanitize_extracted_text(raw_text, max_bytes=max_bytes)
            lat = (time.perf_counter() - t0) * 1000.0
            tika_ver = self._get_version()

            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=tika_ver,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={
                    "detected_mime": detected_mime,
                    "raw_length_bytes": len(data),
                    "extracted_chars": len(cleaned_text),
                    "http_status": status_code,
                    "metadata": meta_dict
                }
            )
            return res, cleaned_text
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"Tika extraction failed: {str(e)}"
            )
            return res, ""


class NotConfiguredTextExtractionProvider(TextExtractionPort):
    def __init__(self, reason: str = "TIKA_ENDPOINT not configured in environment"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return NotConfiguredProvider("text_extraction", self.reason).probe()

    def extract_text(
        self,
        data: bytes,
        mime_type: Optional[str] = None,
        max_bytes: int = 1_000_000
    ) -> Tuple[ProviderResult, str]:
        return self.probe(), ""


class SandboxTextExtractionProvider(TextExtractionPort):
    """Test-only simulation active when ZONATA_TEST_MODE=1."""
    def __init__(self):
        super().__init__(provider_name="sandbox_tika", sandbox=True)

    def _is_test(self) -> bool:
        return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")

    def probe(self) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_tika_v2.9.2",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"sandbox": True}
        )

    def extract_text(
        self,
        data: bytes,
        mime_type: Optional[str] = None,
        max_bytes: int = 1_000_000
    ) -> Tuple[ProviderResult, str]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), ""

        # Simple text extraction simulation
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = f"[Binary Document of {len(data)} bytes - Synthetic Text Extraction]"

        cleaned = _sanitize_extracted_text(text, max_bytes=max_bytes)
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_tika_v2.9.2",
            sandbox=True,
            latency_ms=0.2,
            cost=0.0,
            metadata={"detected_mime": mime_type or "text/plain", "extracted_chars": len(cleaned)}
        ), cleaned


def resolve_text_extraction_provider() -> TextExtractionPort:
    tika_endpoint = os.environ.get("TIKA_ENDPOINT")
    if tika_endpoint:
        return ApacheTikaProvider(tika_endpoint)
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    if is_test:
        return SandboxTextExtractionProvider()
    return NotConfiguredTextExtractionProvider()
