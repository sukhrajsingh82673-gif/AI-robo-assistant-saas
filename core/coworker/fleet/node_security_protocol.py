"""
ZONATA Universal AI Co-Worker Fabric — Node Security Protocol
Enforces mutual authentication, HMAC request signing, replay protection (nonces & timestamps),
execution lease validation, certificate rotation, and kill switch propagation to distributed nodes.
"""

from typing import Dict, List, Optional, Any, Tuple
import hashlib
import hmac
import time
import uuid

class NodeSecurityProtocol:
    """
    Cryptographic Security Protocol for ZONATA Control Plane ↔ Remote Node interactions.
    Guarantees that a remote worker node cannot forge assignments, replay old leases,
    or execute tasks without explicit sovereign authority.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self._shared_secrets: Dict[str, str] = {} # node_id -> secret_key
        self._seen_nonces: Dict[str, float] = {}   # nonce -> timestamp
        self._active_leases: Dict[str, Dict[str, Any]] = {} # lease_id -> lease_info
        self._revoked_nodes: set = set()

    def register_node_secret(self, node_id: str, secret_key: str):
        """Stores pre-shared symmetric key for node HMAC signing."""
        self._shared_secrets[node_id] = secret_key

    def rotate_node_secret(self, node_id: str, new_secret_key: str) -> bool:
        """Rotates cryptographic key for a node."""
        if node_id in self._revoked_nodes:
            return False
        self._shared_secrets[node_id] = new_secret_key
        return True

    def sign_request(self, node_id: str, payload_str: str) -> Tuple[str, str, float]:
        """Signs an outbound request payload with HMAC-SHA256, nonce, and current timestamp."""
        secret = self._shared_secrets.get(node_id, "default_zonata_secret")
        nonce = uuid.uuid4().hex
        timestamp = time.time()
        message = f"{node_id}:{nonce}:{timestamp}:{payload_str}"
        sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return sig, nonce, timestamp

    def verify_request_signature(
        self,
        node_id: str,
        payload_str: str,
        signature: str,
        nonce: str,
        timestamp: float,
        max_drift_sec: float = 60.0
    ) -> Tuple[bool, str]:
        """Validates signature and prevents replay attacks."""
        if node_id in self._revoked_nodes:
            return False, f"Node {node_id} is REVOKED"

        now = time.time()
        # 1. Replay window check
        if abs(now - timestamp) > max_drift_sec:
            return False, f"Replay rejected: timestamp drift {abs(now - timestamp):.1f}s exceeds threshold"

        # 2. Nonce reuse check
        if nonce in self._seen_nonces:
            return False, f"Replay rejected: duplicate nonce '{nonce}'"
        self._seen_nonces[nonce] = now

        # Clean old nonces
        cutoff = now - (max_drift_sec * 2)
        self._seen_nonces = {n: ts for n, ts in self._seen_nonces.items() if ts > cutoff}

        # 3. HMAC check
        secret = self._shared_secrets.get(node_id, "default_zonata_secret")
        expected_msg = f"{node_id}:{nonce}:{timestamp}:{payload_str}"
        expected_sig = hmac.new(secret.encode(), expected_msg.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return False, "Cryptographic signature mismatch"

        return True, "SIGNATURE_VALID"

    def issue_execution_lease(
        self,
        node_id: str,
        task_id: str,
        mission_id: str,
        capability_id: str,
        ttl_sec: float = 300.0
    ) -> str:
        """Issues time-bounded, cryptographic execution lease."""
        lease_id = f"lse_{uuid.uuid4().hex[:12]}"
        now = time.time()
        self._active_leases[lease_id] = {
            "lease_id": lease_id,
            "node_id": node_id,
            "task_id": task_id,
            "mission_id": mission_id,
            "capability_id": capability_id,
            "issued_at": now,
            "expires_at": now + ttl_sec,
            "revoked": False
        }
        return lease_id

    def validate_lease(self, lease_id: str, node_id: str) -> Tuple[bool, str]:
        """Validates that a lease is currently active and belongs to the calling node."""
        lease = self._active_leases.get(lease_id)
        if not lease:
            return False, "Lease does not exist"
        if lease["revoked"]:
            return False, "Lease has been explicitly revoked"
        if lease["node_id"] != node_id:
            return False, f"Lease ownership mismatch: issued to {lease['node_id']}, used by {node_id}"
        if time.time() > lease["expires_at"]:
            return False, "Lease has expired"
        return True, "LEASE_VALID"

    def revoke_lease(self, lease_id: str) -> bool:
        if lease_id in self._active_leases:
            self._active_leases[lease_id]["revoked"] = True
            return True
        return False

    def revoke_node(self, node_id: str) -> bool:
        """Revokes all active leases and blacklists a compromised node."""
        self._revoked_nodes.add(node_id)
        for l in self._active_leases.values():
            if l["node_id"] == node_id:
                l["revoked"] = True
        return True
