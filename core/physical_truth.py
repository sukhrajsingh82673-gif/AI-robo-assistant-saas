"""
RoboAssistant 1.0.0-GA Physical Truth Engine
Validates actual physical machine and digital state. Reasoning is never proof.
"""

import os
import hashlib
import subprocess
from typing import Optional
from .models import PhysicalVerification

class PhysicalTruthEngine:
    """
    Independent Reality Verification Engine.
    Ensures that an agent's claim of completion is physically verified in reality.
    """

    @staticmethod
    def calculate_sha256(filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    @classmethod
    def verify_file_exists(cls, filepath: str) -> PhysicalVerification:
        exists = os.path.exists(filepath) and os.path.isfile(filepath)
        size = os.path.getsize(filepath) if exists else 0
        return PhysicalVerification(
            check_type="file_exists",
            target_path=filepath,
            expected_val="true",
            actual_val="true" if exists else "false",
            verified=exists,
            details=f"File presence verified. Size: {size} bytes" if exists else "Target file does not exist on filesystem"
        )

    @classmethod
    def verify_sha256_match(cls, filepath: str, expected_hash: str) -> PhysicalVerification:
        if not os.path.exists(filepath):
            return PhysicalVerification(
                check_type="sha256_match",
                target_path=filepath,
                expected_val=expected_hash,
                actual_val="FILE_NOT_FOUND",
                verified=False,
                details="Cannot verify hash: file does not exist."
            )
        actual_hash = cls.calculate_sha256(filepath)
        match = (actual_hash.lower() == expected_hash.lower())
        return PhysicalVerification(
            check_type="sha256_match",
            target_path=filepath,
            expected_val=expected_hash,
            actual_val=actual_hash,
            verified=match,
            details=f"SHA-256 match confirmed ({actual_hash[:12]}...)" if match else f"Hash mismatch! Expected {expected_hash}, got {actual_hash}"
        )

    @classmethod
    def verify_process_exit(cls, cmd: list[str], expected_exit_code: int = 0) -> PhysicalVerification:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            verified = (res.returncode == expected_exit_code)
            return PhysicalVerification(
                check_type="exit_code_zero",
                target_path=" ".join(cmd),
                expected_val=str(expected_exit_code),
                actual_val=str(res.returncode),
                verified=verified,
                details=f"Command executed. Exit code: {res.returncode}. Output snippet: {res.stdout.strip()[:100]}"
            )
        except Exception as e:
            return PhysicalVerification(
                check_type="exit_code_zero",
                target_path=" ".join(cmd),
                expected_val=str(expected_exit_code),
                actual_val="EXCEPTION",
                verified=False,
                details=f"Execution failed: {str(e)}"
            )

    @classmethod
    def verify_binary_header(cls, filepath: str, expected_type: str = "ELF") -> PhysicalVerification:
        """Verifies binary header magic (ELF: \\x7fELF, PE: MZ, Script: #!)"""
        if not os.path.exists(filepath):
            return PhysicalVerification(
                check_type="binary_header",
                target_path=filepath,
                expected_val=expected_type,
                actual_val="FILE_NOT_FOUND",
                verified=False,
                details="Binary file does not exist."
            )
        try:
            with open(filepath, "rb") as f:
                header = f.read(16)
            verified = False
            detected = "UNKNOWN"
            if header.startswith(b"\x7fELF"):
                detected = "ELF"
            elif header.startswith(b"MZ"):
                detected = "PE"
            elif header.startswith(b"#!"):
                detected = "SCRIPT"
            elif header.startswith(b"%PDF"):
                detected = "PDF"
            elif header.startswith(b"\x89PNG"):
                detected = "PNG"

            verified = (detected == expected_type)
            return PhysicalVerification(
                check_type="binary_header",
                target_path=filepath,
                expected_val=expected_type,
                actual_val=detected,
                verified=verified,
                details=f"Header inspection: detected {detected}, expected {expected_type}."
            )
        except Exception as e:
            return PhysicalVerification(
                check_type="binary_header",
                target_path=filepath,
                expected_val=expected_type,
                actual_val="ERROR",
                verified=False,
                details=str(e)
            )
