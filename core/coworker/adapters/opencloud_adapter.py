"""
ZONATA Autonomous Coworker 2.0 — OpenCloud Remote Node Adapter
Executes desktop computer-use commands across remote headless cloud instances
(AWS EC2, GCP, Azure, Bare-metal nodes) via governed agent protocol.
"""

from __future__ import annotations
import time
import json
import os
import urllib.request
import urllib.error
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from ..computer_use_engine import ComputerUseEngine


class OpenCloudAdapter:
    """
    Binds ComputerUseEngine to remote headless cloud instances.
    Coordinates telemetry heartbeats, display buffers, and remote session state.
    """

    def __init__(
        self,
        node_endpoint: str = "http://127.0.0.1:9099",
        auth_token: Optional[str] = None,
        local_fallback_engine: Optional[ComputerUseEngine] = None
    ):
        self.node_endpoint = node_endpoint.rstrip("/")
        self.auth_token = auth_token or os.environ.get("OPENCLOUD_AUTH_TOKEN")
        self.fallback_engine = local_fallback_engine or ComputerUseEngine()
        self.is_connected = False
        self.remote_metadata: Dict[str, Any] = {
            "platform": "linux",
            "arch": "x86_64",
            "resolution": "1920x1080",
            "xvfb_active": True
        }

    def check_connection(self, timeout: float = 2.0) -> bool:
        """Pings remote worker node /health endpoint."""
        try:
            req = urllib.request.Request(f"{self.node_endpoint}/health")
            if self.auth_token:
                req.add_header("Authorization", f"Bearer {self.auth_token}")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                self.is_connected = (resp.status == 200 and data.get("status") == "OK")
                if "metadata" in data:
                    self.remote_metadata.update(data["metadata"])
                return self.is_connected
        except Exception:
            self.is_connected = False
            return False

    def connect(self) -> bool:
        """Establishes handshake with remote cloud worker node."""
        return self.check_connection()

    def dispatch_primitive(
        self,
        primitive_name: str,
        parameters: Dict[str, Any],
        allow_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Dispatches primitive action to remote cloud node over HTTP POST /dispatch.
        If node is unreachable:
          - if allow_fallback=True: executes via local engine, labeling output as LOCAL_FALLBACK.
          - if allow_fallback=False: reports BLOCKED_BY_EXTERNAL_DEPENDENCY.
        """
        # If node is reachable, dispatch over real HTTP to remote worker
        if self.is_connected or self.connect():
            try:
                payload = json.dumps({"primitive": primitive_name, "parameters": parameters}).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.node_endpoint}/dispatch",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                if self.auth_token:
                    req.add_header("Authorization", f"Bearer {self.auth_token}")
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    remote_res = json.loads(resp.read().decode())
                    return {
                        "success": True,
                        "remote_dispatched": True,
                        "node": self.node_endpoint,
                        "result": remote_res.get("result", remote_res)
                    }
            except Exception as e:
                self.is_connected = False
                if not allow_fallback:
                    return {
                        "success": False,
                        "status": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                        "error": f"Remote node dispatch failed: {str(e)}",
                        "node": self.node_endpoint
                    }

        # Handle fallback when remote is unreachable
        if not allow_fallback:
            return {
                "success": False,
                "status": "BLOCKED_BY_EXTERNAL_DEPENDENCY",
                "error": f"OpenCloud node at {self.node_endpoint} is offline",
                "node": self.node_endpoint
            }

        # Fallback to local engine with honest labeling
        action_method = getattr(self.fallback_engine, primitive_name, None)
        if callable(action_method):
            try:
                if primitive_name in ("click", "double_click", "right_click", "move"):
                    x = parameters.get("x", 0)
                    y = parameters.get("y", 0)
                    res = action_method(x, y)
                elif primitive_name == "type_text":
                    res = action_method(parameters.get("text", ""))
                else:
                    res = action_method()
                return {
                    "success": True,
                    "remote_dispatched": False,
                    "execution_source": "LOCAL_FALLBACK",
                    "result": res,
                    "node": self.node_endpoint
                }
            except Exception as e:
                return {
                    "success": False,
                    "remote_dispatched": False,
                    "execution_source": "LOCAL_FALLBACK",
                    "error": str(e),
                    "node": self.node_endpoint
                }

        return {"success": False, "error": f"Unsupported primitive: {primitive_name}"}

    def capture_remote_screenshot(self) -> bytes:
        """Retrieves current frame buffer from remote instance or local fallback."""
        if self.is_connected:
            try:
                req = urllib.request.Request(f"{self.node_endpoint}/screenshot")
                if self.auth_token:
                    req.add_header("Authorization", f"Bearer {self.auth_token}")
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    return resp.read()
            except Exception:
                pass
        return self.fallback_engine.screenshot()


class _OpenCloudWorkerHTTPHandler(BaseHTTPRequestHandler):
    """Embedded HTTP handler simulating or serving a real OpenCloud remote worker node."""

    engine: ComputerUseEngine = None

    def log_message(self, format, *args):
        pass  # suppress noisy stdout

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = json.dumps({"status": "OK", "metadata": {"platform": "linux", "xvfb_active": True}}).encode()
            self.wfile.write(resp)
        elif self.path == "/screenshot":
            png = self.engine.screenshot() if self.engine else b"\x89PNG\r\n\x1a\n"
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(png)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/dispatch":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode("utf-8")) if body else {}
            prim = data.get("primitive", "observe")
            params = data.get("parameters", {})
            action_method = getattr(self.engine, prim, None)
            res = {}
            if callable(action_method):
                if prim in ("click", "double_click", "right_click", "move"):
                    res = action_method(params.get("x", 0), params.get("y", 0))
                elif prim == "type_text":
                    res = action_method(params.get("text", ""))
                else:
                    res = action_method()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "primitive": prim, "result": res}).encode())
        else:
            self.send_response(404)
            self.end_headers()


class OpenCloudMockWorkerServer:
    """Test utility to run an actual local HTTP worker server for OpenCloud integration tests."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9199, engine: Optional[ComputerUseEngine] = None):
        self.host = host
        self.port = port
        self.engine = engine or ComputerUseEngine()
        _OpenCloudWorkerHTTPHandler.engine = self.engine
        self.server = HTTPServer((self.host, self.port), _OpenCloudWorkerHTTPHandler)
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
