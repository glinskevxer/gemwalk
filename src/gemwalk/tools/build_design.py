"""Write the map of the package out of the package.

``docs/design.md`` is a list of every module in layer order with the first
sentence of its own docstring beside it. It is generated rather than written
because a hand written architecture document describes the architecture on the
day somebody wrote it, and this one cannot: a module added without a docstring
fails ``check_docstrings``, and a module added without a layer fails
``check_layers``, so anything that reaches this document has already said what
it is and where it sits.

Run with ``--check`` it compares instead of writing, which is what ci does.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict

from gemwalk.tools.check_layers import LAYERS, layer_of
from gemwalk.tools.walker import Module, modules, repo_root

TARGET = "docs/design.md"
HEADER = """# How the package is put together

Written by `gemwalk.tools.build_design` out of the modules themselves. Do not
edit: change a docstring and run the tool.

Imports only ever run downhill. A module may reach the layers under it and no
further, which is what `gemwalk.tools.check_layers` holds. The tools sit outside
the whole thing and may reach anything, because looking at everything is what
they are for.
"""

NAMES = {
    0: "The foundation: quantities, dates, the regulation itself",
    1: "The model: the things the desk keeps records about",
    2: "The store: rows, and the readings worked out of them",
    3: "The desks: everything that looks at more than one record",
    4: "The paperwork",
    5: "The command line",
    9: "The tools, which are not part of the package",
}


def first_sentence(module: Module) -> str:
    """The first sentence of a module's docstring, on one line."""
    said = ast.get_docstring(module.tree) or ""
    first = said.strip().split("\n\n")[0].replace("\n", " ").strip()
    return first if first.endswith(".") else first + "."


def grouped() -> dict[int, list[Module]]:
    """Every module in the package, gathered by the layer it sits in."""
    found: dict[int, list[Module]] = defaultdict(list)
    for module in modules():
        if module.name.endswith("__init__") or module.name == "gemwalk":
            continue
        layer = layer_of(module.name)
        if layer is None:
            continue
        found[layer].append(module)
    return found


def build() -> str:
    """The whole document, as text."""
    lines = [HEADER.rstrip()]
    by_layer = grouped()
    for layer in sorted(by_layer):
        lines.extend(["", f"## Layer {layer} — {NAMES.get(layer, 'unnamed')}", ""])
        for module in sorted(by_layer[layer], key=lambda m: m.name):
            lines.append(f"- **`{module.name}`** — {first_sentence(module)}")
    lines.extend(["", "## What each part may reach", "", "| part | layer |", "| --- | --- |"])
    for part, layer in sorted(LAYERS.items(), key=lambda pair: (pair[1], pair[0])):
        lines.append(f"| `gemwalk.{part}` | {layer} |")
    return "\n".join(lines) + "\n"


def written() -> str:
    """What the file on disk says, or an empty string if there is none."""
    path = repo_root() / TARGET
    return path.read_text() if path.exists() else ""


def update() -> int:
    """Write the document out."""
    path = repo_root() / TARGET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build())
    print(f"build_design: wrote {TARGET}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Write the document, or check the one on disk is current."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" not in args:
        return update()
    if written() == build():
        print("build_design: nothing to report")
        return 0
    print(f"build_design: {TARGET} is out of date, run this tool with no arguments")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
