"""ZONATA Sovereign Core — Deterministic Calculator Tool.

Implements OpenCode Step 2E (Requirement 2 & 6):
- Exact integer / Decimal arithmetic in pure code, never delegated to an LLM.
- Safe AST evaluation permitting only numeric literals and standard arithmetic operators.
- Rejects any syntax execution, variable access, function calls, or injections.
- Returns exact Decimal precision.
"""

from __future__ import annotations
import ast
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, Union
from pydantic import BaseModel, Field

from core.authority.types import ActionClass
from core.tools.contract import ToolContract, SideEffectClass


class CalculatorInput(BaseModel):
    expression: str = Field(..., description="Mathematical expression to evaluate (e.g. '100.50 * 1.05 + 12.34')")
    precision: Optional[int] = Field(None, description="Optional decimal places to round result")


class CalculatorOutput(BaseModel):
    expression: str
    result: str = Field(..., description="Exact string representation of Decimal result")
    is_integer: bool = Field(..., description="Whether the exact result is a whole integer")
    minor_units: Optional[int] = Field(None, description="Integer minor units (if precision 2 is used or cents)")


_ALLOWED_OPERATORS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a ** b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: a,
}


def evaluate_decimal_expression(expression: str, precision: Optional[int] = None) -> Decimal:
    """Safely and deterministically evaluates an arithmetic expression into an exact Decimal."""
    clean_expr = expression.strip()
    if not clean_expr:
        raise ValueError("Empty mathematical expression")

    try:
        parsed = ast.parse(clean_expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Malformed mathematical expression: {e}")

    def _eval_node(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, str)):
                try:
                    return Decimal(str(node.value))
                except InvalidOperation:
                    raise ValueError(f"Cannot parse constant as Decimal: {node.value}")
            raise ValueError(f"Disallowed constant type in expression: {type(node.value).__name__}")
        elif isinstance(node, ast.UnaryOp):
            op_cls = type(node.op)
            if op_cls in _ALLOWED_OPERATORS:
                operand_val = _eval_node(node.operand)
                return _ALLOWED_OPERATORS[op_cls](operand_val)
            raise ValueError(f"Unsupported unary operator: {op_cls.__name__}")
        elif isinstance(node, ast.BinOp):
            op_cls = type(node.op)
            if op_cls in _ALLOWED_OPERATORS:
                left_val = _eval_node(node.left)
                right_val = _eval_node(node.right)
                if op_cls in (ast.Div, ast.FloorDiv, ast.Mod) and right_val == 0:
                    raise ZeroDivisionError("Division by zero in deterministic calculator")
                return _ALLOWED_OPERATORS[op_cls](left_val, right_val)
            raise ValueError(f"Unsupported binary operator: {op_cls.__name__}")
        else:
            raise ValueError(f"Forbidden AST element in mathematical expression: {type(node).__name__}")

    res = _eval_node(parsed)

    if precision is not None:
        q = Decimal(10) ** -precision
        res = res.quantize(q, rounding=ROUND_HALF_UP)

    return res


class CalculatorTool(ToolContract):
    name = "calculator"
    description = "Deterministic integer / Decimal arithmetic in code, never delegated to model."
    version = "1.0.0"
    side_effect_class = SideEffectClass.READ
    required_capability = "database"
    required_action_class = ActionClass.READ_INTERNAL
    cost_cents = 0
    timeout_seconds = 5.0
    supports_idempotency = True

    input_schema = CalculatorInput
    output_schema = CalculatorOutput

    def execute(
        self,
        tenant_id: str,
        company_id: str,
        principal_id: str,
        args: CalculatorInput,
        idempotency_key: Optional[str] = None,
    ) -> CalculatorOutput:
        dec_val = evaluate_decimal_expression(args.expression, precision=args.precision)
        is_int = (dec_val == dec_val.to_integral())
        minor_units = None
        if args.precision == 2 or (args.precision is None and len(str(dec_val).split(".")[-1]) <= 2):
            try:
                minor_units = int((dec_val * 100).to_integral_value())
            except Exception:
                pass

        return CalculatorOutput(
            expression=args.expression,
            result=str(dec_val),
            is_integer=is_int,
            minor_units=minor_units,
        )
