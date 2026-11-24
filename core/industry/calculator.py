"""
Declarative Domain Calculator Evaluator
Evaluates domain formulas AST-safely using predefined arithmetic operators.
Supports named data sources, input validation, and golden test qualification.
"""

import ast
import operator
from typing import Dict, Any, List, Union

# Safe AST operators allowed in formula execution
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class UnsafeFormulaError(ValueError):
    """Raised when an expression contains non-arithmetic AST nodes."""
    pass


class SafeMathEvaluator(ast.NodeVisitor):
    """Evaluates mathematical AST trees strictly without arbitrary code execution."""

    def __init__(self, variables: Dict[str, Union[int, float]]):
        self.variables = variables

    def visit(self, node: ast.AST) -> Union[int, float]:
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise UnsafeFormulaError(f"Unsupported constant type: {type(node.value)}")
        elif isinstance(node, ast.Name):
            if node.id in self.variables:
                val = self.variables[node.id]
                if not isinstance(val, (int, float)):
                    raise ValueError(f"Variable '{node.id}' must be numeric, got {type(val)}")
                return val
            raise KeyError(f"Undefined formula variable '{node.id}'")
        elif isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    return 0.0  # Return zero on divide-by-zero to maintain robustness
                return SAFE_OPERATORS[op_type](left, right)
            raise UnsafeFormulaError(f"Unsupported binary operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            operand = self.visit(node.operand)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](operand)
            raise UnsafeFormulaError(f"Unsupported unary operator: {op_type}")
        else:
            raise UnsafeFormulaError(f"Unsafe AST node encountered: {type(node).__name__}")


class DomainCalculator:
    """Executes a single declarative domain formula."""

    def __init__(self, calc_spec: Dict[str, Any]):
        self.spec = calc_spec
        self.calculator_id = calc_spec["calculator_id"]
        self.name = calc_spec.get("name", self.calculator_id)
        self.formula = calc_spec["formula"]
        self.data_source = calc_spec.get("data_source", "generic_folio")
        self.golden_tests = calc_spec.get("golden_tests", [])

        # Parse AST at initialization to verify formula safety
        try:
            self._ast = ast.parse(self.formula, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Syntax error in formula '{self.formula}': {exc}")

        # Validate that all nodes in AST are safe arithmetic nodes
        allowed_node_types = (
            ast.Expression,
            ast.Constant,
            ast.Name,
            ast.BinOp,
            ast.UnaryOp,
            ast.Load,
        ) + tuple(SAFE_OPERATORS.keys())
        for node in ast.walk(self._ast):
            if not isinstance(node, allowed_node_types):
                raise UnsafeFormulaError(f"Unsafe node '{type(node).__name__}' in formula '{self.formula}'")
            if isinstance(node, ast.BinOp) and type(node.op) not in SAFE_OPERATORS:
                raise UnsafeFormulaError(f"Unsafe binary operator '{type(node.op).__name__}' in formula '{self.formula}'")
            if isinstance(node, ast.UnaryOp) and type(node.op) not in SAFE_OPERATORS:
                raise UnsafeFormulaError(f"Unsafe unary operator '{type(node.op).__name__}' in formula '{self.formula}'")

    def evaluate(self, inputs: Dict[str, Union[int, float]]) -> float:
        """Evaluates formula with provided input variables."""
        evaluator = SafeMathEvaluator(inputs)
        return float(evaluator.visit(self._ast))

    def run_golden_tests(self) -> Dict[str, Any]:
        """Runs all declared golden test cases and asserts output matches expected within tolerance."""
        passed = 0
        failed = 0
        details = []

        for i, test in enumerate(self.golden_tests):
            inputs = test.get("inputs", {})
            expected = float(test.get("expected_output", 0.0))
            tolerance = float(test.get("tolerance", 0.001))

            actual = self.evaluate(inputs)
            diff = abs(actual - expected)
            is_pass = diff <= tolerance

            if is_pass:
                passed += 1
            else:
                failed += 1

            details.append({
                "test_index": i,
                "inputs": inputs,
                "expected": expected,
                "actual": actual,
                "diff": diff,
                "passed": is_pass
            })

        return {
            "calculator_id": self.calculator_id,
            "total_tests": len(self.golden_tests),
            "passed": passed,
            "failed": failed,
            "status": "PASS" if failed == 0 else "FAIL",
            "details": details
        }
