"""The model is frozen, and nothing in the package carries a mutable default.

Every record in the model is a frozen dataclass, and a change to one produces a
new one. That is not a style preference: a service that hands a caller a record
and then mutates it has handed the caller a value that quietly changed, and
half the clocks in this package are worked out by comparing a record to a later
version of itself.

A mutable default argument is the other one. It is shared between every call of
the function, so a list that starts empty stops being empty the first time
anything is put in it, and nothing about the call site suggests that.
"""

from __future__ import annotations

import ast
import sys

from gemwalk.tools.walker import Module, modules, report

FROZEN_PACKAGES = frozenset({"model"})
MUTABLE = (ast.List, ast.Dict, ast.Set)


def is_dataclass(node: ast.ClassDef) -> tuple[bool, bool]:
    """Whether a class is a dataclass, and whether it was frozen."""
    for decorator in node.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        named = call.func if call is not None else decorator
        name = named.attr if isinstance(named, ast.Attribute) else getattr(named, "id", "")
        if name != "dataclass":
            continue
        if call is None:
            return True, False
        for keyword in call.keywords:
            if keyword.arg == "frozen" and isinstance(keyword.value, ast.Constant):
                return True, bool(keyword.value.value)
        return True, False
    return False, False


def frozen_faults(module: Module) -> list[str]:
    """Every record in the model that can be changed after it is made."""
    if module.package not in FROZEN_PACKAGES:
        return []
    found: list[str] = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.ClassDef):
            continue
        made, frozen = is_dataclass(node)
        if made and not frozen:
            found.append(f"{module.relative}:{node.lineno}: {node.name} is not frozen")
    return found


def default_faults(module: Module) -> list[str]:
    """Every function in the module with a mutable default argument."""
    found: list[str] = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if isinstance(default, MUTABLE):
                found.append(f"{module.relative}:{node.lineno}: {node.name} has a mutable default")
    return found


def faults_in(module: Module) -> list[str]:
    """Everything wrong with how one module is put together."""
    return frozen_faults(module) + default_faults(module)


def main() -> int:
    """Check the model is frozen and no default is shared between calls."""
    faults: list[str] = []
    for module in modules():
        faults.extend(faults_in(module))
    return report("check_design", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
