"""
Standard Department Pack Schema (zonata.department-pack/v1)
===========================================================
Defines the schema and validation for department packs.
Each department pack declares:
- Domain metadata, schema version, owner
- Required capabilities & Ports
- Workflows (Temporal workflows registered by this department)
- Policies & guardrails (including Rule 62 Human Gate requirements)
- Metric definitions (Cube semantic models)
- Replay fixtures and connector bindings
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class DepartmentPackMetadata(BaseModel):
    name: str = Field(..., description="Canonical department name, e.g. finance, hr, sales")
    display_name: str
    version: str = Field(..., regex=r"^\d+\.\d+\.\d+$")
    description: str
    owner_team: str
    schema_version: str = Field("zonata.department-pack/v1")


class DepartmentCapability(BaseModel):
    capability_id: str
    description: str
    required_ports: List[str] = Field(default_factory=list)
    risk_level: str = Field("low", description="'low', 'medium', 'high', or 'critical'")
    reserved_human_decision: bool = Field(False, description="Whether human gateway approval is mandatory")


class DepartmentPolicyRule(BaseModel):
    rule_id: str
    rule_name: str
    description: str
    rule_type: str = Field(..., description="'gateway_gate', 'budget_limit', 'counterfactual_fairness', 'sanctions'")
    enforcement: str = Field("blocking", description="'blocking', 'audit_only', or 'quarantine'")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class DepartmentPackManifest(BaseModel):
    manifest_version: str = Field("zonata.department-pack/v1")
    metadata: DepartmentPackMetadata
    capabilities: List[DepartmentCapability] = Field(default_factory=list)
    policies: List[DepartmentPolicyRule] = Field(default_factory=list)
    workflows: List[str] = Field(default_factory=list, description="Registered Temporal workflow identifiers")
    metrics: List[str] = Field(default_factory=list, description="Exported KPI metric identifiers")

    @validator("manifest_version")
    def validate_manifest_version(cls, v):
        if v != "zonata.department-pack/v1":
            raise ValueError("Manifest version must be 'zonata.department-pack/v1'")
        return v
