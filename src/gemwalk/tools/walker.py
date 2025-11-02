"""Finding this package's own source, and reading it as syntax trees.

Every check works off the files that are actually in the package directory,
not off an import list, so a module nobody imports is still checked.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


def package_root() -> Path:
    """The directory this package's source lives in."""
    return Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    """The top of the checkout, which is two directories above the package."""
    return package_root().parent.parent


def suite_root() -> Path:
    """The directory the test suite lives in."""
    return repo_root() / "tests"


@dataclass(frozen=True)
class Module:
    """One source file with its parsed tree and the name it imports as."""

    path: Path
    name: str
    tree: ast.Module

    @property
    def relative(self) -> str:
        """The path as it is written in a message, from the checkout root."""
        return str(self.path.relative_to(repo_root()))

    @property
    def package(self) -> str:
        """The part of the name under ``gemwalk``, or an empty string."""
        parts = self.name.split(".")
        return parts[1] if len(parts) > 1 else ""

    def imports(self) -> list[str]:
        """Every module name this one imports, dotted and absolute.

        ``from gemwalk.tools import check_sql`` names two things: the package
        the name came out of and, if the name happens to be a module, that
        module. Both are recorded, because a check that asks whether anybody
        imports a module has to see the second one.
        """
        found: list[str] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                found.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.append(node.module)
                found.extend(f"{node.module}.{alias.name}" for alias in node.names)
        return found


def _name_of(path: Path, root: Path, prefix: str) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join((prefix, *parts)) if parts else prefix


def modules(under: str = "") -> Iterator[Module]:
    """Every source file in the package, in path order."""
    root = package_root()
    start = root / under if under else root
    for path in sorted(start.rglob("*.py")):
        yield Module(path, _name_of(path, root, "gemwalk"), ast.parse(path.read_text()))


def suite_modules() -> Iterator[Module]:
    """Every test file in the suite, in path order."""
    root = suite_root()
    for path in sorted(root.rglob("*.py")):
        yield Module(path, _name_of(path, root, "tests"), ast.parse(path.read_text()))


def report(name: str, faults: list[str]) -> int:
    """Print what a check found and hand back the exit status it should use."""
    if not faults:
        print(f"{name}: nothing to report")
        return 0
    print(f"{name}: {len(faults)} to fix")
    for fault in faults:
        print(f"  {fault}")
    return 1


__all__ = [
    "Module",
    "modules",
    "package_root",
    "repo_root",
    "report",
    "suite_modules",
    "suite_root",
]
