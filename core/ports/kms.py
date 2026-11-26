"""ZONATA Sovereign Core — Key Management Port & Envelope KMS Adapter.

Implements OpenCode Step 1D.6:
- Port interface: KeyManagementPort
- Methods: generate_data_key, encrypt, decrypt, rewrap.
- Invariant: Never stores plaintext master key in the database.
- RealProvider: SovereignEnvelopeKMSProvider (AES-256-GCM envelope encryption).
- NotConfiguredProvider: When master key / KMS endpoint missing.
- SandboxProvider: Test-only simulation when ZONATA_TEST_MODE=1.
"""

from __future__ import annotations
import base64
import hashlib
import json
import os
import secrets
import struct
import time
from typing import Any, Dict, Optional, Tuple

from core.ports.base import (
    Port,
    PortStatus,
    ProviderResult,
    NotConfiguredProvider,
    SandboxProvider,
)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class KeyManagementPort(Port):
    name = "key_management"
    capability = "key_management"

    def generate_data_key(
        self,
        key_spec: str = "AES_256",
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes, bytes]:
        """Returns (result, plaintext_dek, encrypted_dek_blob)."""
        raise NotImplementedError

    def encrypt(
        self,
        plaintext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        """Envelope encrypts plaintext. Returns (result, envelope_ciphertext_blob)."""
        raise NotImplementedError

    def decrypt(
        self,
        envelope_ciphertext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        """Decrypts envelope ciphertext. Returns (result, plaintext)."""
        raise NotImplementedError

    def rewrap(
        self,
        envelope_ciphertext: bytes,
        old_context: Optional[Dict[str, str]] = None,
        new_context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        """Re-encrypts the envelope's data encryption key under new context/master key."""
        raise NotImplementedError


class SovereignEnvelopeKMSProvider(KeyManagementPort):
    """Real sovereign envelope KMS adapter using AES-256-GCM."""

    def __init__(self, master_key_material: Optional[str] = None):
        # Master key must be supplied explicitly or via environment. There is no
        # hardcoded fallback: an unconfigured KMS reports NOT_CONFIGURED instead
        # of running with a publicly-known key.
        raw_key = master_key_material or os.environ.get("KMS_MASTER_KEY") or os.environ.get("SECRET_VAULT_KEY")
        self._configured = bool(raw_key) and HAS_CRYPTOGRAPHY
        if self._configured:
            self._master_key_bytes = hashlib.sha256(raw_key.encode("utf-8")).digest()
            self._master_aesgcm = AESGCM(self._master_key_bytes)
        else:
            self._master_key_bytes = b""
            self._master_aesgcm = None
        super().__init__(provider_name="sovereign_aes_gcm_kms", sandbox=False)

    def _unconfigured_result(self) -> ProviderResult:
        return ProviderResult(
            status=PortStatus.NOT_CONFIGURED,
            provider=self.provider_name,
            provider_ref=None,
            sandbox=False,
            latency_ms=0.0,
            cost="UNMEASURED",
            error="KMS master key not configured (set KMS_MASTER_KEY or SECRET_VAULT_KEY)",
        )

    def _aad_from_context(self, context: Optional[Dict[str, str]]) -> bytes:
        if not context:
            return b""
        sorted_items = sorted(context.items())
        return json.dumps(sorted_items, separators=(",", ":")).encode("utf-8")

    def probe(self) -> ProviderResult:
        if not self._configured:
            return self._unconfigured_result()
        t0 = time.perf_counter()
        try:
            if not HAS_CRYPTOGRAPHY or not self._master_aesgcm:
                raise RuntimeError("cryptography library or master key not initialized")

            # Perform harmless test encryption of 16-byte nonce
            test_nonce = secrets.token_bytes(12)
            test_ct = self._master_aesgcm.encrypt(test_nonce, b"probe", b"aad")
            test_pt = self._master_aesgcm.decrypt(test_nonce, test_ct, b"aad")
            assert test_pt == b"probe"

            lat = (time.perf_counter() - t0) * 1000.0
            key_id = f"kms_kdf_sha256_{hashlib.sha256(self._master_key_bytes).hexdigest()[:16]}"
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=key_id,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"cipher": "AES-256-GCM", "envelope_kms": True}
            )
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"KMS probe failure: {str(e)}"
            )

    def generate_data_key(
        self,
        key_spec: str = "AES_256",
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes, bytes]:
        if not self._configured:
            return self._unconfigured_result(), b"", b""
        t0 = time.perf_counter()
        try:
            plaintext_dek = secrets.token_bytes(32)
            nonce = secrets.token_bytes(12)
            aad = self._aad_from_context(context)

            # Encrypt DEK under Master Key
            encrypted_dek_raw = self._master_aesgcm.encrypt(nonce, plaintext_dek, aad)
            # Pack: [12 bytes nonce][encrypted_dek_raw]
            encrypted_dek_blob = nonce + encrypted_dek_raw

            lat = (time.perf_counter() - t0) * 1000.0
            key_ref = f"dek_{hashlib.sha256(encrypted_dek_blob).hexdigest()[:16]}"
            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=key_ref,
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"key_spec": key_spec, "aad_context": list((context or {}).keys())}
            )
            return res, plaintext_dek, encrypted_dek_blob
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"generate_data_key failed: {str(e)}"
            )
            return res, b"", b""

    def encrypt(
        self,
        plaintext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        if not self._configured:
            return self._unconfigured_result(), b""
        t0 = time.perf_counter()
        try:
            # 1. Generate DEK
            gen_res, plaintext_dek, encrypted_dek_blob = self.generate_data_key("AES_256", context)
            if gen_res.status != PortStatus.OK:
                return gen_res, b""

            # 2. Encrypt plaintext with DEK
            dek_aesgcm = AESGCM(plaintext_dek)
            data_nonce = secrets.token_bytes(12)
            data_aad = self._aad_from_context(context)
            data_ciphertext = dek_aesgcm.encrypt(data_nonce, plaintext, data_aad)

            # 3. Assemble Envelope Blob:
            # Format: [MAGIC 4B (b'ZENV')][VERSION 2B (0x01)][DEK_LEN 2B][ENCRYPTED_DEK][DATA_NONCE 12B][DATA_CIPHERTEXT]
            header = b"ZENV" + struct.pack(">HH", 1, len(encrypted_dek_blob))
            envelope = header + encrypted_dek_blob + data_nonce + data_ciphertext

            lat = (time.perf_counter() - t0) * 1000.0
            blob_hash = hashlib.sha256(envelope).hexdigest()[:16]
            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=f"env_{blob_hash}",
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"cipher": "AES-256-GCM", "envelope_bytes": len(envelope)}
            )
            return res, envelope
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"KMS envelope encryption error: {str(e)}"
            )
            return res, b""

    def decrypt(
        self,
        envelope_ciphertext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        if not self._configured:
            return self._unconfigured_result(), b""
        t0 = time.perf_counter()
        try:
            if not envelope_ciphertext.startswith(b"ZENV"):
                raise ValueError("Invalid envelope magic header; not a ZONATA KMS envelope")

            # Parse header
            version, dek_len = struct.unpack(">HH", envelope_ciphertext[4:8])
            if version != 1:
                raise ValueError(f"Unsupported envelope version: {version}")

            offset = 8
            encrypted_dek_blob = envelope_ciphertext[offset:offset + dek_len]
            offset += dek_len

            data_nonce = envelope_ciphertext[offset:offset + 12]
            offset += 12
            data_ciphertext = envelope_ciphertext[offset:]

            # Decrypt DEK using Master Key
            dek_nonce = encrypted_dek_blob[:12]
            dek_raw_ct = encrypted_dek_blob[12:]
            aad = self._aad_from_context(context)
            plaintext_dek = self._master_aesgcm.decrypt(dek_nonce, dek_raw_ct, aad)

            # Decrypt Data using DEK
            dek_aesgcm = AESGCM(plaintext_dek)
            plaintext = dek_aesgcm.decrypt(data_nonce, data_ciphertext, aad)

            lat = (time.perf_counter() - t0) * 1000.0
            pt_digest = hashlib.sha256(plaintext).hexdigest()[:16]
            res = ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=f"dec_{pt_digest}",
                sandbox=False,
                latency_ms=lat,
                cost=0.0,
                metadata={"decrypted_bytes": len(plaintext)}
            )
            return res, plaintext
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000.0
            res = ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                latency_ms=lat,
                error=f"KMS decryption error: {str(e)}"
            )
            return res, b""

    def rewrap(
        self,
        envelope_ciphertext: bytes,
        old_context: Optional[Dict[str, str]] = None,
        new_context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        """Decrypts data and re-encrypts under new context without persistent key exposure."""
        if not self._configured:
            return self._unconfigured_result(), b""
        t0 = time.perf_counter()
        dec_res, plaintext = self.decrypt(envelope_ciphertext, old_context)
        if dec_res.status != PortStatus.OK:
            return dec_res, b""

        enc_res, new_envelope = self.encrypt(plaintext, new_context)
        if enc_res.status != PortStatus.OK:
            return enc_res, b""

        lat = (time.perf_counter() - t0) * 1000.0
        res = ProviderResult(
            status=PortStatus.OK,
            provider=self.provider_name,
            provider_ref=f"rewrap_{enc_res.provider_ref}",
            sandbox=False,
            latency_ms=lat,
            cost=0.0,
            metadata={"rewrapped": True}
        )
        return res, new_envelope


class NotConfiguredKMSProvider(KeyManagementPort):
    def __init__(self, reason: str = "KMS provider or cryptographic engine not configured"):
        super().__init__(provider_name="not_configured", sandbox=False)
        self.reason = reason

    def probe(self) -> ProviderResult:
        return NotConfiguredProvider("key_management", self.reason).probe()

    def generate_data_key(
        self,
        key_spec: str = "AES_256",
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes, bytes]:
        return self.probe(), b"", b""

    def encrypt(
        self,
        plaintext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        return self.probe(), b""

    def decrypt(
        self,
        envelope_ciphertext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        return self.probe(), b""

    def rewrap(
        self,
        envelope_ciphertext: bytes,
        old_context: Optional[Dict[str, str]] = None,
        new_context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        return self.probe(), b""


class SandboxKMSProvider(KeyManagementPort):
    """Test-only simulation active when ZONATA_TEST_MODE=1."""
    def __init__(self):
        super().__init__(provider_name="sandbox_kms", sandbox=True)

    def _is_test(self) -> bool:
        return os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")

    def probe(self) -> ProviderResult:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected")
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_kms_v1",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0,
            metadata={"sandbox": True}
        )

    def generate_data_key(
        self,
        key_spec: str = "AES_256",
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes, bytes]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), b"", b""
        raw_dek = b"sandbox_32_bytes_plaintext_dek!"
        enc_dek = b"sandbox_encrypted_dek_blob_data"
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_dek_1",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0
        ), raw_dek, enc_dek

    def encrypt(
        self,
        plaintext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), b""
        # Simple sandbox reversal obfuscation
        envelope = b"SBX_ENV_" + base64.b64encode(plaintext)
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_enc_1",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0
        ), envelope

    def decrypt(
        self,
        envelope_ciphertext: bytes,
        context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        if not self._is_test():
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox rejected"), b""
        if not envelope_ciphertext.startswith(b"SBX_ENV_"):
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Invalid sandbox envelope"), b""
        pt = base64.b64decode(envelope_ciphertext[8:])
        return ProviderResult(
            status=PortStatus.SANDBOX,
            provider=self.provider_name,
            provider_ref="sandbox_dec_1",
            sandbox=True,
            latency_ms=0.1,
            cost=0.0
        ), pt

    def rewrap(
        self,
        envelope_ciphertext: bytes,
        old_context: Optional[Dict[str, str]] = None,
        new_context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        dec_res, pt = self.decrypt(envelope_ciphertext, old_context)
        if dec_res.status != PortStatus.SANDBOX:
            return dec_res, b""
        return self.encrypt(pt, new_context)


class LocalEnvelopeKeyProvider(SovereignEnvelopeKMSProvider):
    """Local sovereign envelope key provider.

    Implements Step 1E envelope encryption requirement.
    RULE 41 ENFORCEMENT: Removed from production code path.
    Production profile refuses to start with interim local providers.
    """

    def __init__(self, master_key_material: Optional[str] = None):
        super().__init__(master_key_material=master_key_material)
        self.provider_name = "local_envelope_kms"

    def probe(self) -> ProviderResult:
        app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
        is_production = (
            (app_env in ("production", "prod", "staging"))
            or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")
            or (os.environ.get("ZONATA_PRODUCTION", "0") == "1")
        )
        if is_production:
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                provider_ref=None,
                sandbox=False,
                latency_ms=0.0,
                cost=0.0,
                error="Rule 41 Violation: LocalEnvelopeKeyProvider is prohibited in production profile.",
            )

        res = super().probe()
        if res.status == PortStatus.OK:
            allow_degraded = (
                os.environ.get("ZONATA_ALLOW_DEGRADED") == "1"
                or os.environ.get("LOCAL_ENVELOPE_KEY") == "1"
                or os.environ.get("USE_LOCAL_ENVELOPE_KMS") == "1"
            )
            if allow_degraded:
                return ProviderResult(
                    status=PortStatus.DEGRADED,
                    provider=self.provider_name,
                    provider_ref=res.provider_ref,
                    sandbox=False,
                    latency_ms=res.latency_ms,
                    cost=0.0,
                    metadata={"notice": "LocalEnvelopeKeyProvider running in sovereign degraded mode", "degraded": True}
                )
            else:
                return ProviderResult(
                    status=PortStatus.FAILED,
                    provider=self.provider_name,
                    provider_ref=None,
                    sandbox=False,
                    latency_ms=res.latency_ms,
                    cost=0.0,
                    error="Local envelope key provider prohibited in production without ZONATA_ALLOW_DEGRADED=1 or LOCAL_ENVELOPE_KEY=1"
                )
        return res


class OpenBaoTransitKMSProvider(KeyManagementPort):
    """
    Production OpenBao Transit KMS Provider (MPL-2.0).
    Implements envelope encryption via OpenBao Transit engine.
    """

    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        key_name: str = "zonata-root",
    ):
        super().__init__(provider_name="openbao_transit_kms", sandbox=False)
        self.addr = (addr or os.environ.get("OPENBAO_ADDR") or os.environ.get("VAULT_ADDR") or "http://localhost:8200").rstrip("/")
        self.token = token or os.environ.get("VAULT_TOKEN", "")
        self.key_name = key_name

    def _http_post(self, path: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        import urllib.request, urllib.error
        url = f"{self.addr}{path}"
        headers = {"X-Vault-Token": self.token, "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {"errors": [body or str(e)]}
            return e.code, parsed
        except Exception as e:
            return 500, {"errors": [str(e)]}

    def probe(self) -> ProviderResult:
        import urllib.request
        url = f"{self.addr}/v1/sys/seal-status"
        req = urllib.request.Request(url, headers={"X-Vault-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("sealed", True):
                    return ProviderResult(
                        status=PortStatus.FAILED,
                        provider=self.provider_name,
                        error="OpenBao Transit KMS is sealed",
                    )
                return ProviderResult(
                    status=PortStatus.OK,
                    provider=self.provider_name,
                    provider_ref=f"openbao://transit/{self.key_name}",
                    metadata={"transit_key": self.key_name, "version": data.get("version")},
                )
        except Exception as e:
            return ProviderResult(
                status=PortStatus.FAILED,
                provider=self.provider_name,
                error=f"OpenBao connection failed: {e}",
            )

    def generate_data_key(
        self, context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes, bytes]:
        t_key = (context or {}).get("tenant_id")
        key = f"tenant-{t_key}" if t_key else self.key_name
        payload: Dict[str, Any] = {"bits": 256}
        if context:
            b64_ctx = base64.b64encode(json.dumps(sorted(context.items())).encode("utf-8")).decode("utf-8")
            payload["context"] = b64_ctx
        code, resp = self._http_post(f"/v1/transit/datakey/plaintext/{key}", payload)
        if code == 200:
            data = resp.get("data", {})
            plain_dek = base64.b64decode(data.get("plaintext", ""))
            cipher_dek = data.get("ciphertext", "").encode("utf-8")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/datakey/{key}"), plain_dek, cipher_dek
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), b"", b""

    def encrypt(
        self, plaintext: bytes, context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        t_key = (context or {}).get("tenant_id")
        key = f"tenant-{t_key}" if t_key else self.key_name
        payload: Dict[str, Any] = {"plaintext": base64.b64encode(plaintext).decode("utf-8")}
        if context:
            b64_ctx = base64.b64encode(json.dumps(sorted(context.items())).encode("utf-8")).decode("utf-8")
            payload["context"] = b64_ctx
        code, resp = self._http_post(f"/v1/transit/encrypt/{key}", payload)
        if code == 200:
            ct = resp.get("data", {}).get("ciphertext", "").encode("utf-8")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{key}"), ct
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), b""

    def decrypt(
        self, envelope_ciphertext: bytes, context: Optional[Dict[str, str]] = None
    ) -> Tuple[ProviderResult, bytes]:
        t_key = (context or {}).get("tenant_id")
        key = f"tenant-{t_key}" if t_key else self.key_name
        payload: Dict[str, Any] = {"ciphertext": envelope_ciphertext.decode("utf-8")}
        if context:
            b64_ctx = base64.b64encode(json.dumps(sorted(context.items())).encode("utf-8")).decode("utf-8")
            payload["context"] = b64_ctx
        code, resp = self._http_post(f"/v1/transit/decrypt/{key}", payload)
        if code == 200:
            pt = base64.b64decode(resp.get("data", {}).get("plaintext", ""))
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{key}"), pt
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), b""

    def rewrap_key(
        self,
        envelope_ciphertext: bytes,
        old_context: Optional[Dict[str, str]] = None,
        new_context: Optional[Dict[str, str]] = None,
    ) -> Tuple[ProviderResult, bytes]:
        t_key = (new_context or old_context or {}).get("tenant_id")
        key = f"tenant-{t_key}" if t_key else self.key_name
        payload: Dict[str, Any] = {"ciphertext": envelope_ciphertext.decode("utf-8")}
        if old_context:
            payload["context"] = base64.b64encode(json.dumps(sorted(old_context.items())).encode("utf-8")).decode("utf-8")
        code, resp = self._http_post(f"/v1/transit/rewrap/{key}", payload)
        if code == 200:
            new_ct = resp.get("data", {}).get("ciphertext", "").encode("utf-8")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{key}"), new_ct
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), b""


def resolve_kms_provider() -> KeyManagementPort:
    app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
    is_production = (
        (app_env in ("production", "prod", "staging"))
        or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")
        or (os.environ.get("ZONATA_PRODUCTION", "0") == "1")
    )

    openbao_addr = os.environ.get("OPENBAO_ADDR") or os.environ.get("VAULT_ADDR")
    if openbao_addr:
        return OpenBaoTransitKMSProvider(addr=openbao_addr)

    use_local = (
        os.environ.get("USE_LOCAL_ENVELOPE_KMS") == "1"
        or os.environ.get("LOCAL_ENVELOPE_KEY") == "1"
        or os.environ.get("KMS_PROVIDER", "").lower() == "local"
    )

    if is_production and use_local:
        raise RuntimeError(
            "Rule 41 Violation: Production profile refuses to start with LocalEnvelopeKeyProvider. "
            "ZONATA_ALLOW_DEGRADED no longer covers key management or secrets."
        )

    raw_key = os.environ.get("KMS_MASTER_KEY") or os.environ.get("SECRET_VAULT_KEY")
    if HAS_CRYPTOGRAPHY and raw_key:
        if use_local:
            return LocalEnvelopeKeyProvider(raw_key)
        return SovereignEnvelopeKMSProvider(raw_key)

    is_test = os.environ.get("ZONATA_TEST_MODE") == "1" or os.environ.get("APP_ENV") in ("test", "testing")
    if is_test:
        return SandboxKMSProvider()

    if is_production:
        raise RuntimeError(
            "Rule 41 Violation: Production profile requires configured KMS or OpenBao. "
            "Unconfigured KMS is rejected."
        )

    return NotConfiguredKMSProvider(
        "KMS master key not configured (set KMS_MASTER_KEY, SECRET_VAULT_KEY, or OPENBAO_ADDR)"
    )

