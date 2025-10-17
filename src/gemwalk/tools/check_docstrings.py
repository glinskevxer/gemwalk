"""Every module, class and public function says what it is for.

A private helper does not need one, and a test does not need one on every
function, but anything somebody outside the file can reach does. The check is
worth having because a public name with no sentence beside it is nearly always
a name that was not thought about, not a name that was obvious.
"""

from __future__ import annotations

import ast
import sys

from gemwalk.tools.walker import Module, modules, report

Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


def is_public(name: str) -> bool:
    """True when a name is reachable from outside the module that defines it.

    A dunder is not one of these. ``__str__`` and ``__post_init__`` say what
    they do by being called what they are called, and a rule that demanded a
    sentence on each of them produced sixty of them saying nothing.
    """
    return not name.startswith("_")


def wanted(node: ast.AST) -> bool:
    """True when this node has to carry a docstring."""
    if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        return is_public(node.name)
    return False


def faults_in(module: Module) -> list[str]:
    """Everything in one module that should say what it is for and does not."""
    found: list[str] = []
    if not ast.get_docstring(module.tree):
        found.append(f"{module.relative}: the module has no docstring")
    for node in ast.walk(module.tree):
        if not wanted(node):
            continue
        assert isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        if not ast.get_docstring(node):
            found.append(f"{module.relative}:{node.lineno}: {node.name} has no docstring")
    return found


def main() -> int:
    """Check every module in the package."""
    faults: list[str] = []
    for module in modules():
        faults.extend(faults_in(module))
    return report("check_docstrings", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
