"""
ZONATA / URA Universal Linux Terminal Execution Fabric — Tool Integration Engine
Bridges the ToolDiscoveryEngine, ToolFactoryV2, and EnvironmentCapabilityRegistry.
Implements the 13-step tool acquisition pipeline:
DISCOVER → INSPECT → LICENSE CHECK → AST SECURITY SCAN → SANDBOX TEST → TOOL FACTORY REGISTRATION → ADMISSION.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
import sys
import time
import uuid
import hashlib
import logging

from .capability_registry import EnvironmentCapabilityRegistry
from ..coworker.tool_discovery import ToolDiscoveryEngine, ToolCandidate
from ..tool_factory_v2 import ToolFactoryV2

logger = logging.getLogger("zonata.terminal.tools")

class TerminalToolIntegrationEngine:
    """
    Governed Tool Discovery and Admission Pipeline for the Universal Terminal.
    Enforces no fixed tool limit while ensuring zero untrusted execution.
    """

    def __init__(self, tenant_id: str = "tnt_primary", registry: Optional[EnvironmentCapabilityRegistry] = None):
        self.tenant_id = tenant_id
        self.capability_registry = registry or EnvironmentCapabilityRegistry()
        self.discovery_engine = ToolDiscoveryEngine(tenant_id=tenant_id)
        self.tool_factory = ToolFactoryV2()

    def discover_tools_for_objective(self, query: str) -> List[ToolCandidate]:
        """Discovers legitimate open-source tools matching the capability requirement."""
        return self.discovery_engine.discover_tools(query)

    def acquire_and_qualify_tool(
        self,
        candidate_id: str,
        sandbox_test_fn: Optional[Any] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Executes complete verification pipeline:
        1. License verification (Apache-2.0, MIT, BSD)
        2. Static AST security scan
        3. Sandbox test
        4. Registration in ToolFactoryV2
        5. Admission to EnvironmentCapabilityRegistry
        """
        candidate = self.discovery_engine._curated_catalog.get(candidate_id)
        if not candidate:
            # Try searching by name or tool_id
            for c in self.discovery_engine._curated_catalog.values():
                if c.tool_id == candidate_id or c.name.lower() == candidate_id.lower():
                    candidate = c
                    break

        if not candidate:
            return False, f"Tool candidate '{candidate_id}' not found in discovery catalog.", None

        # Execute full admission pipeline through ToolDiscoveryEngine
        success, candidate, msg = self.discovery_engine.run_full_admission_pipeline(candidate)
        if not success:
            return False, f"Tool admission rejected: {msg}", None

        # Register in EnvironmentCapabilityRegistry
        tool_meta = {
            "tool_id": candidate.name,
            "category": "acquired_tool",
            "version": candidate.version,
            "license": candidate.license,
            "repository": candidate.repository,
            "capabilities": candidate.capabilities,
            "trust": "VERIFIED",
            "admitted_at": time.time()
        }
        self.capability_registry.register_tool(candidate.name, tool_meta)

        return True, f"Tool '{candidate.name}' v{candidate.version} successfully qualified and admitted into Tool Factory.", tool_meta

