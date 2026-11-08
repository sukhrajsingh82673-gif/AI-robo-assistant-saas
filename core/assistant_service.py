"""
RoboAssistant Company OS 1.0 — ZONATA AI Universal Assistant Service
Sovereign personal and organizational communication gateway between the Owner (Host),
the AI CEO, autonomous workforce, document management, multimodal runtimes, and meeting orchestration.

Architectural Separation:
- Owner (Host): Sovereign Human Authority.
- ZONATA AI: Universal Personal & Company Assistant & Communication Gateway.
- AI CEO: Sovereign Executive Authority over company workforce, governance, and strategy.

Enforces:
- Personal vs Company context classification and strict storage/governance isolation.
- Structured AI CEO delegation pipeline (Owner -> ZONATA AI -> AI CEO -> Workforce -> Verification -> Owner).
- Real document generation (PDF, DOCX, XLSX, PPTX, CSV) and intelligent file retrieval.
- Provider-confirmed meeting scheduling with AI representative disclosure (never fabricated links).
- Cryptographic evidence ledger sealing and human authorization gates.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import json
import logging
import re
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from .db import db
from .document_generator import document_generator, DocumentFormat, StorageBoundary, DocumentCategory

logger = logging.getLogger("zonata.assistant")

class IntentCategory(str, Enum):
    PERSONAL = "PERSONAL"
    COMPANY = "COMPANY"
    MIXED = "MIXED"
    DOCUMENT_REQUEST = "DOCUMENT_REQUEST"
    MEETING_REQUEST = "MEETING_REQUEST"
    RESEARCH = "RESEARCH"
    INFORMATION_RETRIEVAL = "INFORMATION_RETRIEVAL"
    APPLICATION_CHANGE = "APPLICATION_CHANGE"
    OPERATIONAL_TASK = "OPERATIONAL_TASK"
    AMBIGUOUS = "AMBIGUOUS"


# The assistant never reports a downstream mission as verified.  These are the
# only lifecycle states it is allowed to expose to the Owner.
EXECUTION_STATES = (
    "RECEIVED",
    "ACCEPTED",
    "DELEGATED",
    "EXECUTING",
    "AWAITING_APPROVAL",
    "COMPLETED",
    "VERIFIED",
    "DELIVERED",
    "BLOCKED",
)


class AssistantContextClassifier:
    """
    Intelligent request classifier that separates personal requests from corporate
    directives, identifies document production, scheduling, research, retrieval,
    application-change and operational intent, and detects ambiguity.

    The classifier is deliberately conservative: an unclear request is never
    silently forwarded to the AI CEO as company work.  Company routing requires
    either an explicit Owner choice or an unambiguous company signal.
    """

    COMPANY_KEYWORDS = [
        "revenue", "gross margin", "margin", "p&l", "pms", "erp", "crm", "sales",
        "churn", "ebitda", "q1", "q2", "q3", "q4", "fiscal", "board", "director",
        "employee", "coworker", "workforce", "department", "hiring", "firing",
        "payroll", "vendor", "invoice", "compliance", "audit", "sop", "kpi",
        "kra", "mission", "corporate", "client", "customer", "procurement",
        "hotel", "jaipur", "delhi", "resort", "royal hotel", "zonata tech",
        "entity", "company", "our business", "our team",
    ]

    PERSONAL_KEYWORDS = [
        "my personal", "personal note", "private", "my diet", "my gym", "workout",
        "recipe", "vacation for me", "family", "personal budget", "personal task",
        "my shopping", "grocery", "hobby", "learning plan for me",
        "personal expense", "my journal", "personal memo", "my own",
    ]

    DOCUMENT_KEYWORDS = [
        "generate pdf", "create pdf", "pdf report", "docx", "word document",
        "spreadsheet", "excel", "xlsx", "pptx", "presentation", "slides", "csv",
        "download document", "export file", "find document", "find the document",
        "retrieve file", "show document", "where is the document", "create report",
        "draft proposal", "write a report", "make a report",
    ]

    MEETING_KEYWORDS = [
        "schedule meeting", "schedule a meeting", "book meeting", "google meet",
        "calendar", "convene council", "set up call", "alignment call",
        "schedule alignment", "reschedule meeting", "meeting link",
        "invite to meeting", "schedule call", "book a call",
    ]

    APPLICATION_KEYWORDS = [
        "change the app", "change the application", "modify the app",
        "modify the code", "update the ui", "change the ui", "fix the bug",
        "deploy the app", "change the frontend", "change the backend",
        "add a feature", "remove a feature", "refactor",
    ]

    OPERATIONAL_KEYWORDS = [
        "run the", "execute the", "restart the", "deploy", "sync the",
        "backup", "send an email", "send email", "create a ticket",
        "open a ticket", "trigger the workflow", "start the workflow",
        "shut down", "reboot",
    ]

    RESEARCH_KEYWORDS = [
        "research", "market intelligence", "competitor analysis", "trend",
        "industry analysis", "compare", "sources", "citations",
    ]

    AMBIGUOUS_TRIGGERS = [
        "review expenses", "audit budget", "organize notes", "schedule reminder",
        "check files", "look into this", "handle it", "do the needful",
        "sort this out", "take care of it",
    ]

    @classmethod
    def _matches(cls, prompt: str, keywords: List[str]) -> bool:
        for keyword in keywords:
            if " " in keyword:
                if keyword in prompt:
                    return True
            elif re.search(r"\b" + re.escape(keyword) + r"\b", prompt):
                return True
        return False

    @classmethod
    def _clarification(cls) -> str:
        return (
            "I can handle this privately for you, or route it to the AI CEO as "
            "company work. Which should I use? (Personal stays in your private "
            "workspace; Company is delegated through the AI CEO.)"
        )

    @classmethod
    def classify(cls, prompt: str, explicit_workspace: Optional[str] = None) -> Dict[str, Any]:
        p_lower = (prompt or "").lower().strip()
        explicit = (explicit_workspace or "").upper()
        if explicit not in ("PERSONAL", "COMPANY"):
            explicit = ""

        # 0. Empty input is never a company directive.
        if not p_lower:
            return {
                "category": IntentCategory.AMBIGUOUS.value,
                "confidence": 0.0,
                "is_ambiguous": True,
                "clarification": "What would you like me to do?",
                "suggested_routing": "OWNER_CLARIFICATION",
                "workspace_hint": explicit or "AUTO",
            }

        # 1. Scheduling and document production are modes, not company signals.
        if cls._matches(p_lower, cls.MEETING_KEYWORDS):
            return {
                "category": IntentCategory.MEETING_REQUEST.value,
                "confidence": 0.95,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "MEETING_SERVICE",
                "workspace_hint": explicit or "AUTO",
            }

        if cls._matches(p_lower, cls.DOCUMENT_KEYWORDS):
            is_retrieval = any(
                token in p_lower
                for token in ("find", "search", "where is", "retrieve", "download", "show document")
            )
            return {
                "category": (
                    IntentCategory.INFORMATION_RETRIEVAL.value
                    if is_retrieval
                    else IntentCategory.DOCUMENT_REQUEST.value
                ),
                "confidence": 0.92,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "DOCUMENT_SERVICE",
                "workspace_hint": explicit or "AUTO",
            }

        # 2. Application changes are never executed by the assistant.
        if cls._matches(p_lower, cls.APPLICATION_KEYWORDS):
            return {
                "category": IntentCategory.APPLICATION_CHANGE.value,
                "confidence": 0.90,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "OWNER_APPROVAL_REQUIRED",
                "workspace_hint": explicit or "COMPANY",
            }

        # 3. An explicit Owner workspace choice wins over keyword inference.
        if explicit:
            return {
                "category": explicit,
                "confidence": 1.0,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "PERSONAL_ASSISTANT" if explicit == "PERSONAL" else "AI_CEO",
                "workspace_hint": explicit,
            }

        has_personal = cls._matches(p_lower, cls.PERSONAL_KEYWORDS)
        has_company = cls._matches(p_lower, cls.COMPANY_KEYWORDS)

        # 4. Mixed requests must not leak one context into the other.
        if has_personal and has_company:
            return {
                "category": IntentCategory.MIXED.value,
                "confidence": 0.80,
                "is_ambiguous": True,
                "clarification": (
                    "This touches both your private information and company data. "
                    "Should I keep it personal, or send only the company part to the AI CEO?"
                ),
                "suggested_routing": "OWNER_CLARIFICATION",
                "workspace_hint": "AUTO",
            }

        if has_personal:
            return {
                "category": IntentCategory.PERSONAL.value,
                "confidence": 0.94,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "PERSONAL_ASSISTANT",
                "workspace_hint": "PERSONAL",
            }

        if has_company:
            return {
                "category": IntentCategory.COMPANY.value,
                "confidence": 0.95,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "AI_CEO",
                "workspace_hint": "COMPANY",
            }

        # 5. Research without a context signal is personal by default; it only
        # becomes company work when the Owner explicitly says so.
        if cls._matches(p_lower, cls.RESEARCH_KEYWORDS):
            return {
                "category": IntentCategory.RESEARCH.value,
                "confidence": 0.85,
                "is_ambiguous": False,
                "clarification": None,
                "suggested_routing": "PERSONAL_ASSISTANT",
                "workspace_hint": "PERSONAL",
            }

        # 6. Operational verbs still need an explicit context.
        if cls._matches(p_lower, cls.OPERATIONAL_KEYWORDS):
            return {
                "category": IntentCategory.OPERATIONAL_TASK.value,
                "confidence": 0.70,
                "is_ambiguous": True,
                "clarification": cls._clarification(),
                "suggested_routing": "OWNER_CLARIFICATION",
                "workspace_hint": "AUTO",
            }

        # 7. Anything else is ambiguous.  Never default to company execution.
        return {
            "category": IntentCategory.AMBIGUOUS.value,
            "confidence": 0.40,
            "is_ambiguous": True,
            "clarification": cls._clarification(),
            "suggested_routing": "OWNER_CLARIFICATION",
            "workspace_hint": "AUTO",
        }



class FloatingAssistantService:
    """
    Unified ZONATA AI Assistant Service — Sovereign Communication Gateway.
    Coordinates personal execution independently, and delegates company-level
    operations strictly through the sovereign AI CEO.
    """

    def __init__(self, tenant_id: str = "tnt_primary"):
        self.tenant_id = tenant_id

    # =========================================================================
    # UNIFIED INTERACTION PIPELINE (Owner -> ZONATA AI Gateway)
    # =========================================================================

    def interact(
        self,
        prompt: str,
        workspace_mode: str = "AUTO", # AUTO | PERSONAL | COMPANY
        company_id: Optional[str] = None,
        user_id: str = "usr_owner",
        session_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Master interaction entrypoint for ZONATA AI Assistant:
        1. Classifies request context (Personal vs Company vs Ambiguous vs Document vs Meeting).
        2. Routes Personal requests directly to isolated personal storage and intelligence.
        3. Forwards Company directives to the sovereign AI CEO runtime.
        4. Handles real document generation (PDF, DOCX, XLSX, CSV) and intelligent search.
        5. Schedules meetings only after a calendar provider confirms them.
        6. Persists conversation turns in assistant_messages.
        7. Returns direct, verified deliverable cards to the Owner.
        """
        now = time.time()
        sess_id = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        cid = (company_id or "").strip() or None

        # Step 1: Context Classification.  Classification happens before logging
        # so a personal request is never written into a company conversation.
        classification = AssistantContextClassifier.classify(
            prompt=prompt,
            explicit_workspace=workspace_mode if workspace_mode != "AUTO" else None
        )
        cat = classification["category"]
        hint = (classification.get("workspace_hint") or "").upper()

        # Determine the true storage/logging boundary for this turn.
        if hint == "PERSONAL" or workspace_mode == "PERSONAL":
            log_company_id = None
            effective_mode = "PERSONAL"
        elif hint == "COMPANY" or workspace_mode == "COMPANY":
            log_company_id = cid
            effective_mode = "COMPANY"
        else:
            log_company_id = None
            effective_mode = "AMBIGUOUS"

        self._record_message(
            session_id=sess_id,
            user_id=user_id,
            company_id=log_company_id,
            sender="user",
            workspace_mode=effective_mode,
            content=prompt,
            intent_category=cat,
        )

        # Step 2: Handle Ambiguous / Mixed Requests with one concise question.
        if classification["is_ambiguous"] and classification["clarification"]:
            reply_text = classification["clarification"]
            choices = [
                {"label": "🏢 Company task (delegate to the AI CEO)", "mode": "COMPANY"},
                {"label": "👤 Personal request (private)", "mode": "PERSONAL"},
            ]
            res_payload = {
                "success": True,
                "reply": reply_text,
                "intent_category": cat,
                "workspace_mode": "AMBIGUOUS",
                "routed_to": "OWNER_CLARIFICATION",
                "execution_state": "RECEIVED",
                "choices": choices,
                "action_card": None,
                "deliverable_card": None,
                "citations": [{
                    "source_type": "INTERNAL",
                    "label": "ZONATA Intent Arbiter",
                    "verified": True,
                }],
                "classification": classification,
                "timestamp": now,
            }
            self._record_message(
                sess_id, user_id, log_company_id, "assistant", "AMBIGUOUS",
                reply_text, citations=res_payload["citations"], intent_category=cat,
            )
            return res_payload

        # Step 3: Application changes require an approved engineering workflow.
        if cat == IntentCategory.APPLICATION_CHANGE.value:
            reply_text = (
                "That is an application-change request. I cannot modify production code "
                "or deploy from the assistant. Nothing has been changed. If you confirm, "
                "this must be handled as an approved engineering task through the governed "
                "workforce workflow."
            )
            payload = {
                "success": True,
                "reply": reply_text,
                "intent_category": cat,
                "workspace_mode": "COMPANY",
                "routed_to": "OWNER_APPROVAL_REQUIRED",
                "execution_state": "AWAITING_APPROVAL",
                "choices": [],
                "action_card": {
                    "type": "APPLICATION_CHANGE_REQUEST",
                    "requires_approval": True,
                    "status": "NOT_EXECUTED",
                },
                "deliverable_card": None,
                "citations": [{
                    "source_type": "INTERNAL",
                    "label": "ZONATA Change Control",
                    "verified": True,
                }],
                "classification": classification,
                "timestamp": now,
            }
            self._record_message(
                sess_id, user_id, cid, "assistant", "COMPANY", reply_text,
                payload["action_card"], payload["citations"], intent_category=cat,
            )
            return payload

        # Step 4: Meeting scheduling.
        if cat == IntentCategory.MEETING_REQUEST.value:
            return self._handle_meeting_intent(prompt, cid, user_id, sess_id, effective_mode)

        # Step 5: Document production / retrieval.
        if cat in (
            IntentCategory.DOCUMENT_REQUEST.value,
            IntentCategory.INFORMATION_RETRIEVAL.value,
        ):
            boundary = "PERSONAL" if effective_mode == "PERSONAL" else "COMPANY"
            return self._handle_document_intent(
                prompt, cid, user_id, sess_id, boundary, attachments=attachments
            )

        # Step 6: Personal assistance and personal research stay private.
        if cat == IntentCategory.PERSONAL.value or (
            cat == IntentCategory.RESEARCH.value and effective_mode == "PERSONAL"
        ):
            return self._handle_personal_intent(prompt, user_id, sess_id, attachments=attachments)

        # Step 7: Operational tasks still need a real executor; never simulate one.
        if cat == IntentCategory.OPERATIONAL_TASK.value and effective_mode != "COMPANY":
            reply_text = (
                "I can see this is an operational request, but no authorised executor is "
                "attached to a private workspace. Nothing was executed. Switch to Company "
                "context if this should go to the AI CEO, or connect an approved host executor."
            )
            payload = {
                "success": True,
                "reply": reply_text,
                "intent_category": cat,
                "workspace_mode": "PERSONAL",
                "routed_to": "PERSONAL_SANDBOX",
                "execution_state": "BLOCKED",
                "action_card": None,
                "deliverable_card": None,
                "citations": [{
                    "source_type": "INTERNAL",
                    "label": "ZONATA Execution Boundary",
                    "verified": True,
                }],
                "classification": classification,
                "timestamp": now,
            }
            self._record_message(
                sess_id, user_id, None, "assistant", "PERSONAL", reply_text,
                citations=payload["citations"], intent_category=cat,
            )
            return payload

        # Step 8: Company work goes through the sovereign AI CEO.
        if not cid:
            reply_text = (
                "Company work needs a verified company context. Nothing was delegated. "
                "Select a company and resend the request."
            )
            payload = {
                "success": False,
                "reply": reply_text,
                "intent_category": cat,
                "workspace_mode": "COMPANY",
                "routed_to": "AI_CEO",
                "execution_state": "BLOCKED",
                "action_card": None,
                "deliverable_card": None,
                "citations": [],
                "classification": classification,
                "timestamp": now,
            }
            self._record_message(
                sess_id, user_id, None, "assistant", "COMPANY", reply_text,
                intent_category=cat,
            )
            return payload

        return self._handle_company_intent(
            prompt, cid, user_id, sess_id, attachments, classification
        )

    # -------------------------------------------------------------------------
    # Intent Handlers
    # -------------------------------------------------------------------------

    def _handle_personal_intent(
        self,
        prompt: str,
        user_id: str,
        session_id: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Processes personal requests strictly within the private personal sandbox."""
        now = time.time()
        p_lower = prompt.lower()
        attachments = attachments or []

        deliverable_card = None
        provider = None
        model = None
        degraded = False

        wants_document = any(
            w in p_lower
            for w in (
                "pdf", "note", "memo", "summary", "plan", "document", "docx",
                "sheet", "spreadsheet", "write", "draft",
            )
        )

        if wants_document:
            title = f"Personal Memo - {prompt[:40]}"
            fmt = DocumentFormat.PDF if "pdf" in p_lower else DocumentFormat.TXT
            body, provider, model, degraded = self._personal_document_body(prompt)
            doc = document_generator.generate_document(
                title=title,
                format_type=fmt,
                category=DocumentCategory.PERSONAL_DOCUMENT,
                content=body,
                metadata={
                    "verification_status": "PERSONAL_UNVERIFIED",
                    "generated_by": provider or "zonata_text_composer",
                    "model": model,
                },
                storage_boundary=StorageBoundary.PERSONAL,
                user_id=user_id,
                tenant_id=self.tenant_id,
            )
            deliverable_card = {
                "type": "DOCUMENT",
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "format": doc["format"],
                "download_url": doc["download_url"],
                "sha256": doc["sha256"],
                "storage_boundary": "PERSONAL",
                "file_path": doc["file_path"],
            }
            reply = (
                f"I created your private deliverable: **{doc['title']}** "
                f"({doc['format']}). It is stored only in your personal workspace."
            )
            if degraded:
                reply += (
                    " Note: no personal language model was reachable, so the file "
                    "contains a structured record of your request rather than a "
                    "model-written draft."
                )
            execution_state = "DELIVERED"
        else:
            answer, provider, model, degraded = self._personal_answer(prompt)
            if degraded:
                reply = (
                    "I could not reach a personal language model, so I have not "
                    "answered this request. Nothing was executed and no company "
                    "system was contacted. You can configure a model in Settings "
                    "or retry later."
                )
                execution_state = "BLOCKED"
            else:
                reply = answer
                execution_state = "COMPLETED"

        if attachments:
            stored = [a for a in attachments if a.get("doc_id")]
            if stored:
                names = ", ".join(str(a.get("name") or a.get("doc_id")) for a in stored)
                reply += (
                    f"\n\nAttached files stored privately: {names}. "
                    "Content extraction is only available for text-based files in this build."
                )
            else:
                reply += (
                    "\n\nAttachment metadata was received but no file was stored; "
                    "please re-attach the file."
                )

        citations = [{
            "source_type": "INTERNAL",
            "label": "Host Private Workspace (no company disclosure)",
            "verified": True,
        }]
        if provider:
            citations.append({
                "source_type": "MODEL",
                "label": f"{provider}/{model or 'default'}",
                "verified": False,
            })

        self._record_message(
            session_id, user_id, None, "assistant", "PERSONAL", reply,
            deliverable_card, citations, intent_category=IntentCategory.PERSONAL.value,
        )
        return {
            "success": execution_state != "BLOCKED",
            "reply": reply,
            "intent_category": IntentCategory.PERSONAL.value,
            "workspace_mode": "PERSONAL",
            "routed_to": "PERSONAL_SANDBOX",
            "execution_state": execution_state,
            "action_card": None,
            "deliverable_card": deliverable_card,
            "citations": citations,
            "provider": provider,
            "model": model,
            "degraded": degraded,
            "timestamp": now,
        }

    def _personal_answer(self, prompt: str):
        """Return (answer, provider, model, degraded) using the governed LLM runtime."""
        try:
            from core.llm_runtime import llm_runtime
            res = llm_runtime.chat(
                tenant_id=self.tenant_id,
                company_id="",
                system=(
                    "You are ZONATA AI, the Owner's private assistant. Answer the "
                    "Owner directly and concisely. This is a personal, non-company "
                    "request. Do not claim to have executed actions you did not "
                    "perform, and do not invent sources."
                ),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.4,
                intent="personal",
            )
            if res.degraded or not res.content:
                return "", res.provider, res.model, True
            return res.content, res.provider, res.model, False
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Personal model unavailable: %s", exc)
            return "", None, None, True

    def _personal_document_body(self, prompt: str):
        """Build real document content, preferring the model when available."""
        answer, provider, model, degraded = self._personal_answer(
            f"Write the requested personal document. Request: {prompt}"
        )
        if answer and not degraded:
            return answer, provider, model, False
        body = (
            "PERSONAL RECORD\n"
            "================\n\n"
            f"Owner request: {prompt}\n"
            f"Created: {time.ctime()}\n\n"
            "This file is a faithful record of the request created in the private "
            "workspace. No company system was contacted and no external action was "
            "taken. Configure a personal language model to have ZONATA AI write a "
            "full prose draft instead of this structured record."
        )
        return body, provider, model, True

    def _handle_company_intent(
        self,
        prompt: str,
        company_id: str,
        user_id: str,
        session_id: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        classification: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Communicates with the sovereign AI CEO runtime.  The assistant only
        relays verified upstream facts.  It never invents an evidence digest,
        never claims a mission completed, and never turns an exception into a
        fabricated success message.
        """
        now = time.time()
        attachments = attachments or []
        reply_text = ""
        action_card = None
        deliverable_card = None
        citations = []
        evidence_hash = None
        execution_state = "RECEIVED"
        success = False
        ceo_command_type = None
        model_used = None
        epistemic = None
        requested_category = (classification or {}).get("category", IntentCategory.COMPANY.value)

        try:
            with db.get_connection() as conn:
                comp = conn.execute(
                    "SELECT name, industry, revenue FROM companies "
                    "WHERE company_id = ? AND tenant_id = ?",
                    (company_id, self.tenant_id),
                ).fetchone()
                comp_name = comp["name"] if comp else "Selected company"
                comp_industry = comp["industry"] if comp else "General business"

            company_meta = {
                "company_id": company_id,
                "company_name": comp_name,
                "industry": comp_industry,
            }

            from core.ceo_conversation_engine import CEOConversationEngine
            ceo_engine = CEOConversationEngine(tenant_id=self.tenant_id, company_id=company_id)

            ceo_resp = ceo_engine.process_owner_directive(
                instruction=prompt,
                caller_role="OWNER",
                spending_limit_inr=self._resolve_ceo_spending_limit(company_id),
                company_metadata=company_meta,
            )

            reply_text = ceo_resp.reply_text or ""
            evidence_hash = ceo_resp.evidence_digest
            ceo_command_type = ceo_resp.command_type
            model_used = ceo_resp.model_used
            epistemic = ceo_resp.epistemic_classification
            success = bool(ceo_resp.success)

            if not success:
                execution_state = "BLOCKED"
            elif ceo_resp.requires_approval:
                execution_state = "AWAITING_APPROVAL"
            elif ceo_resp.resulting_mission:
                execution_state = "DELEGATED"
            elif ceo_resp.command_type == "CLARIFICATION_REQUIRED":
                execution_state = "ACCEPTED"
            else:
                execution_state = "ACCEPTED"

            if ceo_resp.resulting_mission:
                m = ceo_resp.resulting_mission
                action_card = {
                    "type": "WORKFORCE_MISSION",
                    "mission_id": m.get("mission_id"),
                    "department": m.get("department", "Operations"),
                    "objective": m.get("objective", prompt),
                    # Relay the delegation, not an unverified completion claim.
                    "status": "DELEGATED",
                    "reported_state": m.get("state") or m.get("status"),
                    "verification_status": "UNVERIFIED",
                    "stage": "WORKFORCE_DELEGATED",
                    "requires_approval": ceo_resp.requires_approval,
                    "approval_id": ceo_resp.approval_id,
                }
                reply_text = (
                    f"{reply_text}\n\n"
                    "The AI CEO has delegated this objective to the workforce. "
                    "This is not yet a verified deliverable; completion will only be "
                    "reported after the responsible executive verifies the output."
                )

            if ceo_resp.requires_approval:
                reply_text = (
                    f"{reply_text}\n\n"
                    "Execution is paused until the approval is recorded. Nothing has "
                    "been executed yet."
                )

            citations.append({
                "source_type": "INTERNAL",
                "label": f"AI CEO executive runtime: {comp_name}",
                "verified": bool(evidence_hash),
                "scope": f"Company: {company_id}",
            })

        except Exception as exc:
            logger.exception("AI CEO delegation failed for company %s", company_id)
            reply_text = (
                "I could not reach the AI CEO runtime, so this request was not "
                "delegated and no company work was started. "
                f"Failure: {type(exc).__name__}."
            )
            execution_state = "BLOCKED"
            success = False
            citations.append({
                "source_type": "INTERNAL",
                "label": "ZONATA AI CEO runtime (unavailable)",
                "verified": False,
            })

        if attachments:
            stored = [a for a in attachments if a.get("doc_id")]
            if stored:
                names = ", ".join(str(a.get("name") or a.get("doc_id")) for a in stored)
                reply_text += (
                    f"\n\nAttached files stored in the company workspace: {names}. "
                    "Content extraction is only available for text-based files in this build."
                )
            else:
                reply_text += (
                    "\n\nAttachment metadata was received but no file was stored; "
                    "please re-attach the file."
                )

        self._record_message(
            session_id=session_id,
            user_id=user_id,
            company_id=company_id,
            sender="assistant",
            workspace_mode="COMPANY",
            content=reply_text,
            deliverables=deliverable_card,
            citations=citations,
            intent_category=requested_category,
        )

        return {
            "success": success,
            "reply": reply_text,
            "intent_category": requested_category,
            "workspace_mode": "COMPANY",
            "routed_to": "AI_CEO",
            "execution_state": execution_state,
            "ceo_command_type": ceo_command_type,
            "model_used": model_used,
            "epistemic_classification": epistemic,
            "action_card": action_card,
            "deliverable_card": deliverable_card,
            "citations": citations,
            "evidence_hash": evidence_hash,
            "timestamp": now,
        }

    def _resolve_ceo_spending_limit(self, company_id: str) -> float:
        """Resolve the CEO autonomy cap from settings; fail closed to the registry default."""
        try:
            from core.settings import rbac
            from core.settings.service import settings_v2_service
            principal = rbac.Principal(
                user_id="usr_owner",
                tenant_id=self.tenant_id,
                company_id=company_id,
                role=rbac.ROLE_OWNER,
            )
            payload = settings_v2_service.effective(principal, "ceo_spending_limit", company_id=company_id)
            value = payload.get("value")
            if value is not None:
                return float(value)
        except Exception as exc:
            logger.debug("Could not resolve ceo_spending_limit: %s", exc)
        try:
            from core.settings.registry import settings_registry
            definition = settings_registry.get("ceo_spending_limit")
            if definition is not None:
                return float(definition.default)
        except Exception:
            pass
        return 0.0

    def _handle_document_intent(
        self,
        prompt: str,
        company_id: Optional[str],
        user_id: str,
        session_id: str,
        storage_boundary: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Search the authorised repository or produce a real file.

        A search always reports what the index actually contains.  A missing
        result is reported as ``NOT_FOUND`` instead of silently generating a
        file, and generated content is only described as verified when the
        generator returned a real artefact on disk.
        """
        now = time.time()
        p_lower = prompt.lower()
        boundary = (storage_boundary or "PERSONAL").upper()
        if boundary not in ("PERSONAL", "COMPANY"):
            boundary = "PERSONAL"
        scoped_company = company_id if boundary == "COMPANY" else None

        if boundary == "COMPANY" and not scoped_company:
            reply = (
                "Company documents need a verified company context. Nothing was "
                "searched or generated. Select a company and try again."
            )
            self._record_message(
                session_id, user_id, None, "assistant", "COMPANY", reply,
                intent_category=IntentCategory.INFORMATION_RETRIEVAL.value,
            )
            return {
                "success": False,
                "reply": reply,
                "intent_category": IntentCategory.INFORMATION_RETRIEVAL.value,
                "workspace_mode": "COMPANY",
                "routed_to": "DOCUMENT_SERVICE",
                "execution_state": "BLOCKED",
                "action_card": None,
                "deliverable_card": None,
                "citations": [],
                "timestamp": now,
            }

        is_search = any(
            w in p_lower
            for w in ("find", "search", "where is", "retrieve", "get document", "download", "show document")
        )

        if is_search:
            query_terms = re.sub(
                r"\b(find|search|where is|retrieve|get|show|document|documents|file|files|the|a|an|my|our|please)\b",
                " ",
                p_lower,
            )
            query_terms = re.sub(r"\s+", " ", query_terms).strip()
            results = document_generator.search_documents(
                tenant_id=self.tenant_id,
                user_id=user_id,
                query=query_terms or None,
                storage_boundary=boundary,
                company_id=scoped_company,
            )
            if not results:
                reply = (
                    f"No {boundary.lower()} document matched that search. "
                    "Nothing was created and no other workspace was searched."
                )
                self._record_message(
                    session_id, user_id, scoped_company, "assistant", boundary, reply,
                    intent_category=IntentCategory.INFORMATION_RETRIEVAL.value,
                )
                return {
                    "success": True,
                    "reply": reply,
                    "intent_category": IntentCategory.INFORMATION_RETRIEVAL.value,
                    "workspace_mode": boundary,
                    "routed_to": "DOCUMENT_SERVICE",
                    "execution_state": "COMPLETED",
                    "result_state": "NOT_FOUND",
                    "action_card": None,
                    "deliverable_card": None,
                    "citations": [{
                        "source_type": "INTERNAL",
                        "label": "Document Repository Index",
                        "verified": True,
                    }],
                    "timestamp": now,
                }

            top_doc = results[0]
            others = results[1:5]
            reply = (
                f"I found {len(results)} matching document(s) in the "
                f"{boundary.lower()} workspace. Top result: **{top_doc['title']}** "
                f"({top_doc['format']})."
            )
            if others:
                reply += "\nAlso matched: " + ", ".join(d["title"] for d in others) + "."
            deliverable_card = {
                "type": "DOCUMENT",
                "doc_id": top_doc["doc_id"],
                "title": top_doc["title"],
                "format": top_doc["format"],
                "download_url": top_doc["download_url"],
                "sha256": top_doc["sha256"],
                "storage_boundary": top_doc["storage_boundary"],
            }
            citations = [{
                "source_type": "INTERNAL",
                "label": "Document Repository Index",
                "verified": True,
            }]
            self._record_message(
                session_id, user_id, scoped_company, "assistant", boundary, reply,
                deliverable_card, citations,
                intent_category=IntentCategory.INFORMATION_RETRIEVAL.value,
            )
            return {
                "success": True,
                "reply": reply,
                "intent_category": IntentCategory.INFORMATION_RETRIEVAL.value,
                "workspace_mode": boundary,
                "routed_to": "DOCUMENT_SERVICE",
                "execution_state": "COMPLETED",
                "result_state": "FOUND",
                "action_card": None,
                "deliverable_card": deliverable_card,
                "citations": citations,
                "timestamp": now,
            }

        # ---- Production path -------------------------------------------------
        fmt = DocumentFormat.PDF
        if "xlsx" in p_lower or "excel" in p_lower or "spreadsheet" in p_lower:
            fmt = DocumentFormat.XLSX
        elif "docx" in p_lower or "word" in p_lower:
            fmt = DocumentFormat.DOCX
        elif "pptx" in p_lower or "slides" in p_lower or "presentation" in p_lower:
            fmt = DocumentFormat.PPTX
        elif "csv" in p_lower:
            fmt = DocumentFormat.CSV
        elif "txt" in p_lower or "markdown" in p_lower or " md" in p_lower:
            fmt = DocumentFormat.TXT

        title = f"Document Deliverable - {prompt[:35]}"
        body, provider, model, degraded = self._document_body(prompt, boundary, scoped_company)
        content_body = body + "\n\n" + self._document_footer(
            prompt=prompt,
            boundary=boundary,
            provider=provider,
            model=model,
            degraded=degraded,
        )

        try:
            doc = document_generator.generate_document(
                title=title,
                format_type=fmt,
                category=(
                    DocumentCategory.COMPANY_DOCUMENT
                    if boundary == "COMPANY"
                    else DocumentCategory.PERSONAL_DOCUMENT
                ),
                content=content_body,
                metadata={
                    "verification_status": "GENERATED",
                    "generated_by": provider or "zonata_text_composer",
                    "model": model,
                    "degraded": degraded,
                },
                storage_boundary=boundary,
                user_id=user_id,
                tenant_id=self.tenant_id,
                company_id=scoped_company,
            )
        except Exception as exc:
            logger.exception("Document generation failed")
            reply = (
                "Document generation failed, so no file exists and nothing is "
                f"available to download. Failure: {type(exc).__name__}."
            )
            self._record_message(
                session_id, user_id, scoped_company, "assistant", boundary, reply,
                intent_category=IntentCategory.DOCUMENT_REQUEST.value,
            )
            return {
                "success": False,
                "reply": reply,
                "intent_category": IntentCategory.DOCUMENT_REQUEST.value,
                "workspace_mode": boundary,
                "routed_to": "DOCUMENT_GENERATOR",
                "execution_state": "BLOCKED",
                "action_card": None,
                "deliverable_card": None,
                "citations": [],
                "timestamp": now,
            }

        deliverable_card = {
            "type": "DOCUMENT",
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "format": doc["format"],
            "download_url": doc["download_url"],
            "sha256": doc["sha256"],
            "storage_boundary": doc["storage_boundary"],
        }

        reply = (
            f"I created a real **{doc['format']}** file: **{doc['title']}** "
            f"({doc['size_bytes']} bytes, SHA-256 `{doc['sha256'][:16]}…`) in the "
            f"{boundary.lower()} workspace. Use the download card to open it."
        )
        if degraded:
            reply += (
                " No language model was reachable, so the file contains a structured "
                "record of the request instead of a model-written draft."
            )

        citations = [{
            "source_type": "INTERNAL",
            "label": "Native Document Generator",
            "verified": True,
        }]
        if provider:
            citations.append({
                "source_type": "MODEL",
                "label": f"{provider}/{model or 'default'}",
                "verified": False,
            })

        if attachments:
            stored = [a for a in attachments if a.get("doc_id")]
            if stored:
                reply += "\nAttached files registered: " + ", ".join(
                    str(a.get("name") or a.get("doc_id")) for a in stored
                ) + "."
            else:
                reply += "\nAttachment metadata arrived without a stored file; re-attach to add it."

        self._record_message(
            session_id, user_id, scoped_company, "assistant", boundary, reply,
            deliverable_card, citations,
            intent_category=IntentCategory.DOCUMENT_REQUEST.value,
        )
        return {
            "success": True,
            "reply": reply,
            "intent_category": IntentCategory.DOCUMENT_REQUEST.value,
            "workspace_mode": boundary,
            "routed_to": "DOCUMENT_GENERATOR",
            "execution_state": "DELIVERED",
            "action_card": None,
            "deliverable_card": deliverable_card,
            "citations": citations,
            "provider": provider,
            "model": model,
            "degraded": degraded,
            "timestamp": now,
        }

    def _document_body(self, prompt: str, boundary: str, company_id: Optional[str] = None):
        """Return (content, provider, model, degraded) for a real document."""
        system = (
            "You are ZONATA AI, producing a document for its Owner. Write the "
            "actual content requested. Do not invent metrics, certifications, "
            "audit seals, or telemetry. If facts are unknown, say so plainly."
        )
        try:
            from core.llm_runtime import llm_runtime
            res = llm_runtime.chat(
                tenant_id=self.tenant_id,
                company_id="" if boundary == "PERSONAL" else (company_id or ""),
                system=system,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1400,
                temperature=0.3,
                intent="document",
            )
            if res.content and not res.degraded:
                return res.content, res.provider, res.model, False
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Document model unavailable: %s", exc)

        return (
            "DOCUMENT RECORD\n"
            "===============\n\n"
            f"Owner request: {prompt}\n"
            f"Storage boundary: {boundary}\n"
            f"Created: {time.ctime()}\n\n"
            "No language model was reachable when this file was created, so this "
            "document is a faithful structured record of the request rather than "
            "a model-written draft. Configure a language model in Settings to "
            "generate full prose content."
        ), None, None, True

    @staticmethod
    def _document_footer(prompt: str, boundary: str, provider: Optional[str],
                         model: Optional[str], degraded: bool) -> str:
        return (
            "---\n"
            f"Created by ZONATA AI for the Owner on {time.ctime()}.\n"
            f"Workspace: {boundary}.\n"
            f"Content source: {(provider + '/' + (model or 'default')) if provider else 'structured record (no model reachable)'}\n"
            f"Model draft: {'no' if degraded else 'yes'}\n"
            "This file is not a certification and carries no audit seal."
        )

    def _handle_meeting_intent(
        self,
        prompt: str,
        company_id: Optional[str],
        user_id: str,
        session_id: str,
        workspace_mode: str = "COMPANY",
    ) -> Dict[str, Any]:
        """Schedule a meeting only when a real provider confirms it."""
        now = time.time()
        boundary = (workspace_mode or "COMPANY").upper()

        if boundary == "PERSONAL":
            reply = (
                "Meeting scheduling is only enabled for the governed company "
                "workspace. Nothing was booked and no external calendar was "
                "contacted for this private request."
            )
            self._record_message(
                session_id, user_id, None, "assistant", "PERSONAL", reply,
                intent_category=IntentCategory.MEETING_REQUEST.value,
            )
            return {
                "success": False,
                "reply": reply,
                "intent_category": IntentCategory.MEETING_REQUEST.value,
                "workspace_mode": "PERSONAL",
                "routed_to": "MEETING_SERVICE",
                "execution_state": "BLOCKED",
                "provider_status": "NOT_ATTEMPTED",
                "action_card": None,
                "deliverable_card": None,
                "citations": [],
                "timestamp": now,
            }

        if not company_id:
            reply = (
                "A meeting needs a verified company context. Nothing was "
                "scheduled and no link was created."
            )
            self._record_message(
                session_id, user_id, None, "assistant", "COMPANY", reply,
                intent_category=IntentCategory.MEETING_REQUEST.value,
            )
            return {
                "success": False,
                "reply": reply,
                "intent_category": IntentCategory.MEETING_REQUEST.value,
                "workspace_mode": "COMPANY",
                "routed_to": "MEETING_SERVICE",
                "execution_state": "BLOCKED",
                "provider_status": "NOT_ATTEMPTED",
                "action_card": None,
                "deliverable_card": None,
                "citations": [],
                "timestamp": now,
            }

        from core.meeting_service import AiCeoMeetingService
        meeting_svc = AiCeoMeetingService(tenant_id=self.tenant_id)

        try:
            sched_res = meeting_svc.schedule_meeting_autonomous(
                prompt=prompt,
                company_id=company_id,
                user_id=user_id,
                platform="GOOGLE_MEET",
                ai_representative_enabled=True,
            )
        except Exception as exc:
            logger.exception("Meeting scheduling failed")
            sched_res = {
                "success": False,
                "provider_status": "BLOCKED",
                "reason": type(exc).__name__,
                "message": "Meeting scheduling failed before any provider confirmation.",
            }

        provider_status = str(sched_res.get("provider_status") or "BLOCKED").upper()
        provider_confirmed = bool(sched_res.get("success")) and provider_status == "CONFIRMED"

        if not provider_confirmed:
            reason = sched_res.get("reason") or "PROVIDER_UNAVAILABLE"
            reply = (
                "I did not schedule the meeting. "
                + str(sched_res.get("message") or "The calendar provider did not confirm the event.")
                + f"\n\nProvider status: {provider_status} ({reason})."
            )
            action_card = {
                "type": "MEETING_INVITE",
                "status": "BLOCKED",
                "provider_status": provider_status,
                "reason": reason,
                "title": sched_res.get("title"),
                "google_meet_url": None,
            }
            citations = [{
                "source_type": "INTERNAL",
                "label": "Calendar provider (unconfirmed)",
                "verified": False,
            }]
            self._record_message(
                session_id, user_id, company_id, "assistant", "COMPANY", reply,
                action_card, citations,
                intent_category=IntentCategory.MEETING_REQUEST.value,
            )
            return {
                "success": False,
                "reply": reply,
                "intent_category": IntentCategory.MEETING_REQUEST.value,
                "workspace_mode": "COMPANY",
                "routed_to": "MEETING_SERVICE",
                "execution_state": "BLOCKED",
                "provider_status": provider_status,
                "action_card": action_card,
                "deliverable_card": None,
                "citations": citations,
                "timestamp": now,
            }

        meet_url = sched_res.get("google_meet_url") or ""
        dial_in = sched_res.get("dial_in") or {}
        lines = [
            "**Meeting confirmed by the calendar provider.**",
            "",
            f"- Session: {sched_res.get('title')}",
            f"- Time: {sched_res.get('scheduled_time_formatted')} ({sched_res.get('duration_minutes')} minutes)",
        ]
        if meet_url:
            lines.append(f"- Video link: {meet_url}")
        else:
            lines.append("- Video link: none was issued by the provider for this event.")
        if dial_in.get("phone"):
            pin = f" (PIN: {dial_in['pin']})" if dial_in.get("pin") else ""
            lines.append(f"- Dial-in: {dial_in['phone']}{pin}")
        if sched_res.get("calendar_event_id"):
            lines.append(f"- Calendar event: {sched_res['calendar_event_id']}")
        if sched_res.get("statutory_disclosure"):
            lines.append(f"- AI participation: {sched_res['statutory_disclosure']}")
        lines.append("")
        lines.append(
            "The briefing dossier was generated from this request and the confirmed "
            "provider details. Invitees receive the disclosure only if the provider "
            "delivered the invitation."
        )
        reply = "\n".join(lines)

        action_card = {
            "type": "MEETING_INVITE",
            "status": "SCHEDULED",
            "provider_status": provider_status,
            "meeting_id": sched_res.get("meeting_id"),
            "title": sched_res.get("title"),
            "google_meet_url": meet_url or None,
            "calendar_event_id": sched_res.get("calendar_event_id"),
            "scheduled_time": sched_res.get("scheduled_time_formatted"),
            "dial_in": dial_in or None,
            "ai_representative_disclosed": bool(sched_res.get("statutory_disclosure")),
            "briefing_dossier_url": sched_res.get("briefing_dossier_url"),
        }
        citations = [{
            "source_type": "INTERNAL",
            "label": f"Calendar provider confirmed ({provider_status})",
            "verified": True,
        }]
        deliverable_card = None
        if sched_res.get("briefing_dossier_url"):
            deliverable_card = {
                "type": "DOCUMENT",
                "doc_id": sched_res.get("briefing_dossier_id"),
                "download_url": sched_res.get("briefing_dossier_url"),
                "title": f"Briefing Dossier - {str(sched_res.get('title'))[:30]}",
                "storage_boundary": "COMPANY",
            }

        self._record_message(
            session_id, user_id, company_id, "assistant", "COMPANY", reply,
            action_card, citations,
            intent_category=IntentCategory.MEETING_REQUEST.value,
        )
        return {
            "success": True,
            "reply": reply,
            "intent_category": IntentCategory.MEETING_REQUEST.value,
            "workspace_mode": "COMPANY",
            "routed_to": "MEETING_SERVICE",
            "execution_state": "COMPLETED",
            "provider_status": provider_status,
            "action_card": action_card,
            "deliverable_card": deliverable_card,
            "citations": citations,
            "timestamp": now,
        }

    # =========================================================================
    # PERSISTENCE & COMPATIBILITY
    # =========================================================================

    def _record_message(
        self,
        session_id: str,
        user_id: str,
        company_id: Optional[str],
        sender: str,
        workspace_mode: str,
        content: str,
        deliverables: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        intent_category: Optional[str] = None,
    ) -> None:
        """Stores a conversation turn, including its classified intent."""
        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        now = time.time()
        try:
            with db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO assistant_messages (
                        message_id, tenant_id, company_id, user_id, session_id,
                        sender, workspace_mode, content, intent_category,
                        deliverables, citations, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        msg_id, self.tenant_id, company_id, user_id, session_id,
                        sender, workspace_mode, content, intent_category,
                        json.dumps(deliverables) if deliverables else None,
                        json.dumps(citations) if citations else None,
                        now
                    )
                )
                conn.commit()
        except Exception:
            logger.exception("Could not persist assistant message")

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves conversational messages for an active session."""
        with db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM assistant_messages
                WHERE tenant_id = ? AND session_id = ?
                ORDER BY timestamp ASC LIMIT ?
                """,
                (self.tenant_id, session_id, limit)
            ).fetchall()

        results = []
        for r in rows:
            deliv = json.loads(r["deliverables"]) if r["deliverables"] else None
            cites = json.loads(r["citations"]) if r["citations"] else []
            results.append({
                "message_id": r["message_id"],
                "sender": r["sender"],
                "workspace_mode": r["workspace_mode"],
                "content": r["content"],
                "deliverables": deliv,
                "citations": cites,
                "timestamp": r["timestamp"]
            })
        return results

    # =========================================================================
    # BACKWARD COMPATIBILITY HANDLERS (Preserves existing contracts)
    # =========================================================================

    def handle_ai_chat(
        self,
        prompt: str,
        company_id: Optional[str] = None,
        user_id: str = "usr_owner",
    ) -> Dict[str, Any]:
        """Legacy AI-chat entry point backed by the same honest runtime.

        Internal citations come from the real search index.  No external source
        is cited unless a retrieval provider returned it, and an unavailable
        language model produces an explicit degraded answer rather than a
        canned success message.
        """
        now = time.time()
        p_lower = (prompt or "").lower()
        cid = (company_id or "").strip() or None
        citations: List[Dict[str, Any]] = []
        context_lines: List[str] = []

        # Internal evidence is limited to the verified company context.
        if cid:
            try:
                with db.get_connection() as conn:
                    comp = conn.execute(
                        "SELECT name FROM companies WHERE company_id = ? AND tenant_id = ?",
                        (cid, self.tenant_id),
                    ).fetchone()
                if comp:
                    context_lines.append(f"Company: {comp['name']} ({cid})")
                    citations.append({
                        "source_type": "INTERNAL",
                        "label": f"ZONATA company registry: {comp['name']}",
                        "verified": True,
                        "scope": f"Company: {cid}",
                    })
            except Exception:
                logger.exception("Company lookup failed")
            try:
                from core.search_engine import GlobalSearchEngine
                search = GlobalSearchEngine.search_all(self.tenant_id, prompt)
                items = search.get("items") or []
                if items:
                    context_lines.append("Internal matches:")
                    for item in items[:5]:
                        context_lines.append(
                            f"- {item.get('category')}: {item.get('title')} "
                            f"({item.get('subtitle') or ''})"
                        )
                    citations.append({
                        "source_type": "INTERNAL",
                        "label": f"ZONATA internal search ({len(items)} matches)",
                        "verified": True,
                        "scope": f"Company: {cid}",
                    })
            except Exception:
                logger.exception("Internal search failed")

        research_query = any(
            w in p_lower
            for w in ("competitor", "market", "industry", "external", "trend", "news")
        )

        answer = ""
        provider = None
        model = None
        degraded = True
        try:
            from core.llm_runtime import llm_runtime
            res = llm_runtime.chat(
                tenant_id=self.tenant_id,
                company_id=cid or "",
                system=(
                    "You are ZONATA AI, the Owner's assistant. Answer concisely. "
                    "Use only the supplied internal context for company facts. "
                    "Do not invent external sources, statistics, or citations. "
                    "If you do not know, say so."
                ),
                messages=[{
                    "role": "user",
                    "content": (
                        (("Internal context:\n" + "\n".join(context_lines) + "\n\n") if context_lines else "")
                        + f"Question: {prompt}"
                    ),
                }],
                max_tokens=900,
                temperature=0.4,
                intent="chat",
            )
            if res.content and not res.degraded:
                answer = res.content
                provider = res.provider
                model = res.model
                degraded = False
                citations.append({
                    "source_type": "MODEL",
                    "label": f"{provider}/{model or 'default'}",
                    "verified": False,
                })
        except Exception as exc:
            logger.warning("AI chat model unavailable: %s", exc)

        if degraded:
            answer = (
                "I could not reach a language model, so I am not going to invent an "
                "answer. No external source was fetched and no action was executed."
            )

        if research_query:
            citations.append({
                "source_type": "EXTERNAL",
                "label": "External research provider (not configured)",
                "verified": False,
                "status": "UNAVAILABLE",
                "scope": "No external retrieval was performed",
            })
            if degraded:
                answer += " External research is also unavailable because no retrieval provider is configured."

        return {
            "reply": answer,
            "citations": citations,
            "deliverable": None,
            "action_card": None,
            "provider": provider,
            "model": model,
            "degraded": degraded,
            "timestamp": now,
            "mode": "AI_CHAT",
        }

    def create_coworker_task(
        self,
        prompt: str,
        workspace_mode: str = "PERSONAL",
        company_id: Optional[str] = None,
        user_id: str = "usr_owner"
    ) -> Dict[str, Any]:
        """Preserves legacy coworker task creation while maintaining 10-stage lifecycle."""
        task_id = f"cwk_{uuid.uuid4().hex[:8]}"
        now = time.time()
        prompt_lower = prompt.lower()

        if any(w in prompt_lower for w in ["pay", "buy", "transfer", "bank", "card", "spend"]):
            permission_tier = "FINANCIAL_ACTION"
            requires_approval = True
            target_outcome = "Authorize and execute financial transaction."
        elif any(w in prompt_lower for w in ["password", "token", "credential", "login", "secret"]):
            permission_tier = "CREDENTIAL_ACCESS"
            requires_approval = True
            target_outcome = "Retrieve credential handle within isolated vault."
        elif any(w in prompt_lower for w in ["delete", "remove", "overwrite", "write", "modify file"]):
            permission_tier = "FILE_WRITE"
            requires_approval = True
            target_outcome = "Perform sandboxed file system mutation."
        else:
            permission_tier = "SAFE_BROWSE"
            requires_approval = False
            target_outcome = "Read-only inspection and telemetry synthesis."

        initial_status = "AWAITING_APPROVAL" if requires_approval else "PLANNING"
        approval_status = "PENDING" if requires_approval else "AUTO"

        execution_log = [
            {"stage": "INITIATED", "timestamp": now, "detail": f"Task created in {workspace_mode} workspace."},
            {"stage": "PLANNING", "timestamp": now + 0.1, "detail": f"Synthesized plan for target outcome: {target_outcome}."}
        ]

        if requires_approval:
            execution_log.append({
                "stage": "AWAITING_APPROVAL",
                "timestamp": now + 0.2,
                "detail": f"Sensitive permission tier '{permission_tier}' requires Host authorization."
            })
        else:
            # A safe tier does not mean the work happened.  No host executor has
            # reported back, so the task stays queued rather than auto-completing.
            execution_log.append({
                "stage": "QUEUED",
                "timestamp": now + 0.2,
                "detail": (
                    "No host executor is attached, so this task has not run. "
                    "Completion requires a verified execution receipt."
                ),
            })

        # A receipt only exists after a real executor reports verified output.
        receipt_id = None

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO coworker_tasks (
                    task_id, tenant_id, company_id, user_id, workspace_mode,
                    prompt, target_outcome, status, permission_tier,
                    approval_status, execution_log, receipt_id, created_at,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id, self.tenant_id, company_id, user_id, workspace_mode,
                    prompt, target_outcome, initial_status, permission_tier,
                    approval_status, json.dumps(execution_log), receipt_id, now,
                    None
                )
            )
            conn.commit()

        return self.get_coworker_task(task_id)

    def approve_coworker_task(self, task_id: str, approved: bool = True) -> Dict[str, Any]:
        task = self.get_coworker_task(task_id)
        if not task:
            raise ValueError("Coworker task not found")

        now = time.time()
        log = task["execution_log"]

        if approved:
            log.extend([
                {"stage": "APPROVED", "timestamp": now, "detail": "Host authorised the gated action."},
                {
                    "stage": "QUEUED",
                    "timestamp": now,
                    "detail": (
                        "Authorised, but not executed: no host executor has reported "
                        "a verified result yet."
                    ),
                },
            ])
            status = "APPROVED"
            approval_status = "APPROVED"
            completed_at = None
        else:
            log.append({"stage": "REVERTED", "timestamp": now, "detail": "Host denied authorization for sensitive action."})
            status = "REVERTED"
            approval_status = "DENIED"
            completed_at = now

        with db.get_connection() as conn:
            conn.execute(
                """
                UPDATE coworker_tasks SET
                    status = ?, approval_status = ?, execution_log = ?, completed_at = ?
                WHERE task_id = ? AND tenant_id = ?
                """,
                (status, approval_status, json.dumps(log), completed_at, task_id, self.tenant_id)
            )
            conn.commit()

        return self.get_coworker_task(task_id)

    def get_coworker_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            r = conn.execute(
                "SELECT * FROM coworker_tasks WHERE task_id = ? AND tenant_id = ?",
                (task_id, self.tenant_id)
            ).fetchone()
            if not r:
                return None
            log = []
            if r["execution_log"]:
                try:
                    log = json.loads(r["execution_log"])
                except Exception:
                    pass
            return {
                "task_id": r["task_id"],
                "tenant_id": r["tenant_id"],
                "company_id": r["company_id"],
                "user_id": r["user_id"],
                "workspace_mode": r["workspace_mode"],
                "prompt": r["prompt"],
                "target_outcome": r["target_outcome"],
                "status": r["status"],
                "permission_tier": r["permission_tier"],
                "approval_status": r["approval_status"],
                "execution_log": log,
                "receipt_id": r["receipt_id"],
                "created_at": r["created_at"],
                "completed_at": r["completed_at"]
            }

    def list_coworker_tasks(
        self,
        workspace_mode: Optional[str] = None,
        limit: int = 20,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM coworker_tasks WHERE tenant_id = ?"
        params: List[Any] = [self.tenant_id]
        if workspace_mode and workspace_mode != "all":
            query += " AND workspace_mode = ?"
            params.append(workspace_mode)
            if workspace_mode == "PERSONAL" and user_id:
                query += " AND user_id = ?"
                params.append(user_id)
        elif user_id:
            # Company tasks are visible to the company workspace; personal tasks
            # stay scoped to their owner.
            query += " AND (workspace_mode = 'COMPANY' OR user_id = ?)"
            params.append(user_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with db.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()

        results = []
        for r in rows:
            log = []
            if r["execution_log"]:
                try:
                    log = json.loads(r["execution_log"])
                except Exception:
                    pass
            results.append({
                "task_id": r["task_id"],
                "workspace_mode": r["workspace_mode"],
                "prompt": r["prompt"],
                "target_outcome": r["target_outcome"],
                "status": r["status"],
                "permission_tier": r["permission_tier"],
                "approval_status": r["approval_status"],
                "execution_log": log,
                "receipt_id": r["receipt_id"],
                "created_at": r["created_at"]
            })
        return results
