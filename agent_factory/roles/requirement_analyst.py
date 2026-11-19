"""ZONATA Agent Factory - Requirement Analyst Role.

Translates natural language manufacturing requests into structured
Agent Requirement Specifications (ARS) stored in af_requirement_spec.
Operates with strict input sanitisation, schema validation, and deterministic output.
"""

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional
from agent_factory.templates.loader import TemplateLoader


class RequirementAnalyst:
    """Analyzes user request requirements and drafts an Agent Requirement Specification (ARS)."""

    def __init__(self, template_loader: Optional[TemplateLoader] = None):
        self.template_loader = template_loader or TemplateLoader()

    def analyze(
        self,
        request_id: str,
        natural_language: str,
        template_ref: Optional[str] = None,
        mode: str = "single"
    ) -> Dict[str, Any]:
        """Analyze natural language request and produce a structured ARS draft."""
        nl_lower = natural_language.lower()

        # Inferred category & capabilities
        inferred_category = "custom"
        suggested_template = template_ref
        capabilities_needed = ["reasoning.plan", "tool.use"]
        risk_tier = "R1"
        clarifications = []

        if any(w in nl_lower for w in ["c-suite", "executive", "ceo", "strategy", "board"]):
            inferred_category = "c_suite"
            if not suggested_template:
                suggested_template = "c-suite-advisory@1.0.0"
            capabilities_needed.extend(["knowledge.retrieve", "document.generate"])
            risk_tier = "R1"
        elif any(w in nl_lower for w in ["finance", "accounting", "ledger", "reconciliation", "tax"]):
            inferred_category = "finance"
            if not suggested_template:
                suggested_template = "finance-reconciliation@1.0.0"
            capabilities_needed.extend(["database.query_readonly"])
            risk_tier = "R1"
        elif any(w in nl_lower for w in ["marketing", "campaign", "newsletter", "copy", "seo"]):
            inferred_category = "marketing"
            if not suggested_template:
                suggested_template = "marketing-campaign@1.0.0"
            capabilities_needed.extend(["document.generate"])
            risk_tier = "R1"
        elif any(w in nl_lower for w in ["code", "software", "pull request", "pr review", "refactor"]):
            inferred_category = "software_engineering"
            if not suggested_template:
                suggested_template = "software-engineering-review@1.0.0"
            capabilities_needed.extend(["code.analyze"])
            risk_tier = "R2"
        elif any(w in nl_lower for w in ["devops", "incident", "logs", "alert", "outage"]):
            inferred_category = "devops"
            if not suggested_template:
                suggested_template = "devops-incident-triage@1.0.0"
            risk_tier = "R2"
        elif any(w in nl_lower for w in ["security", "cve", "vulnerability", "sbom", "audit"]):
            inferred_category = "defensive_cybersecurity"
            if not suggested_template:
                suggested_template = "defensive-cybersecurity-audit@1.0.0"
            risk_tier = "R2"

        # Check for ambiguity requiring clarification
        if len(natural_language.strip()) < 30:
            clarifications.append("Request is brief; specify target systems and expected deliverables.")

        if "database" in nl_lower and "write" in nl_lower:
            clarifications.append("Database write access requested. Clarify required tables and audit mechanisms.")
            risk_tier = "R2"

        constraints = {
            "max_steps": 30 if risk_tier in ("R0", "R1") else 50,
            "timeout_seconds": 600 if risk_tier in ("R0", "R1") else 900,
            "max_cost_usd_per_task": 1.0,
            "network_restricted": True
        }

        # Validate template reference if provided
        if suggested_template:
            tpl = self.template_loader.resolve(suggested_template)
            if tpl:
                risk_tier = tpl.default_risk_tier

        ars_id = str(uuid.uuid4())
        ars = {
            "id": ars_id,
            "request_id": request_id,
            "version": 1,
            "category": inferred_category,
            "parsed_goal": natural_language[:500],
            "capabilities_needed": sorted(list(set(capabilities_needed))),
            "constraints": constraints,
            "suggested_template_ref": suggested_template,
            "risk_tier_inferred": risk_tier,
            "clarifications_needed": clarifications,
            "status": "APPROVED" if not clarifications else "CLARIFYING",
            "spec_hash": hashlib.sha256(natural_language.encode("utf-8")).hexdigest()
        }
        return ars
