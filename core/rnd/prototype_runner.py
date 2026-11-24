"""
Sandboxed Prototype Runner Engine
=================================
Executes experimental prototypes in an isolated subprocess with strict resource bounds:
- CPU execution timeout
- Environment variable isolation (zero host secrets exposed, Rule 41)
- Standard output and error stream capture
- Produced artifact hashing and extraction
"""

import subprocess
import sys
import tempfile
import os
import hashlib
import time
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PrototypeExecutionRequest(BaseModel):
    code: str
    timeout_seconds: float = Field(5.0, le=60.0)
    mock_env_vars: Dict[str, str] = Field(default_factory=dict)
    expected_artifacts: List[str] = Field(default_factory=list)


class PrototypeExecutionResult(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    execution_time_seconds: float
    timed_out: bool
    artifact_hashes: Dict[str, str] = Field(default_factory=dict)


class SandboxedPrototypeRunner:
    """Executes prototype scripts within an isolated temporary sandbox."""

    def execute_prototype(self, request: PrototypeExecutionRequest) -> PrototypeExecutionResult:
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_path = os.path.join(tmp_dir, "prototype.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(request.code)

            # Scrubbed environment (Rule 41: no host secrets passed)
            clean_env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONPATH": tmp_dir,
                "ZONATA_SANDBOX": "1"
            }
            clean_env.update(request.mock_env_vars)

            start_time = time.time()
            timed_out = False
            exit_code = 0
            stdout_str = ""
            stderr_str = ""

            try:
                proc = subprocess.run(
                    [sys.executable, script_path],
                    cwd=tmp_dir,
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    timeout=request.timeout_seconds
                )
                exit_code = proc.returncode
                stdout_str = proc.stdout
                stderr_str = proc.stderr
            except subprocess.TimeoutExpired as e:
                timed_out = True
                exit_code = -1
                stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                stderr_str = "Execution timed out"

            duration = round(time.time() - start_time, 3)

            # Capture artifact hashes
            artifacts: Dict[str, str] = {}
            for fname in request.expected_artifacts:
                fpath = os.path.join(tmp_dir, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as af:
                        artifacts[fname] = hashlib.sha256(af.read()).hexdigest()

            return PrototypeExecutionResult(
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                execution_time_seconds=duration,
                timed_out=timed_out,
                artifact_hashes=artifacts
            )
