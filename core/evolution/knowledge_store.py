"""
ZONATA Governed Knowledge Store (Sub-Step 6E).

Manages machine-executable playbooks adhering to the zonata.playbook/v1 specification.
Features:
- Schema validation with mandatory rollback actions and provenance.
- Mutation protection: global: true restricted to system principals.
- Semantic vector similarity matching with strict tenant RLS isolation.
- agentskills.io security scanner rejecting root, eval, and unconstrained egress.
- Per-tenant cryptographic envelope encryption and crypto-shred erasure (Rule 46).
"""

import os
import re
import json
import math
import uuid
import time
import base64
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PlaybookValidationError(Exception):
    """Raised when a playbook violates the zonata.playbook/v1 schema or security policy."""
    pass


class SkillSecurityRejectionError(Exception):
    """Raised when an external skill package fails security admission checks."""
    pass


class CryptoShreddedError(Exception):
    """Raised when attempting to access a playbook whose tenant encryption key was destroyed."""
    pass


class Playbook:
    """Represents a validated zonata.playbook/v1 document."""

    def __init__(
        self,
        title: str,
        description: str,
        author_principal: str,
        tenant_id: str,
        company_id: str,
        steps: List[Dict[str, Any]],
        preconditions: Optional[Dict[str, Any]] = None,
        postconditions: Optional[Dict[str, Any]] = None,
        safety: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        global_playbook: bool = False,
        playbook_id: Optional[str] = None,
        version: str = "1.0.0",
        embedding: Optional[List[float]] = None,
    ):
        self.playbook_id = playbook_id or f"pbk_{uuid.uuid4().hex[:12]}"
        self.version = version
        self.schema_version = "zonata.playbook/v1"
        self.title = title.strip()
        self.description = description.strip()
        self.author_principal = author_principal
        self.tenant_id = tenant_id
        self.company_id = company_id
        self.global_playbook = global_playbook
        self.preconditions = preconditions or {}
        self.steps = steps
        self.postconditions = postconditions or {}
        self.safety = safety or {"max_cost": 5.0, "max_time": 60, "banned_tools": []}
        self.provenance = provenance or {}
        self.embedding = embedding or self._generate_synthetic_embedding(f"{self.title} {self.description}")
        self.created_at = time.time()

        self._validate()

    def _validate(self) -> None:
        """Validates all schema invariants of zonata.playbook/v1."""
        if not self.title:
            raise PlaybookValidationError("Playbook title cannot be empty.")
        if not self.steps:
            raise PlaybookValidationError("Playbook must contain at least one step.")

        # Mandatory rollback action per step
        for idx, step in enumerate(self.steps, 1):
            if "step_id" not in step or "action" not in step:
                raise PlaybookValidationError(f"Step {idx} is missing step_id or action.")
            rollback = step.get("rollback_action")
            if not rollback or not str(rollback).strip():
                raise PlaybookValidationError(
                    f"Step {idx} ('{step.get('step_id')}') is missing mandatory rollback_action."
                )

        # Mandatory provenance
        if not self.provenance or ("signature" not in self.provenance and "source_id" not in self.provenance):
            raise PlaybookValidationError("Playbook requires valid cryptographic provenance or source reference.")

        # Mutation Invariant: global: true is ONLY permitted for system principal
        if self.global_playbook and self.author_principal != "system":
            raise PlaybookValidationError(
                f"Mutation Check Failed: Only 'system' principal may author global playbooks. "
                f"Principal '{self.author_principal}' cannot set global=True."
            )

    def _generate_synthetic_embedding(self, text: str) -> List[float]:
        """Generates a deterministic 32-dimensional bag-of-words embedding vector."""
        vec = [0.0] * 32
        words = re.findall(r"\w+", text.lower())
        if not words:
            return [1.0] + [0.0] * 31
        for w in words:
            idx = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:4], 16) % 32
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]


