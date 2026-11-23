"""ZONATA Agent Factory - SpecCompiler.

Compiles declarative zonata.agent/v1 specifications into governed execution graphs.
Enforces the mandatory rule:
Every node that touches the outside world (model, tool, mcp, delegate, retrieve, external network)
is wrapped by GovernedCall. Pure nodes (validate, branch, report) execute in-process.

Static check: asserts that 100% of external nodes in the compiled graph carry a valid GovernedCall wrapper.
"""

from __future__ import annotations
import copy
import hashlib
from typing import Any, Callable, Dict, List, Optional, Set

from agent_factory.build.governed_call import governed_call, GovernedCallContext


EXTERNAL_STEP_KINDS = {"model", "agent_loop", "tool", "delegate", "retrieve", "parallel_map", "mcp"}
INTERNAL_STEP_KINDS = {"validate", "branch", "report", "approval", "transform"}


class CompiledNode:
    def __init__(
        self,
        node_id: str,
        kind: str,
        is_external: bool,
        governed_wrapper: Optional[Callable] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.node_id = node_id
        self.kind = kind
        self.is_external = is_external
        self.governed_wrapper = governed_wrapper
        self.config = config or {}

    def execute(self, state: Dict[str, Any], ctx: GovernedCallContext, agent_meta: Dict[str, Any]) -> Any:
        if self.is_external:
            if not self.governed_wrapper:
                raise RuntimeError(f"Compiler invariant violated: external node '{self.node_id}' missing governed wrapper!")
            return self.governed_wrapper(state, ctx, agent_meta)
        else:
            # Internal execution (pure validation/transform)
            state[f"result_{self.node_id}"] = {"status": "ok", "node": self.node_id}
            return state


class CompiledGraph:
    def __init__(
        self,
        agent_name: str,
        version: str,
        nodes: Dict[str, CompiledNode],
        edges: List[Dict[str, str]],
        entry_point: str,
        workflow_type: str
    ):
        self.agent_name = agent_name
        self.version = version
        self.nodes = nodes
        self.edges = edges
        self.entry_point = entry_point
        self.workflow_type = workflow_type

    def get_external_nodes(self) -> List[CompiledNode]:
        return [n for n in self.nodes.values() if n.is_external]

    def verify_no_unwrapped_external_nodes(self) -> bool:
        """Static verification: assert that 100% of external nodes are wrapped."""
        for node in self.get_external_nodes():
            if node.governed_wrapper is None:
                return False
        return True

    def run(self, initial_input: Dict[str, Any], ctx: GovernedCallContext, agent_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Execute compiled graph across defined workflow steps."""
        state = copy.deepcopy(initial_input)
        current_node_id = self.entry_point

        visited = set()
        while current_node_id:
            if current_node_id in visited and self.workflow_type != "supervisor":
                break
            visited.add(current_node_id)
            node = self.nodes.get(current_node_id)
            if not node:
                break

            out = node.execute(state, ctx, agent_meta)
            if isinstance(out, dict):
                state.update(out)

            # Follow edge
            next_edges = [e["to"] for e in self.edges if e["from"] == current_node_id]
            current_node_id = next_edges[0] if next_edges else None

        return state


class SpecCompiler:
    """Compiles a verified zonata.agent/v1 spec into a CompiledGraph."""

    def compile(self, spec: Dict[str, Any]) -> CompiledGraph:
        metadata = spec.get("metadata", {})
        name = metadata.get("name", "agent-anonymous")
        version = metadata.get("version", "1.0.0")
        workflow = spec.get("workflow", {})
        wf_type = workflow.get("type", "sequential")
        raw_steps = workflow.get("steps", [])

        if not raw_steps:
            # Default steps if not explicitly listed in workflow
            raw_steps = [
                {"id": "step_validate_input", "kind": "validate"},
                {"id": "step_model_reasoning", "kind": "model", "prompt": spec.get("role", {}).get("instructions", "")},
                {"id": "step_generate_output", "kind": "report"}
            ]

        nodes: Dict[str, CompiledNode] = {}
        edges: List[Dict[str, str]] = []

        prev_node_id = None
        for step in raw_steps:
            node_id = step["id"]
            kind = step["kind"]
            is_external = kind in EXTERNAL_STEP_KINDS

            wrapper = None
            if is_external:
                # Wrap node with governed_call closure
                target_resource = step.get("tool") or step.get("agent") or f"model:{spec.get('model', {}).get('profile', 'default')}"

                def make_wrapper(step_kind: str, target: str, step_cfg: Dict[str, Any]):
                    def _call_wrapper(current_state: Dict[str, Any], g_ctx: GovernedCallContext, a_meta: Dict[str, Any]):
                        args = {"state": current_state, "step_config": step_cfg}
                        res = governed_call(step_kind, target, args, agent=a_meta, ctx=g_ctx)
                        return {f"result_{step_cfg.get('id', 'node')}": res}
                    return _call_wrapper

                wrapper = make_wrapper(kind, target_resource, step)

            nodes[node_id] = CompiledNode(
                node_id=node_id,
                kind=kind,
                is_external=is_external,
                governed_wrapper=wrapper,
                config=step
            )

            if prev_node_id:
                edges.append({"from": prev_node_id, "to": node_id})
            prev_node_id = node_id

        entry_point = raw_steps[0]["id"] if raw_steps else ""
        graph = CompiledGraph(
            agent_name=name,
            version=version,
            nodes=nodes,
            edges=edges,
            entry_point=entry_point,
            workflow_type=wf_type
        )

        # Invariant check
        if not graph.verify_no_unwrapped_external_nodes():
            raise RuntimeError(f"SpecCompiler error: emitted unwrapped external node in agent '{name}'")

        return graph
