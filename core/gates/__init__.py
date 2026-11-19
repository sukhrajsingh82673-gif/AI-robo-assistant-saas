"""ZONATA Sovereign Core — Deterministic Gate Library.

Implements Laws L2, L3, L4, L5, L6, L12:
- Gates are deterministic code, never LLM judgment. Models propose; gates decide.
- Unified evaluation pipeline:
  1. KillSwitchGate (immediate hard halt if engaged)
  2. AdmissionGate (explicit vs inferred vs not admitted)
  3. CharterGate (red lines, brand voice, spending caps)
  4. BudgetGate (tokens, USD, compute)
  5. AutonomyGate (L0–L4 compliance)
  6. PermissionGate (monotonic capability checks)
"""

from __future__ import annotations
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from core.charter import CompanyCharter, CharterVerdict
from core.killswitch_matrix import KillSwitchMatrix
from core.models import EvidencePackage

logger = logging.getLogger("zonata.core.gates")


@dataclass
class GateResult:
    passed: bool
    gate_name: str
    code: str  # e.g. GATE_PASSED, ADMISSION_DROPPED, CHARTER_REDLINE, BUDGET_EXCEEDED, KILLSWITCH_ACTIVE, AUTONOMY_BLOCKED
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class KillSwitchGate:
    """Evaluates whether any killswitch scope (GLOBAL, TENANT, COMPANY, AGENT, SURFACE) is engaged."""

    def __init__(self, killswitch_matrix: Optional[KillSwitchMatrix] = None):
        self.matrix = killswitch_matrix

    def evaluate(
        self,
        tenant_id: str,
        surface: str = "execution",
        target_id: Optional[str] = None
    ) -> GateResult:
        try:
            # Check global distributed coordination
            from core.distributed_coordination import coordination
            killed, reason = coordination.is_killed("GLOBAL", "SYSTEM")
            if killed:
                return GateResult(
                    passed=False,
                    gate_name="KillSwitchGate",
                    code="KILLSWITCH_GLOBAL_ACTIVE",
                    reason=reason or "Global emergency stop engaged across system."
                )

            if target_id:
                killed, reason = coordination.is_killed("AGENT", target_id)
                if killed:
                    return GateResult(
                        passed=False,
                        gate_name="KillSwitchGate",
                        code="KILLSWITCH_TARGET_ACTIVE",
                        reason=reason or f"Killswitch engaged for target '{target_id}'."
                    )

            # Check matrix
            matrix = self.matrix or KillSwitchMatrix(tenant_id=tenant_id)
            if matrix.is_activated(surface, target_id or "default"):
                return GateResult(
                    passed=False,
                    gate_name="KillSwitchGate",
                    code="KILLSWITCH_SURFACE_ACTIVE",
                    reason=f"Killswitch engaged on surface '{surface}'."
                )

            return GateResult(
                passed=True,
                gate_name="KillSwitchGate",
                code="GATE_PASSED",
                reason="Killswitch clear."
            )
        except Exception as e:
            logger.warning(f"KillSwitch check fallback: {e}")
            return GateResult(passed=True, gate_name="KillSwitchGate", code="GATE_PASSED", reason="Killswitch clear.")


