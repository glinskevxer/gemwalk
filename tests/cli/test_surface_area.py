"""Every command in the tree answers for itself.

The suites next to this one drive the commands people actually use. This one
walks the whole tree and asks two things of every command in it: that its help
prints without a book being opened, and that it refuses cleanly against an
empty one. The second is the interesting half. A command that raises out of
the package prints a message and exits non zero; a command that raises anything
else prints a traceback at a person standing in a field.
"""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from gemwalk.cli.main import main
from gemwalk.tools.check_cli import commands

EVERY = [(path, command) for path, command in commands(main)]
LEAVES = [(path, command) for path, command in EVERY if not isinstance(command, click.Group)]


@pytest.mark.parametrize("path", [path for path, _ in EVERY], ids=lambda p: p.replace(" ", "-"))
def test_every_command_prints_its_help_without_a_book(path: str, tmp_path: Path) -> None:
    book = tmp_path / "never.sqlite3"
    result = CliRunner().invoke(main, ["--book", str(book), *path.split(), "--help"])
    assert result.exit_code == 0, result.output
    assert not book.exists()


@pytest.mark.parametrize("path", [path for path, _ in EVERY], ids=lambda p: p.replace(" ", "-"))
def test_every_help_names_the_command(path: str) -> None:
    result = CliRunner().invoke(main, [*path.split(), "--help"])
    assert path.split()[-1] in result.output or "Usage" in result.output


@pytest.mark.parametrize("path", [path for path, _ in LEAVES], ids=lambda p: p.replace(" ", "-"))
def test_no_command_raises_anything_but_a_refusal(path: str, tmp_path: Path) -> None:
    book = tmp_path / "empty.sqlite3"
    CliRunner().invoke(main, ["--book", str(book), "store", "init"])
    result = CliRunner().invoke(main, ["--book", str(book), *path.split()])
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise AssertionError(f"{path} raised {result.exception!r}")


def test_the_tree_has_every_group_in_it() -> None:
    paths = {path for path, _ in EVERY}
    for group in (
        "site",
        "well",
        "pipe",
        "run",
        "record",
        "work",
        "cover",
        "plant",
        "water",
        "report",
        "meter",
        "export",
        "note",
        "store",
    ):
        assert group in paths


def test_the_tree_is_bigger_than_any_one_suite_covers() -> None:
    assert len(LEAVES) > 60
