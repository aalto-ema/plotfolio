"""Small arithmetic expression language; project expressions never execute Python."""

import ast
import operator

import numpy as np

FUNCTIONS = {
    name: getattr(np, name)
    for name in (
        "sin",
        "cos",
        "tan",
        "exp",
        "log",
        "log10",
        "sqrt",
        "abs",
        "minimum",
        "maximum",
        "where",
    )
}
BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
COMPARE = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}


def expression(text, variables, column_lookup=None):
    if len(text) > 2000:
        raise ValueError("Expression is too long.")
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as error:
        raise ValueError("Invalid expression syntax.") from error
    if sum(1 for _ in ast.walk(tree)) > 150:
        raise ValueError("Expression is too complex.")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (float, int, bool):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if isinstance(node, ast.Name) and node.id in ("pi", "e"):
            return getattr(np, node.id)
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            # NumPy arithmetic avoids arbitrarily large Python integer powers.
            return BINARY[type(node.op)](
                np.asarray(visit(node.left)), np.asarray(visit(node.right))
            )
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -visit(node.operand) if isinstance(node.op, ast.USub) else visit(node.operand)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE:
            return COMPARE[type(node.ops[0])](visit(node.left), visit(node.comparators[0]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            if (
                node.func.id == "col"
                and column_lookup
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                return column_lookup(node.args[0].value)
            if node.func.id in FUNCTIONS:
                return FUNCTIONS[node.func.id](*[visit(arg) for arg in node.args])
        raise ValueError(
            "Use numeric columns, arithmetic, comparisons, or supported math functions only."
        )

    with np.errstate(all="ignore"):
        return visit(tree)
