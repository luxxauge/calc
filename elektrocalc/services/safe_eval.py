from __future__ import annotations

import ast
from decimal import Decimal
from typing import Any

ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Num,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd,
    ast.Call,
)

ALLOWED_FUNCS = {
    "min": min,
    "max": max,
    "round": round,
    "int": int,
    "float": float,
    "ceil": lambda x: int(-(-float(x)//1)),
    "floor": lambda x: int(float(x)//1),
}

MAX_LEN = 200


def safe_eval(expr: str, variables: dict[str, Any]) -> Decimal:
    expr = (expr or "0").strip()
    if len(expr) > MAX_LEN:
        raise ValueError("expression too long")
    if not expr:
        return Decimal("0")
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError("expression contains disallowed syntax")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
                raise ValueError("only simple safe functions allowed")
    code = compile(tree, "<expr>", "eval")
    env = {"__builtins__": {}}
    env.update(ALLOWED_FUNCS)
    env.update(variables)
    val = eval(code, env, {})
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")
