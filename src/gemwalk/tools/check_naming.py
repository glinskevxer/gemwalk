"""No name in this package is a word that says nothing.

A function called ``process``, a class called ``Manager``, a variable called
``data``: each of them names the shape of the code rather than the thing it is
about, and in a package where the whole point is that a reading is not a
finding and a finding is not a work order, that is a real cost.

The check reads identifiers out of the syntax tree rather than searching the
text, so a docstring may say the words and an attribute somebody else's library
owns is not this package's problem.
"""

from __future__ import annotations

import ast
import sys

from gemwalk.tools.walker import Module, modules, report

VAGUE = frozenset(
    {
        "data",
        "info",
        "manager",
        "helper",
        "helpers",
        "util",
        "utils",
        "misc",
        "stuff",
        "tmp",
        "temp",
        "obj",
        "thing",
        "things",
        "val",
        "vals",
        "res",
        "ret",
        "handler",
        "wrapper",
        "process",
        "do",
    }
)


def is_vague(name: str) -> bool:
    """True when a name is one of the words that say nothing."""
    lowered = name.lower().strip("_")
    if lowered in VAGUE:
        return True
    return any(lowered.startswith(f"{word}_") or lowered.endswith(f"_{word}") for word in VAGUE)


def names_in(module: Module) -> list[tuple[int, str]]:
    """Every identifier this module defines, with the line it is defined on."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.append((node.lineno, node.name))
            if isinstance(node, ast.ClassDef):
                continue
            for argument in [*node.args.args, *node.args.kwonlyargs, *node.args.posonlyargs]:
                found.append((argument.lineno, argument.arg))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found.append((target.lineno, target.id))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.append((node.target.lineno, node.target.id))
    return found


def faults_in(module: Module) -> list[str]:
    """Every name in one module that says nothing."""
    found: list[str] = []
    stem = module.name.rsplit(".", 1)[-1]
    if is_vague(stem):
        found.append(f"{module.relative}: the module itself is called {stem}")
    for lineno, name in names_in(module):
        if is_vague(name):
            found.append(f"{module.relative}:{lineno}: {name} says nothing")
    return found


def main() -> int:
    """Check every name in the package says something."""
    faults: list[str] = []
    for module in modules():
        faults.extend(faults_in(module))
    return report("check_naming", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
