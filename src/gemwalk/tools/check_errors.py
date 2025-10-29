"""Every refusal this package makes is one of its own.

A ``ValueError`` out of a service tells the caller nothing except that
something went wrong somewhere. The package's own tree carries what was refused
and why, which is what a message printed at a person needs, and it lets the
command line turn any of them into a line of text with no traceback in exactly
one place.

The tools are allowed to raise whatever they like. They are not part of the
package's surface and nothing catches them.
"""

from __future__ import annotations

import ast
import sys

from gemwalk.tools.walker import Module, modules, report

BUILTINS = frozenset(
    {
        "Exception",
        "BaseException",
        "ValueError",
        "TypeError",
        "KeyError",
        "IndexError",
        "RuntimeError",
        "AttributeError",
        "NotImplementedError",
        "AssertionError",
    }
)
ALLOWED_MODULES = frozenset({"gemwalk.errors"})
ALLOWED_NAMES = frozenset({"NotImplementedError"})
ALLOWED_PACKAGES = frozenset({"tools"})


def raised_name(node: ast.Raise) -> str | None:
    """What a raise statement raises, by name, or nothing if it re raises."""
    thrown = node.exc
    if thrown is None:
        return None
    if isinstance(thrown, ast.Call):
        thrown = thrown.func
    if isinstance(thrown, ast.Name):
        return thrown.id
    if isinstance(thrown, ast.Attribute):
        return thrown.attr
    return None


def faults_in(module: Module) -> list[str]:
    """Every builtin exception raised in one module."""
    if module.name in ALLOWED_MODULES or module.package in ALLOWED_PACKAGES:
        return []
    found: list[str] = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Raise):
            continue
        name = raised_name(node)
        if name in BUILTINS and name not in ALLOWED_NAMES:
            found.append(f"{module.relative}:{node.lineno}: raises {name}, not one of ours")
    return found


def main() -> int:
    """Check every raise in the package raises one of the package's own."""
    faults: list[str] = []
    for module in modules():
        faults.extend(faults_in(module))
    return report("check_errors", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
