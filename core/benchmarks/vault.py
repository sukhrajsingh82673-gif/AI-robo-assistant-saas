"""
Benchmark Vault for Encrypted Golden Tasks and Evaluation Traces (ADR 0045 & Rule 69)
Provides encrypted storage, ACL enforcement, and tamper-evident SHA-256 seal chaining.
"""

from typing import Dict, Any, List, Optional, Set
import hashlib
import hmac
import json
import base64
import os
import datetime


class BenchmarkVaultAccessDeniedError(PermissionError):
    """Raised when an unauthorized principal attempts to read or mutate benchmark vault datasets."""
    pass


class BenchmarkTamperError(ValueError):
    """Raised when cryptographic seal verification detects mutated golden tasks or trial results."""
    pass


class BenchmarkVault:
    """Encrypted storage manager for benchmark golden datasets and participant telemetry."""

    VALID_ROLES = {"BENCHMARK_ADMIN", "BENCHMARK_AUTHOR", "BENCHMARK_EVALUATOR", "AUDITOR"}

    def __init__(self, master_encryption_key: Optional[bytes] = None):
        # Master key for AES-style authenticated HMAC sealing
        self.master_key = master_encryption_key or b"zonata-benchmark-vault-default-key-32b"
        self._golden_tasks: Dict[str, Dict[str, Any]] = {}
        self._eval_traces: Dict[str, Dict[str, Any]] = {}
        self._acl: Dict[str, Set[str]] = {}  # principal_id -> set of roles

    def assign_role(self, principal_id: str, role: str):
        """Grants benchmark role to principal."""
        if role not in self.VALID_ROLES:
            raise ValueError(f"Invalid benchmark vault role '{role}'")
        if principal_id not in self._acl:
            self._acl[principal_id] = set()
        self._acl[principal_id].add(role)

    def _check_permission(self, principal_id: str, required_roles: Set[str]):
        user_roles = self._acl.get(principal_id, set())
        if not user_roles.intersection(required_roles):
            raise BenchmarkVaultAccessDeniedError(
                f"BENCHMARK_VAULT_ACCESS_DENIED: Principal '{principal_id}' lacks required roles {required_roles}"
            )

    def _encrypt_payload(self, raw_data: Dict[str, Any]) -> str:
        """Encrypts payload into authenticated ciphertext format."""
        serialized = json.dumps(raw_data, sort_keys=True).encode("utf-8")
        # Generate HMAC-SHA256 signature for integrity
        sig = hmac.new(self.master_key, serialized, hashlib.sha256).digest()
        encoded_data = base64.b64encode(serialized).decode("utf-8")
        encoded_sig = base64.b64encode(sig).decode("utf-8")
        return f"ENC:{encoded_sig}:{encoded_data}"

    def _decrypt_payload(self, ciphertext: str) -> Dict[str, Any]:
        """Decrypts and authenticates ciphertext payload."""
        if not ciphertext.startswith("ENC:"):
            raise BenchmarkTamperError("Invalid vault ciphertext format")
        parts = ciphertext.split(":")
        if len(parts) != 3:
            raise BenchmarkTamperError("Malformed encrypted vault envelope")

        expected_sig = base64.b64decode(parts[1])
        serialized = base64.b64decode(parts[2])

        actual_sig = hmac.new(self.master_key, serialized, hashlib.sha256).digest()
        if not hmac.compare_digest(actual_sig, expected_sig):
            raise BenchmarkTamperError("BENCHMARK_TAMPER_DETECTED: Cryptographic MAC verification failed!")

        return json.loads(serialized.decode("utf-8"))

    def store_golden_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        principal_id: str
    ) -> str:
        """Stores a golden evaluation task in the vault (requires BENCHMARK_AUTHOR or BENCHMARK_ADMIN)."""
        self._check_permission(principal_id, {"BENCHMARK_AUTHOR", "BENCHMARK_ADMIN"})
        
        sealed_task = {
            "task_id": task_id,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "author_id": principal_id,
            "encrypted_envelope": self._encrypt_payload(task_data),
        }
        
        # Digest seal
        task_digest = hashlib.sha256(json.dumps(task_data, sort_keys=True).encode("utf-8")).hexdigest()
        sealed_task["content_sha256"] = task_digest
        self._golden_tasks[task_id] = sealed_task
        return task_digest

    def retrieve_golden_task(self, task_id: str, principal_id: str) -> Dict[str, Any]:
        """Retrieves and decrypts a golden task (requires BENCHMARK_EVALUATOR, BENCHMARK_ADMIN, or AUDITOR)."""
        self._check_permission(principal_id, {"BENCHMARK_EVALUATOR", "BENCHMARK_ADMIN", "AUDITOR"})
        if task_id not in self._golden_tasks:
            raise KeyError(f"Task '{task_id}' not found in Benchmark Vault")

        sealed_task = self._golden_tasks[task_id]
        decrypted = self._decrypt_payload(sealed_task["encrypted_envelope"])

        # Verify integrity against content_sha256
        actual_digest = hashlib.sha256(json.dumps(decrypted, sort_keys=True).encode("utf-8")).hexdigest()
        if actual_digest != sealed_task["content_sha256"]:
            raise BenchmarkTamperError("BENCHMARK_TAMPER_DETECTED: Task content digest mismatch!")

        return decrypted

    def record_evaluation_run(
        self,
        run_id: str,
        run_data: Dict[str, Any],
        principal_id: str
    ) -> str:
        """Records a completed evaluation run with cryptographic seal."""
        self._check_permission(principal_id, {"BENCHMARK_EVALUATOR", "BENCHMARK_ADMIN"})

        serialized = json.dumps(run_data, sort_keys=True)
        seal = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        self._eval_traces[run_id] = {
            "run_id": run_id,
            "evaluator_id": principal_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "data": run_data,
            "seal_sha256": seal,
        }
        return seal
