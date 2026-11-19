"""
RoboAssistant Company OS — Operational Skills & SOPs Catalog
Provides deterministic, standard operating procedures (SOPs) for autonomous agents.

Each skill is an executable *contract*: it declares the minimum authority tier,
the risk class, the inputs it needs, the checks that must pass and the evidence
that must exist before an agent or employee may act on the result. The
``skill_arena`` engine enforces these fields; the catalog is not just prose.

Where a skill maps to an installed agent operating protocol, ``protocol_source``
records the mapping. The runtime does not claim to execute a coding-agent skill
inside the product; it applies the protocol's rules to corporate decisions.
"""

from typing import Dict, List, Any, Optional

SKILLS_CATALOG: Dict[str, Dict[str, Any]] = {
    "task-planning": {
        "id": "task-planning",
        "name": "Autonomous Task Planning & Decomposition",
        "category": "Orchestration",
        "description": "Standard procedure for decomposing high-level company goals into unambiguous, actionable child tasks with clear acceptance criteria.",
        "author": "Enterprise Core",
        "version": "2.5.0",
        "authority_floor": "MANAGER",
        "risk_class": "LOW",
        "required_inputs": ["objective"],
        "sop_rules": [
            "Never create child tasks with descriptions that say 'see parent' — every task must be self-contained and independently executable.",
            "Identify and declare all DAG dependencies explicitly before assigning tasks to prevent execution deadlocks.",
            "Formulate specific, testable acceptance criteria for each subtask so verification can be 100% automated.",
            "If an execution path requires external capital spend or destructive mutation, insert an explicit 'pending_approval' gate."
        ],
        "checks": [
            "objective_is_specific",
            "every_task_has_acceptance_criteria",
            "dependencies_declared",
            "approval_gate_for_spend_or_destructive_action"
        ],
        "applicable_roles": ["Chief Executive Officer (CEO)", "Chief Technology Officer (CTO)", "Lead Product Manager"],
        "protocol_source": "GSD-style spec decomposition",
    },
    "issue-triage": {
        "id": "issue-triage",
        "name": "Deterministic Issue Triage & Prioritization",
        "category": "Operations",
        "description": "Lifecycle contract for processing incoming tasks, assigning priority buckets, and ensuring single-worker task locks.",
        "author": "Enterprise Core",
        "version": "1.9.0",
        "authority_floor": "EMPLOYEE",
        "risk_class": "LOW",
        "required_inputs": ["issue"],
        "sop_rules": [
            "Process tasks strictly in order: in_progress tasks first, then in_review, then todo.",
            "Skip 'blocked' tasks until upstream dependencies are satisfied.",
            "Always acquire an atomic lease (checkout) with run ID before commencing work; halt immediately on 409 Conflict.",
            "Update issue status incrementally with evidence deltas to preserve an immutable timeline."
        ],
        "checks": [
            "priority_is_one_of_allowed_values",
            "blocked_issue_not_started",
            "lease_required_before_execution"
        ],
        "applicable_roles": ["All Autonomous Agents"],
        "protocol_source": "Enterprise operations",
    },
    "board-reporting": {
        "id": "board-reporting",
        "name": "Executive Board Reporting & Approval Escalation",
        "category": "Governance",
        "description": "SOP for compiling high-signal briefings, unblocking stalled initiatives, and presenting structured proposals for owner sign-off.",
        "author": "Enterprise Core",
        "version": "2.2.0",
        "authority_floor": "EXECUTIVE",
        "risk_class": "MEDIUM",
        "required_inputs": ["topic"],
        "sop_rules": [
            "Synthesize outcomes into three core metrics: Capital efficiency, SLA completion rate, and verified truth delta.",
            "Present decisions in actionable multiple-choice format with clear risk/benefit analysis.",
            "Highlight budget ceilings and notify the board immediately when spending reaches 80% of threshold."
        ],
        "checks": [
            "metrics_are_computed_from_rows",
            "recommendation_has_risk_label",
            "spend_threshold_disclosed"
        ],
        "applicable_roles": ["Chief Executive Officer (CEO)", "Chief Operating Officer (COO)"],
        "protocol_source": "Enterprise governance",
    },
    "code-review-gate": {
        "id": "code-review-gate",
        "name": "Automated Code Review & Integrity Gate",
        "category": "Engineering",
        "description": "Enforces strict static verification, security scanning, and test pass requirements before accepting software changes.",
        "author": "Enterprise Core",
        "version": "3.1.0",
        "authority_floor": "OPERATOR",
        "risk_class": "MEDIUM",
        "required_inputs": ["change_summary"],
        "sop_rules": [
            "Verify all files match formatting and lint standards with zero warnings.",
            "Execute end-to-end regression suites and verify 100% passing results.",
            "Scan diffs for hardcoded credentials, bearer tokens, or private keys; reject immediately on detection."
        ],
        "checks": [
            "tests_pass_after_last_edit",
            "no_new_secret_in_diff",
            "destructive_migration_reviewed"
        ],
        "applicable_roles": ["Chief Technology Officer (CTO)", "Senior Fullstack Engineer", "QA & Reliability Engineer"],
        "protocol_source": "Enterprise engineering / Gravitas verification gate",
    },
    "incident-recovery": {
        "id": "incident-recovery",
        "name": "Autonomous Incident Recovery & Exponential Backoff",
        "category": "Resilience",
        "description": "Resilience protocol handling agent timeouts, API exhaustion (e.g. 429 errors), and state restoration.",
        "author": "Enterprise Core",
        "version": "2.3.0",
        "authority_floor": "OPERATOR",
        "risk_class": "MEDIUM",
        "required_inputs": ["incident"],
        "sop_rules": [
            "Apply exponential backoff (base * 2^failures) with randomized symmetric jitter on API rate limit encounters.",
            "On 5 consecutive unhandled failures, gracefully pause the agent and submit a diagnostic alert to the owner.",
            "Replay recent session events from checkpoint to recover intermediate progress without data loss."
        ],
        "checks": [
            "failure_count_recorded",
            "backoff_is_bounded",
            "checkpoint_exists_before_replay"
        ],
        "applicable_roles": ["All Autonomous Agents", "DevOps & Platform Engineer"],
        "protocol_source": "Enterprise resilience",
    },
    "verified-delivery": {
        "id": "verified-delivery",
        "name": "Verified Delivery & Evidence Gate",
        "category": "Governance",
        "description": "A claim may only be reported as delivered when its evidence exists and re-verification passes after the final change.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "EMPLOYEE",
        "risk_class": "LOW",
        "required_inputs": ["claim"],
        "evidence_required": True,
        "sop_rules": [
            "Read the target before editing; no blind writes.",
            "Run verification after the final mutation, never on a stale run.",
            "Attach the raw evidence reference to the claim; a green test is not proof of a business outcome.",
            "If evidence is missing or stale, report UNVERIFIED instead of success."
        ],
        "checks": [
            "claim_has_evidence_reference",
            "verification_ran_after_last_edit",
            "business_outcome_distinguished_from_task_success"
        ],
        "applicable_roles": ["All Autonomous Agents", "QA & Reliability Engineer"],
        "protocol_source": "Gravitas-style evidence-backed verification",
    },
    "scope-discipline": {
        "id": "scope-discipline",
        "name": "Scope Discipline & Anti-Bloat Review",
        "category": "Engineering",
        "description": "Rejects speculative work that is not tied to a stated requirement, owner, or measurable acceptance criterion.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "MANAGER",
        "risk_class": "LOW",
        "required_inputs": ["proposed_scope"],
        "sop_rules": [
            "Apply YAGNI: do not build a capability until a real workflow needs it.",
            "Prefer native libraries and existing engines over new frameworks.",
            "Every scope item needs an owner, a requirement reference and an acceptance test.",
            "Cap speculative scope at 12 items per review; split larger proposals."
        ],
        "checks": [
            "every_scope_item_has_requirement",
            "every_scope_item_has_acceptance_test",
            "no_unbounded_new_dependency",
            "scope_size_within_limit"
        ],
        "applicable_roles": ["Lead Product Manager", "CTO"],
        "protocol_source": "Ponytail-style YAGNI / decision ladder",
    },
    "finance-control": {
        "id": "finance-control",
        "name": "Finance Control & Segregation of Duties",
        "category": "Finance",
        "description": "Contract for spending proposals: budget, per-claim cap, approver role and separation of duties.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "MANAGER",
        "risk_class": "HIGH",
        "required_inputs": ["amount"],
        "limits": {"max_amount_inr": 1000000, "max_amount_usd": 12000},
        "sop_rules": [
            "Caller-asserted approval status is ignored; claims enter as SUBMITTED.",
            "The claimant cannot approve their own expense.",
            "Budget is checked at intake and again immediately before posting.",
            "No general-ledger post occurs before an authorised approval decision."
        ],
        "checks": [
            "amount_within_hard_limit",
            "claimant_not_approver",
            "budget_available",
            "approval_record_matches_principal"
        ],
        "applicable_roles": ["CFO", "Finance Manager"],
        "protocol_source": "Enterprise finance policy",
    },
    "risk-adjudication": {
        "id": "risk-adjudication",
        "name": "Multi-Judge Risk Adjudication Arena",
        "category": "Governance",
        "description": "Scores independent options through finance, risk, operations and compliance lenses, then routes the outcome to the required authority.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "MANAGER",
        "risk_class": "HIGH",
        "required_inputs": ["question", "options"],
        "sop_rules": [
            "At least two independent options must be scored; a single option is a proposal, not a decision.",
            "Judges score evidence, risk, reversibility, cost and policy compliance independently.",
            "Disagreement is surfaced as CONTESTED, never hidden behind an average.",
            "Missing evidence produces NEEDS_EVIDENCE instead of a confident answer.",
            "High-risk or irreversible outcomes require an authorised human decision."
        ],
        "checks": [
            "at_least_two_options",
            "every_option_scored_by_every_judge",
            "policy_evaluated",
            "consensus_or_escalation_recorded",
            "evidence_sealed"
        ],
        "applicable_roles": ["CEO", "COO", "CFO", "Risk Officer", "Department Manager"],
        "protocol_source": "Arena-style independent adjudication",
    },
    "workforce-delegation": {
        "id": "workforce-delegation",
        "name": "Authority-Aware Workforce Delegation",
        "category": "Workforce",
        "description": "Routes work to an employee only when the assignee's authority tier and tool scope cover the task.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "MANAGER",
        "risk_class": "MEDIUM",
        "required_inputs": ["task", "assignee_role"],
        "sop_rules": [
            "The assignee's authority tier must be at least the task's required tier.",
            "Financial, destructive or external actions keep the approval gate.",
            "Delegation never transfers owner sovereignty or tenant scope.",
            "The assignee must receive the acceptance criteria, not just the objective."
        ],
        "checks": [
            "assignee_authority_sufficient",
            "task_has_acceptance_criteria",
            "approval_gate_preserved",
            "tenant_scope_preserved"
        ],
        "applicable_roles": ["CEO", "COO", "Department Manager"],
        "protocol_source": "Enterprise workforce governance",
    },
    "incident-reporting": {
        "id": "incident-reporting",
        "name": "Incident Reporting & Redaction",
        "category": "Resilience",
        "description": "Produces a diagnostic incident report with secrets removed and an explicit blast-radius statement.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "EMPLOYEE",
        "risk_class": "LOW",
        "required_inputs": ["incident_summary"],
        "sop_rules": [
            "Collect standard diagnostics before proposing a cause.",
            "Redact tokens, passwords, connection strings and private keys.",
            "State impact, affected tenants and current mitigation explicitly.",
            "Do not close an incident without a verification step."
        ],
        "checks": [
            "summary_present",
            "no_secret_pattern_in_report",
            "impact_stated",
            "verification_step_present"
        ],
        "applicable_roles": ["All Autonomous Agents", "DevOps & Platform Engineer"],
        "protocol_source": "Report-style diagnostics with redaction",
    },
    "infrastructure-readiness": {
        "id": "infrastructure-readiness",
        "name": "Infrastructure Readiness & Free-Tier Gate",
        "category": "Infrastructure",
        "description": "Checks whether a requested backend capability can run with the configured/free resources before any paid upgrade.",
        "author": "Enterprise Core",
        "version": "1.0.0",
        "authority_floor": "MANAGER",
        "risk_class": "MEDIUM",
        "required_inputs": ["provider"],
        "sop_rules": [
            "Prefer an already-configured free or embedded capability.",
            "Report missing configuration as BLOCKED, not as implemented.",
            "Do not purchase infrastructure without a measured workload that needs it.",
            "Every readiness result names the exact environment variables required, never their values."
        ],
        "checks": [
            "provider_known",
            "required_config_listed",
            "free_tier_or_existing_resource_preferred",
            "no_secret_value_returned"
        ],
        "applicable_roles": ["CTO", "Platform Engineer"],
        "protocol_source": "Neon-style branch-first / free-tier readiness",
    },
}


class OperatingSkillRegistry:
    """Registry providing access to enterprise operational skills."""

    @staticmethod
    def list_skills() -> List[Dict[str, Any]]:
        return list(SKILLS_CATALOG.values())

    @staticmethod
    def get_skill(skill_id: str) -> Optional[Dict[str, Any]]:
        return SKILLS_CATALOG.get(skill_id)


# Aliases for backwards compatibility
ExecutiveSkillRegistry = OperatingSkillRegistry
SkillRegistry = OperatingSkillRegistry
