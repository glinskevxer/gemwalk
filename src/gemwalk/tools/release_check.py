"""Everything that has to be true before a version is tagged.

It is the last thing ``check.sh`` runs and the last job in ci. Each line of it
is something that has been wrong at least once: a version bumped in one file
and not the other, a changelog with no entry for the version being released, a
console script pointing at a function that was renamed.
"""

from __future__ import annotations

import importlib
import sys

from gemwalk import __version__
from gemwalk.tools.check_package import pyproject
from gemwalk.tools.walker import repo_root, report

REQUIRED = ("README.md", "CHANGELOG.md", "constraints.txt", "check.sh", "migrations.lock")
DOCUMENTS = ("docs/schema.sql", "docs/rules.md", "docs/glossary.md")


def missing_files() -> list[str]:
    """Every file a release has to ship that is not in the checkout."""
    root = repo_root()
    return [f"{name} is missing" for name in (*REQUIRED, *DOCUMENTS) if not (root / name).exists()]


def changelog_faults() -> list[str]:
    """Whether the changelog has an entry for the version being released."""
    path = repo_root() / "CHANGELOG.md"
    if not path.exists():
        return []
    if f"## {__version__}" not in path.read_text():
        return [f"CHANGELOG.md has no entry for {__version__}"]
    return []


def script_faults() -> list[str]:
    """Every console script that does not point at something importable."""
    scripts = pyproject().get("scripts") or {}
    if not isinstance(scripts, dict):
        return []
    faults: list[str] = []
    for name, target in scripts.items():
        module_name, _, attribute = str(target).partition(":")
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            faults.append(f"the {name} script points at {module_name}, which will not import")
            continue
        if attribute and not hasattr(module, attribute):
            faults.append(f"the {name} script points at {target}, and there is no {attribute}")
    return faults


def description_faults() -> list[str]:
    """Whether the package says what it is in both places it has to."""
    project = pyproject()
    faults: list[str] = []
    if not project.get("description"):
        faults.append("pyproject has no description")
    readme = repo_root() / "README.md"
    if readme.exists() and "gemwalk" not in readme.read_text().lower():
        faults.append("README.md does not name the package")
    return faults


def main() -> int:
    """Check everything that has to be true before a version is tagged."""
    faults = missing_files() + changelog_faults() + script_faults() + description_faults()
    return report("release_check", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