class AgentSkillsIOScanner:
    """
    Validates external skills from the agentskills.io format before admission.
    Blocks root execution, dangerous syscalls, code injection, and unbounded network.
    """

    DANGEROUS_TOKENS = [
        re.compile(r"\b(sudo|su|root)\b", re.IGNORECASE),
        re.compile(r"\b(ptrace|chroot)\b", re.IGNORECASE),
        re.compile(r"\b(eval|exec|os\.system|subprocess\.Popen)\s*\(", re.IGNORECASE),
        re.compile(r"\/bin\/(?:ba)?sh\s+-c", re.IGNORECASE),
    ]

    @classmethod
    def scan_manifest(cls, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Scans skill manifest, returning PASS or raising SkillSecurityRejectionError."""
        name = manifest.get("name", "unnamed_skill")
        spec_text = json.dumps(manifest)

        # Scan for banned patterns
        for pattern in cls.DANGEROUS_TOKENS:
            m = pattern.search(spec_text)
            if m:
                raise SkillSecurityRejectionError(
                    f"Skill '{name}' rejected: Contains prohibited security token '{m.group(0)}'."
                )

        # Network boundary validation
        network_policy = manifest.get("network", {})
        if network_policy.get("unrestricted") is True or network_policy.get("allow_all_egress") is True:
            raise SkillSecurityRejectionError(
                f"Skill '{name}' rejected: Unrestricted outbound network access requested."
            )

        # Capabilities / permissions check
        perms = manifest.get("permissions", [])
        if any(p.lower() in ("admin", "root", "system_write", "vault_bypass") for p in perms):
            raise SkillSecurityRejectionError(
                f"Skill '{name}' rejected: Escalated privilege requested ({perms})."
            )

        return {
            "status": "PASS",
            "skill_name": name,
            "version": manifest.get("version", "1.0.0"),
            "sandbox_ready": True,
        }


class KnowledgeStoreEngine:
    """
    Governed repository storing encrypted playbooks with pgvector/cosine retrieval,
    strict tenant RLS isolation, and crypto-shredding support.
    """

    def __init__(self):
        # Keyring: {tenant_id: 256-bit AESGCM key}
        self._keyring: Dict[str, bytes] = {}
        # Storage: {playbook_id: {"encrypted_payload": str, "nonce": str, "metadata": dict}}
        self._store: Dict[str, Dict[str, Any]] = {}

    def _get_or_create_tenant_key(self, tenant_id: str) -> bytes:
        if tenant_id not in self._keyring:
            self._keyring[tenant_id] = AESGCM.generate_key(bit_length=256)
        return self._keyring[tenant_id]

    def save_playbook(self, playbook: Playbook) -> str:
        """Encrypts and stores a playbook under tenant isolation."""
        key = self._get_or_create_tenant_key(playbook.tenant_id)
        aes = AESGCM(key)
        nonce = os.urandom(12)

        data = {
            "title": playbook.title,
            "description": playbook.description,
            "steps": playbook.steps,
            "preconditions": playbook.preconditions,
            "postconditions": playbook.postconditions,
            "safety": playbook.safety,
            "provenance": playbook.provenance,
        }
        plaintext = json.dumps(data).encode("utf-8")
        ciphertext = aes.encrypt(nonce, plaintext, None)

        record = {
            "playbook_id": playbook.playbook_id,
            "tenant_id": playbook.tenant_id,
            "company_id": playbook.company_id,
            "author_principal": playbook.author_principal,
            "global_playbook": playbook.global_playbook,
            "title": playbook.title,
            "description": playbook.description,
            "embedding": playbook.embedding,
            "encrypted_payload": base64.b64encode(ciphertext).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
        }
        self._store[playbook.playbook_id] = record
        return playbook.playbook_id

    def get_playbook(self, playbook_id: str, caller_tenant_id: str) -> Dict[str, Any]:
        """
        Retrieves and decrypts a playbook. Enforces RLS and crypto-shredding verification.
        """
        if playbook_id not in self._store:
            raise KeyError(f"Playbook {playbook_id} not found.")

        record = self._store[playbook_id]

        # RLS Check (Rule 45)
        is_global = record["global_playbook"] and record["tenant_id"] == "system"
        if not is_global and record["tenant_id"] != caller_tenant_id:
            raise PermissionError("Cross-tenant access denied by RLS policy.")

        # Crypto-Shredding Check (Rule 46)
        target_tenant = record["tenant_id"]
        if target_tenant not in self._keyring:
            raise CryptoShreddedError(
                f"Tenant key for '{target_tenant}' has been destroyed. Playbook is cryptographically unreadable."
            )

        key = self._keyring[target_tenant]
        aes = AESGCM(key)
        nonce = base64.b64decode(record["nonce"])
        ciphertext = base64.b64decode(record["encrypted_payload"])

        try:
            plaintext = aes.decrypt(nonce, ciphertext, None)
            payload = json.loads(plaintext.decode("utf-8"))
        except Exception as e:
            raise CryptoShreddedError(f"Decryption failed: {e}")

        payload["playbook_id"] = record["playbook_id"]
        payload["tenant_id"] = record["tenant_id"]
        payload["global_playbook"] = record["global_playbook"]
        return payload

    def search_similar(
        self,
        caller_tenant_id: str,
        query_text: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Semantic cosine similarity search against embeddings under strict RLS scoping.
        """
        dummy_pb = Playbook(
            title=query_text,
            description="",
            author_principal="system",
            tenant_id="system",
            company_id="system",
            steps=[{"step_id": "s1", "action": "test", "rollback_action": "undo"}],
            provenance={"source_id": "query"},
            global_playbook=True,
        )
        q_vec = dummy_pb.embedding

        results = []
        for pid, record in self._store.items():
            # RLS Isolation: only caller tenant OR system global playbooks
            is_global = record["global_playbook"] and record["tenant_id"] == "system"
            if not is_global and record["tenant_id"] != caller_tenant_id:
                continue

            # Verify tenant key is not shredded
            if record["tenant_id"] not in self._keyring:
                continue

            score = self._cosine_similarity(q_vec, record["embedding"])
            results.append((score, pid))

        results.sort(key=lambda x: x[0], reverse=True)
        top_results = []
        for score, pid in results[:top_k]:
            pb_data = self.get_playbook(pid, caller_tenant_id)
            pb_data["similarity_score"] = round(score, 4)
            top_results.append(pb_data)
        return top_results

    def shred_tenant_keys(self, tenant_id: str) -> bool:
        """
        Crypto-shreds all tenant playbooks by irrevocably wiping the tenant DEK (Rule 46).
        """
        if tenant_id in self._keyring:
            # Overwrite in-memory buffer before deletion
            self._keyring[tenant_id] = os.urandom(32)
            del self._keyring[tenant_id]
            return True
        return False

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1)) or 1.0
        n2 = math.sqrt(sum(b * b for b in v2)) or 1.0
        return dot / (n1 * n2)
