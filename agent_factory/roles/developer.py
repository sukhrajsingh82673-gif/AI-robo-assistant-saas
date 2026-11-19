"""ZONATA Agent Factory - Developer Role.

Takes architecture design + template + ARS and produces a fully rendered,
declarative zonata.agent/v1 specification ready for validation.
"""

from typing import Any, Dict, List, Optional
from agent_factory.templates.loader import TemplateLoader


class AgentDeveloper:
    def __init__(self, template_loader: Optional[TemplateLoader] = None):
        self.template_loader = template_loader or TemplateLoader()

    def build_spec(
        self,
        ars: Dict[str, Any],
        design: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Produce a complete candidate zonata.agent/v1 document."""
        tpl_ref = design.get("template_used")
        template = self.template_loader.resolve(tpl_ref) if tpl_ref else None

        params = params or {}
        agent_name = params.get("name", design.get("agent_slug", "custom-agent"))
        # Ensure clean slug matching regex ^[a-z0-9][a-z0-9-]{2,62}$
        agent_name = agent_name.lower().replace("_", "-")
        if len(agent_name) < 3:
            agent_name = f"{agent_name}-agent"

        if template:
            base = template.instantiate({
                "name": agent_name,
                "display_name": params.get("display_name", agent_name.replace("-", " ").title()),
                "role_title": params.get("role_title", ars.get("parsed_goal", "")[:100]),
                "mission": ars.get("parsed_goal", "")[:900]
            })
            return base

        # Fallback to scratch synthesis if no template was matched
        return {
            "apiVersion": "zonata.agent/v1",
            "kind": "Agent",
            "metadata": {
                "name": agent_name,
                "display_name": agent_name.replace("-", " ").title(),
                "version": "1.0.0",
                "category": design.get("category", "custom"),
                "risk_tier": design.get("risk_tier", "R1")
            },
            "identity": {
                "principal_kind": "agent",
                "tenant_bound": True,
                "may_use_employees": False
            },
            "role": {
                "title": f"{agent_name.replace('-', ' ').title()} Specialist",
                "mission": ars.get("parsed_goal", "Execute designated workflows under corporate governance"),
                "responsibilities": ["Perform designated operations", "Report outcomes with evidence"],
                "out_of_scope": ["Direct production DB writes", "Direct commanding of employees"],
                "success_criteria": ["All execution steps pass validation"],
                "instructions": "Execute assigned duties with strict audit trail attribution."
            },
            "model": {
                "requirements": {
                    "complexity": "medium",
                    "privacy": "internal"
                }
            },
            "capabilities": {
                "requested": [{"key": cap} for cap in design.get("required_capabilities", ["tool.use"])]
            },
            "permissions": {
                "requested": {
                    "tools": [],
                    "network": {"external": False, "allowed_hosts": []},
                    "writes": False
                }
            },
            "workflow": {
                "type": design.get("workflow_topology", "sequential"),
                "steps": [
                    {"id": "step_validate", "kind": "validate"},
                    {"id": "step_process", "kind": "model"},
                    {"id": "step_report", "kind": "report"}
                ]
            },
            "memory": {
                "conversation": {"enabled": True, "max_messages": 30},
                "pii_policy": "redact"
            },
            "limits": {
                "max_steps": 30,
                "timeout_seconds": 600,
                "max_cost_usd_per_task": 1.0
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
                    {"id": "author_smoke", "input": {"test": True}, "expect": {"status": "ok"}, "mandatory": True}
                ],
                "dataset_refs": [f"{agent_name}-dataset@1.0.0"]
            }
        }
