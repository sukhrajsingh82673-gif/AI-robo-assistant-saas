"""
Enterprise Operating Skills & Multi-Judge Decision Arena.

This module turns corporate decision-making into a governed, auditable
contract instead of a single model answer:

  1. A skill contract declares the minimum authority tier, risk class,
     required inputs and verification checks.
  2. The arena scores at least two independent options through four
     deterministic lenses (FINANCE, RISK, OPERATIONS, COMPLIANCE).
  3. Consensus / majority / contested / insufficient-evidence is reported
     explicitly; disagreement is never averaged away.
  4. PolicyEngine V2 decides whether the outcome is allowed, needs approval
     or must be escalated.
  5. The required authority tier is compared with the requester's role.
  6. Every evaluation is sealed in the tenant evidence ledger and persisted
     with its tenant/company scope.

The scoring is deterministic so it is reproducible and testable. It does not
pretend that a language model produced the decision; an LLM may add advisory
commentary elsewhere, but the authoritative ranking is computed in code.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from core.db import db
from core.evidence_ledger import EvidenceLedger
from core.models import PhysicalVerification
from core.operating_skills import OperatingSkillRegistry
from core.policy_engine_v2 import PolicyContext, PolicyDecision, PolicyEngineV2


ROLE_TO_AUTHORITY = {
    "OBSERVER": "EMPLOYEE",
    "AUDITOR": "MANAGER",
    "OPERATOR": "EMPLOYEE",
    "SYSTEM_AGENT": "EMPLOYEE",
    "MANAGER": "MANAGER",
    "EXECUTIVE": "EXECUTIVE",
    "OWNER": "OWNER",
    "GLOBAL_ADMIN": "OWNER",
}

AUTHORITY_RANK = {"EMPLOYEE": 0, "MANAGER": 1, "EXECUTIVE": 2, "OWNER": 3}
RISK_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
RISK_TO_AUTHORITY = {
    "LOW": "EMPLOYEE",
    "MEDIUM": "MANAGER",
    "HIGH": "EXECUTIVE",
    "CRITICAL": "OWNER",
}
RISK_TO_SCORE = {"LOW": 1.0, "MEDIUM": 0.7, "HIGH": 0.4, "CRITICAL": 0.1}
REVERSIBILITY_TO_SCORE = {"REVERSIBLE": 1.0, "PARTIAL": 0.6, "IRREVERSIBLE": 0.2}

# Four independent judging lenses. Weights must sum to 1.0.
JUDGE_LENSES: Dict[str, Dict[str, float]] = {
    "FINANCE": {"evidence": 0.20, "cost": 0.35, "risk": 0.25, "reversibility": 0.20, "policy": 0.00},
    "RISK": {"evidence": 0.25, "cost": 0.10, "risk": 0.40, "reversibility": 0.25, "policy": 0.00},
    "OPERATIONS": {"evidence": 0.30, "cost": 0.25, "risk": 0.20, "reversibility": 0.25, "policy": 0.00},
    "COMPLIANCE": {"evidence": 0.35, "cost": 0.00, "risk": 0.20, "reversibility": 0.10, "policy": 0.35},
}


def role_to_authority(role: str) -> str:
    return ROLE_TO_AUTHORITY.get(str(role or "").upper(), "EMPLOYEE")


def _authority_max(*tiers: str) -> str:
    return max(tiers, key=lambda t: AUTHORITY_RANK.get(t, 0))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class SkillArena:
    """Governed skill execution and multi-judge decision adjudication."""

    VERSION = "1.0.0"
    MAX_OPTIONS = 8
    MIN_EVIDENCE_SUPPORT = 0.35

    def __init__(
        self,
        tenant_id: str,
        company_id: str,
        ledger: Optional[EvidenceLedger] = None,
    ):
        if not tenant_id or not company_id:
            raise ValueError("tenant_id and company_id are required for the skill arena.")
        self.tenant_id = tenant_id
        self.company_id = company_id
        self._init_db()
        self.ledger = ledger or self._tenant_ledger()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    @staticmethod
    def _init_db() -> None:
        with db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS arena_decisions (
                    decision_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    requester_role TEXT NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    judges_json TEXT NOT NULL,
                    scores_json TEXT NOT NULL,
                    winner_option_id TEXT,
                    winner_title TEXT,
                    consensus_outcome TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agreement REAL NOT NULL DEFAULT 0.0,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    risk_level TEXT NOT NULL,
                    required_authority TEXT NOT NULL,
                    requester_authority TEXT NOT NULL,
                    authority_granted INTEGER NOT NULL DEFAULT 0,
                    policy_decision TEXT NOT NULL,
                    approval_id TEXT,
                    evidence_id TEXT,
                    evidence_status TEXT,
                    notes TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_arena_decisions_scope "
                "ON arena_decisions(tenant_id, company_id, created_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    skill_id TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    requester_role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    required_authority TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    result_json TEXT,
                    evidence_id TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_skill_runs_scope "
                "ON skill_runs(tenant_id, company_id, created_at)"
            )
            conn.commit()

    def _tenant_ledger(self) -> EvidenceLedger:
        try:
            from core.tenancy import get_ledger
            return get_ledger(self.tenant_id)
        except Exception:
            return EvidenceLedger()

    @staticmethod
    def _seal(
        ledger: EvidenceLedger,
        *,
        action_id: str,
        agent_id: str,
        check_type: str,
        target: str,
        expected: str,
        actual: str,
        verified: bool,
        details: str,
        tenant_id: str,
        company_id: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        verification = PhysicalVerification(
            check_type=check_type,
            target_path=target,
            expected_val=expected,
            actual_val=actual,
            verified=verified,
            details=details,
        )
        metadata = {
            "tenant_id": tenant_id,
            "company_id": company_id,
            "execution_mode": "DETERMINISTIC_CONTRACT",
            "engine": "skill_arena",
            "engine_version": SkillArena.VERSION,
        }
        if extra:
            metadata.update(extra)
        package = ledger.seal_evidence(
            action_id=action_id,
            mission_id=f"mis_arena_{uuid.uuid4().hex[:8]}",
            agent_id=agent_id,
            verifications=[verification],
            metadata=metadata,
        )
        return {
            "evidence_id": package.evidence_id,
            "evidence_status": getattr(package.status, "value", str(package.status)),
            "sha256_digest": package.sha256_digest,
            "merkle_root": ledger.get_merkle_root(),
            "verification_scope": "DETERMINISTIC_CONTRACT",
        }

    # ------------------------------------------------------------------
    # Skill catalog and execution
    # ------------------------------------------------------------------
    def list_skills(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        authority = role_to_authority(role) if role else None
        skills = OperatingSkillRegistry.list_skills()
        if not authority:
            return skills
        result = []
        for skill in skills:
            item = dict(skill)
            floor = item.get("authority_floor", "EMPLOYEE")
            item["available_to_requester"] = (
                AUTHORITY_RANK.get(authority, 0) >= AUTHORITY_RANK.get(floor, 0)
            )
            result.append(item)
        return result

    def run_skill(
        self,
        skill_id: str,
        inputs: Optional[Dict[str, Any]],
        requester: Dict[str, Any],
    ) -> Dict[str, Any]:
        skill = OperatingSkillRegistry.get_skill(skill_id)
        if not skill:
            return {"success": False, "status": "NOT_FOUND", "error": f"Unknown skill '{skill_id}'."}

        inputs = dict(inputs or {})
        requester_id = str(requester.get("user_id") or "unknown")
        role = str(requester.get("role") or "OBSERVER")
        authority = role_to_authority(role)
        floor = str(skill.get("authority_floor", "EMPLOYEE"))
        required_authority = _authority_max(floor, RISK_TO_AUTHORITY.get(skill.get("risk_class", "LOW"), "EMPLOYEE"))

        checks: List[Dict[str, Any]] = []
        missing = [k for k in (skill.get("required_inputs") or []) if inputs.get(k) in (None, "", [])]
        checks.append({
            "check": "required_inputs_present",
            "passed": not missing,
            "detail": "missing: " + ", ".join(missing) if missing else "all required inputs present",
        })

        evidence_required = bool(skill.get("evidence_required"))
        evidence_refs = inputs.get("evidence_refs") or []
        if not isinstance(evidence_refs, list):
            evidence_refs = [evidence_refs] if evidence_refs else []
        if evidence_required:
            checks.append({
                "check": "evidence_reference_present",
                "passed": bool(evidence_refs),
                "detail": f"{len(evidence_refs)} evidence reference(s)",
            })

        limits = skill.get("limits") or {}
        amount = _as_float(inputs.get("amount"))
        if "max_amount_inr" in limits and amount > 0:
            passed = amount <= float(limits["max_amount_inr"])
            checks.append({
                "check": "amount_within_hard_limit",
                "passed": passed,
                "detail": f"{amount:.2f} <= {float(limits['max_amount_inr']):.2f}",
            })

        if skill_id == "scope-discipline":
            scope = inputs.get("proposed_scope") or []
            if not isinstance(scope, list):
                scope = [scope]
            passed = 0 < len(scope) <= 12
            checks.append({
                "check": "scope_size_within_limit",
                "passed": passed,
                "detail": f"{len(scope)} item(s); limit 12",
            })

        if skill_id == "risk-adjudication":
            options = inputs.get("options") or []
            checks.append({
                "check": "at_least_two_options",
                "passed": isinstance(options, list) and len(options) >= 2,
                "detail": f"{len(options) if isinstance(options, list) else 0} option(s)",
            })

        authority_ok = AUTHORITY_RANK.get(authority, 0) >= AUTHORITY_RANK.get(required_authority, 0)
        checks.append({
            "check": "requester_authority_sufficient",
            "passed": authority_ok,
            "detail": f"requester={authority}, required={required_authority}",
        })

        contract_ok = all(c["passed"] for c in checks)
        if not authority_ok:
            status = "ESCALATED"
        elif not contract_ok:
            status = "CONTRACT_FAILED"
        else:
            status = "SATISFIED"

        result_payload = {
            "skill_id": skill_id,
            "skill_version": skill.get("version"),
            "protocol_source": skill.get("protocol_source"),
            "status": status,
            "execution_mode": "DETERMINISTIC_CONTRACT",
            "authority": {
                "requester": authority,
                "required": required_authority,
                "granted": authority_ok,
            },
            "checks": checks,
            "inputs_received": sorted(inputs.keys()),
            "result": {
                "contract_satisfied": contract_ok,
                "next_action": (
                    "Proceed under the skill's SOP and attach evidence."
                    if status == "SATISFIED"
                    else "Route to a higher authority or provide the missing contract inputs."
                ),
            },
            "created_at": time.time(),
        }

        evidence = self._seal(
            self.ledger,
            action_id=f"act_skill_{uuid.uuid4().hex[:6]}",
            agent_id=requester_id,
            check_type="skill_contract",
            target=f"skill://{skill_id}",
            expected="CONTRACT_SATISFIED",
            actual=status,
            verified=contract_ok and authority_ok,
            details=f"Skill '{skill_id}' contract evaluated for {requester_id} ({authority}).",
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            extra={"skill_id": skill_id, "run_id": None},
        )
        result_payload["evidence"] = evidence

        run_id = f"skr_{uuid.uuid4().hex[:10]}"
        result_payload["run_id"] = run_id
        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO skill_runs (
                    run_id, tenant_id, company_id, skill_id, requester_id,
                    requester_role, status, required_authority, inputs_json,
                    checks_json, result_json, evidence_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, self.tenant_id, self.company_id, skill_id, requester_id,
                    role, status, required_authority, json.dumps(inputs, sort_keys=True, default=str),
                    json.dumps(checks, sort_keys=True, default=str),
                    json.dumps(result_payload, sort_keys=True, default=str),
                    evidence["evidence_id"], time.time(),
                ),
            )
            conn.commit()

        result_payload["success"] = status in ("SATISFIED", "ESCALATED")
        return result_payload

    # ------------------------------------------------------------------
    # Decision arena
    # ------------------------------------------------------------------
    def evaluate(
        self,
        request: Dict[str, Any],
        requester: Dict[str, Any],
    ) -> Dict[str, Any]:
        question = str(request.get("question") or "").strip()
        if not question:
            raise ValueError("A decision question is required.")
        raw_options = request.get("options") or []
        if not isinstance(raw_options, list) or len(raw_options) < 2:
            raise ValueError("At least two independent options are required for an arena decision.")
        if len(raw_options) > self.MAX_OPTIONS:
            raise ValueError(f"At most {self.MAX_OPTIONS} options may be scored in one arena.")

        requester_id = str(requester.get("user_id") or "unknown")
        role = str(requester.get("role") or "OBSERVER")
        authority = role_to_authority(role)
        request_risk = str(request.get("risk_level") or "MEDIUM").upper()
        if request_risk not in RISK_RANK:
            request_risk = "MEDIUM"
        data_classification = str(request.get("data_classification") or "INTERNAL").upper()
        requested_spend_usd = _as_float(request.get("requested_spend_usd"))
        remaining_budget_usd = _as_float(request.get("remaining_budget_usd"), 1000.0)
        request_refs = request.get("evidence_refs") or []
        if not isinstance(request_refs, list):
            request_refs = [request_refs] if request_refs else []

        options = [
            self._normalise_option(option, idx, request_risk, request_refs)
            for idx, option in enumerate(raw_options)
        ]

        policy = PolicyEngineV2().evaluate(
            PolicyContext(
                requester_id=requester_id,
                requester_type="HUMAN" if role in ("OWNER", "EXECUTIVE", "MANAGER") else "AI_EMPLOYEE",
                requester_roles=[role],
                requester_departments=list(requester.get("departments") or []),
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                action="DECIDE",
                intent=question[:500],
                mission_id=None,
                data_classification=data_classification,
                tool_risk_class=(
                    "IRREVERSIBLE" if request_risk == "CRITICAL"
                    else "HIGH_RISK" if request_risk == "HIGH"
                    else "LOW_RISK"
                ),
                requested_spend_usd=requested_spend_usd,
                employee_remaining_budget_usd=remaining_budget_usd,
            )
        )

        scores, judge_winners = self._score_options(options)
        aggregate, borda = self._aggregate(scores, list(scores.keys()), options)
        winner = max(
            options,
            key=lambda o: (aggregate.get(o["id"], 0.0), borda.get(o["id"], 0.0), -o["index"]),
        )
        agreement = self._agreement(judge_winners, winner["id"])

        winner_evidence = self._evidence_support(winner)
        required_authority = _authority_max(
            RISK_TO_AUTHORITY.get(request_risk, "MANAGER"),
            RISK_TO_AUTHORITY.get(winner["risk_level"], "MANAGER"),
        )
        if policy.decision in (PolicyDecision.REQUIRE_APPROVAL, PolicyDecision.ESCALATE):
            required_authority = _authority_max(required_authority, "EXECUTIVE")
        authority_granted = AUTHORITY_RANK.get(authority, 0) >= AUTHORITY_RANK.get(required_authority, 0)

        compliant_options = [o for o in options if o["policy_compliant"]]
        notes: List[str] = []
        approval_id = None

        if policy.decision == PolicyDecision.DENY or not compliant_options:
            consensus = "DENIED"
            status = "DENIED"
            notes.append("PolicyEngine denied the decision or no policy-compliant option exists.")
        elif winner_evidence < self.MIN_EVIDENCE_SUPPORT:
            consensus = "INSUFFICIENT_EVIDENCE"
            status = "NEEDS_EVIDENCE"
            notes.append(
                f"Winner evidence support {winner_evidence:.2f} is below the "
                f"{self.MIN_EVIDENCE_SUPPORT:.2f} threshold; gather evidence before deciding."
            )
        else:
            if agreement >= 0.75:
                consensus = "CONSENSUS"
            elif agreement >= 0.50:
                consensus = "MAJORITY"
            else:
                consensus = "CONTESTED"

            needs_approval = (
                policy.decision in (PolicyDecision.REQUIRE_APPROVAL, PolicyDecision.ESCALATE)
                or RISK_RANK.get(request_risk, 1) >= RISK_RANK["HIGH"]
                or RISK_RANK.get(winner["risk_level"], 1) >= RISK_RANK["HIGH"]
                or consensus == "CONTESTED"
                or not authority_granted
            )
            if needs_approval:
                approval_id = self._create_approval(question, winner, policy, required_authority, request_risk)
                status = "ESCALATED" if not authority_granted else "PENDING_APPROVAL"
                if consensus == "CONTESTED":
                    notes.append("Judges disagree; a human authority must resolve the decision.")
                if not authority_granted:
                    notes.append(
                        f"Requester authority {authority} is below required {required_authority}."
                    )
            else:
                status = "DECIDED"

        evidence = self._seal(
            self.ledger,
            action_id=f"act_arena_{uuid.uuid4().hex[:6]}",
            agent_id=requester_id,
            check_type="arena_consensus",
            target=f"arena://{self.tenant_id}/{self.company_id}",
            expected="CONSENSUS_OR_ESCALATION",
            actual=f"{consensus}/{status}",
            verified=consensus in ("CONSENSUS", "MAJORITY", "CONTESTED"),
            details=(
                f"Multi-judge arena scored {len(options)} options; winner='{winner['title']}'; "
                f"agreement={agreement:.2f}; policy={policy.decision}; status={status}."
            ),
            tenant_id=self.tenant_id,
            company_id=self.company_id,
            extra={"question": question[:300]},
        )

        decision_id = f"dcd_{uuid.uuid4().hex[:10]}"
        created_at = time.time()
        result = {
            "success": status not in ("DENIED",),
            "decision_id": decision_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "question": question,
            "options": options,
            "judges": [
                {"lens": lens, "weights": weights, "scores": scores[lens]}
                for lens, weights in JUDGE_LENSES.items()
            ],
            "aggregate_scores": aggregate,
            "borda_scores": borda,
            "winner": {
                "option_id": winner["id"],
                "title": winner["title"],
                "risk_level": winner["risk_level"],
                "estimated_cost_usd": winner["estimated_cost_usd"],
                "evidence_support": round(winner_evidence, 4),
                "aggregate_score": round(aggregate.get(winner["id"], 0.0), 4),
            },
            "consensus": {
                "outcome": consensus,
                "agreement": round(agreement, 4),
                "confidence": round(_clamp(0.5 * agreement + 0.5 * aggregate.get(winner["id"], 0.0)), 4),
            },
            "status": status,
            "policy": {
                "decision": policy.decision,
                "reasons": policy.reasons,
                "restrictions": policy.restrictions,
            },
            "authority": {
                "requester": authority,
                "required": required_authority,
                "granted": authority_granted,
            },
            "approval_id": approval_id,
            "evidence": evidence,
            "notes": notes,
            "execution_mode": "DETERMINISTIC_ARENA",
            "engine_version": self.VERSION,
            "created_at": created_at,
        }

        with db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO arena_decisions (
                    decision_id, tenant_id, company_id, requester_id, requester_role,
                    question, options_json, judges_json, scores_json, winner_option_id,
                    winner_title, consensus_outcome, status, agreement, confidence,
                    risk_level, required_authority, requester_authority, authority_granted,
                    policy_decision, approval_id, evidence_id, evidence_status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id, self.tenant_id, self.company_id, requester_id, role,
                    question,
                    json.dumps(options, sort_keys=True, default=str),
                    json.dumps(result["judges"], sort_keys=True, default=str),
                    json.dumps({"aggregate": aggregate, "borda": borda}, sort_keys=True, default=str),
                    winner["id"], winner["title"], consensus, status,
                    agreement, result["consensus"]["confidence"], request_risk,
                    required_authority, authority, 1 if authority_granted else 0,
                    policy.decision, approval_id, evidence["evidence_id"],
                    evidence["evidence_status"], json.dumps(notes),
                    created_at,
                ),
            )
            conn.commit()

        return result

    # ------------------------------------------------------------------
    # Listing / retrieval
    # ------------------------------------------------------------------
    def list_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM arena_decisions WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (self.tenant_id, self.company_id, limit),
            ).fetchall()
        return [self._decode_decision(dict(row)) for row in rows]

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        with db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM arena_decisions WHERE decision_id = ? AND tenant_id = ? AND company_id = ?",
                (decision_id, self.tenant_id, self.company_id),
            ).fetchone()
        return self._decode_decision(dict(row)) if row else None

    def list_skill_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        with db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM skill_runs WHERE tenant_id = ? AND company_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (self.tenant_id, self.company_id, limit),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            for key in ("inputs_json", "checks_json", "result_json"):
                try:
                    item[key.replace("_json", "")] = json.loads(item.pop(key) or "{}")
                except (json.JSONDecodeError, TypeError):
                    item[key.replace("_json", "")] = item.pop(key)
            output.append(item)
        return output

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_option(
        option: Any,
        idx: int,
        request_risk: str,
        request_refs: List[Any],
    ) -> Dict[str, Any]:
        raw = dict(option) if isinstance(option, dict) else {"title": str(option)}
        refs = raw.get("evidence_refs") or request_refs or []
        if not isinstance(refs, list):
            refs = [refs] if refs else []
        risk = str(raw.get("risk_level") or request_risk).upper()
        if risk not in RISK_RANK:
            risk = request_risk
        reversibility = str(raw.get("reversibility") or "PARTIAL").upper()
        if reversibility not in REVERSIBILITY_TO_SCORE:
            reversibility = "PARTIAL"
        return {
            "id": str(raw.get("id") or f"opt_{idx + 1}"),
            "index": idx,
            "title": str(raw.get("title") or f"Option {idx + 1}")[:300],
            "description": str(raw.get("description") or "")[:2000],
            "risk_level": risk,
            "reversibility": reversibility,
            "estimated_cost_usd": max(0.0, _as_float(raw.get("estimated_cost_usd"))),
            "evidence_refs": [str(r) for r in refs if str(r).strip()],
            "confidence": _clamp(_as_float(raw.get("confidence"), 0.5)),
            "policy_compliant": bool(raw.get("policy_compliant", True)),
            "assumptions": list(raw.get("assumptions") or [])[:20],
            "expected_impact": str(raw.get("expected_impact") or "")[:1000],
        }

    @staticmethod
    def _evidence_support(option: Dict[str, Any]) -> float:
        refs = len(set(option.get("evidence_refs") or []))
        evidence_component = min(1.0, refs / 2.0)
        return _clamp(0.5 * evidence_component + 0.5 * option.get("confidence", 0.5))

    @staticmethod
    def _cost_score(option: Dict[str, Any]) -> float:
        return 1.0 / (1.0 + option.get("estimated_cost_usd", 0.0) / 1000.0)

    def _score_option(self, option: Dict[str, Any], weights: Dict[str, float]) -> float:
        return _clamp(
            weights["evidence"] * self._evidence_support(option)
            + weights["cost"] * self._cost_score(option)
            + weights["risk"] * RISK_TO_SCORE.get(option["risk_level"], 0.4)
            + weights["reversibility"] * REVERSIBILITY_TO_SCORE.get(option["reversibility"], 0.6)
            + weights["policy"] * (1.0 if option.get("policy_compliant") else 0.0)
        )

    def _score_options(
        self, options: List[Dict[str, Any]]
    ) -> tuple[Dict[str, Dict[str, float]], Dict[str, str]]:
        scores: Dict[str, Dict[str, float]] = {}
        winners: Dict[str, str] = {}
        for lens, weights in JUDGE_LENSES.items():
            lens_scores = {o["id"]: round(self._score_option(o, weights), 6) for o in options}
            scores[lens] = lens_scores
            winners[lens] = max(options, key=lambda o: lens_scores[o["id"]])["id"]
        return scores, winners

    @staticmethod
    def _aggregate(
        scores: Dict[str, Dict[str, float]],
        lenses: List[str],
        options: List[Dict[str, Any]],
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        aggregate = {
            o["id"]: round(sum(scores[lens][o["id"]] for lens in lenses) / len(lenses), 6)
            for o in options
        }
        max_points = max(1, len(options) - 1)
        borda_points = {o["id"]: 0.0 for o in options}
        for lens in lenses:
            ordered = sorted(options, key=lambda o: scores[lens][o["id"]], reverse=True)
            for rank, option in enumerate(ordered):
                borda_points[option["id"]] += (len(options) - 1 - rank)
        borda = {
            o["id"]: round(borda_points[o["id"]] / (len(lenses) * max_points), 6)
            for o in options
        }
        return aggregate, borda

    @staticmethod
    def _agreement(judge_winners: Dict[str, str], winner_id: str) -> float:
        if not judge_winners:
            return 0.0
        return sum(1 for w in judge_winners.values() if w == winner_id) / len(judge_winners)

    def _create_approval(
        self,
        question: str,
        winner: Dict[str, Any],
        policy: Any,
        required_authority: str,
        risk_level: str,
    ) -> Optional[str]:
        try:
            from core.approvals import ApprovalPipeline
            request = ApprovalPipeline.create_request(
                tenant_id=self.tenant_id,
                company_id=self.company_id,
                agent_id="skill_arena",
                action_desc=f"Arena decision: {question[:160]}",
                reason=(
                    f"Policy={policy.decision}; required_authority={required_authority}; "
                    f"winner='{winner['title'][:120]}'; risk={risk_level}."
                ),
                risk_level=risk_level,
                consequence="Decision is recorded but execution remains blocked until an authorised decision.",
            )
            return request.get("request_id")
        except Exception:
            return None

    @staticmethod
    def _decode_decision(item: Dict[str, Any]) -> Dict[str, Any]:
        for key in ("options_json", "judges_json", "scores_json", "notes"):
            if key in item and isinstance(item[key], str):
                try:
                    item[key.replace("_json", "")] = json.loads(item.pop(key))
                except json.JSONDecodeError:
                    item[key.replace("_json", "")] = item.pop(key)
        if "authority_granted" in item:
            item["authority_granted"] = bool(item["authority_granted"])
        return item
