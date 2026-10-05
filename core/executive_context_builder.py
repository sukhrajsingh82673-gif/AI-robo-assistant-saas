"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Executive Context Builder & Governed Prompt Architecture

Implements Section 6, Section 7, Section 29, Section 30 of the Gemma 4 Master Specification:
- Assembles dynamic, least-privilege executive context from live state without dumping the entire DB
- Modular prompt composition:
    1. Constitutional Context (Invariants, Sovereignty, Kill switches)
    2. Role Context (AI CEO executive boundaries, Capability != Authority)
    3. Organizational Context (Tenant, Company, Departments, Workload)
    4. Mission Context (Active strategic missions and dependencies)
    5. Tool Context (Available governed capabilities)
    6. Memory Context (Relevant organizational facts & working memory)
    7. Conversation Context (Recent dialogue window)
    8. Policy Context (Financial ceilings, Risk limits, Escalation rules)
- Strict Prompt Injection Defense & Data Isolation (Instructions vs Untrusted Data)
- Versioning & Cryptographic Digest:
    prompt_version, model_version, context_hash, tool_manifest_hash, policy_version
"""

import time
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.ceo import PromptInjectionDefense

logger = logging.getLogger("zonata.executive.context")

@dataclass
class AssembledExecutiveContext:
    tenant_id: str
    company_id: str
    prompt_version: str
    model_version: str
    policy_version: str
    system_instruction: str
    composed_prompt: str
    untrusted_data_payload: Dict[str, Any]
    context_hash: str
    tool_manifest_hash: str
    active_missions_count: int
    pending_approvals_count: int
    budget_ceiling_inr: float
    least_privilege_scope: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutiveContextBuilder:
    """
    Constructs governed, bounded, auditable context for the Gemma 4 cognitive executive layer.
    """

    PROMPT_VERSION = "2.4.0-GEMMA4-GOVERNED"
    POLICY_VERSION = "8.2.0-SOVEREIGN"

    @classmethod
    def sanitize_untrusted_input(cls, user_input: str) -> tuple[str, bool]:
        """
        Scans and sanitizes untrusted input, detecting injection patterns.
        """
        match = PromptInjectionDefense.scan_for_injection(user_input)
        if match:
            logger.warning(f"Prompt injection pattern detected: {match}")
            return f"[SECURITY_ISOLATED_DATA: Input contained unsafe pattern '{match}']", True
        return user_input, False

    @classmethod
    def build_context(
        cls,
        tenant_id: str,
        company_id: str,
        owner_instruction: str,
        company_metadata: Optional[Dict[str, Any]] = None,
        active_missions: Optional[List[Dict[str, Any]]] = None,
        departments: Optional[List[Dict[str, Any]]] = None,
        pending_approvals: Optional[List[Dict[str, Any]]] = None,
        recent_decisions: Optional[List[Dict[str, Any]]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        memory_items: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        spending_limit_inr: float = 50000.0,
        model_version: str = "gemma-4-31b-it",
        department_scope: Optional[str] = None
    ) -> AssembledExecutiveContext:
        """
        Assembles governed, least-privilege executive context for Gemma 4.
        """
        sanitized_instruction, injection_flagged = cls.sanitize_untrusted_input(owner_instruction)

        comp_meta = company_metadata or {
            "company_name": "Royal Hotel Jaipur",
            "industry": "Hospitality",
            "revenue": 1200000.0,
            "cost": 750000.0
        }

        # 1. Constitutional Context
        const_ctx = (
            "--- SECTION 1: CONSTITUTIONAL & SOVEREIGN INVARIANTS ---\n"
            "1. SOVEREIGN AUTHORITY: The Human Owner is the supreme authority. Gemma 4 is a cognitive assistant, not root authority.\n"
            "2. CAPABILITY != AUTHORITY: Possession of a tool does not grant permission to execute it without governance authorization.\n"
            "3. CLAIM != EXECUTION != REALITY: Model inferences are not facts until verified by the Physical Truth Engine.\n"
            "4. FAIL CLOSED: If instructions are ambiguous or evidence is conflicting, ask clarification; never execute destructive mutations.\n"
            "5. ISOLATION: Strict multitenant and company isolation enforced; cross-tenant data access is impossible.\n"
        )

        # 2. Role Context
        role_ctx = (
            "--- SECTION 2: AI CEO EXECUTIVE ROLE ---\n"
            f"You are the governed AI CEO operating under ZONATA OS for company: {comp_meta.get('company_name')} ({comp_meta.get('industry')}).\n"
            "Your duties: understand objectives, inspect operational state, formulate plans, decompose tasks, request authorizations, "
            "supervise departments, verify outcomes, and report transparently to the Owner.\n"
        )

        # 3. Organizational Context (Least-Privilege Scoped)
        dept_list = departments or [
            {"name": "Revenue Management", "status": "ACTIVE", "workload_pct": 65},
            {"name": "Operations", "status": "ACTIVE", "workload_pct": 70},
            {"name": "Marketing", "status": "ACTIVE", "workload_pct": 45},
            {"name": "Finance", "status": "ACTIVE", "workload_pct": 40}
        ]
        if department_scope:
            dept_list = [d for d in dept_list if d.get("name") == department_scope] or dept_list

        org_ctx = (
            "--- SECTION 3: ORGANIZATIONAL STATE ---\n"
            f"Company: {comp_meta.get('company_name')} | Tenant ID: {tenant_id} | Company ID: {company_id}\n"
            f"Financial Baseline: Monthly Revenue ₹{comp_meta.get('revenue', 0):,.2f}, Operating Cost ₹{comp_meta.get('cost', 0):,.2f}\n"
            f"Active Departments ({len(dept_list)}):\n" +
            "\n".join([f"  - {d.get('name')}: Workload {d.get('workload_pct', 0)}% (Status: {d.get('status', 'ACTIVE')})" for d in dept_list]) +
            "\n"
        )

        # 4. Mission Context (Executive Summary, avoiding context blowout)
        miss_list = active_missions or []
        mission_summaries = [
            f"  - [{m.get('priority', 'P1')}] {m.get('title', 'Mission')} (Dept: {m.get('department')}, Status: {m.get('status')})"
            for m in miss_list[:5]
        ]
        mission_ctx = (
            "--- SECTION 4: ACTIVE MISSIONS SUMMARY ---\n"
            f"Total Active Missions: {len(miss_list)}\n" +
            ("\n".join(mission_summaries) if mission_summaries else "  - No active missions currently executing.") +
            "\n"
        )

        # 5. Tool Context (Governed Manifest)
        tools = available_tools or [
            {"tool_id": "hospitality_pms_yield_optimizer", "description": "Adjusts room rates and dynamic pricing based on occupancy targets"},
            {"tool_id": "marketing_campaign_dispatcher", "description": "Dispatches localized marketing outreach across digital channels"},
            {"tool_id": "operational_night_audit_runner", "description": "Executes accounting and ledger reconciliation audit"},
            {"tool_id": "customer_support_inbox_triager", "description": "Prioritizes and routes guest service inquiries"}
        ]
        tool_manifest_str = json.dumps(tools, sort_keys=True)
        tool_manifest_hash = hashlib.sha256(tool_manifest_str.encode("utf-8")).hexdigest()

        tool_ctx = (
            "--- SECTION 5: GOVERNED CAPABILITIES (TOOLS) ---\n"
            "You may propose tool invocations. The AuthorityGateway determines whether execution is permitted:\n" +
            "\n".join([f"  - {t['tool_id']}: {t.get('description', '')}" for t in tools]) +
            "\n"
        )

        # 6. Memory Context
        mems = memory_items or []
        mem_ctx = (
            "--- SECTION 6: RELEVANT ORGANIZATIONAL MEMORY ---\n" +
            ("\n".join([f"  - [Level {m.get('level', 5)}] {m.get('content')}" for m in mems[:4]]) if mems else "  - Clean working baseline.") +
            "\n"
        )

        # 7. Policy & Financial Boundaries Context
        policy_ctx = (
            "--- SECTION 7: POLICY & RISK BOUNDARIES ---\n"
            f"Financial Authorization Limit: ₹{spending_limit_inr:,.2f} INR\n"
            "- Actions exceeding ₹50,000 INR require Human Owner Approval.\n"
            "- Destructive mutations, employee terminations, and legal commitments require Human Owner Approval.\n"
            "- All decisions must be accompanied by cryptographic evidence and rollback plans.\n"
        )

        # 8. Conversation Context
        conv_hist = conversation_history or []
        conv_ctx = (
            "--- SECTION 8: RECENT EXECUTIVE CONVERSATION ---\n" +
            ("\n".join([f"  {c.get('role', 'user').upper()}: {c.get('content')}" for c in conv_hist[-3:]]) if conv_hist else "  (New executive dialogue)") +
            "\n"
        )

        # Composition of System Instruction
        system_instruction = (
            f"{const_ctx}\n{role_ctx}\n{policy_ctx}\n"
            "Format all strategic actions into structured executive decisions. "
            "Differentiate between FACT, OBSERVATION, INFERENCE, and RECOMMENDATION. "
            "When evidence is insufficient, state 'Insufficient evidence'."
        )

        # Composition of Context
        composed_prompt = (
            f"{org_ctx}\n{mission_ctx}\n{tool_ctx}\n{mem_ctx}\n{conv_ctx}\n"
            f"--- SECTION 9: HUMAN OWNER DIRECTIVE ---\n"
            f"OWNER SAYS: \"{sanitized_instruction}\"\n"
            "--- END OF PROMPT ---"
        )

        full_raw = f"{system_instruction}\n{composed_prompt}"
        context_hash = hashlib.sha256(full_raw.encode("utf-8")).hexdigest()

        return AssembledExecutiveContext(
            tenant_id=tenant_id,
            company_id=company_id,
            prompt_version=cls.PROMPT_VERSION,
            model_version=model_version,
            policy_version=cls.POLICY_VERSION,
            system_instruction=system_instruction,
            composed_prompt=composed_prompt,
            untrusted_data_payload={"raw_directive": owner_instruction, "injection_flagged": injection_flagged},
            context_hash=context_hash,
            tool_manifest_hash=tool_manifest_hash,
            active_missions_count=len(miss_list),
            pending_approvals_count=len(pending_approvals or []),
            budget_ceiling_inr=spending_limit_inr,
            least_privilege_scope=department_scope or "GLOBAL_EXECUTIVE"
        )
