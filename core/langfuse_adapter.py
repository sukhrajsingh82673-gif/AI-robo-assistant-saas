"""
ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
Governed Langfuse AI Observability & Execution Tracing Adapter
=============================================================
Centralized, reusable instrumentation adapter providing end-to-end tracing,
performance profiling, cost accounting, and diagnostic analytics for the
ZONATA AI CEO, Gemma 4, Letta memory, Agency Swarm, LangGraph, MCP, and A2A.

Constitutional Invariants:
1. MODEL != AUTHORITY: Observability never grants permissions or modifies policy.
2. EVIDENCE != TELEMETRY: EvidenceLedger remains sole cryptographic audit authority.
3. ZERO_SECRET_TELEMETRY: All telemetry is pre-scrubbed via Presidio DLP before persistence.
4. STRICT_TENANT_ISOLATION: Traces and analytics are strictly partitioned by tenant_id.
5. SCOPED_FAIL_SAFE: Low-risk tasks fail-open on telemetry outage; audited tasks fail-closed.
"""

import os
import time
import uuid
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from core.langfuse_engine import langfuse_engine, LangfuseEngine, LangfuseGeneration, MODEL_PRICING_PER_1M
from core.presidio_dlp_engine import presidio_analyzer, presidio_anonymizer

logger = logging.getLogger("zonata.ai.langfuse.adapter")


class ExecutionStage(str, Enum):
    AI_CEO_PLANNING = "AI_CEO_PLANNING"
    GEMMA_4_MODEL_CALL = "GEMMA_4_MODEL_CALL"
    LETTA_MEMORY_RETRIEVAL = "LETTA_MEMORY_RETRIEVAL"
    LETTA_MEMORY_UPDATE = "LETTA_MEMORY_UPDATE"
    AGENCY_SWARM_DELEGATION = "AGENCY_SWARM_DELEGATION"
    LANGGRAPH_WORKFLOW = "LANGGRAPH_WORKFLOW"
    MCP_TOOL_INVOCATION = "MCP_TOOL_INVOCATION"
    A2A_INTERACTION = "A2A_INTERACTION"
    APPROVAL_EVALUATION = "APPROVAL_EVALUATION"
    TASK_COMPLETION = "TASK_COMPLETION"
    FAILURE_HANDLING = "FAILURE_HANDLING"


class StageStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    BLOCKED_POLICY = "BLOCKED_POLICY"
    RETRYING = "RETRYING"


@dataclass
class StageSpan:
    span_id: str
    trace_id: str
    task_id: str
    stage: ExecutionStage
    agent_id: str
    tenant_id: str
    model: str
    model_version: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: StageStatus = StageStatus.SUCCESS
    retry_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    tool_invocations: List[Dict[str, Any]] = field(default_factory=list)
    sanitized_error: Optional[str] = None
    approval_status: Optional[str] = None  # REQUESTED, GRANTED, DENIED, PENDING, NONE
    verification_status: Optional[str] = None  # VERIFIED, UNVERIFIED, TAMPER_DETECTED
    eval_scores: Dict[str, float] = field(default_factory=dict)
    eval_criteria_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stage"] = self.stage.value if isinstance(self.stage, ExecutionStage) else self.stage
        d["status"] = self.status.value if isinstance(self.status, StageStatus) else self.status
        return d


