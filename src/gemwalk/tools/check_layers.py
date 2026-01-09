"""Imports only ever run downhill.

The package is in layers and each one may reach the ones under it and no
further. A model that reaches into the store is a model that cannot be used
without a book, and a store that reaches into a service is a circular import
waiting for somebody to add one more line.

The layers, lowest first: the foundation modules that hold quantities, dates
and the regulation itself; the model; the store; the services; the reports; the
command line. The tools sit outside and may reach anything, because their whole
job is to look at everything.
"""

from __future__ import annotations

import sys

from gemwalk.tools.walker import modules, report

LAYERS: dict[str, int] = {
    "errors": 0,
    "units": 0,
    "clock": 0,
    "rules": 0,
    "ids": 2,
    "assess": 2,
    "nmoc": 1,
    "quality": 0,
    "design": 2,
    "model": 1,
    "store": 2,
    "service": 3,
    "report": 4,
    "cli": 5,
    "tools": 9,
}


def layer_of(name: str) -> int | None:
    """Which layer a dotted module name sits in, or nothing if it is not ours."""
    parts = name.split(".")
    if not parts or parts[0] != "gemwalk":
        return None
    if len(parts) == 1:
        return 0
    return LAYERS.get(parts[1])


def main() -> int:
    """Check every import in the package runs downhill."""
    faults: list[str] = []
    for module in modules():
        mine = layer_of(module.name)
        if mine is None:
            faults.append(f"{module.relative}: no layer is written down for this module")
            continue
        for imported in module.imports():
            theirs = layer_of(imported)
            if theirs is None:
                continue
            if theirs > mine:
                faults.append(
                    f"{module.relative}: layer {mine} imports {imported} at layer {theirs}"
                )
    return report("check_layers", faults)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
