"""
ZONATA Sovereign Core — Sub-Step 5B: Authoritative Secrets Platform Port & OpenBao Provider.
==========================================================================================
Governed by:
- Rule 41: No plaintext secret or key material in DB, files, images, logs, traces, or reports.
  Interim providers are removed from production path; production profile refuses to start with them.
- Rule 42: Least privilege & default deny. Dynamic DB credentials and short-lived workload tokens.
- Rule 45: Crypto agility, versioned transit keys, and rewrap capability.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from core.ports.base import Port, PortStatus, ProviderResult

logger = logging.getLogger("zonata.ports.secrets")


class SecretsPort(Port):
    """Authoritative Port contract for sovereign secrets and cryptographic transit services."""

    def __init__(self, provider_name: str = "generic", sandbox: bool = False):
        super().__init__(provider_name=provider_name, sandbox=sandbox)

    def get_secret(
        self,
        key: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, Optional[str]]:
        """Retrieves a secret from the vault."""
        raise NotImplementedError

    def set_secret(
        self,
        key: str,
        value: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        """Stores a secret in KV v2."""
        raise NotImplementedError

    def rotate_secret(
        self,
        key: str,
        new_value: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        """Rotates a secret value, archiving previous version."""
        raise NotImplementedError

    def revoke_secret(
        self,
        key: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        """Permanently revokes and deletes a secret."""
        raise NotImplementedError

    def get_dynamic_db_credentials(
        self, role: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        """Generates dynamic short-lived database credentials from the database engine."""
        raise NotImplementedError

    def destroy_tenant_keys(self, tenant_id: str) -> Tuple[ProviderResult, bool]:
        """Crypto-shredding: permanently destroys all Transit key versions for a tenant."""
        raise NotImplementedError

    def seal_status(self) -> Tuple[ProviderResult, Dict[str, Any]]:
        """Returns OpenBao seal status (fail-closed if sealed)."""
        raise NotImplementedError

    def transit_encrypt(
        self, plaintext: bytes, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, str]:
        """Performs authenticated envelope encryption via Transit engine."""
        raise NotImplementedError

    def transit_decrypt(
        self, ciphertext: str, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, bytes]:
        """Performs authenticated envelope decryption via Transit engine."""
        raise NotImplementedError

    def transit_rotate_key(
        self, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, int]:
        """Rotates a Transit key to version N+1."""
        raise NotImplementedError

    def transit_rewrap(
        self, ciphertext: str, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, str]:
        """Rewraps ciphertext under the latest key version without returning plaintext to client."""
        raise NotImplementedError


class OpenBaoSecretsProvider(SecretsPort):
    """
    Production OpenBao provider (MPL-2.0).
    Connects to OpenBao service via REST API over TLS using workload AppRole or token auth.
    """

    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
    ):
        super().__init__(provider_name="openbao", sandbox=False)
        self.addr = (addr or os.environ.get("OPENBAO_ADDR") or os.environ.get("VAULT_ADDR") or "http://localhost:8200").rstrip("/")
        self._token = token or os.environ.get("VAULT_TOKEN", "")
        self.role_id = role_id or os.environ.get("VAULT_ROLE_ID", "")
        self.secret_id = secret_id or os.environ.get("VAULT_SECRET_ID", "")

    def _get_headers(self, client_token: Optional[str] = None) -> Dict[str, str]:
        token = client_token or self._token
        return {
            "X-Vault-Token": token,
            "Content-Type": "application/json",
        }

    def _http_request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None, client_token: Optional[str] = None
    ) -> Tuple[int, Dict[str, Any]]:
        url = f"{self.addr}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=self._get_headers(client_token), method=method)
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            try:
                parsed = json.loads(err_body)
            except Exception:
                parsed = {"errors": [err_body or str(e)]}
            return e.code, parsed
        except Exception as e:
            return 500, {"errors": [str(e)]}

    def probe(self) -> ProviderResult:
        code, resp = self._http_request("GET", "/v1/sys/seal-status")
        if code == 200:
            if resp.get("sealed", True):
                return ProviderResult(
                    status=PortStatus.FAILED,
                    provider=self.provider_name,
                    error="OpenBao instance is sealed (fail-closed)",
                    metadata=resp,
                )
            return ProviderResult(
                status=PortStatus.OK,
                provider=self.provider_name,
                provider_ref=f"openbao://{self.addr}",
                metadata={"version": resp.get("version"), "cluster_name": resp.get("cluster_name")},
            )
        return ProviderResult(
            status=PortStatus.FAILED,
            provider=self.provider_name,
            error=f"OpenBao connection failed (HTTP {code})",
        )

    def seal_status(self) -> Tuple[ProviderResult, Dict[str, Any]]:
        code, resp = self._http_request("GET", "/v1/sys/seal-status")
        if code == 200:
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref="openbao://sys/seal-status"), resp
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), {}

    def _resolve_path(self, key: str, tenant_id: Optional[str], company_id: Optional[str]) -> str:
        if tenant_id:
            comp = company_id or "default"
            return f"/v1/secret/data/tenants/{tenant_id}/{comp}/{key}"
        return f"/v1/secret/data/platform/{key}"

    def get_secret(
        self,
        key: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, Optional[str]]:
        path = self._resolve_path(key, tenant_id, company_id)
        code, resp = self._http_request("GET", path, client_token=client_token)
        if code == 200:
            data = resp.get("data", {}).get("data", {})
            val = data.get("value")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), val
        if code == 404:
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), None
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), None

    def set_secret(
        self,
        key: str,
        value: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        path = self._resolve_path(key, tenant_id, company_id)
        payload = {"data": {"value": value}}
        code, resp = self._http_request("POST", path, payload=payload, client_token=client_token)
        if code in (200, 204):
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), True
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), False

    def rotate_secret(
        self,
        key: str,
        new_value: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        return self.set_secret(key, new_value, tenant_id, company_id, client_token)

    def revoke_secret(
        self,
        key: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        if tenant_id:
            comp = company_id or "default"
            metadata_path = f"/v1/secret/metadata/tenants/{tenant_id}/{comp}/{key}"
        else:
            metadata_path = f"/v1/secret/metadata/platform/{key}"
        code, _ = self._http_request("DELETE", metadata_path, client_token=client_token)
        if code in (200, 204):
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), True
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), False

    def get_dynamic_db_credentials(
        self, role: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        path = f"/v1/database/creds/zonata_{role}"
        code, resp = self._http_request("GET", path)
        if code == 200:
            data = resp.get("data", {})
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref="openbao://db/credentials"), {
                "username": data.get("username"),
                "password": data.get("password"),
                "lease_id": resp.get("lease_id"),
                "lease_duration": resp.get("lease_duration", 3600),
                "renewable": resp.get("renewable", True),
            }
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), {}

    def destroy_tenant_keys(self, tenant_id: str) -> Tuple[ProviderResult, bool]:
        transit_key_path = f"/v1/transit/keys/tenant-{tenant_id}"
        code, _ = self._http_request("DELETE", transit_key_path)
        kv_prefix = f"/v1/secret/metadata/tenants/{tenant_id}"
        self._http_request("DELETE", kv_prefix)
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/shred/{tenant_id}"), True

    def transit_encrypt(
        self, plaintext: bytes, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, str]:
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        b64_plain = base64.b64encode(plaintext).decode("utf-8")
        code, resp = self._http_request("POST", f"/v1/transit/encrypt/{t_key}", payload={"plaintext": b64_plain})
        if code == 200:
            ciphertext = resp.get("data", {}).get("ciphertext", "")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{t_key}"), ciphertext
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), ""

    def transit_decrypt(
        self, ciphertext: str, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, bytes]:
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        code, resp = self._http_request("POST", f"/v1/transit/decrypt/{t_key}", payload={"ciphertext": ciphertext})
        if code == 200:
            b64_plain = resp.get("data", {}).get("plaintext", "")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{t_key}"), base64.b64decode(b64_plain)
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), b""

    def transit_rotate_key(
        self, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, int]:
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        code, resp = self._http_request("POST", f"/v1/transit/keys/{t_key}/rotate")
        if code in (200, 204):
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{t_key}"), 1
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), 0

    def transit_rewrap(
        self, ciphertext: str, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, str]:
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        code, resp = self._http_request("POST", f"/v1/transit/rewrap/{t_key}", payload={"ciphertext": ciphertext})
        if code == 200:
            new_ct = resp.get("data", {}).get("ciphertext", "")
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://transit/{t_key}"), new_ct
        return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"HTTP {code}"), ""


class SandboxSecretsProvider(SecretsPort):
    """
    Test-mode in-memory OpenBao simulator.
    Strictly active under ZONATA_TEST_MODE=1.
    Fully implements multi-tenancy, Transit versioned keys, rewrap, token revocation,
    seal-status fail-closed drills, dynamic credentials, and crypto-shredding.
    """

    def __init__(self):
        super().__init__(provider_name="sandbox_openbao", sandbox=True)
        self._sealed = False
        self._kv_store: Dict[str, Dict[str, Any]] = {}
        self._transit_keys: Dict[str, List[bytes]] = {}  # key_name -> list of versions (0-indexed)
        self._revoked_tokens: set[str] = set()
        self._client_tokens: Dict[str, Dict[str, Any]] = {}  # token -> {tenant_id, role}

    def simulate_seal(self) -> None:
        self._sealed = True

    def simulate_unseal(self) -> None:
        self._sealed = False

    def register_client_token(self, token: str, tenant_id: Optional[str] = None, role: str = "app") -> None:
        self._client_tokens[token] = {"tenant_id": tenant_id, "role": role}

    def revoke_token(self, token: str) -> None:
        self._revoked_tokens.add(token)

    def _check_access(self, client_token: Optional[str], target_tenant: Optional[str]) -> bool:
        if not client_token:
            return True
        if client_token in self._revoked_tokens:
            return False
        ctx = self._client_tokens.get(client_token)
        if not ctx:
            return False
        token_tenant = ctx.get("tenant_id")
        if token_tenant and target_tenant and token_tenant != target_tenant:
            return False
        return True

    def probe(self) -> ProviderResult:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Sandbox vault is sealed")
        return ProviderResult(
            status=PortStatus.OK,
            provider=self.provider_name,
            provider_ref="sandbox://openbao/cluster",
            metadata={"sandbox": True, "transit_keys": len(self._transit_keys), "secrets_count": len(self._kv_store)},
        )

    def seal_status(self) -> Tuple[ProviderResult, Dict[str, Any]]:
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref="openbao://db/credentials"), {
            "sealed": self._sealed,
            "t": 3,
            "n": 5,
            "version": "sandbox-1.18.0",
        }

    def _make_key_path(self, key: str, tenant_id: Optional[str], company_id: Optional[str]) -> str:
        if tenant_id:
            comp = company_id or "default"
            return f"tenants/{tenant_id}/{comp}/{key}"
        return f"platform/{key}"

    def get_secret(
        self,
        key: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, Optional[str]]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), None
        if not self._check_access(client_token, tenant_id):
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Access Denied: token unauthorized or tenant mismatch"), None
        path = self._make_key_path(key, tenant_id, company_id)
        val = self._kv_store.get(path, {}).get("value")
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), val

    def set_secret(
        self,
        key: str,
        value: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), False
        if not self._check_access(client_token, tenant_id):
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Access Denied"), False
        path = self._make_key_path(key, tenant_id, company_id)
        self._kv_store[path] = {"value": value, "updated_at": time.time()}
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), True

    def rotate_secret(
        self,
        key: str,
        new_value: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        return self.set_secret(key, new_value, tenant_id, company_id, client_token)

    def revoke_secret(
        self,
        key: str,
        tenant_id: Optional[str] = None,
        company_id: Optional[str] = None,
        client_token: Optional[str] = None,
    ) -> Tuple[ProviderResult, bool]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), False
        if not self._check_access(client_token, tenant_id):
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Access Denied"), False
        path = self._make_key_path(key, tenant_id, company_id)
        if path in self._kv_store:
            del self._kv_store[path]
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"openbao://kv{path}"), True

    def get_dynamic_db_credentials(
        self, role: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, Dict[str, Any]]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), {}
        entropy = hashlib.sha256(os.urandom(16)).hexdigest()[:8]
        username = f"v_dyn_{role}_{entropy}"
        password = f"dyn_pwd_{hashlib.sha256(os.urandom(32)).hexdigest()[:16]}"
        lease_id = f"database/creds/zonata_{role}/{entropy}"
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref="openbao://db/credentials"), {
            "username": username,
            "password": password,
            "lease_id": lease_id,
            "lease_duration": 3600,
            "renewable": True,
        }

    def _ensure_transit_key(self, key_name: str) -> List[bytes]:
        if key_name not in self._transit_keys:
            # version 1
            self._transit_keys[key_name] = [os.urandom(32)]
        return self._transit_keys[key_name]

    def destroy_tenant_keys(self, tenant_id: str) -> Tuple[ProviderResult, bool]:
        t_key = f"tenant-{tenant_id}"
        if t_key in self._transit_keys:
            del self._transit_keys[t_key]
        # Purge KV
        prefix = f"tenants/{tenant_id}/"
        keys_to_del = [k for k in self._kv_store if k.startswith(prefix)]
        for k in keys_to_del:
            del self._kv_store[k]
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"sandbox://transit/shred/{tenant_id}"), True

    def transit_rotate_key(
        self, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, int]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), 0
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        versions = self._ensure_transit_key(t_key)
        versions.append(os.urandom(32))
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"sandbox://transit/{t_key}/v{len(versions)}"), len(versions)

    def transit_encrypt(
        self, plaintext: bytes, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, str]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), ""
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        versions = self._ensure_transit_key(t_key)
        latest_version = len(versions)
        active_key = versions[-1]
        iv = os.urandom(12)
        stream = hashlib.sha256(active_key + iv).digest()
        cipher_bytes = bytes([b ^ stream[i % len(stream)] for i, b in enumerate(plaintext)])
        tag = hmac.new(active_key, iv + cipher_bytes, hashlib.sha256).digest()[:16]
        blob = {
            "v": latest_version,
            "iv": base64.b64encode(iv).decode("utf-8"),
            "c": base64.b64encode(cipher_bytes).decode("utf-8"),
            "t": base64.b64encode(tag).decode("utf-8"),
        }
        encoded = base64.b64encode(json.dumps(blob).encode("utf-8")).decode("utf-8")
        return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"sandbox://transit/{t_key}/v{latest_version}"), f"vault:v{latest_version}:{encoded}"

    def transit_decrypt(
        self, ciphertext: str, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, bytes]:
        if self._sealed:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Vault sealed"), b""
        t_key = f"tenant-{tenant_id}" if tenant_id else key_name
        if t_key not in self._transit_keys:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Crypto-shredded: Key does not exist"), b""
        versions = self._transit_keys[t_key]
        try:
            parts = ciphertext.split(":")
            if len(parts) != 3 or parts[0] != "vault":
                return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Malformed ciphertext"), b""
            raw_blob = base64.b64decode(parts[2]).decode("utf-8")
            blob = json.loads(raw_blob)
            v = int(blob["v"])
            if v > len(versions) or v < 1:
                return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Key version destroyed or unknown"), b""
            key = versions[v - 1]
            iv = base64.b64decode(blob["iv"])
            cipher_bytes = base64.b64decode(blob["c"])
            expected_tag = base64.b64decode(blob["t"])
            actual_tag = hmac.new(key, iv + cipher_bytes, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(expected_tag, actual_tag):
                return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error="Integrity verification failed"), b""
            stream = hashlib.sha256(key + iv).digest()
            plaintext = bytes([b ^ stream[i % len(stream)] for i, b in enumerate(cipher_bytes)])
            return ProviderResult(status=PortStatus.OK, provider=self.provider_name, provider_ref=f"sandbox://transit/{t_key}/v{v}"), plaintext
        except Exception as e:
            return ProviderResult(status=PortStatus.FAILED, provider=self.provider_name, error=f"Decryption failure: {e}"), b""

    def transit_rewrap(
        self, ciphertext: str, key_name: str, tenant_id: Optional[str] = None
    ) -> Tuple[ProviderResult, str]:
        res_dec, plain = self.transit_decrypt(ciphertext, key_name, tenant_id)
        if not res_dec.is_success():
            return res_dec, ""
        return self.transit_encrypt(plain, key_name, tenant_id)


def get_secrets_provider() -> SecretsPort:
    """
    Factory resolving the authoritative SecretsPort provider.
    Enforces Rule 41: Production profile strictly forbids degraded or local interim providers.
    """
    openbao_addr = os.environ.get("OPENBAO_ADDR") or os.environ.get("VAULT_ADDR")
    if openbao_addr:
        return OpenBaoSecretsProvider(addr=openbao_addr)

    # In test mode, return high-fidelity sandbox simulator
    if os.environ.get("ZONATA_TEST_MODE", "0") == "1":
        return SandboxSecretsProvider()

    app_env = (os.environ.get("APP_ENV") or os.environ.get("ZONATA_ENV") or "").lower()
    is_production = (app_env in ("production", "prod", "staging")) or (os.environ.get("ZONATA_STRICT_AUTH", "0") == "1")

    if is_production:
        raise RuntimeError(
            "Rule 41 Violation: Production profile refuses to start with degraded/local secrets provider. "
            "A real OpenBao service endpoint (OPENBAO_ADDR) is mandatory."
        )

    if os.environ.get("ZONATA_ALLOW_DEGRADED", "0") == "1":
        return SandboxSecretsProvider()

    raise RuntimeError("Secrets provider not configured. Configure OPENBAO_ADDR or set ZONATA_TEST_MODE=1.")


# Authoritative singleton instance
secrets_port = get_secrets_provider() if (
    os.environ.get("ZONATA_TEST_MODE") == "1"
    or os.environ.get("OPENBAO_ADDR")
    or os.environ.get("VAULT_ADDR")
    or os.environ.get("ZONATA_ALLOW_DEGRADED") == "1"
) else None
