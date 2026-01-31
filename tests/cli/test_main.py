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
