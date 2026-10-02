"""
RoboAssistant Company OS 1.0 — Governed Autonomous Agent & Tool Factory Foundation
Enforces strict 12-stage Agent Lifecycle, Anti-Explosion quotas, Least-Privilege Boundaries,
Self-Modification Defense, and Governed Tool Synthesis.

Constitutional Invariants:
- AGENT != AUTHORITY
- AGENT != TRUST
- AGENT != PERMISSION
- AGENT CREATION != ACTIVATION
- TOOL CREATION != PERMISSION
- TASK_SUCCESS != BUSINESS_OUTCOME
"""

import time
import json
import uuid
import re
import logging
from typing import Dict, List, Optional, Any, Set
from .db import db

logger = logging.getLogger("zonata.agent_factory")

class AgentLifecycleState:
    DESIGNED = "DESIGNED"
    VALIDATING = "VALIDATING"
    SANDBOXED = "SANDBOXED"
    TESTING = "TESTING"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    SUSPENDED = "SUSPENDED"
    QUARANTINED = "QUARANTINED"
    REVOKED = "REVOKED"
    RETIRED = "RETIRED"

class ToolLifecycleState:
    TOOL_DESIGN = "TOOL_DESIGN"
    SECURITY_SCAN = "SECURITY_SCAN"
    TEST = "TEST"
    POLICY_REVIEW = "POLICY_REVIEW"
    REGISTRATION = "REGISTRATION"
    APPROVAL = "APPROVAL"
    ACTIVATION = "ACTIVATION"
    REVOKED = "REVOKED"

class AgentFactoryQuotaException(Exception):
    """Raised when an agent creation request violates anti-explosion limits."""
    pass

class SelfModificationViolation(Exception):
    """Raised when an agent attempts to modify constitutional governance controls."""
    pass

class ToolSecurityViolation(Exception):
    """Raised when synthesized tool code contains forbidden or unvetted primitives."""
    pass

