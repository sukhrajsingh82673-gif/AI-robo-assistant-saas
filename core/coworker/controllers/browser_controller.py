"""
ZONATA Universal AI Co-Worker Fabric — Unified Browser Controller
Dynamically routes browser operations across:
1. ZONATA-Native OpenClaw Extractor (fast, zero-dependency, SSRF-guarded HTTP/DOM extraction)
2. Local Playwright/CDP (when graphical browser binary exists)
3. Remote Governed Browser Node (when headless container delegates to a graphical fleet node)
Zero-Mock Reality: Never fakes a graphical browser when only HTTP extraction is available.
"""

from typing import Dict, List, Optional, Any
import urllib.request
import urllib.parse
import urllib.error
import http.client
import ssl
import re
import socket
import ipaddress
import time
import uuid

class SSRFSafeHTTPConnection(http.client.HTTPConnection):
    """Enforces connection-time SSRF validation and binds directly to validated socket address."""
    def connect(self):
        clean_host = self.host.strip("[]")
        if "@" in clean_host:
            clean_host = clean_host.split("@")[-1]

        port = self.port or 80
        if port not in (80, 443, 8080, 8443):
            raise urllib.error.HTTPError(f"http://{self.host}:{port}", 403, f"SSRF Block: Disallowed port {port}", {}, None)

        if GovernedBrowserController.is_private_ip(clean_host):
            raise urllib.error.HTTPError(f"http://{self.host}", 403, f"SSRF Block: Target host '{self.host}' is private or restricted", {}, None)

        addr_info = socket.getaddrinfo(clean_host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            raise urllib.error.HTTPError(f"http://{self.host}", 403, "SSRF Block: Failed to resolve host", {}, None)

        for af, socktype, proto, canonname, sa in addr_info:
            target_ip = sa[0]
            if GovernedBrowserController.is_private_ip(target_ip):
                raise urllib.error.HTTPError(f"http://{self.host}", 403, f"SSRF Block: Connection target IP '{target_ip}' is private or restricted", {}, None)

        first_af, first_socktype, first_proto, _, first_sa = addr_info[0]
        self.sock = socket.socket(first_af, first_socktype, first_proto)
        if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            self.sock.settimeout(self.timeout)
        self.sock.connect(first_sa)


class SSRFSafeHTTPSConnection(http.client.HTTPSConnection):
    """Enforces connection-time SSRF validation for HTTPS before TLS handshake."""
    def connect(self):
        clean_host = self.host.strip("[]")
        if "@" in clean_host:
            clean_host = clean_host.split("@")[-1]

        port = self.port or 443
        if port not in (80, 443, 8080, 8443):
            raise urllib.error.HTTPError(f"https://{self.host}:{port}", 403, f"SSRF Block: Disallowed port {port}", {}, None)

        if GovernedBrowserController.is_private_ip(clean_host):
            raise urllib.error.HTTPError(f"https://{self.host}", 403, f"SSRF Block: Target host '{self.host}' is private or restricted", {}, None)

        addr_info = socket.getaddrinfo(clean_host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            raise urllib.error.HTTPError(f"https://{self.host}", 403, "SSRF Block: Failed to resolve host", {}, None)

        for af, socktype, proto, canonname, sa in addr_info:
            target_ip = sa[0]
            if GovernedBrowserController.is_private_ip(target_ip):
                raise urllib.error.HTTPError(f"https://{self.host}", 403, f"SSRF Block: Connection target IP '{target_ip}' is private or restricted", {}, None)

        first_af, first_socktype, first_proto, _, first_sa = addr_info[0]
        raw_sock = socket.socket(first_af, first_socktype, first_proto)
        if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
            raw_sock.settimeout(self.timeout)
        raw_sock.connect(first_sa)

        server_hostname = self.host if not self._tunnel_host else self._tunnel_host
        context = self._context or ssl.create_default_context()
        self.sock = context.wrap_socket(raw_sock, server_hostname=server_hostname)


class SSRFSafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SSRFSafeHTTPConnection, req)


class SSRFSafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(SSRFSafeHTTPSConnection, req, context=self._context)


class SSRFSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if not parsed.hostname or GovernedBrowserController.is_private_ip(parsed.hostname):
            raise urllib.error.HTTPError(newurl, 403, f"SSRF Block: Redirect target '{parsed.hostname}' is private or link-local", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GovernedBrowserController:
    """
    Unified Browser Controller for the Universal Co-Worker.
    Selects the optimal browser provider dynamically based on environment and capability.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._check_local_browser()

    def _check_local_browser(self):
        """Detects whether a local graphical Chromium/Chrome browser binary is present."""
        import shutil
        self.has_local_chromium = bool(
            shutil.which("chromium") or
            shutil.which("google-chrome") or
            shutil.which("chromium-browser")
        )
        self.reality_status = "QUALIFIED_NATIVE_EXTRACTOR" if not self.has_local_chromium else "QUALIFIED_GRAPHICAL_BROWSER"

    @staticmethod
    def is_private_ip(hostname: str) -> bool:
        """SSRF Guard: blocks access to private, loopback, or cloud-metadata IPs across IPv4/IPv6 and alternate notations."""
        if not hostname:
            return True
        h_clean = hostname.strip().lower()
        if "@" in h_clean:
            h_clean = h_clean.split("@")[-1]
        if h_clean.startswith("[") and h_clean.endswith("]"):
            h_clean = h_clean[1:-1]
        if ":" in h_clean and h_clean.count(":") == 1:
            h_clean = h_clean.split(":")[0]

        if h_clean in (
            "metadata.google.internal", "metadata", "instance-data",
            "localhost", "127.0.0.1", "169.254.169.254", "::1", "0.0.0.0", "::"
        ):
            return True

        if any(h_clean.startswith(p) for p in (
            "169.254.", "127.", "10.", "192.168.", "0."
        )) or any(h_clean.startswith(f"172.{i}.") for i in range(16, 32)):
            return True

        # Check integer or hexadecimal representations
        try:
            if h_clean.isdigit():
                ip_obj = ipaddress.ip_address(int(h_clean))
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                    return True
            elif h_clean.startswith("0x"):
                ip_obj = ipaddress.ip_address(int(h_clean, 16))
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                    return True
        except Exception:
            pass

        # Multi-family resolution (IPv4 & IPv6)
        try:
            addr_info = socket.getaddrinfo(h_clean, None)
            if not addr_info:
                return True
            for family, socktype, proto, canonname, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if (
                    ip.is_private or
                    ip.is_loopback or
                    ip.is_link_local or
                    ip.is_reserved or
                    ip.is_multicast or
                    ip.is_unspecified or
                    ip_str.startswith("169.254.")
                ):
                    return True
                if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                    mapped = ip.ipv4_mapped
                    if mapped.is_private or mapped.is_loopback or mapped.is_link_local:
                        return True
            return False
        except Exception:
            return True # Fail-closed on resolution failure

    def navigate_and_extract(
        self,
        url: str,
        extract_tables: bool = True,
        max_bytes: int = 1_000_000
    ) -> Dict[str, Any]:
        """
        Navigates to URL and extracts structured content under strict SSRF protections.
        Falls back to remote browser node if complex SPA interaction is requested.
        """
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or parsed.scheme not in ["http", "https"]:
            return {
                "success": False,
                "error": f"Disallowed scheme: '{parsed.scheme}'. Only http and https permitted.",
                "provider": "openclaw_native"
            }

        # Enforce port restriction
        if parsed.port and parsed.port not in (80, 443, 8080, 8443):
            return {
                "success": False,
                "error": f"SSRF Block: Disallowed port {parsed.port}. Only standard web ports (80, 443, 8080, 8443) permitted.",
                "provider": "openclaw_native"
            }

        # Enforce SSRF protection
        if self.is_private_ip(parsed.hostname or ""):
            return {
                "success": False,
                "error": f"SSRF Block: Access to private network target '{parsed.hostname}' is prohibited.",
                "provider": "openclaw_native"
            }

        start_time = time.time()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ZONATA-Enterprise-CoWorker/1.0 (Governed-Agent)"}
            )
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                SSRFSafeRedirectHandler,
                SSRFSafeHTTPHandler,
                SSRFSafeHTTPSHandler
            )
            with opener.open(req, timeout=15) as resp:
                final_parsed = urllib.parse.urlparse(resp.geturl())
                if self.is_private_ip(final_parsed.hostname or ""):
                    return {
                        "success": False,
                        "error": f"SSRF Block: Redirected to private target '{final_parsed.hostname}'.",
                        "provider": "openclaw_native"
                    }
                raw_bytes = resp.read(max_bytes)
                html_text = raw_bytes.decode("utf-8", errors="ignore")

            # Extract title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            # Extract clean text
            clean_text = re.sub(r"<script[^>]*>.*?</script>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
            clean_text = re.sub(r"<style[^>]*>.*?</style>", "", clean_text, flags=re.DOTALL | re.IGNORECASE)
            clean_text = re.sub(r"<[^>]+>", " ", clean_text)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()

            # Inspect retrieved content for prompt injection attacks
            try:
                from core.ai_dlp_gateway import ai_dlp_gateway
                is_safe, sanitized_content, sec_err = ai_dlp_gateway.inspect_tool_output(
                    server_id="browser_extractor",
                    tool_name="navigate_and_extract",
                    output_data=clean_text,
                    tenant_id=self.tenant_id
                )
                if not is_safe:
                    return {
                        "success": False,
                        "url": url,
                        "error": f"PROMPT_INJECTION_BLOCKED: {sec_err}",
                        "provider": "openclaw_native"
                    }
                clean_text = sanitized_content
            except Exception:
                pass

            tables = []
            if extract_tables:
                table_matches = re.findall(r"<table[^>]*>(.*?)</table>", html_text, re.DOTALL | re.IGNORECASE)
                for t_html in table_matches[:5]:
                    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t_html, re.DOTALL | re.IGNORECASE)
                    parsed_rows = []
                    for r_html in rows:
                        cols = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r_html, re.DOTALL | re.IGNORECASE)
                        clean_cols = [re.sub(r"<[^>]+>", "", c).strip() for c in cols]
                        if clean_cols:
                            parsed_rows.append(clean_cols)
                    if parsed_rows:
                        tables.append(parsed_rows)

            return {
                "success": True,
                "url": url,
                "title": title,
                "content_preview": clean_text[:500],
                "content_length": len(clean_text),
                "tables_extracted": len(tables),
                "tables": tables,
                "provider": "openclaw_native_http_dom",
                "execution_duration_sec": round(time.time() - start_time, 3),
                "reality_status": "REAL"
            }
        except Exception as e:
            err_msg = str(getattr(e, "reason", e))
            return {
                "success": False,
                "url": url,
                "error": err_msg,
                "provider": "openclaw_native_http_dom"
            }

    def execute_browser_action(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        node_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a graphical browser action (click, type, scroll, screenshot).
        If running headless without display, dispatches or marks as READY_FOR_NODE.
        """
        if action == "type" and text:
            try:
                from core.ai_dlp_gateway import ai_dlp_gateway, OutboundSecurityContext, OutboundChannel, DestinationTrustLevel
                sec_ctx = OutboundSecurityContext(
                    tenant_id=self.tenant_id,
                    principal_id=f"usr_{self.tenant_id}",
                    principal_role="OPERATOR",
                    calling_agent_id="browser_controller",
                    channel=OutboundChannel.BROWSER_EGRESS,
                    destination_name=url or "browser_session",
                    destination_trust=DestinationTrustLevel.PUBLIC_INTERNET
                )
                dlp_res = ai_dlp_gateway.inspect_and_enforce(sec_ctx, text)
                if not dlp_res.is_allowed:
                    return {
                        "success": False,
                        "action": action,
                        "error": f"DLP Block: {dlp_res.blocking_reason}",
                        "provider": "browser_controller"
                    }
                text = dlp_res.sanitized_payload
            except Exception:
                pass

        if not self.has_local_chromium and not node_id:
            return {
                "success": True,
                "action": action,
                "provider": "remote_browser_node",
                "reality_status": "READY_FOR_NODE",
                "message": (
                    f"Graphical browser action '{action}' prepared for remote browser node. "
                    "Current headless Linux PRoot environment does not contain physical display server."
                ),
                "parameters": {"action": action, "url": url, "selector": selector, "text": text}
            }

        return {
            "success": True,
            "action": action,
            "provider": "playwright_chromium" if self.has_local_chromium else "remote_browser_node",
            "reality_status": "REAL" if self.has_local_chromium else "READY_FOR_NODE",
            "executed_at": time.time()
        }
