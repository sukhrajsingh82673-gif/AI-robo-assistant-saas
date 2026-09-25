"""
ZONATA Universal AI CEO — Adaptive Discovery Interview Engine
Conducts targeted, context-aware interviews with company owners to establish
operational truth without exhausting questionnaires, respecting skips and deferrals.
"""

from typing import Dict, List, Optional, Any, Tuple
import json
import time
import uuid

from core.db import db
from zonata.models import (
    EpistemicState,
    EntityType,
    RelationType,
    InterviewQuestion,
    InterviewExchange,
    AnswerType,
    DiscoveryState
)
from zonata.knowledge_graph import CompanyKnowledgeGraph
from zonata.discovery import CompanyDiscoveryEngine

# Key strategic dimensions required for full organization design
CORE_DIMENSIONS = [
    {
        "id": "DIM_IDENTITY",
        "category": "IDENTITY",
        "weight": 0.15,
        "label": "Company identity, core business model, and operational locations",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.COMPANY)) > 0
    },
    {
        "id": "DIM_REVENUE",
        "category": "REVENUE",
        "weight": 0.15,
        "label": "Primary revenue streams, customer pricing model, and billing mechanism",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.REVENUE_STREAM)) > 0 or len(kg.find_nodes_by_type(EntityType.SERVICE)) > 0 or len(kg.find_nodes_by_type(EntityType.PRODUCT)) > 0
    },
    {
        "id": "DIM_OPERATIONS",
        "category": "OPERATIONS",
        "weight": 0.15,
        "label": "Core operational processes, inventory/capacity, and physical or digital workflows",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.PROCESS)) > 0 or len(kg.find_nodes_by_type(EntityType.ASSET)) > 0 or len(kg.find_nodes_by_type(EntityType.MACHINE)) > 0
    },
    {
        "id": "DIM_SYSTEMS",
        "category": "SYSTEMS",
        "weight": 0.15,
        "label": "Connected systems (PMS, ERP, CRM, POS, Accounting, Tools)",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.SYSTEM)) > 0 or len(kg.find_nodes_by_type(EntityType.APPLICATION)) > 0
    },
    {
        "id": "DIM_FINANCIALS",
        "category": "FINANCE",
        "weight": 0.15,
        "label": "Financial health baseline (monthly run-rate, costs, margins, cash runway)",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.FINANCIAL_ACCOUNT)) > 0 or len(kg.find_nodes_by_type(EntityType.EXPENSE)) > 0
    },
    {
        "id": "DIM_WORKFORCE",
        "category": "WORKFORCE",
        "weight": 0.10,
        "label": "Existing human workforce, outsourced partners, and major operational bottlenecks",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.PERSON)) > 0
    },
    {
        "id": "DIM_COMPETITIVE",
        "category": "COMPETITIVE",
        "weight": 0.05,
        "label": "Competitors, market positioning, and direct alternatives",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.COMPETITOR)) > 0
    },
    {
        "id": "DIM_GOALS_RISKS",
        "category": "GOALS_RISKS",
        "weight": 0.10,
        "label": "Immediate operational goals, quarterly targets, and primary operational risks",
        "detect": lambda kg: len(kg.find_nodes_by_type(EntityType.GOAL)) > 0 or len(kg.find_nodes_by_type(EntityType.RISK)) > 0
    }
]

