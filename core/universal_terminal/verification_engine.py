"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Verification Engine
Enforces independent postcondition verification.
Mandatory Invariant: EXIT CODE 0 != TASK SUCCESS.
Distinguishes: COMMAND_EXECUTED, COMMAND_SUCCEEDED, TASK_VERIFIED, BUSINESS_OBJECTIVE_ACHIEVED.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import hashlib
import subprocess
import time
import urllib.request
import json
import logging

from .models import (
    SemanticExecutionState, VerificationPostcondition, TerminalSession
)

logger = logging.getLogger("zonata.terminal.verification")

class TerminalVerificationEngine:
    """
    Independent Verification Engine.
    Validates real postconditions using empirical ground truth, not self-narrative.
    """

    @classmethod
    def verify_postconditions(
        cls,
        session: TerminalSession,
        postconditions: List[VerificationPostcondition]
    ) -> Tuple[bool, List[VerificationPostcondition]]:
        """Evaluates each postcondition independently."""
        all_passed = True
        evaluated = []

        for cond in postconditions:
            cond_passed, actual_val, detail = cls._evaluate_condition(cond)
            cond.passed = cond_passed
            cond.actual_value = actual_val
            cond.evidence_detail = detail
            if not cond_passed:
                all_passed = False
            evaluated.append(cond)
            session.log(f"Verification '{cond.name}': {'PASSED' if cond_passed else 'FAILED'} ({detail})")

        return all_passed, evaluated

    @classmethod
    def _evaluate_condition(cls, cond: VerificationPostcondition) -> Tuple[bool, Any, str]:
        c_type = cond.check_type
        exp = cond.expected_value

        # 1. FILE_EXISTS
        if c_type == "FILE_EXISTS":
            path = str(exp)
            exists = os.path.exists(path)
            detail = f"File {path} exists={exists}"
            return exists, exists, detail

        # 2. FILE_SHA256
        elif c_type == "FILE_SHA256":
            path, expected_hash = exp if isinstance(exp, (list, tuple)) else (exp, "")
            if not os.path.exists(path):
                return False, None, f"File {path} does not exist for SHA-256 check."
            with open(path, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            passed = (actual_hash == expected_hash)
            return passed, actual_hash, f"Hash match={passed} (actual: {actual_hash[:8]}, expected: {expected_hash[:8]})"

        # 3. BINARY_FUNCTIONAL_TEST
        elif c_type == "BINARY_FUNCTIONAL_TEST":
            # exp is (binary_name, test_arg, expected_substring)
            binary, test_arg, expected_sub = exp
            try:
                proc = subprocess.run(
                    f"{binary} {test_arg}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = proc.stdout + proc.stderr
                passed = proc.returncode == 0 and (expected_sub in output)
                return passed, proc.returncode, f"Binary test code={proc.returncode}, substring match={expected_sub in output}"
            except Exception as e:
                return False, str(e), f"Binary functional test error: {str(e)}"

        # 4. PORT_LISTENING
        elif c_type == "PORT_LISTENING":
            port = int(exp)
            # Try connecting to localhost port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            res = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            passed = (res == 0)
            return passed, res, f"Port {port} connection response={res} (0=connected)"

        # 5. HEALTH_URL_OK
        elif c_type == "HEALTH_URL_OK":
            url = str(exp)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ZONATA-Verifier/1.0"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    passed = (resp.status == 200)
                    return passed, resp.status, f"HTTP {url} returned {resp.status}"
            except Exception as e:
                return False, str(e), f"HTTP health check failed: {str(e)}"

        # 6. COMMAND_OUTPUT_MATCH
        elif c_type == "COMMAND_OUTPUT_MATCH":
            cmd, expected_sub = exp
            try:
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                output = proc.stdout + proc.stderr
                passed = expected_sub in output
                return passed, output[:200], f"Substring match={passed}"
            except Exception as e:
                return False, str(e), f"Command check error: {str(e)}"


        return False, None, f"Unknown check type: {c_type}"
