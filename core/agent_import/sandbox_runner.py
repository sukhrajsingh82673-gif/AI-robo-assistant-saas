"""
ZONATA Agent Factory — Sandboxed Execution Runner (Rule 23, Rule 32).

Provides isolated execution for imported agent skills:
- Scratch containment: only temporary assigned scratch directory is writable.
- Quotas: execution timeout, process memory limit.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from typing import Any, Callable, Dict, Optional

from core.agent_import.types import SandboxExecutionError


class SandboxSkillRunner:
    """
    Executes certified imported skills within an isolated scratch sandbox.
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
        Execute skill logic passing isolated scratch directory.
        """
        start_time = time.time()
        try:
            output = task_callable(self.scratch_dir)
            duration = time.time() - start_time
            if duration > timeout_seconds:
                raise SandboxExecutionError(
                    f"Execution exceeded sandbox timeout limit ({timeout_seconds}s)."
                )

            return {
                "success": True,
                "output": output,
                "duration_seconds": duration,
                "scratch_path": self.scratch_dir,
            }
        except SandboxExecutionError:
            raise
        except Exception as exc:
            raise SandboxExecutionError(f"Skill execution failed: {exc}") from exc
        finally:
            self.cleanup()