QUESTION_TEMPLATES = {
    "IDENTITY": [
        InterviewQuestion(
            question_id="q_identity_model",
            category="IDENTITY",
            text="Could you describe what this company does, its primary industry, and where its main operations or properties are located?",
            context_reason="The CEO needs fundamental business context before determining organizational requirements.",
            priority=10,
            suggested_answers=["We operate a 45-room boutique hotel and resort in Goa", "We are a B2B SaaS platform for logistics companies", "We manufacture precision CNC automotive components in Pune"]
        ),
        InterviewQuestion(
            question_id="q_identity_hours",
            category="IDENTITY",
            text="What are your standard operating hours, and do you require 24/7 continuous autonomous monitoring or shift-based supervision?",
            context_reason="Determines whether night shift agents and 24x7 autonomous handovers are required.",
            priority=8,
            suggested_answers=["24/7 continuous operations", "Regular business hours (9 AM - 6 PM) with weekend on-call", "Two 8-hour production shifts"]
        )
    ],
    "SYSTEMS": [
        InterviewQuestion(
            question_id="q_systems_core",
            category="SYSTEMS",
            text="What core software systems do you currently rely on (e.g. PMS, ERP, CRM, POS, Accounting software like QuickBooks or Tally)?",
            context_reason="Identifies which system connectors and software bridges the AI organization must interface with.",
            priority=9,
            suggested_answers=["Cloudbeds PMS and Tally Prime", "Salesforce CRM, Stripe, and QuickBooks Online", "SAP ERP and custom internal database"]
        ),
        InterviewQuestion(
            question_id="q_systems_pricing",
            category="SYSTEMS",
            text="How is pricing or quotation currently calculated and updated in your system? Is it manual or automated?",
            context_reason="Determines if a specialized Revenue Management Agent or dynamic pricing workflow is needed.",
            priority=7,
            suggested_answers=["Manual rate updates by our manager", "Automated rules based on occupancy", "Custom quoting tool integrated with CRM"]
        )
    ],
    "REVENUE": [
        InterviewQuestion(
            question_id="q_revenue_streams",
            category="REVENUE",
            text="What are your main revenue streams and what is your average transaction or booking value?",
            context_reason="Needed to align financial KPIs and build revenue causality chains.",
            priority=9,
            suggested_answers=["Room bookings (70%) and F&B / events (30%)", "Monthly recurring software subscriptions ($99/mo)", "Direct B2B purchase orders from enterprise clients"]
        )
    ],
    "OPERATIONS": [
        InterviewQuestion(
            question_id="q_operations_bottlenecks",
            category="OPERATIONS",
            text="What are the biggest operational bottlenecks or repetitive administrative tasks consuming your team's time today?",
            context_reason="Allows the CEO to design specialized workforce roles to eliminate highest-friction operational costs.",
            priority=8,
            suggested_answers=["OTA booking reconciliation and customer message replies", "Manual invoice generation and payment follow-ups", "Inventory tracking and supplier purchase order delays"]
        )
    ],
    "FINANCE": [
        InterviewQuestion(
            question_id="q_finance_baseline",
            category="FINANCE",
            text="What is your approximate monthly revenue and operating cost baseline? (Estimates are fine, or say 'Skip' if confidential)",
            context_reason="Calibrates executive spending limits, employee budget caps, and Company Health score.",
            priority=7,
            suggested_answers=["Roughly ₹40-50 lakh monthly revenue with ₹30 lakh operating cost", "About $25k MRR and $15k burn rate", "Skip"]
        )
    ],
    "WORKFORCE": [
        InterviewQuestion(
            question_id="q_workforce_structure",
            category="WORKFORCE",
            text="What human roles currently exist in the business (e.g., General Manager, Receptionist, Sales Reps, Engineers), and what should AI handle vs human staff?",
            context_reason="Helps the CEO design the reporting hierarchy and human-AI handoff boundaries.",
            priority=8,
            suggested_answers=["GM and 10 on-site staff; AI should handle guest comms, pricing, and bookkeeping", "3 founders + 4 developers; AI should handle sales outreach, QA, and DevOps"]
        )
    ],
    "COMPETITIVE": [
        InterviewQuestion(
            question_id="q_competitive_landscape",
            category="COMPETITIVE",
            text="Who are your top 2-3 direct competitors, and how does your offering differentiate from theirs?",
            context_reason="Initializes competitive intelligence tracking without accessing unauthorized systems.",
            priority=6,
            suggested_answers=["Competitor A and Competitor B nearby; we differentiate on premium guest experience", "Competitor X; we differentiate on lower price and faster onboarding"]
        )
    ],
    "GOALS_RISKS": [
        InterviewQuestion(
            question_id="q_goals_risks_quarter",
            category="GOALS_RISKS",
            text="What is your single most important business objective for the next quarter, and what is the biggest risk that could prevent it?",
            context_reason="The CEO generates a mission-first workforce directly tied to your primary strategic objective.",
            priority=9,
            suggested_answers=["Increase direct bookings by 30% to reduce OTA commission fees", "Reach $50k MRR while maintaining >99.9% uptime", "Reduce component defect rate below 0.1%"]
        )
    ]
}

