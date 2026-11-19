"""Write-only secret storage for Settings V2.

Secrets are encrypted with AES-GCM using a master key supplied by the
environment (production) or a ``0600`` local key file (development).  The
database stores only ciphertext, nonce, key id, and the last four characters as
display metadata.  No public method returns ciphertext or plaintext; the
runtime-only ``decrypt_for_runtime`` exists for consumers that genuinely need
the credential and is never wired to an HTTP response.

Importing this module is side-effect free: the key is loaded lazily, so a test
that only imports the package does not create a key file.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets as pysecrets
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.settings.errors import SecretsUnavailable, ValidationError
from core.settings.models import ScopeType, SecretRef

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # pragma: no cover - dependency probe
    AESGCM = None  # type: ignore

MASTER_KEY_ENV = "ZONATA_SETTINGS_MASTER_KEY"
PREVIOUS_KEY_ENV = "ZONATA_SETTINGS_MASTER_KEY_PREVIOUS"
KEY_FILE_ENV = "ZONATA_SETTINGS_KEY_FILE"
DEFAULT_KEY_FILE = os.path.join("storage", ".settings_master_key")

PRODUCTION_ENV_VALUES = {"production", "prod", "ga", "live"}
MAX_SECRET_LENGTH = 8192


def _is_production() -> bool:
    env = str(os.environ.get("ZONATA_ENV", "")).strip().lower()
    if env in PRODUCTION_ENV_VALUES:
        return True
    return str(os.environ.get("ZONATA_PUBLIC_GA_MODE", "0")) == "1"


def _decode_key(raw: str) -> Optional[bytes]:
    """Accept 32 raw bytes, 64 hex characters, or base64-encoded 32 bytes."""
    value = str(raw or "").strip()
    if not value:
        return None
    if len(value) == 64:
        try:
            decoded = bytes.fromhex(value)
            if len(decoded) == 32:
                return decoded
        except ValueError:
            pass
    raw_bytes = value.encode("utf-8")
    if len(raw_bytes) == 32:
        return raw_bytes
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    try:
        decoded = base64.b64decode(value + "=" * (-len(value) % 4))
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return None


def key_id_for(key: bytes) -> str:
    """Stable, non-secret identifier for a key."""
    return "k_" + hashlib.sha256(key).hexdigest()[:16]


def _read_key_file(path: str) -> Optional[bytes]:
    if not path or not os.path.exists(path):
        return None
    try:
        stat = os.stat(path)
        if stat.st_mode & 0o077:
            # A world/group readable master key is worse than no key.
            raise SecretsUnavailable(
                f"Master key file {path!r} must not be readable by group or others."
            )
        with open(path, "rb") as handle:
            return _decode_key(handle.read().decode("utf-8"))
    except SecretsUnavailable:
        raise
    except Exception:
        return None


def _write_key_file(path: str) -> bytes:
    key = pysecrets.token_bytes(32)
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(base64.urlsafe_b64encode(key))
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return key


@dataclass(frozen=True)
class MasterKey:
    key: bytes
    key_id: str
    source: str

    def __repr__(self) -> str:  # never leak bytes
        return f"MasterKey(key_id={self.key_id!r}, source={self.source!r})"


class KeyRing:
    """Current key plus optional previous keys for decryption during rotation."""

    def __init__(self, current: MasterKey, previous: Tuple[MasterKey, ...] = ()) -> None:
        self.current = current
        self._by_id = {key.key_id: key for key in (current,) + previous}

    @classmethod
    def load(cls, allow_generate: bool = True) -> "KeyRing":
        raw = os.environ.get(MASTER_KEY_ENV, "")
        key = _decode_key(raw)
        production = _is_production()

        if production:
            # Production may only use an explicit environment key.  A file is
            # an operator convenience for local development, not a production
            # secret store.
            if key is None:
                raise SecretsUnavailable(
                    "Secret writes are disabled: production requires "
                    "ZONATA_SETTINGS_MASTER_KEY to be a valid 32-byte key."
                )
            source = "env"
        elif key is None:
            key_file = os.environ.get(KEY_FILE_ENV, DEFAULT_KEY_FILE)
            key = _read_key_file(key_file)
            source = f"file:{key_file}"
            if key is None and allow_generate:
                if os.path.exists(key_file):
                    raise SecretsUnavailable(
                        f"Master key file {key_file!r} exists but is not a valid 32-byte key."
                    )
                key = _write_key_file(key_file)
                source = f"generated:{key_file}"
        else:
            source = "env"

        if key is None:
            raise SecretsUnavailable(
                "Secret writes are disabled: set ZONATA_SETTINGS_MASTER_KEY "
                "to a 32-byte key (64 hex characters or base64)."
            )

        previous: List[MasterKey] = []
        for item in str(os.environ.get(PREVIOUS_KEY_ENV, "")).split(","):
            decoded = _decode_key(item)
            if decoded:
                previous.append(MasterKey(decoded, key_id_for(decoded), "previous"))
        return cls(MasterKey(key, key_id_for(key), source), tuple(previous))

    def get(self, key_id: str) -> Optional[MasterKey]:
        return self._by_id.get(key_id)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SettingsSecretVault:
    """Encrypted, write-only secret store."""

    def __init__(self, keyring: Optional[KeyRing] = None, clock: Any = time.time) -> None:
        self._keyring = keyring
        self._clock = clock

    @property
    def available(self) -> bool:
        try:
            self._require_ring()
            return True
        except SecretsUnavailable:
            return False

    def _require_ring(self) -> KeyRing:
        if self._keyring is None:
            self._keyring = KeyRing.load()
        if AESGCM is None:
            raise SecretsUnavailable(
                "The 'cryptography' package is required to store settings secrets."
            )
        return self._keyring

    # ----------------------------------------------------------- encryption
    def _encrypt(self, plaintext: str) -> Tuple[str, str, str]:
        ring = self._require_ring()
        nonce = pysecrets.token_bytes(12)
        cipher = AESGCM(ring.current.key)
        ciphertext = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)
        return _b64encode(ciphertext), _b64encode(nonce), ring.current.key_id

    def _decrypt(self, ciphertext_b64: str, nonce_b64: str, key_id: str) -> str:
        ring = self._require_ring()
        master = ring.get(key_id)
        if master is None:
            raise SecretsUnavailable(
                "The master key that encrypted this secret is not available."
            )
        try:
            cipher = AESGCM(master.key)
            plaintext = cipher.decrypt(_b64decode(nonce_b64), _b64decode(ciphertext_b64), None)
            return plaintext.decode("utf-8")
        except Exception:
            # Never include ciphertext, nonce, or plaintext in the error.
            raise SecretsUnavailable("The stored secret could not be decrypted.")

    # --------------------------------------------------------------- writes
    def put(
        self,
        conn: Any,
        *,
        tenant_id: str,
        company_id: Optional[str],
        scope_type: ScopeType,
        scope_id: str,
        name: str,
        value: str,
        created_by: str,
        commit: bool = False,
    ) -> SecretRef:
        if not tenant_id or not scope_id:
            raise ValidationError("tenant_id and scope_id are required for a secret.")
        if not name:
            raise ValidationError("A secret name is required.")
        if value is None or not str(value).strip():
            raise ValidationError("A secret value is required.")
        text = str(value)
        if len(text) > MAX_SECRET_LENGTH:
            raise ValidationError(f"A secret may not exceed {MAX_SECRET_LENGTH} characters.")
        if "\x00" in text:
            raise ValidationError("A secret may not contain NUL bytes.")

        ciphertext, nonce, key_id = self._encrypt(text)
        # A short secret would otherwise be fully exposed by its own hint.
        last4 = text[-4:] if len(text) >= 8 else ""
        now = float(self._clock())
        scope_value = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)

        existing = conn.execute(
            """
            SELECT secret_id, version, created_at FROM secrets
            WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND name = ?
            """,
            (tenant_id, scope_value, scope_id, name),
        ).fetchone()

        if existing is not None:
            secret_id = str(existing[0])
            version = int(existing[1] or 1) + 1
            created_at = float(existing[2] or now)
            conn.execute(
                """
                UPDATE secrets SET
                    tenant_id = ?, company_id = ?, ciphertext = ?, nonce = ?,
                    key_id = ?, last4 = ?, rotated_at = ?, version = ?
                WHERE secret_id = ?
                """,
                (
                    tenant_id,
                    company_id,
                    ciphertext,
                    nonce,
                    key_id,
                    last4,
                    now,
                    version,
                    secret_id,
                ),
            )
            rotated_at = now
        else:
            secret_id = f"sec_{pysecrets.token_hex(12)}"
            version = 1
            created_at = now
            rotated_at = None
            conn.execute(
                """
                INSERT INTO secrets
                    (secret_id, tenant_id, company_id, scope_type, scope_id,
                     name, ciphertext, nonce, key_id, last4, created_by,
                     created_at, rotated_at, last_used_at, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 1)
                """,
                (
                    secret_id,
                    tenant_id,
                    company_id,
                    scope_value,
                    scope_id,
                    name,
                    ciphertext,
                    nonce,
                    key_id,
                    last4,
                    created_by,
                    created_at,
                ),
            )

        if commit:
            conn.commit()
        return SecretRef(
            name=name,
            scope_type=scope_type if isinstance(scope_type, ScopeType) else ScopeType(str(scope_type)),
            scope_id=scope_id,
            last4=last4,
            key_id=key_id,
            created_by=created_by,
            created_at=created_at,
            rotated_at=rotated_at,
            configured=True,
            version=version,
        )

    def revoke(
        self,
        conn: Any,
        *,
        tenant_id: str,
        scope_type: ScopeType,
        scope_id: str,
        name: str,
        commit: bool = False,
    ) -> bool:
        scope_value = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
        cursor = conn.execute(
            """
            DELETE FROM secrets
            WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND name = ?
            """,
            (tenant_id, scope_value, scope_id, name),
        )
        if commit:
            conn.commit()
        return int(getattr(cursor, "rowcount", 0) or 0) > 0

    # ---------------------------------------------------------------- reads
    def list_metadata(
        self,
        conn: Any,
        tenant_id: str,
        company_id: Optional[str] = None,
        scope_type: Optional[ScopeType] = None,
        scope_id: Optional[str] = None,
    ) -> List[SecretRef]:
        query = """
            SELECT name, scope_type, scope_id, last4, key_id, created_by,
                   created_at, rotated_at, last_used_at, version
            FROM secrets WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if company_id:
            # Platform and organization secrets are tenant-wide and stored
            # without a company.  Company listings include them; company-scoped
            # secrets always carry a company id and stay isolated.
            query += " AND (company_id = ? OR company_id IS NULL)"
            params.append(company_id)
        if scope_type is not None:
            query += " AND scope_type = ?"
            params.append(scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type))
        if scope_id:
            query += " AND scope_id = ?"
            params.append(scope_id)
        query += " ORDER BY name ASC"
        rows = conn.execute(query, tuple(params)).fetchall()
        result: List[SecretRef] = []
        for row in rows:
            try:
                scope = ScopeType(str(row[1]))
            except ValueError:
                continue
            result.append(
                SecretRef(
                    name=str(row[0]),
                    scope_type=scope,
                    scope_id=str(row[2]),
                    last4=str(row[3] or ""),
                    key_id=str(row[4] or ""),
                    created_by=row[5],
                    created_at=float(row[6]) if row[6] is not None else None,
                    rotated_at=float(row[7]) if row[7] is not None else None,
                    last_used_at=float(row[8]) if row[8] is not None else None,
                    configured=True,
                    version=int(row[9] or 1),
                )
            )
        return result

    def get_metadata(
        self,
        conn: Any,
        tenant_id: str,
        scope_type: ScopeType,
        scope_id: str,
        name: str,
    ) -> Optional[SecretRef]:
        scope_value = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
        row = conn.execute(
            """
            SELECT name, scope_type, scope_id, last4, key_id, created_by,
                   created_at, rotated_at, last_used_at, version
            FROM secrets
            WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND name = ?
            """,
            (tenant_id, scope_value, scope_id, name),
        ).fetchone()
        if row is None:
            return None
        return SecretRef(
            name=str(row[0]),
            scope_type=scope_type if isinstance(scope_type, ScopeType) else ScopeType(scope_value),
            scope_id=str(row[2]),
            last4=str(row[3] or ""),
            key_id=str(row[4] or ""),
            created_by=row[5],
            created_at=float(row[6]) if row[6] is not None else None,
            rotated_at=float(row[7]) if row[7] is not None else None,
            last_used_at=float(row[8]) if row[8] is not None else None,
            configured=True,
            version=int(row[9] or 1),
        )

    def decrypt_for_runtime(
        self,
        conn: Any,
        tenant_id: str,
        scope_type: ScopeType,
        scope_id: str,
        name: str,
    ) -> Optional[str]:
        """Runtime-only plaintext lookup.  Never expose this over HTTP."""
        scope_value = scope_type.value if isinstance(scope_type, ScopeType) else str(scope_type)
        row = conn.execute(
            """
            SELECT ciphertext, nonce, key_id FROM secrets
            WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND name = ?
            """,
            (tenant_id, scope_value, scope_id, name),
        ).fetchone()
        if row is None:
            return None
        plaintext = self._decrypt(str(row[0]), str(row[1]), str(row[2]))
        try:
            conn.execute(
                "UPDATE secrets SET last_used_at = ? WHERE tenant_id = ? AND scope_type = ? AND scope_id = ? AND name = ?",
                (float(self._clock()), tenant_id, scope_value, scope_id, name),
            )
        except Exception:
            pass
        return plaintext


settings_vault = SettingsSecretVault()
