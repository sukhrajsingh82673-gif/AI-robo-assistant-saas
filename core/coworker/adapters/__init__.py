"""
ZONATA Autonomous Coworker 2.0 — Computer-Use Adapter Registry
Exports Hermes, OpenCloud, and OpenDots computer-use adapters.
"""

from .hermes_adapter import HermesComputerUseAdapter
from .opencloud_adapter import OpenCloudAdapter
from .opendots_adapter import OpenDotsAdapter

__all__ = [
    "HermesComputerUseAdapter",
    "OpenCloudAdapter",
    "OpenDotsAdapter",
]