class CEODiscoveryInterview:
    """
    Adaptive questioning controller for the CEO discovery phase.
    """

    def __init__(self):
        self.discovery_engine = CompanyDiscoveryEngine()

    def calculate_completeness(self, tenant_id: str, company_id: str) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Evaluates current Knowledge Graph against required core dimensions.
        Returns: (completeness_score [0.0 - 1.0], missing_information list)
        """
        kg = CompanyKnowledgeGraph(tenant_id, company_id)
        # Also check answered or skipped interview questions
        with db.get_connection() as conn:
            answered_categories = set(
                row["category"]
                for row in conn.execute(
                    "SELECT DISTINCT category FROM zonata_interviews WHERE tenant_id = ? AND company_id = ? AND answer_type IN ('ANSWERED', 'SKIPPED', 'BEST_EVIDENCE')",
                    (tenant_id, company_id)
                ).fetchall()
            )

        score = 0.0
        missing: List[Dict[str, Any]] = []

        for dim in CORE_DIMENSIONS:
            detected = dim["detect"](kg) or (dim["category"] in answered_categories)
            if detected:
                score += dim["weight"]
            else:
                missing.append({
                    "id": dim["id"],
                    "category": dim["category"],
                    "label": dim["label"],
                    "weight": dim["weight"]
                })

        return min(1.0, score), missing

    def get_next_question(self, tenant_id: str, company_id: str) -> Optional[InterviewQuestion]:
        """
        Adaptively chooses the next most valuable question for the owner.
        Considers already asked questions, skipped topics, and missing dimensions.
        """
        with db.get_connection() as conn:
            asked_qids = set(
                row["question_id"]
                for row in conn.execute(
                    "SELECT question_id FROM zonata_interviews WHERE tenant_id = ? AND company_id = ?",
                    (tenant_id, company_id)
                ).fetchall()
            )

        # Calculate current knowledge gaps
        score, missing = self.calculate_completeness(tenant_id, company_id)
        if score >= 0.85 or not missing:
            return None # Sufficient context achieved to proceed to Organization Design!

        # Sort missing dimensions by weight descending
        sorted_missing = sorted(missing, key=lambda m: m["weight"], reverse=True)

        for m in sorted_missing:
            cat = m["category"]
            candidates = QUESTION_TEMPLATES.get(cat, [])
            for q in sorted(candidates, key=lambda x: x.priority, reverse=True):
                if q.question_id not in asked_qids:
                    return q

        # Fallback to any remaining unasked template
        for cat, questions in QUESTION_TEMPLATES.items():
            for q in sorted(questions, key=lambda x: x.priority, reverse=True):
                if q.question_id not in asked_qids:
                    return q

        return None

    def submit_answer(
        self,
        tenant_id: str,
        company_id: str,
        question_id: str,
        answer_text: str
    ) -> Dict[str, Any]:
        """
        Processes owner's response to an interview question.
        Supports:
        - Normal answer (extracts facts and updates graph)
        - 'Skip' (records gap without penalty)
        - 'Not available' (marks unavailable)
        - 'Ask later' (defers)
        - 'Use your best available evidence' (records estimate with EpistemicState.ESTIMATE)
        """
        session = self.discovery_engine.get_or_create_session(tenant_id, company_id)
        now = time.time()
        lower_ans = answer_text.strip().lower()

        # Classify answer type
        if lower_ans.startswith("skip") or "skip" in lower_ans or lower_ans in ("pass", "next"):
            ans_type = AnswerType.SKIPPED
        elif any(w in lower_ans for w in ["not available", "don't know", "n/a", "no data"]):
            ans_type = AnswerType.NOT_AVAILABLE
        elif any(w in lower_ans for w in ["ask later", "ask me later", "later", "defer"]):
            ans_type = AnswerType.ASK_LATER
        elif any(w in lower_ans for w in ["best available evidence", "best evidence", "use your best"]):
            ans_type = AnswerType.BEST_EVIDENCE
        else:
            ans_type = AnswerType.ANSWERED

        # Find question template details
        q_obj = None
        for cat_list in QUESTION_TEMPLATES.values():
            for q in cat_list:
                if q.question_id == question_id:
                    q_obj = q
                    break
            if q_obj:
                break

        if not q_obj:
            q_obj = InterviewQuestion(
                question_id=question_id,
                category="GENERAL",
                text=f"Question {question_id}",
                context_reason="General operational discovery"
            )

        extracted_findings = []

        if ans_type == AnswerType.ANSWERED:
            extracted_findings = self.discovery_engine.ingest_owner_statement(
                tenant_id=tenant_id,
                company_id=company_id,
                statement=answer_text,
                source=f"INTERVIEW:{question_id}",
                session_id=session.session_id
            )
        elif ans_type == AnswerType.BEST_EVIDENCE:
            # Generate bounded heuristic estimate tagged as ESTIMATE
            f = self.discovery_engine.record_finding(
                tenant_id=tenant_id,
                company_id=company_id,
                entity_type=EntityType.GOAL,
                entity_id=f"est_{question_id}_{company_id}",
                attribute="inferred_parameter",
                value=f"AI Inferred estimate based on industry benchmarks for {q_obj.category}",
                source="AI_BENCHMARK_ESTIMATE",
                source_type="INFERRED",
                evidence=f"Owner requested best available evidence for {question_id}",
                epistemic_state=EpistemicState.ESTIMATE,
                confidence=0.65,
                session_id=session.session_id
            )
            extracted_findings.append(f)
        elif ans_type == AnswerType.ASK_LATER:
            session.deferred_topics.append(q_obj.text)

        exchange_id = f"exch_{uuid.uuid4().hex[:10]}"

        # Persist exchange to database
        with db.get_connection() as conn:
            conn.execute("""
                INSERT INTO zonata_interviews (
                    exchange_id, session_id, tenant_id, company_id, question_id,
                    category, question_text, context_reason, answer_text, answer_type,
                    extracted_facts, asked_at, answered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exchange_id, session.session_id, tenant_id, company_id, question_id,
                q_obj.category, q_obj.text, q_obj.context_reason, answer_text,
                ans_type.value, json.dumps([f.to_dict() for f in extracted_findings]),
                now, now
            ))
            conn.commit()

        # Recalculate completeness
        new_score, missing = self.calculate_completeness(tenant_id, company_id)
        ready_for_org = new_score >= 0.70 or len(missing) == 0

        # Update session
        with db.get_connection() as conn:
            new_status = "READY_FOR_ORG" if ready_for_org else "IN_PROGRESS"
            conn.execute("""
                UPDATE zonata_discovery_sessions
                SET completeness_score = ?, missing_info = ?, deferred_topics = ?, status = ?, updated_at = ?
                WHERE session_id = ?
            """, (
                new_score, json.dumps(missing), json.dumps(session.deferred_topics),
                new_status, now, session.session_id
            ))
            conn.commit()

        next_q = self.get_next_question(tenant_id, company_id) if not ready_for_org else None

        return {
            "exchange_id": exchange_id,
            "session_id": session.session_id,
            "answer_type": ans_type.value,
            "facts_extracted": len(extracted_findings),
            "completeness_score": round(new_score, 4),
            "completeness_pct": f"{int(new_score * 100)}%",
            "missing_information": missing,
            "is_ready_for_org": ready_for_org,
            "next_question": next_q.to_dict() if next_q else None
        }

    def get_interview_history(self, tenant_id: str, company_id: str) -> List[Dict[str, Any]]:
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM zonata_interviews WHERE tenant_id = ? AND company_id = ? ORDER BY asked_at ASC",
                (tenant_id, company_id)
            ).fetchall()
            return [
                {
                    "exchange_id": r["exchange_id"],
                    "question_id": r["question_id"],
                    "category": r["category"],
                    "question_text": r["question_text"],
                    "context_reason": r["context_reason"],
                    "answer_text": r["answer_text"],
                    "answer_type": r["answer_type"],
                    "asked_at": r["asked_at"],
                    "answered_at": r["answered_at"]
                }
                for r in rows
            ]
