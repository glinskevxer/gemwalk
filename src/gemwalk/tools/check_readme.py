"""Replay the transcript in the readme instead of trusting it.

A readme with a worked example in it is a readme that is wrong within a month.
The example here is not prose: every ``$ gemwalk`` line in the console block is
run against a fresh book, in order, and what it printed is compared with what
the readme says it printed.

Run with ``--update`` it writes the readme's output back from what the commands
actually did, which turns a rename into a one command fix instead of a stale
document nobody trusts.
"""

from __future__ import annotations

import re
import shlex
import sys
import tempfile
from dataclasses import dataclass

from click.testing import CliRunner

from gemwalk.cli.main import main as tree
from gemwalk.tools.walker import repo_root, report

TARGET = "README.md"
FENCE = re.compile(r"```console\n(.*?)```", re.DOTALL)
PROMPT = "$ gemwalk "


@dataclass
class Step:
    """One command out of the transcript and what the readme says it printed."""

    command: str
    printed: list[str]

    @property
    def words(self) -> list[str]:
        """The command split the way a shell would split it."""
        return shlex.split(self.command)


def parse(text: str) -> list[Step]:
    """Every step of every console block in the readme, in order."""
    steps: list[Step] = []
    for block in FENCE.findall(text):
        for raw in block.splitlines():
            if raw.startswith(PROMPT):
                steps.append(Step(raw[len(PROMPT) :], []))
            elif steps:
                steps[-1].printed.append(raw)
    return steps


BOOK = "northridge.sqlite3"


def replay(steps: list[Step]) -> list[Step]:
    """Run every step against one fresh book and record what it printed.

    The book is opened by a relative name inside a directory the runner throws
    away, because a command that prints where the book is would otherwise put a
    temporary path in the readme and never match again.
    """
    runner = CliRunner()
    played: list[Step] = []
    with tempfile.TemporaryDirectory() as room, runner.isolated_filesystem(temp_dir=room):
        for step in steps:
            result = runner.invoke(tree, ["--book", BOOK, *step.words])
            printed = result.output.rstrip("\n").splitlines()
            if result.exit_code != 0:
                printed.append(f"[exit {result.exit_code}]")
            played.append(Step(step.command, printed))
    return played


def render(text: str, played: list[Step]) -> str:
    """The readme with the transcript's output written back from the replay."""
    steps = iter(played)

    def rewrite(match: re.Match[str]) -> str:
        """One console block, with its output written back from the replay."""
        lines: list[str] = []
        for raw in match.group(1).splitlines():
            if raw.startswith(PROMPT):
                lines.append(raw)
                lines.extend(next(steps).printed)
        return "```console\n" + "\n".join(lines) + "\n```"

    return FENCE.sub(rewrite, text)


def faults(steps: list[Step], played: list[Step]) -> list[str]:
    """Every step whose output is not what the readme says it is."""
    found: list[str] = []
    for said, did in zip(steps, played, strict=True):
        if said.printed != did.printed:
            found.append(
                f"gemwalk {said.command}: the readme says\n"
                + "\n".join(f"      {line}" for line in said.printed)
                + "\n    and it printed\n"
                + "\n".join(f"      {line}" for line in did.printed)
            )
    return found


def main(argv: list[str] | None = None) -> int:
    """Replay the readme, or write its output back from the replay."""
    args = list(sys.argv[1:] if argv is None else argv)
    path = repo_root() / TARGET
    text = path.read_text()
    steps = parse(text)
    if not steps:
        return report("check_readme", [f"{TARGET} has no console block to replay"])
    played = replay(steps)
    if "--update" in args:
        path.write_text(render(text, played))
        print(f"check_readme: replayed {len(steps)} commands into {TARGET}")
        return 0
    return report("check_readme", faults(steps, played))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
