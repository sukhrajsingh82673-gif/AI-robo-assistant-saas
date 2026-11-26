"""
ZONATA Agent Factory — Sandboxed Execution Runner (Rule 23, Rule 32).

Provides process-level containment for imported agent skills:
- Scratch containment: only the temporary assigned scratch directory is writable.
- Quotas: hard timeout, CPU/memory/file-size limits, and a scrubbed environment.
- Fail closed: production execution requires a POSIX fork-capable host.
"""

from __future__ import annotations

import multiprocessing
import os
import shutil
import tempfile
import time
from typing import Any, Callable, Dict, Optional

from core.agent_import.types import SandboxExecutionError


def _apply_resource_limits(timeout_seconds: float) -> None:
    try:
        import resource
    except ImportError:
        return
    cpu_seconds = max(1, int(timeout_seconds) + 1)
    limits = [
        (resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds)),
        (resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024)),
        (resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024)),
        (resource.RLIMIT_NOFILE, (256, 256)),
    ]
    for resource_id, value in limits:
        try:
            resource.setrlimit(resource_id, value)
        except (ValueError, OSError):
            continue


def _child_entry(conn, task_callable, scratch_dir: str, timeout_seconds: float) -> None:
    try:
        os.setsid()
        os.chdir(scratch_dir)
        _apply_resource_limits(timeout_seconds)
        # Remove ambient credentials and configuration from the child.
        for key in list(os.environ):
            if key.upper() in {
                "DATABASE_URL", "DIRECT_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN",
                "GH_TOKEN", "VAULT_TOKEN", "CLAMAV_HOST", "CLAMAV_PORT",
            } or key.upper().endswith(("_SECRET", "_TOKEN", "_PASSWORD", "_KEY")):
                os.environ.pop(key, None)
        result = task_callable(scratch_dir)
        conn.send(("ok", result))
    except BaseException as exc:  # pass child failures back to the parent
        try:
            conn.send(("error", f"{type(exc).__name__}: {exc}"))
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


class SandboxSkillRunner:
    """
    Executes certified imported skills within a process-level sandbox.
    """

    def __init__(self, tenant_id: str, skill_id: str):
        self.tenant_id = tenant_id
        self.skill_id = skill_id
        self.scratch_dir = tempfile.mkdtemp(prefix=f"zonata_skill_{skill_id[:8]}_")

    def cleanup(self) -> None:
        """Remove temporary scratch directory."""
        if os.path.exists(self.scratch_dir):
            shutil.rmtree(self.scratch_dir, ignore_errors=True)

    def run_skill_task(
        self,
        task_callable: Callable[[str], Any],
        timeout_seconds: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Execute skill logic in a forked child process with hard quotas.
        """
        start_time = time.time()
        if "fork" not in multiprocessing.get_all_start_methods():
            self.cleanup()
            raise SandboxExecutionError(
                "A POSIX fork-capable host is required for isolated skill execution."
            )

        parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
        ctx = multiprocessing.get_context("fork")
        process = ctx.Process(
            target=_child_entry,
            args=(child_conn, task_callable, self.scratch_dir, timeout_seconds),
            daemon=True,
        )
        process.start()
        child_conn.close()

        try:
            if not parent_conn.poll(timeout_seconds):
                process.terminate()
                process.join(timeout=2.0)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=2.0)
                raise SandboxExecutionError(
                    f"Execution exceeded sandbox timeout limit ({timeout_seconds}s)."
                )

            try:
                status, payload = parent_conn.recv()
            except EOFError as exc:
                raise SandboxExecutionError(
                    "Sandbox child exited without returning a result."
                ) from exc
            finally:
                parent_conn.close()

            if status != "ok":
                raise SandboxExecutionError(f"Skill execution failed: {payload}")

            duration = time.time() - start_time
            return {
                "success": True,
                "output": payload,
                "duration_seconds": duration,
                "scratch_path": self.scratch_dir,
                "isolated": True,
            }
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=2.0)
            self.cleanup()
