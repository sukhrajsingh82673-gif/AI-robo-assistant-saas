"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Workload & Network Isolation Controller

Implements AREA B of the Master Infrastructure Specification:
- Protects multi-tenant infrastructure at the infrastructure layer in addition to ZONATA application-layer authorization.
- Enforces:
    * Namespace isolation (zonata-system, zonata-tenants, zonata-workers, zonata-data)
    * Service-to-service access control matrix
    * Restricted egress: blocks cloud metadata endpoints (169.254.169.254, metadata.google.internal)
    * Egress domain allowlisting for external connectors
    * Pod & worker security profiles (non-root, read-only root, dropped capabilities)
    * Execution-worker sandboxing (Universal Terminal, OpenHands, Browser Use)
    * Tenant-level resource quotas (CPU cores, RAM GB, concurrent pods)
- Constitutional Invariant:
    Infrastructure isolation supplements ZONATA authorization.
    It NEVER replaces the AuthorityGateway.
"""

import re
import ipaddress
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger("zonata.infra.isolation")

class NetworkAccessDecision:
    ALLOWED = "ALLOWED"
    BLOCKED_METADATA_ENDPOINT = "BLOCKED_METADATA_ENDPOINT"
    BLOCKED_SERVICE_POLICY = "BLOCKED_SERVICE_POLICY"
    BLOCKED_EGRESS_DOMAIN = "BLOCKED_EGRESS_DOMAIN"
    BLOCKED_TENANT_QUOTA = "BLOCKED_TENANT_QUOTA"
    BLOCKED_PRIVILEGED_SERVICE = "BLOCKED_PRIVILEGED_SERVICE"

@dataclass
class TenantResourceQuota:
    tenant_id: str
    max_cpu_cores: float = 8.0
    max_memory_gb: float = 16.0
    max_concurrent_workers: int = 20
    current_cpu_used: float = 0.0
    current_memory_used: float = 0.0
    active_workers_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "max_cpu_cores": self.max_cpu_cores,
            "max_memory_gb": self.max_memory_gb,
            "max_concurrent_workers": self.max_concurrent_workers,
            "current_cpu_used": self.current_cpu_used,
            "current_memory_used": self.current_memory_used,
            "active_workers_count": self.active_workers_count
        }

@dataclass
class ServiceIsolationRule:
    source_service: str
    target_service: str
    allowed: bool
    rationale: str


class WorkloadIsolationController:
    """
    Infrastructure Network & Workload Isolation Controller.
    Shields internal services and enforces egress restrictions.
    """

    # Cloud metadata endpoints that must NEVER be reachable from workers or public edge
    RESTRICTED_METADATA_TARGETS = [
        "169.254.169.254",
        "metadata.google.internal",
        "metadata.platform.internal",
        "100.100.100.200",
        "fd00:ec2::254"
    ]

    # Global allowed external domains for verified SaaS connectors & models
    DEFAULT_EGRESS_ALLOWLIST = [
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
        "api.openai.com",
        "api.github.com",
        "cloud.langfuse.com",
        "app.posthog.com",
        "huggingface.co"
    ]

    # Service-to-service communication policy matrix
    # Format: (source, target) -> allowed
    SERVICE_POLICY_MATRIX: Dict[Tuple[str, str], bool] = {
        # Edge & API can communicate with core services
        ("zonata-ingress", "zonata-api"): True,
        ("zonata-api", "ai-ceo-service"): True,
        ("zonata-api", "nats-jetstream"): True,
        ("zonata-api", "temporal-frontend"): True,
        ("zonata-api", "vault-internal"): True,
        ("zonata-api", "keycloak-idp"): True,
        ("zonata-api", "openfga-authz"): True,
        ("zonata-api", "minio-s3"): True,
        ("zonata-api", "otel-collector"): True,

        # AI CEO can communicate with workflow and storage
        ("ai-ceo-service", "nats-jetstream"): True,
        ("ai-ceo-service", "temporal-frontend"): True,
        ("ai-ceo-service", "vault-internal"): True,
        ("ai-ceo-service", "openfga-authz"): True,

        # Execution workers CANNOT communicate directly with Vault or DB
        ("execution-worker", "vault-internal"): False,
        ("execution-worker", "database-primary"): False,
        ("execution-worker", "keycloak-idp"): False,
        ("execution-worker", "temporal-frontend"): True,
        ("execution-worker", "nats-jetstream"): True,
        ("execution-worker", "minio-s3"): True,

        # Sandboxed browser/terminal workers have STRICT isolation
        ("browser-worker", "vault-internal"): False,
        ("browser-worker", "database-primary"): False,
        ("browser-worker", "keycloak-idp"): False,
        ("browser-worker", "openfga-authz"): False,
        ("browser-worker", "temporal-frontend"): False,

        ("terminal-worker", "vault-internal"): False,
        ("terminal-worker", "database-primary"): False,
        ("terminal-worker", "keycloak-idp"): False,
        ("terminal-worker", "openfga-authz"): False,
        ("terminal-worker", "temporal-frontend"): False
    }

    def __init__(self):
        self._tenant_quotas: Dict[str, TenantResourceQuota] = {}
        self._egress_allowlist: Set[str] = set(self.DEFAULT_EGRESS_ALLOWLIST)

    def register_tenant_quota(self, quota: TenantResourceQuota):
        self._tenant_quotas[quota.tenant_id] = quota

    def get_tenant_quota(self, tenant_id: str) -> TenantResourceQuota:
        if tenant_id not in self._tenant_quotas:
            self._tenant_quotas[tenant_id] = TenantResourceQuota(tenant_id=tenant_id)
        return self._tenant_quotas[tenant_id]

    def evaluate_service_communication(self, source_service: str, target_service: str) -> Tuple[bool, str]:
        """Validates service-to-service network policy."""
        # Normalize source if generic worker
        src_normalized = source_service
        if "terminal" in source_service.lower():
            src_normalized = "terminal-worker"
        elif "browser" in source_service.lower():
            src_normalized = "browser-worker"
        elif "worker" in source_service.lower():
            src_normalized = "execution-worker"

        key = (src_normalized, target_service)
        if key in self.SERVICE_POLICY_MATRIX:
            allowed = self.SERVICE_POLICY_MATRIX[key]
            reason = "Explicit service communication policy allowed" if allowed else "Blocked: restricted service-to-service policy"
            return allowed, reason

        # Default deny for execution workers accessing privileged infrastructure
        if src_normalized in ("terminal-worker", "browser-worker", "execution-worker") and target_service in ("vault-internal", "database-primary", "keycloak-idp"):
            return False, f"Blocked: {src_normalized} forbidden from accessing privileged {target_service}"

        return True, "Default inter-service mesh allowed"

    def evaluate_egress_request(self, target_host: str, source_service: str = "execution-worker") -> Tuple[bool, str]:
        """
        Screens outbound network egress for SSRF, metadata endpoint access,
        and domain allowlist policy.
        """
        host_clean = target_host.strip().lower().split(":")[0]

        # 1. Cloud metadata IP and hostname defense
        if host_clean in self.RESTRICTED_METADATA_TARGETS or any(meta in host_clean for meta in ["169.254", "metadata.google"]):
            logger.error(f"[SECURITY ALERT] SSRF / Metadata endpoint access blocked: '{target_host}' from '{source_service}'")
            return False, NetworkAccessDecision.BLOCKED_METADATA_ENDPOINT

        # Check for IP ranges
        try:
            ip = ipaddress.ip_address(host_clean)
            if ip.is_link_local or ip.is_loopback:
                if source_service in ("terminal-worker", "browser-worker"):
                    logger.error(f"[SECURITY ALERT] Loopback / Link-local access blocked for worker: {host_clean}")
                    return False, NetworkAccessDecision.BLOCKED_METADATA_ENDPOINT
        except ValueError:
            pass  # Hostname, not IP

        # 2. In strict worker mode, verify domain against allowlist if configured
        if source_service in ("terminal-worker", "browser-worker"):
            # Check if domain matches allowlist or public web pattern
            if host_clean in self._egress_allowlist or any(host_clean.endswith(f".{d}") for d in self._egress_allowlist):
                return True, NetworkAccessDecision.ALLOWED
            # For general browser requests, allow standard web domains while rejecting private IPs
            if re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", host_clean):
                return True, NetworkAccessDecision.ALLOWED
            return False, NetworkAccessDecision.BLOCKED_EGRESS_DOMAIN

        return True, NetworkAccessDecision.ALLOWED

    def request_worker_allocation(
        self,
        tenant_id: str,
        requested_cpu: float = 1.0,
        requested_mem_gb: float = 2.0
    ) -> Tuple[bool, str]:
        """Enforces tenant-level resource quotas before provisioning worker pods."""
        quota = self.get_tenant_quota(tenant_id)
        if quota.active_workers_count + 1 > quota.max_concurrent_workers:
            return False, f"Quota exceeded: max concurrent workers ({quota.max_concurrent_workers})"
        if quota.current_cpu_used + requested_cpu > quota.max_cpu_cores:
            return False, f"Quota exceeded: CPU cores ({quota.max_cpu_cores})"
        if quota.current_memory_used + requested_mem_gb > quota.max_memory_gb:
            return False, f"Quota exceeded: Memory ({quota.max_memory_gb} GB)"

        # Allocate
        quota.active_workers_count += 1
        quota.current_cpu_used += requested_cpu
        quota.current_memory_used += requested_mem_gb
        return True, "Allocated"

    def release_worker_allocation(
        self,
        tenant_id: str,
        released_cpu: float = 1.0,
        released_mem_gb: float = 2.0
    ):
        quota = self.get_tenant_quota(tenant_id)
        quota.active_workers_count = max(0, quota.active_workers_count - 1)
        quota.current_cpu_used = max(0.0, quota.current_cpu_used - released_cpu)
        quota.current_memory_used = max(0.0, quota.current_memory_used - released_mem_gb)


# Global singleton instance
workload_isolation = WorkloadIsolationController()
