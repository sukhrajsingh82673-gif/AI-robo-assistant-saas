"""ZONATA Sovereign Core — OCR Port & Apache Tika / Tesseract OCR Adapter.

Implements OpenCode Step 1D.4:
- Port interface: OCRPort
- RealProvider: ApacheTikaOCRProvider (calls Tika /tika endpoint with OCR headers).
- Returns text and bounding boxes if available.
- Invariant: If image has no text, returns empty text with status OK (never failure).
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
from typing import Any, Dict, List, Optional, Tuple

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
)


class OCRPort(Port):
    name = "ocr"
    capability = "ocr"

    def extract_ocr(
        self,
        image_bytes: bytes,
        lang: str = "eng"
    ) -> Tuple[ProviderResult, str, List[Dict[str, Any]]]:
        raise NotImplementedError


class ApacheTikaOCRProvider(OCRPort):
    """Real OCR adapter leveraging Apache Tika's embedded Tesseract OCR pipeline."""

    def __init__(self, endpoint_url: Optional[str] = None):
        endpoint = endpoint_url or os.environ.get("TIKA_ENDPOINT", "http://localhost:9998")
        self.endpoint = endpoint.rstrip("/")
        super().__init__(provider_name="apache_tika_ocr", sandbox=False)

    def _get_version(self) -> str:
        try:
            req = urllib.request.Request(f"{self.endpoint}/version")
            with urllib.request.urlopen(req, timeout=3) as resp:
                raw = resp.read().decode("utf-8", "ignore").strip()
                return f"{raw} (OCR)"
        except Exception:
            return "apache_tika_ocr"

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
                    provider_ref=f"{ver}_ocr_ready",
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={"version": ver, "ocr_engine": "tesseract"}
                )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"OCR backend unreachable: {str(e)}"
            )

    def extract_ocr(
        self,
        image_bytes: bytes,
        lang: str = "eng"
    ) -> Tuple[ProviderResult, str, List[Dict[str, Any]]]:
        t0 = time.perf_counter()
        headers = {
            "Accept": "text/plain",
            "Content-Length": str(len(image_bytes)),
            "X-Tika-PDFOcrStrategy": "ocr_only",
            "X-Tika-OCRLanguage": lang
        }

        try:
            req = urllib.request.Request(
                f"{self.endpoint}/tika",
                data=image_bytes,
                headers=headers,
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw_text = resp.read().decode("utf-8", "replace").strip()
                status_code = resp.status

            lat = (time.perf_counter() - t0) * 1000.0
            version_str = self._get_version()

            # Bounding boxes (empty list if plain text output format)
            bounding_boxes: List[Dict[str, Any]] = []

            # Rule: If image has no text, returns empty text with OK, not failure.
            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=version_str,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={
                    "text_length": len(raw_text),
                    "has_text": bool(raw_text),
                    "lang": lang,
                    "http_status": status_code
                }
            )
            return res, raw_text, bounding_boxes
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"OCR processing failed: {str(e)}"
            )
            return res, "", []


class NotConfiguredOCRProvider(OCRPort):
    def __init__(self, reason: str = "TIKA_ENDPOINT not configured in environment"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return NotConfiguredProvider("ocr", self.reason).probe()

    def extract_ocr(
        self,
        image_bytes: bytes,
        lang: str = "eng"
    ) -> Tuple[ProviderResult, str, List[Dict[str, Any]]]:
        return self.probe(), "", []


class SandboxOCRProvider(OCRPort):
    """Test-only simulation active when ZONATA_TEST_MODE=1."""
    def __init__(self):
        super().__init__(provider_name="sandbox_ocr", sandbox=True)

    def _is_test(self) -> bool:
        return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")

    def probe(self) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_ocr_v1",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"sandbox": True}
        )

    def extract_ocr(
        self,
        image_bytes: bytes,
        lang: str = "eng"
    ) -> Tuple[ProviderResult, str, List[Dict[str, Any]]]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), "", []

        # If dummy image (e.g. 1x1 blank PNG), return empty string with OK
        if len(image_bytes) < 100:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.provider_name,
                provider_ref="sandbox_ocr_blank",
                sandbox=True,
                latency_ms=0.1,
                cost=0.0,
                metadata={"has_text": False}
            ), "", []

        # Synthetic detected text
        text = f"Sample Transcribed OCR Text for image ({len(image_bytes)} bytes)"
        boxes = [{"text": "Sample", "x": 10, "y": 10, "w": 50, "h": 20}]
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_ocr_v1",
            sandbox=True,
            latency_ms=0.2,
            cost=0.0,
            metadata={"has_text": True, "boxes_count": len(boxes)}
        ), text, boxes


def resolve_ocr_provider() -> OCRPort:
    tika_endpoint = os.environ.get("TIKA_ENDPOINT")
    if tika_endpoint:
        return ApacheTikaOCRProvider(tika_endpoint)
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    if is_test:
        return SandboxOCRProvider()
    return NotConfiguredOCRProvider()
