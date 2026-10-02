"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
V7 Architecture — SOP Ingestion & Operational Policy Compiler
Converts raw corporate SOPs, policy manuals, and process documentation
into machine-enforceable employee specifications with full source provenance.

Constitutional Invariants:
  PROVENANCE_TRACKING (Every generated rule traceable to source text)
  NO_HALLUCINATED_POLICIES (Ambiguous statements marked AMBIGUOUS_REQUIRES_REVIEW)
  DO_NOT_DUMP_DOC_INTO_PROMPT (Structure into discrete policy & knowledge references)
"""

import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("zonata.v7.sop_compiler")

@dataclass
class PolicyRuleProvenance:
    rule_id: str
    source_doc: str
    source_section: str
    extracted_statement: str
    interpreted_policy: str
    confidence_score: float
    status: str                         # VALIDATED, AMBIGUOUS_REQUIRES_REVIEW, REJECTED
    rule_type: str                      # CONSTRAINT, WORKFLOW, AUTHORITY, ESCALATION, TOOL, KPI

@dataclass
class SOPCompilationResult:
    compilation_id: str
    document_title: str
    extracted_role: str
    extracted_department: str
    responsibilities: List[str]
    workflows: List[Dict[str, Any]]
    authorities: List[Dict[str, Any]]
    constraints: List[str]
    escalation_triggers: List[Dict[str, Any]]
    required_tools: List[str]
    suggested_kpis: List[Dict[str, Any]]
    suggested_kras: List[Dict[str, Any]]
    provenance_chain: List[PolicyRuleProvenance]
    ambiguities_requiring_review: List[Dict[str, Any]]
    compilation_confidence: float

class SOPPolicyCompiler:
    """
    Parses unstructured and semi-structured business SOPs into structured
    operational rules, KRA/KPI mappings, tool permissions, and escalation policies.
    """
    def compile_sop_text(self, document_title: str, text: str, default_department: str = "OPERATIONS") -> SOPCompilationResult:
        """
        Executes the multi-stage interpretation pipeline on raw SOP document text.
        """
        compilation_id = f"sop_cmp_{uuid.uuid4().hex[:12]}"
        sections = self._parse_sections(text)

        provenance_chain: List[PolicyRuleProvenance] = []
        ambiguities: List[Dict[str, Any]] = []
        responsibilities: List[str] = []
        workflows: List[Dict[str, Any]] = []
        authorities: List[Dict[str, Any]] = []
        constraints: List[str] = []
        escalation_triggers: List[Dict[str, Any]] = []
        required_tools: Set[str] = set()
        suggested_kpis: List[Dict[str, Any]] = []
        suggested_kras: List[Dict[str, Any]] = []

        extracted_role = "OPERATIONAL_SPECIALIST"
        extracted_dept = default_department

        for sec_title, sec_content in sections.items():
            lines = [l.strip() for l in sec_content.splitlines() if l.strip()]
            sec_lower = sec_title.lower()

            # 1. Role & Department Extraction
            for line in lines:
                m = re.search(r"(?:role|position|title):\s*([A-Za-z0-9\s\-]+)", line, re.IGNORECASE)
                if m:
                    extracted_role = m.group(1).strip()
                m_dept = re.search(r"department:\s*([A-Za-z0-9\s\-]+)", line, re.IGNORECASE)
                if m_dept:
                    extracted_dept = m_dept.group(1).strip()

            # 2. Responsibilities & Workflows
            if "responsibilit" in sec_lower or "duty" in sec_lower or "scope" in sec_lower:
                for line in lines:
                    cleaned = re.sub(r"^[\*\-\d\.\)]+\s*", "", line)
                    if len(cleaned) > 5:
                        responsibilities.append(cleaned)
                        rule = PolicyRuleProvenance(
                            rule_id=f"rul_{uuid.uuid4().hex[:8]}",
                            source_doc=document_title,
                            source_section=sec_title,
                            extracted_statement=line,
                            interpreted_policy=f"EXECUTE_RESPONSIBILITY: {cleaned}",
                            confidence_score=0.95,
                            status="VALIDATED",
                            rule_type="WORKFLOW"
                        )
                        provenance_chain.append(rule)

            # 3. Process & Workflow Steps
            if "procedure" in sec_lower or "process" in sec_lower or "workflow" in sec_lower or "step" in sec_lower:
                wf_steps = []
                for line in lines:
                    step_text = re.sub(r"^[\*\-\d\.\)]+\s*", "", line)
                    if step_text:
                        wf_steps.append(step_text)
                if wf_steps:
                    workflows.append({
                        "workflow_name": sec_title,
                        "steps": wf_steps
                    })

            # 4. Authority, Approvals, & Constraints
            if "authority" in sec_lower or "approval" in sec_lower or "limit" in sec_lower or "rule" in sec_lower:
                for line in lines:
                    # Detect spending or discount ceiling
                    spend_match = re.search(r"(?:spend|discount|refund|transfer|limit|ceiling|up to)[:\s]+(?:₹|\$|USD)?\s*([0-9,]+)", line, re.IGNORECASE)
                    if spend_match:
                        raw_amt = float(spend_match.group(1).replace(",", ""))
                        authorities.append({
                            "type": "FINANCIAL_CEILING",
                            "limit_usd": raw_amt,
                            "condition": line
                        })
                        provenance_chain.append(PolicyRuleProvenance(
                            rule_id=f"rul_{uuid.uuid4().hex[:8]}",
                            source_doc=document_title,
                            source_section=sec_title,
                            extracted_statement=line,
                            interpreted_policy=f"MAX_FINANCIAL_THRESHOLD <= {raw_amt}",
                            confidence_score=0.98,
                            status="VALIDATED",
                            rule_type="AUTHORITY"
                        ))
                    elif re.search(r"\b(must not|prohibited|forbidden|never)\b", line.lower()):
                        cleaned_c = re.sub(r"^[\*\-\d\.\)]+\s*", "", line)
                        constraints.append(cleaned_c)
                        provenance_chain.append(PolicyRuleProvenance(
                            rule_id=f"rul_{uuid.uuid4().hex[:8]}",
                            source_doc=document_title,
                            source_section=sec_title,
                            extracted_statement=line,
                            interpreted_policy=f"HARD_CONSTRAINT: {cleaned_c}",
                            confidence_score=0.95,
                            status="VALIDATED",
                            rule_type="CONSTRAINT"
                        ))
                    elif "as deemed appropriate" in line.lower() or "whenever necessary" in line.lower() or "at discretion" in line.lower():
                        # Ambiguous discretion rule: DO NOT GUESS
                        rule = PolicyRuleProvenance(
                            rule_id=f"rul_{uuid.uuid4().hex[:8]}",
                            source_doc=document_title,
                            source_section=sec_title,
                            extracted_statement=line,
                            interpreted_policy="AMBIGUOUS_DISCRETIONARY_INSTRUCTION",
                            confidence_score=0.40,
                            status="AMBIGUOUS_REQUIRES_REVIEW",
                            rule_type="AUTHORITY"
                        )
                        provenance_chain.append(rule)
                        ambiguities.append({
                            "source_section": sec_title,
                            "statement": line,
                            "reason": "Discretionary language detected without clear numerical boundary or supervisor approval trigger."
                        })

            # 5. Escalation Matrix
            if "escalat" in sec_lower or "incident" in sec_lower or "exception" in sec_lower:
                for line in lines:
                    cleaned_esc = re.sub(r"^[\*\-\d\.\)]+\s*", "", line)
                    escalation_triggers.append({
                        "trigger": cleaned_esc,
                        "escalate_to": "SUPERVISOR"
                    })
                    provenance_chain.append(PolicyRuleProvenance(
                        rule_id=f"rul_{uuid.uuid4().hex[:8]}",
                        source_doc=document_title,
                        source_section=sec_title,
                        extracted_statement=line,
                        interpreted_policy=f"ESCALATE_IF: {cleaned_esc}",
                        confidence_score=0.90,
                        status="VALIDATED",
                        rule_type="ESCALATION"
                    ))

            # 6. Tools & Systems Mentioned
            tool_keywords = {
                "pms": "PMS_HOTEL_CONNECTOR",
                "booking": "BOOKING_ENGINE_API",
                "salesforce": "SALESFORCE_CRM",
                "jira": "JIRA_TICKETS",
                "slack": "SLACK_NOTIFIER",
                "spreadsheet": "SPREADSHEET_ENGINE",
                "analytics": "ANALYTICS_QUERY_TOOL",
                "email": "CORPORATE_EMAIL_CLIENT",
                "terminal": "BASH_TERMINAL_SANDBOX"
            }
            for kw, tool_id in tool_keywords.items():
                if kw in sec_content.lower():
                    required_tools.add(tool_id)

            # 7. KPI / Metrics Extraction
            if "kpi" in sec_lower or "metric" in sec_lower or "target" in sec_lower:
                for line in lines:
                    m_kpi = re.search(r"([A-Za-z\s]+)[:\-]+([0-9\.\%\$\₹A-Za-z\s\/]+)", line)
                    if m_kpi:
                        kpi_name = m_kpi.group(1).strip()
                        target_val = m_kpi.group(2).strip()
                        suggested_kpis.append({
                            "name": kpi_name,
                            "target": target_val,
                            "unit": "%" if "%" in target_val else "CURRENCY" if ("₹" in target_val or "$" in target_val) else "UNITS",
                            "verification_method": "LEDGER_RECONCILIATION"
                        })

        # Calculate overall compilation confidence
        if provenance_chain:
            avg_conf = sum(p.confidence_score for p in provenance_chain) / len(provenance_chain)
        else:
            avg_conf = 0.50

        return SOPCompilationResult(
            compilation_id=compilation_id,
            document_title=document_title,
            extracted_role=extracted_role,
            extracted_department=extracted_dept,
            responsibilities=responsibilities,
            workflows=workflows,
            authorities=authorities,
            constraints=constraints,
            escalation_triggers=escalation_triggers,
            required_tools=sorted(list(required_tools)),
            suggested_kpis=suggested_kpis,
            suggested_kras=suggested_kras,
            provenance_chain=provenance_chain,
            ambiguities_requiring_review=ambiguities,
            compilation_confidence=round(avg_conf, 2)
        )

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Split document text into titled sections based on Markdown or common headers."""
        sections: Dict[str, str] = {}
        current_title = "Overview"
        current_lines: List[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Match Markdown headers (# Section) or uppercase headers (SECTION:)
            header_match = re.match(r"^(?:#{1,4}\s+|[A-Z\s]{3,}:)\s*(.+)$", stripped)
            if header_match:
                if current_lines:
                    sections[current_title] = "\n".join(current_lines)
                    current_lines = []
                current_title = header_match.group(1).strip()
            else:
                current_lines.append(stripped)

        if current_lines:
            sections[current_title] = "\n".join(current_lines)

        return sections

sop_compiler = SOPPolicyCompiler()
