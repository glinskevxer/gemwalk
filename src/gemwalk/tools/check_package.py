"""The package agrees with itself about what it is and what it exports.

Three things drift apart quietly. The version in ``pyproject.toml`` and the one
in ``__init__.py``, because only one of them is what ``pip`` shows. The names in
an ``__all__`` and the names actually defined, because deleting a function does
not delete its export. The order of an ``__all__`` is left to ruff, which has
an opinion about it and is right. And the direct dependencies and the constraints file,
because adding a dependency is one line and remembering to pin its closure is
not.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib

from gemwalk import __version__
from gemwalk.tools.walker import Module, modules, repo_root, report

PIN = re.compile(r"^([A-Za-z0-9._-]+)\s*==")


def pyproject() -> dict[str, object]:
    """The project table out of pyproject.toml."""
    with (repo_root() / "pyproject.toml").open("rb") as handle:
        loaded = tomllib.load(handle)
    project = loaded.get("project", {})
    return dict(project) if isinstance(project, dict) else {}


def exported(module: Module) -> list[str] | None:
    """The names a module puts in ``__all__``, or nothing if it has none."""
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "__all__" not in targets:
            continue
        if isinstance(node.value, ast.List | ast.Tuple):
            return [
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
    return None


def defined(module: Module) -> set[str]:
    """Every name a module defines or imports at the top level."""
    names: set[str] = set()
    for node in module.tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return names


def export_faults() -> list[str]:
    """Every name exported by a module that the module does not define."""
    faults: list[str] = []
    for module in modules():
        names = exported(module)
        if names is None:
            continue
        have = defined(module)
        for name in names:
            if name not in have:
                faults.append(f"{module.relative}: __all__ names {name}, which is not here")
        for name in sorted(set(names)):
            if names.count(name) > 1:
                faults.append(f"{module.relative}: __all__ names {name} twice")
    return faults


def version_faults() -> list[str]:
    """Every place the version is written that does not agree with the package."""
    project = pyproject()
    written = project.get("version")
    if written != __version__:
        return [f"pyproject says version {written!r} and the package says {__version__!r}"]
    return []


def pinned() -> set[str]:
    """Every distribution named in the constraints file."""
    path = repo_root() / "constraints.txt"
    if not path.exists():
        return set()
    found: set[str] = set()
    for line in path.read_text().splitlines():
        match = PIN.match(line.strip())
        if match is not None:
            found.add(match.group(1).lower().replace("_", "-"))
    return found


def dependency_faults() -> list[str]:
    """Every direct dependency the constraints file does not pin."""
    project = pyproject()
    direct: list[str] = []
    listed = project.get("dependencies")
    if isinstance(listed, list):
        direct.extend(str(item) for item in listed)
    extras = project.get("optional-dependencies")
    if isinstance(extras, dict):
        for group in extras.values():
            if isinstance(group, list):
                direct.extend(str(item) for item in group)
    have = pinned()
    faults: list[str] = []
    for requirement in direct:
        match = PIN.match(requirement)
        if match is None:
            faults.append(f"{requirement!r} is not pinned to one version")
            continue
        name = match.group(1).lower().replace("_", "-")
        if name not in have:
            faults.append(f"{name} is a dependency and constraints.txt does not pin it")
    return faults


def main() -> int:
    """Check the version, the exports and the pins all agree."""
    return report("check_package", version_faults() + export_faults() + dependency_faults())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