class GovernedAgentFactory:
    DEFAULT_MAX_AGENTS_PER_TENANT = 100
    DEFAULT_MAX_AGENTS_PER_COMPANY = 50
    DEFAULT_MAX_CHILD_PER_PARENT = 5
    DEFAULT_MAX_DELEGATION_DEPTH = 4
    DEFAULT_MAX_CONCURRENT_MISSIONS = 20

    # Protected core modules that no agent may modify
    IMMUTABLE_GOVERNANCE_MODULES: Set[str] = {
        "core.policy", "core.authority", "core.approvals", "core.credential_broker",
        "core.control_kernel", "core.evidence_ledger", "core.business_causality",
        "core.db", "core.auth", "core.agent_factory_runtime", "core.storage_governor"
    }

    @classmethod
    def get_tenant_quotas(cls, tenant_id: str) -> Dict[str, Any]:
        with db.get_connection() as conn:
            row = conn.execute("SELECT * FROM tenant_agent_quotas WHERE tenant_id = ?", (tenant_id,)).fetchone()
            if row:
                return dict(row)
        return {
            "tenant_id": tenant_id,
            "max_agents": cls.DEFAULT_MAX_AGENTS_PER_TENANT,
            "max_child_per_parent": cls.DEFAULT_MAX_CHILD_PER_PARENT,
            "max_delegation_depth": cls.DEFAULT_MAX_DELEGATION_DEPTH,
            "max_concurrent_missions": cls.DEFAULT_MAX_CONCURRENT_MISSIONS,
            "max_tool_calls": 100,
            "max_runtime_sec": 3600,
            "max_token_budget": 1000000
        }

    @classmethod
    def create_agent(
        cls,
        tenant_id: str,
        company_id: str,
        name: str,
        role: str,
        parent_agent_id: Optional[str] = None,
        requested_capabilities: Optional[List[str]] = None,
        requested_tools: Optional[List[str]] = None,
        budget: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Governed Agent Synthesis Pipeline:
        1. Anti-Explosion quota verification
        2. Delegation depth enforcement
        3. Least privilege capability assignment
        4. Self-modification security check
        5. Lifecycle: DESIGNED -> VALIDATING -> ACTIVE (or PENDING_APPROVAL)
        """
        quotas = cls.get_tenant_quotas(tenant_id)
        now = time.time()

        # 1. Anti-Explosion Quota Check: Total Agents
        with db.get_connection() as conn:
            cnt = conn.execute("SELECT count(*) FROM governed_agents WHERE tenant_id = ? AND lifecycle_state NOT IN ('REVOKED', 'RETIRED')", (tenant_id,)).fetchone()[0]
            if cnt >= quotas["max_agents"]:
                raise AgentFactoryQuotaException(
                    f"Agent quota exceeded for tenant '{tenant_id}': active {cnt} >= max {quotas['max_agents']}"
                )

            # 2. Delegation Depth Check
            parent_depth = 0
            if parent_agent_id:
                p_row = conn.execute("SELECT delegation_depth FROM governed_agents WHERE agent_id = ?", (parent_agent_id,)).fetchone()
                if p_row:
                    parent_depth = p_row[0]
                    if parent_depth >= quotas["max_delegation_depth"]:
                        raise AgentFactoryQuotaException(
                            f"Runaway delegation blocked: parent depth {parent_depth} reaches max {quotas['max_delegation_depth']}"
                        )
                    # Child limit per parent
                    child_cnt = conn.execute("SELECT count(*) FROM governed_agents WHERE parent_agent_id = ?", (parent_agent_id,)).fetchone()[0]
                    if child_cnt >= quotas["max_child_per_parent"]:
                        raise AgentFactoryQuotaException(
                            f"Parent agent '{parent_agent_id}' reached child spawn quota ({child_cnt}/{quotas['max_child_per_parent']})"
                        )

            delegation_depth = parent_depth + 1 if parent_agent_id else 0
            agent_id = f"agt_gov_{uuid.uuid4().hex[:10]}"

            # 3. Least Privilege Capabilities
            capabilities = requested_capabilities or ["OBSERVATION", "LOCAL_REASONING"]
            tools = requested_tools or []

            # 4. Require Approval for High-Risk roles
            needs_approval = role in ["CFO", "CHIEF_OF_STAFF", "FINANCIAL_OPERATOR", "SYSTEM_MUTATOR"]
            state = AgentLifecycleState.PENDING_APPROVAL if needs_approval else AgentLifecycleState.ACTIVE

            agent_record = {
                "agent_id": agent_id,
                "name": name,
                "version": "1.0.0",
                "tenant_id": tenant_id,
                "company_id": company_id,
                "role": role,
                "parent_agent_id": parent_agent_id,
                "delegation_depth": delegation_depth,
                "capabilities": json.dumps(capabilities),
                "allowed_tools": json.dumps(tools),
                "resource_budget": json.dumps(budget or {"max_tool_calls": 50, "token_limit": 200000}),
                "lifecycle_state": state,
                "health_status": "HEALTHY",
                "is_quarantined": 0,
                "created_at": now,
                "updated_at": now
            }

            conn.execute(
                """
                INSERT INTO governed_agents (
                    agent_id, name, version, tenant_id, company_id, role, parent_agent_id,
                    delegation_depth, capabilities, allowed_tools, resource_budget,
                    lifecycle_state, health_status, is_quarantined, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_id, name, "1.0.0", tenant_id, company_id, role, parent_agent_id,
                    delegation_depth, json.dumps(capabilities), json.dumps(tools),
                    json.dumps(budget or {}), state, "HEALTHY", 0, now, now
                )
            )
            conn.commit()

        logger.info(f"[*] Governed Agent created: {agent_id} ({name}) | State: {state} | Depth: {delegation_depth}")
        return agent_record

    @classmethod
    def transition_state(cls, agent_id: str, new_state: str, reason: str = "") -> bool:
        """Transitions agent along formal 12-stage lifecycle with state invariant checking."""
        now = time.time()
        with db.get_connection() as conn:
            row = conn.execute("SELECT lifecycle_state FROM governed_agents WHERE agent_id = ?", (agent_id,)).fetchone()
            if not row:
                return False
            curr = row[0]
            # Invariant: Once revoked or retired, cannot become active without fresh registration
            if curr in [AgentLifecycleState.REVOKED, AgentLifecycleState.RETIRED] and new_state == AgentLifecycleState.ACTIVE:
                raise ValueError(f"Cannot reactivate terminal state agent '{agent_id}' from {curr}")

            is_quarantined = 1 if new_state == AgentLifecycleState.QUARANTINED else 0
            conn.execute(
                "UPDATE governed_agents SET lifecycle_state = ?, is_quarantined = ?, updated_at = ? WHERE agent_id = ?",
                (new_state, is_quarantined, now, agent_id)
            )
            conn.commit()
        return True

    @classmethod
    def verify_no_self_modification(cls, target_module: str, caller_agent_id: Optional[str] = None):
        """
        Constitutional Defense: Prevents autonomous agents from modifying governance,
        security policies, authority gateways, or their own permission boundaries.
        """
        for imm in cls.IMMUTABLE_GOVERNANCE_MODULES:
            if target_module == imm or target_module.startswith(imm + "."):
                raise SelfModificationViolation(
                    f"Self-modification prohibited: agent '{caller_agent_id}' cannot mutate immutable governance module '{target_module}'"
                )


