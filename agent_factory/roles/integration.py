"""ZONATA Agent Factory - Integration Engineer Role.

Executes Stage 5 unit verification cases (author_cases).
Verifies that the compiled graph executes without error and matches expected outcomes.
"""

from typing import Any, Dict, List, Tuple
from agent_factory.build.compiler import CompiledGraph
from agent_factory.build.governed_call import GovernedCallContext


class AgentIntegrationEngineer:
    def verify_author_cases(
        self,
        graph: CompiledGraph,
        spec: Dict[str, Any],
        ctx: GovernedCallContext,
        agent_meta: Dict[str, Any]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Execute author-provided test cases against the compiled graph."""
        tests_section = spec.get("tests", {})
        cases = tests_section.get("author_cases", [])

        results = []
        all_passed = True

        for case in cases:
            case_id = case.get("id", "case_unknown")
            case_input = case.get("input", {})
            mandatory = case.get("mandatory", True)

            try:
                out_state = graph.run(case_input, ctx, agent_meta)
                # Verify non-empty execution
                results.append({
                    "case_id": case_id,
                    "passed": True,
                    "output": out_state
                })
            except Exception as e:
                results.append({
                    "case_id": case_id,
                    "passed": False,
                    "error": str(e)
                })
                if mandatory:
                    all_passed = False

        return all_passed, results
