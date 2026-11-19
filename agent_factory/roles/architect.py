"""ZONATA Agent Factory - Architect Role.

Translates an approved Agent Requirement Specification (ARS) into an initial
candidate agent architecture and capability specification.
"""

from typing import Any, Dict, List, Optional
from agent_factory.templates.loader import TemplateLoader


class AgentArchitect:
    def __init__(self, template_loader: Optional[TemplateLoader] = None):
        self.template_loader = template_loader or TemplateLoader()

    def design(self, ars: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Produce an architecture plan and candidate spec skeleton from an ARS."""
        category = ars.get("category", "custom")
        risk_tier = ars.get("risk_tier_inferred", "R1")
        tpl_ref = ars.get("suggested_template_ref")

        template = None
        if tpl_ref:
            template = self.template_loader.resolve(tpl_ref)

        agent_slug = f"{category}-agent"
        if template:
            agent_slug = f"{template.name}"

        # Architecture design document
        design_doc = {
            "agent_slug": agent_slug,
            "category": category,
            "risk_tier": risk_tier,
            "template_used": tpl_ref,
            "workflow_topology": "sequential",
            "required_capabilities": ars.get("capabilities_needed", []),
            "constraints": ars.get("constraints", {}),
            "state_schema": {
                "input": {"type": "object"},
                "output": {"type": "object"}
            }
        }
        return design_doc
