"""The command line describes itself, all the way down.

A command with no help is a command nobody outside the team can use, and an
option with no help is worse, because it looks documented until you read it. So
every group, every command and every option carries a sentence, and the check
walks the real click tree rather than the source, which means a command that is
defined and never registered is invisible to it and shows up in check_wiring
instead.

It also walks the shell script the ci job runs and looks every command in it up
in the tree. Nothing else compiles a shell script inside a yaml file, and a
command that was renamed months ago will sit in there being green until
somebody runs it by hand.
"""

from __future__ import annotations

import re
import sys

import click

from gemwalk.cli.main import main as tree
from gemwalk.tools.walker import repo_root, report

WALK = ".github/workflows/ci.yml"
INVOCATION = re.compile(r"^\s*(?:\$\(?\w+\)?\s+)?gemwalk\b(?P<rest>.*)$")


def commands(group: click.Group, prefix: str = "") -> list[tuple[str, click.Command]]:
    """Every command in the tree, deepest last, with its full path."""
    found: list[tuple[str, click.Command]] = []
    for name, command in sorted(group.commands.items()):
        path = f"{prefix}{name}"
        found.append((path, command))
        if isinstance(command, click.Group):
            found.extend(commands(command, f"{path} "))
    return found


def described() -> list[str]:
    """Every command or option in the tree with nothing written about it."""
    faults: list[str] = []
    for path, command in commands(tree):
        if not command.help:
            faults.append(f"{path} says nothing about what it does")
        for parameter in command.params:
            if not isinstance(parameter, click.Option) or parameter.name == "help":
                continue
            if not parameter.help:
                faults.append(f"{path} --{parameter.name} says nothing about what it is")
    return faults


def paths() -> set[str]:
    """Every command path the tree answers to."""
    return {path for path, _ in commands(tree)}


def spoken_in_the_walk() -> list[str]:
    """Every command the ci walk invokes, in the order it invokes them."""
    path = repo_root() / WALK
    if not path.exists():
        return []
    spoken: list[str] = []
    for raw in path.read_text().splitlines():
        match = INVOCATION.match(raw)
        if match is None:
            continue
        words: list[str] = []
        for word in match.group("rest").split():
            if word.startswith(("-", '"')):
                break
            words.append(word)
        if words and words[0] == "--book":
            words = words[2:]
        if words:
            spoken.append(" ".join(words))
    return spoken


def walk_faults() -> list[str]:
    """Every command the ci walk invokes that the tree does not answer to."""
    known = paths()
    faults: list[str] = []
    for spoken in spoken_in_the_walk():
        if spoken in known:
            continue
        head = " ".join(spoken.split()[:2])
        if head in known:
            continue
        faults.append(f"{WALK} runs {spoken!r} and nothing answers to it")
    return faults


def main() -> int:
    """Check the tree describes itself and the ci walk only says real commands."""
    return report("check_cli", described() + walk_faults())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
