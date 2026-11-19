"""ZONATA Agent Factory - Certification Bundle Packaging & Verification.

Implements Gate AT-15:
- Packages certified agent versions with gate evaluation results
- Generates detached Ed25519 signature
- Persists certification bundle in af_artifact and af_certification
- Verifies signed bundles and detects package tampering
"""

from __future__ import annotations
import base64
import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from agent_factory.build.signer import sign_manifest, verify_manifest, canonical, sha256_hex
from agent_factory.ports import EvidenceEvent


class CertificationBundleManager:
    def __init__(
        self,
        db_conn_factory,
        evidence_port,
        signing_key: Optional[Ed25519PrivateKey] = None,
        signing_key_id: str = "cert_key_01"
    ):
        self.db_conn_factory = db_conn_factory
        self.evidence = evidence_port
        self.signing_key = signing_key or Ed25519PrivateKey.generate()
        self.signing_key_id = signing_key_id

    def build_and_seal_bundle(
        self,
        tenant_id: str,
        subject_kind: str,
        agent_version_id: Optional[str],
        batch_id: Optional[str],
        gate_results: Dict[str, Any],
        issued_by: str = "principal.evaluator.cert_manager"
    ) -> Dict[str, Any]:
        """Assemble, sign, and store certification bundle."""
        cert_id = f"crt_{uuid.uuid4().hex[:12]}"
        artifact_id = f"art_cert_{cert_id}"
        now = time.time()

        all_mandatory_passed = bool(gate_results.get("all_mandatory_passed", False))
        if not all_mandatory_passed:
            raise ValueError("Cannot certify package when mandatory gates failed!")

        # 1. Manifest
        bundle_manifest = {
            "certification_id": cert_id,
            "tenant_id": tenant_id,
            "subject_kind": subject_kind,
            "agent_version_id": agent_version_id,
            "batch_id": batch_id,
            "gate_policy_version": gate_results.get("policy_version", "1.0.0"),
            "tier": gate_results.get("tier", "R1"),
            "gates_summary": [
                {"gate": g["gate"], "passed": g["passed"]}
                for g in gate_results.get("gates", [])
            ],
            "issued_at": now
        }

        # 2. Detached Ed25519 signature
        signed_cert = sign_manifest(self.signing_key, bundle_manifest, self.signing_key_id)

        bundle_payload = {
            "manifest": bundle_manifest,
            "signature": signed_cert,
            "gate_results": gate_results
        }
        bundle_bytes = canonical(bundle_payload)
        bundle_sha256 = sha256_hex(bundle_bytes)

        # 3. Append to EvidenceLedger
        ev_id = self.evidence.append_event(EvidenceEvent(
            subject_kind="certification",
            subject_id=cert_id,
            event_type="certification.issued",
            actor=issued_by,
            payload_hashes={
                "cert_id": cert_id,
                "bundle_sha256": bundle_sha256,
                "agent_version_id": str(agent_version_id),
                "batch_id": str(batch_id)
            },
            timestamp=now,
            tenant_id=tenant_id
        ))

        # 4. Persist in database
        with self.db_conn_factory() as conn:
            # Store in af_artifact
            conn.execute("""
                INSERT INTO af_artifact (
                    id, tenant_id, kind, sha256, size_bytes, storage_uri,
                    signature, signing_key_id, created_by, created_at
                ) VALUES (?, ?, 'certification_bundle', ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact_id, tenant_id, bundle_sha256, len(bundle_bytes),
                f"storage://certifications/{cert_id}.json",
                signed_cert["signature"], signed_cert["signing_key_id"],
                issued_by, now
            ))

            # Store in af_certification
            conn.execute("""
                INSERT INTO af_certification (
                    id, tenant_id, subject_kind, agent_version_id, batch_id,
                    gate_policy_version, gate_results, all_mandatory_passed,
                    bundle_artifact_id, evidence_ledger_ref, issued_by, issued_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, (
                cert_id, tenant_id, subject_kind, agent_version_id, batch_id,
                bundle_manifest["gate_policy_version"], json.dumps(gate_results),
                artifact_id, ev_id, issued_by, now
            ))

            # Update agent_version status to CERTIFIED if applicable
            if agent_version_id:
                conn.execute(
                    "UPDATE af_agent_version SET status = 'CERTIFIED' WHERE id = ?",
                    (agent_version_id,)
                )

            conn.commit()

        return {
            "certification_id": cert_id,
            "manifest": bundle_manifest,
            "bundle_artifact_id": artifact_id,
            "bundle_sha256": bundle_sha256,
            "signature": signed_cert,
            "evidence_ledger_ref": ev_id,
            "all_mandatory_passed": True
        }

    def verify_bundle(
        self,
        bundle_payload: Dict[str, Any],
        revoked_key_ids: Optional[set] = None
    ) -> Tuple[bool, str]:
        """Verify signature and integrity of a certification bundle (AT-15)."""
        manifest = bundle_payload.get("manifest")
        signed = bundle_payload.get("signature")
        if not manifest or not signed:
            return False, "invalid bundle format"

        pub_key = self.signing_key.public_key()
        return verify_manifest(pub_key, manifest, signed, revoked_key_ids)
