"""ZONATA Agent Factory - Quarantined OSS Agent Importer.

Implements Section 6.11 (Import lane & flag-gated sandboxes):
- Untrusted open-source agents are never executed on the host.
- In T0 environments (e.g. Termux/ARM64 without microVMs/Docker), requests
  requiring T1/T2 sandboxes fail-closed with AF-SANDBOX-UNAVAILABLE.
- Converts declarative manifests into zonata.agent/v1 specifications.
"""

from __future__ import annotations
import os
import re
from typing import Any, Dict, List, Optional


class SandboxUnavailableError(Exception):
    """Raised when the requested sandbox isolation tier (T1/T2) is unavailable on this host."""
    pass


def get_available_sandbox_tiers() -> List[str]:
    """Return available sandbox tiers from environment."""
    tiers_env = os.environ.get("AF_SANDBOX_TIERS", "T0")
    return [t.strip().upper() for t in tiers_env.split(",") if t.strip()]


class QuarantinedAgentImporter:
    def __init__(self, allowed_tiers: Optional[List[str]] = None):
        self.allowed_tiers = allowed_tiers or get_available_sandbox_tiers()

    def import_agent(
        self,
        source_url: str,
        manifest_data: Optional[Dict[str, Any]] = None,
        tier_requested: str = "T1"
    ) -> Dict[str, Any]:
        """
        Import an open-source agent package into a quarantined specification.
        Enforces flag-gated sandbox availability.
        """
        # 1. Honest sandbox tier check
        if tier_requested not in self.allowed_tiers:
            raise SandboxUnavailableError(
                f"AF-SANDBOX-UNAVAILABLE: Sandbox tier '{tier_requested}' is not provisioned on this host. "
                f"Available tiers: {self.allowed_tiers}."
            )

        manifest_data = manifest_data or {}
        raw_name = manifest_data.get("name", "imported-agent")
        clean_name = re.sub(r"[^a-z0-9-]", "-", raw_name.lower())[:60]
        if len(clean_name) < 3:
            clean_name = f"{clean_name}-imp"

        # 2. Pure declarative extraction (never executes host code)
        spec = {
            "apiVersion": "zonata.agent/v1",
            "kind": "Agent",
            "metadata": {
                "name": clean_name,
                "display_name": f"Imported: {raw_name}",
                "version": "1.0.0",
                "category": "custom",
                "risk_tier": "R2",
                "labels": {
                    "source_url": source_url,
                    "quarantined": "true"
                }
            },
            "identity": {
                "principal_kind": "agent",
                "tenant_bound": True,
                "may_use_employees": False
            },
            "role": {
                "title": f"Quarantined {clean_name}",
                "mission": manifest_data.get("description", "Imported open-source capability"),
                "responsibilities": ["Perform imported domain task within sandbox boundary"],
                "out_of_scope": ["Host filesystem access", "Unrestricted network egress", "Employee command"],
                "success_criteria": ["All execution contained in isolated sandbox"],
                "instructions": "Execute exclusively through governed sandboxed tools."
            },
            "model": {
                "requirements": {
                    "complexity": "medium",
                    "privacy": "internal"
                }
            },
            "capabilities": {
                "requested": [{"key": "tool.use"}]
            },
            "permissions": {
                "requested": {
                    "tools": [],
                    "network": {"external": False, "allowed_hosts": []},
                    "writes": False
                }
            },
            "workflow": {
                "type": "sequential",
                "steps": [
                    {"id": "step_validate", "kind": "validate"},
                    {"id": "step_run", "kind": "tool", "tool": "quarantine.execute_sandboxed"}
                ]
            },
            "memory": {
                "conversation": {"enabled": False},
                "pii_policy": "redact"
            },
            "limits": {
                "max_steps": 20,
                "timeout_seconds": 300,
                "max_cost_usd_per_task": 0.5
            },
            "io": {
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"}
            },
            "observability": {
                "trace": True,
                "capture_content": "redacted"
            },
            "tests": {
                "author_cases": [
                    {"id": "quarantine_smoke", "input": {"ping": "pong"}, "expect": {"ok": True}}
                ],
                "dataset_refs": ["quarantine-eval@1.0.0"]
            }
        }
        return spec
