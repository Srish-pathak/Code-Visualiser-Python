import ast
from typing import Any


class StaticAnalyzer(ast.NodeVisitor):
    """Find simple Python call-signature mismatches."""

    def __init__(self) -> None:
        self.functions: dict[str, int] = {}
        self.bugs: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions[node.name] = len(node.args.args)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in self.functions:
                expected = self.functions[name]
                actual = len(node.args)
                if expected != actual:
                    self.bugs.append(
                        {
                            "line": node.lineno,
                            "severity": "critical",
                            "description":
                                f"Function '{name}' expects "
                                f"{expected} arguments "
                                f"but received {actual}."
                        }
                    )
        self.generic_visit(node)


def analyze_static(code: str, language: str) -> list[dict[str, Any]]:
    """Return static-analysis findings for Python code."""
    if language != "Python":
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    analyzer = StaticAnalyzer()
    analyzer.visit(tree)
    return analyzer.bugs