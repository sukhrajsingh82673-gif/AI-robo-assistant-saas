"""ZONATA Sovereign Core — Object Storage Port & SeaweedFS (S3-Compatible) Adapter.

Implements OpenCode Step 1D.1:
- Port interface: StoragePort
- RealProvider: SeaweedFSS3Provider (put, get, head, delete, list)
- Reality Ladder: STORED only after read-back and SHA-256 digest match.
- NotConfiguredProvider: When S3_ENDPOINT missing.
- SandboxProvider: Test-only simulation when ZONATA_TEST_MODE=1.
"""

from __future__ import annotations
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
)


class StoragePort(Port):
    name = "storage"
    capability = "storage"

    def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> ProviderResult:
        raise NotImplementedError

    def get(self, bucket: str, key: str) -> Tuple[ProviderResult, Optional[bytes]]:
        raise NotImplementedError

    def head(self, bucket: str, key: str) -> ProviderResult:
        raise NotImplementedError

    def delete(self, bucket: str, key: str) -> ProviderResult:
        raise NotImplementedError

    def list(self, bucket: str, prefix: str = "") -> Tuple[ProviderResult, List[Dict[str, Any]]]:
        raise NotImplementedError


class SeaweedFSS3Provider(StoragePort):
    """Real S3-compatible object store adapter backed by SeaweedFS."""

    def __init__(self, endpoint_url: Optional[str] = None):
        endpoint = endpoint_url or os.environ.get("S3_ENDPOINT", "http://localhost:8333")
        self.endpoint = endpoint.rstrip("/")
        super().__init__(provider_name="seaweedfs_s3", sandbox=False)

    def _url(self, bucket: str, key: str = "") -> str:
        clean_key = key.lstrip("/")
        if clean_key:
            return f"{self.endpoint}/{bucket}/{clean_key}"
        return f"{self.endpoint}/{bucket}"

    def probe(self) -> ProviderResult:
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(self.endpoint, headers={"User-Agent": "ZONATA-Storage/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                lat = (time.perf_counter() - t0) * 1000.0
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=f"s3_ping_{resp.status}",
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={"endpoint": self.endpoint, "http_status": resp.status}
                )
        except urllib.error.HTTPError as e:
            lat = (time.perf_counter() - t0) * 1000.0
            if e.code in (200, 403, 404):
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=f"s3_ping_{e.code}",
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={"endpoint": self.endpoint, "http_status": e.code}
                )
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"HTTP {e.code}: {e.reason}"
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=str(e)
            )

    def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> ProviderResult:
        """Stores object and enforces Reality Ladder: reads back and validates SHA-256."""
        t0 = time.perf_counter()
        expected_sha = hashlib.sha256(data).hexdigest()
        target_url = self._url(bucket, key)

        try:
            # 1. HTTP PUT upload
            req = urllib.request.Request(
                target_url,
                data=data,
                headers={
                    "Content-Type": content_type,
                    "Content-Length": str(len(data)),
                    "x-amz-content-sha256": expected_sha
                },
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                etag = (resp.headers.get("ETag") or "").strip('"')

            # 2. Reality Ladder: Real read-back verification
            read_req = urllib.request.Request(target_url, method="GET")
            with urllib.request.urlopen(read_req, timeout=10) as read_resp:
                read_back_data = read_resp.read()
                read_back_etag = (read_resp.headers.get("ETag") or "").strip('"')

            # 3. Checksum verification
            actual_sha = hashlib.sha256(read_back_data).hexdigest()
            if actual_sha != expected_sha:
                lat = (time.perf_counter() - t0) * 1000.0
                return ProviderResult(
                    status=PortStatus.FAILED,
                    provider=self.provider_name,
                    provider_ref=None,
                    latency_ms=lat,
                    error=f"Integrity check failed: expected {expected_sha}, got {actual_sha}"
                )

            lat = (time.perf_counter() - t0) * 1000.0
            ref = read_back_etag or etag or f"sha256_{expected_sha[:16]}"
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=ref,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={
                    "bucket": bucket,
                    "key": key,
                    "size_bytes": len(data),
                    "sha256": actual_sha,
                    "etag": ref,
                    "stored": True
                }
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"S3 PUT failure: {str(e)}"
            )

    def get(self, bucket: str, key: str) -> Tuple[ProviderResult, Optional[bytes]]:
        t0 = time.perf_counter()
        target_url = self._url(bucket, key)
        try:
            req = urllib.request.Request(target_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                etag = (resp.headers.get("ETag") or "").strip('"')
                ct = resp.headers.get("Content-Type", "application/octet-stream")

            digest = hashlib.sha256(data).hexdigest()
            lat = (time.perf_counter() - t0) * 1000.0
            ref = etag or f"sha256_{digest[:16]}"
            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=ref,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"size_bytes": len(data), "sha256": digest, "content_type": ct}
            )
            return res, data
        except urllib.error.HTTPError as e:
            lat = (time.perf_counter() - t0) * 1000.0
            st = PortStatus.FAILED
            res = ProviderResult(
                status=st,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"HTTP {e.code}: {e.reason}"
            )
            return res, None
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=str(e)
            )
            return res, None

    def head(self, bucket: str, key: str) -> ProviderResult:
        t0 = time.perf_counter()
        target_url = self._url(bucket, key)
        try:
            req = urllib.request.Request(target_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                etag = (resp.headers.get("ETag") or "").strip('"')
                clen = int(resp.headers.get("Content-Length", 0))
                ct = resp.headers.get("Content-Type", "")

            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=etag or f"head_{bucket}_{key}",
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"content_length": clen, "content_type": ct, "etag": etag}
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=str(e)
            )

    def delete(self, bucket: str, key: str) -> ProviderResult:
        t0 = time.perf_counter()
        target_url = self._url(bucket, key)
        try:
            req = urllib.request.Request(target_url, method="DELETE")
            with urllib.request.urlopen(req, timeout=5) as resp:
                status_code = resp.status

            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=f"del_{status_code}",
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"bucket": bucket, "key": key, "deleted": True}
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=str(e)
            )

    def list(self, bucket: str, prefix: str = "") -> Tuple[ProviderResult, List[Dict[str, Any]]]:
        t0 = time.perf_counter()
        qs = f"?prefix={urllib.parse.quote(prefix)}" if prefix else ""
        target_url = f"{self._url(bucket)}{qs}"
        try:
            req = urllib.request.Request(target_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()

            items: List[Dict[str, Any]] = []
            try:
                root = ET.fromstring(content)
                # Parse standard S3 ListBucketResult XML
                ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"} if "http://" in content.decode("utf-8", "ignore") else {}
                contents = root.findall(".//Contents") or root.findall(".//s3:Contents", ns)
                for item in contents:
                    k = (item.find("Key") or item.find("s3:Key", ns))
                    s = (item.find("Size") or item.find("s3:Size", ns))
                    e = (item.find("ETag") or item.find("s3:ETag", ns))
                    if k is not None and k.text:
                        items.append({
                            "key": k.text,
                            "size": int(s.text) if s is not None and s.text else 0,
                            "etag": (e.text or "").strip('"') if e is not None else ""
                        })
            except Exception:
                # If SeaweedFS returns JSON or simple listing
                pass

            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=f"list_{bucket}_{len(items)}",
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"count": len(items), "prefix": prefix}
            )
            return res, items
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=str(e)
            )
            return res, []


