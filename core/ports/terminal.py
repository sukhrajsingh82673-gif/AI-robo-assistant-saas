"""
ZONATA Sovereign Core — Terminal Port & Execution Engine (Rule 23, 26, 27).
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, Optional

from core.ports.base import Port, PortStatus, ProviderResult
from core.terminal.classifier import CommandClassifier
from core.terminal.types import (
    CommandTier,
    DangerousCommandForbiddenError,
    HighImpactApprovalRequiredError,
    TerminalCommandResult,
    TerminalDisabledError,
)


class BaseTerminalProvider:
    @property
    def name(self) -> str:
        return "base_terminal"

    def execute(
        self,
        command: str,
        is_human_approved: bool = False,
        timeout_seconds: float = 30.0,
    ) -> TerminalCommandResult:
        raise NotImplementedError


class SandboxTerminalProvider(BaseTerminalProvider):
    @property
    def name(self) -> str:
        return "sandbox_terminal"

    def execute(
        self,
        command: str,
        is_human_approved: bool = False,
        timeout_seconds: float = 30.0,
    ) -> TerminalCommandResult:
        tier = CommandClassifier.classify(command)
        if tier == CommandTier.FORBIDDEN_DENIED:
            raise DangerousCommandForbiddenError(
                f"Command '{command}' is classified as FORBIDDEN_DENIED by sovereign security policy."
            )
        if tier == CommandTier.HIGH_IMPACT and not is_human_approved:
            raise HighImpactApprovalRequiredError(
                f"Command '{command}' is classified as HIGH_IMPACT and requires human approval."
            )

        start_time = time.time()
        stdout_sim = f"simulated_output_for: {command}\n"
        delimited = (
            f"<<<TERMINAL_OUTPUT command='{command}' exit_code=0>>>\n"
            f"{stdout_sim}"
            f"<<<END_TERMINAL_OUTPUT>>>"
        )

        return TerminalCommandResult(
            status=PortStatus.OK,
            provider=self.name,
            provider_ref=f"sandbox_term_{int(time.time())}",
            sandbox=True,
            latency_ms=(time.time() - start_time) * 1000,
            command=command,
            tier=tier,
            exit_code=0,
            stdout=stdout_sim,
            stderr="",
            delimited_output=delimited,
        )


class LocalTerminalProvider(BaseTerminalProvider):
    @property
    def name(self) -> str:
        return "local_terminal"

    def execute(
        self,
        command: str,
        is_human_approved: bool = False,
        timeout_seconds: float = 30.0,
    ) -> TerminalCommandResult:
        tier = CommandClassifier.classify(command)
        if tier == CommandTier.FORBIDDEN_DENIED:
            raise DangerousCommandForbiddenError(
                f"Command '{command}' is classified as FORBIDDEN_DENIED by sovereign security policy."
            )
        if tier == CommandTier.HIGH_IMPACT and not is_human_approved:
            raise HighImpactApprovalRequiredError(
                f"Command '{command}' is classified as HIGH_IMPACT and requires human approval."
            )

        start_time = time.time()
        killed = False
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = f"TIMEOUT: Execution exceeded {timeout_seconds}s limit."
            exit_code = 124
            killed = True

        delimited = (
            f"<<<TERMINAL_OUTPUT command='{command}' exit_code={exit_code}>>>\n"
            f"{stdout}\n{stderr}".rstrip() + "\n"
            f"<<<END_TERMINAL_OUTPUT>>>"
        )

        return TerminalCommandResult(
            status=PortStatus.OK,
            provider=self.name,
            provider_ref=f"local_term_{int(time.time())}",
            sandbox=False,
            latency_ms=(time.time() - start_time) * 1000,
            command=command,
            tier=tier,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            delimited_output=delimited,
            killed_by_signal=killed,
        )


class TerminalPort(Port):
    name = "terminal"
    capability = "terminal"

    def __init__(self):
        super().__init__(provider_name="terminal_default", sandbox=False)
        self.sandbox_provider = SandboxTerminalProvider()
        self.local_provider = LocalTerminalProvider()

    def is_enabled(self) -> bool:
        # Terminal defaults to OFF (Setting: TERMINAL_ENABLED=0)
        return os.environ.get("TERMINAL_ENABLED") == "1"

    def probe(self) -> ProviderResult:
        is_test = os.environ.get("ZONATA_TEST_MODE") == "1"
        if is_test:
            return ProviderResult(
                status=PortStatus.SANDBOX,
                provider=self.sandbox_provider.name,
                provider_ref=f"sandbox_terminal_{int(time.time())}",
                sandbox=True,
            )
        if not self.is_enabled():
            return ProviderResult(
                status=PortStatus.NOT_CONFIGURED,
                provider="disabled_terminal",
                provider_ref=None,
                sandbox=False,
                error="Terminal capability is disabled by default (TERMINAL_ENABLED=0).",
            )
        return ProviderResult(
            status=PortStatus.OK,
            provider=self.local_provider.name,
            provider_ref=f"local_terminal_{int(time.time())}",
            sandbox=False,
        )

    def execute(
        self,
        command: str,
        tenant_id: str,
        company_id: str,
        is_human_approved: bool = False,
        timeout_seconds: float = 30.0,
    ) -> TerminalCommandResult:
        is_test = os.environ.get("ZONATA_TEST_MODE") == "1"
        if not is_test and not self.is_enabled():
            raise TerminalDisabledError(
                "Terminal execution is disabled. Enable TERMINAL_ENABLED=1 to permit governed terminal execution."
            )

        provider = self.sandbox_provider if is_test else self.local_provider
        return provider.execute(
            command=command,
            is_human_approved=is_human_approved,
            timeout_seconds=timeout_seconds,
        )


terminal_port = TerminalPort()
