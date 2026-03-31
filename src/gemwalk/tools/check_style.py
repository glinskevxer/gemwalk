"""The writing conventions, held by a tool rather than by remembering them.

Three of these are about the prose and one is about the code.

A docstring's first line ends with a full stop, because it is a sentence and
because every tool that reads docstrings assumes it is one. Nothing left in the
package says TODO, because a note to nobody in particular in a file nobody is
reading is not a plan. Nothing outside the tools and the command line prints,
because a library that prints has decided where its output goes on behalf of
whoever imported it.

The fourth is that nothing outside the tools uses ``assert``. An assertion is
compiled out under ``-O``, so a package that checks a real precondition with one
is a package whose checks disappear in exactly the environment that runs it
fastest. This found two of them writing a column that cannot be blank.
"""

from __future__ import annotations

import ast
import re
import sys

from gemwalk.tools.walker import Module, modules, report

NOTES = re.compile(r"\b(TODO|FIXME|HACK|XXX:)\b")
MAY_PRINT = frozenset({"tools", "cli"})
MAY_ASSERT = frozenset({"tools"})


def docstrings_in(module: Module) -> list[tuple[int, str]]:
    """Every docstring in a module, with the line it starts on."""
    found: list[tuple[int, str]] = []
    said = ast.get_docstring(module.tree)
    if said:
        found.append((1, said))
    for node in ast.walk(module.tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            said = ast.get_docstring(node)
            if said:
                found.append((node.lineno, said))
    return found


def sentence_faults(module: Module) -> list[str]:
    """Every docstring whose first line is not a sentence."""
    faults: list[str] = []
    for lineno, said in docstrings_in(module):
        first = said.strip().splitlines()[0].strip()
        if not first.endswith((".", ":", "?", "!")):
            faults.append(f"{module.relative}:{lineno}: the first line does not end a sentence")
    return faults


def note_faults(module: Module) -> list[str]:
    """Every note to nobody left in the source."""
    faults: list[str] = []
    for number, line in enumerate(module.source().splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#") and NOTES.search(stripped):
            faults.append(f"{module.relative}:{number}: a note to nobody was left here")
    return faults


def print_faults(module: Module) -> list[str]:
    """Every call to print outside the tools and the command line."""
    if module.package in MAY_PRINT:
        return []
    faults: list[str] = []
    for node in ast.walk(module.tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            faults.append(f"{module.relative}:{node.lineno}: a library that prints")
    return faults


def assert_faults(module: Module) -> list[str]:
    """Every assertion outside the tools, which is a check that can vanish."""
    if module.package in MAY_ASSERT:
        return []
    return [
        f"{module.relative}:{node.lineno}: an assert is compiled out under -O"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Assert)
    ]


def faults_in(module: Module) -> list[str]:
    """Everything about how one module is written that breaks a convention."""
    return (
        sentence_faults(module) + note_faults(module) + print_faults(module) + assert_faults(module)
    )


def main() -> int:
    """Check the package is written the way it says it is."""
    faults: list[str] = []
    for module in modules():
        faults.extend(faults_in(module))
    return report("check_style", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