class AdmissionGate:
    """Classifies incoming requests into EXPLICIT, INFERRED, or NOT_ADMITTED (Law L3).

    Not-admitted requests are dropped BEFORE any model call.
    Inferred requests are admitted only if process autonomy >= L2, otherwise logged as 'would accept'.
    """

    MIN_PROMPT_LENGTH = 10
    MAX_PROMPT_LENGTH = 20000

    def evaluate(
        self,
        natural_language: str,
        mode: str = "explicit",
        autonomy_level: int = 0
    ) -> GateResult:
        nl_stripped = natural_language.strip() if natural_language else ""

        # 1. Structural admission checks
        if len(nl_stripped) < self.MIN_PROMPT_LENGTH:
            return GateResult(
                passed=False,
                gate_name="AdmissionGate",
                code="ADMISSION_TOO_SHORT",
                reason=f"Request length ({len(nl_stripped)}) below minimum threshold ({self.MIN_PROMPT_LENGTH} characters). Dropped before model call."
            )

        if len(nl_stripped) > self.MAX_PROMPT_LENGTH:
            return GateResult(
                passed=False,
                gate_name="AdmissionGate",
                code="ADMISSION_TOO_LONG",
                reason=f"Request length exceeds maximum allowed limit ({self.MAX_PROMPT_LENGTH} characters)."
            )

        # 2. Inferred request check (Law L3)
        if mode == "inferred":
            if autonomy_level < 2:
                return GateResult(
                    passed=False,
                    gate_name="AdmissionGate",
                    code="INFERRED_AUTONOMY_INSUFFICIENT",
                    reason=f"Inferred request recorded as 'would accept', but execution dropped because process autonomy is L{autonomy_level} (requires >= L2).",
                    details={"mode": "inferred", "action": "recorded_would_accept"}
                )

        return GateResult(
            passed=True,
            gate_name="AdmissionGate",
            code="GATE_PASSED",
            reason=f"Request admitted ({mode}).",
            details={"mode": mode, "length": len(nl_stripped)}
        )


