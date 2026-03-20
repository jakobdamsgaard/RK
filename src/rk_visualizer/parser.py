from __future__ import annotations

import ast
import math
from collections.abc import Callable, Iterable


class ExpressionCompilationError(ValueError):
    """Raised when an expression contains unsupported syntax."""


SAFE_NAMES: dict[str, float | Callable[..., float]] = {
    "abs": abs,
    "min": min,
    "max": max,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "sqrt": math.sqrt,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
}


ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.IfExp,
    ast.Compare,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
)


class SafeExpressionValidator(ast.NodeVisitor):
    def __init__(self, variable_names: Iterable[str]) -> None:
        self.variable_names = set(variable_names)
        self.available_names = self.variable_names | set(SAFE_NAMES)

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, ALLOWED_NODES):
            raise ExpressionCompilationError(
                f"Unsupported syntax: {node.__class__.__name__}."
            )
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id not in self.available_names:
            raise ExpressionCompilationError(f"Unknown name: {node.id}.")

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            raise ExpressionCompilationError("Only direct function calls are allowed.")
        if node.func.id not in SAFE_NAMES or not callable(SAFE_NAMES[node.func.id]):
            raise ExpressionCompilationError(f"Function is not allowed: {node.func.id}.")
        if node.keywords:
            raise ExpressionCompilationError("Keyword arguments are not supported.")
        self.generic_visit(node)


def compile_expression(
    expression: str,
    variable_names: tuple[str, ...] = ("t", "y"),
) -> Callable[..., float]:
    stripped = expression.strip()
    if not stripped:
        raise ExpressionCompilationError("Expression cannot be empty.")

    try:
        parsed = ast.parse(stripped, mode="eval")
    except SyntaxError as error:
        raise ExpressionCompilationError(str(error)) from error

    SafeExpressionValidator(variable_names).visit(parsed)
    compiled = compile(parsed, "<expression>", "eval")

    def evaluate(*args: float) -> float:
        if len(args) != len(variable_names):
            raise TypeError(
                f"Expected {len(variable_names)} variables, received {len(args)}."
            )
        local_names = dict(zip(variable_names, args, strict=True))
        value = eval(compiled, {"__builtins__": {}}, {**SAFE_NAMES, **local_names})
        return float(value)

    return evaluate

