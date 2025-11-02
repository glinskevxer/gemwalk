"""Every module in the package is named by some test.

Coverage answers a different question. It says a line ran, which it will do for
a module that only ever gets dragged in by something else importing it. This
asks whether anybody wrote a test *about* the module, which is the question you
actually want answered before shipping it.
"""

from __future__ import annotations

import sys

from gemwalk.tools.walker import modules, report, suite_modules

SKIP = frozenset(
    {
        "gemwalk",
        "gemwalk.model",
        "gemwalk.service",
        "gemwalk.store",
        "gemwalk.report",
        "gemwalk.cli",
        "gemwalk.tools",
    }
)


def named_by_the_suite() -> set[str]:
    """Every module of this package that some test file imports by name."""
    named: set[str] = set()
    for module in suite_modules():
        for imported in module.imports():
            if imported.startswith("gemwalk"):
                named.add(imported)
    return named


def faults(named: set[str]) -> list[str]:
    """Every module of the package that no test file imports."""
    return [
        f"{module.relative}: nothing in the suite imports {module.name}"
        for module in modules()
        if module.name not in SKIP and module.name not in named
    ]


def main() -> int:
    """Check nothing in the package is a module nobody wrote a test about."""
    return report("check_tests", faults(named_by_the_suite()))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
