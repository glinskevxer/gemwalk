"""Write the glossary out of the enumerations the package is made of.

Every word this desk uses for a state, a kind or a step is an enumeration
member somewhere. The glossary is built from them, so a state that gets added
and not explained is a line that appears in the document with nothing beside
it, which is easier to notice than a state nobody wrote down at all.
"""

from __future__ import annotations

import sys
from enum import Enum

from gemwalk.model.device import Kind, State
from gemwalk.model.exceedance import Stage
from gemwalk.model.landfill import Cover
from gemwalk.model.liquids import SumpKind
from gemwalk.model.plant import ControlKind
from gemwalk.model.surface import Step
from gemwalk.model.work import Job, Standing
from gemwalk.nmoc import Tier
from gemwalk.rules import Finding
from gemwalk.tools.walker import repo_root

TARGET = "docs/glossary.md"
HEADER = """# The words this desk uses

Written by `gemwalk.tools.build_glossary` out of the enumerations in the
package. Do not edit: add the member and run the tool.
"""

GROUPS: list[tuple[str, str, type[Enum]]] = [
    ("Devices", "what was put in the ground", Kind),
    ("Device states", "where a device is in its life", State),
    ("Cover", "what is on top of an area", Cover),
    ("Findings", "the kinds of reading that put a device out of compliance", Finding),
    ("Exceedance stages", "how far along a wellhead clock is", Stage),
    ("Surface steps", "what a spot on the cover is waiting for", Step),
    ("Control devices", "what burns the gas", ControlKind),
    ("Sumps", "what the condensate is caught in", SumpKind),
    ("Jobs", "what a crew is sent to do", Job),
    ("Work order states", "where an order is", Standing),
    ("Emission rate tiers", "how much of the calculation the site measured", Tier),
]


def build() -> str:
    """The whole glossary, as text."""
    lines = [HEADER.rstrip()]
    for title, blurb, group in GROUPS:
        lines.extend(["", f"## {title}", "", f"{blurb.capitalize()}.", ""])
        for member in group:
            lines.append(f"- **{member.value}** — `{group.__name__}.{member.name}`")
    return "\n".join(lines) + "\n"


def written() -> str:
    """What the file on disk says, or an empty string if there is none."""
    path = repo_root() / TARGET
    return path.read_text() if path.exists() else ""


def update() -> int:
    """Write the glossary out."""
    path = repo_root() / TARGET
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build())
    print(f"build_glossary: wrote {TARGET}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Write the glossary, or check the one on disk is current."""
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" not in args:
        return update()
    if written() == build():
        print("build_glossary: nothing to report")
        return 0
    print(f"build_glossary: {TARGET} is out of date, run this tool with no arguments")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
