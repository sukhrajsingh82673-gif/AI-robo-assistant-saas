"""ZONATA Sovereign Core — LangGraph State Schema & Reducers.

Implements OpenCode Step 4C (Standing Rules 26, 33, 35):
1. Typed state schema for cyclic agent graphs:
   - Planning, Tool Execution, Critic Evaluation, and Decision Routing.
2. Invariants:
   - Page and external tool content is marked as untrusted data (Rule 26).
   - Cyclic iterations strictly bounded (max_iterations <= 5).
   - Idempotency keys recorded deterministically in state history (Rule 35).
"""

from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional


@dataclass
class AgentState:
    run_id: str
    tenant_id: str
    company_id: str
    actor_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)
    current_step: int = 0
    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    critic_feedback: Optional[str] = None
    needs_revision: bool = False
    iteration: int = 0
    max_iterations: int = 5
    idempotency_keys: List[str] = field(default_factory=list)
    completed: bool = False
    final_output: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "company_id": self.company_id,
            "actor_id": self.actor_id,
            "messages": self.messages,
            "plan": self.plan,
            "current_step": self.current_step,
            "tool_outputs": self.tool_outputs,
            "critic_feedback": self.critic_feedback,
            "needs_revision": self.needs_revision,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "idempotency_keys": self.idempotency_keys,
            "completed": self.completed,
            "final_output": self.final_output,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentState:
        return cls(
            run_id=data.get("run_id", ""),
            tenant_id=data.get("tenant_id", ""),
            company_id=data.get("company_id", ""),
            actor_id=data.get("actor_id", ""),
            messages=data.get("messages", []),
            plan=data.get("plan", []),
            current_step=data.get("current_step", 0),
            tool_outputs=data.get("tool_outputs", {}),
            critic_feedback=data.get("critic_feedback"),
            needs_revision=data.get("needs_revision", False),
            iteration=data.get("iteration", 0),
            max_iterations=data.get("max_iterations", 5),
            idempotency_keys=data.get("idempotency_keys", []),
            completed=data.get("completed", False),
            final_output=data.get("final_output"),
            error=data.get("error"),
        )

    def add_message(self, role: str, content: str, is_untrusted: bool = False) -> None:
        if is_untrusted:
            content = f"<<<UNTRUSTED_CONTENT>>>\n{content}\n<<<END_UNTRUSTED_CONTENT>>>"
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })

    def record_idempotency_key(self, key: str) -> None:
        if key not in self.idempotency_keys:
            self.idempotency_keys.append(key)
