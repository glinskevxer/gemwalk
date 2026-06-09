"""The handbook names commands that exist, in an order the tree agrees with.

``docs/operating.md`` is the one document in the repository that is written by
hand rather than generated, because the order the work happens in is not
something the code knows. What the code does know is whether the commands it
names are real, and that is exactly the half of a handbook that rots.

So every indented line in it that starts with ``gemwalk`` is looked up in the
click tree. And every group in the tree has to appear in it at least once,
because a handbook is allowed to leave a command out and is not allowed to
leave a whole part of the job out.
"""

from __future__ import annotations

import re
import sys

import click

from gemwalk.cli.main import main as command_tree
from gemwalk.tools.check_cli import commands, paths
from gemwalk.tools.walker import repo_root, report

TARGET = "docs/operating.md"
NAMED = re.compile(r"^\s{4,}gemwalk\s+(?P<rest>[a-z][a-z0-9 -]*)$")
# The handbook is a sequence and not a reference, so a command it does not name
# is fine. A group it does not name is not: that is a part of the job nobody
# wrote up. These two are exceptions because neither is a part of the job.
NOT_A_JOB = frozenset({"about", "export"})


def named() -> list[str]:
    """Every command the handbook names, in the order it names them."""
    path = repo_root() / TARGET
    if not path.exists():
        return []
    found: list[str] = []
    for line in path.read_text().splitlines():
        match = NAMED.match(line)
        if match is not None:
            found.append(match.group("rest").strip())
    return found


def unknown() -> list[str]:
    """Every command the handbook names that the tree does not answer to."""
    known = paths()
    return [
        f"{TARGET} names {said!r} and nothing answers to it"
        for said in named()
        if said not in known
    ]


def unwritten() -> list[str]:
    """Every group of the tree the handbook never gets to at all."""
    reached = {said.split()[0] for said in named()}
    missing: list[str] = []
    for path, command in commands(command_tree):
        if not isinstance(command, click.Group) or " " in path:
            continue
        if path in NOT_A_JOB or path in reached:
            continue
        missing.append(f"{path} is a whole group and {TARGET} never gets to it")
    return missing


def main() -> int:
    """Check the handbook names real commands and mentions every one of them."""
    path = repo_root() / TARGET
    if not path.exists():
        return report("check_handbook", [f"{TARGET} is missing"])
    if not named():
        return report("check_handbook", [f"{TARGET} names no commands at all"])
    return report("check_handbook", unknown() + unwritten())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
