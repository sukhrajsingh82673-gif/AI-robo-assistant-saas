"""End-to-end smoke test for the URA UI shell (jsdom).

Boots an isolated API server, registers a fresh owner, then drives the real
front end through tests/ui_shell_smoke.js with jsdom. This is the gate for the
UI redesign phases: it proves the shell, live Overview data, settings,
command palette, Companies/Security/Approvals screens, hidden Terminal screen
and Arabic/RTL switching all still work together.

The test skips cleanly when Node or jsdom is unavailable so Python-only
environments are not blocked.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMOKE_SCRIPT = os.path.join(ROOT, "tests", "ui_shell_smoke.js")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, process: subprocess.Popen, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"API server exited early with code {process.returncode}")
        try:
            with urllib.request.urlopen(base_url + "/api/v1/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError) as exc:  # server still booting
            last_error = exc
        time.sleep(0.25)
    raise AssertionError(f"API server did not become healthy in {timeout}s: {last_error}")


def _post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for the UI smoke test")
def test_ura_ui_shell_smoke() -> None:
    if not os.path.exists(SMOKE_SCRIPT):
        pytest.fail(f"missing smoke script: {SMOKE_SCRIPT}")
    try:
        jsdom_check = subprocess.run(
            ["node", "-e", "require.resolve('jsdom')"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("timed out while checking for jsdom")
    if jsdom_check.returncode != 0:
        pytest.skip("jsdom is not installed (npm install --save-dev jsdom)")

    workdir = tempfile.mkdtemp(prefix="ura-ui-smoke-", dir=os.environ.get("URA_TMP_DIR") or None)
    db_path = os.path.join(workdir, "ui_smoke.db")
    auth_path = os.path.join(workdir, "auth.json")
    server_log = os.path.join(workdir, "server.log")
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = dict(os.environ)
    env.update(
        {
            "PORT": str(port),
            "ZONATA_TEST_MODE": "1",
            "ZONATA_DB_PATH": db_path,
            "ZONATA_SESSION_TEST_DB": db_path,
            "PYTHONUNBUFFERED": "1",
        }
    )

    log_handle = open(server_log, "w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-u", "api_server.py"],
        cwd=ROOT,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    try:
        try:
            _wait_for_health(base_url, process)
        except AssertionError:
            log_handle.flush()
            with open(server_log, "r", encoding="utf-8", errors="replace") as handle:
                tail = handle.read()[-4000:]
            pytest.fail(f"isolated API server failed to start. Last log lines:\n{tail}")

        registration = _post_json(
            base_url + "/api/auth/register",
            {
                "name": "UI Smoke Owner",
                "email": f"ui-smoke-{int(time.time() * 1000)}@example.com",
                "password": "SmokeTestPassword123!",
                "tenant_name": "UI Smoke Enterprise",
            },
        )
        assert registration.get("token"), f"registration returned no token: {registration}"
        assert registration.get("user"), f"registration returned no user: {registration}"

        # A freshly registered owner has no company in the operating portfolio
        # yet. Onboard one so the shell has a real company context to render.
        onboarded = _post_json(
            base_url + "/api/onboard",
            {
                "name": "UI Smoke Enterprise",
                "industry": "Software",
                "business_model": "Subscription",
            },
            token=registration["token"],
        )
        company_id = onboarded.get("company_id")
        assert company_id, f"onboarding returned no company id: {onboarded}"
        registration["user"]["company_id"] = company_id

        with open(auth_path, "w", encoding="utf-8") as handle:
            json.dump(registration, handle)

        node_env = dict(os.environ)
        node_env.update({"URA_BASE_URL": base_url, "URA_AUTH_FILE": auth_path})
        run = subprocess.run(
            ["node", SMOKE_SCRIPT],
            cwd=ROOT,
            env=node_env,
            capture_output=True,
            text=True,
            timeout=420,
        )
        output = (run.stdout or "") + ("\n" + run.stderr if run.stderr else "")
        assert run.returncode == 0, f"UI smoke test failed (exit {run.returncode}):\n{output}"
        assert "RESULT: all checks passed" in output, f"UI smoke test did not pass all checks:\n{output}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        log_handle.close()
        shutil.rmtree(workdir, ignore_errors=True)
