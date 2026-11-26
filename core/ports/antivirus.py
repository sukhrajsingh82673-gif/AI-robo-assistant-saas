"""ZONATA Sovereign Core — Antivirus Port & ClamAV Network Daemon Adapter.

Implements OpenCode Step 1D.2:
- Port interface: AntivirusPort
- RealProvider: ClamAVDaemonProvider via clamd network socket (zINSTREAM protocol).
- Verdicts: CLEAN, INFECTED, or FAILED.
- Never claim scanned if ClamAV was unreachable.
- NotConfiguredProvider: When CLAMAV_HOST/CLAMAV_PORT missing.
- SandboxProvider: Test-only simulation when ZONATA_TEST_MODE=1.
"""

from __future__ import annotations
import os
import socket
import struct
import time
from typing import Optional

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
)

EICAR_TEST_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class AntivirusPort(Port):
    name = "antivirus"
    capability = "antivirus"

    def scan_bytes(self, data: bytes, filename: Optional[str] = None) -> ProviderResult:
        raise NotImplementedError


class ClamAVDaemonProvider(AntivirusPort):
    """Real ClamAV daemon adapter over TCP socket using zINSTREAM command."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        self.host = host or os.environ.get("CLAMAV_HOST", "localhost")
        self.port = port or int(os.environ.get("CLAMAV_PORT", "3310"))
        super().__init__(provider_name="clamav_daemon", sandbox=False)

    def _get_version(self) -> str:
        """Fetch ClamAV daemon engine and signature version string."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        try:
            s.connect((self.host, self.port))
            s.sendall(b"zVERSION\0")
            raw = s.recv(1024)
            return raw.decode("utf-8", "replace").strip("\0\n\r")
        except Exception:
            return "clamav_unknown"
        finally:
            s.close()

    def probe(self) -> ProviderResult:
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            s.connect((self.host, self.port))
            s.sendall(b"zPING\0")
            resp = s.recv(1024)
            lat = (time.perf_counter() - t0) * 1000.0
            if b"PONG" in resp:
                ver = self._get_version()
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=ver,
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={"host": self.host, "port": self.port, "version": ver}
                )
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"Unexpected daemon ping reply: {resp!r}"
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"ClamAV unreachable at {self.host}:{self.port}: {str(e)}"
            )
        finally:
            s.close()

    def scan_bytes(self, data: bytes, filename: Optional[str] = None) -> ProviderResult:
        """Streams bytes to ClamAV clamd daemon chunk-by-chunk via zINSTREAM."""
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15.0)

        try:
            s.connect((self.host, self.port))
            # Start zINSTREAM session
            s.sendall(b"zINSTREAM\0")

            # Stream data in 4KB chunks, prefixed by 4-byte big-endian length
            chunk_size = 4096
            offset = 0
            while offset < len(data):
                chunk = data[offset:offset + chunk_size]
                chunk_len = struct.pack(">I", len(chunk))
                s.sendall(chunk_len + chunk)
                offset += len(chunk)

            # Terminate stream with 4-byte zero length
            s.sendall(struct.pack(">I", 0))

            # Read response from daemon (e.g. 'stream: OK\0' or 'stream: Eicar-Signature FOUND\0')
            response = b""
            while True:
                buf = s.recv(1024)
                if not buf:
                    break
                response += buf
                if b"\0" in response or b"\n" in response:
                    break

            lat = (time.perf_counter() - t0) * 1000.0
            resp_str = response.decode("utf-8", "replace").strip("\0\n\r")
            version_str = self._get_version()

            if "FOUND" in resp_str:
                # Virus found
                virus_name = resp_str.replace("stream:", "").replace("FOUND", "").strip()
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=version_str,
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={
                        "verdict": "INFECTED",
                        "virus_name": virus_name,
                        "raw_response": resp_str,
                        "size_bytes": len(data),
                        "filename": filename
                    }
                )
            elif "OK" in resp_str:
                # Clean
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=version_str,
                    sandbox=False,
                    latency_ms=lat,
                    cost=0.0,
                    metadata={
                        "verdict": "CLEAN",
                        "raw_response": resp_str,
                        "size_bytes": len(data),
                        "filename": filename
                    }
                )
            else:
                return ProviderResult(
                    status=PortStatus.FAILED,
                    provider=self.provider_name,
                    provider_ref=None,
                    latency_ms=lat,
                    error=f"ClamAV scan error: {resp_str}"
                )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"ClamAV daemon unreachable or socket error: {str(e)}"
            )
        finally:
            s.close()


class NotConfiguredAntivirusProvider(AntivirusPort):
    def __init__(self, reason: str = "CLAMAV_HOST / CLAMAV_PORT not configured"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return NotConfiguredProvider("antivirus", self.reason).probe()

    def scan_bytes(self, data: bytes, filename: Optional[str] = None) -> ProviderResult:
        return self.probe()


class SandboxAntivirusProvider(AntivirusPort):
    """Test-only simulation active when ZONATA_TEST_MODE=1."""
    def __init__(self):
        super().__init__(provider_name="sandbox_antivirus", sandbox=True)

    def _is_test(self) -> bool:
        return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")

    def probe(self) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_clamav_v1.4",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"sandbox": True, "verdict": "CLEAN"}
        )

    def scan_bytes(self, data: bytes, filename: Optional[str] = None) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")

        # Detect test virus signature
        if EICAR_TEST_SIGNATURE in data or b"X5O!P%@AP" in data:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.provider_name,
                provider_ref="sandbox_clamav_v1.4",
                sandbox=True,
                latency_ms=0.2,
                cost=0.0,
                metadata={
                    "verdict": "INFECTED",
                    "virus_name": "Eicar-Test-Signature",
                    "filename": filename,
                    "size_bytes": len(data)
                }
            )

        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_clamav_v1.4",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={
                "verdict": "CLEAN",
                "filename": filename,
                "size_bytes": len(data)
            }
        )


def resolve_antivirus_provider() -> AntivirusPort:
    clamav_host = os.environ.get("CLAMAV_HOST")
    clamav_port = os.environ.get("CLAMAV_PORT")
    if clamav_host and clamav_port:
        return ClamAVDaemonProvider(clamav_host, int(clamav_port))
    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    if is_test:
        return SandboxAntivirusProvider()
    return NotConfiguredAntivirusProvider()
