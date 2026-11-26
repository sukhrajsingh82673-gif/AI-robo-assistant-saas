"""
Marketplace Capability Sandbox Runtime (Rule 81).
Treats all third-party code as hostile. Enforces capability constraints at call time.
"""

from typing import Dict, Any, List, Optional, Set


class SandboxViolationError(PermissionError):
    """Raised when third-party code attempts ungranted capabilities or network access."""
    pass


class MarketplaceSandbox:
    """
    Simulates gVisor / microVM sandboxed execution environment.
    Verifies capability authorization and network egress allowlisting.
    """

    def __init__(self, tenant_id: str, package_id: str, granted_capabilities: List[str]):
        self.tenant_id = tenant_id
        self.package_id = package_id
        self.granted_capabilities: Set[str] = set(granted_capabilities)
        self.is_revoked: bool = False

    def revoke(self):
        self.is_revoked = True

    def execute_operation(self, capability_needed: str, target_resource: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes capability-checked operation on behalf of third-party package.
        """
        if self.is_revoked:
            raise SandboxViolationError(f"Execution denied: Package '{self.package_id}' has been revoked.")

        # Check capability and network egress constraints
        if capability_needed == "network:egress":
            egress_cap = f"network:egress:{target_resource}"
            if (
                egress_cap not in self.granted_capabilities
                and "network:egress:*" not in self.granted_capabilities
                and "network:egress" not in self.granted_capabilities
            ):
                raise SandboxViolationError(
                    f"Rule 81 Violation: Egress to domain '{target_resource}' is prohibited. Not in consented capabilities."
                )
        else:
            has_base_cap = capability_needed in self.granted_capabilities
            has_scoped_cap = bool(target_resource and f"{capability_needed}:{target_resource}" in self.granted_capabilities)
            if not (has_base_cap or has_scoped_cap):
                raise SandboxViolationError(
                    f"Rule 81 Violation: Package '{self.package_id}' lacks required capability '{capability_needed}'."
                )

        return {
            "status": "SUCCESS",
            "capability": capability_needed,
            "target": target_resource,
            "tenant_id": self.tenant_id,
        }
