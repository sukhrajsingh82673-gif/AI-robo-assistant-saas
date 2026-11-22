"""
ZONATA Device Pairing & Key Binding Engine
==========================================
OpenCode Step 3B: Host agent pairing protocol with human step-up authentication.
Ensures private key never leaves the host machine; cloud stores tenant-bound public key.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from typing import Dict, Any, Optional, Tuple

from core.db import db, tenant_scoped
from core.host.types import (
    DeviceRecord,
    DeviceStatus,
    StepUpAuthenticationRequiredError,
    HostSecurityViolation,
    ensure_host_permission_tables,
)

logger = logging.getLogger("zonata.host.pairing")
ensure_host_permission_tables()


class PairingManager:
    """Manages secure one-time pairing between the user's host machine and cloud tenant."""

    CODE_TTL_SECONDS = 300.0  # 5-minute pairing code validity window

    @classmethod
    def hash_code(cls, code: str) -> str:
        return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()

    @classmethod
    @tenant_scoped
    def initiate_pairing(
        cls,
        tenant_id: str,
        company_id: str,
        owner_id: str,
        device_name: str,
        os_type: str,
    ) -> Tuple[str, str, float]:
        """
        Initiates a pairing workflow for a new device.
        Returns (device_id, one_time_code, expires_at).
        """
        device_id = f"dev_{uuid.uuid4().hex[:12]}"
        one_time_code = f"{secrets.randbelow(1000000):06d}"
        code_hash = cls.hash_code(one_time_code)
        now = time.time()
        expires_at = now + cls.CODE_TTL_SECONDS

        sql = """
        INSERT INTO devices (
            device_id, tenant_id, company_id, owner_id, device_name,
            os_type, public_key, pairing_status, pairing_code_hash,
            pairing_code_expires_at, last_seen_at, created_at
        ) VALUES (
            :device_id, :tenant_id, :company_id, :owner_id, :device_name,
            :os_type, '', 'PENDING', :pairing_code_hash,
            :pairing_code_expires_at, :last_seen_at, :created_at
        )
        """
        with db.get_connection() as conn:
            conn.execute(
                sql,
                {
                    "device_id": device_id,
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "owner_id": owner_id,
                    "device_name": device_name,
                    "os_type": os_type,
                    "pairing_code_hash": code_hash,
                    "pairing_code_expires_at": expires_at,
                    "last_seen_at": now,
                    "created_at": now,
                },
            )
            if hasattr(conn, "commit"):
                conn.commit()

        logger.info(f"Initiated pairing for device {device_id} ({device_name}) under tenant {tenant_id}")
        return device_id, one_time_code, expires_at

    @classmethod
    @tenant_scoped
    def complete_pairing(
        cls,
        device_id: str,
        one_time_code: str,
        public_key: str,
        is_human_step_up_authenticated: bool,
    ) -> DeviceRecord:
        """
        Completes pairing by verifying the code and binding the public key.
        Requires step-up authentication of the human owner.
        """
        if not is_human_step_up_authenticated:
            raise StepUpAuthenticationRequiredError(
                "Pairing requires verified step-up authentication by the human owner."
            )

        if not public_key or len(public_key.strip()) < 32:
            raise HostSecurityViolation("Invalid public key provided for device pairing.")

        now = time.time()
        select_sql = """
        SELECT device_id, tenant_id, company_id, owner_id, device_name,
               os_type, public_key, pairing_status, pairing_code_hash,
               pairing_code_expires_at, last_seen_at, created_at
        FROM devices
        WHERE device_id = :device_id
        """
        with db.get_connection() as conn:
            row = conn.execute(select_sql, {"device_id": device_id}).fetchone()
            if not row:
                raise HostSecurityViolation(f"Device {device_id} not found.")

            if row["pairing_status"] == DeviceStatus.PAIRED.value:
                raise HostSecurityViolation(f"Device {device_id} is already paired.")

            code_hash = row["pairing_code_hash"]
            expires_at = row["pairing_code_expires_at"]

            if not code_hash or not expires_at:
                raise HostSecurityViolation("No active pairing session found for this device.")

            if now > expires_at:
                raise HostSecurityViolation("Pairing code has expired. Please initiate pairing again.")

            computed_hash = cls.hash_code(one_time_code)
            if not hmac.compare_digest(computed_hash, code_hash):
                raise HostSecurityViolation("Invalid pairing code provided.")

            update_sql = """
            UPDATE devices
            SET public_key = :public_key,
                pairing_status = 'PAIRED',
                pairing_code_hash = NULL,
                pairing_code_expires_at = NULL,
                last_seen_at = :last_seen_at
            WHERE device_id = :device_id
            """
            conn.execute(
                update_sql,
                {
                    "device_id": device_id,
                    "public_key": public_key.strip(),
                    "last_seen_at": now,
                },
            )
            if hasattr(conn, "commit"):
                conn.commit()

        logger.info(f"Successfully paired device {device_id} with public key binding.")
        return DeviceRecord(
            device_id=device_id,
            tenant_id=row["tenant_id"],
            company_id=row["company_id"],
            owner_id=row["owner_id"],
            device_name=row["device_name"],
            os_type=row["os_type"],
            public_key=public_key.strip(),
            pairing_status=DeviceStatus.PAIRED,
            last_seen_at=now,
            created_at=row["created_at"],
        )

    @classmethod
    @tenant_scoped
    def get_device(cls, device_id: str) -> Optional[DeviceRecord]:
        sql = """
        SELECT device_id, tenant_id, company_id, owner_id, device_name,
               os_type, public_key, pairing_status, pairing_code_hash,
               pairing_code_expires_at, last_seen_at, created_at
        FROM devices
        WHERE device_id = :device_id
        """
        with db.get_connection() as conn:
            row = conn.execute(sql, {"device_id": device_id}).fetchone()
            if not row:
                return None
            return DeviceRecord(
                device_id=row["device_id"],
                tenant_id=row["tenant_id"],
                company_id=row["company_id"],
                owner_id=row["owner_id"],
                device_name=row["device_name"],
                os_type=row["os_type"],
                public_key=row["public_key"],
                pairing_status=DeviceStatus(row["pairing_status"]),
                pairing_code_hash=row["pairing_code_hash"],
                pairing_code_expires_at=row["pairing_code_expires_at"],
                last_seen_at=row["last_seen_at"],
                created_at=row["created_at"],
            )

    @classmethod
    @tenant_scoped
    def revoke_device(cls, device_id: str, actor_id: str) -> bool:
        now = time.time()
        sql = """
        UPDATE devices
        SET pairing_status = 'REVOKED',
            last_seen_at = :now
        WHERE device_id = :device_id
        """
        with db.get_connection() as conn:
            conn.execute(sql, {"device_id": device_id, "now": now})
            if hasattr(conn, "commit"):
                conn.commit()
        logger.warning(f"Device {device_id} revoked by actor {actor_id}")
        return True
