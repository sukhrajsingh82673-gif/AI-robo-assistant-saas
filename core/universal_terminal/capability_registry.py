"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Environment Capability Registry
Maintains catalog of validated Linux runtime profiles, distributions, architectures,
desktop environments, tools, security classifications, and system capabilities.
"""

from typing import Dict, List, Optional, Any, Set
import copy
import time
from .models import (
    RuntimeProfile, ExecutionMode, IsolationLevel, DesktopEnvironment, NetworkMode
)

class EnvironmentCapabilityRegistry:
    """
    Catalog of validated Linux environments and execution profiles.
    Subordinate to ZONATA Sovereign Authority and AICU strategic direction.
    """

    def __init__(self):
        self._profiles: Dict[str, RuntimeProfile] = {}
        self._tools_catalog: Dict[str, Dict[str, Any]] = {}
        self._seed_standard_profiles()
        self._seed_tools_catalog()

    def _seed_standard_profiles(self):
        # 1. Standard Linux Development Profile (Debian/Ubuntu)
        self.register_profile(RuntimeProfile(
            profile_id="profile_linux_dev",
            distribution="debian",
            version="12-bookworm",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.LOCAL_SANDBOX,
            isolation_level=IsolationLevel.LEVEL_1_SANDBOX,
            network_mode=NetworkMode.PACKAGE_REPOSITORIES_ONLY,
            min_ram_mb=1024,
            recommended_ram_mb=4096,
            min_disk_mb=4096,
            preinstalled_tools=["bash", "git", "python3", "gcc", "make", "curl", "tar"],
            capabilities=[
                "software_development", "compilation", "git_operations",
                "testing", "dependency_management", "script_execution"
            ],
            metadata={"description": "Standard governed Linux developer sandbox"}
        ))

        # 2. Lightweight Linux Environment (Alpine)
        self.register_profile(RuntimeProfile(
            profile_id="profile_linux_lightweight",
            distribution="alpine",
            version="3.19",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.LOCAL_SANDBOX,
            isolation_level=IsolationLevel.LEVEL_1_SANDBOX,
            network_mode=NetworkMode.OFFLINE,
            min_ram_mb=256,
            recommended_ram_mb=512,
            min_disk_mb=512,
            preinstalled_tools=["sh", "busybox", "python3", "apk"],
            capabilities=[
                "lightweight_execution", "resource_constrained", "fast_startup",
                "basic_scripting", "text_processing"
            ],
            metadata={"description": "Ultra-lightweight Linux environment for resource-constrained hosts (<2GB RAM)"}
        ))

        # 3. Authorized Defensive Security Lab Profile (Kali / Forensics)
        self.register_profile(RuntimeProfile(
            profile_id="profile_security_lab",
            distribution="kali",
            version="2024.1",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.SECURITY_LAB,
            isolation_level=IsolationLevel.LEVEL_2_CONTAINER,
            network_mode=NetworkMode.RESTRICTED_NETWORK,
            min_ram_mb=2048,
            recommended_ram_mb=8192,
            min_disk_mb=8192,
            preinstalled_tools=["nmap", "tshark", "tcpdump", "openssl", "volatility", "binwalk"],
            capabilities=[
                "security_testing", "vulnerability_assessment", "incident_investigation",
                "forensic_analysis", "network_diagnostics", "defensive_hardening"
            ],
            trust_level="VERIFIED",
            metadata={"description": "Governed defensive cybersecurity and forensic analysis runtime"}
        ))

        # 4. Privacy-Oriented Ephemeral Profile (Tails / Amnesic Isolation)
        self.register_profile(RuntimeProfile(
            profile_id="profile_privacy_isolated",
            distribution="tails",
            version="6.0",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.DISPOSABLE_RUNTIME,
            isolation_level=IsolationLevel.LEVEL_3_VM,
            network_mode=NetworkMode.RESTRICTED_NETWORK,
            min_ram_mb=2048,
            recommended_ram_mb=4096,
            min_disk_mb=2048,
            is_ephemeral=True,
            preinstalled_tools=["tor", "gnupg", "shred", "curl"],
            capabilities=[
                "privacy_sensitive", "zero_persistence", "ephemeral_isolation", "crypto_verification"
            ],
            metadata={"description": "Amnesic zero-retention privacy runtime (ephemeral RAM-only state)"}
        ))

        # 5. Linux Desktop / GUI Execution Profile (XFCE / Virtual Display)
        self.register_profile(RuntimeProfile(
            profile_id="profile_desktop_gui",
            distribution="debian",
            version="12-desktop",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.VIRTUAL_DISPLAY,
            execution_mode=ExecutionMode.LOCAL_CONTAINER,
            isolation_level=IsolationLevel.LEVEL_2_CONTAINER,
            network_mode=NetworkMode.ALLOWLIST_DOMAINS,
            min_ram_mb=2048,
            recommended_ram_mb=8192,
            min_disk_mb=10240,
            gpu_required=False,
            preinstalled_tools=["xvfb", "xfce4", "xdotool", "scrot", "chromium", "firefox"],
            capabilities=[
                "gui_automation", "desktop_applications", "browser_testing",
                "visual_inspection", "virtual_display"
            ],
            metadata={"description": "Dynamic Linux Desktop environment with virtual display buffer"}
        ))

        # 6. Dedicated High-Performance Build Node Profile (Fedora / Buildroot)
        self.register_profile(RuntimeProfile(
            profile_id="profile_build_node",
            distribution="fedora",
            version="39",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.DEDICATED_BUILD_NODE,
            isolation_level=IsolationLevel.LEVEL_2_CONTAINER,
            network_mode=NetworkMode.PACKAGE_REPOSITORIES_ONLY,
            min_ram_mb=4096,
            recommended_ram_mb=16384,
            min_disk_mb=20480,
            preinstalled_tools=["gcc", "clang", "cmake", "rustc", "cargo", "golang", "gradle"],
            capabilities=[
                "high_concurrency_build", "docker_compilation", "rust_build", "go_build", "java_build"
            ],
            metadata={"description": "High-throughput build & compilation node with parallel toolchains"}
        ))

        # 7. Controlled Host Execution Profile
        self.register_profile(RuntimeProfile(
            profile_id="profile_host_controlled",
            distribution="host_native",
            version="kernel_native",
            architecture="native",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.AUTHORIZED_HOST_EXECUTION,
            isolation_level=IsolationLevel.LEVEL_4_HOST,
            network_mode=NetworkMode.INTERNAL_NETWORK,
            min_ram_mb=1024,
            recommended_ram_mb=2048,
            min_disk_mb=1024,
            is_ephemeral=False,
            capabilities=["host_administration", "direct_hardware_access", "service_management"],
            metadata={"description": "Controlled host environment requiring explicit authority lease"}
        ))

        # 8. Enterprise Production Execution Profile
        self.register_profile(RuntimeProfile(
            profile_id="profile_production_verified",
            distribution="debian",
            version="12-hardened",
            architecture="x86_64",
            desktop_environment=DesktopEnvironment.HEADLESS,
            execution_mode=ExecutionMode.PRODUCTION_EXECUTION,
            isolation_level=IsolationLevel.LEVEL_5_PRODUCTION,
            network_mode=NetworkMode.PRODUCTION_NETWORK,
            min_ram_mb=4096,
            recommended_ram_mb=8192,
            min_disk_mb=10240,
            is_ephemeral=False,
            capabilities=["production_deployment", "high_availability", "cryptographic_audit"],
            metadata={"description": "Hardened production workload runtime with cryptographic audit"}
        ))

    def _seed_tools_catalog(self):
        """Seed tools across package ecosystems."""
        tools = [
            {"tool_id": "git", "category": "vcs", "license": "GPL-2.0", "versions": ["2.43.0"], "trust": "VERIFIED"},
            {"tool_id": "python3", "category": "interpreter", "license": "PSF", "versions": ["3.11", "3.12", "3.14"], "trust": "VERIFIED"},
            {"tool_id": "pytest", "category": "testing", "license": "MIT", "versions": ["8.1.1"], "trust": "VERIFIED"},
            {"tool_id": "node", "category": "runtime", "license": "MIT", "versions": ["20.11.1"], "trust": "VERIFIED"},
            {"tool_id": "npm", "category": "package_manager", "license": "Artistic-2.0", "versions": ["10.2.4"], "trust": "VERIFIED"},
            {"tool_id": "cargo", "category": "build", "license": "MIT/Apache-2.0", "versions": ["1.76.0"], "trust": "VERIFIED"},
            {"tool_id": "rustc", "category": "compiler", "license": "MIT/Apache-2.0", "versions": ["1.76.0"], "trust": "VERIFIED"},
            {"tool_id": "go", "category": "compiler", "license": "BSD-3-Clause", "versions": ["1.22.0"], "trust": "VERIFIED"},
            {"tool_id": "docker", "category": "container", "license": "Apache-2.0", "versions": ["25.0.3"], "trust": "VERIFIED"},
            {"tool_id": "nmap", "category": "security", "license": "NPSL", "versions": ["7.94"], "trust": "VERIFIED"},
            {"tool_id": "xvfb", "category": "desktop", "license": "MIT", "versions": ["21.1.8"], "trust": "VERIFIED"},
            {"tool_id": "curl", "category": "network", "license": "curl", "versions": ["8.5.0"], "trust": "VERIFIED"},
            {"tool_id": "tar", "category": "utility", "license": "GPL-3.0", "versions": ["1.35"], "trust": "VERIFIED"},
            {"tool_id": "make", "category": "build", "license": "GPL-3.0", "versions": ["4.4.1"], "trust": "VERIFIED"},
            {"tool_id": "gcc", "category": "compiler", "license": "GPL-3.0", "versions": ["13.2.0"], "trust": "VERIFIED"}
        ]
        for t in tools:
            self._tools_catalog[t["tool_id"]] = t

    def register_profile(self, profile: RuntimeProfile):
        self._profiles[profile.profile_id] = profile

    def get_profile(self, profile_id: str) -> Optional[RuntimeProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[RuntimeProfile]:
        return list(self._profiles.values())

    def query_profiles_for_capability(self, capability: str) -> List[RuntimeProfile]:
        return [
            p for p in self._profiles.values()
            if capability in p.capabilities or capability in p.preinstalled_tools
        ]

    def register_tool(self, tool_id: str, metadata: Dict[str, Any]):
        self._tools_catalog[tool_id] = metadata

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        return self._tools_catalog.get(tool_id)

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools_catalog.values())

    def is_tool_available(self, tool_id: str, profile_id: str = "profile_linux_dev") -> bool:
        prof = self.get_profile(profile_id)
        if not prof:
            return False
        return tool_id in prof.preinstalled_tools or tool_id in self._tools_catalog

    def is_installed(self, tool_id: str) -> bool:
        """Checks if a tool is active, registered, and not quarantined."""
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        return tool.get("trust") not in ["QUARANTINED", "REVOKED"]
