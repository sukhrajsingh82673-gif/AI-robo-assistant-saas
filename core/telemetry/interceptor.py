"""
ZONATA Telemetry Interceptors & Runtime Instrumentation
======================================================
Provides non-invasive context managers and decorators to instrument:
- LLMGateway calls (emitting GenAI token counts and latency)
- ActionGateway and ToolRegistry executions (emitting tool execution metadata)
- AgentRuntime steps and workflows
"""

import time
import functools
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator, Callable

from core.telemetry.context import CorrelationContext
from core.telemetry.tracer import ZonataTracer, ZonataSpan, SpanKind, StatusCode, get_tracer

logger = logging.getLogger("zonata.telemetry.interceptor")


@contextmanager
def trace_span(
    name: str,
    context: Optional[CorrelationContext] = None,
    parent: Optional[ZonataSpan] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    tenant_allow_prompt_capture: bool = False,
    tracer: Optional[ZonataTracer] = None,
) -> Generator[ZonataSpan, None, None]:
    """
    Context manager to start, execute, and automatically end/record a span.
    Handles exception recording and error status codes cleanly.
    """
    active_tracer = tracer or get_tracer()
    span = active_tracer.start_span(
        name=name,
        context=context,
        kind=kind,
        parent=parent,
        attributes=attributes,
        tenant_allow_prompt_capture=tenant_allow_prompt_capture,
    )
    try:
        yield span
    except Exception as exc:
        span.record_exception(exc)
        raise
    finally:
        span.end()
        active_tracer.record_span(span)


def instrument_llm_call(
    func: Optional[Callable] = None,
    *,
    tracer: Optional[ZonataTracer] = None
) -> Callable:
    """Decorator to instrument LLM generation calls with GenAI semantic conventions."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            active_tracer = tracer or get_tracer()

            # Extract context or create default
            ctx = kwargs.get("correlation_context") or getattr(args[0], "context", None)
            if not isinstance(ctx, CorrelationContext):
                ctx = CorrelationContext()

            model_name = kwargs.get("model") or "unknown"
            tenant_allow_prompts = kwargs.get("tenant_allow_prompt_capture", False)

            with trace_span(
                f"llm.generate {model_name}",
                context=ctx,
                kind=SpanKind.CLIENT,
                tenant_allow_prompt_capture=tenant_allow_prompts,
                tracer=active_tracer
            ) as span:
                span.set_attribute("gen_ai.system", "zonata-llm-gateway")
                span.set_attribute("gen_ai.request.model", model_name)

                prompt = kwargs.get("prompt")
                if prompt:
                    span.set_attribute("zonata.prompt_body", str(prompt))

                result = fn(*args, **kwargs)

                # Record token metrics if present on result
                if hasattr(result, "usage") and isinstance(result.usage, dict):
                    p_tokens = result.usage.get("prompt_tokens") or result.usage.get("input_tokens")
                    c_tokens = result.usage.get("completion_tokens") or result.usage.get("output_tokens")
                    cost = result.usage.get("cost_micros")
                    span.set_genai_attributes(
                        model=model_name,
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        cost_micros=cost,
                        response_body=getattr(result, "text", None) or getattr(result, "content", None)
                    )

                return result

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def instrument_tool_call(
    func: Optional[Callable] = None,
    *,
    tracer: Optional[ZonataTracer] = None
) -> Callable:
    """Decorator to instrument ActionGateway and ToolRegistry executions."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            active_tracer = tracer or get_tracer()

            tool_name = kwargs.get("tool_name") or "tool"
            ctx = kwargs.get("correlation_context")
            if not isinstance(ctx, CorrelationContext):
                ctx = CorrelationContext()

            with trace_span(
                f"tool.execute {tool_name}",
                context=ctx,
                kind=SpanKind.INTERNAL,
                tracer=active_tracer
            ) as span:
                span.set_attribute("zonata.tool_name", tool_name)
                if "capability_id" in kwargs:
                    span.set_attribute("zonata.capability_id", kwargs["capability_id"])

                result = fn(*args, **kwargs)
                return result

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
