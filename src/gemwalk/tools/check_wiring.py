"""Every public method on a desk has a caller.

A service method with green tests and nobody calling it is a draft. It reads
like part of the package, it is covered, and the behaviour it implements has
never once happened in the running program.

A caller is anything outside the service layer: a report, the command line, a
tool, or the test suite. The suite counts, because a method the suite calls is
at least one somebody exercised on purpose, but those are printed separately so
the difference between wired up and merely tested stays visible.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field

from gemwalk.tools.walker import Module, modules, report, suite_modules


@dataclass
class Surface:
    """Which methods exist, and every name that is called anywhere."""

    methods: dict[str, str] = field(default_factory=dict)
    called_in_package: set[str] = field(default_factory=set)
    called_in_suite: set[str] = field(default_factory=set)


def methods_of(module: Module) -> dict[str, str]:
    """Every public method defined on a class in one module."""
    found: dict[str, str] = {}
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for body in node.body:
            if not isinstance(body, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if body.name.startswith("_"):
                continue
            found[f"{node.name}.{body.name}"] = f"{module.relative}:{body.lineno}"
    return found


def calls_in(module: Module) -> set[str]:
    """Every attribute name that is reached for in one module."""
    return {node.attr for node in ast.walk(module.tree) if isinstance(node, ast.Attribute)}


def survey(under: str = "service") -> Surface:
    """Read the desks and everything that could be calling them."""
    found = Surface()
    for module in modules(under):
        found.methods.update(methods_of(module))
    for module in modules():
        if module.package == under:
            continue
        found.called_in_package |= calls_in(module)
    for module in suite_modules():
        found.called_in_suite |= calls_in(module)
    return found


def faults(found: Surface) -> list[str]:
    """Every method with no caller, and every one only the suite calls."""
    out: list[str] = []
    for name, where in sorted(found.methods.items()):
        method = name.split(".", 1)[1]
        if method in found.called_in_package:
            continue
        if method in found.called_in_suite:
            out.append(f"{where}: {name} is only ever called by the suite")
        else:
            out.append(f"{where}: {name} has no caller at all")
    return out


def main() -> int:
    """Check every public desk method is called from outside the service layer."""
    return report("check_wiring", faults(survey()))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