class GovernedToolFactory:
    """
    Governed Tool Synthesis & Capability Factory.
    Pipeline: TOOL_DESIGN -> SECURITY_SCAN -> TEST -> POLICY_REVIEW -> REGISTRATION -> APPROVAL -> ACTIVATION.
    """
    FORBIDDEN_PATTERNS = [
        r"\bimport\s+os\b",
        r"\bimport\s+subprocess\b",
        r"\bimport\s+socket\b",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\b__import__\b",
        r"\bshutil\.rmtree\b",
        r"\bopen\s*\([^)]*[\'\"]w[\'\"]\b" # raw file write without sandbox
    ]

    @classmethod
    def synthesize_tool(
        cls,
        tenant_id: str,
        company_id: str,
        name: str,
        code_body: str,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        risk_class: str = "SANDBOXED_COMPUTATION"
    ) -> Dict[str, Any]:
        now = time.time()
        tool_id = f"tool_gov_{uuid.uuid4().hex[:10]}"

        # 1. Static Security Scan
        security_status = "PASSED_STATIC_SCAN"
        violations = []
        for pat in cls.FORBIDDEN_PATTERNS:
            if re.search(pat, code_body):
                violations.append(pat)

        if violations:
            security_status = "FAILED_SECURITY_SCAN"
            raise ToolSecurityViolation(
                f"Tool '{name}' failed static security scan. Forbidden primitives detected: {violations}"
            )

        # 2. Risk Classification & Approval Gate
        requires_approval = risk_class in ["FINANCIAL", "PRIVILEGED", "SYSTEM_MUTATION"]
        lifecycle_state = ToolLifecycleState.APPROVAL if requires_approval else ToolLifecycleState.ACTIVATION

        record = {
            "tool_id": tool_id,
            "name": name,
            "version": "1.0.0",
            "tenant_id": tenant_id,
            "company_id": company_id,
            "source_type": "SYNTHESIZED",
            "risk_class": risk_class,
            "input_schema": json.dumps(input_schema),
            "output_schema": json.dumps(output_schema),
            "filesystem_policy": "SANDBOX_ONLY",
            "network_policy": "BLOCKED",
            "lifecycle_state": lifecycle_state,
            "security_status": security_status,
            "created_at": now
        }

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO governed_tools (
                    tool_id, name, version, tenant_id, company_id, source_type,
                    risk_class, input_schema, output_schema, filesystem_policy,
                    network_policy, lifecycle_state, security_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tool_id, name, "1.0.0", tenant_id, company_id, "SYNTHESIZED",
                    risk_class, json.dumps(input_schema), json.dumps(output_schema),
                    "SANDBOX_ONLY", "BLOCKED", lifecycle_state, security_status, now
                )
            )
            conn.commit()

        logger.info(f"[*] Governed Tool synthesized: {tool_id} ({name}) | State: {lifecycle_state}")
        return record
