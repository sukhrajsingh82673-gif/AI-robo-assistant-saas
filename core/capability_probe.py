"""ZONATA Sovereign Core — Capability Reality Probe.

Implements OpenCode Step 1C:
For each capability, perform one real, harmless call and classify it:
- database (dialect, RLS active)
- storage (object store S3/SeaweedFS)
- email_out (SMTP/Mailpit)
- email_in (IMAP)
- calendar (CalDAV)
- antivirus (ClamAV daemon)
- text_extraction (Apache Tika)
- ocr (Apache Tika OCR)
- search (vector/FTS)
- key_management (KMS/Sovereign Vault)
- llm (Model provider)
- browser (NOT_IMPLEMENTED)
- desktop_control (NOT_IMPLEMENTED)
- payments (Stripe/Sandbox)
- secrets (Vault/KMS)
- workflow_engine (Temporal/NATS/Outbox)
- mcp (Model Context Protocol)
- observability (OTEL/Metrics)

Truth Rule: Nothing reports success it did not achieve.
"""

from __future__ import annotations
import os
import secrets
import socket
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from core.ports.base import (
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    NotImplementedProvider,
    SandboxProvider,
)


def _is_test_mode() -> bool:
    return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")


def _http_get_status(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 3.0):
    """Perform a harmless authenticated GET and return (status_code|None, error|None)."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(256)
            return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return None, str(e)


def probe_database() -> ProviderResult:
    """Probe primary database connection, dialect, and row-level security status."""
    t0 = time.perf_counter()
    try:
        from core.db import db
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        latency_ms = (time.perf_counter() - t0) * 1000.0

        dialect = db.get_dialect()
        rls_active = False

        if dialect == "postgresql":
            try:
                cur.execute("SELECT count(*) FROM pg_tables WHERE rowsecurity = true;")
                row = cur.fetchone()
                rls_active = (row[0] > 0) if row else False
            except Exception:
                rls_active = False

        is_production = os.environ.get("APP_ENV") == "production"
        allow_degraded = os.environ.get("ZONATA_ALLOW_DEGRADED") == "1"

        if dialect == "sqlite" and is_production and allow_degraded:
            status = PortStatus.DEGRADED
        else:
            status = PortStatus.OK

        return ProviderResult(
            status=status,
            provider=f"database_{dialect}",
            provider_ref=f"db_conn_{dialect}",
            sandbox=(dialect == "sqlite"),
            latency_ms=latency_ms,
            cost=0.0,
            metadata={"dialect": dialect, "rls_active": rls_active}
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="database",
            provider_ref=None,
            sandbox=False,
            latency_ms=latency_ms,
            cost="UNMEASURED",
            error=str(e)
        )


def probe_storage() -> ProviderResult:
    """Probe object storage endpoint (SeaweedFS / S3)."""
    from core.ports.storage import resolve_storage_provider
    return resolve_storage_provider().probe()


def probe_email_out() -> ProviderResult:
    """Probe SMTP outbound service (e.g. Mailpit or production SMTP)."""
    from core.ports.email import resolve_email_provider
    return resolve_email_provider().probe()


def probe_email_in() -> ProviderResult:
    """Probe inbound IMAP service."""
    t0 = time.perf_counter()
    imap_host = os.environ.get("IMAP_HOST")
    imap_port = int(os.environ.get("IMAP_PORT", 993 if imap_host else 0))

    if not imap_host or imap_port <= 0:
        if _is_test_mode():
            return SandboxProvider("email_in", "imap_sandbox").probe()
        return NotConfiguredProvider("email_in", "IMAP_HOST not configured").probe()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((imap_host, imap_port))
        s.close()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.OK,
            provider="imap",
            provider_ref=f"imap_{imap_host}",
            sandbox=False,
            latency_ms=latency_ms,
            cost=0.0
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="imap",
            latency_ms=latency_ms,
            error=str(e)
        )


def probe_calendar() -> ProviderResult:
    """Probe CalDAV enterprise calendar server."""
    t0 = time.perf_counter()
    caldav_url = os.environ.get("CALDAV_URL")
    if not caldav_url:
        if _is_test_mode():
            return SandboxProvider("calendar", "caldav_sandbox").probe()
        return NotConfiguredProvider("calendar", "CALDAV_URL not configured").probe()

    try:
        req = urllib.request.Request(caldav_url, headers={"User-Agent": "ZONATA-Probe/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.OK,
                provider="caldav",
                provider_ref=f"caldav_{resp.status}",
                sandbox=False,
                latency_ms=latency_ms,
                cost=0.0
            )
    except urllib.error.HTTPError as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if e.code in (401, 403, 404, 200, 207):
            return ProviderResult(
                status=PortStatus.OK,
                provider="caldav",
                provider_ref=f"caldav_http_{e.code}",
                sandbox=False,
                latency_ms=latency_ms,
                cost=0.0
            )
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="caldav",
            latency_ms=latency_ms,
            error=str(e)
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="caldav",
            latency_ms=latency_ms,
            error=str(e)
        )


def probe_antivirus() -> ProviderResult:
    """Probe ClamAV network daemon (Port 3310)."""
    from core.ports.antivirus import resolve_antivirus_provider
    return resolve_antivirus_provider().probe()


def probe_text_extraction() -> ProviderResult:
    """Probe Apache Tika server (e.g. http://localhost:9998/version)."""
    from core.ports.text_extraction import resolve_text_extraction_provider
    return resolve_text_extraction_provider().probe()


def probe_ocr() -> ProviderResult:
    """Probe OCR capability (Tika Tesseract OCR / native OCR)."""
    from core.ports.ocr import resolve_ocr_provider
    return resolve_ocr_provider().probe()


def probe_search() -> ProviderResult:
    """Probe search indexing backend with a real HTTP reachability check."""
    t0 = time.perf_counter()
    search_endpoint = os.environ.get("SEARCH_ENDPOINT")
    search_provider = os.environ.get("SEARCH_PROVIDER", "custom")

    if not search_endpoint:
        if _is_test_mode():
            return SandboxProvider("search", "search_sandbox").probe()
        return NotConfiguredProvider(
            "search",
            "SEARCH_ENDPOINT not configured; a provider name alone is not a live check"
        ).probe()

    code, err = _http_get_status(search_endpoint, timeout=3.0)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    if code is not None and 200 <= code < 400:
        return ProviderResult(
            status=PortStatus.OK,
            provider=search_provider,
            provider_ref=f"search_http_{code}",
            sandbox=False,
            latency_ms=latency_ms,
            cost=0.0,
            metadata={"endpoint": search_endpoint, "http_status": code}
        )
    return ProviderResult(
        status=PortStatus.FAILED,
        provider=search_provider,
        provider_ref=None,
        sandbox=False,
        latency_ms=latency_ms,
        cost="UNMEASURED",
        error=f"Search endpoint unreachable or unhealthy: {err}"
    )


def probe_key_management() -> ProviderResult:
    """Probe Sovereign Key Management (AES-256-GCM / KMS)."""
    from core.ports.kms import resolve_kms_provider
    return resolve_kms_provider().probe()


def probe_llm() -> ProviderResult:
    """Probe LLM model provider and reality state."""
    t0 = time.perf_counter()
    provider = os.environ.get("ZONATA_LLM_PROVIDER", "").lower()
    is_prod = os.environ.get("APP_ENV") == "production"
    allow_degraded = os.environ.get("ZONATA_ALLOW_DEGRADED") == "1"

    if not provider:
        # Check standard API keys
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("GEMINI_API_KEY"):
            provider = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        elif _is_test_mode() or not is_prod or allow_degraded:
            provider = "embedded_free"
        else:
            return NotConfiguredProvider("llm", "No LLM API keys configured in environment").probe()

    latency_ms = (time.perf_counter() - t0) * 1000.0

    if provider == "embedded_free":
        if is_prod and allow_degraded:
            status = PortStatus.DEGRADED
        elif _is_test_mode():
            status = PortStatus.SANDBOX
        else:
            status = PortStatus.DEGRADED
        return ProviderResult(
            status=status,
            provider="embedded_free",
            provider_ref="heuristic_rule_engine",
            sandbox=True,
            latency_ms=latency_ms,
            cost=0.0,
            metadata={"model": "embedded_free_rule_engine", "degraded": True}
        )

    key_map = {
        "openai": os.environ.get("OPENAI_API_KEY"),
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "gemini": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
    }

    if provider in ("ollama", "local"):
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        code, err = _http_get_status(f"{base}/api/tags", timeout=3.0)
    elif provider in key_map and key_map[provider]:
        api_key = key_map[provider]
        if provider == "openai":
            code, err = _http_get_status(
                "https://api.openai.com/v1/models",
                {"Authorization": f"Bearer {api_key}"},
            )
        elif provider == "anthropic":
            code, err = _http_get_status(
                "https://api.anthropic.com/v1/models",
                {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            )
        else:
            code, err = _http_get_status(
                "https://generativelanguage.googleapis.com/v1beta/models?key="
                + urllib.parse.quote(api_key, safe=""),
            )
    else:
        return NotConfiguredProvider(
            "llm",
            f"No API key or verified endpoint configured for LLM provider '{provider}'"
        ).probe()

    latency_ms = (time.perf_counter() - t0) * 1000.0
    if code == 200:
        return ProviderResult(
            status=PortStatus.OK,
            provider=provider,
            provider_ref=f"llm_{provider}_models_200",
            sandbox=False,
            latency_ms=latency_ms,
            cost="UNMEASURED",
            metadata={"provider": provider, "verified": True}
        )
    return ProviderResult(
        status=PortStatus.FAILED,
        provider=provider,
        provider_ref=None,
        sandbox=False,
        latency_ms=latency_ms,
        cost="UNMEASURED",
        error=f"LLM provider probe failed: {err or 'unexpected status ' + str(code)}"
    )


def probe_browser() -> ProviderResult:
    """Probe browser control capability. Explicitly NOT_IMPLEMENTED."""
    return NotImplementedProvider(
        capability="browser",
        reason="Browser automation runtime is NOT_IMPLEMENTED in sovereign core"
    ).probe()


def probe_desktop_control() -> ProviderResult:
    """Probe desktop GUI control capability. Explicitly NOT_IMPLEMENTED."""
    return NotImplementedProvider(
        capability="desktop_control",
        reason="Desktop GUI automation runtime is NOT_IMPLEMENTED in sovereign core"
    ).probe()


def probe_payments() -> ProviderResult:
    """Probe enterprise payments provider."""
    t0 = time.perf_counter()
    stripe_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_key:
        if _is_test_mode():
            return SandboxProvider("payments", "stripe_sandbox").probe()
        return NotConfiguredProvider("payments", "STRIPE_API_KEY not configured").probe()

    # Harmless authenticated call: retrieve account balance (no money moves).
    code, err = _http_get_status(
        "https://api.stripe.com/v1/balance",
        {"Authorization": f"Bearer {stripe_key}"},
        timeout=4.0,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0
    if code == 200:
        return ProviderResult(
            status=PortStatus.OK,
            provider="stripe",
            provider_ref=f"stripe_balance_http_{code}",
            sandbox=False,
            latency_ms=latency_ms,
            cost="UNMEASURED",
            metadata={"verified": True}
        )
    return ProviderResult(
        status=PortStatus.FAILED,
        provider="stripe",
        provider_ref=None,
        sandbox=False,
        latency_ms=latency_ms,
        cost="UNMEASURED",
        error=f"Stripe credentials rejected or unreachable: {err or 'status ' + str(code)}"
    )


def probe_secrets() -> ProviderResult:
    """Probe the mediated secret store with a real store/retrieve round-trip."""
    t0 = time.perf_counter()
    probe_value = secrets.token_hex(16)
    try:
        from core.secrets import SecretManager
        probe_name = f"capability_probe_{probe_value[:8]}"
        ref = SecretManager.store_secret("__probe__", probe_name, probe_value)
        retrieved = SecretManager.get_secret(ref)
        SecretManager._SECRETS.pop(ref, None)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if retrieved == probe_value:
            return ProviderResult(
                status=PortStatus.OK,
                provider="mediated_secret_store",
                provider_ref=ref,
                sandbox=False,
                latency_ms=latency_ms,
                cost=0.0,
                metadata={"backend": "in_memory_mediated"}
            )
        raise RuntimeError("secret round-trip mismatch")
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="mediated_secret_store",
            provider_ref=None,
            sandbox=False,
            latency_ms=latency_ms,
            cost="UNMEASURED",
            error=f"Secret store probe failed: {str(e)}"
        )


def probe_workflow_engine() -> ProviderResult:
    """Probe durable workflow engine (Temporal / NATS / Embedded outbox)."""
    t0 = time.perf_counter()
    temporal_host = os.environ.get("TEMPORAL_HOST")
    nats_url = os.environ.get("NATS_URL")

    if temporal_host:
        try:
            h, p = temporal_host.split(":")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((h, int(p)))
            s.close()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.OK,
                provider="temporal",
                provider_ref=f"temporal_{temporal_host}",
                sandbox=False,
                latency_ms=latency_ms,
                cost=0.0
            )
        except Exception:
            pass

    if nats_url:
        try:
            # simple TCP handshake
            url_part = nats_url.replace("nats://", "")
            h, p = url_part.split(":")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((h, int(p)))
            s.close()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.OK,
                provider="nats",
                provider_ref=f"nats_{h}_{p}",
                sandbox=False,
                latency_ms=latency_ms,
                cost=0.0
            )
        except Exception:
            pass

    # Verify the embedded transactional outbox really exists and is queryable.
    try:
        from core.outbox import TransactionalOutbox
        from core.db import db
        TransactionalOutbox()
        conn = db.get_connection()
        row = conn.execute("SELECT COUNT(*) FROM af_outbox").fetchone()
        count = int(row[0]) if row else 0
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.OK,
            provider="embedded_transactional_outbox",
            provider_ref=f"outbox_events_{count}",
            sandbox=_is_test_mode(),
            latency_ms=latency_ms,
            cost=0.0,
            metadata={"outbox_table": "af_outbox", "event_count": count}
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="embedded_transactional_outbox",
            provider_ref=None,
            sandbox=False,
            latency_ms=latency_ms,
            cost="UNMEASURED",
            error=f"Transactional outbox probe failed: {str(e)}"
        )