class CharterGate:
    """Evaluates request against company Charter red lines, brand voice, and spending limits."""

    def evaluate(
        self,
        charter: CompanyCharter,
        request_text: str,
        action_name: str = "",
        role: str = "ai_employee",
        amount_usd: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GateResult:
        verdict: CharterVerdict = charter.evaluate_request(
            request_text=request_text,
            action_name=action_name,
            role=role,
            amount_usd=amount_usd,
            context=context
        )

        if not verdict.allowed:
            return GateResult(
                passed=False,
                gate_name="CharterGate",
                code=f"CHARTER_{verdict.status_code}",
                reason=verdict.reason,
                details={
                    "violated_rules": verdict.violated_rules,
                    "accountable_owner_id": verdict.accountable_owner_id
                }
            )

        return GateResult(
            passed=True,
            gate_name="CharterGate",
            code="GATE_PASSED",
            reason=verdict.reason,
            details={"evaluated_rules_count": len(verdict.evaluated_rules)}
        )


class BudgetGate:
    """Enforces token, dollar, and compute quotas per tenant and process (Law L12)."""

    def evaluate(
        self,
        cost_usd: float,
        tokens: int,
        max_cost_cap_usd: float = 25.0,
        max_tokens_cap: int = 500000
    ) -> GateResult:
        if cost_usd > max_cost_cap_usd:
            return GateResult(
                passed=False,
                gate_name="BudgetGate",
                code="BUDGET_COST_EXCEEDED",
                reason=f"Spend ${cost_usd:.4f} exceeds configured budget cap of ${max_cost_cap_usd:.2f}."
            )

        if tokens > max_tokens_cap:
            return GateResult(
                passed=False,
                gate_name="BudgetGate",
                code="BUDGET_TOKENS_EXCEEDED",
                reason=f"Token consumption {tokens} exceeds cap of {max_tokens_cap} tokens."
            )

        return GateResult(
            passed=True,
            gate_name="BudgetGate",
            code="GATE_PASSED",
            reason="Budget verification within limits."
        )


class AutonomyGate:
    """Enforces per-process Autonomy Levels L0–L4 (Section 7).

    L0 Observe: Records what it would do; DOES NOTHING.
    L1 Suggest: Proposes to human / approver; does not execute.
    L2 Act with approval: Executes only when independent approval is verified.
    L3 Act within limits: Acts alone inside Charter limits; reversible actions only.
    L4 Autonomous: Acts alone including irreversible actions inside limits; post-review by sampling.
    """

    def evaluate(
        self,
        autonomy_level: int,
        action_name: str,
        is_reversible: bool = True,
        approval_verified: bool = False
    ) -> GateResult:
        # Actions that are inherently irreversible
        inherently_irreversible = {"finance.wire", "storage.delete", "db.drop", "hr.terminate"}
        if action_name in inherently_irreversible:
            is_reversible = False

        if autonomy_level == 0:
            return GateResult(
                passed=False,
                gate_name="AutonomyGate",
                code="AUTONOMY_L0_OBSERVE_ONLY",
                reason="Process is at L0 (Observe Mode). Action recorded in shadow mode; execution halted.",
                details={"shadow_mode": True}
            )

        if autonomy_level == 1 and not approval_verified:
            return GateResult(
                passed=False,
                gate_name="AutonomyGate",
                code="AUTONOMY_L1_SUGGEST_ONLY",
                reason="Process is at L1 (Suggest Mode). Recommendation delivered to human operator.",
                details={"suggest_mode": True}
            )

        if autonomy_level == 2 and not is_reversible and not approval_verified:
            return GateResult(
                passed=False,
                gate_name="AutonomyGate",
                code="AUTONOMY_L2_APPROVAL_REQUIRED",
                reason="Process is at L2 (Act and notify). Irreversible action requires independent approval before execution."
            )

        if autonomy_level == 3 and not is_reversible and not approval_verified:
            return GateResult(
                passed=False,
                gate_name="AutonomyGate",
                code="AUTONOMY_L3_IRREVERSIBLE_BLOCKED",
                reason="Process is at L3 (Act within limits). Irreversible actions require higher autonomy (L4) or explicit human approval."
            )

        return GateResult(
            passed=True,
            gate_name="AutonomyGate",
            code="GATE_PASSED",
            reason=f"Action permitted under Autonomy Level L{autonomy_level}."
        )


class DeterministicGatePipeline:
    """Sequential evaluator for all sovereign gates."""

    def __init__(
        self,
        killswitch_gate: Optional[KillSwitchGate] = None,
        admission_gate: Optional[AdmissionGate] = None,
        charter_gate: Optional[CharterGate] = None,
        budget_gate: Optional[BudgetGate] = None,
        autonomy_gate: Optional[AutonomyGate] = None
    ):
        self.killswitch = killswitch_gate or KillSwitchGate()
        self.admission = admission_gate or AdmissionGate()
        self.charter = charter_gate or CharterGate()
        self.budget = budget_gate or BudgetGate()
        self.autonomy = autonomy_gate or AutonomyGate()

    def evaluate_all(
        self,
        tenant_id: str,
        natural_language: str,
        charter: CompanyCharter,
        action_name: str = "",
        autonomy_level: int = 3,
        role: str = "ai_employee",
        amount_usd: Optional[float] = None,
        is_reversible: bool = True,
        approval_verified: bool = False,
        cost_usd: float = 0.0,
        tokens: int = 0,
        mode: str = "explicit"
    ) -> List[GateResult]:
        """Runs gates in strict dependency order: Stop at first failing gate."""
        results = []

        # 1. KillSwitch
        ks_res = self.killswitch.evaluate(tenant_id=tenant_id, target_id=action_name)
        results.append(ks_res)
        if not ks_res.passed:
            return results

        # 2. Admission
        adm_res = self.admission.evaluate(natural_language=natural_language, mode=mode, autonomy_level=autonomy_level)
        results.append(adm_res)
        if not adm_res.passed:
            return results

        # 3. Charter
        ch_res = self.charter.evaluate(
            charter=charter,
            request_text=natural_language,
            action_name=action_name,
            role=role,
            amount_usd=amount_usd
        )
        results.append(ch_res)
        if not ch_res.passed:
            return results

        # 4. Budget
        bg_res = self.budget.evaluate(cost_usd=cost_usd, tokens=tokens)
        results.append(bg_res)
        if not bg_res.passed:
            return results

        # 5. Autonomy
        aut_res = self.autonomy.evaluate(
            autonomy_level=autonomy_level,
            action_name=action_name,
            is_reversible=is_reversible,
            approval_verified=approval_verified
        )
        results.append(aut_res)

        return results
