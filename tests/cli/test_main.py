"""The top level command and the book it opens."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from gemwalk import __version__
from gemwalk.cli.main import main, run
from gemwalk.store.migrations import MIGRATIONS


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def invoke(runner: CliRunner, book: Path, *args: str) -> Result:
    return runner.invoke(main, ["--book", str(book), *args])


def test_help_does_not_make_a_book(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    result = runner.invoke(main, ["--book", str(book), "--help"])
    assert result.exit_code == 0
    assert not book.exists()


def test_about_says_what_this_is(runner: CliRunner, tmp_path: Path) -> None:
    result = invoke(runner, tmp_path / "one.sqlite3", "about")
    assert result.exit_code == 0
    assert __version__ in result.output
    assert "landfill gas" in result.output


def test_the_version_flag_names_the_package(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "gemwalk" in result.output
    assert __version__ in result.output


def test_init_makes_a_book_at_the_current_schema(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    result = invoke(runner, book, "store", "init")
    assert result.exit_code == 0
    assert book.exists()
    assert f"schema {MIGRATIONS[-1].number}" in result.output


def test_init_twice_changes_nothing(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    result = invoke(runner, book, "store", "init")
    assert result.exit_code == 0
    assert str(MIGRATIONS[-1].number) in result.output


def test_counts_names_every_table(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    result = invoke(runner, book, "store", "counts")
    assert result.exit_code == 0
    assert "site" in result.output
    assert "device" in result.output
    assert "exceedance" in result.output


def test_check_passes_on_a_fresh_book(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    result = invoke(runner, book, "store", "check")
    assert result.exit_code == 0
    assert "nothing owed" in result.output


def test_the_book_can_come_out_of_the_environment(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    book = tmp_path / "fromenv.sqlite3"
    monkeypatch.setenv("GEMWALK_BOOK", str(book))
    result = runner.invoke(main, ["store", "init"])
    assert result.exit_code == 0
    assert book.exists()


def test_the_console_script_returns_zero_on_a_good_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("sys.argv", ["gemwalk", "--book", str(tmp_path / "x.sqlite3"), "about"])
    assert run() == 0


def test_the_console_script_returns_one_on_a_refusal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("sys.argv", ["gemwalk", "badger"])
    assert run() != 0


def test_seeding_fills_the_book(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    result = invoke(runner, book, "store", "seed")
    assert result.exit_code == 0
    assert "seeded" in result.output
    assert "device" in result.output


def test_seeding_twice_is_refused_without_force(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "seed")
    result = invoke(runner, book, "store", "seed")
    assert result.exit_code != 0
    assert "already has a site" in result.output


def test_a_seeded_book_prints_its_reports(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "seed")
    result = invoke(runner, book, "report", "year", "NORTHRIDGE", "2025")
    assert result.exit_code == 0
    assert "6 monitoring runs" in result.output


def test_verify_says_a_fresh_book_is_sound(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    result = invoke(runner, book, "store", "verify")
    assert result.exit_code == 0
    assert "sound" in result.output


def test_tidy_says_how_big_the_book_was_and_is(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "seed")
    result = invoke(runner, book, "store", "tidy")
    assert result.exit_code == 0
    assert "bytes before" in result.output


def test_a_backup_is_a_whole_book(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "seed")
    target = tmp_path / "copy.sqlite3"
    result = invoke(runner, book, "store", "backup", str(target))
    assert result.exit_code == 0
    assert target.exists()
    again = runner.invoke(main, ["--book", str(target), "store", "rows"])
    assert "reading" in again.output


def test_rows_comes_back_biggest_first(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "seed")
    result = invoke(runner, book, "store", "rows")
    assert result.exit_code == 0
    assert result.output.index("reading") < result.output.index("site")


def test_check_names_the_migrations_a_book_is_missing(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gemwalk.store.migrations import Migration

    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    extra = Migration(99, "one more", "CREATE TABLE later (x TEXT);")
    # Opening the book migrates it, so the only way to be behind by the time
    # the command runs is for the package to have grown a migration the book
    # has not seen, which is what this stands in for.
    monkeypatch.setattr("gemwalk.cli.main.pending", lambda _: [extra])
    result = invoke(runner, book, "store", "check")
    assert result.exit_code != 0
    assert "missing migrations" in result.output


def test_verify_refuses_a_book_with_a_row_pointing_at_nothing(
    runner: CliRunner, tmp_path: Path
) -> None:
    from gemwalk.store.book import Book

    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    with Book.open(book) as opened:
        opened.execute("PRAGMA foreign_keys = OFF")
        opened.execute(
            "INSERT INTO area (label, site, name, acres, first_waste, cover) "
            "VALUES ('A-99', 'NOWHERE', 'phase 99', 4.0, '2020-01-01', 'daily')"
        )
    result = invoke(runner, book, "store", "verify")
    assert result.exit_code != 0
    assert "not sound" in result.output
    assert "points at a site that is not there" in result.output


def test_the_console_script_prints_a_refusal_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = tmp_path / "northridge.sqlite3"
    monkeypatch.setattr("sys.argv", ["gemwalk", "--book", str(book), "site", "show", "NOWHERE"])
    assert run() != 0
    assert "NOWHERE" in capsys.readouterr().err + capsys.readouterr().out


def test_the_console_script_turns_a_bare_refusal_into_a_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from gemwalk.errors import RuleError

    def angry(**_: object) -> None:
        raise RuleError("something", "went wrong")

    monkeypatch.setattr("gemwalk.cli.main.main.main", angry)
    monkeypatch.setattr("sys.argv", ["gemwalk", "about"])
    assert run() == 1
    assert "error: something: went wrong" in capsys.readouterr().err


def test_the_console_script_says_so_when_it_is_stopped(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import click

    def stopped(**_: object) -> None:
        raise click.Abort

    monkeypatch.setattr("gemwalk.cli.main.main.main", stopped)
    monkeypatch.setattr("sys.argv", ["gemwalk", "about"])
    assert run() == 1
    assert "aborted" in capsys.readouterr().err


def test_review_says_a_seeded_book_looks_right(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "seed")
    result = invoke(runner, book, "store", "review", "NORTHRIDGE")
    assert result.exit_code == 0
    assert "nothing about these records looks wrong" in result.output


def test_review_names_what_is_wrong(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    invoke(
        runner,
        book,
        "site",
        "open",
        "NORTHRIDGE",
        "Northridge",
        "--subpart",
        "XXX",
        "--permit",
        "p",
        "--zone",
        "UTC",
        "--capacity",
        "1",
        "--opened",
        "2000-01-01",
    )
    result = invoke(runner, book, "store", "review", "NORTHRIDGE")
    assert result.exit_code == 0
    assert "3 things to look at" in result.output
    assert "burn the gas" in result.output


def test_review_can_be_narrowed_to_the_serious_ones(runner: CliRunner, tmp_path: Path) -> None:
    book = tmp_path / "northridge.sqlite3"
    invoke(runner, book, "store", "init")
    invoke(
        runner,
        book,
        "site",
        "open",
        "NORTHRIDGE",
        "Northridge",
        "--subpart",
        "XXX",
        "--permit",
        "p",
        "--zone",
        "UTC",
        "--capacity",
        "1",
        "--opened",
        "2000-01-01",
    )
    result = invoke(runner, book, "store", "review", "NORTHRIDGE", "--serious")
    assert result.exit_code == 0
    assert "1 things to look at" in result.output
