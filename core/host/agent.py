"""
ZONATA Standalone Host Agent Runtime
====================================
OpenCode Step 3B: Host agent executing on user workstation.
Enforces:
- Rule 23: Consent enforced on host (local allowlists, cloud cannot widen).
- Rule 24: Private keys never leave the machine.
- Deny-by-default for password managers, banking, and OS security apps.
- Emergency physical kill switch.
"""

from __future__ import annotations
import json
import logging
import secrets
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519

from core.db import db
from core.host.types import (
    GrantMode,
    GrantScope,
    GrantEventType,
    HostGrantRecord,
    DENIED_BY_DEFAULT_APPS,
    HostSecurityViolation,
    OutOfGrantError,
    DeniedByDefaultError,
)
from core.host.session import HostSessionManager

logger = logging.getLogger("zonata.host.agent")


class ZonataHostAgent:
    """
    Lightweight sovereign agent daemon installed on the owner's computer.
    Connects outbound only to cloud; all command consent is verified locally.
    """

    def __init__(self, device_name: str = "Workstation", os_type: str = "linux"):
        self.device_name = device_name
        self.os_type = os_type
        self.device_id: Optional[str] = None
        self.tenant_id: Optional[str] = None
        self.company_id: Optional[str] = None

        # Private key never leaves this instance and is never persisted in plaintext DB
        self._private_key: ed25519.Ed25519PrivateKey = ed25519.Ed25519PrivateKey.generate()
        self._public_key: ed25519.Ed25519PublicKey = self._private_key.public_key()

        # Local grant store enforced on the machine itself
        self._local_grants: Dict[str, HostGrantRecord] = {}
        self._kill_switch_engaged: bool = False
        self._active_session_id: Optional[str] = None
        self._sequence_counter: int = 0

    @property
    def public_key_hex(self) -> str:
        return self._public_key.public_bytes_raw().hex()

    def get_public_key_pem(self) -> str:
        return self.public_key_hex

    def sign_envelope(
        self,
        session_id: str,
        sequence_no: int,
        timestamp: float,
        nonce: str,
        payload: Dict[str, Any],
    ) -> str:
        """Signs an outbound envelope using the host's private key."""
        canonical_bytes = HostSessionManager.canonical_envelope_bytes(
            session_id, sequence_no, timestamp, nonce, payload
        )
        signature = self._private_key.sign(canonical_bytes)
        return signature.hex()

    def create_outbound_envelope(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Packages a payload into a signed envelope with sequence counter and nonce."""
        if not self._active_session_id:
            raise HostSecurityViolation("Host agent has no active session.")

        self._sequence_counter += 1
        seq = self._sequence_counter
        ts = time.time()
        nonce = secrets.token_hex(16)
        sig_hex = self.sign_envelope(self._active_session_id, seq, ts, nonce, payload)

        return {
            "session_id": self._active_session_id,
            "device_id": self.device_id,
            "sequence_no": seq,
            "timestamp": ts,
            "nonce": nonce,
            "payload": payload,
            "signature": sig_hex,
            "public_key": self.public_key_hex,
        }

    def sync_local_grant(self, grant: HostGrantRecord) -> None:
        """Stores or updates a grant in the local host store."""
        self._local_grants[grant.grant_id] = grant

    def trigger_kill_switch(self, actor: str = "HUMAN_PHYSICAL") -> bool:
        """
        Emergency halt triggered by global hotkey, tray button, or safety monitor.
        Immediately halts execution, drops session, and reports to cloud.
        """
        self._kill_switch_engaged = True
        logger.critical(f"HOST KILL SWITCH TRIGGERED by {actor} on {self.device_name}!")

        if self._active_session_id:
            try:
                HostSessionManager.halt_session(
                    session_id=self._active_session_id,
                    reason=f"HOST_PHYSICAL_KILL_SWITCH_TRIGGERED_BY_{actor}",
                    actor_id=actor,
                )
            except Exception as e:
                logger.error(f"Error halting cloud session from kill switch: {e}")

        # Record kill switch event in grant events
        if self.device_id and self.tenant_id:
            now = time.time()
            sql = """
            INSERT INTO grant_events (
                event_id, grant_id, device_id, tenant_id, company_id,
                event_type, details, actor_id, actor_type, timestamp
            ) VALUES (
                :event_id, NULL, :device_id, :tenant_id, :company_id,
                :event_type, :details, :actor_id, :actor_type, :timestamp
            )
            """
            try:
                with db.get_connection() as conn:
                    conn.execute(sql, {
                        "event_id": f"gev_{uuid.uuid4().hex[:12]}",
                        "device_id": self.device_id,
                        "tenant_id": self.tenant_id,
                        "company_id": self.company_id or "default",
                        "event_type": GrantEventType.KILL_SWITCH_ENGAGED.value,
                        "details": json.dumps({"source": "LOCAL_PHYSICAL_KILL_SWITCH", "actor": actor}),
                        "actor_id": actor,
                        "actor_type": "HUMAN_PHYSICAL",
                        "timestamp": now,
                    })
                    if hasattr(conn, "commit"):
                        conn.commit()
            except Exception:
                pass

        return True

    def reset_kill_switch_for_test(self) -> None:
        """Resets the kill switch flag for test environments only."""
        self._kill_switch_engaged = False

    def execute_command(self, command_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforces Rule 23 (Consent on host): evaluates incoming action against local grants.
        Rejects out-of-grant commands, deny-by-default apps, and observe-mode inputs.
        """
        # 1. Physical Kill Switch Check
        if self._kill_switch_engaged:
            raise HostSecurityViolation("Host kill switch is engaged. All host automation is halted.")

        app_name = str(command_payload.get("app_name", "")).lower().strip()
        action_type = str(command_payload.get("action_type", "")).lower().strip()
        action_class = str(command_payload.get("action_class", "READ_ONLY")).upper().strip()
        now = time.time()

        # 2. Deny-by-default Applications Check
        if app_name in DENIED_BY_DEFAULT_APPS:
            has_explicit_app_grant = False
            for grant in self._local_grants.values():
                if grant.status == "ACTIVE" and grant.valid_from <= now < grant.valid_until:
                    if app_name in [a.lower() for a in grant.allowed_apps]:
                        has_explicit_app_grant = True
                        break

            human_explicit_confirmed = command_payload.get("human_explicit_confirmation") is True
            if not (has_explicit_app_grant and human_explicit_confirmed):
                # Record denial event
                self._record_command_event(GrantEventType.COMMAND_DENIED, command_payload, "DENIED_BY_DEFAULT_PROTECTED_APP")
                raise DeniedByDefaultError(
                    f"DENIED BY DEFAULT: Access to protected application '{app_name}' is blocked. "
                    "Access requires an explicit grant naming the application AND secondary human confirmation."
                )

        # 3. Local Grant Matching
        matching_grant: Optional[HostGrantRecord] = None
        for grant in self._local_grants.values():
            if grant.status == "ACTIVE" and grant.valid_from <= now < grant.valid_until:
                # Check application match
                allowed_apps_lower = [a.lower() for a in grant.allowed_apps]
                if "*" in grant.allowed_apps or app_name in allowed_apps_lower:
                    # Check action class match
                    if not grant.allowed_actions or "*" in grant.allowed_actions or action_class in grant.allowed_actions:
                        matching_grant = grant
                        break

        if not matching_grant:
            self._record_command_event(GrantEventType.COMMAND_DENIED, command_payload, "NO_MATCHING_GRANT")
            raise OutOfGrantError(
                f"Action on app '{app_name}' with action '{action_type}' ({action_class}) "
                "is outside any active host grant."
            )

        # 4. Mode-specific Enforcement
        synthetic_input_actions = {"click", "double_click", "type", "keypress", "drag", "mouse_down", "paste"}
        if matching_grant.mode == GrantMode.OBSERVE:
            if action_type in synthetic_input_actions or action_class in {"MODIFY_DATA", "HIGH_RISK"}:
                self._record_command_event(GrantEventType.COMMAND_DENIED, command_payload, "OBSERVE_MODE_INPUT_FORBIDDEN")
                raise OutOfGrantError(
                    f"Host grant mode is OBSERVE. Synthetic input action '{action_type}' is strictly forbidden."
                )

        if matching_grant.mode == GrantMode.CONFIRM_EACH:
            if not command_payload.get("human_confirmed"):
                self._record_command_event(GrantEventType.COMMAND_DENIED, command_payload, "CONFIRM_EACH_UNCONFIRMED")
                raise OutOfGrantError(
                    f"Host grant mode is CONFIRM_EACH. Action '{action_type}' was not confirmed by the human on the host."
                )

        # 5. Successful Execution Verification
        self._record_command_event(GrantEventType.COMMAND_ALLOWED, command_payload, "IN_GRANT_EXECUTED", matching_grant.grant_id)
        return {
            "status": "SUCCESS",
            "executed": True,
            "device_id": self.device_id,
            "app_name": app_name,
            "action_type": action_type,
            "mode": matching_grant.mode.value,
            "grant_id": matching_grant.grant_id,
            "timestamp": now,
        }

    def _record_command_event(
        self,
        event_type: GrantEventType,
        payload: Dict[str, Any],
        reason: str,
        grant_id: Optional[str] = None,
    ) -> None:
        if not (self.device_id and self.tenant_id):
            return
        now = time.time()
        sql = """
        INSERT INTO grant_events (
            event_id, grant_id, device_id, tenant_id, company_id,
            event_type, details, actor_id, actor_type, timestamp
        ) VALUES (
            :event_id, :grant_id, :device_id, :tenant_id, :company_id,
            :event_type, :details, :actor_id, :actor_type, :timestamp
        )
        """
        try:
            with db.get_connection() as conn:
                conn.execute(sql, {
                    "event_id": f"gev_{uuid.uuid4().hex[:12]}",
                    "grant_id": grant_id,
                    "device_id": self.device_id,
                    "tenant_id": self.tenant_id,
                    "company_id": self.company_id or "default",
                    "event_type": event_type.value,
                    "details": json.dumps({"payload": payload, "reason": reason}),
                    "actor_id": self.device_id,
                    "actor_type": "HOST_AGENT",
                    "timestamp": now,
                })
                if hasattr(conn, "commit"):
                    conn.commit()
        except Exception:
            pass
