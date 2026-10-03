"""
ZONATA Universal AI Co-worker Fabric — Capability Provider Adapters
"""

from .openadapt_provider import OpenAdaptProvider
from .visual_cua_provider import VisualCUAProvider
from .desktop_native_providers import (
    WindowsDesktopProvider, MacOSDesktopProvider, LinuxDesktopProvider
)
from .computer_use_mcp_provider import ComputerUseMCPProvider
from .playwright_provider import PlaywrightProvider
from .rpa_providers import RobocorpProvider, OpenRPAProvider
from .api_mcp_provider import APIMCPProvider

__all__ = [
    "OpenAdaptProvider",
    "VisualCUAProvider",
    "WindowsDesktopProvider",
    "MacOSDesktopProvider",
    "LinuxDesktopProvider",
    "ComputerUseMCPProvider",
    "PlaywrightProvider",
    "RobocorpProvider",
    "OpenRPAProvider",
    "APIMCPProvider"
]
