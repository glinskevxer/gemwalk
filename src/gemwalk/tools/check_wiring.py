"""Every public method on a desk has a caller.

A service method with green tests and nobody calling it is a draft. It reads
like part of the package, it is covered, and the behaviour it implements has
never once happened in the running program.

A caller is any module other than the one that defines the method: another
desk, a report, the command line, a tool, or the test suite. It has to be
another module, because a method whose only caller is the class it lives on is
private with a public name. The suite counts, because a method the suite calls
is at least one somebody exercised on purpose, but those are printed separately
so the difference between wired up and merely tested stays visible.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field

from gemwalk.tools.walker import Module, modules, report, suite_modules


@dataclass
class Surface:
    """Which methods exist, where, and which module calls each name."""

    methods: dict[str, str] = field(default_factory=dict)
    homes: dict[str, str] = field(default_factory=dict)
    callers: dict[str, set[str]] = field(default_factory=dict)
    called_in_suite: set[str] = field(default_factory=set)

    def called_elsewhere(self, method: str, home: str) -> bool:
        """True when some module other than *home* reaches for this name."""
        return bool(self.callers.get(method, set()) - {home})


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
        for name, where in methods_of(module).items():
            found.methods[name] = where
            found.homes[name] = module.name
    for module in modules():
        for name in calls_in(module):
            found.callers.setdefault(name, set()).add(module.name)
    for module in suite_modules():
        found.called_in_suite |= calls_in(module)
    return found


def faults(found: Surface) -> list[str]:
    """Every method with no caller, and every one only the suite calls."""
    out: list[str] = []
    for name, where in sorted(found.methods.items()):
        method = name.split(".", 1)[1]
        if found.called_elsewhere(method, found.homes.get(name, "")):
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
