"""Safe scientific expression evaluator using Python AST."""

from __future__ import annotations

import ast
import math
from typing import Any, Callable


class EvaluationError(ValueError):
    """Raised when an expression cannot be evaluated safely."""


_ALLOWED_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

_ALLOWED_FUNCTIONS: dict[str, Callable[..., float]] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": math.pow,
    "fabs": math.fabs,
    "factorial": math.factorial,
    "degrees": math.degrees,
    "radians": math.radians,
    "floor": math.floor,
    "ceil": math.ceil,
}

_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}


class _Evaluator(ast.NodeVisitor):
    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> float:
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise EvaluationError(f"Operator not allowed: {op_type.__name__}")
        left = self.visit(node.left)
        right = self.visit(node.right)
        return float(_ALLOWED_BINOPS[op_type](left, right))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise EvaluationError(f"Unary operator not allowed: {op_type.__name__}")
        value = self.visit(node.operand)
        return float(_ALLOWED_UNARYOPS[op_type](value))

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise EvaluationError("Only direct function calls are allowed")
        fn_name = node.func.id
        fn = _ALLOWED_FUNCTIONS.get(fn_name)
        if fn is None:
            raise EvaluationError(f"Function not allowed: {fn_name}")
        args = [self.visit(arg) for arg in node.args]
        if node.keywords:
            raise EvaluationError("Keyword arguments are not allowed")
        if fn_name == "factorial":
            if len(args) != 1:
                raise EvaluationError("factorial() takes exactly one argument")
            n = args[0]
            if not float(n).is_integer():
                raise EvaluationError("factorial() only accepts integers")
            args = [int(n)]
        try:
            return float(fn(*args))
        except Exception as exc:
            raise EvaluationError(str(exc)) from exc

    def visit_Name(self, node: ast.Name) -> float:
        if node.id in _ALLOWED_CONSTANTS:
            return float(_ALLOWED_CONSTANTS[node.id])
        raise EvaluationError(f"Unknown identifier: {node.id}")

    def visit_Constant(self, node: ast.Constant) -> float:
        value = node.value
        if isinstance(value, (int, float)):
            return float(value)
        raise EvaluationError("Only numeric constants are allowed")

    def generic_visit(self, node: ast.AST) -> Any:
        raise EvaluationError(f"Expression component not allowed: {type(node).__name__}")


def evaluate_expression(expression: str) -> float:
    """Evaluate a scientific expression safely.

    Args:
        expression: Mathematical expression.

    Returns:
        Computed result as float.

    Raises:
        EvaluationError: For unsafe or invalid expressions.
    """

    stripped = expression.strip()
    if not stripped:
        raise EvaluationError("Expression cannot be empty")

    try:
        tree = ast.parse(stripped, mode="eval")
    except SyntaxError as exc:
        raise EvaluationError("Invalid syntax") from exc

    evaluator = _Evaluator()
    return evaluator.visit(tree)
