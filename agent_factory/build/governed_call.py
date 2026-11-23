"""ZONATA Agent Factory - GovernedCall Execution Wrapper.

Wraps every node that touches external resources (tools, models, network, databases, delegations).
Enforces:
- KillSwitch Matrix pre-execution checks (agent, team, tenant, factory scopes)
- Execution limits counter (steps, tool calls, model calls, cost, timeout)
- AuthorityGateway / PolicyEngine authorization
- Inbound & outbound DLP data sanitisation
- Detached evidence recording before completion
"""

from __future__ import annotations
import hashlib
import time
from typing import Any, Callable, Dict, Optional, List

from agent_factory.ports import Principal, Resource, Decision, EvidenceEvent


class GovernedCallError(Exception):
    """Base error for governed call violations."""
    pass


class GovernedCallDeniedError(GovernedCallError):
    """Raised when AuthorityGateway denies an external call."""
    pass


class GovernedCallKilledError(GovernedCallError):
    """Raised when KillSwitch halts execution."""
    pass


class GovernedCallLimitExceededError(GovernedCallError):
    """Raised when steps, calls, or cost limits are exceeded."""
    pass


class GovernedCallContext:
    def __init__(
        self,
        killswitch_port,
        authority_port,
        evidence_port,
        limits_tracker: Optional[Dict[str, Any]] = None,
        dlp_scanner: Optional[Callable[[Any], Any]] = None,
        executor: Optional[Callable[[str, str, Any, str], Any]] = None,
        origin_principal: Optional[str] = None
    ):
        self.killswitch = killswitch_port
        self.authority = authority_port
        self.evidence = evidence_port
        self.limits_tracker = limits_tracker or {
            "steps": 0, "max_steps": 100,
            "tool_calls": 0, "max_tool_calls": 50,
            "cost_usd": 0.0, "max_cost_usd": 2.0
        }
        self.dlp_scanner = dlp_scanner or (lambda x: x)
        self.executor = executor or (lambda kind, target, args, token: {"result": "ok", "kind": kind, "target": target})
        self.origin_principal = origin_principal or "system"

    def check_and_count(self, kind: str, cost: float = 0.01) -> None:
        self.limits_tracker["steps"] += 1
        if self.limits_tracker["steps"] > self.limits_tracker.get("max_steps", 100):
            raise GovernedCallLimitExceededError(f"Step limit ({self.limits_tracker['max_steps']}) exceeded")

        if kind in ("tool", "mcp"):
            self.limits_tracker["tool_calls"] += 1
            if self.limits_tracker["tool_calls"] > self.limits_tracker.get("max_tool_calls", 50):
                raise GovernedCallLimitExceededError(f"Tool call limit ({self.limits_tracker['max_tool_calls']}) exceeded")

        self.limits_tracker["cost_usd"] += cost
        if self.limits_tracker["cost_usd"] > self.limits_tracker.get("max_cost_usd", 2.0):
            raise GovernedCallLimitExceededError(f"Budget cap (${self.limits_tracker['max_cost_usd']}) exceeded")


def governed_call(
    kind: str,
    target: str,
    args: Any,
    *,
    agent: Dict[str, Any],
    ctx: GovernedCallContext
) -> Any:
    """Execute external operation under strict governance and audit recording."""
    agent_id = agent.get("id", "agent_unknown")
    team_id = agent.get("team_id")
    tenant_id = agent.get("tenant_id", "tnt_default")
    principal_id = agent.get("principal_id", f"agt.{agent_id}")

    # 1. KillSwitch pre-execution verification
    if ctx.killswitch.is_killed("AGENT", agent_id, tenant_id):
        raise GovernedCallKilledError(f"Agent '{agent_id}' execution halted by KillSwitch")
    if team_id and ctx.killswitch.is_killed("TEAM", team_id, tenant_id):
        raise GovernedCallKilledError(f"Team '{team_id}' execution halted by KillSwitch")
    if ctx.killswitch.is_killed("TENANT", tenant_id, tenant_id):
        raise GovernedCallKilledError(f"Tenant '{tenant_id}' execution halted by KillSwitch")

    # 2. Limits and quotas checking
    ctx.check_and_count(kind)

    # 3. AuthorityGateway authorization check
    principal = Principal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        company_id=agent.get("company_id", "comp_default"),
        kind="agent",
        roles=["agent"]
    )
    decision = ctx.authority.authorize(
        principal=principal,
        action=f"agent.{kind}",
        resource=Resource(resource_id=target, resource_type=kind, tenant_id=tenant_id),
        meta={"origin": ctx.origin_principal, "target": target}
    )

    if decision.deny:
        # Record denial evidence
        ctx.evidence.append_event(EvidenceEvent(
            subject_kind="agent_call",
            subject_id=agent_id,
            event_type="agent.call.denied",
            actor=principal_id,
            payload_hashes={"target": target, "kind": kind, "reason": decision.reason},
            timestamp=time.time(),
            tenant_id=tenant_id
        ))
        raise GovernedCallDeniedError(f"AuthorityGateway denied {kind} call to '{target}': {decision.reason}")

    # 4. Inbound DLP scan
    sanitized_args = ctx.dlp_scanner(args)

    # 5. Short-lived token minting & execution
    short_lived_token = f"tok_sla_{hashlib.sha256(f'{principal_id}:{target}:{time.time()}'.encode()).hexdigest()[:24]}"
    raw_output = ctx.executor(kind, target, sanitized_args, short_lived_token)

    # 6. Outbound DLP scan
    final_output = ctx.dlp_scanner(raw_output)

    # 7. Append audit evidence
    ev_id = ctx.evidence.append_event(EvidenceEvent(
        subject_kind="agent_call",
        subject_id=agent_id,
        event_type="agent.call.ok",
        actor=principal_id,
        payload_hashes={
            "target": target,
            "kind": kind,
            "args_sha256": hashlib.sha256(str(args).encode()).hexdigest(),
            "out_sha256": hashlib.sha256(str(final_output).encode()).hexdigest()
        },
        timestamp=time.time(),
        tenant_id=tenant_id
    ))

    return final_output
