"""The note group."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.cli.support import Shell, furnish, shell


@pytest.fixture
def cli(tmp_path: Path) -> Shell:
    made = shell(tmp_path)
    furnish(made)
    return made


def write(cli: Shell, subject: str, body: str, at: str = "2025-04-08 16:20") -> str:
    return cli.ok("note", "write", subject, at, body, "--by", "D. Kasprzak")


def test_a_note_says_what_it_landed_against(cli: Shell) -> None:
    out = write(cli, "VW-001", "valve seized, freed with a wrench")
    assert "against device VW-001" in out


def test_a_note_against_an_area_says_so(cli: Shell) -> None:
    assert "against area A-03" in write(cli, "A-03", "ponding after the storm")


def test_a_label_the_book_never_issued_is_refused(cli: Shell) -> None:
    assert "VW-999" in cli.fails(
        "note", "write", "VW-999", "2025-04-08 16:20", "x", "--by", "D. K."
    )


def test_a_thing_nobody_wrote_about_says_so(cli: Shell) -> None:
    assert "nobody has written anything down" in cli.ok("note", "about", "VW-001")


def test_the_notes_about_a_thing_print_whole(cli: Shell) -> None:
    write(cli, "VW-001", "valve seized")
    out = cli.ok("note", "about", "VW-001")
    assert "valve seized" in out
    assert "D. Kasprzak" in out


def test_a_note_is_found_by_a_word_it_says(cli: Shell) -> None:
    write(cli, "VW-001", "valve seized, freed with a wrench")
    out = cli.ok("note", "find", "NORTHRIDGE", "wrench")
    assert "1 notes say" in out
    assert "VW-001" in out


def test_a_word_nobody_wrote_finds_nothing(cli: Shell) -> None:
    assert "0 notes say" in cli.ok("note", "find", "NORTHRIDGE", "badger")


def test_a_site_with_no_notes_says_so(cli: Shell) -> None:
    assert "nothing has been written down" in cli.ok("note", "recent", "NORTHRIDGE")


def test_the_recent_notes_come_back_newest_first(cli: Shell) -> None:
    write(cli, "VW-001", "first")
    write(cli, "A-03", "second", at="2025-05-08 09:00")
    out = cli.ok("note", "recent", "NORTHRIDGE")
    assert out.index("second") < out.index("first")


def test_the_counts_name_the_kinds_that_have_notes(cli: Shell) -> None:
    write(cli, "VW-001", "one")
    write(cli, "A-03", "two")
    out = cli.ok("note", "kinds", "NORTHRIDGE")
    assert "device" in out
    assert "area" in out


def test_the_notes_of_one_kind_can_be_listed(cli: Shell) -> None:
    write(cli, "VW-001", "one")
    write(cli, "A-03", "two")
    out = cli.ok("note", "kinds", "NORTHRIDGE", "--about", "area")
    assert "1 notes about a area" in out
    assert "A-03" in out
