"""Sql lives in the store and nowhere else.

One command was found writing its own query against ``sqlite_master`` because
the repository it needed did not have a method for it. It worked. It also meant
the shape of a table was known in two places, and the second one was not going
to be updated by a migration.

The check reads every string constant in the package and looks for the words a
statement starts with. The store may say them. The migrations are the store.
Nothing else may.
"""

from __future__ import annotations

import ast
import re
import sys

from gemwalk.tools.walker import Module, modules, report

# Case matters. Every statement in this package is written with its keywords in
# capitals, and matching either case turns an ordinary sentence beginning with
# the word "update" into a finding.
STATEMENTS = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|PRAGMA)\b")
# The tools are allowed to ask sqlite about itself, because that is what a
# check of the schema is. Nothing else outside the store may say any of these.
ALLOWED = ("store", "tools")


def strings_in(module: Module) -> list[tuple[int, str]]:
    """Every string constant in a module, with the line it is written on."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append((node.lineno, node.value))
    return found


def faults_in(module: Module) -> list[str]:
    """Every statement written outside the store."""
    if module.package in ALLOWED:
        return []
    found: list[str] = []
    for lineno, text in strings_in(module):
        if STATEMENTS.match(text):
            first = text.strip().splitlines()[0][:60]
            found.append(f"{module.relative}:{lineno}: sql outside the store: {first!r}")
    return found


def main() -> int:
    """Check no module outside the store writes a statement."""
    faults: list[str] = []
    for module in modules():
        faults.extend(faults_in(module))
    return report("check_sql", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