class NotConfiguredStorageProvider(StoragePort):
    def __init__(self, reason: str = "S3_ENDPOINT not configured in environment"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return NotConfiguredProvider("storage", self.reason).probe()

    def put(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> ProviderResult:
        return self.probe()

    def get(self, bucket: str, key: str) -> Tuple[ProviderResult, Optional[bytes]]:
        return self.probe(), None

    def head(self, bucket: str, key: str) -> ProviderResult:
        return self.probe()

    def delete(self, bucket: str, key: str) -> ProviderResult:
        return self.probe()

    def list(self, bucket: str, prefix: str = "") -> Tuple[ProviderResult, List[Dict[str, Any]]]:
        return self.probe(), []


class SandboxStorageProvider(StoragePort):
    """In-memory simulation active only when ZONATA_TEST_MODE=1."""
    def __init__(self):
        super().__init__(provider_name="sandbox_storage", sandbox=True)
        self._store: Dict[str, Dict[str, Any]] = {}

    def _is_test(self) -> bool:
        return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")

    def probe(self) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                error="Sandbox rejected in non-test mode"
            )
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=f"sandbox_store_{len(self._store)}",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"items_count": len(self._store)}
        )

    def put(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        digest = hashlib.sha256(data).hexdigest()
        full_key = f"{bucket}/{key}"
        self._store[full_key] = {
            "data": data,
            "sha256": digest,
            "size": len(data),
            "content_type": content_type,
            "etag": f"sandbox_etag_{digest[:12]}"
        }
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=self._store[full_key]["etag"],
            sandbox=True,
            latency_ms=0.2,
            cost=0.0,
            metadata={"bucket": bucket, "key": key, "sha256": digest, "size_bytes": len(data)}
        )

    def get(self, bucket: str, key: str) -> Tuple[ProviderResult, Optional[bytes]]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), None
        full_key = f"{bucket}/{key}"
        if full_key not in self._store:
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                error=f"Key not found: {full_key}"
            ), None
        item = self._store[full_key]
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=item["etag"],
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"sha256": item["sha256"], "size_bytes": item["size"]}
        ), item["data"]

    def head(self, bucket: str, key: str) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        full_key = f"{bucket}/{key}"
        if full_key not in self._store:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Not found")
        item = self._store[full_key]
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=item["etag"],
            sandbox=True,
            latency_ms=0.1,
            metadata={"content_length": item["size"]}
        )

    def delete(self, bucket: str, key: str) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        full_key = f"{bucket}/{key}"
        self._store.pop(full_key, None)
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=f"del_{key}",
            sandbox=True,
            latency_ms=0.1,
            metadata={"deleted": True}
        )

    def list(self, bucket: str, prefix: str = "") -> Tuple[ProviderResult, List[Dict[str, Any]]]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), []
        match = []
        for k, v in self._store.items():
            if k.startswith(f"{bucket}/{prefix}"):
                obj_key = k[len(bucket) + 1:]
                match.append({"key": obj_key, "size": v["size"], "etag": v["etag"]})
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref=f"list_{len(match)}",
            sandbox=True,
            latency_ms=0.1,
            metadata={"count": len(match)}
        ), match


def resolve_storage_provider() -> StoragePort:
    """Resolve active storage provider based on environment and truth invariants."""
    s3_endpoint = os.environ.get("S3_ENDPOINT")
    if s3_endpoint:
        return SeaweedFSS3Provider(s3_endpoint)
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    if is_test:
        return SandboxStorageProvider()
    return NotConfiguredStorageProvider()
