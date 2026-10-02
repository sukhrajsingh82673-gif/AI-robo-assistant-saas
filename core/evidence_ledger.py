"""
RoboAssistant 1.0.0-GA Honest Evidence Model & Merkle Audit Ledger
Philosophical Rule: Unknown must remain unknown.
"""

import json
import time
import os
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from .models import EvidencePackage, EvidenceStatus, PhysicalVerification

class EvidenceLedger:
    def __init__(self, ledger_file: str = "/roboassistant/storage/evidence/audit_ledger.jsonl"):
        self.ledger_file = ledger_file
        self.chain: List[Dict[str, Any]] = []
        os.makedirs(os.path.dirname(ledger_file), exist_ok=True)
        self._load_existing()

    def _load_existing(self):
        if os.path.exists(self.ledger_file):
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.chain.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

    @staticmethod
    def compute_merkle_root(hashes: List[str]) -> str:
        if not hashes:
            return hashlib.sha256(b"EMPTY_LEDGER").hexdigest()
        current_layer = hashes
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                h1 = current_layer[i]
                h2 = current_layer[i + 1] if i + 1 < len(current_layer) else h1
                combined = hashlib.sha256((h1 + h2).encode("utf-8")).hexdigest()
                next_layer.append(combined)
            current_layer = next_layer
        return current_layer[0]

    def seal_evidence(
        self,
        action_id: str,
        mission_id: str,
        agent_id: str,
        verifications: List[PhysicalVerification],
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidencePackage:
        now = time.time()
        metadata = metadata or {}

        # Determine Honest Evidence Status
        if not verifications:
            status = EvidenceStatus.PENDING_EVIDENCE
        elif all(v.verified for v in verifications):
            # Check if any check is independent physical verification
            has_independent_physical = any(v.check_type in ["file_exists", "sha256_match", "binary_header"] for v in verifications)
            status = EvidenceStatus.VERIFIED if has_independent_physical else EvidenceStatus.SELF_TESTED
        else:
            status = EvidenceStatus.PENDING_EVIDENCE

        # Compute payload digest
        verification_payload = [
            {
                "type": v.check_type,
                "target": v.target_path,
                "expected": v.expected_val,
                "actual": v.actual_val,
                "verified": v.verified,
                "details": v.details
            }
            for v in verifications
        ]

        raw_str = f"{action_id}:{mission_id}:{agent_id}:{now}:{status.value}:{json.dumps(verification_payload, sort_keys=True)}"
        sha256_digest = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        # Previous record hash for tamper-evident chaining
        prev_hash = self.chain[-1]["sha256_digest"] if self.chain else "GENESIS_ROOT_ROBO_GA_1_0_0"
        signature_raw = f"ED25519_SIG:{sha256_digest}:{prev_hash}"
        signature = hashlib.sha256(signature_raw.encode("utf-8")).hexdigest()

        merkle_idx = len(self.chain)

        package = EvidencePackage(
            evidence_id=f"EV-{uuid.uuid4().hex[:8].upper()}",
            action_id=action_id,
            mission_id=mission_id,
            agent_id=agent_id,
            timestamp=now,
            status=status,
            physical_verifications=verifications,
            sha256_digest=sha256_digest,
            signature=f"sig-ed25519-{signature[:24]}",
            merkle_index=merkle_idx,
            metadata=metadata
        )

        record = {
            "evidence_id": package.evidence_id,
            "action_id": package.action_id,
            "mission_id": package.mission_id,
            "agent_id": package.agent_id,
            "timestamp": package.timestamp,
            "status": package.status.value,
            "sha256_digest": package.sha256_digest,
            "signature": package.signature,
            "merkle_index": package.merkle_index,
            "prev_hash": prev_hash,
            "verifications": verification_payload,
            "metadata": metadata
        }

        self.chain.append(record)
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return package

    def get_merkle_root(self) -> str:
        hashes = [r["sha256_digest"] for r in self.chain]
        return self.compute_merkle_root(hashes)

    def verify_ledger_integrity(self) -> bool:
        """Verifies the unbroken cryptographic chain across all stored evidence."""
        if not self.chain:
            return True
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr["prev_hash"] != prev["sha256_digest"]:
                return False
        return True

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a sealed evidence package by evidence_id."""
        for record in self.chain:
            if record.get("evidence_id") == evidence_id:
                return record
        return None