def probe_mcp() -> ProviderResult:
    """Probe ZONATA's own governed MCP registry (not an external CLI directory)."""
    t0 = time.perf_counter()
    try:
        from core.db import db
        conn = db.get_connection()
        row = conn.execute("SELECT COUNT(*) FROM mcp_servers").fetchone()
        count = int(row[0]) if row else 0
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if count > 0:
            return ProviderResult(
                status=PortStatus.OK,
                provider="zonata_mcp_registry",
                provider_ref=f"mcp_db_servers_{count}",
                sandbox=False,
                latency_ms=latency_ms,
                cost=0.0,
                metadata={"registered_servers": count}
            )
        if _is_test_mode():
            return SandboxProvider("mcp", "mcp_sandbox").probe()
        return NotConfiguredProvider(
            "mcp", "No MCP servers registered in ZONATA registry"
        ).probe()
    except Exception as e:
        if _is_test_mode():
            return SandboxProvider("mcp", "mcp_sandbox").probe()
        return NotConfiguredProvider(
            "mcp", f"MCP registry not initialised: {str(e)}"
        ).probe()


def probe_observability() -> ProviderResult:
    """Probe observability by rendering the real Prometheus metrics registry."""
    t0 = time.perf_counter()
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    try:
        from core.observability_stack import sre_metrics
        exposition = sre_metrics.scrape_prometheus_format()
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if not exposition or "zonata_" not in exposition:
            raise RuntimeError("Prometheus registry rendered no zonata metrics")
        return ProviderResult(
            status=PortStatus.OK,
            provider="internal_prometheus_metrics",
            provider_ref=f"metrics_exposition_{len(exposition)}b",
            sandbox=False,
            latency_ms=latency_ms,
            cost=0.0,
            metadata={
                "exposition": "prometheus",
                "otel_endpoint_configured": bool(otel_endpoint),
                "otel_verified": False,
            }
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return ProviderResult(
            status=PortStatus.FAILED,
            provider="internal_prometheus_metrics",
            provider_ref=None,
            sandbox=False,
            latency_ms=latency_ms,
            cost="UNMEASURED",
            error=f"Observability probe failed: {str(e)}"
        )


PROBE_DISPATCH = {
    "database": probe_database,
    "storage": probe_storage,
    "email_out": probe_email_out,
    "email_in": probe_email_in,
    "calendar": probe_calendar,
    "antivirus": probe_antivirus,
    "text_extraction": probe_text_extraction,
    "ocr": probe_ocr,
    "search": probe_search,
    "key_management": probe_key_management,
    "llm": probe_llm,
    "browser": probe_browser,
    "desktop_control": probe_desktop_control,
    "payments": probe_payments,
    "secrets": probe_secrets,
    "workflow_engine": probe_workflow_engine,
    "mcp": probe_mcp,
    "observability": probe_observability,
}


def probe_all_capabilities() -> Dict[str, ProviderResult]:
    """Execute reality probes across all 18 standard enterprise capabilities."""
    results: Dict[str, ProviderResult] = {}
    for capability, probe_fn in PROBE_DISPATCH.items():
        try:
            results[capability] = probe_fn()
        except Exception as e:
            results[capability] = ProviderResult(
                status=PortStatus.FAILED,
                provider="probe_runner",
                provider_ref=None,
                sandbox=False,
                latency_ms=0.0,
                cost="UNMEASURED",
                error=f"Probe exception: {e}"
            )
    return results


def summarize_capabilities(results: Dict[str, ProviderResult]) -> Dict[str, int]:
    """Provide high-level summary counts for owner reporting."""
    counts = {
        "live": 0,
        "test_only": 0,
        "not_connected": 0,
        "degraded": 0,
        "not_implemented": 0,
        "failed": 0
    }
    for res in results.values():
        if res.status == PortStatus.OK:
            counts["live"] += 1
        elif res.status == PortStatus.SANDBOX:
            counts["test_only"] += 1
        elif res.status == PortStatus.NOT_CONFIGURED:
            counts["not_connected"] += 1
        elif res.status == PortStatus.DEGRADED:
            counts["degraded"] += 1
        elif res.status == PortStatus.NOT_IMPLEMENTED:
            counts["not_implemented"] += 1
        elif res.status == PortStatus.FAILED:
            counts["failed"] += 1
    return counts
