"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Universal Runtime Router
Dynamically routes technical objectives to the optimal Linux execution profile and adapter
based on 18 criteria: capabilities, security, resources, architecture, desktop needs,
isolation level, network mode, and company policies.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
from dataclasses import dataclass, field

from .models import (
    RuntimeProfile, ExecutionMode, IsolationLevel, DesktopEnvironment,
    NetworkMode, TerminalCommandRisk
)
from .capability_registry import EnvironmentCapabilityRegistry
from .resource_inspector import ResourceInspector
from .runtime_adapters import (
    BaseRuntimeAdapter, LinuxRuntimeAdapter, ContainerRuntimeAdapter,
    VMRuntimeAdapter, DesktopRuntimeAdapter, RemoteLinuxRuntimeAdapter,
    HeadlessRuntimeAdapter
)

@dataclass
class EnvironmentSelectionDecision:
    selected_profile_id: str
    selected_adapter_id: str
    distribution: str
    version: str
    desktop_environment: DesktopEnvironment
    execution_mode: ExecutionMode
    isolation_level: IsolationLevel
    network_mode: NetworkMode
    reason: str
    score: float
    host_capacity: Dict[str, Any]
    fallback_profiles: List[str]
    timestamp: float = field(default_factory=time.time)

class UniversalRuntimeRouter:
    """
    Intelligent, policy-governed runtime router.
    AICU/Co-Worker requests a technical objective; the router selects the Linux execution world.
    """

    def __init__(self, registry: Optional[EnvironmentCapabilityRegistry] = None):
        self.registry = registry or EnvironmentCapabilityRegistry()
        self._adapters: Dict[str, BaseRuntimeAdapter] = {
            "adapter_linux_sandbox": LinuxRuntimeAdapter(),
            "adapter_container": ContainerRuntimeAdapter(),
            "adapter_micro_vm": VMRuntimeAdapter(),
            "adapter_desktop_gui": DesktopRuntimeAdapter(),
            "adapter_remote_linux": RemoteLinuxRuntimeAdapter(),
            "adapter_headless_linux": HeadlessRuntimeAdapter()
        }
        self._history: List[EnvironmentSelectionDecision] = []

    def get_adapter(self, adapter_id: str) -> Optional[BaseRuntimeAdapter]:
        return self._adapters.get(adapter_id)

    def select_environment(
        self,
        objective: str,
        required_capabilities: Optional[List[str]] = None,
        risk_level: TerminalCommandRisk = TerminalCommandRisk.READ_ONLY,
        isolation_override: Optional[IsolationLevel] = None,
        force_gui: bool = False,
        remote_preferred: bool = False,
        company_policy: Optional[Dict[str, Any]] = None
    ) -> EnvironmentSelectionDecision:
        """
        Dynamically selects the optimal Linux environment and runtime adapter.
        Evaluates real machine metrics, required capabilities, security boundaries, and desktop needs.
        """
        req_caps = set(required_capabilities or [])
        obj_lower = objective.lower()
        host_sys = ResourceInspector.inspect_system()
        is_constrained = host_sys["is_resource_constrained"]
        ram_total_mb = host_sys["ram"]["total_mb"]
        ram_avail_mb = host_sys["ram"]["available_mb"]

        # 1. Determine GUI vs Headless requirement
        gui_keywords = ["gui", "desktop", "browser", "display", "visual", "ui", "chromium", "firefox", "window", "screenshot"]
        needs_gui = force_gui or any(kw in obj_lower for kw in gui_keywords) or "gui_automation" in req_caps

        # 2. Determine Security Testing / Defensive Lab requirement
        sec_keywords = ["security test", "vulnerability", "audit security", "nmap", "packet capture", "forensic", "incident analysis", "malware analysis", "wireshark", "cve"]
        is_security_lab = any(kw in obj_lower for kw in sec_keywords) or "security_testing" in req_caps

        # 3. Determine Privacy-Sensitive / Amnesic requirement
        privacy_keywords = ["privacy", "anonymize", "amnesic", "zero-retention", "ephemeral ram", "tor", "tails"]
        is_privacy = any(kw in obj_lower for kw in privacy_keywords) or "zero_persistence" in req_caps

        # 4. Determine Build / Compilation requirement
        build_keywords = ["compile", "build", "cargo build", "rustc", "gcc", "gradle", "make", "docker build", "clang"]
        is_heavy_build = any(kw in obj_lower for kw in build_keywords) and ram_avail_mb > 4096

        # 5. Determine Production requirement
        is_production = risk_level == TerminalCommandRisk.PRODUCTION_MUTATION or "production" in obj_lower

        # Selection logic based on capabilities and policy (NOT distro branding)
        selected_profile_id = "profile_linux_dev"
        selected_adapter_id = "adapter_linux_sandbox"
        reason = "Standard Linux development environment selected."
        score = 80.0

        if is_production:
            selected_profile_id = "profile_production_verified"
            selected_adapter_id = "adapter_linux_sandbox"
            reason = "Production execution requires cryptographic audit and production-verified profile."
            score = 98.0
        elif is_privacy:
            selected_profile_id = "profile_privacy_isolated"
            selected_adapter_id = "adapter_micro_vm"
            reason = "Privacy-sensitive workload routed to ephemeral isolated VM."
            score = 95.0
        elif is_security_lab:
            selected_profile_id = "profile_security_lab"
            selected_adapter_id = "adapter_container"
            reason = "Authorized defensive security workload routed to isolated security lab container."
            score = 94.0
        elif needs_gui:
            selected_profile_id = "profile_desktop_gui"
            selected_adapter_id = "adapter_desktop_gui"
            reason = "GUI/desktop interaction detected; provisioned Linux Desktop with virtual display."
            score = 92.0
        elif is_constrained or ram_avail_mb < 1500:
            selected_profile_id = "profile_linux_lightweight"
            selected_adapter_id = "adapter_headless_linux"
            reason = f"Host is resource-constrained (Available RAM: {ram_avail_mb}MB); routed to ultra-lightweight Alpine profile."
            score = 90.0
        elif is_heavy_build:
            selected_profile_id = "profile_build_node"
            selected_adapter_id = "adapter_container"
            reason = "High-throughput build workload routed to build node container."
            score = 88.0
        else:
            selected_profile_id = "profile_linux_dev"
            selected_adapter_id = "adapter_linux_sandbox"
            reason = "Standard Linux development workload routed to sandboxed development environment."
            score = 85.0

        profile = self.registry.get_profile(selected_profile_id)
        if not profile:
            # Fallback to dev profile
            profile = self.registry.get_profile("profile_linux_dev")
            selected_profile_id = "profile_linux_dev"

        # Apply isolation override if specified by PolicyEngine
        isolation = isolation_override or profile.isolation_level

        decision = EnvironmentSelectionDecision(
            selected_profile_id=selected_profile_id,
            selected_adapter_id=selected_adapter_id,
            distribution=profile.distribution,
            version=profile.version,
            desktop_environment=profile.desktop_environment,
            execution_mode=profile.execution_mode,
            isolation_level=isolation,
            network_mode=profile.network_mode,
            reason=reason,
            score=score,
            host_capacity=host_sys,
            fallback_profiles=["profile_linux_dev", "profile_linux_lightweight"]
        )

        self._history.append(decision)
        return decision
