"""Tests for SpecCompiler and Static External Node Wrapping Checks (Phase 4)."""

import pytest
from agent_factory.build.compiler import SpecCompiler
from agent_factory.templates.loader import TemplateLoader


def test_compiler_static_check_all_external_nodes_wrapped():
    """Static check test: verify compiler cannot emit an external node without a governed wrapper."""
    loader = TemplateLoader()
    template = loader.resolve("c-suite-advisory")
    spec = template.instantiate({"name": "c-suite-agent"})

    compiler = SpecCompiler()
    graph = compiler.compile(spec)

    # 1. Verification function returns True
    assert graph.verify_no_unwrapped_external_nodes() is True

    # 2. Inspect external nodes directly
    ext_nodes = graph.get_external_nodes()
    assert len(ext_nodes) > 0
    for node in ext_nodes:
        assert node.is_external is True
        assert node.governed_wrapper is not None, f"Node {node.node_id} is external but has no governed wrapper!"


def test_compiler_handles_dag_steps():
    spec = {
        "metadata": {"name": "multi-step-agent", "version": "1.0.0"},
        "workflow": {
            "type": "sequential",
            "steps": [
                {"id": "step_val", "kind": "validate"},
                {"id": "step_tool1", "kind": "tool", "tool": "web.fetch_page"},
                {"id": "step_tool2", "kind": "tool", "tool": "doc.generate"},
                {"id": "step_rep", "kind": "report"}
            ]
        }
    }
    compiler = SpecCompiler()
    graph = compiler.compile(spec)

    assert len(graph.nodes) == 4
    ext_nodes = graph.get_external_nodes()
    assert len(ext_nodes) == 2
    assert {n.node_id for n in ext_nodes} == {"step_tool1", "step_tool2"}
    assert graph.verify_no_unwrapped_external_nodes() is True