class GovernedLangfuseAdapter:
    """
    Centralized, sovereign Langfuse telemetry adapter for ZONATA AI CEO operations.
    Enforces pre-telemetry redaction, tenant isolation, and failure resilience.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "GovernedLangfuseAdapter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, engine: Optional[LangfuseEngine] = None):
        self.engine = engine or langfuse_engine
        self._spans: List[StageSpan] = []
        self._active_spans: Dict[str, StageSpan] = {}
        self._lock = threading.Lock()

    # =========================================================================
    # 1. PRE-TELEMETRY DATA SANITIZATION (ZERO CREDENTIAL LEAKS)
    # =========================================================================

    def sanitize_payload(self, text: Optional[str]) -> str:
        """
        Pre-screens text with Microsoft Presidio entity analyzer & anonymizer
        before telemetry recording to guarantee zero raw credentials in observability.
        """
        if not text:
            return ""
        if not isinstance(text, str):
            try:
                text = json.dumps(text)
            except Exception:
                text = str(text)

        # Detect and scrub sensitive entities (API keys, SSN, tokens, PAN, etc.)
        results = presidio_analyzer.analyze(text)
        if results:
            anon = presidio_anonymizer.anonymize(text, results)
            return anon.text
        return text

    def sanitize_dict(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Recursively scrubs strings in dictionaries before telemetry storage."""
        if not data:
            return {}
        cleaned = {}
        for k, v in data.items():
            if isinstance(v, str):
                cleaned[k] = self.sanitize_payload(v)
            elif isinstance(v, dict):
                cleaned[k] = self.sanitize_dict(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    self.sanitize_dict(x) if isinstance(x, dict)
                    else (self.sanitize_payload(x) if isinstance(x, str) else x)
                    for x in v
                ]
            else:
                cleaned[k] = v
        return cleaned

    # =========================================================================
    # 2. STAGE SPAN LIFECYCLE (START -> COMPLETE)
    # =========================================================================

    def start_stage_span(
        self,
        stage: ExecutionStage,
        task_id: str,
        tenant_id: str = "tnt_primary",
        trace_id: Optional[str] = None,
        agent_id: str = "ai_ceo",
        model: str = "gemma-4-31b-it",
        model_version: str = "v1.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> StageSpan:
        """Starts a monitored execution stage span."""
        span_id = f"span_{uuid.uuid4().hex[:12]}"
        t_id = trace_id or f"trace_{uuid.uuid4().hex[:16]}"
        now = time.time()

        span = StageSpan(
            span_id=span_id,
            trace_id=t_id,
            task_id=task_id,
            stage=stage,
            agent_id=agent_id,
            tenant_id=tenant_id,
            model=model,
            model_version=model_version,
            start_time=now,
            metadata=self.sanitize_dict(metadata or {})
        )

        with self._lock:
            self._active_spans[span_id] = span

        return span

    def finish_stage_span(
        self,
        span_id: str,
        status: StageStatus = StageStatus.SUCCESS,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_invocations: Optional[List[Dict[str, Any]]] = None,
        error_msg: Optional[str] = None,
        approval_status: Optional[str] = None,
        verification_status: Optional[str] = None,
        eval_scores: Optional[Dict[str, float]] = None,
        eval_criteria_version: Optional[str] = None,
        fail_closed: bool = False
    ) -> Optional[StageSpan]:
        """
        Completes an execution span, records metrics, token cost, and syncs
        to the underlying Langfuse engine with scoped fail-open/fail-closed semantics.
        """
        with self._lock:
            span = self._active_spans.pop(span_id, None)

        if not span:
            logger.warning(f"finish_stage_span called for unknown span_id={span_id}")
            return None

        now = time.time()
        span.end_time = now
        span.duration_ms = max(0.0, (now - span.start_time) * 1000.0)
        span.status = status
        span.input_tokens = input_tokens
        span.output_tokens = output_tokens
        span.total_tokens = input_tokens + output_tokens
        span.cost_usd = self.engine.calculate_cost(span.model, input_tokens, output_tokens)

        # Sanitize tool calls and errors
        clean_tools = []
        for t in (tool_invocations or []):
            clean_tools.append({
                "name": t.get("name", "unknown_tool"),
                "success": bool(t.get("success", True)),
                "latency_ms": float(t.get("latency_ms", 0.0)),
                "error_category": self.sanitize_payload(t.get("error_category", "")) if t.get("error_category") else None
            })
        span.tool_invocations = clean_tools

        if error_msg:
            span.sanitized_error = self.sanitize_payload(error_msg)

        span.approval_status = approval_status
        span.verification_status = verification_status
        span.eval_scores = eval_scores or {}
        span.eval_criteria_version = eval_criteria_version

        # Record span to local memory buffer
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > 5000:
                self._spans.pop(0)

        # Sync generation to LangfuseEngine with scoped failure handling
        try:
            self.engine.record_generation(
                name=f"{span.stage.value}:{span.agent_id}",
                model=span.model,
                prompt=self.sanitize_payload(span.metadata.get("prompt", f"Execution in stage {span.stage.value}")),
                response=self.sanitize_payload(span.metadata.get("response", f"Completed with status {span.status.value}")),
                input_tokens=span.input_tokens,
                output_tokens=span.output_tokens,
                latency_ms=span.duration_ms,
                tenant_id=span.tenant_id,
                mission_id=span.task_id,
                agent_id=span.agent_id,
                trace_id=span.trace_id,
                tool_calls=span.tool_invocations,
                metadata={
                    "span_id": span.span_id,
                    "stage": span.stage.value,
                    "status": span.status.value,
                    "approval_status": span.approval_status,
                    "verification_status": span.verification_status,
                    "eval_criteria_version": span.eval_criteria_version
                }
            )
            # Attach evaluation scores if present
            for metric, score in span.eval_scores.items():
                self.engine.submit_score(span.span_id, metric, score)

        except Exception as e:
            logger.error(f"Langfuse engine sync failed for span {span_id}: {e}")
            if fail_closed:
                # High-risk financial or audited tasks fail-closed if required
                raise RuntimeError(f"Audited operation failed: telemetry backend unavailable: {e}")
            # Low-risk routine operations fail-open safely (governance continues)
            span.metadata["langfuse_sync_status"] = "DEGRADED_FAIL_OPEN"

        return span

    # =========================================================================
    # 3. CONVENIENCE STAGE TRACERS
    # =========================================================================

    def trace_model_call(
        self,
        model: str,
        prompt: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        tenant_id: str = "tnt_primary",
        task_id: str = "task_root",
        agent_id: str = "ai_ceo",
        trace_id: Optional[str] = None
    ) -> StageSpan:
        """One-shot helper for recording an LLM/Gemma call with auto-sanitization."""
        span = self.start_stage_span(
            stage=ExecutionStage.GEMMA_4_MODEL_CALL,
            task_id=task_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
            agent_id=agent_id,
            model=model,
            metadata={"prompt": prompt, "response": response}
        )
        return self.finish_stage_span(
            span_id=span.span_id,
            status=StageStatus.SUCCESS,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

    def trace_memory_op(
        self,
        operation: str,  # RETRIEVAL or UPDATE
        tier: str,       # OPERATIONAL, EPISODIC, BUSINESS
        key: str,
        latency_ms: float,
        success: bool = True,
        tenant_id: str = "tnt_primary",
        task_id: str = "task_root",
        agent_id: str = "ai_ceo"
    ) -> StageSpan:
        """Traces Letta memory reads and writes."""
        stage = ExecutionStage.LETTA_MEMORY_RETRIEVAL if "retriev" in operation.lower() else ExecutionStage.LETTA_MEMORY_UPDATE
        span = self.start_stage_span(
            stage=stage,
            task_id=task_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            metadata={"tier": tier, "memory_key": self.sanitize_payload(key)}
        )
        return self.finish_stage_span(
            span_id=span.span_id,
            status=StageStatus.SUCCESS if success else StageStatus.FAILED
        )

    def trace_approval_event(
        self,
        task_id: str,
        amount_inr: float,
        approval_status: str,  # REQUESTED, GRANTED, DENIED
        tenant_id: str = "tnt_primary",
        agent_id: str = "ai_ceo"
    ) -> StageSpan:
        """Traces financial threshold checks and human approval state."""
        span = self.start_stage_span(
            stage=ExecutionStage.APPROVAL_EVALUATION,
            task_id=task_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            metadata={"amount_inr": amount_inr}
        )
        return self.finish_stage_span(
            span_id=span.span_id,
            status=StageStatus.SUCCESS if approval_status in ("GRANTED", "REQUESTED") else StageStatus.BLOCKED_POLICY,
            approval_status=approval_status
        )

    # =========================================================================
    # 4. TENANT-ISOLATED QUERIES & ANALYTICS
    # =========================================================================

    def get_spans(
        self,
        tenant_id: str,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        stage: Optional[ExecutionStage] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves spans strictly filtered by tenant_id."""
        with self._lock:
            out = []
            for s in self._spans:
                if s.tenant_id != tenant_id:
                    continue
                if task_id and s.task_id != task_id:
                    continue
                if agent_id and s.agent_id != agent_id:
                    continue
                if stage and s.stage != stage:
                    continue
                out.append(s.to_dict())
            return out

    # =========================================================================
    # 5. DIAGNOSTIC BOTTLENECK & ERROR ANALYZER
    # =========================================================================

    def analyze_system_bottlenecks(self, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes collected telemetry to discover empirical execution patterns:
        - Frequently failing task categories
        - Low-performing agents
        - Excessive retries and unnecessary tool calls
        - Memory retrieval failures
        - High-latency stages
        - Model cost vs quality trade-offs
        - Actionable AI CEO improvement recommendations
        """
        with self._lock:
            target_spans = [
                s for s in self._spans
                if not tenant_id or s.tenant_id == tenant_id
            ]

        if not target_spans:
            return {
                "total_spans": 0,
                "failing_task_categories": {},
                "agent_success_rates": {},
                "tool_failure_rates": {},
                "stage_latencies_ms": {},
                "total_cost_usd": 0.0,
                "recommended_improvements": []
            }

        failing_categories: Dict[str, int] = {}
        agent_stats: Dict[str, Dict[str, int]] = {}
        tool_failures: Dict[str, int] = {}
        stage_latencies: Dict[str, List[float]] = {}
        total_cost = 0.0
        memory_failures = 0

        for s in target_spans:
            total_cost += s.cost_usd
            stage_name = s.stage.value if isinstance(s.stage, ExecutionStage) else str(s.stage)

            # Latency per stage
            stage_latencies.setdefault(stage_name, []).append(s.duration_ms)

            # Agent stats
            agent_stats.setdefault(s.agent_id, {"total": 0, "success": 0, "failed": 0})
            agent_stats[s.agent_id]["total"] += 1
            if s.status == StageStatus.SUCCESS:
                agent_stats[s.agent_id]["success"] += 1
            else:
                agent_stats[s.agent_id]["failed"] += 1
                failing_categories[stage_name] = failing_categories.get(stage_name, 0) + 1

            # Memory retrieval failures
            if s.stage == ExecutionStage.LETTA_MEMORY_RETRIEVAL and s.status != StageStatus.SUCCESS:
                memory_failures += 1

            # Tool failures
            for t in s.tool_invocations:
                t_name = t.get("name", "unknown")
                if not t.get("success", True):
                    tool_failures[t_name] = tool_failures.get(t_name, 0) + 1

        # Calculate agent success percentages
        agent_success_rates = {}
        for a_id, st in agent_stats.items():
            rate = round((st["success"] / st["total"]) * 100.0, 1) if st["total"] > 0 else 0.0
            agent_success_rates[a_id] = {
                "success_rate_pct": rate,
                "total_executions": st["total"],
                "failures": st["failed"]
            }

        # Stage average latencies
        stage_avg_latencies = {
            st: round(sum(lats) / len(lats), 2)
            for st, lats in stage_latencies.items()
        }

        # Formulate grounded improvement proposals for AI CEO review
        recommendations = []
        for a_id, rate_info in agent_success_rates.items():
            if rate_info["success_rate_pct"] < 80.0 and rate_info["total_executions"] >= 3:
                recommendations.append(
                    f"Agent '{a_id}' exhibits low completion rate ({rate_info['success_rate_pct']}%). "
                    "Recommend prompt recalibration or specialist re-delegation."
                )

        if memory_failures > 0:
            recommendations.append(
                f"Observed {memory_failures} Letta memory retrieval failures. "
                "Recommend indexing operational memory keys and expanding retrieval context."
            )

        for t_name, fail_count in tool_failures.items():
            if fail_count >= 2:
                recommendations.append(
                    f"Tool '{t_name}' failed {fail_count} times. "
                    "Recommend verifying MCP tool connection or updating fallback parameters."
                )

        return {
            "total_spans": len(target_spans),
            "failing_task_categories": failing_categories,
            "agent_success_rates": agent_success_rates,
            "tool_failure_rates": tool_failures,
            "stage_latencies_ms": stage_avg_latencies,
            "memory_retrieval_failures": memory_failures,
            "total_cost_usd": round(total_cost, 6),
            "recommended_improvements": recommendations
        }


# Global singleton
governed_langfuse_adapter = GovernedLangfuseAdapter.get_instance()
