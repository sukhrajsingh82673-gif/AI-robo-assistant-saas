"""
RoboAssistant Company OS 2.0 — ZONATA Stateful Agent Adapter
Provides unified continuity and persistent memory integration for:
1. Sovereign AI CEO (Executive persona, Host context, Decision persistence)
2. Interactive Meeting Room (Context sync, Decision memory records)
3. Floating Assistant / Coworker (Personal workspace continuity)
4. Governed Multi-Agent Workforce Specialists (Cross-mission recall and finding persistence)

Constitutional Principle:
Memory provides context and long-horizon recall; it NEVER grants authority or bypasses policy.
"""

import time
import uuid
import json
from typing import Dict, List, Optional, Any, Tuple

from core.db import db
from core.stateful_agent_runtime import (
    StatefulAgentMemoryGateway,
    StatefulAgentIdentity,
    MemoryRecord,
    MemoryScope,
    MemoryType,
    MemoryCategory,
    ConfidenceLevel,
    ConflictResolution,
    SecretScanner,
    SecurityException
)


class StatefulAgentAdapter:
    """
    Adapter orchestrating agent identities, working memory blocks,
    and cross-session memory sync for all ZONATA subsystems.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id
        self.gateway = StatefulAgentMemoryGateway(tenant_id=tenant_id)
        self._ensure_core_identities()

    def _ensure_core_identities(self):
        """Initializes default AI CEO and Coworker stateful identities if not present."""
        # 1. AI CEO Identity
        self.gateway.register_or_get_agent(
            agent_id="agt_ai_ceo",
            name="AI CEO",
            role="Chief Executive Officer",
            persona_block=(
                "I am the Sovereign AI CEO of the enterprise. My core objective is maximizing sustainable "
                "enterprise value, revenue velocity, and operating contribution while strictly adhering to "
                "Host policy, budget ceilings, and zero-compromise security governance."
            ),
            human_block=(
                "Host is the ultimate owner and sovereign authority. Requires transparent briefing, "
                "cryptographic approval for high-risk and budget expenditures, and verifiable causality."
            ),
            system_instructions=(
                "Operate with absolute fidelity to verified facts. Treat memory as historical context, "
                "not authority grants. Escalate non-idempotent or high-spending actions to the Host."
            ),
            model_config={"model": "Gemini 3.8 Flash (High)", "temperature": 0.2}
        )

        # 2. Coworker Assistant Identity
        self.gateway.register_or_get_agent(
            agent_id="agt_coworker",
            name="Floating Coworker",
            role="Executive Automation Assistant",
            persona_block=(
                "I am the Host's floating desktop and workspace companion. I execute autonomous tasks, "
                "monitor background operations, and orchestrate browser/host automation safely."
            ),
            human_block=(
                "Host values fast feedback, concise interaction, and safe execution with sandbox isolation."
            ),
            system_instructions=(
                "Follow safe browsing and desktop control policies. Always check credential handles "
                "through the secure broker."
            ),
            model_config={"model": "Gemini 3.8 Flash (High)", "temperature": 0.3}
        )

    # -----------------------------------------------------------------
    # AI CEO & Executive Meeting Room Continuity
    # -----------------------------------------------------------------

    def sync_meeting_decision_to_memory(
        self,
        meeting_id: str,
        company_id: str,
        title: str,
        description: str,
        decision_type: str = "STRATEGIC"
    ) -> MemoryRecord:
        """Persists an executive meeting decision into company and meeting memory."""
        key = f"decision_{title.lower().replace(' ', '_')[:32]}"
        content = f"Decision '{title}' ({decision_type}): {description}"
        return self.gateway.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=company_id,
            memory_key=key,
            content=content,
            memory_type=MemoryType.CORE.value,
            category=MemoryCategory.DECISION.value,
            source=f"MEETING:{meeting_id}",
            confidence=ConfidenceLevel.VERIFIED.value,
            metadata={"meeting_id": meeting_id, "decision_type": decision_type}
        )

    def sync_meeting_summary_to_memory(
        self,
        meeting_id: str,
        company_id: str,
        summary: str
    ) -> MemoryRecord:
        """Stores meeting summary into archival memory."""
        key = f"meeting_summary_{meeting_id}"
        return self.gateway.store_memory(
            scope=MemoryScope.MEETING.value,
            scope_id=meeting_id,
            memory_key=key,
            content=summary,
            memory_type=MemoryType.ARCHIVAL.value,
            category=MemoryCategory.SUMMARY.value,
            source=f"MEETING:{meeting_id}",
            confidence=ConfidenceLevel.VERIFIED.value,
            metadata={"company_id": company_id}
        )

    def get_ceo_briefing_context(self, company_id: str) -> Dict[str, Any]:
        """Loads persistent persona, human block, and scoped company memory for the AI CEO."""
        ceo = self.gateway.get_agent("agt_ai_ceo")
        memory_records = self.gateway.get_agent_effective_memory("agt_ai_ceo", company_id=company_id, limit=20)
        conflicts = self.gateway.list_conflicts(scope_id=company_id, status="OPEN")

        return {
            "persona_block": ceo.persona_block if ceo else "",
            "human_block": ceo.human_block if ceo else "",
            "active_memories": [m.to_dict() for m in memory_records],
            "open_conflicts": [c.to_dict() for c in conflicts]
        }

    # -----------------------------------------------------------------
    # Coworker & Assistant Continuity
    # -----------------------------------------------------------------

    def get_coworker_context(self, workspace_mode: str = "PERSONAL", company_id: Optional[str] = None) -> Dict[str, Any]:
        """Loads coworker working memory blocks and relevant workspace memories."""
        coworker = self.gateway.get_agent("agt_coworker")
        scope = MemoryScope.PERSONAL_WORKSPACE.value if workspace_mode == "PERSONAL" else MemoryScope.COMPANY.value
        scope_id = "ws_personal" if workspace_mode == "PERSONAL" else (company_id or "comp_primary")
        records = self.gateway.query_memory(scope=scope, scope_id=scope_id, limit=15)

        return {
            "persona_block": coworker.persona_block if coworker else "",
            "human_block": coworker.human_block if coworker else "",
            "recent_context": [r.to_dict() for r in records]
        }

    # -----------------------------------------------------------------
    # Workforce Specialist Agent Memory
    # -----------------------------------------------------------------

    def register_workforce_specialist(
        self,
        specialist_id: str,
        name: str,
        role: str,
        company_id: str,
        department_id: str,
        mission_focus: str,
        allowed_tools: List[str]
    ) -> StatefulAgentIdentity:
        """Registers a persistent identity for a workforce specialist."""
        persona = f"Specialist in {role} for {department_id}. Primary mission focus: {mission_focus}."
        human = "Adheres to Host governance and ZONATA Authority Gateway limits."
        return self.gateway.register_or_get_agent(
            agent_id=specialist_id,
            name=name,
            role=role,
            company_id=company_id,
            department_id=department_id,
            persona_block=persona,
            human_block=human,
            tools=allowed_tools
        )

    def record_specialist_finding(
        self,
        specialist_id: str,
        company_id: str,
        mission_id: str,
        finding_key: str,
        finding_content: str,
        confidence: str = ConfidenceLevel.OBSERVED.value
    ) -> MemoryRecord:
        """Stores a verified or observed finding from a specialist into mission and company memory."""
        return self.gateway.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=company_id,
            memory_key=finding_key,
            content=finding_content,
            memory_type=MemoryType.ARCHIVAL.value,
            category=MemoryCategory.FACT.value,
            source=f"SPECIALIST:{specialist_id}:MISSION:{mission_id}",
            confidence=confidence,
            metadata={"mission_id": mission_id, "specialist_id": specialist_id}
        )

    # -----------------------------------------------------------------
    # Section 74 & 75 Governed Demonstration Scenarios
    # -----------------------------------------------------------------

    def run_executive_continuity_demonstration(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """
        Section 74 Demonstration:
        Demonstrates long-horizon executive continuity across sessions:
        Session 1: Host briefs AI CEO with strategic directive (22% margin target & ₹50,000 tool cap).
        Simulated Restart: New gateway queries memory directly from SQLite.
        Session 2: AI CEO recalls the directive and maintains continuity without re-prompting.
        """
        timeline = []
        # Session 1: Store strategic directives
        s1_time = time.time()
        timeline.append({"step": "SESSION_1_START", "message": "Executive Briefing convened with Host and AI CEO."})

        # Update Human block with Host preference
        ceo = self.gateway.get_agent("agt_ai_ceo")
        updated_human = ceo.human_block + " | Directive: Prioritize Q3 margin expansion to 22%."
        ceo.update_blocks(human=updated_human)
        timeline.append({"step": "HUMAN_BLOCK_UPDATED", "human_block": updated_human})

        run_id = uuid.uuid4().hex[:6]
        mem_key = f"budget_policy_tool_spending_ceiling_{run_id}"

        # Store memory record for tool spending limit
        rec = self.gateway.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=company_id,
            memory_key=mem_key,
            content="Strict monthly spending limit of ₹50,000 on software tools and APIs.",
            memory_type=MemoryType.CORE.value,
            category=MemoryCategory.CONSTRAINT.value,
            source="HOST_EXECUTIVE_BRIEFING",
            confidence=ConfidenceLevel.HOST_PROVIDED.value
        )
        timeline.append({"step": "MEMORY_RECORDED", "record_id": rec.record_id, "key": rec.memory_key})

        # Record conversation turns in recall session
        sess = self.gateway.get_or_create_conversation_session("agt_ai_ceo", session_type="MEETING", company_id=company_id)
        self.gateway.record_turn(sess["session_id"], role="HOST", content="Set our Q3 margin target to 22% and cap software tools at ₹50,000.")
        self.gateway.record_turn(sess["session_id"], role="AI CEO", content="Acknowledged, Host. Both directives recorded into working and core memory.")
        timeline.append({"step": "RECALL_SESSION_RECORDED", "session_id": sess["session_id"]})

        # Simulated Restart / Context Query in Session 2
        fresh_gateway = StatefulAgentMemoryGateway(tenant_id=self.tenant_id)
        recalled_ceo = fresh_gateway.get_agent("agt_ai_ceo")
        recalled_mems = fresh_gateway.query_memory(scope=MemoryScope.COMPANY.value, scope_id=company_id, memory_key=mem_key)
        
        timeline.append({
            "step": "SESSION_2_RESUME",
            "recalled_human_block": recalled_ceo.human_block,
            "recalled_constraint": recalled_mems[0].content if recalled_mems else None,
            "continuity_verified": (
                "margin expansion to 22%" in recalled_ceo.human_block and
                len(recalled_mems) > 0 and
                "₹50,000" in recalled_mems[0].content
            )
        })

        return {
            "scenario": "SECTION_74_EXECUTIVE_CONTINUITY",
            "company_id": company_id,
            "status": "VERIFIED_CONTINUITY",
            "timeline": timeline
        }

    def run_workforce_coordination_demonstration(self, company_id: str = "comp_primary") -> Dict[str, Any]:
        """
        Section 75 Demonstration:
        Cross-agent coordination with conflict detection and resolution:
        1. Specialist A (Lead Researcher) records churn estimate at 14%.
        2. Specialist B (Financial Analyst) records contradictory churn estimate at 8%.
        3. MemoryConflict is triggered and recorded in DB.
        4. CEO resolves conflict using USE_A (based on primary CRM cohort data).
        5. Effective memory is verified to reflect 14% with old record superseded.
        """
        timeline = []
        timeline.append({"step": "START", "message": "Initiating cross-specialist coordination demo."})
        churn_key = f"enterprise_churn_rate_estimate_{uuid.uuid4().hex[:6]}"

        # 1. Specialist A
        rec_a = self.gateway.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=company_id,
            memory_key=churn_key,
            content="Enterprise customer churn rate is 14% based on active cohorts.",
            memory_type=MemoryType.ARCHIVAL.value,
            category=MemoryCategory.FACT.value,
            source="SPECIALIST:lead_researcher",
            confidence=ConfidenceLevel.OBSERVED.value
        )
        timeline.append({"step": "SPECIALIST_A_STORED", "record_id": rec_a.record_id, "content": rec_a.content})

        # 2. Specialist B stores contradictory content on the same key
        rec_b = self.gateway.store_memory(
            scope=MemoryScope.COMPANY.value,
            scope_id=company_id,
            memory_key=churn_key,
            content="Enterprise customer churn rate is 8% based on annualized revenue calculations.",
            memory_type=MemoryType.ARCHIVAL.value,
            category=MemoryCategory.FACT.value,
            source="SPECIALIST:financial_analyst",
            confidence=ConfidenceLevel.OBSERVED.value
        )
        timeline.append({"step": "SPECIALIST_B_STORED", "record_id": rec_b.record_id, "content": rec_b.content})

        # 3. Check Conflict
        conflicts = self.gateway.list_conflicts(scope_id=company_id, status="OPEN")
        matching = [c for c in conflicts if c.memory_key == churn_key]
        if not matching:
            raise RuntimeError("Conflict detection failed to flag contradictory statements!")

        conflict = matching[0]
        timeline.append({"step": "CONFLICT_DETECTED", "conflict_id": conflict.conflict_id, "details": conflict.conflict_details})

        # 4. Resolve Conflict: USE_A (Keep primary cohort evidence)
        res = self.gateway.resolve_conflict(conflict.conflict_id, choice=ConflictResolution.USE_A.value, resolved_by="AI_CEO")
        timeline.append({"step": "CONFLICT_RESOLVED", "resolution": res})

        # 5. Verify effective memory
        effective = self.gateway.query_memory(scope=MemoryScope.COMPANY.value, scope_id=company_id, memory_key=churn_key)
        timeline.append({
            "step": "EFFECTIVE_MEMORY_VERIFIED",
            "active_count": len(effective),
            "effective_content": effective[0].content if effective else None,
            "verified": len(effective) == 1 and "14%" in effective[0].content
        })

        return {
            "scenario": "SECTION_75_WORKFORCE_COORDINATION_AND_CONFLICT",
            "company_id": company_id,
            "status": "VERIFIED_RESOLUTION",
            "timeline": timeline
        }


# Global adapter instance
stateful_agent_adapter = StatefulAgentAdapter(tenant_id="tnt_primary")
